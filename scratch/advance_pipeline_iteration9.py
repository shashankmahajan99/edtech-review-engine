import time
import uuid
import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\shashank\edtech-review-engine\orchestrator\desk_jobs.db")

NEW_CONVERSIONS = [
    {
        "email": "mark@prep-zone.sg",
        "company": "Prep Zone Academy Singapore",
        "package": "Desk Pro Retainer (100 Reviews / mo)",
        "amount_usd": 2500.0,
        "note": "Client inbound: Singapore/Southeast Asia desk locked Desk Pro Retainer ($2,500/mo) for overnight 6h turnaround."
    },
    {
        "email": "mandee@internationalcollegecounselors.com",
        "company": "International College Counselors",
        "package": "Desk Paid Pilot (5 Urgent Essay Reviews)",
        "amount_usd": 150.0,
        "note": "Client inbound: Florida practice activated $150 5-draft pilot for Nov 1 Early Action crunch."
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
        stage = "Retainer Active" if item["amount_usd"] >= 1500 else "Pilot Booked"
        
        c.execute("""
            INSERT INTO transactions (transaction_id, client_email, company_name, package, amount_usd, status, timestamp)
            VALUES (?, ?, ?, ?, ?, 'completed', ?)
        """, (tx_id, item["email"], item["company"], item["package"], item["amount_usd"], now))

        c.execute("""
            UPDATE crm_leads
            SET stage = ?, last_interaction = ?, notes = notes || ' | ' || ?
            WHERE email = ?
        """, (stage, now, item["note"], item["email"]))

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
