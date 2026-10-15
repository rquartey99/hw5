"""The Campus Customs agent team: five PydanticAI agents that share one MCP connection and can delegate to each other.

Roles (prompts in prompts/<role>.md, MCP tools per role in ROLE_TOOLS):
    boss              - owns the ticket queue, routes work, settles conflicts
    inventory         - stock, fulfilment, restock vendors
    accounting        - cash, pricing/margins, payments
    facilities        - leases and rent
    customer_service  - requesters, replies, quotes

Every agent also has `delegate(to, task)`, so any agent can hand work to any other (full connectivity).
Loops are bounded: no self-delegation, no cycles, a depth cap, and one usage budget for the whole team run.
Every agent-loop step is appended to output/audit_trail.json (see audit.py).
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.client.transports import StdioTransport  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, RunContext  # noqa: E402
from pydantic_ai.exceptions import UsageLimitExceeded  # noqa: E402
from pydantic_ai.mcp import MCPToolset  # noqa: E402
from pydantic_ai.models import Model  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.settings import ModelSettings  # noqa: E402
from pydantic_ai.usage import RunUsage, UsageLimits  # noqa: E402

import approvals  # noqa: E402
import audit  # noqa: E402
from models import AGENT_NAMES, AgentName, TaskReport, TeamDeps  # noqa: E402

HERE = Path(__file__).resolve().parent
HW_ROOT = HERE.parent  # hw5/
load_dotenv(HW_ROOT / ".env")  # hw5/.env (copy .env.example and add your key)

MODEL_NAME = "gpt-6-luna"  # user's choice for every agent in Homework 5
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
PROMPTS_DIR = HERE / "prompts"
MCP_PYTHON = Path(sys.executable)  # the same venv that runs the backend (hw5/.venv)
MCP_SERVER = HW_ROOT / "mcp_server" / "server.py"
RULES_TODO = "TODO(Regi)"
ORIGINAL_DB = HW_ROOT / "data" / "campus_customs.db"
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB", HW_ROOT / "data" / "campus_customs_new.db"))  # working copy

# ---------------------------------------------------------------- limits (keep token use in check)
MAX_DELEGATION_DEPTH = 2  # boss -> teammate -> one more teammate, no deeper
TEAM_USAGE_LIMITS = UsageLimits(  # shared by every agent in one team run
    request_limit=30,
    tool_calls_limit=40,
    total_tokens_limit=200_000,
)
MODEL_SETTINGS = ModelSettings(max_tokens=4000)  # cap on any single model response

# ---------------------------------------------------------------- which MCP tools each role sees
WRITE_TOOLS = {"update_ticket", "fulfill_order", "record_payment", "add_desk_note"}
ROLE_TOOLS: dict[AgentName, set[str]] = {
    "boss": {"list_open_tickets", "get_ticket", "get_cash_position", "update_ticket", "add_desk_note"},
    "inventory": {"check_order_fulfillment", "check_stock", "fulfill_order", "list_vendors", "get_ticket"},
    "accounting": {"get_cash_position", "quote_bulk_discount", "record_payment", "list_vendors", "get_ticket"},
    "facilities": {"get_lease", "get_ticket", "update_ticket"},
    "customer_service": {"get_ticket", "list_open_tickets", "check_stock", "quote_bulk_discount", "update_ticket"},
}


class AgentUnavailable(RuntimeError):
    """The team can't run (e.g. PORTKEY_API_KEY missing)."""


def build_model() -> Model:
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentUnavailable("PORTKEY_API_KEY is not set in the project .env file.")
    client = AsyncOpenAI(api_key=api_key, base_url=PORTKEY_BASE_URL, default_headers={"x-portkey-api-key": api_key})
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


async def guard_tool_call(ctx: RunContext[TeamDeps], call_tool, name: str, args: dict[str, Any]):
    """Runs before every MCP tool call: blocks writes unless the human allowed them, and keeps payments in human
    hands. With a named approver (CLI --approver) their name is stamped on the payment; without one the payment is
    queued for a person to approve on the board. Either way an agent can never approve its own payment."""
    if name in WRITE_TOOLS and not ctx.deps.allow_writes:
        return {"error": f"{name} changes the shop and this run is read-only. Nothing changed."}
    if name == "record_payment":
        if not ctx.deps.approver:
            item = approvals.queue(ctx.deps.run_id, ctx.deps.agent, name, args)
            return {
                "status": "pending_human_approval",
                "approval_id": item["id"],
                "message": "Queued for a person to approve on the board. Nothing has been paid yet. "
                           "Report it under needs_human.",
            }
        args = {**args, "approved_by": ctx.deps.approver}
    return await call_tool(name, args)


def _transport() -> StdioTransport:
    """Launch mcp_server/server.py over stdio with the backend's Python, pointed at this backend's working copy."""
    return StdioTransport(
        command=str(MCP_PYTHON),
        args=[str(MCP_SERVER)],
        cwd=str(MCP_SERVER.parent),
        env={"CAMPUS_CUSTOMS_DB": str(DB_PATH)},
    )


def mcp_toolset(source: Any = None) -> MCPToolset:
    """One MCP connection for the whole team."""
    return MCPToolset(source or _transport(), process_tool_call=guard_tool_call, max_retries=1)


