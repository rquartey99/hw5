"""Payments waiting for a person.

When an agent calls record_payment in a run with no human approver, agents.guard_tool_call queues it here
instead of paying. The board lists pending items; a person clicks Approve (main.py runs the payment through
the MCP server with their name as approved_by) or Reject. Stored in output/pending_approvals.json.
"""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
APPROVALS_PATH = Path(os.getenv("APPROVALS_FILE", HERE.parent / "output" / "pending_approvals.json"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _locked():
    """Load the list under a file lock and save it back when the block finishes."""
    APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(APPROVALS_PATH.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        items = json.loads(APPROVALS_PATH.read_text()) if APPROVALS_PATH.exists() else []
        yield items
        tmp = APPROVALS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(items, indent=1))
        tmp.replace(APPROVALS_PATH)


def queue(run_id: str, agent: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Add a pending action. approved_by is dropped: only the person who clicks Approve supplies it."""
    item = {
        "id": uuid.uuid4().hex[:8],
        "status": "pending",
        "created_at": _now(),
        "run_id": run_id,
        "requested_by": agent,
        "tool": tool,
        "args": {k: v for k, v in args.items() if k != "approved_by"},
        "decided_by": None,
        "decided_at": None,
        "result": None,
    }
    with _locked() as items:
        items.append(item)
    return item


def list_all(status: str | None = None) -> list[dict[str, Any]]:
    with _locked() as items:
        return [i for i in items if status is None or i["status"] == status]


def get(approval_id: str) -> dict[str, Any] | None:
    return next((i for i in list_all() if i["id"] == approval_id), None)


def decide(approval_id: str, status: str, by: str, result: Any = None) -> dict[str, Any] | None:
    """Record approved / rejected / failed. Only a pending item can be decided."""
    with _locked() as items:
        for item in items:
            if item["id"] == approval_id and item["status"] == "pending":
                item.update(status=status, decided_by=by, decided_at=_now(), result=result)
                return item
    return None


def clear() -> int:
    """Drop every item (used by the database reset). Returns how many were removed."""
    with _locked() as items:
        n = len(items)
        items.clear()
    return n
