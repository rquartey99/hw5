# Campus Customs MCP Server

A FastMCP server that gives the Campus Customs agent team (boss, inventory, accounting, facilities, customer service) the tools it needs to work the shop's open tickets: orders, rent and discount requests.

## Database

It uses **`../data/campus_customs_new.db`**, the working copy. The original `data/campus_customs.db` is never used, and the server refuses to start if pointed at it. The shop's "today" comes from the `desk` table. Read tools open the file read-only. Write tools check every change against the database and change nothing if a check fails.

## Tools

| Tool | What it does | Tables |
|---|---|---|
| `list_open_tickets()` | Every ticket that isn't closed, oldest first. | tickets |
| `get_ticket(ticket_id)` | One ticket with all its fields. | tickets |
| `update_ticket(ticket_id, status, note)` | **Write.** Set status (`open`, `in_progress`, `closed`) and append a dated note. | tickets |
| `check_order_fulfillment(ticket_id)` | Can an order ticket ship from stock? Shows its linked restock invoice and vendor. | tickets, inventory, invoices, vendors |
| `check_stock(sku, size?)` | Stock on hand and aisle for a sku. | inventory |
| `fulfill_order(ticket_id)` | **Write.** Ship an open customer order from stock and close it. Refuses if stock is short. | inventory, tickets |
| `list_vendors()` | Vendors, specialties and lead times. | vendors |
| `quote_bulk_discount(sku, size, qty, discount_pct)` | Price a bulk order at a discount: profit, cost floor and stock shortfall. | pricing, inventory |
| `get_cash_position()` | Cash against unpaid rent and open invoices. | cash_accounts, leases, invoices, vendors, payments |
| `get_lease(lease_id)` | Rent, landlord, due date and whether it's paid. | leases, payments |
| `record_payment(kind, ref_id, amount, account, approved_by)` | **Write.** Pay an open invoice or the current rent. The amount must match exactly and a named approver is required. | payments, cash_accounts, invoices |
| `add_desk_note(note)` | **Write.** Add a dated handoff note to the desk. | desk |

## Run

From `hw5/`, after setting up the shared venv (see the main README):

```bash
.venv/bin/python mcp_server/server.py          # stdio
.venv/bin/python mcp_server/server.py --http   # http://127.0.0.1:8001/mcp
```

The backend starts its own copy of this server over stdio for every team run, and Claude Code connects to it through `hw5/.mcp.json`.
