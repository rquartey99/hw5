"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")


class TaskReport(BaseModel):
    """What every agent hands back when it finishes a task (to the human or to the agent that delegated it)."""

    agent: AgentName
    ticket_ids: list[int] = Field(default_factory=list, description="Tickets this report is about.")
    status: Literal["done", "needs_human", "blocked", "info"] = Field(
        description="done = finished; needs_human = waiting on a person (approval, customer reply); "
        "blocked = can't proceed with the shop's data/tools; info = answered a question, nothing changed."
    )
    summary: str = Field(description="Plain-language result in 1-4 sentences.")
    facts: list[str] = Field(
        default_factory=list, description="Shop facts used, each as it came back from a tool (no invented numbers)."
    )
    actions_taken: list[str] = Field(
        default_factory=list, description="Changes made to the shop (payments, ticket updates, stock moves)."
    )
    needs_human: list[str] = Field(
        default_factory=list, description="Decisions a person must make before anything else happens."
    )


@dataclass
class TeamDeps:
    """Per-agent-run context. Child runs get a copy with themselves added to `chain`."""

    run_id: str  # one id for the whole team run, shared by every delegated agent
    agent: AgentName
    chain: list[AgentName]  # who delegated to whom, root first, ending with this agent
    allow_writes: bool = False  # write tools are hidden unless the human starts the run with writes on
    approver: str | None = None  # human named as payment approver; injected into record_payment
    agent_run_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def depth(self) -> int:
        return len(self.chain) - 1


class AuditStep(BaseModel):
    """One step of one agent loop, appended to output/audit_trail.json.

    People and the system log here too (agent = "human" / "system"): payment approvals, rejections, resets.
    """

    timestamp: str
    run_id: str
    agent_run_id: str
    agent: AgentName | Literal["human", "system"]
    delegated_by: AgentName | None
    chain: list[AgentName]
    depth: int
    step: int
    node: Literal[
        "user_prompt", "model_request", "model_response", "end", "error",
        "run_started", "run_finished", "approval_decided", "database_reset", "ticket_resolved",
    ]
    model: str | None = None
    detail: dict[str, Any]
    run_usage: dict[str, int] = Field(
        default_factory=dict, description="Cumulative usage for the whole team run at this step."
    )
