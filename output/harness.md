# Campus Customs Agent Harness

How the Campus Customs desk works end to end:
- **Data:** a SQLite shop database.
- **MCP server:** the only way agents touch that data.
- **Agents:** a five-agent PydanticAI team that delegates work to each other.
- **Backend:** a FastAPI app that runs the team and holds payments for a person to approve.
- **Dashboard:** a React board where you watch the team and approve or decline payments.

```
React board (frontend/, :5173) ──HTTP──▶ FastAPI (backend/main.py, :8000)
                                             │ runs
                                             ▼
                          boss ⇄ inventory ⇄ accounting ⇄ facilities ⇄ customer_service   (PydanticAI, gpt-6-luna)
                                             │ MCP (stdio)
                                             ▼
                          campus-customs MCP server (mcp_server/server.py)
                                             │ SQL
                                             ▼
                          data/campus_customs_new.db   (working copy; original never touched)
```

**Quick start** (two terminals):

```bash
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

Then open http://localhost:5173.

---

## 1. Database

### Files
| File | Role |
|---|---|
| `data/campus_customs.db` | **Original. Read-only.** Never modified. `POST /api/reset` copies its values back into the working copy. |
| `data/campus_customs_new.db` | **Working copy.** Every agent, tool, route and problem reads and writes this file only. |

### The shop's "today"
`desk.date_today` is **2026-08-31**. Agents use it, not the real clock, for anything due or overdue.

### Tables
Only three real foreign keys exist: `tickets.invoice_id → invoices.id`, `tickets.lease_id → leases.id`, and `invoices.vendor_id → vendors.id`. Every other link is matched by value, so agents make those joins through the tools.

```
vendors ──< invoices ──< tickets >── leases
                              │
                       sku + size (no FK, matched by value)
                              │
                 inventory (sku, size) ── pricing (sku)

