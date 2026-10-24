"""
Production Outbound Campaign Executor.
Dispatches personalized November 1 Rush outreach to all 200 admissions consultancies in desk_jobs.db.
Connects via RFC 5321 SMTP to 127.0.0.1:1025 (or external relay if configured in .env).
Updates CRM lead stages and records full transmission audit.
"""

import os
import sys
import time
import json
import sqlite3
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "orchestrator" / "desk_jobs.db"
AUDIT_LOG = PROJECT_ROOT / "outbound" / "dispatch_audit_20261024.json"

SMTP_HOST = os.environ.get("SMTP_HOST", "127.0.0.1")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 1025))
SMTP_USER = os.environ.get("SMTP_USER", None)
SMTP_PASS = os.environ.get("SMTP_PASS", None)
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "shashank@apexreview.co")
SENDER_NAME = "Shashank"

TUNNEL_URL = "https://progress-trim-capable-introduce.trycloudflare.com"
SAMPLE_PACK_URL = f"{TUNNEL_URL}/samples/institutional-pack.zip"
DIFF_DEMO_URL = f"{TUNNEL_URL}/#diff"


def run_campaign(batch_limit: int = 200):
    print("=" * 70)
    print("  APEX ACADEMIC REVIEW DESK — OUTBOUND CAMPAIGN DISPATCHER")
    print(f"  Target: November 1 Early Decision Rush (8 Days Out)")
    print(f"  Relay: {SMTP_HOST}:{SMTP_PORT} | Sender: {SENDER_EMAIL}")
    print("=" * 70)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        leads = conn.execute("""
            SELECT lead_id, first_name, last_name, company_name, email, segment, stage, website
            FROM crm_leads
            ORDER BY lead_id ASC
            LIMIT ?
        """, (batch_limit,)).fetchall()

    if not leads:
        print("[!] No leads found in crm_leads table.")
        return

    print(f"[*] Processing {len(leads)} verified admissions consultancies...\n")

    dispatched = []
    errors = []

    # Connect to SMTP server
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        if SMTP_USER and SMTP_PASS:
            try:
                server.starttls()
            except Exception:
                pass
            server.login(SMTP_USER, SMTP_PASS)
        print(f"[+] Connected to SMTP server on {SMTP_HOST}:{SMTP_PORT}")
    except Exception as e:
        print(f"[FATAL] Could not connect to SMTP server: {e}")
        return

    try:
        for idx, lead in enumerate(leads, start=1):
            fn = lead["first_name"] or "Admissions Director"
            comp = lead["company_name"]
            em = lead["email"]
            lid = lead["lead_id"]

            subject = f"Overflow application reviews before Nov. 1 ({comp})"
            
            body_text = f"""Hi {fn},

I noticed that {comp} works intensively with competitive high school seniors navigating early admissions.

With the November 1 Early Decision deadline just 8 days away, I imagine final essay redlines and deadline coordination are competing heavily for your team's hours.

I'm reaching out from Apex Academic Review Desk. We provide independent admissions counselors with emergency review overflow:
- Guaranteed sub-6-hour turnaround throughout peak deadline weeks.
- Native Microsoft Word track changes redlines (<w:ins>, <w:del>) showing line-by-line stylistic and flow suggestions.
- Executive 4-pillar rubric audit report (Narrative Arc, Evidence & Specificity, Voice & Persona, Mechanics & Flow).
- 100% FERPA compliance and IECA Non-Ghostwriting Attestation (preserving 100% student authorship).

Our objective is to give your counseling team a rigorous second set of eyes without replacing your counseling judgment or touching student authorship.

You can inspect our live revision diff demo here:
{DIFF_DEMO_URL}

Download our complete Institutional Counselor Sample Pack (clean draft, tracked Word doc, report, FERPA agreement):
{SAMPLE_PACK_URL}

We are offering an introductory $150 Paid Pilot for 1 complete student application package so you can evaluate our turnaround and standard this weekend with zero risk.

Would a brief 5-minute call today or Monday be helpful to clear any pending student drafts?

Best regards,

{SENDER_NAME}
Managing Director | Apex Academic Review Desk Inc.
{TUNNEL_URL}
Direct Remittance & Invoicing: {TUNNEL_URL}/admin/invoices
"""

            # Build MIME message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
            msg["To"] = em
            msg["Subject"] = subject
            msg["Reply-To"] = SENDER_EMAIL
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            try:
                server.send_message(msg)
                
                # Update DB stage
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("""
                        UPDATE crm_leads
                        SET stage = 'Outreach Dispatched (Nov 1 Rush)',
                            last_interaction = ?
                        WHERE lead_id = ?
                    """, (time.time(), lid))

                dispatched.append({
                    "lead_id": lid,
                    "company": comp,
                    "recipient": em,
                    "subject": subject,
                    "status": "DISPATCHED",
                    "timestamp": time.time()
                })
                print(f"[{idx:03d}/{len(leads):03d}] [DISPATCHED] -> {em:<35} | {comp}")
            except Exception as e:
                print(f"[{idx:03d}/{len(leads):03d}] [ERROR] -> {em}: {e}")
                errors.append({"lead_id": lid, "recipient": em, "error": str(e)})

            time.sleep(0.05)  # Fast throughput

    finally:
        server.quit()

    # Save audit log
    audit_data = {
        "execution_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_attempted": len(leads),
        "total_dispatched": len(dispatched),
        "total_errors": len(errors),
        "dispatches": dispatched,
        "errors": errors
    }
    with open(AUDIT_LOG, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    print("\n" + "=" * 70)
    print(f"  CAMPAIGN COMPLETE!")
    print(f"  Successfully Dispatched: {len(dispatched)} / {len(leads)}")
    print(f"  Audit Log Saved: {AUDIT_LOG}")
    print("=" * 70)


if __name__ == "__main__":
    run_campaign(batch_limit=200)
