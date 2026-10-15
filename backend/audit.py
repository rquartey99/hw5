"""Append-only audit trail: one AuditStep per agent-loop step, written to output/audit_trail.json.

The file is a JSON array that only ever grows. Each step is appended as it happens (so a crash still
leaves a record), under a file lock, and written atomically (temp file + rename) so the array is never
half-written.
"""

from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_core import to_jsonable_python

from models import AuditStep, TeamDeps

HERE = Path(__file__).resolve().parent
AUDIT_PATH = Path(os.getenv("AUDIT_TRAIL", HERE.parent / "output" / "audit_trail.json"))
MAX_FIELD_CHARS = 4000  # long tool results are clipped so the trail stays readable


def _clip(value: Any) -> Any:
    """JSON-safe copy of value; anything that serializes longer than MAX_FIELD_CHARS becomes a clipped string."""
    data = to_jsonable_python(value, fallback=str)
    text = data if isinstance(data, str) else json.dumps(data)
    if len(text) <= MAX_FIELD_CHARS:
        return data
    return text[:MAX_FIELD_CHARS] + f"... [clipped {len(text) - MAX_FIELD_CHARS} chars]"


def _parts(parts) -> list[dict[str, Any]]:
    out = []
    for p in parts:
        item: dict[str, Any] = {"kind": p.part_kind}
        if hasattr(p, "tool_name"):
            item["tool"] = p.tool_name
            item["tool_call_id"] = getattr(p, "tool_call_id", None)
        if p.part_kind == "tool-call":
            item["args"] = _clip(p.args_as_dict())
        elif p.part_kind == "thinking":
            item["content"] = "[reasoning omitted]"
        elif hasattr(p, "content"):
            item["content"] = _clip(p.content)
        out.append(item)
    return out


def _usage(usage) -> dict[str, int]:
    return {
        k: getattr(usage, k, 0) or 0
        for k in ("requests", "tool_calls", "input_tokens", "output_tokens")
    }


def describe(node) -> tuple[str, str | None, dict[str, Any]]:
    """(node kind, model name, detail) for one node from Agent.iter()."""
    if Agent.is_user_prompt_node(node):
        return "user_prompt", None, {"prompt": _clip(node.user_prompt)}
    if Agent.is_model_request_node(node):
        return "model_request", None, {"parts": _parts(node.request.parts)}
    if Agent.is_call_tools_node(node):
        r = node.model_response
        return "model_response", r.model_name, {
            "parts": _parts(r.parts),
            "finish_reason": r.finish_reason,
            "request_usage": {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens},
        }
    if Agent.is_end_node(node):
        return "end", None, {"output": _clip(node.data.output)}
    return "error", None, {"unknown_node": type(node).__name__}


def append(step: AuditStep, path: Path = AUDIT_PATH) -> None:
    """Add one step to the end of the trail without touching earlier entries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = json.loads(path.read_text()) if path.exists() and path.stat().st_size else []
        entries.append(step.model_dump(mode="json"))
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, indent=1))
        tmp.replace(path)


def record_event(run_id: str, actor: str, node_kind: str, detail: dict) -> None:
    """A step that isn't part of an agent loop: a run starting/finishing, a person approving, a reset."""
    append(
        AuditStep(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            run_id=run_id,
            agent_run_id="",
            agent=actor,
            delegated_by=None,
            chain=[],
            depth=0,
            step=0,
            node=node_kind,
            detail=_clip(detail),
        )
    )


def read(after: int | None = None, limit: int = 100) -> tuple[list[dict], int]:
    """Entries from index `after` on (oldest first, at most `limit`); with no `after`, the latest `limit` entries.
    Also returns the total count, which the caller passes back as `after` next time to get only new entries."""
    if not AUDIT_PATH.exists() or not AUDIT_PATH.stat().st_size:
        return [], 0
    entries = json.loads(AUDIT_PATH.read_text())
    start = max(len(entries) - limit, 0) if after is None else max(after, 0)
    return [{"index": i, **e} for i, e in enumerate(entries[start:start + limit], start)], len(entries)


def record(deps: TeamDeps, step: int, node_kind: str, model: str | None, detail: dict, usage) -> None:
    append(
        AuditStep(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            run_id=deps.run_id,
            agent_run_id=deps.agent_run_id,
            agent=deps.agent,
            delegated_by=deps.chain[-2] if len(deps.chain) > 1 else None,
            chain=deps.chain,
            depth=deps.depth,
            step=step,
            node=node_kind,
            model=model,
            detail=detail,
            run_usage=_usage(usage),
        )
    )