payments ── kind + ref_id → invoices.id or leases.id (no FK)
payments.account → cash_accounts.name (no FK)
```

Row counts below are the original values (after a reset).

| Table | Fields | Why it matters for the agents |
|---|---|---|
| `desk` (1) | `date_today`, `notes` | The shop's clock and shared notepad. "Today" decides what's overdue. The boss leaves readable handoff notes for a human reviewer in `notes`. |
| `inventory` (10; key `sku`+`size`) | `sku`, `name`, `size`, `qty`, `location` | Stock on hand by size and aisle. Inventory checks it before anything is promised: tee S = 0 (ticket 101), hoodie M = 8 of 20 wanted (ticket 103). The Crest Mug is also out of stock. |
| `pricing` (4) | `sku`, `unit_cost`, `list_price` | Cost and list price, so the margin floor for any discount. A hoodie is $22 cost and $58 list. |
| `vendors` (3) | `id`, `name`, `specialty`, `lead_days` | Who restocks what, and how fast: Bulldog Print Co (apparel, 5 days), Elm City Gifts (mugs, 3 days), QuickShip CT (courier, 1 day). Used for suggested delivery dates. |
| `leases` (1) | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes` | Rent for the Chapel Street shop: $2,400 to Elm City Properties, due 2026-09-02. It's the biggest fixed bill, and your rules pay it first. |
| `cash_accounts` (1) | `name`, `balance`, `date` | Checking: $3,400 at the start. Every spending decision depends on it. The board shows it live. |
| `payments` (0) | `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | The ledger of money actually paid. `approved_by` is required, so every payment names the person who approved it. |
| `invoices` (1) | `id`, `vendor_id`, `amount`, `due_date`, `status`, `description` | Vendor bills. Invoice 501 is an $840 rush reprint of the size S tee, due 2026-08-28 and still open (3 days overdue). |
| `tickets` (3) | `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at` | The work queue. `type` says who should own a ticket. The link columns say which tables to pull. `status` is `open`, `in_progress` or `closed`. |

### The 3 tickets and how they link
- **101, customer order (Tauhid Zaman):** wants 1 × `CC-TEE-WHITE`, size S. Stock for S is **0** (M 5, L 3, XL 2). It links to invoice 501, the $840 rush reprint from Bulldog Print Co, which is overdue and has a 5-day lead time.
- **102, rent notice (Elm City Properties):** lease 1, **$2,400** due 2026-09-02. Checking ($3,400) covers it and leaves $1,000.
- **103, price override (Yale AI Club):** wants 20 × `CC-HOOD-NAVY`, size M, at a discount. Only **8** are on hand (12 short). Cost is $22 and list is $58, so 20 at list is $1,160 and the cost floor is $440.
- **They compete for the same cash:** rent ($2,400) plus invoice 501 ($840) is $3,240, which leaves only $160. That's why the team has to share context and why a person approves the money.

### Gaps worth knowing
- There's no customer table (`requester` is free text) and no way to message customers.
- `tickets.sku` has no foreign key to `inventory` or `pricing`. Invoice 501 names its SKU only inside its description.
- `payments.kind` + `ref_id` has no database-level foreign key. `record_payment` enforces it instead.

---

## 2. MCP server: `mcp_server/server.py` (`campus-customs`)

This FastMCP server is the agents' only route to `data/campus_customs_new.db`. Read tools open the file read-only. Write tools check every change against the data first and change nothing if a check fails. The server refuses to start if it's pointed at the original database.

| Tool | Tables: read (R) / write (W) | Used by | Added | Main ticket |
|---|---|---|---|---|
| `check_order_fulfillment(ticket_id)` | R: tickets, inventory, invoices, vendors, desk | inventory | P3 | **101** |
| `get_cash_position()` | R: cash_accounts, leases, invoices, vendors, payments, desk | boss, accounting | P3 | **102** |
| `quote_bulk_discount(sku, size, qty, discount_pct)` | R: pricing, inventory | accounting, customer_service | P3 | **103** |
| `list_open_tickets()` | R: tickets | boss, customer_service | P5 | all |
| `get_ticket(ticket_id)` | R: tickets | all 5 | P5 | all |
| `check_stock(sku, size?)` | R: inventory | inventory, customer_service | P5 | 101, 103 |
| `list_vendors()` | R: vendors | inventory, accounting | P5 | 101, 103 |
| `get_lease(lease_id)` | R: leases, payments, desk | facilities | P5 | 102 |
| `update_ticket(ticket_id, status, note)` | **W: tickets** (R: desk) | boss, facilities, customer_service | P5 | all |
| `fulfill_order(ticket_id)` | **W: inventory, tickets** (R: desk) | inventory | P5 | 101 |
| `record_payment(kind, ref_id, amount, account, approved_by)` | **W: payments, cash_accounts, invoices** (R: leases, desk) | accounting | P5 | 102 (and 101's invoice) |
| `add_desk_note(note)` | **W: desk** | boss | P5 | all |

**Why the three Problem 3 tools fit their tickets:**
- `check_order_fulfillment` puts 101's stock check and its restock invoice in one answer.
- `get_cash_position` shows 102's rent next to every other bill on the same cash.
- `quote_bulk_discount` tests 103's discount levels against cost and stock.

**What the write tools check:**
- **`update_ticket`:** the status must be `open`, `in_progress` or `closed`, and a note is required. The note is added to the ticket with the desk date.
- **`fulfill_order`:** only ships an open `customer_order` when stock covers the whole quantity.
- **`record_payment`:** pays only when all of these hold:
  - the amount exactly equals the invoice amount or the monthly rent
  - the bill is unpaid
  - the account covers it
  - an approver is named

  It then inserts a payment, lowers the balance, and marks a paid invoice `paid`.
- **`get_cash_position`:** stops counting rent once a lease payment exists for the current due date.

The server is registered for Claude Code in `hw5/.mcp.json`. Each tool was tested over that connection, and the results are in `output/mcp_smoke.json`.

---

## 3. The 5 agents: `backend/`

There are five PydanticAI agents, all on **`gpt-6-luna`** through Portkey (`PORTKEY_API_KEY` from `hw5/.env`). Prompts live in `backend/prompts/<agent>.md`. Each prompt has a role section (written by Claude) and a **Shop rules** section (written by Regi, word for word). Each agent finishes with a `TaskReport` (`backend/models.py`) containing:
- `status`: `done`, `needs_human`, `blocked` or `info`
- `summary`
- `facts`
- `actions_taken`
- `needs_human`

| Agent | Job | MCP tools | Shop rules (Regi's, condensed) |
|---|---|---|---|
| **boss** | Entry point. Reads the ticket, routes work, combines reports, settles conflicts. | list_open_tickets, get_ticket, get_cash_position, update_ticket, add_desk_note | Prioritize paying rent. Close a ticket when the requester is satisfied. Leave a very readable audit trail in desk notes. |
| **inventory** | Stock, whether an order ships, fulfilment, vendors and lead times. | check_order_fulfillment, check_stock, fulfill_order, list_vendors, get_ticket | Offer stock if it covers the order. If not, offer another size or a backorder. Reorders are a human's call. Suggest delivery dates but don't promise them. |
| **accounting** | Cash against bills, discount margins, payments. | get_cash_position, quote_bulk_discount, record_payment, list_vendors, get_ticket | Rent first. Warn when the balance falls below $500. Never sell below cost; step discounts up based on how likely the customer is to buy. Rush reprints are never worth it. |
| **facilities** | Leases and landlord tickets. | get_lease, get_ticket, update_ticket | Pay rent 10–15 days before it's due. Alert a human right away if funds can't cover rent. Only pass the ticket on. |
| **customer_service** | Requesters, replies, quotes. | get_ticket, list_open_tickets, check_stock, quote_bulk_discount, update_ticket | Polite and friendly. Promises must come from the database. Fill bulk orders if stock covers them, otherwise alert a human. Send simple replies; draft complex ones for Regi. |

**Full connectivity:** every agent also has `delegate(to, task)` and can hand work to any of the other four. The teammate's `TaskReport` comes back as the tool result.

**Files:**
- `agents.py`: roles, tool access, delegation, guardrails, the agent loop
- `models.py`: data types
- `audit.py`: the audit trail
- `approvals.py`: the payment queue
- `run.py`: command line
- `main.py`: the API

**Agent loop:** `Team.run_agent()` steps through `Agent.iter()` one node at a time (user prompt → model request → model response with tool calls → … → end). It appends each node to `output/audit_trail.json` as it happens.

**Audit trail:** append-only, never wiped. Each step records:
- `timestamp`
- `run_id` (shared across the whole team run)
- `agent_run_id`
- `agent`, `delegated_by` and the full `chain`
- `depth` and `step`
- `node`
- the model that answered
- the details: prompt, tool calls and arguments, tool results (clipped at 4,000 characters), finish reason, tokens per request, final report
- cumulative team usage

People and the system log there too: `run_started`, `run_finished`, `ticket_resolved`, `approval_decided` and `database_reset`.

---

## 4. API routes: `backend/main.py` (port 8000)

- `GET /api/health`: server is up, which database it uses, and whether a run is in progress.
- `GET /api/tickets`: all 3 tickets with their raw `status` and `state` (`open` or `resolved`).
- `POST /api/tickets/{ticket_id}/run`: starts the team on a ticket in the background and returns a `run_id`. One run at a time. When it finishes, the ticket is marked resolved.
- `GET /api/runs/{run_id}`: `running`, `done` (with the boss's report) or `failed`.
- `GET /api/events?after=N&limit=100`: audit-trail events, oldest first. Pass back `next` to get only new events.
- `GET /api/approvals?status=pending`: payments waiting on a person, with `payee` and `ticket_id`.
- `POST /api/approvals/{id}/approve` (body `{"approver": "Name"}`): a person approves. The payment runs through `record_payment`'s checks with their name on it.
- `POST /api/approvals/{id}/reject` (body `{"approver": "Name", "reason": "..."}`): a person declines. Nothing is paid.
- `GET /api/cash`: current checking balance from `cash_accounts`.
- `POST /api/reset`: copies the original database values back into the working copy and clears queued approvals. The audit trail is kept. Refused while a run is in progress.

CORS allows the Vite page at `http://localhost:5173` and `http://127.0.0.1:5173` (`FRONTEND_ORIGINS` overrides this).

