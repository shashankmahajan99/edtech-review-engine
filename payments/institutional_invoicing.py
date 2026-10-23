"""
Institutional Invoicing & Retainer Billing Engine for Apex Academic Review Desk Inc.
Generates B2B institutional invoices with ACH/Wire, Stripe, and UPI payment instructions,
tracking billing lifecycles from Issuance to Settlement.
"""

import os
import time
import uuid
import sqlite3
from typing import Dict, List, Any, Optional
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "orchestrator" / "desk_jobs.db"


def init_invoicing_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS institutional_invoices (
                invoice_id TEXT PRIMARY KEY,
                client_company TEXT,
                client_email TEXT,
                billing_contact TEXT,
                package_name TEXT,
                amount_usd REAL,
                status TEXT DEFAULT 'issued', -- 'issued', 'paid', 'cancelled'
                due_date REAL,
                payment_method TEXT DEFAULT 'ACH_WIRE_STRIPE',
                pdf_link TEXT,
                created_at REAL,
                settled_at REAL DEFAULT 0
            )
        """)


def create_invoice(client_company: str, client_email: str, billing_contact: str, package_name: str, amount_usd: float) -> Dict[str, Any]:
    init_invoicing_db()
    invoice_id = f"INV-APX-{time.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    now = time.time()
    due = now + (86400 * 7) # Net 7 terms

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO institutional_invoices (
                invoice_id, client_company, client_email, billing_contact,
                package_name, amount_usd, status, due_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'issued', ?, ?)
        """, (invoice_id, client_company, client_email, billing_contact, package_name, amount_usd, due, now))

    return {
        "invoice_id": invoice_id,
        "client_company": client_company,
        "amount_usd": amount_usd,
        "due_date": due,
        "status": "issued"
    }


def get_all_invoices(limit: int = 25) -> List[Dict[str, Any]]:
    init_invoicing_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM institutional_invoices ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_invoice_by_id(invoice_id: str) -> Optional[Dict[str, Any]]:
    init_invoicing_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM institutional_invoices WHERE invoice_id = ?", (invoice_id,)).fetchone()
        return dict(row) if row else None


init_invoicing_db()
