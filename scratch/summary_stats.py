import sqlite3

conn = sqlite3.connect(r'C:\Users\shashank\edtech-review-engine\orchestrator\desk_jobs.db')
c = conn.cursor()
print('--- LATEST TRANSACTIONS ---')
c.execute('SELECT transaction_id, client_email, company_name, package, amount_usd, status FROM transactions ORDER BY timestamp DESC LIMIT 6')
for r in c.fetchall():
    print(r)

print('\n--- CRM PIPELINE BREAKDOWN ---')
c.execute('SELECT stage, count(*) FROM crm_leads GROUP BY stage')
for r in c.fetchall():
    print(r)

print('\n--- TOTAL CASH COLLECTED / INVOICED ---')
c.execute("SELECT sum(amount_usd), count(*) FROM transactions WHERE status = 'completed'")
total_sum, count = c.fetchone()
print(f"Total Transactions: {count}")
print(f"Total Revenue: ${total_sum:,.2f} USD")
conn.close()
