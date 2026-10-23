"""
Continuous Background Poller & Autonomous Task Dispatcher.
Checks token replenishment, unreviewed submissions, reviewer queues, and CRM pipeline.
"""

import time
import sys
import json
import sqlite3
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.token_manager import TokenManager
from outbound.leads_prospector import LeadManager

DB_PATH = PROJECT_ROOT / "orchestrator" / "desk_jobs.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HEARTBEAT_FILE = OUTPUT_DIR / "daemon_heartbeat.json"


def poll_cycle():
    tm = TokenManager()
    lead_mgr = LeadManager()
    
    # 1. Check token refreshes
    status = tm.check_refresh_status()
    refreshed = status.get("refreshed_models", [])
    if refreshed:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [✓] High-capacity models refreshed and back online: {refreshed}", flush=True)
    
    # 2. Check database submission queue
    qa_pending = 0
    approved_count = 0
    pending_payouts_inr = 0
    crm_replies = 0

    if DB_PATH.exists():
        try:
            with sqlite3.connect(DB_PATH) as conn:
                qa_pending = conn.execute("SELECT COUNT(*) FROM submissions WHERE status = 'in_qa'").fetchone()[0]
                approved_count = conn.execute("SELECT COUNT(*) FROM submissions WHERE status = 'approved'").fetchone()[0]
                pending_payouts_inr = conn.execute("SELECT COALESCE(SUM(amount_inr), 0) FROM reviewer_earnings WHERE status = 'pending'").fetchone()[0]
                crm_replies = conn.execute("SELECT COUNT(*) FROM crm_leads WHERE stage = 'Inbound Replied'").fetchone()[0]
        except Exception as e:
            print(f"[!] Warning DB read: {e}", flush=True)

    # 3. Log heartbeat state
    heartbeat_data = {
        "timestamp": time.time(),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "heavy_thinker": tm.get_optimal_model("heavy_thinking"),
        "worker_model": tm.get_optimal_model("execution"),
        "qa_queue_pending": qa_pending,
        "approved_certified": approved_count,
        "pending_payouts_inr": pending_payouts_inr,
        "inbound_crm_replies": crm_replies,
        "status": "HEALTHY_OPERATIONAL"
    }

    try:
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(heartbeat_data, f, indent=2)
    except Exception:
        pass

    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [HEARTBEAT] Engine Online | Thinker: {heartbeat_data['heavy_thinker']} | "
        f"Queue: {qa_pending} in QA, {approved_count} certified | Payouts: INR {pending_payouts_inr:,.0f} | CRM Replies: {crm_replies}",
        flush=True
    )

    return heartbeat_data


def run_poller_daemon(interval_seconds: int = 60):
    print("=" * 65)
    print("  AUTONOMOUS ORCHESTRATION POLLER DAEMON ACTIVE (V3.2)")
    print("=" * 65)
    print(f"Polling cycle interval: {interval_seconds}s\n", flush=True)
    
    while True:
        try:
            poll_cycle()
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nPoller daemon stopped gracefully.")
            break
        except Exception as e:
            print(f"[!] Error in poller cycle: {e}", flush=True)
            time.sleep(10)


if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_poller_daemon(interval)
