"""Campus Customs backend: FastAPI routes the desk board calls.

Start from this folder:  uvicorn main:app --reload --port 8000

Ticket runs happen in the background (they take a while); the board polls /api/events and /api/runs/{id}.
Payments the agents want to make wait in /api/approvals until a person clicks Approve.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import approvals
import audit
from agents import DB_PATH, ORIGINAL_DB, Team, call_mcp_tool

app = FastAPI(title="Campus Customs desk")
# The Vite dashboard (frontend/, `npm run dev`) runs on port 5173; let the browser call these routes from it.
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in FRONTEND_ORIGINS if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Swappable so tests can run the team on a scripted model instead of gpt-6-luna.
app.state.team_factory: Callable[[], Team] = Team
RUNS: dict[str, dict[str, Any]] = {}  # run_id -> status/report, for this server process
_tasks: set[asyncio.Task] = set()  # keep background runs referenced until they finish


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db() -> sqlite3.Connection:
    """Read-only connection to the working copy for the board's lookups."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _running() -> dict[str, Any] | None:
    return next((r for r in RUNS.values() if r["status"] == "running"), None)


# ---------------------------------------------------------------- request bodies


class RunRequest(BaseModel):
    allow_writes: bool = Field(True, description="Let agents update tickets/stock. Payments still wait for approval.")


class Decision(BaseModel):
    approver: str = Field(min_length=1, description="Name of the person clicking the button.")
    reason: str | None = None


# ---------------------------------------------------------------- routes


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "database": DB_PATH.name, "running": _running() is not None}


@app.get("/api/tickets")
def tickets() -> list[dict[str, Any]]:
    """Every ticket, with the raw status and a simple open/resolved flag for the board."""
    with _db() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM tickets ORDER BY id")]
    for r in rows:
        r["state"] = "resolved" if r["status"] == "closed" else "open"
    return rows


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int, body: RunRequest | None = None) -> dict[str, Any]:
    """Start the agent team on one ticket in the background and return its run_id right away."""
    body = body or RunRequest()
    with _db() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            raise HTTPException(404, f"No ticket {ticket_id}.")
    if busy := _running():
        raise HTTPException(409, f"Run {busy['run_id']} on ticket {busy['ticket_id']} is still going.")

    run_id = uuid.uuid4().hex[:12]
    RUNS[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "running", "started_at": _now(),
                    "finished_at": None, "report": None, "error": None}
    audit.record_event(run_id, "system", "run_started", {"ticket_id": ticket_id, "allow_writes": body.allow_writes})

    async def work() -> None:
        run = RUNS[run_id]
        try:
            team = app.state.team_factory()
            _, report = await team.run(f"Handle ticket {ticket_id}.", allow_writes=body.allow_writes, run_id=run_id)
            run.update(status="done", report=report.model_dump())
            if body.allow_writes:
                await _resolve_ticket(run_id, ticket_id, report.summary)
        except Exception as exc:
            run.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        run["finished_at"] = _now()
        audit.record_event(run_id, "system", "run_finished",
                           {"ticket_id": ticket_id, "status": run["status"], "error": run["error"]})

    task = asyncio.create_task(work())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"run_id": run_id, "ticket_id": ticket_id, "status": "running"}


async def _resolve_ticket(run_id: str, ticket_id: int, summary: str) -> None:
    """When a run finishes, mark its ticket resolved (closed) with the boss's summary, unless an agent already did."""
    with _db() as conn:
        status = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()["status"]
    if status == "closed":
        return
    result = await call_mcp_tool(
        "update_ticket",
        {"ticket_id": ticket_id, "status": "closed", "note": f"Resolved by agent team run {run_id}: {summary}"},
    )
    audit.record_event(run_id, "system", "ticket_resolved", {"ticket_id": ticket_id, "result": result})


@app.get("/api/runs/{run_id}")
def run_status(run_id: str) -> dict[str, Any]:
    """Status of a run started here: running, done (with the boss's report) or failed."""
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} in this server session.")
    return RUNS[run_id]


