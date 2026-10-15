# Campus Customs Desk: Homework 5

A five-agent team that works the Campus Customs shop's open tickets, with a person approving every payment.

- **MCP server** (`mcp_server/server.py`): FastMCP tools over the shop database. It is the only way the agents touch the data.
- **Agent team** (`backend/`): five PydanticAI agents (boss, inventory, accounting, facilities, customer service) on OpenAI's `gpt-6-luna` through Portkey. Any agent can delegate to any other.
- **Backend** (`backend/main.py`): FastAPI routes that run the team, list tickets and events, hold payments for human approval, show cash, and reset the database.
- **Desk board** (`frontend/`): React + Vite + TypeScript dashboard for watching the agents work and approving payments.

Start with **`output/harness.md`** for the full picture: tables, tools, agents, routes, dashboard and safety rules.

## What's in this folder

```
hw5/
├── AI_prompts.md            prompts used for each problem
├── README.md                this file
├── requirements.txt         Python packages (one shared venv for backend + MCP server)
├── .env.example             template for the API key file
├── .gitignore
├── .mcp.json                registers the MCP server with Claude Code (open hw5/ in Claude Code)
├── data/
│   ├── campus_customs.db        ORIGINAL database. Never modified.
│   └── campus_customs_new.db    WORKING copy. Everything reads and writes this one.
├── mcp_server/
│   ├── server.py            the campus-customs MCP server (12 tools)
│   └── README.md
├── backend/
│   ├── main.py              FastAPI routes
│   ├── models.py            data types (TaskReport, TeamDeps, AuditStep)
│   ├── agents.py            the 5 agents, delegation, guardrails, agent loop
│   ├── audit.py             append-only audit trail
│   ├── approvals.py         payments waiting for a person
│   ├── run.py               command-line runner
│   └── prompts/             boss.md, inventory.md, accounting.md, facilities.md, customer_service.md
├── frontend/                React + Vite + TypeScript desk board
└── output/
    ├── harness.md           how the whole system works
    ├── mcp_smoke.json       each MCP tool called through Claude Code, checked against the DB
    ├── desk_tickets.html    Expected vs Actual per ticket, itemized Cash, Reflection (double-click to open)
    ├── design.md            dashboard look and why
    ├── resolved_tickets.json  per-ticket outcome, agent contributions, human approvals
    ├── resolved_board.html  screenshots of the board for each resolved ticket (double-click to open)
    ├── audit_trail.json     every agent step, approval and reset (append-only)
    └── github_url.txt       link to this repo
```

The committed `data/campus_customs_new.db` holds the state **after** the Problem 9 run: all 3 tickets resolved, rent paid, and checking at $1,000. Steps 1 and 5 below put it back to the original for a fresh run.

## Requirements
- **Python 3.11+** (tested with 3.14)
- **Node.js 20.19+** (tested with 24)
- A **Portkey API key** with access to OpenAI's `gpt-6-luna`

## Setup (once)

From inside `hw5/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then open .env and paste your Portkey key
cd frontend && npm install && cd ..
```

The key is read by `backend/agents.py` from `hw5/.env` and is never sent to the browser.

## 1. Copy the original database to the working one (when you need a clean run)

Do this with the backend stopped. It throws away everything the agents changed: payments, ticket statuses, desk notes.

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Checking goes back to **$3,400**, tickets 101–103 are `open`, and there are no payments. Never edit `data/campus_customs.db` itself.

## 2. Start the MCP server

The backend starts its own copy of the MCP server over stdio for every team run, so **you don't need to start it for the board to work**. To run it yourself (for example, to inspect the tools):

```bash
.venv/bin/python mcp_server/server.py            # stdio
.venv/bin/python mcp_server/server.py --http     # http://127.0.0.1:8001/mcp
```

To call the tools from Claude Code, open the `hw5/` folder in Claude Code and approve the `campus-customs` server from `.mcp.json`. It uses `.venv/bin/python`, so do the setup first.

## 3. Start the FastAPI backend (terminal 1)

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

Check it at http://127.0.0.1:8000/api/health. The routes are listed in `output/harness.md`, section 4.

## 4. Start the React board (terminal 2)

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The bottom-left corner should say "Connected · http://127.0.0.1:8000".

## 5. Reset the database before a full 3-ticket run

With both servers running, reset from the board or the API. Either one copies the original values into the working database and clears any queued approvals; the audit trail is kept.
- **On the board:** click **Reset shop data** (bottom right).
- **From a terminal:**

  ```bash
  curl -X POST http://127.0.0.1:8000/api/reset
  ```

Then run the tickets **one at a time**:
1. Type your name under **Approving as** (top right).
2. Select **#102 Rent due** and press **Send in the team**. Rent comes first under the shop rules. When accounting queues the $2,400 rent check, click **Approve**. Checking drops to $1,000.
3. Select **#101 Bulldog tee** and press **Send in the team**.
4. Select **#103 Bulk hoodie discount** and press **Send in the team**.

Each ticket is marked **Resolved** when its run finishes. Every step is added to `output/audit_trail.json`.

### Command-line option

```bash
cd backend
../.venv/bin/python run.py --ticket 101        # read-only
../.venv/bin/python run.py --ticket 102 --allow-writes --approver "Your Name"
```

## Safety in short
- Agents can't pay anything themselves. Payments wait on the board until a person clicks Approve, and that person's name is recorded.
- Every write is checked against the data: exact amounts, no double payments, no overdrafts, no shipping stock that isn't there.
- Each agent sees only the tools for its job. The original database can't be opened by the tools.
- One token, request and tool-call budget covers a whole team run, and delegation is at most 2 levels deep.

See `output/harness.md`, section 6, for the full rules.
