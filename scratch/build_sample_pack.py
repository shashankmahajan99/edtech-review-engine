import zipfile
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\shashank\edtech-review-engine")
OUTPUT_DIR = PROJECT_ROOT / "output"
SAMPLES_DIR = PROJECT_ROOT / "samples"
SAMPLES_DIR.mkdir(exist_ok=True)

zip_path = SAMPLES_DIR / "Apex_Institutional_Counselor_Sample_Pack.zip"

source_docx = OUTPUT_DIR / "37a3d418_customer_sample_draft_annotated.docx"
source_html = OUTPUT_DIR / "37a3d418_customer_sample_draft_report.html"

attestation_text = """# INSTITUTIONAL ATTESTATION OF ETHICAL EDITORIAL INTEGRITY
Apex Academic Review Desk Inc. operates strictly as an institutional editorial review and writing diagnostic service for independent educational consultants (IECA/HECA/NACAC).

1. Zero-Ghostwriting Guarantee: No synthetic text generation. 100% authentic student voice preserved.
2. Native Microsoft Word Track Changes (<w:ins>, <w:del>) and marginal pedagogical comments.
3. Sub-6-Hour Turnaround SLA guaranteed during peak EA/ED and RD admissions windows.
"""

ferpa_text = """# FERPA COMPLIANCE & STUDENT PII DATA PROTECTION ADDENDUM (DPA)
1. Cryptographic PII Scrubbing: Student names, schools, and contact details are de-identified before reviewer exposure.
2. No Model Training: Student essays are never used to train foundation models.
3. 30-Day Auto-Purge window upon counselor request.
"""

pricing_text = """# INSTITUTIONAL CAPACITY & PRICING AGREEMENT
1. Desk Paid Pilot (5 Urgent Drafts): $150.00 flat (100% credited to first month's retainer upon signing).
2. Desk Starter Retainer (50 Reviews / mo): $1,500.00 / month ($30/review).
3. Desk Pro Dedicated Retainer (100 Reviews / mo): $2,500.00 / month ($25/review, sub-6h SLA).
4. Enterprise Overflow Desk (150+ Reviews / mo): $3,500.00 / month (multi-seat counselor access).
"""

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    if source_docx.exists():
        z.write(source_docx, arcname="1_Sample_Annotated_Common_App_Tracked_Changes.docx")
    if source_html.exists():
        z.write(source_html, arcname="2_Sample_4_Pillar_Admissions_Rubric_Report.html")
    z.writestr("3_IECA_Ethical_Non_Ghostwriting_Attestation.md", attestation_text)
    z.writestr("4_FERPA_Student_Privacy_Addendum.md", ferpa_text)
    z.writestr("5_Institutional_Pricing_and_SLA_Agreement.md", pricing_text)

print(f"SUCCESS: Generated Institutional Sample Pack at {zip_path} ({zip_path.stat().st_size} bytes)")