@app.get("/api/events")
def events(
    after: int | None = Query(None, description="Index to continue from (the `next` value of the last call)."),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """Recent audit-trail events, oldest first. Poll with ?after=<next> to get only new ones."""
    entries, total = audit.read(after, limit)
    return {"events": entries, "next": min(total, entries[-1]["index"] + 1) if entries else total}


@app.get("/api/approvals")
def list_approvals(status: str | None = Query(None, pattern="^(pending|approved|rejected|failed)$")):
    """Payments the agents asked for; ?status=pending for the ones waiting on a person.

    Each item also gets `payee` and `ticket_id` from the database so the board can say who gets paid and why.
    """
    items = approvals.list_all(status)
    with _db() as conn:
        for item in items:
            args = item["args"]
            if args.get("kind") == "lease":
                row = conn.execute(
                    "SELECT l.landlord AS payee, t.id AS ticket_id FROM leases l "
                    "LEFT JOIN tickets t ON t.lease_id = l.id WHERE l.id = ?", (args.get("ref_id"),)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT v.name AS payee, t.id AS ticket_id FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
                    "LEFT JOIN tickets t ON t.invoice_id = i.id WHERE i.id = ?", (args.get("ref_id"),)
                ).fetchone()
            item["payee"] = row["payee"] if row else None
            item["ticket_id"] = row["ticket_id"] if row else None
    return items


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: str, body: Decision) -> dict[str, Any]:
    """A person approves a queued payment: it runs through the MCP server's checks with their name on it."""
    item = approvals.get(approval_id)
    if item is None:
        raise HTTPException(404, f"No approval {approval_id}.")
    if item["status"] != "pending":
        raise HTTPException(409, f"Approval {approval_id} is already {item['status']}.")
    result = await call_mcp_tool(item["tool"], {**item["args"], "approved_by": body.approver.strip()})
    status = "failed" if isinstance(result, dict) and "error" in result else "approved"
    item = approvals.decide(approval_id, status, body.approver.strip(), result)
    audit.record_event(item["run_id"], "human", "approval_decided",
                       {"approval_id": approval_id, "decision": status, "by": item["decided_by"],
                        "tool": item["tool"], "args": item["args"], "result": result})
    return item


@app.post("/api/approvals/{approval_id}/reject")
def reject(approval_id: str, body: Decision) -> dict[str, Any]:
    """A person turns a queued payment down. Nothing is paid."""
    item = approvals.decide(approval_id, "rejected", body.approver.strip(), {"reason": body.reason})
    if item is None:
        raise HTTPException(409, f"Approval {approval_id} doesn't exist or isn't pending.")
    audit.record_event(item["run_id"], "human", "approval_decided",
                       {"approval_id": approval_id, "decision": "rejected", "by": item["decided_by"],
                        "reason": body.reason})
    return item


@app.get("/api/cash")
def cash() -> dict[str, Any]:
    """Current checking balance from cash_accounts."""
    with _db() as conn:
        row = conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()
    if row is None:
        raise HTTPException(404, "No checking account.")
    return dict(row)


@app.post("/api/reset")
def reset() -> dict[str, Any]:
    """Put the working copy back to the original database's values for a fresh run.

    Clears queued approvals (they point at the old state). The audit trail is kept: it is append-only.
    """
    if busy := _running():
        raise HTTPException(409, f"Run {busy['run_id']} is still going; reset after it finishes.")
    src = sqlite3.connect(f"file:{ORIGINAL_DB}?mode=ro", uri=True)
    dst = sqlite3.connect(DB_PATH)
    try:
        src.backup(dst)  # page-by-page copy; safe even if another process has the file open
    finally:
        src.close()
        dst.close()
    cleared = approvals.clear()
    audit.record_event("reset", "system", "database_reset",
                       {"copied_from": ORIGINAL_DB.name, "to": DB_PATH.name, "approvals_cleared": cleared})
    return {"status": "reset", "database": DB_PATH.name, "approvals_cleared": cleared}