async def call_mcp_tool(name: str, args: dict[str, Any]) -> Any:
    """Call one MCP tool directly, outside any agent (used when a person approves a queued payment)."""
    async with Client(_transport()) as client:
        result = await client.call_tool(name, args, raise_on_error=False)
    if result.structured_content is not None:
        return result.structured_content
    return {"error": " ".join(getattr(c, "text", "") for c in result.content)}


def load_prompt(role: AgentName) -> str:
    return (PROMPTS_DIR / f"{role}.md").read_text()


def prompts_missing_rules() -> list[AgentName]:
    """Roles whose prompt still has the shop-rules placeholder."""
    return [role for role in AGENT_NAMES if RULES_TODO in load_prompt(role)]


class Team:
    """Builds the five agents and runs them. `model`/`toolset` can be swapped for offline tests."""

    def __init__(self, model: Model | None = None, toolset: MCPToolset | None = None):
        self.model = model or build_model()
        self.toolset = toolset or mcp_toolset()
        self.agents: dict[AgentName, Agent[TeamDeps, TaskReport]] = {r: self._build(r) for r in AGENT_NAMES}

    def _build(self, role: AgentName) -> Agent[TeamDeps, TaskReport]:
        allowed = ROLE_TOOLS[role]

        def role_filter(ctx: RunContext[TeamDeps], tool_def) -> bool:
            return tool_def.name in allowed and (ctx.deps.allow_writes or tool_def.name not in WRITE_TOOLS)

        agent = Agent(
            self.model,
            name=role,
            deps_type=TeamDeps,
            output_type=TaskReport,
            toolsets=[self.toolset.filtered(role_filter)],
            model_settings=MODEL_SETTINGS,
            retries=2,
        )

        @agent.instructions
        def instructions(ctx: RunContext[TeamDeps]) -> str:
            # Re-read every run so prompt edits apply without a restart.
            d = ctx.deps
            return (
                load_prompt(role)
                + "\n\n## This run\n"
                + f"- You are: {role}\n"
                + f"- Delegation chain: {' -> '.join(d.chain)} (depth {d.depth} of max {MAX_DELEGATION_DEPTH})\n"
                + f"- Shop changes: {'ALLOWED' if d.allow_writes else 'NOT allowed (read-only run)'}\n"
                + f"- Payment approver: {d.approver or 'none - record_payment queues it for a person to approve; list it in needs_human'}\n"
                + f"- Set `agent` in your TaskReport to '{role}'.\n"
            )

        @agent.tool
        async def delegate(ctx: RunContext[TeamDeps], to: AgentName, task: str) -> TaskReport | str:
            """Hand a task to a teammate and get their TaskReport back.

            Args:
                to: boss, inventory, accounting, facilities or customer_service.
                task: What you need, including ticket ids and exactly what to report back.
            """
            return await self.delegate(ctx, to, task)

        return agent

    async def delegate(self, ctx: RunContext[TeamDeps], to: AgentName, task: str) -> TaskReport | str:
        d = ctx.deps
        if to == d.agent:
            return "You can't delegate to yourself. Do the task with your own tools or pick a teammate."
        if to in d.chain:
            return (f"{to} is already in this delegation chain ({' -> '.join(d.chain)}). "
                    "Don't loop back; finish with what you have and report it.")
        if d.depth >= MAX_DELEGATION_DEPTH:
            return "Delegation depth limit reached. Finish with your own tools and list what's left in needs_human."
        child = TeamDeps(
            run_id=d.run_id, agent=to, chain=[*d.chain, to], allow_writes=d.allow_writes, approver=d.approver
        )
        try:
            return await self.run_agent(to, task, child, usage=ctx.usage)
        except UsageLimitExceeded:
            raise  # the team budget is a hard stop for everyone
        except Exception as exc:  # a teammate failing shouldn't crash the caller; tell it instead
            return f"{to} failed: {type(exc).__name__}: {exc}"

    async def run_agent(
        self, role: AgentName, prompt: str, deps: TeamDeps, usage: RunUsage | None = None
    ) -> TaskReport:
        """One agent loop, stepped node by node so every step lands in the audit trail."""
        deps.agent_run_id = uuid.uuid4().hex[:12]
        step = 0
        try:
            async with self.agents[role].iter(
                prompt, deps=deps, usage=usage, usage_limits=TEAM_USAGE_LIMITS
            ) as run:
                async for node in run:
                    step += 1
                    kind, model, detail = audit.describe(node)
                    audit.record(deps, step, kind, model, detail, run.usage)
                return run.result.output
        except Exception as exc:
            audit.record(deps, step + 1, "error", None, {"error": f"{type(exc).__name__}: {exc}"}, usage or RunUsage())
            raise

    async def run(
        self, prompt: str, *, allow_writes: bool = False, approver: str | None = None, run_id: str | None = None
    ) -> tuple[str, TaskReport]:
        """Start a team run at the boss. Returns (run_id, boss's final report)."""
        run_id = run_id or uuid.uuid4().hex[:12]
        deps = TeamDeps(run_id=run_id, agent="boss", chain=["boss"], allow_writes=allow_writes, approver=approver)
        async with self.toolset:  # one MCP connection shared by every agent in the run
            report = await self.run_agent("boss", prompt, deps)
        return run_id, report
