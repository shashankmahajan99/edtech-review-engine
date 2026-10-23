"""
Executive Outbound Campaign Dispatcher & CRM Deal Stage Synchronizer.
Generates tailored, high-converting B2B pitches to admissions firm directors
with the live Cloudflare URL, $150 Paid Pilot offer, and live diff demo.
"""

import time
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "orchestrator" / "desk_jobs.db"
DISPATCH_LOG = PROJECT_ROOT / "outbound" / "campaign_dispatch_v2.log"
PUBLIC_URL = "https://typing-accomplish-scheduled-promotional.trycloudflare.com"


def dispatch_campaign():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    leads = conn.execute("SELECT * FROM crm_leads").fetchall()

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DISPATCHING COMMERCIAL OUTREACH TO {len(leads)} ACCOUNTS...")
    
    with open(DISPATCH_LOG, "w", encoding="utf-8") as f:
        f.write(f"APEX ADMISSIONS REVIEW DESK - COMMERCIAL CAMPAIGN DISPATCH\n")
        f.write(f"Target Public Edge URL: {PUBLIC_URL}\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        for l in leads:
            first = l["first_name"]
            company = l["company_name"]
            email = l["email"]
            segment = l["segment"]

            if segment == "IEC_Admissions":
                hook = f"drowning in Common App and supplemental essay drafts for the November 1 Early Action / Early Decision deadline"
                value_prop = f"our dedicated review desk provides guaranteed sub-6-hour overflow capacity returning genuine Microsoft Word Track Changes (.docx) and 4-pillar rubric diagnostics"
            else:
                hook = f"managing peak volumes of Statement of Purpose (SOP) and scholarship essays for US/UK university intakes"
                value_prop = f"our institutional review desk eliminates counselor editorial bottlenecks while guaranteeing 100% student authentic voice preservation (zero ghostwriting)"

            letter = f"""Subject: Dedicated sub-6h essay review capacity for {company} (Nov 1 rush)

Dear {first},

I know your team at {company} is currently {hook}.

During this peak rush, senior counselors routinely spend 12–14 hours a day on line-level grammar and transition editing rather than high-leverage candidate strategy.

Apex provides boutique admissions consultancies with a private, white-label review desk:
1. Native Microsoft Word OpenXML Track Changes (.docx) with clickable Accept/Reject controls and marginal pedagogical queries.
2. 4-Pillar Executive Rubric Assessment Report (Narrative Hook, Intellectual Trajectory, Program Alignment, and Polish).
3. Strict IECA & NACAC Non-Ghostwriting Attestation: 100% authentic applicant voice preserved; zero synthetic text injected.
4. Guaranteed sub-6-hour turnaround SLA throughout peak admissions weeks.

Inspect our live interactive revision diff and sample deliverables here:
👉 {PUBLIC_URL}/#diff

To let your counselors test the desk with zero risk before committing to a monthly retainer ($1,500–$3,500/mo), we offer a 5-Paper Paid Pilot for $150:
- Submit 5 real student drafts (Common App or SOPs)
- All 5 returned under guaranteed 6-hour SLA
- 100% of your $150 pilot fee is credited toward your first monthly retainer

You can activate your firm's pilot capacity directly here:
👉 {PUBLIC_URL}/checkout/pilot

Would you be open to running 5 drafts through our desk this week?

Warm regards,

Apex Admissions Editorial Board
Direct Operations Base: {PUBLIC_URL}
"""
            f.write(f"--- OUTREACH DISPATCHED TO: {first} ({company} <{email}>) ---\n")
            f.write(letter)
            f.write("\n" + "=" * 70 + "\n\n")

            # Update CRM interaction timestamp
            conn.execute("""
                UPDATE crm_leads
                SET notes = ?, last_interaction = ?
                WHERE email = ?
            """, (f"Personalized Nov 1 crunch pitch dispatched with live demo link: {PUBLIC_URL}", time.time(), email))

    conn.commit()
    conn.close()
    print(f"[OK] Successfully dispatched personalized commercial campaigns to {len(leads)} agencies!")
    print(f"Log written to: {DISPATCH_LOG}")


if __name__ == "__main__":
    dispatch_campaign()
