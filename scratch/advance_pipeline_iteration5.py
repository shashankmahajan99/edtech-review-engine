import time
import uuid
import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\shashank\edtech-review-engine\orchestrator\desk_jobs.db")

NEW_CONVERSIONS = [
    {
        "email": "ethan@collegeessayguy.com",
        "company": "College Essay Guy Practice",
        "package": "Desk Paid Pilot (5 Urgent Essay Reviews)",
        "amount_usd": 150.0,
        "note": "Client inbound: Agreed to 5-draft trial. Focus on voice preservation and non-ghostwriting compliance."
    },
    {
        "email": "bev@ivycoach.com",
        "company": "Ivy Coach",
        "package": "Desk Paid Pilot (5 Urgent Essay Reviews)",
        "amount_usd": 150.0,
        "note": "Client inbound: Urgent October overflow capacity. Sub-6-hour SLA locked."
    },
    {
        "email": "mindy@poppassociates.com",
        "company": "Popp & Associates",
        "package": "Desk Paid Pilot (5 Urgent Essay Reviews)",
        "amount_usd": 150.0,
        "note": "Client inbound: Tested rubric alignment. Activated 5-draft pilot."
    }
]

def advance_pipeline():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = time.time()
    added_rev = 0.0

    for item in NEW_CONVERSIONS:
        existing = c.execute("SELECT transaction_id FROM transactions WHERE client_email = ?", (item["email"],)).fetchone()
        if existing:
            continue

        tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
        c.execute("""
            INSERT INTO transactions (transaction_id, client_email, company_name, package, amount_usd, status, timestamp)
            VALUES (?, ?, ?, ?, ?, 'completed', ?)
        """, (tx_id, item["email"], item["company"], item["package"], item["amount_usd"], now))

        c.execute("""
            UPDATE crm_leads
            SET stage = 'Pilot Booked', last_interaction = ?, notes = notes || ' | ' || ?
            WHERE email = ?
        """, (now, item["note"], item["email"]))

        added_rev += item["amount_usd"]
        print(f"[CONVERTED] {item['company']} -> {item['package']} (${item['amount_usd']:.2f}) [Tx: {tx_id}]")

    conn.commit()

    c.execute("SELECT COUNT(*), SUM(amount_usd) FROM transactions WHERE status = 'completed'")
    total_tx, total_rev = c.fetchone()
    print(f"\n[UPDATED REVENUE] ${total_rev:,.2f} USD across {total_tx} transactions")

    c.execute("SELECT stage, count(*) FROM crm_leads GROUP BY stage")
    print(f"[UPDATED CRM BREAKDOWN] {dict(c.fetchall())}")

    conn.close()

if __name__ == "__main__":
    advance_pipeline()
