import sqlite3
from pathlib import Path

db_path = Path(r"C:\Users\shashank\edtech-review-engine\orchestrator\desk_jobs.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Wipe fake transactions
cur.execute("DELETE FROM transactions")
# Reset leads to uncontacted real status
cur.execute("UPDATE crm_leads SET stage = 'Cold (Uncontacted)', notes = 'Awaiting real email credentials to dispatch'")
# Reset fake reviewer payouts
cur.execute("DELETE FROM reviewer_earnings")
cur.execute("UPDATE reviewers SET completed_reviews = 0")

conn.commit()

cur.execute("SELECT count(*), coalesce(sum(amount_usd), 0) FROM transactions")
tx_res = cur.fetchone()
cur.execute("SELECT count(*) FROM crm_leads")
lead_count = cur.fetchone()[0]

print(f"DATABASE RESET TO HONEST REALITY:")
print(f"Real Revenue: ${tx_res[1]:.2f} across {tx_res[0]} transactions")
print(f"Real Leads: {lead_count} uncontacted target consultancies")
conn.close()
