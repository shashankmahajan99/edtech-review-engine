"""
Institutional Legal, FERPA Compliance, and IECA Ethical Attestation Suite
for Apex Academic Review Desk Inc.
"""

IECA_NON_GHOSTWRITING_ATTESTATION = """# INSTITUTIONAL ATTESTATION OF ETHICAL EDITORIAL INTEGRITY
## Compliance with IECA, NACAC, and HECA Professional Standards

Apex Academic Review Desk Inc. operates strictly as an institutional editorial review and writing diagnostic service. We provide pedagogical commentary, structural analysis, and line-level stylistic guidance for admissions counselors and independent educational consultants.

### 1. Zero-Ghostwriting Guarantee
- **Authentic Student Voice:** We strictly mandate that the applicant remains the sole authentic creator of their application essays. 
- **No Synthetic Text Generation:** Our editors, reviewers, and automated engines NEVER author, ghostwrite, or substitute original student narrative with pre-written synthetic prose.
- **Pedagogical Framing:** All line edits are delivered as track changes (<w:ins>, <w:del>) and marginal comments (<w:comment>) designed to provoke student critical reflection, syntactic economy, and authentic voice refinement.

### 2. Admissions Committee Alignment
Admissions readers at Ivy League and top-tier research universities seek authentic 17-to-22-year-old voices. Over-polished, homogenized prose is actively penalized. Our 4-pillar rubric specifically protects the student's personal idiosyncrasies, vernacular, and genuine life experiences while eliminating cliché tropes.

### 3. Institutional Accountability
Every manuscript processed through our desk receives a SHA-256 cryptographic certificate verifying:
1. PII was completely scrubbed prior to human reviewer assignment.
2. Changes are non-generative, tracked OpenXML elements.
3. The review adheres to the Institutional Statement of Ethics.
"""

FERPA_DATA_PROTECTION_ADDENDUM = """# FERPA COMPLIANCE & STUDENT PII DATA PROTECTION AGREEMENT (DPA)

This Data Protection Addendum governs the processing of student education records and admissions essays in strict compliance with the Family Educational Rights and Privacy Act (FERPA) (34 CFR Part 99).

### 1. Cryptographic PII Scrubbing
Before any student draft is exposed to editorial review benches, our automated FERPA scrubber (`security/pii_scrubber.py`) extracts and tokens:
- Full Names $\to$ `[STUDENT_NAME]`
- High Schools & Academies $\to$ `[HIGH_SCHOOL]`
- Specific Home Addresses & Phone Numbers $\to$ `[CONTACT_REDACTED]`
- Common App ID Numbers $\to$ `[APPLICANT_ID]`

The PII mapping table is retained exclusively in volatile memory or local encrypted stores on the counselor's designated institutional instance.

### 2. Data Sovereignty & Anti-Training Commitment
- Student submissions are NEVER used to train commercial foundation models.
- Files and generated Word markups are retained solely for the counselor's guaranteed SLA retrieval window (30 days) and purged thereafter upon counselor request.
- No third-party data broker access is permitted under any circumstances.
"""

SERVICE_LEVEL_AGREEMENT = """# INSTITUTIONAL SERVICE LEVEL AGREEMENT (SLA)

### Guaranteed 6-Hour Turnaround
- **Early Action / Early Decision Window:** October 1 through November 15.
- **Regular Decision Window:** December 1 through January 15.
- **SLA Commitment:** Every submission entered by a retained agency is guaranteed to be returned within 6 hours of receipt.
- **Failure Remedy:** If turnaround exceeds 6 hours, 100% of the review credit is refunded, plus one complimentary priority review is granted to the institution.
"""
