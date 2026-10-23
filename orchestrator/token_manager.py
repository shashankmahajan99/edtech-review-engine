"""
Multi-Model Token Manager & Adaptive Rate-Limit Poller.
Orchestrates high-reasoning thinkers (Astra / GPT-6 / Argon) vs fast execution workers (Flash / Sonnet),
monitoring quota exhaustion and auto-routing tasks with scheduled polling wakeups.
"""

import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parent / "orchestrator.db"


class TokenManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_status (
                    model_slug TEXT PRIMARY KEY,
                    tier TEXT,
                    is_active INTEGER DEFAULT 1,
                    exhausted_at REAL DEFAULT 0,
                    cooldown_seconds INTEGER DEFAULT 3600,
                    tokens_used_today INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0
                )
            """)
            # Seed default model routing tiers
            default_models = [
                ("gpt-6.1-astra", "tier_1_thinker", 1, 0, 3600),
                ("gemini-4-argon", "tier_1_thinker", 1, 0, 1800),
                ("gemini-3.8-flash", "tier_2_worker", 1, 0, 600),
                ("claude-sonnet-5-5", "tier_2_worker", 1, 0, 900),
                ("gpt-oss-120b", "tier_2_worker", 1, 0, 300),
            ]
            for slug, tier, active, exh, cd in default_models:
                conn.execute("""
                    INSERT OR IGNORE INTO model_status (model_slug, tier, is_active, exhausted_at, cooldown_seconds)
                    VALUES (?, ?, ?, ?, ?)
                """, (slug, tier, active, exh, cd))

    def record_exhaustion(self, model_slug: str, cooldown_seconds: int = 3600):
        """Marks a model as exhausted (e.g. on HTTP 429 rate limit or token limit reached)."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE model_status
                SET is_active = 0, exhausted_at = ?, cooldown_seconds = ?, failure_count = failure_count + 1
                WHERE model_slug = ?
            """, (now, cooldown_seconds, model_slug))
        print(f"[!] MODEL EXHAUSTED: {model_slug} marked cooldown for {cooldown_seconds}s until {time.ctime(now + cooldown_seconds)}")

    def check_refresh_status(self) -> Dict[str, Any]:
        """Polls exhausted models and reactivates those whose cooldown window has expired."""
        now = time.time()
        refreshed = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT model_slug, exhausted_at, cooldown_seconds 
                FROM model_status 
                WHERE is_active = 0
            """)
            for slug, exh_at, cd in cursor.fetchall():
                if now >= (exh_at + cd):
                    conn.execute("UPDATE model_status SET is_active = 1, exhausted_at = 0 WHERE model_slug = ?", (slug,))
                    refreshed.append(slug)
        
        return {
            "refreshed_models": refreshed,
            "checked_at": now
        }

    def get_optimal_model(self, task_type: str = "execution") -> str:
        """
        Returns the highest-capability active model available for the task.
        Falls back seamlessly to tier-2 if tier-1 is exhausted.
        """
        self.check_refresh_status()
        
        target_tier = "tier_1_thinker" if task_type == "heavy_thinking" else "tier_2_worker"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT model_slug FROM model_status
                WHERE tier = ? AND is_active = 1
                ORDER BY failure_count ASC LIMIT 1
            """, (target_tier,))
            row = cursor.fetchone()
            if row:
                return row[0]
            
            # Fallback to any active model
            cursor = conn.execute("""
                SELECT model_slug FROM model_status
                WHERE is_active = 1
                ORDER BY tier DESC LIMIT 1
            """)
            fallback = cursor.fetchone()
            return fallback[0] if fallback else "gemini-3.8-flash"


if __name__ == "__main__":
    tm = TokenManager()
    print("[*] Optimal model for heavy thinking:", tm.get_optimal_model("heavy_thinking"))
    print("[*] Optimal model for routine execution:", tm.get_optimal_model("execution"))
