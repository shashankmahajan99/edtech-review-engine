import urllib.request, json, sqlite3, time

# 1. Local Healthcheck
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5) as res:
        health_data = json.loads(res.read().decode())
        print('[HEALTH] Local API:', health_data)
except Exception as e:
    print('[ERR] Local API error:', e)

# 2. Database Stats
conn = sqlite3.connect(r'C:\Users\shashank\edtech-review-engine\orchestrator\desk_jobs.db')
c = conn.cursor()
c.execute("SELECT COUNT(*), SUM(amount_usd) FROM transactions WHERE status = 'completed'")
tx_count, rev_usd = c.fetchone()
print(f'[METRICS] Total Revenue: ${rev_usd:,.2f} USD across {tx_count} transactions')

c.execute("SELECT stage, count(*) FROM crm_leads GROUP BY stage")
stages = dict(c.fetchall())
print('[METRICS] CRM Stages:', stages)

c.execute("SELECT status, count(*) FROM submissions GROUP BY status")
sub_stats = dict(c.fetchall())
print('[METRICS] Submissions:', sub_stats)

c.execute("SELECT count(*), coalesce(sum(amount_inr), 0) FROM reviewer_earnings WHERE status = 'pending'")
pending_payouts = c.fetchone()
print(f'[METRICS] Reviewer Pending Payouts: {pending_payouts[0]} requests (INR {pending_payouts[1]:,.2f})')

conn.close()

# 3. Tunnel Verification
tunnel_url = 'https://typing-accomplish-scheduled-promotional.trycloudflare.com'
try:
    with urllib.request.urlopen(tunnel_url + '/api/health', timeout=8) as res:
        print('[HEALTH] Global Cloudflare Edge:', res.status)
except Exception as e:
    print('[ERR] Cloudflare Edge error:', e)
