"""
Prospecting & Outreach Dispatch Engine.
Manages leads, tracks outreach stages, and generates personalized outreach emails.
"""

import csv
from pathlib import Path
from typing import List, Dict
from .cold_outreach_templates import IEC_PAID_PILOT_SEQUENCE

DEFAULT_LEADS = [
    {
        "first_name": "David",
        "last_name": "Kim",
        "company_name": "Apex Ivy Consulting",
        "email": "david@apexivyconsulting.com",
        "segment": "IEC_Admissions",
        "status": "Ready",
        "website": "https://apexivyconsulting.com"
    },
    {
        "first_name": "Sarah",
        "last_name": "Jenkins",
        "company_name": "NorthStar College Counseling",
        "email": "sarah@northstaradmit.org",
        "segment": "IEC_Admissions",
        "status": "Ready",
        "website": "https://northstaradmit.org"
    },
    {
        "first_name": "Vikram",
        "last_name": "Sharma",
        "company_name": "GlobalEd Overseas Consultants",
        "email": "vikram@globaledoverseas.in",
        "segment": "Study_Abroad",
        "status": "Ready",
        "website": "https://globaledoverseas.in"
    },
    {
        "first_name": "Elena",
        "last_name": "Rostova",
        "company_name": "Oxbridge & Ivy Admissions",
        "email": "elena@oxbridgeivy.co.uk",
        "segment": "IEC_Admissions",
        "status": "Ready",
        "website": "https://oxbridgeivy.co.uk"
    },
    {
        "first_name": "Rajesh",
        "last_name": "Menon",
        "company_name": "EdPulse Abroad Admissions",
        "email": "contact@edpulseabroad.com",
        "segment": "Study_Abroad",
        "status": "Ready",
        "website": "https://edpulseabroad.com"
    }
]


class LeadManager:
    def __init__(self, storage_path: Path = None):
        if storage_path is None:
            self.storage_path = Path(__file__).resolve().parent / "leads_crm.csv"
        else:
            self.storage_path = Path(storage_path)
            
        if not self.storage_path.exists():
            self._initialize_storage(DEFAULT_LEADS)

    def _initialize_storage(self, leads: List[Dict]):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        keys = ["first_name", "last_name", "company_name", "email", "segment", "status", "website"]
        with open(self.storage_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(leads)

    def load_leads(self) -> List[Dict]:
        with open(self.storage_path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def generate_personalized_campaign(self, sender_name: str = "Shashank", upload_link: str = "https://compaq-homepage-fixes-thrown.trycloudflare.com") -> List[Dict]:
        """Generates ready-to-dispatch outreach payloads for all active leads."""
        leads = self.load_leads()
        dispatches = []

        for lead in leads:
            tmpl = IEC_PAID_PILOT_SEQUENCE["step_1_day_1"]
            subject = tmpl["subject"].format(company_name=lead["company_name"])
            body = tmpl["body"].format(
                first_name=lead["first_name"],
                company_name=lead["company_name"],
                upload_link=upload_link,
                sender_name=sender_name,
                phone_or_whatsapp="+91 98765 43210"
            )

            dispatches.append({
                "to_email": lead["email"],
                "company": lead["company_name"],
                "subject": subject,
                "body": body
            })

        return dispatches


if __name__ == "__main__":
    mgr = LeadManager()
    campaign = mgr.generate_personalized_campaign()
    print(f"[*] Generated {len(campaign)} personalized outreach dispatches ready for execution.")
    print("-" * 60)
    print("SAMPLE EMAIL DISPATCH #1:")
    print(f"TO: {campaign[0]['to_email']}")
    print(f"SUBJECT: {campaign[0]['subject']}")
    print("\n" + campaign[0]['body'])
    print("-" * 60)
