import sqlite3

conn = sqlite3.connect(r"C:\Users\shashank\edtech-review-engine\orchestrator\desk_jobs.db")
conn.row_factory = sqlite3.Row
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

stages = [dict(r) for r in conn.execute("SELECT stage, count(lead_id) as cnt FROM crm_leads GROUP BY stage").fetchall()]
print("Lead stages:", stages)

leads = [dict(r) for r in conn.execute("SELECT first_name, last_name, company_name, email, stage FROM crm_leads LIMIT 5").fetchall()]
print("Sample Leads:", leads)
