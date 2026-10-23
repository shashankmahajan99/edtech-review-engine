"""
Autonomous Outbound Email Dispatcher.
Dispatches personalized Paid Pilot outreach to verified admissions directors.
Supports both live SMTP (via .env) and Staging Dry-Run mode.
"""

import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List

from .leads_prospector import LeadManager

DISPATCH_LOG = Path(__file__).resolve().parent / "dispatch_log.txt"


class EmailDispatcher:
    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.smtp_user = os.environ.get("SMTP_USER")
        self.smtp_pass = os.environ.get("SMTP_PASS")
        self.sender_email = os.environ.get("SENDER_EMAIL", "admissions-desk@apexreview.co")
        self.lead_mgr = LeadManager()

    def dispatch_all(self, dry_run: bool = True) -> List[Dict]:
        """
        Iterates through all leads in CRM with status 'Ready' and dispatches outreach.
        In dry-run mode, logs exact transmission payload and updates CRM state.
        """
        campaign = self.lead_mgr.generate_personalized_campaign()
        results = []

        print("=" * 65)
        print(f"  LAUNCHING OUTBOUND DISPATCHER (Mode: {'DRY-RUN / STAGING' if dry_run else 'LIVE SMTP'})")
        print("=" * 65)

        for item in campaign:
            recipient = item["to_email"]
            company = item["company"]
            subject = item["subject"]
            body = item["body"]

            if dry_run or not self.smtp_host:
                print(f"[STAGING DISPATCH] -> {recipient} ({company})")
                print(f"                   Subject: {subject}")
                # Log dispatch
                with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DISPATCHED TO: {recipient} | {company}\n")
                    f.write(f"SUBJECT: {subject}\n\n{body}\n")
                    f.write("-" * 65 + "\n")
                
                results.append({"email": recipient, "status": "Dispatched (Staging)", "timestamp": time.time()})
            else:
                try:
                    msg = MIMEMultipart()
                    msg["From"] = self.sender_email
                    msg["To"] = recipient
                    msg["Subject"] = subject
                    msg.attach(MIMEText(body, "plain"))

                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_pass)
                        server.send_message(msg)

                    print(f"[LIVE DISPATCH SUCCESS] -> {recipient}")
                    results.append({"email": recipient, "status": "Sent (Live SMTP)", "timestamp": time.time()})
                except Exception as e:
                    print(f"[!] Dispatch failed for {recipient}: {e}")
                    results.append({"email": recipient, "status": f"Failed: {e}", "timestamp": time.time()})

            time.sleep(0.5)

        print(f"\n[OK] Completed campaign dispatch across {len(results)} enterprise leads.")
        return results


if __name__ == "__main__":
    dispatcher = EmailDispatcher()
    dispatcher.dispatch_all(dry_run=True)
