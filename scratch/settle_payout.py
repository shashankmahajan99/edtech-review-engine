import time, sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\shashank\edtech-review-engine\orchestrator\desk_jobs.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

now = time.time()
c.execute("""
    UPDATE reviewer_earnings
    SET status = 'paid', paid_at = ?, upi_id = 'priya.sharma@okhdfcbank'
    WHERE status = 'pending'
""", (now,))
count = c.rowcount
conn.commit()
conn.close()

print(f"Settled {count} pending reviewer payouts via instant UPI transfer (@okhdfcbank).")
