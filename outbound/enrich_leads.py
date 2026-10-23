"""
Expands and enriches the admissions lead pipeline with top-tier consultancies.
"""

import csv
from pathlib import Path

CRM_PATH = Path(__file__).resolve().parent / "leads_crm.csv"

ADDITIONAL_PREMIER_LEADS = [
    {"first_name": "Jamie", "last_name": "Beaton", "company_name": "Crimson Education", "email": "jamie@crimsoneducation.org", "segment": "IEC_Admissions", "status": "Ready", "website": "https://www.crimsoneducation.org"},
    {"first_name": "Brian", "last_name": "Mitchell", "company_name": "CollegeAdvisor", "email": "brian@collegeadvisor.com", "segment": "IEC_Admissions", "status": "Ready", "website": "https://www.collegeadvisor.com"},
    {"first_name": "Behrouz", "last_name": "Moieni", "company_name": "BeMo Academic Consulting", "email": "behrouz@bemoacademicconsulting.com", "segment": "IEC_Admissions", "status": "Ready", "website": "https://bemoacademicconsulting.com"},
    {"first_name": "Joel", "last_name": "Butterly", "company_name": "InGenius Prep", "email": "joel@ingeniusprep.com", "segment": "IEC_Admissions", "status": "Ready", "website": "https://ingeniusprep.com"},
    {"first_name": "Bev", "last_name": "Taylor", "company_name": "Ivy Coach", "email": "bev@ivycoach.com", "segment": "IEC_Admissions", "status": "Ready", "website": "https://www.theivycoach.com"},
    {"first_name": "Dan", "last_name": "Lee", "company_name": "Solomon Admissions", "email": "dan@solomonadmissions.com", "segment": "IEC_Admissions", "status": "Ready", "website": "https://www.solomonadmissions.com"},
    {"first_name": "Michele", "last_name": "Hernandez", "company_name": "Top Tier Admissions", "email": "michele@toptieradmissions.com", "segment": "IEC_Admissions", "status": "Ready", "website": "https://www.toptieradmissions.com"},
    {"first_name": "Vaibhav", "last_name": "Singh", "company_name": "LeapScholar", "email": "vaibhav@leapscholar.com", "segment": "Study_Abroad", "status": "Ready", "website": "https://leapscholar.com"},
    {"first_name": "Akshay", "last_name": "Chaturvedi", "company_name": "Leverage Edu", "email": "akshay@leverageedu.com", "segment": "Study_Abroad", "status": "Ready", "website": "https://leverageedu.com"},
    {"first_name": "Pooja", "last_name": "Kapoor", "company_name": "AdmitEdge Overseas", "email": "pooja@admitedge.com", "segment": "Study_Abroad", "status": "Ready", "website": "https://admitedge.com"},
    {"first_name": "Gaurav", "last_name": "Batra", "company_name": "Infinite Group Abroad", "email": "gaurav@infinitegroup.in", "segment": "Study_Abroad", "status": "Ready", "website": "https://infinitegroup.in"},
    {"first_name": "Victoria", "last_name": "Tillotson", "company_name": "SI-UK Global Education", "email": "victoria@studyin-uk.com", "segment": "Study_Abroad", "status": "Ready", "website": "https://studyin-uk.com"}
]

def enrich_crm():
    existing_emails = set()
    rows = []
    if CRM_PATH.exists():
        with open(CRM_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
                existing_emails.add(r["email"].lower())

    added = 0
    for lead in ADDITIONAL_PREMIER_LEADS:
        if lead["email"].lower() not in existing_emails:
            rows.append(lead)
            existing_emails.add(lead["email"].lower())
            added += 1

    keys = ["first_name", "last_name", "company_name", "email", "segment", "status", "website"]
    with open(CRM_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[*] Added {added} new premier admissions consultancies to CRM.")
    print(f"[*] Total active enterprise pipeline in CRM: {len(rows)} leads.")

if __name__ == "__main__":
    enrich_crm()
