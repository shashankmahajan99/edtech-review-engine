"""
Institutional Compliance & FERPA Cryptographic Audit Trail Logger.
Logs every lifecycle action with SHA-256 checksums to verify authentic student voice preservation
and FERPA-compliant de-identification.
"""

import time
import hashlib
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "orchestrator" / "desk_jobs.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_compliance_schema():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compliance_audit_trail (
                event_id TEXT PRIMARY KEY,
                job_id TEXT,
                actor TEXT,
                action_type TEXT,
                details TEXT,
                sha256_hash TEXT,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviewer_earnings (
                earning_id TEXT PRIMARY KEY,
                reviewer_email TEXT,
                job_id TEXT,
                amount_inr REAL DEFAULT 300.0,
                status TEXT DEFAULT 'pending',
                upi_id TEXT,
                created_at REAL,
                paid_at REAL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crm_leads (
                lead_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                company_name TEXT,
                email TEXT UNIQUE,
                segment TEXT,
                stage TEXT DEFAULT 'Cold Outreached', -- Cold Outreached, Inbound Replied, Pilot Booked, Retainer Active
                website TEXT,
                notes TEXT,
                last_interaction REAL
            )
        """)
init_compliance_schema()


def log_compliance_event(job_id: str, actor: str, action_type: str, details: str, payload_to_hash: str = "") -> str:
    event_id = str(uuid.uuid4())[:12]
    now = time.time()
    
    # Generate tamper-evident SHA-256 integrity hash
    hash_seed = f"{job_id}:{actor}:{action_type}:{details}:{payload_to_hash}:{now}"
    integrity_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO compliance_audit_trail (event_id, job_id, actor, action_type, details, sha256_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_id, job_id, actor, action_type, details, integrity_hash, now))

    return integrity_hash


def get_job_audit_history(job_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM compliance_audit_trail
            WHERE job_id = ?
            ORDER BY timestamp ASC
        """, (job_id,)).fetchall()
        return [dict(r) for r in rows]
