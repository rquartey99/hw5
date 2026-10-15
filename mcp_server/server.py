"""Campus Customs operations MCP — Homework 5.

Gives the agent team tools over ../data/campus_customs_new.db (the working copy).
Read tools open the file read-only; the few write tools validate every change
against the database first. The original campus_customs.db is never touched.

Run from hw5/ (stdio):  .venv/bin/python mcp_server/server.py
Run (HTTP):             .venv/bin/python mcp_server/server.py --http
HTTP URL:                      http://127.0.0.1:8001/mcp

Set CAMPUS_CUSTOMS_DB to point at a different copy (used for offline tests).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ORIGINAL_DB = (ROOT / "data" / "campus_customs.db").resolve()
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB", ROOT / "data" / "campus_customs_new.db")).resolve()
if DB_PATH == ORIGINAL_DB:
    raise SystemExit("Refusing to use the original campus_customs.db; point at the working copy.")

mcp = FastMCP("campus-customs")


def _connect() -> sqlite3.Connection:
    """Open the working copy read-only so read tools can never change it."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_rw() -> sqlite3.Connection:
    """Open the working copy for a write tool; callers wrap changes in one transaction."""
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' comes from the desk table, not the system clock."""
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def _lease_paid(conn: sqlite3.Connection, lease_id: int, next_due: str) -> bool:
    """Rent counts as paid for its next_due once a lease payment lands within the month before it."""
    row = conn.execute(
        """
        SELECT 1 FROM payments
        WHERE kind = 'lease' AND ref_id = ? AND paid_at >= date(?, '-1 month')
        """,
        (lease_id, next_due),
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------- tickets


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket that isn't closed, oldest first, with all of its link columns."""
    with _connect() as conn:
        return [
            dict(r)
            for r in conn.execute("SELECT * FROM tickets WHERE status != 'closed' ORDER BY created_at")
        ]


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket by id with all of its fields (sku/size/qty, lease_id, invoice_id, notes)."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(row) if row else {"error": f"No ticket with id {ticket_id}."}


@mcp.tool
def update_ticket(
    ticket_id: int, status: Literal["open", "in_progress", "closed"], note: str
) -> dict:
    """Change a ticket's status and append a dated note explaining why. WRITES to tickets."""
    note = note.strip()
    if not note:
        return {"error": "A note explaining the change is required."}
    with _connect_rw() as conn:
        conn.execute("BEGIN IMMEDIATE")
        ticket = conn.execute("SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            conn.execute("ROLLBACK")
            return {"error": f"No ticket with id {ticket_id}."}
        today = _today(conn)
        notes = f"{ticket['notes'] or ''}\n[{today}] {note}".strip()
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
        conn.execute("COMMIT")
    return {"ticket_id": ticket_id, "old_status": ticket["status"], "new_status": status, "notes": notes}


# ---------------------------------------------------------------- inventory


@mcp.tool
def check_order_fulfillment(ticket_id: int) -> dict:
    """Check whether an order ticket can ship from stock, and if not, what restock is pending.

    Reads the ticket's sku/size/qty, compares it to inventory on hand, and follows
    the ticket's invoice_id to the linked vendor invoice (amount, due date, status,
    days overdue) and that vendor's lead time.
    """
    with _connect() as conn:
        today = _today(conn)
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"error": f"No ticket with id {ticket_id}."}
        if ticket["sku"] is None:
            return {"error": f"Ticket {ticket_id} is not about a product (type: {ticket['type']})."}

        stock = conn.execute(
            "SELECT name, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (ticket["sku"], ticket["size"]),
        ).fetchone()
        on_hand = stock["qty"] if stock else 0
        wanted = ticket["qty"] or 0

        restock = None
        if ticket["invoice_id"] is not None:
            row = conn.execute(
                """
                SELECT i.id, i.amount, i.due_date, i.status, i.description,
                       v.name AS vendor, v.specialty, v.lead_days,
                       CAST(julianday(?) - julianday(i.due_date) AS INTEGER) AS days_overdue
                FROM invoices i JOIN vendors v ON v.id = i.vendor_id
                WHERE i.id = ?
                """,
                (today, ticket["invoice_id"]),
            ).fetchone()
            if row:
                restock = dict(row)
                restock["days_overdue"] = max(restock["days_overdue"], 0)

    return {
        "today": today,
        "ticket_id": ticket_id,
        "requester": ticket["requester"],
        "sku": ticket["sku"],
        "size": ticket["size"],
        "product": stock["name"] if stock else None,
        "location": stock["location"] if stock else None,
        "qty_wanted": wanted,
        "qty_on_hand": on_hand,
        "can_ship_from_stock": on_hand >= wanted,
        "shortfall": max(wanted - on_hand, 0),
        "linked_restock_invoice": restock,
    }


@mcp.tool
def check_stock(sku: str, size: str | None = None) -> list[dict]:
    """Stock on hand for a sku (every size, or just one size) with product name and aisle."""
    with _connect() as conn:
        if size is None:
            rows = conn.execute("SELECT * FROM inventory WHERE sku = ? ORDER BY rowid", (sku,))
        else:
            rows = conn.execute("SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size))
        return [dict(r) for r in rows]


@mcp.tool
def fulfill_order(ticket_id: int) -> dict:
    """Ship a customer_order ticket from stock: subtract its qty from inventory and close the ticket.

    Refuses if the ticket isn't an open customer order or stock is short. WRITES to inventory and tickets.
    """
    with _connect_rw() as conn:
        conn.execute("BEGIN IMMEDIATE")
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None or ticket["type"] != "customer_order" or ticket["status"] == "closed":
            conn.execute("ROLLBACK")
            return {"error": f"Ticket {ticket_id} is not an open customer_order."}
        stock = conn.execute(
            "SELECT qty FROM inventory WHERE sku = ? AND size = ?", (ticket["sku"], ticket["size"])
        ).fetchone()
        on_hand = stock["qty"] if stock else 0
        if on_hand < ticket["qty"]:
            conn.execute("ROLLBACK")
            return {"error": f"Only {on_hand} on hand; ticket {ticket_id} needs {ticket['qty']}. Nothing changed."}
        today = _today(conn)
        conn.execute(
            "UPDATE inventory SET qty = qty - ? WHERE sku = ? AND size = ?",
            (ticket["qty"], ticket["sku"], ticket["size"]),
        )
        notes = f"{ticket['notes'] or ''}\n[{today}] Fulfilled {ticket['qty']} from stock.".strip()
        conn.execute("UPDATE tickets SET status = 'closed', notes = ? WHERE id = ?", (notes, ticket_id))
        conn.execute("COMMIT")
    return {"ticket_id": ticket_id, "shipped": ticket["qty"], "qty_left": on_hand - ticket["qty"], "status": "closed"}


@mcp.tool
def list_vendors() -> list[dict]:
    """Every vendor with its specialty and lead time in days."""
    with _connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM vendors ORDER BY id")]


# ---------------------------------------------------------------- pricing


@mcp.tool
def quote_bulk_discount(sku: str, size: str, qty: int, discount_pct: float = 0.0) -> dict:
    """Price a bulk order at a proposed discount and check it against cost and stock.

    Reads unit cost and list price from pricing and on-hand quantity from
    inventory. Returns the discounted unit price and total, profit per unit and
    overall, the deepest discount that still covers cost, and any stock shortfall.
    """
    with _connect() as conn:
        price = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
        if price is None:
            return {"error": f"No pricing for sku {sku}."}
        stock = conn.execute(
            "SELECT name, qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        all_sizes = [
            dict(r)
            for r in conn.execute("SELECT size, qty FROM inventory WHERE sku = ? ORDER BY rowid", (sku,))
        ]

    cost, list_price = price["unit_cost"], price["list_price"]
    unit_price = round(list_price * (1 - discount_pct / 100), 2)
    on_hand = stock["qty"] if stock else 0
    return {
        "sku": sku,
        "product": stock["name"] if stock else None,
        "size": size,
        "qty": qty,
        "unit_cost": cost,
        "list_price": list_price,
        "discount_pct": discount_pct,
        "unit_price": unit_price,
        "order_total": round(unit_price * qty, 2),
        "profit_per_unit": round(unit_price - cost, 2),
        "order_profit": round((unit_price - cost) * qty, 2),
        "above_cost": unit_price > cost,
        "max_discount_pct_at_cost": round((1 - cost / list_price) * 100, 1),
        "qty_on_hand": on_hand,
        "shortfall": max(qty - on_hand, 0),
        "stock_all_sizes": all_sizes,
    }


# ---------------------------------------------------------------- money


@mcp.tool
def get_cash_position() -> dict:
    """Show cash on hand against every bill the shop owes, as of the desk date.

    Reads cash account balances, leases (rent and next due date), open vendor
    invoices, and any payments already made, then reports what is overdue, what
    is due soon, and how much cash would remain if every unpaid bill were paid.
    """
    with _connect() as conn:
        today = _today(conn)
        accounts = [dict(r) for r in conn.execute("SELECT name, balance, date FROM cash_accounts")]
        rent = []
        for r in conn.execute(
            """
            SELECT id AS lease_id, space_name, landlord, monthly_rent AS amount, next_due,
                   CAST(julianday(next_due) - julianday(?) AS INTEGER) AS days_until_due
            FROM leases ORDER BY next_due
            """,
            (today,),
        ):
            row = dict(r)
            row["paid"] = _lease_paid(conn, row["lease_id"], row["next_due"])
            rent.append(row)
        invoices = [
            dict(r)
            for r in conn.execute(
                """
                SELECT i.id AS invoice_id, v.name AS vendor, i.amount, i.due_date, i.description,
                       CAST(julianday(i.due_date) - julianday(?) AS INTEGER) AS days_until_due
                FROM invoices i JOIN vendors v ON v.id = i.vendor_id
                WHERE i.status = 'open' ORDER BY i.due_date
                """,
                (today,),
            )
        ]
        payments = [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY paid_at")]

    total_cash = sum(a["balance"] for a in accounts)
    total_owed = sum(r["amount"] for r in rent if not r["paid"]) + sum(i["amount"] for i in invoices)
    return {
        "today": today,
        "accounts": accounts,
        "total_cash": total_cash,
        "rent_due": rent,
        "open_invoices": invoices,
        "payments_made": payments,
        "total_owed": total_owed,
        "cash_left_if_all_paid": total_cash - total_owed,
        "can_cover_all": total_cash >= total_owed,
    }


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """One lease with its rent, landlord, next due date, days until due, and whether it's already paid."""
    with _connect() as conn:
        today = _today(conn)
        row = conn.execute(
            """
            SELECT *, CAST(julianday(next_due) - julianday(?) AS INTEGER) AS days_until_due
            FROM leases WHERE id = ?
            """,
            (today, lease_id),
        ).fetchone()
        if row is None:
            return {"error": f"No lease with id {lease_id}."}
        lease = dict(row)
        lease["paid"] = _lease_paid(conn, lease_id, lease["next_due"])
    return lease


@mcp.tool
def record_payment(
    kind: Literal["invoice", "lease"], ref_id: int, amount: float, account: str, approved_by: str
) -> dict:
    """Pay an open vendor invoice or a lease's rent from a cash account.

    The amount must equal the invoice amount or the monthly rent exactly, the bill
    must be unpaid, the account must cover it, and approved_by must name the person
    who approved it. Inserts a payments row, lowers the account balance, and marks
    a paid invoice 'paid'. WRITES to payments, cash_accounts, invoices.
    """
    if not approved_by.strip():
        return {"error": "approved_by is required; payments need a named approver."}
    with _connect_rw() as conn:
        conn.execute("BEGIN IMMEDIATE")

        def fail(msg: str) -> dict:
            conn.execute("ROLLBACK")
            return {"error": msg + " Nothing changed."}

        today = _today(conn)
        if kind == "invoice":
            bill = conn.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if bill is None:
                return fail(f"No invoice with id {ref_id}.")
            if bill["status"] != "open":
                return fail(f"Invoice {ref_id} is {bill['status']}, not open.")
            owed = bill["amount"]
        else:
            lease = conn.execute("SELECT monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return fail(f"No lease with id {ref_id}.")
            if _lease_paid(conn, ref_id, lease["next_due"]):
                return fail(f"Rent for lease {ref_id} due {lease['next_due']} is already paid.")
            owed = lease["monthly_rent"]
        if abs(amount - owed) > 0.005:
            return fail(f"Amount {amount} doesn't match the {owed} owed.")

        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if acct is None:
            return fail(f"No cash account named {account!r}.")
        if acct["balance"] < amount:
            return fail(f"{account} has {acct['balance']}, not enough for {amount}.")

        cur = conn.execute(
            """
            INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, ref_id, amount, account, today, approved_by.strip()),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?", (amount, today, account)
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        conn.execute("COMMIT")
    return {
        "payment_id": cur.lastrowid,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "paid_at": today,
        "approved_by": approved_by.strip(),
        "new_balance": acct["balance"] - amount,
    }


# ---------------------------------------------------------------- desk


@mcp.tool
def add_desk_note(note: str) -> dict:
    """Append a dated handoff note to the shop desk so other agents and staff can see it. WRITES to desk."""
    note = note.strip()
    if not note:
        return {"error": "Note is empty."}
    with _connect_rw() as conn:
        conn.execute("BEGIN IMMEDIATE")
        desk = conn.execute("SELECT rowid, date_today, notes FROM desk LIMIT 1").fetchone()
        notes = f"{desk['notes'] or ''}\n[{desk['date_today']}] {note}".strip()
        conn.execute("UPDATE desk SET notes = ? WHERE rowid = ?", (notes, desk["rowid"]))
        conn.execute("COMMIT")
    return {"date_today": desk["date_today"], "notes": notes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Serve over HTTP instead of stdio")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8001)
    else:
        mcp.run()
