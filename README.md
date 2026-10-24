# Apex Academic & Admissions Review Desk

A complete, end-to-end digital business engine designed to disintermediate legacy BPO middlemen (such as Trivium Education and ThinkingStorm) and capture high-margin academic content and essay review contracts.

---

## ThinkingStorm Deliverable Pipeline (v2, offline)

The review desk runs on a deterministic engine that needs **no LLM, no network,
and zero tokens** to turn a student draft into a native Word deliverable
(`<name>_commented.docx`) with sentence-anchored comments, knowledge-base links,
and the red Times New Roman 12 pt endnote letter.

```bash
python -m engine.review.cli review draft.docx      # one file
python -m engine.review.cli batch ./inbox          # a folder
python -m engine.review.cli watch                  # hands-free inbox watcher
python -m engine.review.cli selftest               # regression fixtures
python -m unittest discover -s tests -v            # full test suite
```

Every deliverable passes a release gate (text preservation, anchor integrity,
link allow-list, comment register, AI-style proxies, endnote typography) or it is
not written at all. Full design and operations:
[`docs/THINKINGSTORM_PIPELINE.md`](docs/THINKINGSTORM_PIPELINE.md).

---

## Architecture Overview

```
edtech-review-engine/
├── engine/
│   ├── __init__.py
│   ├── prompts.py             # 4-pillar institutional grading rubrics (Academic & Admissions SOP)
│   ├── processor.py           # Core review pipeline (Generates annotated docx + HTML executive rubric)
│   └── cli.py                 # Command-line instant document processor
├── outbound/
│   ├── cold_outreach_templates.py # Battle-tested B2B cold email & LinkedIn sequences
│   ├── leads_crm.csv          # Active CRM tracking prospects, trials, and retainers
│   └── leads_prospector.py    # Automated campaign generator for 500+ consultants
├── portal/
│   └── server.py              # Modern FastAPI client-intake desk & reviewer workbench
├── samples/
│   └── sample_sop.txt         # Benchmark testing manuscript
├── output/                    # Production deliverables (annotated .docx & .html reports)
├── run_portal.py              # One-click portal launcher
└── README.md
```

---

## 1. Quick Start: Process an Essay via CLI

Run a comprehensive review on any essay or manuscript:

```bash
# Admissions SOP / Personal Statement Review
python -m engine.cli --input samples/sample_sop.txt --mode admissions --outdir output

# Standard College / Academic Essay Review
python -m engine.cli --input samples/sample_sop.txt --mode academic --outdir output
```

**Deliverables generated in `output/`:**
* `sample_sop_annotated_review.docx`: Word document with highlighted inline markup, strikethrough replacements, and marginal reviewer notes.
* `sample_sop_executive_report.html`: Institutional 4-pillar quality assessment report with scores and priority revision steps.

---

## 2. Launching the Web Portal & Intake Desk

Start the production web portal:

```bash
python run_portal.py
```

Then visit **`http://127.0.0.1:8000`** in your browser.

* **Client View:** Explore pricing tiers ($24.99 - $34.99 per essay, $1,250/mo retainer) and submit manuscripts via text or `.docx` upload.
* **Reviewer View:** Automatic generation of annotated `.docx` and Executive Rubric report with direct download links.

---

## 3. Launching the Cold Client Acquisition Blitz

To generate personalized outreach emails for admissions consultants and study abroad agency founders:

```bash
python -m outbound.leads_prospector
```

### The "Trojan Horse" Offer
Never pitch a standard sales call. Pitch the 3-hour free trial edit:
> *"Drop 1 essay draft into our portal. We will return a flawless line-edit and 4-tier rubric analysis in 3 hours for free. If you like it, we can take 30 drafts off your desk this month at $28/essay."*

### Conversion Economics
* **500 Outbound Contacts** -> **40 Free Trial Edits** -> **12 Paying B2B Retainers ($1,500/mo)** = **$18,000/month recurring revenue**.
* **Reviewer Payout:** Pay your reviewers ₹300 per review (taking 7 minutes each = ₹2,400/hr, **8x what Trivium pays**).
* **Net Margin:** You retain **80%+ gross margin** as the platform owner.