---

## 5. Dashboard: `frontend/` (React + Vite + TypeScript, port 5173)

- **Tickets:** all 3, each marked Open, Team working or Resolved, with a stamp on resolved ones.
- **Send in the team:** starts a run on the selected ticket.
- **Agent cards:** the boss is Handsome Dan. Each card shows live status and what the agent is doing or saying. The active agent glows gold, a breadcrumb shows the hand-offs, and the full conversation is one click away.
- **What each agent did:** a short summary from each agent's `TaskReport` once the run ends.
- **Approvals:** a payment waiting for approval appears as a paper check to sign as the name under "Approving as", with Approve or Decline.
- **Checking balance:** top right. It turns amber below $500, matching accounting's rule.

The look is Homework 4's Yale palette, plus a late-summer, move-in-week theme keyed to the desk date. See `output/design.md`.

---

## 6. Safety rules

### Built in
- **A human approves money.** An agent's `record_payment` call never pays on its own. It is queued and shown on the board, and the payment happens only when a person clicks Approve. Their name, not the agent's, is written as `approved_by`. From the command line, payments need `--approver "Name"`.
- **Read-only unless allowed.** Write tools are hidden unless the run allows writes. Board runs allow ticket and stock updates; `run.py` is read-only by default.
- **The data checks every write.** Amounts must be exact. There are no double payments, no overdrafts, no shipping more than is in stock, and statuses come from a fixed list. A failed check changes nothing.
- **Least privilege.** Each role sees only its own tools. Only accounting can pay and only inventory can ship.
- **The original is protected.** Only the working copy is reachable, and the MCP server refuses the original. Reset restores it.
- **No invented facts.** Every number must come from a tool, and reports list the facts they used.
- **Shop rules in the prompts.** These are Regi's rules, listed in section 3: rent first, never below cost, warn under $500, humans decide reorders and discounts, no promised dates.
- **Everything is auditable.** Every agent step, tool call, result, approval and reset is in the append-only trail.

### What a real business would add
- Two-person approval above a dollar threshold.
- Spending caps per payment, per day and per vendor, plus an allow-list of payees. Agents never get to edit bank details.
- Customer messages as drafts that a person sends, with personal data redacted before it reaches the model and opt-outs respected.
- Discount tiers set by the owner, not the model.
- A tamper-evident, off-box audit log, with alerts on unusual actions.
- Staging data, backups before write runs, and a kill switch.
- Prompt-injection defense: ticket and email text is data, never instructions.

### Limits that keep token use in check
- **One budget for the whole team run**, shared by every delegated agent: 30 model requests, 40 tool calls and 200,000 tokens. Hitting it stops the run.
- **4,000 tokens at most** per model response.
- **Delegation depth is at most 2** (boss → A → B). Self-delegation and loops back up the chain are refused.
- **Small tool results**, and clipped tool output in the audit trail.
- **Capped retries:** 2 for output validation, 1 for tool errors.
- **The cheap model, `gpt-6-luna`**, for every agent. Each Problem 9 run used about 10–18k input tokens.

---

## 7. Problem 9 run: results

The database was reset to the original values (checking **$3,400**). Claude started each ticket through the board's API, and Regi watched on the board and approved the check.

| Ticket | Run | Agents | Result | Cash |
|---|---|---|---|---|
| 102 rent | `007ea4d28c8a` | boss → accounting | Accounting queued $2,400 rent and **Regi approved it** on the board (payment #1 to Elm City Properties). | −$2,400 → $1,000 |
| 101 tee | `8ec017993f89` | boss → inventory, boss → customer_service | Size S is out of stock. Alternatives (M/L/XL) or a backorder were documented, and outreach and any reorder are left to a person. Invoice 501 was not paid. | $0 |
| 103 hoodies | `34042387cb57` | boss → inventory → accounting, boss → customer_service (its attempt to loop back to boss was refused) | 8 of 20 on hand at $58 list / $22 cost. No discount without a person's OK; customer service drafted a reply. | $0 |

**Ending checking balance:** **$1,000**, which matches `cash_accounts`. The math is $3,400 − $2,400 = $1,000. Invoice 501 ($840) is still open.

**Files:**
- `output/desk_tickets.html`: Expected vs Actual for each ticket, plus the itemized Cash tab
- `output/resolved_tickets.json`
- `output/resolved_board.html`: board screenshots
- `output/audit_trail.json`: every step

**Fix made during Problem 9:** in the first attempt, accounting didn't queue rent. The role text Claude wrote in `prompts/accounting.md` still said payments needed a named approver, which predated the board's approval queue. That sentence was updated to "call `record_payment`; it's queued for a person". Regi's shop rules were not changed. The database was reset before the final runs above, and the earlier attempts stay in the audit trail.
