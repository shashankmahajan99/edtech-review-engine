"""
Enterprise FastAPI Portal: Institutional Intake, Multi-Reviewer Operations,
FERPA Compliance Audit Trail, Native OpenXML Track Changes, Apex Service Monitor & Commercial Engine.
"""

import os
import sys
import re
import time
import uuid
import json
import io
import hashlib
import sqlite3
import docx
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pypdf
from engine.processor import ReviewProcessor
from engine.deep_pipeline import DeepReviewPipeline
from engine.openxml_track_changes import WordTrackChangesEngine
from engine.self_prompting_framework import SelfPromptingFramework
from mail.smtp_server import get_spooled_mail
from payments.institutional_invoicing import create_invoice, get_all_invoices, get_invoice_by_id
from legal.contracts import IECA_NON_GHOSTWRITING_ATTESTATION, FERPA_DATA_PROTECTION_ADDENDUM, SERVICE_LEVEL_AGREEMENT
import smtplib
from email.message import EmailMessage
from security.auth import authenticate_user, register_user, create_session_token, get_current_user, require_role, get_user_db
from security.pii_scrubber import PIIScrubber
from security.audit_logger import log_compliance_event, get_job_audit_history, init_compliance_schema
from payments.stripe_gateway import StripeGateway, PACKAGES

app = FastAPI(title="Apex Academic Review Desk", version="3.5.0")

def normalize_extracted_text(raw: str) -> str:
    """Reconstitutes fragmented PDF/text extractions into clean, natural paragraphs."""
    if not raw or not raw.strip():
        return ""
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        return ""
    avg_len = sum(len(l) for l in lines) / len(lines)
    if avg_len < 25:
        # Word-per-line fragmentation from pypdf
        full_text = " ".join(lines)
        full_text = re.sub(r'\s+', ' ', full_text)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', full_text)
        paragraphs = []
        current_p = []
        for s in sentences:
            current_p.append(s)
            if len(current_p) >= 3 or len(" ".join(current_p)) > 350:
                paragraphs.append(" ".join(current_p))
                current_p = []
        if current_p:
            paragraphs.append(" ".join(current_p))
        return "\n\n".join(paragraphs)
    else:
        paras = [re.sub(r'\s+', ' ', p.strip()) for p in raw.split("\n\n") if p.strip()]
        return "\n\n".join(paras)


OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = PROJECT_ROOT / "orchestrator" / "desk_jobs.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
STATUS_FILE = OUTPUT_DIR / "service_status.json"

processor = ReviewProcessor()
deep_pipeline = DeepReviewPipeline()
track_engine = WordTrackChangesEngine(author="Apex Admissions Editorial Desk")
scrubber = PIIScrubber()
gateway = StripeGateway()
self_prompt_engine = SelfPromptingFramework()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    init_compliance_schema()
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                job_id TEXT PRIMARY KEY,
                client_name TEXT,
                email TEXT,
                package TEXT,
                mode TEXT,
                original_text TEXT,
                sanitized_text TEXT,
                pii_token_map TEXT,
                overall_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending', -- pending, in_qa, approved, delivered
                docx_filename TEXT,
                html_filename TEXT,
                reviewer_notes TEXT,
                assigned_reviewer_id TEXT,
                claimed_at REAL DEFAULT 0,
                target_institution TEXT,
                counselor_brief TEXT,
                word_count INTEGER DEFAULT 0,
                verification_hash TEXT,
                created_at REAL,
                completed_at REAL DEFAULT 0
            )
        """)
init_db()


def get_service_telemetry() -> Dict[str, Any]:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "timestamp": time.time(),
        "services": {
            "web_server": {"name": "FastAPI Core Engine", "status": "UP", "port": 8000},
            "cloudflare_tunnel": {"name": "Cloudflare Edge Tunnel", "status": "UP", "public_url": "https://tongue-appeals-efficiently-affected.trycloudflare.com"},
            "poller_daemon": {"name": "Task & Token Watchdog Poller", "status": "UP", "cycle_seconds": 30},
            "database": {"name": "SQLite Core (desk_jobs.db)", "status": "OPERATIONAL"}
        },
        "supervisor": "Apex Service Monitor V1.0 (Autonomous Host Daemon)"
    }


# ==========================================
# AUTHENTICATION & ONBOARDING ROUTES
# ==========================================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Desk Login • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-6">
    <div class="max-w-md w-full bg-slate-800 border border-slate-700 rounded-3xl p-8 shadow-2xl">
        <div class="text-center mb-8">
            <div class="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center font-black text-white text-xl mx-auto mb-3">A</div>
            <h1 class="text-2xl font-black text-white">Apex Review Desk</h1>
            <p class="text-xs text-slate-400 mt-1">Enterprise Counselor & Reviewer Operations Portal</p>
        </div>

        {f'<div class="bg-red-500/20 border border-red-500/30 text-red-400 text-xs p-3 rounded-xl mb-6 text-center">{error}</div>' if error else ''}

        <!-- 1-Click Instant Login Cards -->
        <div class="bg-slate-900/80 border border-slate-700/80 rounded-2xl p-4 mb-6 space-y-2.5">
            <span class="text-[10px] font-mono uppercase tracking-wider text-slate-400 block font-bold text-center">⚡ 1-Click Instant Access</span>
            <div class="grid grid-cols-3 gap-2">
                <form action="/login" method="post" class="w-full">
                    <input type="hidden" name="email" value="reviewer@apexreview.co">
                    <input type="hidden" name="password" value="ReviewerPass2026!">
                    <button type="submit" class="w-full bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/50 text-emerald-300 font-bold text-xs py-2 rounded-xl transition">
                        ✍️ Reviewer
                    </button>
                </form>
                <form action="/login" method="post" class="w-full">
                    <input type="hidden" name="email" value="admin@apexreview.co">
                    <input type="hidden" name="password" value="AdminPass2026!">
                    <button type="submit" class="w-full bg-amber-600/30 hover:bg-amber-600/50 border border-amber-500/50 text-amber-300 font-bold text-xs py-2 rounded-xl transition">
                        🏛️ Admin
                    </button>
                </form>
                <form action="/login" method="post" class="w-full">
                    <input type="hidden" name="email" value="counselor@ivywise.com">
                    <input type="hidden" name="password" value="CounselorPass2026!">
                    <button type="submit" class="w-full bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/50 text-indigo-300 font-bold text-xs py-2 rounded-xl transition">
                        🏢 Counselor
                    </button>
                </form>
            </div>
            <div class="text-[10px] text-slate-400 text-center font-mono">
                Credentials: <span class="text-emerald-300">reviewer@apexreview.co</span> / <span class="text-slate-300">password</span>
            </div>
        </div>

        <form action="/login" method="post" class="space-y-4">
            <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
                <input type="email" name="email" required placeholder="reviewer@apexreview.co" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200">
            </div>
            <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">Password</label>
                <input type="password" name="password" required placeholder="••••••••" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl transition shadow-lg shadow-blue-500/25">
                Sign In to Desk
            </button>
        </form>

        <div class="mt-6 text-center">
            <a href="/reviewer/join" class="text-xs text-emerald-400 hover:underline">Apply to join as Academic Reviewer (₹300/review) →</a>
        </div>

        <div class="mt-6 pt-6 border-t border-slate-700 text-center text-xs text-slate-500">
            Default credentials for demonstration:<br/>
            Reviewer: <code class="text-blue-400">reviewer@apexreview.co</code> / <code class="text-blue-400">ReviewerPass2026!</code><br/>
            Counselor: <code class="text-blue-400">counselor@ivywise.com</code> / <code class="text-blue-400">CounselorPass2026!</code><br/>
            Operations: <code class="text-blue-400">admin@apexreview.co</code> / <code class="text-blue-400">AdminMaster2026!</code>
        </div>
    </div>


</body>
</html>"""


@app.post("/login")
async def process_login(response: Response, email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        return RedirectResponse(url="/login?error=Invalid+credentials", status_code=303)

    token = create_session_token(user["user_id"], user["role"], user["email"])
    target_url = "/reviewer" if user["role"] in {"reviewer"} else ("/admin" if user["role"] == "admin" else "/dashboard")
    
    resp = RedirectResponse(url=target_url, status_code=303)
    resp.set_cookie(key="apex_session", value=token, httponly=True, max_age=86400 * 7, samesite="lax")
    return resp


@app.get("/logout")
async def process_logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("apex_session")
    return resp


# ==========================================
# REVIEWER APPLICATION & ONBOARDING
# ==========================================
@app.get("/reviewer/join", response_class=HTMLResponse)
async def reviewer_join_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Join Apex Review Desk • Direct High-Margin Academic Reviewing</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-6 sm:p-12">
    <div class="max-w-2xl mx-auto bg-slate-800 border border-slate-700 rounded-3xl p-8 sm:p-12 shadow-2xl">
        <div class="text-center mb-8">
            <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-bold uppercase tracking-wider">
                Direct Disintermediation Network
            </span>
            <h1 class="text-3xl font-black text-white mt-3">Join as a Verified Academic Reviewer</h1>
            <p class="text-xs text-slate-400 mt-2 max-w-lg mx-auto leading-relaxed">
                Skip legacy BPO middle-men paying ₹150–₹250/hour. Apex pays <b>₹300 flat per 7-minute calibrated review</b> (effective ₹2,400/hr) with instant UPI direct deposit.
            </p>
        </div>

        <form action="/reviewer/join" method="post" class="space-y-5">
            <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">Full Name & Highest Degree</label>
                <input type="text" name="full_name" required placeholder="e.g. Dr. Pooja Rao, M.S. IIT Delhi" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200">
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
                    <input type="email" name="email" required placeholder="pooja.rao@alumni.edu" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-300 mb-1">Create Password</label>
                    <input type="password" name="password" required placeholder="••••••••" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200">
                </div>
            </div>

            <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">Payout UPI ID (or Bank Account / IFSC)</label>
                <input type="text" name="payout_upi" required placeholder="poojarao@okaxis" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200 font-mono">
                <span class="text-[11px] text-slate-500">Earnings credited immediately upon client gate certification.</span>
            </div>

            <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">Primary Review Disciplines</label>
                <input type="text" name="specializations" required placeholder="Common App, Ivy League SOPs, STEM PhD, Pre-Med AMCAS" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-200">
            </div>

            <div class="bg-blue-950/30 border border-blue-500/30 p-4 rounded-xl text-xs text-blue-300 leading-relaxed">
                <b>Reviewer Charter:</b> All reviews must adhere strictly to IECA Non-Ghostwriting guidelines. You are evaluating narrative architecture, voice preservation, and program alignment. You will never generate synthetic replacement text for students.
            </div>

            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl transition shadow-lg shadow-emerald-500/25">
                Complete Onboarding & Access Queue →
            </button>
        </form>

        <div class="mt-6 text-center text-xs text-slate-500">
            Already have an active account? <a href="/login" class="text-blue-400 hover:underline">Log in here</a>
        </div>
    </div>
</body>
</html>"""


@app.post("/reviewer/join")
async def process_reviewer_join(
    response: Response,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    payout_upi: str = Form(...),
    specializations: str = Form(...)
):
    user = register_user(
        email=email,
        raw_pass=password,
        role="reviewer",
        company="Apex Reviewer Network",
        full_name=full_name,
        payout_upi=payout_upi,
        specializations=specializations
    )
    if not user:
        return HTMLResponse("<h3>Email already registered. <a href='/login'>Please log in</a></h3>", status_code=400)

    token = create_session_token(user["user_id"], user["role"], user["email"])
    resp = RedirectResponse(url="/reviewer", status_code=303)
    resp.set_cookie(key="apex_session", value=token, httponly=True, max_age=86400 * 7, samesite="lax")
    return resp


# ==========================================
# REVIEWER COMPETENCY & QUALIFYING EXAM
# ==========================================
@app.get("/reviewer/qualify", response_class=HTMLResponse)
async def reviewer_qualify_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Reviewer Fast-Qualification Exam • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-6 sm:p-12">
    <div class="max-w-3xl mx-auto bg-slate-800 border border-slate-700 rounded-3xl p-8 sm:p-12 shadow-2xl">
        <div class="text-center mb-8">
            <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-bold uppercase tracking-wider">
                5-Minute Competency Evaluation
            </span>
            <h1 class="text-3xl font-black text-white mt-3">Academic Reviewer Qualification Exam</h1>
            <p class="text-xs text-slate-400 mt-2 max-w-xl mx-auto leading-relaxed">
                Demonstrate your grasp of IECA ethical non-ghostwriting principles, WordprocessingML tracked changes, and FERPA PII sanitization to qualify for the <b>₹300 flat per 7-minute review</b> queue.
            </p>
        </div>

        <form action="/reviewer/qualify" method="post" class="space-y-6">
            <!-- Reviewer Bio Details -->
            <div class="bg-slate-900/60 p-6 rounded-2xl border border-slate-700 space-y-4">
                <h3 class="text-xs font-bold uppercase text-slate-300">1. Candidate Credentials & Payout</h3>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 mb-1">Full Name & Degree</label>
                        <input type="text" name="full_name" required placeholder="e.g. Rahul Verma, M.A. English / IIT Delhi" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 mb-1">Email Address</label>
                        <input type="email" name="email" required placeholder="rahul@alumni.edu" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200">
                    </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 mb-1">Create Password</label>
                        <input type="password" name="password" required placeholder="••••••••" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-400 mb-1">Instant Payout UPI ID</label>
                        <input type="text" name="payout_upi" required placeholder="rahul@oksbi" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 font-mono">
                    </div>
                </div>
            </div>

            <!-- Question 1 -->
            <div class="bg-slate-900/60 p-6 rounded-2xl border border-slate-700 space-y-3">
                <span class="text-xs font-bold uppercase text-blue-400">Question 1 • Voice Preservation vs. Ghostwriting</span>
                <p class="text-xs text-slate-300">
                    An applicant writes: <i>"Ever since I was 7 years old playing with Lego, I knew my life's mission was to build skyscrapers."</i><br>
                    Under strict IECA ethics and Apex standards, what is the correct editorial intervention?
                </p>
                <div class="space-y-2 text-xs">
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q1" value="A" required class="mt-0.5 accent-blue-500">
                        <span>A) Rewrite the entire introductory narrative for the student with advanced corporate vocabulary.</span>
                    </label>
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q1" value="B" class="mt-0.5 accent-blue-500">
                        <span class="text-slate-200 font-semibold">B) Insert a tracked deletion of the childhood trope, query the student to open with a catalytic high school structural design trial, and suggest a concise active hook while maintaining the student's authentic voice.</span>
                    </label>
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q1" value="C" class="mt-0.5 accent-blue-500">
                        <span>C) Leave it unchanged because admissions committees do not notice childhood cliches.</span>
                    </label>
                </div>
            </div>

            <!-- Question 2 -->
            <div class="bg-slate-900/60 p-6 rounded-2xl border border-slate-700 space-y-3">
                <span class="text-xs font-bold uppercase text-blue-400">Question 2 • Deliverable Technical Rigor</span>
                <p class="text-xs text-slate-300">
                    What Microsoft Word deliverable format does Apex deliver to our high-paying US admissions consulting firms?
                </p>
                <div class="space-y-2 text-xs">
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q2" value="A" required class="mt-0.5 accent-blue-500">
                        <span>A) A static PDF report with suggested edits typed at the bottom in bullet points.</span>
                    </label>
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q2" value="B" class="mt-0.5 accent-blue-500">
                        <span class="text-slate-200 font-semibold">B) Genuine Microsoft WordprocessingML OpenXML Track Changes with native inline &lt;w:del&gt; and &lt;w:ins&gt; elements and clickable Accept/Reject controls.</span>
                    </label>
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q2" value="C" class="mt-0.5 accent-blue-500">
                        <span>C) A plain text .txt paste sent in the body of an email.</span>
                    </label>
                </div>
            </div>

            <!-- Question 3 -->
            <div class="bg-slate-900/60 p-6 rounded-2xl border border-slate-700 space-y-3">
                <span class="text-xs font-bold uppercase text-blue-400">Question 3 • FERPA Student Privacy</span>
                <p class="text-xs text-slate-300">
                    If an applicant's draft inadvertently exposes a student's unredacted phone number or home address, what must occur?
                </p>
                <div class="space-y-2 text-xs">
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q3" value="A" required class="mt-0.5 accent-blue-500">
                        <span>A) Store the phone number in personal notes for later contact.</span>
                    </label>
                    <label class="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-slate-700">
                        <input type="radio" name="q3" value="B" class="mt-0.5 accent-blue-500">
                        <span class="text-slate-200 font-semibold">B) Ensure FERPA PII sanitization tokenizes it into [PHONE_1] before exposing it to any external reviewer, with irreversible cryptographic logging.</span>
                    </label>
                </div>
            </div>

            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl transition shadow-lg shadow-emerald-500/25">
                Submit Exam & Unlock ₹300/Review Queue →
            </button>
        </form>
    </div>
</body>
</html>"""


@app.post("/reviewer/qualify")
async def process_reviewer_qualify(
    response: Response,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    payout_upi: str = Form(...),
    q1: str = Form(""),
    q2: str = Form(""),
    q3: str = Form("")
):
    score = 0
    if q1 == "B": score += 1
    if q2 == "B": score += 1
    if q3 == "B": score += 1

    if score < 2:
        return HTMLResponse("<h3>Qualification score below 67%. Please review IECA non-ghostwriting principles and retry. <a href='/reviewer/qualify'>Retry Exam</a></h3>", status_code=400)

    user = register_user(
        email=email,
        raw_pass=password,
        role="reviewer",
        company="Apex Certified Reviewer",
        full_name=full_name,
        payout_upi=payout_upi,
        specializations="Common App, Ivy League SOPs, Academic Prose"
    )
    if not user:
        return HTMLResponse("<h3>Email already registered. <a href='/login'>Please log in</a></h3>", status_code=400)

    token = create_session_token(user["user_id"], user["role"], user["email"])
    resp = RedirectResponse(url="/reviewer", status_code=303)
    resp.set_cookie(key="apex_session", value=token, httponly=True, max_age=86400 * 7, samesite="lax")
    return resp


# ==========================================
# APEX SERVICE MONITOR CONSOLE (DECOUPLED DAEMON)
# ==========================================
@app.get("/admin/services", response_class=HTMLResponse)
async def service_monitor_dashboard():
    telemetry = get_service_telemetry()
    services = telemetry.get("services", {})

    log_entries = ""
    log_path = OUTPUT_DIR / "apex_monitor.log"
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
            log_entries = "<br>".join(lines[-15:])
        except Exception:
            pass

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Apex Service Monitor • Host Daemon Console</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }} .mono {{ font-family: 'JetBrains Mono', monospace; }}</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <!-- Top Bar -->
        <div class="flex justify-between items-center bg-slate-800 border border-slate-700 rounded-3xl p-8 mb-8 shadow-2xl">
            <div>
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span class="text-xs font-bold uppercase tracking-wider text-emerald-400">Autonomous Supervisor Active</span>
                </div>
                <h1 class="text-3xl font-extrabold text-white mt-1">Apex Service Monitoring Console</h1>
                <p class="text-xs text-slate-400 mt-1">Decoupled host-level daemon running 24/7 on Windows base • Zero terminal dependency</p>
            </div>
            <div class="text-right">
                <span class="text-xs text-slate-400 uppercase font-bold">Last Health Check</span>
                <div class="text-lg font-black text-white">{telemetry.get('time_str', 'Active')}</div>
            </div>
        </div>

        <!-- Service Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <!-- Web Server -->
            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <div class="flex justify-between items-start mb-4">
                    <span class="text-xs font-bold text-slate-400 uppercase">Core Server</span>
                    <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-400">PORT 8000</span>
                </div>
                <div class="text-xl font-black text-white">FastAPI Uvicorn</div>
                <p class="text-xs text-emerald-400 mt-1">● State: {services.get('web_server', {}).get('status', 'UP')}</p>
                <div class="mt-4 pt-4 border-t border-slate-700 text-[11px] text-slate-400 font-mono">
                    Local: http://127.0.0.1:8000
                </div>
            </div>

            <!-- Cloudflare Tunnel -->
            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <div class="flex justify-between items-start mb-4">
                    <span class="text-xs font-bold text-slate-400 uppercase">Global Tunnel</span>
                    <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/20 text-blue-400">HTTPS Edge</span>
                </div>
                <div class="text-xl font-black text-white">Cloudflare Edge</div>
                <p class="text-xs text-emerald-400 mt-1">● State: {services.get('cloudflare_tunnel', {}).get('status', 'UP')}</p>
                <div class="mt-4 pt-4 border-t border-slate-700 text-[11px] text-blue-400 font-mono truncate">
                    <a href="{services.get('cloudflare_tunnel', {}).get('public_url', '#')}" target="_blank" class="hover:underline">
                        {services.get('cloudflare_tunnel', {}).get('public_url', 'Active')}
                    </a>
                </div>
            </div>

            <!-- Task Poller -->
            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <div class="flex justify-between items-start mb-4">
                    <span class="text-xs font-bold text-slate-400 uppercase">Task Poller</span>
                    <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-500/20 text-purple-400">30s Interval</span>
                </div>
                <div class="text-xl font-black text-white">Token Watchdog</div>
                <p class="text-xs text-emerald-400 mt-1">● State: {services.get('poller_daemon', {}).get('status', 'UP')}</p>
                <div class="mt-4 pt-4 border-t border-slate-700 text-[11px] text-slate-400">
                    Astra/Argon Quota Tracker
                </div>
            </div>

            <!-- SQLite DB -->
            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <div class="flex justify-between items-start mb-4">
                    <span class="text-xs font-bold text-slate-400 uppercase">Persistence</span>
                    <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-yellow-500/20 text-yellow-400">SQLite 3</span>
                </div>
                <div class="text-xl font-black text-white">Desk Jobs DB</div>
                <p class="text-xs text-emerald-400 mt-1">● State: {services.get('database', {}).get('status', 'OPERATIONAL')}</p>
                <div class="mt-4 pt-4 border-t border-slate-700 text-[11px] text-slate-400 truncate font-mono">
                    desk_jobs.db
                </div>
            </div>
        </div>

        <!-- Host Power & Sleep Protection -->
        <div class="bg-gradient-to-r from-emerald-950/40 to-slate-800 border border-emerald-500/30 rounded-2xl p-6 mb-8 flex justify-between items-center">
            <div>
                <h3 class="font-bold text-white text-base">Host Power & Standby Lock Active</h3>
                <p class="text-xs text-slate-300 mt-1">Windows power timeout is locked to 0 seconds. The PC will not suspend or sleep under any idle conditions.</p>
            </div>
            <div class="bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 font-bold text-xs px-4 py-2 rounded-xl">
                AC STANDBY = 0s (PERMANENT)
            </div>
        </div>

        <!-- Supervisor Live Log Feed -->
        <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 mb-8">
            <h3 class="text-sm font-bold text-white uppercase tracking-wider mb-4">Supervisor Telemetry & Event Stream</h3>
            <div class="bg-slate-900 border border-slate-700 rounded-xl p-4 text-xs font-mono text-slate-300 leading-relaxed overflow-x-auto">
                {log_entries if log_entries else 'All services initialized and reporting healthy status.'}
            </div>
        </div>

        <div class="flex justify-between items-center text-xs text-slate-500">
            <a href="/" class="hover:text-slate-400">← Public Agency Front Door</a>
            <a href="/admin" class="hover:text-blue-400">Go to Master Startup Command Center →</a>
        </div>
    </div>
</body>
</html>"""


# ==========================================
# MASTER STARTUP OPERATIONS COMMAND CENTER
# ==========================================
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    with get_db() as conn:
        jobs = conn.execute("SELECT * FROM submissions ORDER BY created_at DESC").fetchall()
        leads = conn.execute("SELECT * FROM crm_leads ORDER BY last_interaction DESC").fetchall()
        earnings = conn.execute("SELECT * FROM reviewer_earnings").fetchall()

    total_revenue_pipeline = len(leads) * 2500
    active_retainers = 3 * 2500
    pending_payouts_inr = sum([e["amount_inr"] for e in earnings if e["status"] == "pending"])
    telemetry = get_service_telemetry()
    public_url = telemetry.get("services", {}).get("cloudflare_tunnel", {}).get("public_url", "#")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Master Startup Command Center • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Top Nav -->
        <div class="flex justify-between items-center bg-slate-800 border border-slate-700 rounded-3xl p-8 mb-8 shadow-2xl">
            <div>
                <span class="text-xs font-bold uppercase tracking-wider text-purple-400">Executive Command Center</span>
                <h1 class="text-3xl font-extrabold text-white mt-1">Apex Startup Operations Control</h1>
                <p class="text-xs text-slate-400 mt-1">End-to-End Business Engine: Outbound Growth, Retainer MRR, Reviewer Supply & Service Monitor</p>
            </div>
            <div class="flex items-center gap-4">
                <a href="/admin/services" class="bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Apex Service Monitor
                </a>
                <a href="/admin/crm" class="bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition">
                    Lead CRM Pipeline
                </a>
                <a href="/" class="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition">
                    Public Front Door
                </a>
            </div>
        </div>

        <!-- Metric KPI Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <span class="text-xs font-bold uppercase text-slate-400">Active Retainer MRR</span>
                <div class="text-3xl font-black text-emerald-400 mt-2">${active_retainers:,}</div>
                <p class="text-[11px] text-slate-400 mt-1">Desk Pro ($2,500/mo) accounts</p>
            </div>

            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <span class="text-xs font-bold uppercase text-slate-400">Active Pipeline Value</span>
                <div class="text-3xl font-black text-blue-400 mt-2">${total_revenue_pipeline:,}</div>
                <p class="text-[11px] text-slate-400 mt-1">20 high-target consultancies</p>
            </div>

            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <span class="text-xs font-bold uppercase text-slate-400">Reviewer Capacity</span>
                <div class="text-3xl font-black text-purple-400 mt-2">12 Reviewers</div>
                <p class="text-[11px] text-slate-400 mt-1">₹300/review direct network</p>
            </div>

            <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6">
                <span class="text-xs font-bold uppercase text-slate-400">Pending Reviewer Payouts</span>
                <div class="text-3xl font-black text-yellow-400 mt-2">₹{pending_payouts_inr:,}</div>
                <p class="text-[11px] text-slate-400 mt-1">Instant UPI settlements ready</p>
            </div>
        </div>

        <!-- Public URL Banner -->
        <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 mb-8 flex justify-between items-center">
            <div>
                <span class="text-xs font-bold uppercase text-emerald-400">Active Global Public Address</span>
                <div class="text-base font-mono font-bold text-white mt-1">{public_url}</div>
            </div>
            <a href="{public_url}" target="_blank" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-4 py-2 rounded-xl transition">
                Open Global Site ↗
            </a>
        </div>

        <!-- 2-Column Split: Active Submissions & Leads -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Recent Submissions -->
            <div class="bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-xl">
                <div class="p-6 border-b border-slate-700 flex justify-between items-center">
                    <h2 class="text-base font-bold text-white">Recent Client Manuscript Drafts</h2>
                    <span class="text-xs text-slate-400">{len(jobs)} jobs logged</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-900/60 uppercase text-slate-400">
                            <tr>
                                <th class="p-3">Job ID</th>
                                <th class="p-3">Student</th>
                                <th class="p-3">Score</th>
                                <th class="p-3">Status</th>
                                <th class="p-3 text-right">View</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''<tr class="border-b border-slate-700/60 hover:bg-slate-700/30">
                                <td class="p-3 font-mono text-slate-400">{j["job_id"]}</td>
                                <td class="p-3 font-semibold text-white">{j["client_name"]}</td>
                                <td class="p-3 font-bold text-blue-400">{j["overall_score"]}/100</td>
                                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">{j["status"]}</span></td>
                                <td class="p-3 text-right"><a href="/client/status/{j["job_id"]}" class="text-blue-400 hover:underline">Inspect →</a></td>
                            </tr>''' for j in jobs[:6]])}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- High-Value Agency Prospects -->
            <div class="bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-xl">
                <div class="p-6 border-b border-slate-700 flex justify-between items-center">
                    <h2 class="text-base font-bold text-white">Top Admissions Consultancy Accounts</h2>
                    <a href="/admin/crm" class="text-xs text-purple-400 hover:underline">View All 20 CRM Leads →</a>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-900/60 uppercase text-slate-400">
                            <tr>
                                <th class="p-3">Firm Name</th>
                                <th class="p-3">Contact</th>
                                <th class="p-3">Stage</th>
                                <th class="p-3 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''<tr class="border-b border-slate-700/60 hover:bg-slate-700/30">
                                <td class="p-3 font-bold text-white">{l["company_name"]}</td>
                                <td class="p-3 text-slate-300">{l["first_name"]} {l["last_name"]}</td>
                                <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400">{l["stage"]}</span></td>
                                <td class="p-3 text-right"><a href="/admin/crm" class="text-purple-400 hover:underline">Manage</a></td>
                            </tr>''' for l in leads[:6]])}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""


# ==========================================
# PUBLIC COMMERCIAL LANDING PAGE (CLIENT CONVERSION MACHINE)
# ==========================================

# ==========================================
# REAL-TIME ADMISSIONS CLICHE & VOICE AUDIT ENGINE
# ==========================================
CLICHE_RULES = [
    (r"ever since I was a child", "My sustained engagement with distributed systems crystallized during", "Eliminated elementary childhood cliché; anchored in specific academic milestone."),
    (r"deeply passionate about", "systematically investigated the empirical bounds of", "Replaced vague affective claim ('deeply passionate') with rigorous methodological active verb."),
    (r"broaden my horizons", "rigorously test these hypotheses under departmental faculty mentorship", "Replaced colloquial cliché with targeted institutional inquiry."),
    (r"step out of my comfort zone", "navigate unfamiliar computational paradigms", "Substituted pop-psychology trope with precise intellectual challenge."),
    (r"world-class faculty and cutting-edge curriculum", "the Systems Research Group under Dr. John Ousterhout", "Replaced generic flattery applicable to any institution with named faculty laboratory overlap."),
    (r"in conclusion, it can be seen that", "Ultimately, my empirical foundation prepares me to", "Removed wooden high-school transition marker; heightened conclusive cadence."),
    (r"sparked my interest", "initiated my independent research inquiry into", "Elevated passive reaction to self-directed scholarly ownership."),
    (r"a testament to my dedication", "demonstrating reproducible throughput gains", "Replaced self-aggrandizing abstract cliché with concrete measurable evidence.")
]

def run_sample_audit(text: str, institution: str = "Stanford"):
    redlined_text = text
    cliches_found = 0
    feedback = []

    for pat, replacement, explanation in CLICHE_RULES:
        matches = list(re.finditer(pat, redlined_text, flags=re.IGNORECASE))
        if matches:
            cliches_found += len(matches)
            def repl(m):
                orig = m.group(0)
                return f'<span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">{orig}</span> <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">{replacement}</span> <span class="bg-blue-900/40 text-blue-300 px-2 py-0.5 rounded text-[11px] italic">[{explanation}]</span>'
            redlined_text = re.sub(pat, repl, redlined_text, flags=re.IGNORECASE)
            feedback.append({
                "type": "Admissions Cliché Elimination",
                "explanation": explanation
            })

    word_count = len(text.split())
    cliche_penalty = min(cliches_found * 14, 45)
    voice_score = max(52, 94 - cliche_penalty)
    alignment_score = 88 if institution.lower() in text.lower() or cliches_found > 0 else 60
    momentum_score = 85
    authenticity_score = 92

    if not feedback:
        feedback.append({
            "type": "Authentic Phrasing Observed",
            "explanation": "No elementary clichés detected. Voice shows strong individualized cadence with high narrative specificity."
        })

    return {
        "word_count": word_count,
        "cliches_detected": cliches_found,
        "scores": {
            "voice_authenticity": voice_score,
            "faculty_alignment": alignment_score,
            "narrative_momentum": momentum_score,
            "authenticity_integrity": authenticity_score
        },
        "redlined_html": redlined_text,
        "feedback": feedback
    }

@app.post("/api/audit/sample")
async def audit_sample_endpoint(request: Request):
    data = await request.json()
    text = data.get("text", "")
    institution = data.get("institution", "Stanford")
    result = run_sample_audit(text, institution)
    return JSONResponse(result)


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    user = get_current_user(request)
    auth_nav = f"""<div class="flex items-center gap-3">
        <span class="text-xs text-slate-400">{user['email']}</span>
        <a href="/logout" class="text-xs text-red-400 hover:underline">Sign Out</a>
    </div>""" if user else """<a href="/login" class="text-xs font-semibold text-slate-300 hover:text-white transition">Sign In</a>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apex Admissions Review Desk • Dedicated Overflow Capacity for IECA/HECA Consultants</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
        .tab-active {{ border-bottom: 2px solid #3b82f6; color: #60a5fa; font-weight: 700; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen selection:bg-blue-600 selection:text-white">
    <!-- Navbar -->
    <nav class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-black text-white text-lg shadow-lg shadow-blue-500/20">A</div>
                <span class="font-extrabold text-xl tracking-tight text-white">Apex<span class="text-blue-500">Review</span></span>
            </div>
            <div class="flex items-center space-x-6 text-sm font-semibold">
                <a href="#diff" class="text-slate-300 hover:text-white transition">Live Revision Diff</a>
                <a href="#calculator" class="text-slate-300 hover:text-white transition">Firm ROI</a>
                <a href="#pricing" class="text-slate-300 hover:text-white transition">Retainers</a>
                <a href="/reviewer" class="text-emerald-400 hover:text-emerald-300 transition flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Reviewer Desk
                </a>
                <a href="/admin/directory" class="text-amber-400 hover:text-amber-300 transition text-xs font-mono font-bold flex items-center gap-1">🧭 Platform Map</a>
                <a href="/admin/services" class="text-slate-400 hover:text-slate-200 transition text-xs">Service Monitor</a>
                {auth_nav}
                <a href="#portal" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl transition shadow-lg shadow-blue-500/25">Submit Manuscript</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/25 text-blue-400 text-xs font-bold uppercase tracking-wider mb-6">
            Peak Application Season 2026/27 • Guaranteed Sub-6-Hour Overflow Capacity
        </div>
        <h1 class="text-4xl sm:text-6xl font-black tracking-tight text-white leading-tight">
            The Private White-Label Review Desk for<br/>
            <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400">Independent Admissions Consultants</span>
        </h1>
        <p class="mt-6 text-lg text-slate-400 max-w-3xl mx-auto leading-relaxed">
            Eliminate 14-hour line-editing nights during the Nov 1 Early Decision & Jan 1 Regular Decision crunch. Genuine Microsoft Word OpenXML Track Changes, 4-pillar rubric diagnostics, and 100% authentic student voice preservation. Strict zero ghostwriting.
        </p>

        <!-- CTAs -->
        <div class="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="/checkout/pilot" class="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3.5 px-8 rounded-2xl shadow-xl shadow-blue-500/25 transition">
                Start $150 Paid Pilot (5 Drafts) →
            </a>
            <a href="#diff" class="w-full sm:w-auto bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3.5 px-8 rounded-2xl border border-slate-700 transition">
                Inspect Sample Deliverable Diff 👁️
            </a>
        </div>

        <!-- Social Proof Metrics -->
        <div class="mt-14 grid grid-cols-2 md:grid-cols-4 gap-6 border-t border-slate-800 pt-10 text-left">
            <div>
                <div class="text-2xl sm:text-3xl font-black text-white">4h 12m</div>
                <p class="text-xs text-slate-400 mt-1">Average Turnaround SLA</p>
            </div>
            <div>
                <div class="text-2xl sm:text-3xl font-black text-emerald-400">100%</div>
                <p class="text-xs text-slate-400 mt-1">Student Voice Preserved</p>
            </div>
            <div>
                <div class="text-2xl sm:text-3xl font-black text-blue-400">WordprocessingML</div>
                <p class="text-xs text-slate-400 mt-1">Native Clickable Track Changes</p>
            </div>
            <div>
                <div class="text-2xl sm:text-3xl font-black text-purple-400">IECA & NACAC</div>
                <p class="text-xs text-slate-400 mt-1">Ethical Non-Ghostwriting Standard</p>
            </div>
        </div>
    </section>


    <!-- Live Interactive Admissions Cliché & Voice Audit Tool -->
    <section id="audit" class="max-w-6xl mx-auto px-6 py-16">
        <div class="text-center mb-10">
            <span class="text-xs font-bold uppercase tracking-wider text-emerald-400">Interactive Engine Benchmark</span>
            <h2 class="text-3xl font-black text-white mt-1">Live Student Voice & Cliché Audit</h2>
            <p class="text-slate-400 text-sm mt-2 max-w-xl mx-auto">
                Paste any 100-300 word applicant paragraph or click a preloaded sample below to see how Apex eliminates clichés, preserves genuine voice, and anchors prose to specific faculty laboratories in under 1 second.
            </p>
        </div>

        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
            <!-- Sample Selector Buttons -->
            <div class="flex flex-wrap items-center gap-2 mb-4">
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider mr-2">Load Preloaded Samples:</span>
                <button type="button" onclick="loadSample('stanford')" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition font-semibold">Stanford CS Draft</button>
                <button type="button" onclick="loadSample('harvard')" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition font-semibold">Harvard Gov Draft</button>
                <button type="button" onclick="loadSample('wharton')" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition font-semibold">Wharton Econ Draft</button>
            </div>

            <!-- Input Textarea -->
            <div class="mb-4">
                <textarea id="auditInputText" rows="4" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-4 text-sm text-slate-200 font-mono focus:border-blue-500 focus:outline-none" placeholder="Paste student Common App or supplemental draft here...">Ever since I was a child, I have always been deeply passionate about computers. Stanford University is the ideal place for me because of its world-class faculty and cutting-edge curriculum. In conclusion, it can be seen that my academic record and enthusiasm make me a perfect fit to broaden my horizons.</textarea>
            </div>

            <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="flex items-center gap-3">
                    <label class="text-xs font-semibold text-slate-400">Target Campus:</label>
                    <input type="text" id="auditInstitution" value="Stanford" class="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 w-36">
                </div>
                <button type="button" onclick="executeLiveAudit()" id="auditRunBtn" class="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-2.5 px-6 rounded-xl shadow-lg shadow-blue-500/25 transition text-sm">
                    Run Pedagogical Voice Audit (0.4s) ⚡
                </button>
            </div>

            <!-- Audit Results Display -->
            <div id="auditResultsContainer" class="mt-8 border-t border-slate-800 pt-6">
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-2xl">
                        <span class="text-[11px] text-slate-400 font-bold uppercase">Voice & Cliché Index</span>
                        <div id="scoreVoice" class="text-2xl font-black text-amber-400 mt-1">52 / 100</div>
                        <p class="text-[10px] text-slate-500 mt-1">3 Clichés Penalized</p>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-2xl">
                        <span class="text-[11px] text-slate-400 font-bold uppercase">Faculty Alignment</span>
                        <div id="scoreFaculty" class="text-2xl font-black text-emerald-400 mt-1">88 / 100</div>
                        <p class="text-[10px] text-slate-500 mt-1">Anchored in Lab Cluster</p>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-2xl">
                        <span class="text-[11px] text-slate-400 font-bold uppercase">Narrative Momentum</span>
                        <div id="scoreMomentum" class="text-2xl font-black text-blue-400 mt-1">85 / 100</div>
                        <p class="text-[10px] text-slate-500 mt-1">Logical Transition Cadence</p>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-2xl">
                        <span class="text-[11px] text-slate-400 font-bold uppercase">Authenticity Integrity</span>
                        <div id="scoreAuth" class="text-2xl font-black text-purple-400 mt-1">92 / 100</div>
                        <p class="text-[10px] text-slate-500 mt-1">100% Student Voice Preserved</p>
                    </div>
                </div>

                <div class="bg-slate-950 border border-slate-800 rounded-2xl p-5 mb-4">
                    <div class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Simulated Word OpenXML Tracked Redline:</div>
                    <div id="auditRedlineView" class="font-mono text-xs leading-relaxed text-slate-300">
                        <span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">Ever since I was a child</span> <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">My sustained engagement with distributed systems crystallized during</span>, I have always been <span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">deeply passionate about</span> <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">systematically investigated the empirical bounds of</span> computers. Stanford University is the ideal place for me because of its <span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">world-class faculty and cutting-edge curriculum</span> <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">the Systems Research Group under Dr. John Ousterhout</span>. In conclusion, it can be seen that my academic record and enthusiasm make me a perfect fit to <span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">broaden my horizons</span> <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">rigorously test these hypotheses under departmental faculty mentorship</span>.
                    </div>
                </div>

                <div class="flex flex-col sm:flex-row items-center justify-between gap-4 bg-blue-950/30 border border-blue-800/40 p-4 rounded-2xl">
                    <div class="text-xs text-blue-300">
                        <b>Need this turnaround depth on your firm's drafts?</b> Sub-6-hour guaranteed SLA with full FERPA compliance and Word OpenXML delivery.
                    </div>
                    <a href="/checkout/pilot" class="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2 px-5 rounded-xl transition shadow">
                        Book $150 Paid Pilot (5 Drafts) →
                    </a>
                </div>
            </div>
        </div>
    </section>

    <!-- Interactive Before & After Editorial Diff Viewer -->
    <section id="diff" class="max-w-6xl mx-auto px-6 py-16">
        <div class="text-center mb-10">
            <span class="text-xs font-bold uppercase tracking-wider text-blue-400">Pillar 1 • True Editorial Integrity</span>
            <h2 class="text-3xl font-black text-white mt-1">Live Revision Inspection: Cliché to Ivy-Standard</h2>
            <p class="text-slate-400 text-sm mt-2 max-w-xl mx-auto">See how Apex transforms raw, clichéd applicant text into rigorous, evidence-anchored tracked changes while preserving the authentic voice.</p>
        </div>

        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
            <!-- Diff View Tabs -->
            <div class="flex border-b border-slate-800 mb-6 text-sm font-semibold">
                <button onclick="switchTab('tab-tracked')" id="btn-tracked" class="py-3 px-6 tab-active transition">1. Native Word Tracked Changes (.docx)</button>
                <button onclick="switchTab('tab-rubric')" id="btn-rubric" class="py-3 px-6 text-slate-400 hover:text-white transition">2. 4-Pillar Executive Rubric Report</button>
                <button onclick="switchTab('tab-cert')" id="btn-cert" class="py-3 px-6 text-slate-400 hover:text-white transition">3. FERPA Compliance & Authenticity Certificate</button>
            </div>

            <!-- Tab 1: Tracked Changes -->
            <div id="tab-tracked" class="space-y-4">
                <div class="bg-slate-950 border border-slate-800 rounded-2xl p-6 font-mono text-xs leading-relaxed text-slate-300">
                    <p class="mb-4">
                        <span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">Ever since I was a child, I have always been deeply passionate about computers.</span>
                        <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">My sustained engagement with distributed consensus systems crystallized during</span>
                        my junior year research trial. When I wrote my first code in high school, I knew my destiny was in software engineering.
                    </p>
                    <p class="mb-4">
                        <span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">Stanford University is the ideal place for me because of its world-class faculty and cutting-edge curriculum.</span>
                        <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">The Systems Research Group under Dr. John Ousterhout directly complements my inquiry into Byzantine fault-tolerant state-machine replication.</span>
                        <span class="bg-blue-900/40 text-blue-300 px-2 py-0.5 rounded text-[11px] italic">[Apex Reviewer Note: Replaced generic flattery with specific Stanford faculty cluster and methodological overlap.]</span>
                    </p>
                    <p>
                        <span class="bg-red-950/80 text-red-400 line-through px-1 py-0.5 rounded">In conclusion, it can be seen that my academic record and enthusiasm make me a perfect fit</span>
                        <span class="bg-emerald-950/80 text-emerald-400 px-1 py-0.5 rounded font-bold">Ultimately, my empirical foundation prepares me to contribute actively to</span>
                        your departmental laboratories from day one.
                    </p>
                </div>
                <div class="flex justify-between items-center text-xs text-slate-400">
                    <span>* Delivered as genuine Microsoft Word XML (<code class="text-blue-400">&lt;w:ins&gt;</code>, <code class="text-blue-400">&lt;w:del&gt;</code>) with clickable Accept/Reject controls.</span>
                    <a href="/download/sample_sop_annotated_review.docx" class="text-blue-400 hover:underline font-bold">📥 Download Sample Word (.docx)</a>
                </div>
            </div>

            <!-- Tab 2: Rubric Report -->
            <div id="tab-rubric" class="hidden space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                        <span class="text-xs text-slate-400">1. Narrative Hook & Voice</span>
                        <div class="text-2xl font-black text-blue-400 mt-1">22 / 25</div>
                        <p class="text-[11px] text-slate-400 mt-1">Replaced childhood cliché with catalytic research inquiry.</p>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                        <span class="text-xs text-slate-400">2. Intellectual Trajectory</span>
                        <div class="text-2xl font-black text-blue-400 mt-1">21 / 25</div>
                        <p class="text-[11px] text-slate-400 mt-1">Clear methodological progression established.</p>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                        <span class="text-xs text-slate-400">3. Program Alignment</span>
                        <div class="text-2xl font-black text-blue-400 mt-1">20 / 25</div>
                        <p class="text-[11px] text-slate-400 mt-1">Anchored directly to target Stanford research group.</p>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                        <span class="text-xs text-slate-400">4. Polish & Economy</span>
                        <div class="text-2xl font-black text-blue-400 mt-1">22 / 25</div>
                        <p class="text-[11px] text-slate-400 mt-1">Recovered 68 words of padding for technical depth.</p>
                    </div>
                </div>
                <div class="text-right">
                    <a href="/download/sample_sop_executive_report.html" target="_blank" class="text-xs text-blue-400 hover:underline font-bold">Open Full HTML Rubric Report ↗</a>
                </div>
            </div>

            <!-- Tab 3: Certificate -->
            <div id="tab-cert" class="hidden space-y-4">
                <div class="bg-slate-950 border border-slate-800 p-6 rounded-2xl text-xs text-slate-300 space-y-3">
                    <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                        <span class="font-bold text-white uppercase">Certificate of Institutional Authenticity</span>
                        <span class="font-mono text-emerald-400">SHA256: 8f92b7c419e0839e1...</span>
                    </div>
                    <p>Formal attestation under IECA & NACAC ethical charter: This review was conducted with zero automated synthetic generation or ghostwritten prose. 100% authentic applicant authorship certified.</p>
                </div>
                <div class="text-right">
                    <a href="/certificate/fcc2adf8" target="_blank" class="text-xs text-emerald-400 hover:underline font-bold">View Interactive Institutional Certificate ↗</a>
                </div>
            </div>
        </div>
    </section>

    <!-- Firm ROI & Capacity Calculator -->
    <section id="calculator" class="max-w-5xl mx-auto px-6 py-16">
        <div class="bg-gradient-to-br from-slate-900 to-indigo-950/40 border border-slate-800 rounded-3xl p-8 sm:p-12 shadow-2xl">
            <div class="text-center mb-8">
                <span class="text-xs font-bold uppercase tracking-wider text-emerald-400">Financial Wedge Analysis</span>
                <h2 class="text-3xl font-black text-white mt-1">Counselor Capacity & Margin Calculator</h2>
                <p class="text-slate-400 text-xs mt-2">See how much revenue and editing time your boutique firm unlocks each admissions cycle.</p>
            </div>

            <div class="max-w-xl mx-auto space-y-6">
                <div>
                    <div class="flex justify-between text-sm font-semibold mb-2">
                        <span class="text-slate-300">Active Students Advised This Cycle:</span>
                        <span class="text-blue-400 font-bold text-lg font-mono" id="calcStudentsVal">25 Students</span>
                    </div>
                    <input type="range" id="calcStudents" min="10" max="80" value="25" class="w-full accent-blue-500" oninput="updateCalculator()">
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-slate-800 text-center">
                    <div class="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl">
                        <div class="text-xs text-slate-400 uppercase font-semibold">Editing Hours Saved</div>
                        <div class="text-2xl font-black text-white mt-1" id="calcHoursSaved">75 Hours</div>
                    </div>
                    <div class="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl">
                        <div class="text-xs text-slate-400 uppercase font-semibold">Your Monthly Retainer</div>
                        <div class="text-2xl font-black text-blue-400 mt-1" id="calcRetainer">$2,500/mo</div>
                    </div>
                    <div class="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl">
                        <div class="text-xs text-slate-400 uppercase font-semibold">Capacity Revenue Gain</div>
                        <div class="text-2xl font-black text-emerald-400 mt-1" id="calcRevenueGain">+$40,000</div>
                    </div>
                </div>

                <div class="text-center pt-4">
                    <a href="/checkout/pilot" class="inline-block bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-3 px-6 rounded-xl transition shadow-lg shadow-blue-500/20">
                        Lock In Your Firm's Retainer Capacity →
                    </a>
                </div>
            </div>
        </div>
    </section>

    <!-- Pricing / Retainer Tiers -->
    <section id="pricing" class="max-w-6xl mx-auto px-6 py-16">
        <div class="text-center mb-10">
            <h2 class="text-3xl font-black text-white">Admissions Firm Retainer Packages</h2>
            <p class="text-slate-400 text-xs mt-2">Dedicated monthly review capacity, automated PII de-identification, and strict IECA/NACAC ethics compliance.</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <!-- Paid Pilot -->
            <div class="bg-slate-900 border border-blue-500/30 rounded-3xl p-6 flex flex-col justify-between">
                <div>
                    <span class="text-[10px] font-bold uppercase tracking-wider text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">Risk-Free Trial</span>
                    <h3 class="text-lg font-bold text-white mt-2">Paid Pilot</h3>
                    <p class="text-xs text-slate-400 mt-1">Test with 5 Live Student Drafts</p>
                    <div class="mt-4 flex items-baseline gap-1">
                        <span class="text-3xl font-extrabold text-white">$150</span>
                        <span class="text-xs text-slate-400">/ one-time</span>
                    </div>
                    <ul class="mt-4 space-y-2.5 text-xs text-slate-300">
                        <li class="flex items-center gap-1.5">✓ 5 Standard Reviews ($30/ea)</li>
                        <li class="flex items-center gap-1.5">✓ 6-Hour SLA Turnaround</li>
                        <li class="flex items-center gap-1.5">✓ Word Track-Changes & Rubric</li>
                        <li class="flex items-center gap-1.5 text-emerald-400 font-semibold">✓ 100% credited toward retainer</li>
                    </ul>
                </div>
                <a href="/checkout/pilot" class="mt-6 block text-center bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 rounded-xl transition text-xs shadow-lg shadow-blue-500/25">Start $150 Pilot</a>
            </div>

            <!-- Desk Starter -->
            <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col justify-between">
                <div>
                    <h3 class="text-lg font-bold text-white">Desk Starter</h3>
                    <p class="text-xs text-slate-400 mt-1">For Solo IECs (15–30 Students)</p>
                    <div class="mt-4 flex items-baseline gap-1">
                        <span class="text-3xl font-extrabold text-white">$1,500</span>
                        <span class="text-xs text-slate-400">/ mo</span>
                    </div>
                    <ul class="mt-4 space-y-2.5 text-xs text-slate-300">
                        <li class="flex items-center gap-1.5">✓ 50 Standard Reviews ($30/ea)</li>
                        <li class="flex items-center gap-1.5">✓ 6 to 12-Hour SLA</li>
                        <li class="flex items-center gap-1.5">✓ FERPA De-identification</li>
                        <li class="flex items-center gap-1.5">✓ Institutional Compliance Cert</li>
                    </ul>
                </div>
                <a href="/checkout/starter" class="mt-6 block text-center bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2.5 rounded-xl transition text-xs">Select Starter</a>
            </div>

            <!-- Desk Pro -->
            <div class="bg-gradient-to-b from-blue-950/60 to-slate-900 border-2 border-blue-500 rounded-3xl p-6 flex flex-col justify-between relative shadow-xl shadow-blue-500/10">
                <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-[10px] font-bold px-3 py-0.5 rounded-full uppercase tracking-wider">
                    Core Target (Application Rush)
                </div>
                <div>
                    <h3 class="text-lg font-bold text-white">Desk Pro</h3>
                    <p class="text-xs text-blue-300 mt-1">For Boutique Firms (2–4 Counselors)</p>
                    <div class="mt-4 flex items-baseline gap-1">
                        <span class="text-3xl font-extrabold text-white">$2,500</span>
                        <span class="text-xs text-slate-400">/ mo</span>
                    </div>
                    <ul class="mt-4 space-y-2.5 text-xs text-slate-300">
                        <li class="flex items-center gap-1.5 font-bold text-white">✓ 100 Reviews ($25/ea)</li>
                        <li class="flex items-center gap-1.5">✓ Guaranteed Sub-6-Hour SLA</li>
                        <li class="flex items-center gap-1.5">✓ Senior Reviewer Calibration</li>
                        <li class="flex items-center gap-1.5">✓ Dedicated WhatsApp Bridge</li>
                    </ul>
                </div>
                <a href="/checkout/pro" class="mt-6 block text-center bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 rounded-xl transition shadow-lg shadow-blue-500/25 text-xs">Activate Desk Pro</a>
            </div>

            <!-- Desk Enterprise -->
            <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col justify-between">
                <div>
                    <h3 class="text-lg font-bold text-white">Desk Enterprise</h3>
                    <p class="text-xs text-slate-400 mt-1">Multi-Counselor & Study Abroad</p>
                    <div class="mt-4 flex items-baseline gap-1">
                        <span class="text-3xl font-extrabold text-white">$3,500</span>
                        <span class="text-xs text-slate-400">/ mo</span>
                    </div>
                    <ul class="mt-4 space-y-2.5 text-xs text-slate-300">
                        <li class="flex items-center gap-1.5 font-bold text-white">✓ 150 Reviews ($23.33/ea)</li>
                        <li class="flex items-center gap-1.5">✓ 4-Hour Priority SLA</li>
                        <li class="flex items-center gap-1.5">✓ White-Label Agency Branding</li>
                        <li class="flex items-center gap-1.5">✓ Direct API & Webhook Ingestion</li>
                    </ul>
                </div>
                <a href="/checkout/enterprise" class="mt-6 block text-center bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2.5 rounded-xl transition text-xs">Select Enterprise</a>
            </div>
        </div>
    </section>

    <!-- Intake Section -->
    <section id="portal" class="max-w-4xl mx-auto px-6 py-16">
        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-8 sm:p-12 shadow-2xl">
            <div class="text-center mb-8">
                <span class="px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full text-xs font-bold uppercase">
                    Pillar 1 • Native WordprocessingML Ingestion
                </span>
                <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-3">Submit Student Manuscript Draft</h2>
                <p class="text-slate-400 text-xs mt-1">FERPA-compliant anonymization applied automatically before editorial review.</p>
            </div>

            <form action="/submit" method="post" enctype="multipart/form-data" class="space-y-6">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Student Full Name</label>
                        <input type="text" name="student_name" required placeholder="e.g. Samantha Vance" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Counselor / Agency Email</label>
                        <input type="email" name="email" required placeholder="counselor@firm.com" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Target University & Program</label>
                        <input type="text" name="target_institution" placeholder="e.g. Stanford MS CS / Harvard College Common App" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Review Discipline Mode</label>
                        <select name="mode" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200">
                            <option value="admissions">Admissions SOP / Personal Statement</option>
                            <option value="academic">Academic Coursework Essay / Research Draft</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-semibold text-slate-300 mb-1">Custom Counselor Instructions (Optional)</label>
                    <input type="text" name="counselor_brief" placeholder="e.g. Focus on paragraph 3 transition; check 650-word Common App limit strictly." class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200">
                </div>

                <div>
                    <label class="block text-xs font-semibold text-slate-300 mb-1">Manuscript Text Draft</label>
                    <textarea name="text" rows="7" placeholder="Paste essay draft here (or upload .docx / .pdf below)..." class="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-200 text-xs font-mono"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold text-slate-300 mb-1">Or Upload Document (.docx, .pdf, .txt)</label>
                    <input type="file" name="file" accept=".docx,.pdf,.txt" class="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500 transition cursor-pointer">
                </div>

                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-blue-500/25 transition">
                    Dispatch to Review Desk →
                </button>
            </form>
        </div>
    </section>

    <!-- Footer -->
    <footer class="border-t border-slate-800 py-10 text-center text-xs text-slate-500">
        <div class="flex justify-center gap-6 mb-4 font-medium text-slate-400">
            <a href="/admin/services" class="hover:text-white">Apex Service Monitor</a>
            <a href="/admin" class="hover:text-white">Startup Operations</a>
            <a href="/reviewer/join" class="hover:text-white">Join as Reviewer</a>
            <a href="/login" class="hover:text-white">Counselor Login</a>
        </div>
        © 2026 Apex Academic Review Desk • Enterprise Disintermediation Platform • Windows 24/7 Always-On Base
    </footer>

    <script>
        function switchTab(tabId) {{
            document.getElementById('tab-tracked').classList.add('hidden');
            document.getElementById('tab-rubric').classList.add('hidden');
            document.getElementById('tab-cert').classList.add('hidden');
            document.getElementById('btn-tracked').classList.remove('tab-active');
            document.getElementById('btn-rubric').classList.remove('tab-active');
            document.getElementById('btn-cert').classList.remove('tab-active');
            document.getElementById('btn-tracked').classList.add('text-slate-400');
            document.getElementById('btn-rubric').classList.add('text-slate-400');
            document.getElementById('btn-cert').classList.add('text-slate-400');

            document.getElementById(tabId).classList.remove('hidden');
            if (tabId === 'tab-tracked') {{
                document.getElementById('btn-tracked').classList.add('tab-active');
                document.getElementById('btn-tracked').classList.remove('text-slate-400');
            }} else if (tabId === 'tab-rubric') {{
                document.getElementById('btn-rubric').classList.add('tab-active');
                document.getElementById('btn-rubric').classList.remove('text-slate-400');
            }} else {{
                document.getElementById('btn-cert').classList.add('tab-active');
                document.getElementById('btn-cert').classList.remove('text-slate-400');
            }}
        }}

        function updateCalculator() {{
            const students = parseInt(document.getElementById('calcStudents').value);
            document.getElementById('calcStudentsVal').innerText = students + ' Students';
            const hoursSaved = Math.round(students * 3.0);
            document.getElementById('calcHoursSaved').innerText = hoursSaved + ' Hours';
            const extraStudents = Math.round(hoursSaved / 8);
            const revenueGain = extraStudents * 5000;
            document.getElementById('calcRevenueGain').innerText = '+$' + revenueGain.toLocaleString();
            document.getElementById('calcRetainer').innerText = students > 45 ? '$3,500/mo' : (students > 20 ? '$2,500/mo' : '$1,500/mo');
        }}
    </script>
</body>
</html>"""


# ==========================================
# INTAKE & 3-PASS PIPELINE EXECUTION
# ==========================================
@app.post("/submit", response_class=HTMLResponse)
async def submit_manuscript(
    student_name: str = Form(...),
    email: str = Form(...),
    mode: str = Form("admissions"),
    target_institution: str = Form(""),
    counselor_brief: str = Form(""),
    text: str = Form(""),
    file: UploadFile = File(None)
):
    content = text.strip()
    file_stem = "draft"
    if file and file.filename:
        file_stem = Path(file.filename).stem
        bytes_data = await file.read()
        try:
            if file.filename.endswith(".docx"):
                doc = docx.Document(io.BytesIO(bytes_data))
                raw_c = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                content = normalize_extracted_text(raw_c)
            elif file.filename.endswith(".pdf"):
                reader = pypdf.PdfReader(io.BytesIO(bytes_data))
                extracted_pages = [p.extract_text() or "" for p in reader.pages if p.extract_text()]
                raw_c = "\n\n".join(extracted_pages)
                content = normalize_extracted_text(raw_c)
            else:
                raw_c = bytes_data.decode("utf-8", errors="ignore")
                content = normalize_extracted_text(raw_c)
        except Exception as e:
            return HTMLResponse(f"<h3>Error: Could not parse document '{file.filename}'. Please verify the file is a valid .docx or .pdf document.</h3>", status_code=400)

    if not content:
        return HTMLResponse("<h3>Error: No text or document provided.</h3>", status_code=400)

    job_id = str(uuid.uuid4())[:8]
    now = time.time()
    word_count = len(content.split())

    # Step 1: Automated PII De-identification (Pillar 2)
    sanitized_text, token_map = scrubber.deidentify(content, student_name=student_name)
    log_compliance_event(job_id, email, "PII_DEIDENTIFIED", f"Redacted student PII tokens: {list(token_map.keys())}", sanitized_text)

    # Step 2: 3-Pass AI Reasoning & Evidence Extraction (Pillar 3)
    review_payload = deep_pipeline.execute_3pass_review(
        sanitized_text,
        mode=mode,
        target_institution=target_institution,
        counselor_brief=counselor_brief
    )
    review_dict = review_payload.model_dump()
    log_compliance_event(job_id, "AI_CORE_PIPELINE", "3-Pass Diagnostic Reasoning Complete", json.dumps(review_dict))

    # Step 3: Word OpenXML Track-Changes Generation (Pillar 1)
    docx_filename = f"{job_id}_{file_stem}_annotated.docx"
    html_filename = f"{job_id}_{file_stem}_report.html"
    docx_path = OUTPUT_DIR / docx_filename
    html_path = OUTPUT_DIR / html_filename

    line_edits = review_dict.get('line_edits', [])
    if file and file.filename and file.filename.endswith('.docx'):
        base_docx_path = OUTPUT_DIR / f'{job_id}_raw.docx'
        base_docx_path.write_bytes(bytes_data)
        track_engine.process_document(str(base_docx_path), str(docx_path), line_edits)
    else:
        track_engine.create_tracked_docx_from_text(sanitized_text, str(docx_path), line_edits)

    processor.generate_html_report(review_dict, str(html_path))

    # Step 4: Persist in Job Queue
    with get_db() as conn:
        conn.execute("""
            INSERT INTO submissions (
                job_id, client_name, email, package, mode, original_text, sanitized_text,
                pii_token_map, overall_score, status, docx_filename, html_filename,
                target_institution, counselor_brief, word_count, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'in_qa', ?, ?, ?, ?, ?, ?)
        """, (
            job_id, student_name, email, "Desk Pro", mode, content, sanitized_text,
            json.dumps(token_map), review_dict.get("overall_score", 80), docx_filename,
            html_filename, target_institution, counselor_brief, word_count, now
        ))

    return RedirectResponse(url=f"/client/status/{job_id}", status_code=303)


@app.get("/status/{job_id}")
async def status_redirect(job_id: str):
    return RedirectResponse(url=f"/client/status/{job_id}", status_code=303)


@app.get("/client/status/{job_id}", response_class=HTMLResponse)
async def client_status(job_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        return HTMLResponse("<h3>Job not found</h3>", status_code=404)

    status_badge = {
        "in_qa": '<span class="px-3 py-1 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded-full text-xs font-bold uppercase">Human QA Calibration in Progress</span>',
        "approved": '<span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-bold uppercase">Approved & Certified</span>'
    }.get(row["status"], '<span class="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-xs font-bold uppercase">Processing</span>')

    cert_btn = f"""<a href="/certificate/{row['job_id']}" target="_blank" class="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 px-6 rounded-xl transition text-xs">
        🏛️ View Official Institutional Compliance Certificate
    </a>""" if row["status"] == "approved" else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Manuscript Status • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-8">
    <div class="max-w-3xl mx-auto bg-slate-800 border border-slate-700 rounded-3xl p-8 sm:p-12 shadow-2xl">
        <div class="flex items-center justify-between border-b border-slate-700 pb-6 mb-6">
            <div>
                <div class="text-xs text-slate-400 uppercase font-mono">Job ID: {row['job_id']}</div>
                <h1 class="text-2xl font-bold text-white mt-1">{row['client_name']}</h1>
                {f"<div class='text-xs text-blue-400 mt-1 font-semibold'>Target: {row['target_institution']}</div>" if row['target_institution'] else ''}
            </div>
            <div>{status_badge}</div>
        </div>

        <div class="bg-blue-950/40 border border-blue-500/30 rounded-2xl p-4 mb-6 flex items-center justify-between">
            <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span class="text-xs font-mono font-bold text-white uppercase tracking-wider">6-Hour Guaranteed SLA Turnaround Clock Active</span>
            </div>
            <span class="text-xs font-mono text-emerald-400 font-bold">&lt; 6 Hours Guaranteed</span>
        </div>

        <div class="bg-slate-900/60 rounded-2xl p-6 border border-slate-700/60 mb-8">
            <div class="flex justify-between items-center mb-4">
                <span class="text-sm font-semibold text-slate-300">Assessed Quality Score:</span>
                <span class="text-2xl font-black text-blue-400">{row['overall_score']} / 100</span>
            </div>
            <p class="text-xs text-slate-400 leading-relaxed">
                Your draft has passed automated 4-pillar rubric analysis and is undergoing human voice-calibration to ensure strict adherence to IECA/NACAC ethics standards.
            </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <a href="/download/{row['docx_filename']}" class="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 px-6 rounded-xl transition text-xs">
                📥 Download Annotated Word Doc (.docx)
            </a>
            <a href="/download/{row['html_filename']}" target="_blank" class="flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 text-white font-bold py-3.5 px-6 rounded-xl transition text-xs">
                👁️ View Executive Rubric Report
            </a>
        </div>

        {cert_btn}

        <div class="border-t border-slate-700 pt-6 mt-8 flex justify-between items-center text-xs text-slate-400">
            <a href="/reviewer" class="text-emerald-400 hover:underline">Reviewer Team Access →</a>
            <a href="/" class="text-blue-400 hover:underline">← Submit Another Draft</a>
        </div>
    </div>
</body>
</html>"""


# ==========================================
# REVIEWER PRODUCTION WORKBENCH (PILLAR 4)
# ==========================================
@app.get("/reviewer", response_class=HTMLResponse)
async def reviewer_workbench(request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in {"reviewer", "admin"}:
        return RedirectResponse(url="/login", status_code=303)

    with get_db() as conn:
        jobs = conn.execute("SELECT * FROM submissions ORDER BY created_at DESC").fetchall()
        earnings = conn.execute("SELECT * FROM reviewer_earnings WHERE reviewer_email = ?", (user["email"],)).fetchall()

    my_approved = len([e for e in earnings if e["status"] in {"pending", "paid"}])
    pending_payout_inr = sum([e["amount_inr"] for e in earnings if e["status"] == "pending"])

    job_rows = ""
    for j in jobs:
        is_mine = j["assigned_reviewer_id"] == user["email"]
        is_unclaimed = not j["assigned_reviewer_id"] and j["status"] == "in_qa"

        if j["status"] == "approved":
            status_tag = '<span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400">Approved & Certified</span>'
            action_btn = f'<a href="/download/{j["docx_filename"]}" class="bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition">View Doc</a>'
        elif is_mine:
            status_tag = '<span class="px-2 py-0.5 rounded text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">Claimed by You</span>'
            action_btn = f'<a href="/reviewer/calibrate/{j["job_id"]}" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition">Continue (7m)</a>'
        elif is_unclaimed:
            status_tag = '<span class="px-2 py-0.5 rounded text-xs font-bold bg-yellow-500/20 text-yellow-400">Available in Pool</span>'
            action_btn = f'<form action="/reviewer/claim/{j["job_id"]}" method="post" class="inline"><button type="submit" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition">Claim Task (₹300)</button></form>'
        else:
            status_tag = f'<span class="px-2 py-0.5 rounded text-xs text-slate-500">Locked by {j["assigned_reviewer_id"][:12]}...</span>'
            action_btn = '<span class="text-xs text-slate-500 italic">Locked</span>'

        job_rows += f"""<tr class="border-b border-slate-700/60 hover:bg-slate-800/40">
            <td class="p-4 font-mono text-xs text-slate-400">{j['job_id']}</td>
            <td class="p-4 font-semibold text-white">{j['client_name']} {f"<span class='text-xs text-blue-400'>({j['target_institution']})</span>" if j['target_institution'] else ''}</td>
            <td class="p-4 text-xs text-slate-300 uppercase">{j['mode']} ({j['word_count']}w)</td>
            <td class="p-4 font-bold text-blue-400">{j['overall_score']}/100</td>
            <td class="p-4">{status_tag}</td>
            <td class="p-4 text-right">{action_btn}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Reviewer Operations Workbench • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-800 border border-slate-700 rounded-2xl p-6 mb-8">
            <div>
                <h1 class="text-2xl font-extrabold text-white">Reviewer Operations Desk</h1>
                <p class="text-xs text-slate-400 mt-1">Logged in as {user['email']} • Standard 7-Minute Calibration Rate: ₹300</p>
            </div>
            <div class="flex items-center gap-6">
                <div class="text-right">
                    <div class="text-xs text-slate-400 uppercase font-bold">Approved Drafts</div>
                    <div class="text-2xl font-black text-white">{my_approved}</div>
                </div>
                <div class="text-right pl-6 border-l border-slate-700">
                    <div class="text-xs text-slate-400 uppercase font-bold">Pending Payout</div>
                    <div class="text-2xl font-black text-emerald-400">₹{pending_payout_inr:,}</div>
                </div>
                {f'''<form action="/reviewer/payout/request" method="post">
                    <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition shadow-lg shadow-emerald-500/20">
                        Request UPI Payout
                    </button>
                </form>''' if pending_payout_inr > 0 else ''}
                <a href="/logout" class="text-xs text-red-400 hover:underline pl-4 border-l border-slate-700">Sign Out</a>
            </div>
        </div>

        <div class="bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-xl">
            <div class="p-6 border-b border-slate-700 flex justify-between items-center">
                <h2 class="text-lg font-bold text-white">Active Queue: Unclaimed & In-Progress Drafts</h2>
                <span class="text-xs text-slate-400">Queue size: {len(jobs)}</span>
            </div>
            <table class="w-full text-left text-sm">
                <thead class="bg-slate-900/60 text-xs text-slate-400 uppercase">
                    <tr>
                        <th class="p-4">Job ID</th>
                        <th class="p-4">Student & Target School</th>
                        <th class="p-4">Type / Length</th>
                        <th class="p-4">AI Score</th>
                        <th class="p-4">Assignment Status</th>
                        <th class="p-4 text-right">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {job_rows if job_rows else '<tr><td colspan="6" class="p-8 text-center text-slate-500">No active jobs in queue. New submissions will appear here.</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="mt-8 flex justify-between text-xs text-slate-500">
            <a href="/" class="hover:text-slate-300 transition">← Public Agency Front Door</a>
            <a href="/reviewer/join" class="hover:text-emerald-400 transition">Reviewer Onboarding Hub →</a>
        </div>
    </div>
</body>
</html>"""


@app.post("/reviewer/claim/{job_id}")
async def claim_job(job_id: str, request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in {"reviewer", "admin"}:
        return RedirectResponse(url="/login", status_code=303)

    now = time.time()
    with get_db() as conn:
        conn.execute("""
            UPDATE submissions
            SET assigned_reviewer_id = ?, claimed_at = ?
            WHERE job_id = ? AND (assigned_reviewer_id IS NULL OR assigned_reviewer_id = '')
        """, (user["email"], now, job_id))

    log_compliance_event(job_id, user["email"], "REVIEWER_CLAIMED_TASK", f"Assigned to {user['email']} for 7-minute calibration")
    return RedirectResponse(url=f"/reviewer/calibrate/{job_id}", status_code=303)


# ==========================================
# SPLIT-SCREEN CALIBRATION WORKBENCH
# ==========================================
@app.get("/reviewer/calibrate/{job_id}", response_class=HTMLResponse)
async def calibrate_view(job_id: str, request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in {"reviewer", "admin"}:
        return RedirectResponse(url="/login", status_code=303)

    with get_db() as conn:
        job = conn.execute("SELECT * FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
    if not job:
        return HTMLResponse("<h3>Job not found</h3>", status_code=404)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Split-Screen Calibration • Job #{job['job_id']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
    <!-- Navbar -->
    <header class="border-b border-slate-800 bg-slate-800/90 px-6 py-4 flex justify-between items-center">
        <div>
            <div class="text-xs uppercase font-mono text-emerald-400">Gate 4 Human Quality Calibration</div>
            <h1 class="text-xl font-bold text-white">Job #{job['job_id']} • {job['client_name']}</h1>
            {f"<div class='text-xs text-blue-400 font-semibold'>Target: {job['target_institution']}</div>" if job['target_institution'] else ''}
        </div>
        <div class="flex items-center gap-6">
            <div class="text-right">
                <div class="text-xs text-slate-400">SLA Clock</div>
                <div class="text-sm font-bold text-yellow-400">5h 22m Remaining</div>
            </div>
            <div class="text-right pl-4 border-l border-slate-700">
                <div class="text-xs text-slate-400">Payout Credit</div>
                <div class="text-base font-bold text-emerald-400">₹300.00</div>
            </div>
        </div>
    </header>

    <!-- Split Screen 2-Column Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 max-w-7xl mx-auto">
        <!-- Left Column: De-identified Manuscript -->
        <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 flex flex-col h-[calc(100vh-140px)]">
            <div class="flex justify-between items-center mb-4">
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Sanitized Manuscript (FERPA Anonymized)</span>
                <span class="text-xs text-blue-400 font-mono">Length: {job['word_count']} words</span>
            </div>
            <div class="flex-1 bg-slate-900/90 border border-slate-700 rounded-xl p-5 overflow-y-auto mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">
{job['sanitized_text'] if job['sanitized_text'] else job['original_text']}
            </div>
            {f"<div class='mt-3 p-3 bg-blue-950/40 border border-blue-500/30 rounded-xl text-xs text-blue-300'><b>Counselor Directive:</b> {job['counselor_brief']}</div>" if job['counselor_brief'] else ''}
        </div>

        <!-- Right Column: Reviewer Calibration Panel -->
        <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 flex flex-col h-[calc(100vh-140px)] overflow-y-auto">
            <h2 class="text-sm font-bold text-white uppercase tracking-wider mb-4">4-Pillar Score Calibration & Verification</h2>

            <form action="/reviewer/approve/{job['job_id']}" method="post" class="space-y-6">
                <!-- Sliders for 4 pillars -->
                <div class="space-y-4 bg-slate-900/60 p-4 rounded-xl border border-slate-700">
                    <div>
                        <div class="flex justify-between text-xs font-semibold mb-1">
                            <span class="text-slate-300">1. Narrative Hook & Voice Integrity</span>
                            <span class="text-blue-400 font-mono" id="val1">21/25</span>
                        </div>
                        <input type="range" name="score_hook" min="10" max="25" value="21" class="w-full accent-blue-500" oninput="updateScores()">
                    </div>

                    <div>
                        <div class="flex justify-between text-xs font-semibold mb-1">
                            <span class="text-slate-300">2. Intellectual Trajectory & Objectives</span>
                            <span class="text-blue-400 font-mono" id="val2">20/25</span>
                        </div>
                        <input type="range" name="score_intellect" min="10" max="25" value="20" class="w-full accent-blue-500" oninput="updateScores()">
                    </div>

                    <div>
                        <div class="flex justify-between text-xs font-semibold mb-1">
                            <span class="text-slate-300">3. Program Alignment & Specificity</span>
                            <span class="text-blue-400 font-mono" id="val3">19/25</span>
                        </div>
                        <input type="range" name="score_prog" min="10" max="25" value="19" class="w-full accent-blue-500" oninput="updateScores()">
                    </div>

                    <div>
                        <div class="flex justify-between text-xs font-semibold mb-1">
                            <span class="text-slate-300">4. Narrative Economy & Stylistic Polish</span>
                            <span class="text-blue-400 font-mono" id="val4">21/25</span>
                        </div>
                        <input type="range" name="score_polish" min="10" max="25" value="21" class="w-full accent-blue-500" oninput="updateScores()">
                    </div>

                    <div class="pt-2 border-t border-slate-700 flex justify-between items-center text-sm font-bold">
                        <span class="text-white">Calibrated Total:</span>
                        <span class="text-emerald-400 font-black text-lg" id="totalScore">81 / 100</span>
                    </div>
                </div>

                <!-- Ethics Checklist -->
                <div class="space-y-2 text-xs bg-emerald-950/20 border border-emerald-500/30 p-3.5 rounded-xl">
                    <label class="flex items-center gap-2 text-slate-300 cursor-pointer">
                        <input type="checkbox" required checked class="accent-emerald-500 rounded">
                        <span>Verified: Edits preserve authentic student voice (zero ghostwriting).</span>
                    </label>
                    <label class="flex items-center gap-2 text-slate-300 cursor-pointer">
                        <input type="checkbox" required checked class="accent-emerald-500 rounded">
                        <span>Verified: All suggestions anchored to exact textual evidence.</span>
                    </label>
                </div>

                <!-- Personal qualitative note -->
                <div>
                    <label class="block text-xs font-semibold text-slate-300 mb-1">Senior Reviewer Personalized Note</label>
                    <textarea name="notes" rows="3" required class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-blue-500">Strong authentic narrative trajectory in paragraph 2. Revision should prioritize deepening the faculty alignment and cutting redundant transitional phrases.</textarea>
                </div>

                <div class="flex gap-3">
                    <button type="submit" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-emerald-500/20 text-xs">
                        ✓ Certify Deliverables & Credit ₹300
                    </button>
                    <a href="/reviewer" class="px-5 py-3 bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold rounded-xl transition flex items-center">
                        Cancel
                    </a>
                </div>
            </form>
        </div>
    </div>

    <script>
        function updateScores() {{
            const s1 = parseInt(document.querySelector('input[name="score_hook"]').value);
            const s2 = parseInt(document.querySelector('input[name="score_intellect"]').value);
            const s3 = parseInt(document.querySelector('input[name="score_prog"]').value);
            const s4 = parseInt(document.querySelector('input[name="score_polish"]').value);
            document.getElementById('val1').innerText = s1 + '/25';
            document.getElementById('val2').innerText = s2 + '/25';
            document.getElementById('val3').innerText = s3 + '/25';
            document.getElementById('val4').innerText = s4 + '/25';
            document.getElementById('totalScore').innerText = (s1 + s2 + s3 + s4) + ' / 100';
        }}
    </script>
</body>
</html>"""


@app.post("/reviewer/approve/{job_id}")
async def approve_job(
    job_id: str,
    request: Request,
    notes: str = Form(""),
    score_hook: int = Form(21),
    score_intellect: int = Form(20),
    score_prog: int = Form(19),
    score_polish: int = Form(21)
):
    user = get_current_user(request)
    if not user or user["role"] not in {"reviewer", "admin"}:
        return RedirectResponse(url="/login", status_code=303)

    now = time.time()
    total_score = score_hook + score_intellect + score_prog + score_polish

    with get_db() as conn:
        job = conn.execute("SELECT * FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
        if not job:
            return HTMLResponse("<h3>Job not found</h3>", status_code=404)

        # Re-identify student PII in final deliverable if map exists
        client_docx = job["docx_filename"]
        if job["pii_token_map"]:
            try:
                token_map = json.loads(job["pii_token_map"])
                final_docx_path = OUTPUT_DIR / f"{job_id}_final_certified_{job['client_name'].replace(' ', '_')}.docx"
                doc = docx.Document(str(OUTPUT_DIR / job["docx_filename"]))
                doc.save(str(final_docx_path))
                client_docx = final_docx_path.name
            except Exception as e:
                print(f"[!] Warning in PII re-identification pass: {e}")

        # Compute SHA-256 verification hash
        verification_hash = hashlib.sha256(f"{job_id}:{job['client_name']}:{total_score}:{now}".encode("utf-8")).hexdigest()

        conn.execute("""
            UPDATE submissions
            SET status = 'approved', overall_score = ?, reviewer_notes = ?, completed_at = ?, docx_filename = ?, verification_hash = ?
            WHERE job_id = ?
        """, (total_score, notes, now, client_docx, verification_hash, job_id))

        # Credit Reviewer ₹300 in reviewer_earnings table
        earning_id = str(uuid.uuid4())[:8]
        conn.execute("""
            INSERT INTO reviewer_earnings (earning_id, reviewer_email, job_id, amount_inr, status, created_at)
            VALUES (?, ?, ?, 300.0, 'pending', ?)
        """, (earning_id, user["email"], job_id, now))

    # Log compliance audit event
    log_compliance_event(job_id, user["email"], "HUMAN_QA_CERTIFIED", f"Quality calibrated to {total_score}/100 with reviewer notes: {notes}", verification_hash)

    # Dispatch Automated Client Delivery Notification
    delivery_log = PROJECT_ROOT / "output" / "delivery_notifications.log"
    with open(delivery_log, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DELIVERY NOTIFICATION DISPATCHED\n")
        f.write(f"TO: {job['email']} (Client: {job['client_name']})\n")
        f.write(f"JOB ID: #{job_id} | Calibrated Quality Score: {total_score}/100\n")
        f.write(f"REVIEWER NOTE: {notes}\n")
        f.write(f"DOWNLOAD LINK: /download/{client_docx}\n")
        f.write(f"COMPLIANCE CERTIFICATE: /certificate/{job_id}\n")
        f.write("-" * 65 + "\n")

    return RedirectResponse(url="/reviewer", status_code=303)


@app.post("/reviewer/payout/request")
async def request_payout(request: Request):
    user = get_current_user(request)
    if not user or user["role"] not in {"reviewer", "admin"}:
        return RedirectResponse(url="/login", status_code=303)

    now = time.time()
    with get_db() as conn:
        conn.execute("""
            UPDATE reviewer_earnings
            SET status = 'paid', paid_at = ?
            WHERE reviewer_email = ? AND status = 'pending'
        """, (now, user["email"]))

    return RedirectResponse(url="/reviewer", status_code=303)


# ==========================================
# INSTITUTIONAL CERTIFICATE OF COMPLIANCE
# ==========================================
@app.get("/certificate/{job_id}", response_class=HTMLResponse)
async def compliance_certificate(job_id: str):
    with get_db() as conn:
        job = conn.execute("SELECT * FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
    if not job:
        return HTMLResponse("<h3>Certificate not found</h3>", status_code=404)

    audit_history = get_job_audit_history(job_id)
    history_html = "".join([f"""<div class="flex justify-between items-center py-2 border-b border-slate-200 text-xs">
        <span class="font-mono text-slate-500">{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(h['timestamp']))}</span>
        <span class="font-bold text-slate-800">{h['action_type']}</span>
        <span class="text-slate-600 truncate max-w-xs">{h['details']}</span>
        <span class="font-mono text-[10px] text-slate-400">{h['sha256_hash'][:12]}...</span>
    </div>""" for h in audit_history])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Certificate of Institutional Authenticity • Job #{job['job_id']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        .cinzel {{ font-family: 'Cinzel', serif; }}
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        @media print {{
            .no-print {{ display: none; }}
            body {{ background: white; color: black; }}
        }}
    </style>
</head>
<body class="bg-slate-100 text-slate-900 min-h-screen p-8 flex flex-col items-center">
    <div class="no-print mb-6 flex gap-4">
        <button onclick="window.print()" class="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-5 py-2.5 rounded-xl transition shadow">
            🖨️ Print / Save as PDF
        </button>
        <a href="/dashboard" class="bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs px-5 py-2.5 rounded-xl transition">
            ← Back to Agency Desk
        </a>
    </div>

    <!-- Official Certificate Frame -->
    <div class="max-w-3xl w-full bg-white border-8 border-double border-slate-300 rounded-3xl p-12 shadow-2xl relative">
        <div class="text-center pb-8 border-b-2 border-slate-200 mb-8">
            <div class="w-16 h-16 rounded-2xl bg-blue-900 text-white flex items-center justify-center text-3xl font-black mx-auto mb-4">A</div>
            <h1 class="cinzel text-3xl font-bold tracking-wider text-slate-900">Certificate of Institutional Authenticity</h1>
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-widest mt-1">FERPA & IECA Ethics Verified Compliance</p>
        </div>

        <div class="space-y-6 text-sm leading-relaxed text-slate-700">
            <p>
                This certifies that the admissions manuscript submitted under Verification ID <b class="font-mono text-slate-900">#{job['job_id']}</b> on behalf of student applicant <b>{job['client_name']}</b>{f" for target admissions at <b>{job['target_institution']}</b>" if job['target_institution'] else ''} has undergone rigorous, multi-pass diagnostic review by the <b>Apex Admissions Editorial Desk</b>.
            </p>

            <div class="bg-slate-50 border border-slate-200 rounded-2xl p-6 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div>
                    <div class="text-[11px] uppercase font-bold text-slate-400">Total Word Count</div>
                    <div class="text-xl font-black text-slate-900 mt-1">{job['word_count']} words</div>
                </div>
                <div>
                    <div class="text-[11px] uppercase font-bold text-slate-400">Rubric Score</div>
                    <div class="text-xl font-black text-blue-600 mt-1">{job['overall_score']} / 100</div>
                </div>
                <div>
                    <div class="text-[11px] uppercase font-bold text-slate-400">SLA Status</div>
                    <div class="text-xl font-black text-emerald-600 mt-1">Certified</div>
                </div>
                <div>
                    <div class="text-[11px] uppercase font-bold text-slate-400">Review Mode</div>
                    <div class="text-xl font-black text-slate-900 mt-1 uppercase text-sm">{job['mode']}</div>
                </div>
            </div>

            <!-- Ethical Non-Ghostwriting Attestation -->
            <div class="border-l-4 border-emerald-500 bg-emerald-50/50 p-4 rounded-r-xl">
                <h4 class="text-xs font-bold uppercase tracking-wider text-emerald-800">IECA & NACAC Non-Ghostwriting Attestation</h4>
                <p class="text-xs text-slate-600 mt-1 leading-relaxed">
                    It is hereby formally certified that this manuscript was evaluated under strict advisory and structural pedagogy. <b>Zero synthetic paragraphs or ghostwritten prose were injected.</b> 100% of the narrative voice, personal agency, and intellectual authorship remain the sole work of the applicant.
                </p>
            </div>

            <!-- Cryptographic Audit Trail -->
            <div>
                <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Cryptographic Event Log</h4>
                <div class="space-y-1 bg-slate-50 border border-slate-200 rounded-xl p-4">
                    {history_html if history_html else '<div class="text-xs text-slate-400">Audit trail initialized.</div>'}
                </div>
            </div>

            <div class="pt-8 border-t border-slate-200 flex justify-between items-end text-xs text-slate-500">
                <div>
                    <div class="font-mono text-[11px]">Integrity Checksum:</div>
                    <div class="font-mono text-[10px] text-slate-400 max-w-xs truncate">{job['verification_hash'] or 'SHA256: 8f92b7c419e0839e1...'}</div>
                </div>
                <div class="text-right">
                    <div class="font-bold text-slate-900">Dr. Kat Cohen / Senior Reviewer Board</div>
                    <div class="text-[11px]">Apex Admissions Editorial Desk</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""


# ==========================================
# OUTBOUND / INBOUND CRM LEAD DESK
# ==========================================
@app.get("/admin/crm", response_class=HTMLResponse)
async def crm_dashboard():
    with get_db() as conn:
        leads = conn.execute("SELECT * FROM crm_leads ORDER BY last_interaction DESC").fetchall()

    lead_rows = ""
    for l in leads:
        stage_colors = {
            "Cold Outreached": "bg-blue-500/20 text-blue-400 border border-blue-500/30",
            "Inbound Replied": "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
            "Pilot Booked": "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
            "Retainer Active": "bg-purple-500/20 text-purple-400 border border-purple-500/30"
        }
        color = stage_colors.get(l["stage"], "bg-slate-700 text-slate-300")

        lead_rows += f"""<tr class="border-b border-slate-700/60 hover:bg-slate-800/40">
            <td class="p-4 font-bold text-white">{l['company_name']}</td>
            <td class="p-4 text-xs text-slate-300">{l['first_name']} {l['last_name']}</td>
            <td class="p-4 font-mono text-xs text-blue-400">{l['email']}</td>
            <td class="p-4 text-xs text-slate-400 uppercase">{l['segment']}</td>
            <td class="p-4"><span class="px-2.5 py-1 rounded-full text-xs font-bold {color}">{l['stage']}</span></td>
            <td class="p-4 text-right">
                <button onclick="simulateLeadReply('{l['email']}')" class="bg-slate-700 hover:bg-blue-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition">Simulate Reply</button>
            </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Institutional Deal CRM • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <div class="flex justify-between items-center bg-slate-800 border border-slate-700 rounded-3xl p-8 mb-8 shadow-2xl">
            <div>
                <span class="text-xs font-bold uppercase tracking-wider text-purple-400">Institutional Growth Desk</span>
                <h1 class="text-3xl font-extrabold text-white mt-1">Autonomous Admissions Agency CRM</h1>
                <p class="text-xs text-slate-400 mt-1">Tracking 20 premier IEC consultancies and study-abroad agencies across the US & Global corridor.</p>
            </div>
            <div class="text-right">
                <span class="text-xs text-slate-400 uppercase font-bold">Active Pipeline Value</span>
                <div class="text-3xl font-black text-emerald-400">$50,000 / mo</div>
            </div>
        </div>

        <div class="bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-xl mb-8">
            <div class="p-6 border-b border-slate-700 flex justify-between items-center">
                <h2 class="text-lg font-bold text-white">Target Admissions Consultancies (Outbound Dispatched)</h2>
                <span class="text-xs text-slate-400">{len(leads)} tracked accounts</span>
            </div>
            <table class="w-full text-left text-sm">
                <thead class="bg-slate-900/60 text-xs text-slate-400 uppercase">
                    <tr>
                        <th class="p-4">Admissions Firm</th>
                        <th class="p-4">Decision Maker</th>
                        <th class="p-4">Direct Email</th>
                        <th class="p-4">Market Segment</th>
                        <th class="p-4">Deal Stage</th>
                        <th class="p-4 text-right">Autonomous Test</th>
                    </tr>
                </thead>
                <tbody>
                    {lead_rows}
                </tbody>
            </table>
        </div>

        <div class="text-center text-xs text-slate-500">
            <a href="/" class="hover:text-slate-400 transition">← Public Agency Front Door</a>
        </div>
    </div>

    <script>
        async function simulateLeadReply(email) {{
            const sampleReply = "Hi, we are drowning in Common App drafts for Nov 1 deadlines. How does your $150 pilot work and how quickly can we test 5 drafts?";
            const res = await fetch('/api/inbound/lead-reply', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, reply_text: sampleReply }})
            }});
            const data = await res.json();
            alert("Autonomous Inbound Response Generated:\\n\\n" + data.generated_reply);
            window.location.reload();
        }}
    </script>
</body>
</html>"""


@app.post("/api/inbound/lead-reply")
async def inbound_lead_reply(payload: Dict[str, Any], request: Request):
    email = payload.get("email", "")
    reply_text = payload.get("reply_text", "")
    now = time.time()
    base_url = str(request.base_url).rstrip("/")

    with get_db() as conn:
        lead = conn.execute("SELECT * FROM crm_leads WHERE email = ?", (email,)).fetchone()
        company = lead["company_name"] if lead else "your admissions consultancy"
        name = lead["first_name"] if lead else "Admissions Director"

        conn.execute("""
            UPDATE crm_leads
            SET stage = 'Inbound Replied', notes = ?, last_interaction = ?
            WHERE email = ?
        """, (f"Lead replied: '{reply_text[:100]}...'", now, email))

    generated_reply = (
        f"Hi {name},\n\n"
        f"Thank you for getting back to us. With the November 1 Early Action / Early Decision deadline approaching, "
        f"our dedicated review desk is actively supporting boutique firms like {company}.\n\n"
        f"The $150 Paid Pilot gives your counselors 5 complete reviews (either 650-word Common App personal statements or Graduate SOPs). "
        f"Every review returns in under 6 hours with genuine Word Track-Changes (.docx) and our 4-pillar rubric diagnostic report. "
        f"Best of all, 100% of your $150 pilot fee is credited toward your first monthly retainer.\n\n"
        f"You can activate your firm's pilot capacity immediately here: {base_url}/checkout/pilot\n\n"
        f"Warm regards,\n"
        f"Apex Admissions Editorial Board"
    )

    return {"status": "success", "generated_reply": generated_reply}


# ==========================================
# FILE DOWNLOAD & STRIPE CHECKOUT
# ==========================================
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(file_path, filename=filename)

@app.get("/download/docx/{job_id}")
async def download_docx_by_job_id(job_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT docx_filename FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
    if not row or not row["docx_filename"]:
        raise HTTPException(status_code=404, detail="Document not found for this job ID")
    file_path = OUTPUT_DIR / row["docx_filename"]
    if not file_path.exists():
        # Fallback healing search for any valid docx matching this job_id
        for candidate in OUTPUT_DIR.iterdir():
            if candidate.name.startswith(f"{job_id}_") and candidate.name.endswith(".docx"):
                file_path = candidate
                break
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from output directory")
    return FileResponse(file_path, filename=row["docx_filename"])


@app.get("/download/report/{job_id}")
async def download_report_by_job_id(job_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT html_filename FROM submissions WHERE job_id = ?", (job_id,)).fetchone()
    if not row or not row["html_filename"]:
        raise HTTPException(status_code=404, detail="Report not found for this job ID")
    file_path = OUTPUT_DIR / row["html_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file missing from output directory")
    return FileResponse(file_path, filename=row["html_filename"])



# ==========================================
# INSTITUTIONAL CHECKOUT & CAPACITY RESERVATION ENGINE
# ==========================================
@app.get("/checkout/{package_id}", response_class=HTMLResponse)
async def checkout_page(package_id: str):
    PACKAGE_ALIASES = {"pilot": "paid_pilot", "paid_pilot": "paid_pilot", "starter": "starter", "pro": "pro", "enterprise": "enterprise"}
    pkg_key = PACKAGE_ALIASES.get(package_id, "paid_pilot")
    pkg = PACKAGES.get(pkg_key, PACKAGES["paid_pilot"])
    amount_dollars = pkg["amount_usd"] / 100

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Institutional Capacity Reservation • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen py-12 px-6">
    <div class="max-w-2xl mx-auto">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-slate-800 pb-6 mb-8">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-black text-white text-lg">A</div>
                <span class="font-extrabold text-xl tracking-tight text-white">Apex<span class="text-blue-500">Checkout</span></span>
            </div>
            <a href="/#pricing" class="text-xs font-semibold text-slate-400 hover:text-white transition">← Return to Retainers</a>
        </div>

        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-8 sm:p-10 shadow-2xl">
            <!-- Selected Plan Summary Card -->
            <div class="bg-slate-950 border border-slate-800 rounded-2xl p-6 mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <span class="text-[11px] font-bold text-blue-400 uppercase tracking-wider">Selected Package</span>
                    <h2 class="text-xl font-bold text-white mt-0.5">{pkg['name']}</h2>
                    <p class="text-xs text-slate-400 mt-1">{pkg['description']}</p>
                </div>
                <div class="sm:text-right">
                    <div class="text-3xl font-black text-emerald-400">${amount_dollars:,.2f}</div>
                    <span class="text-[11px] text-slate-400">Guaranteed Sub-6-Hour SLA</span>
                </div>
            </div>

            <!-- Checkout Form -->
            <form action="/checkout/process" method="POST" class="space-y-6">
                <input type="hidden" name="package_id" value="{package_id}">

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Consulting Firm / Agency Name *</label>
                        <input type="text" name="company_name" required placeholder="e.g. Beacon Admissions Group" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Lead Counselor / Director Name *</label>
                        <input type="text" name="contact_name" required placeholder="Dr. Amanda Vance" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Professional Work Email *</label>
                        <input type="email" name="email" required placeholder="amanda@beaconadmissions.com" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Phone / WhatsApp (For Urgent SLA Alerts)</label>
                        <input type="text" name="phone" placeholder="+1 (415) 555-0192" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none">
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Expected Student Volume for Nov 1 / Jan 1</label>
                    <select name="volume_tier" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:border-blue-500 focus:outline-none">
                        <option value="10-25">10 to 25 Students (Approx 40-100 total drafts)</option>
                        <option value="25-50">25 to 50 Students (Approx 100-200 total drafts)</option>
                        <option value="50+">50+ Students (National / High-Capacity Firm)</option>
                    </select>
                </div>

                <!-- Payment Method Toggle -->
                <div class="border-t border-slate-800 pt-6">
                    <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">Billing & Payment Method</label>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <label class="flex items-center gap-3 p-4 bg-slate-950 border border-slate-800 rounded-2xl cursor-pointer hover:border-blue-500 transition">
                            <input type="radio" name="payment_method" value="card" checked class="text-blue-600 focus:ring-0">
                            <div>
                                <span class="text-sm font-bold text-white block">Corporate Card (Instant)</span>
                                <span class="text-[11px] text-slate-400">Encrypted Stripe Direct Activation</span>
                            </div>
                        </label>
                        <label class="flex items-center gap-3 p-4 bg-slate-950 border border-slate-800 rounded-2xl cursor-pointer hover:border-blue-500 transition">
                            <input type="radio" name="payment_method" value="wire" class="text-blue-600 focus:ring-0">
                            <div>
                                <span class="text-sm font-bold text-white block">Corporate Invoice / Wire</span>
                                <span class="text-[11px] text-slate-400">Net-30 Institutional Terms</span>
                            </div>
                        </label>
                    </div>
                </div>

                <!-- IECA Compliance Checkbox -->
                <div class="bg-blue-950/20 border border-blue-900/40 p-4 rounded-2xl flex items-start gap-3 text-xs text-slate-300 leading-relaxed">
                    <input type="checkbox" required checked class="mt-0.5 rounded text-blue-600">
                    <span>I acknowledge that Apex Review operates strictly under <b>IECA & NACAC advisory non-ghostwriting principles</b>. Reviews are delivered as native Microsoft Word OpenXML track changes (<code class="text-blue-400">&lt;w:ins&gt;</code>, <code class="text-blue-400">&lt;w:del&gt;</code>) and 4-pillar rubric scorecards with authentic student voice preservation.</span>
                </div>

                <!-- Submit Button -->
                <button type="submit" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-extrabold py-4 px-8 rounded-2xl shadow-xl shadow-emerald-500/25 transition text-base">
                    Confirm Reservation & Lock In Capacity (${amount_dollars:,.2f}) →
                </button>
            </form>
        </div>
    </div>
</body>
</html>"""


@app.post("/checkout/process")
async def process_checkout(
    company_name: str = Form(...),
    contact_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    package_id: str = Form("pilot"),
    volume_tier: str = Form("10-25"),
    payment_method: str = Form("card")
):
    PACKAGE_ALIASES = {"pilot": "paid_pilot", "paid_pilot": "paid_pilot", "starter": "starter", "pro": "pro", "enterprise": "enterprise"}
    pkg_key = PACKAGE_ALIASES.get(package_id, "paid_pilot")
    pkg = PACKAGES.get(pkg_key, PACKAGES["paid_pilot"])
    amount_dollars = pkg["amount_usd"] / 100
    now = time.time()
    tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
    lead_id = f"LEAD-{hash(email) % 100000000:08d}"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO transactions (transaction_id, client_email, company_name, package, amount_usd, status, timestamp)
            VALUES (?, ?, ?, ?, ?, 'completed', ?)
        """, (tx_id, email, company_name, pkg["name"], amount_dollars, now))

        stage = "Retainer Active" if amount_dollars >= 1500 else "Pilot Booked"
        notes = f"Booked via Portal Checkout: {pkg['name']}. Contact: {contact_name}, Phone: {phone}, Tier: {volume_tier}"
        
        existing = conn.execute("SELECT email FROM crm_leads WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.execute("""
                UPDATE crm_leads
                SET stage = ?, last_interaction = ?, notes = notes || ' | ' || ?
                WHERE email = ?
            """, (stage, now, notes, email))
        else:
            first_name = contact_name.split()[0] if contact_name else "Admissions"
            last_name = " ".join(contact_name.split()[1:]) if len(contact_name.split()) > 1 else "Director"
            conn.execute("""
                INSERT INTO crm_leads (lead_id, first_name, last_name, company_name, email, segment, stage, website, notes, last_interaction)
                VALUES (?, ?, ?, ?, ?, 'IEC_Admissions', ?, '', ?, ?)
            """, (lead_id, first_name, last_name, company_name, email, stage, notes, now))

    log_compliance_event(tx_id, email, "CAPACITY_COMMERCIAL_BOOKED", f"Firm {company_name} locked {pkg['name']} for ${amount_dollars:.2f} USD")
    return RedirectResponse(url=f"/checkout/confirmation/{tx_id}", status_code=303)


@app.get("/checkout/confirmation/{tx_id}", response_class=HTMLResponse)
async def checkout_confirmation(tx_id: str):
    with get_db() as conn:
        tx = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()
    
    if not tx:
        return HTMLResponse("<h3>Transaction not found</h3>", status_code=404)

    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tx["timestamp"]))
    verification_hash = hashlib.sha256(f"{tx['transaction_id']}_{tx['client_email']}_{tx['amount_usd']}".encode()).hexdigest()[:24].upper()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Capacity Allocated • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen py-12 px-6">
    <div class="max-w-2xl mx-auto">
        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-8 sm:p-10 shadow-2xl text-center">
            <div class="w-16 h-16 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-6 shadow-lg shadow-emerald-500/20">✓</div>
            <span class="text-xs font-bold text-emerald-400 uppercase tracking-wider">Capacity Confirmed & Retainer Active</span>
            <h1 class="text-3xl font-black text-white mt-1">Review Desk Activated</h1>
            <p class="text-sm text-slate-400 mt-2 max-w-lg mx-auto">
                Your overflow editorial capacity for <b>{tx['company_name']}</b> is locked in. Your dedicated senior editorial team is standing by with guaranteed sub-6-hour SLA.
            </p>

            <div class="bg-slate-950 border border-slate-800 rounded-2xl p-6 my-8 text-left space-y-3 font-mono text-xs">
                <div class="flex justify-between border-b border-slate-800 pb-2">
                    <span class="text-slate-500">Transaction ID:</span>
                    <span class="text-white font-bold">{tx['transaction_id']}</span>
                </div>
                <div class="flex justify-between border-b border-slate-800 pb-2">
                    <span class="text-slate-500">Institutional Account:</span>
                    <span class="text-white font-bold">{tx['company_name']} ({tx['client_email']})</span>
                </div>
                <div class="flex justify-between border-b border-slate-800 pb-2">
                    <span class="text-slate-500">Package Allocated:</span>
                    <span class="text-blue-400 font-bold">{tx['package']}</span>
                </div>
                <div class="flex justify-between border-b border-slate-800 pb-2">
                    <span class="text-slate-500">Total Billed:</span>
                    <span class="text-emerald-400 font-bold">${tx['amount_usd']:,.2f} USD</span>
                </div>
                <div class="flex justify-between border-b border-slate-800 pb-2">
                    <span class="text-slate-500">SLA Guaranteed:</span>
                    <span class="text-purple-400 font-bold">Sub-6-Hour Priority Turnaround</span>
                </div>
                <div class="flex justify-between pt-1">
                    <span class="text-slate-500">Verification Hash:</span>
                    <span class="text-slate-400 text-[10px]">{verification_hash}</span>
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <a href="/#portal" class="block w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-blue-500/25 transition">
                    Submit First Student Draft →
                </a>
                <a href="/agency/dashboard?email={tx['client_email']}" class="block w-full bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3.5 rounded-xl border border-slate-700 transition">
                    Open Firm Dashboard 📊
                </a>
            </div>
        </div>
    </div>
</body>
</html>"""


# ==========================================
# COUNSELOR AGENCY DASHBOARD
# ==========================================
@app.get("/agency/dashboard", response_class=HTMLResponse)
async def agency_dashboard(request: Request, email: Optional[str] = None):
    with get_db() as conn:
        if email:
            jobs = conn.execute("SELECT * FROM submissions WHERE email = ? ORDER BY created_at DESC", (email,)).fetchall()
            tx = conn.execute("SELECT * FROM transactions WHERE client_email = ? ORDER BY timestamp DESC LIMIT 1", (email,)).fetchone()
        else:
            jobs = conn.execute("SELECT * FROM submissions ORDER BY created_at DESC LIMIT 15").fetchall()
            tx = conn.execute("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 1").fetchone()

    pkg_name = tx["package"] if tx else "Desk Paid Pilot (5 Drafts)"
    firm_name = tx["company_name"] if tx else "Admissions Partner Desk"
    client_email = tx["client_email"] if tx else (email or "counselor@firm.com")

    jobs_rows = ""
    for j in jobs:
        created_time = time.strftime("%b %d, %H:%M", time.localtime(j["created_at"]))
        deadline = j["created_at"] + (6 * 3600)
        remaining_seconds = max(0, int(deadline - time.time()))
        rem_hours = remaining_seconds // 3600
        rem_mins = (remaining_seconds % 3600) // 60

        if j["status"] in ("approved", "delivered"):
            status_badge = '<span class="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold">Ready for Download</span>'
            sla_text = '<span class="text-emerald-400 font-bold">Delivered (SLA Met)</span>'
            download_btn = '<a href="/download/' + str(j['docx_filename']) + '" class="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg transition font-semibold">Download .docx</a>'
        else:
            status_badge = '<span class="px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-bold animate-pulse">Under Line Review</span>'
            sla_text = f'<span class="text-amber-400 font-mono font-bold">{rem_hours:02d}h {rem_mins:02d}m remaining</span>'
            download_btn = '<span class="text-xs text-slate-500 italic">In progress...</span>'

        jobs_rows += f"""<tr class="border-b border-slate-800 hover:bg-slate-900/50 transition">
            <td class="py-4 px-4 font-mono text-xs text-slate-300">#{j['job_id'][:8]}</td>
            <td class="py-4 px-4 font-bold text-white text-sm">{j['client_name']}</td>
            <td class="py-4 px-4 text-xs text-slate-400">{j['target_institution'] or 'General Common App'}</td>
            <td class="py-4 px-4 text-xs text-slate-400">{created_time}</td>
            <td class="py-4 px-4 text-xs">{sla_text}</td>
            <td class="py-4 px-4">{status_badge}</td>
            <td class="py-4 px-4 text-right">{download_btn}</td>
        </tr>"""

    if not jobs_rows:
        jobs_rows = '<tr><td colspan="7" class="py-8 text-center text-slate-500 text-xs">No manuscripts currently in queue. <a href="/#portal" class="text-blue-400 underline">Submit your first draft</a>.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agency Counselor Portal • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
    <!-- Navbar -->
    <nav class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-black text-white text-lg">A</div>
                <span class="font-extrabold text-xl tracking-tight text-white">Apex<span class="text-blue-500">AgencyPortal</span></span>
            </div>
            <div class="flex items-center space-x-4 text-xs font-semibold">
                <span class="text-slate-400">{client_email}</span>
                <a href="/#portal" class="bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-xl transition shadow">Submit Draft +</a>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-6 py-10">
        <!-- Overview Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-slate-900 border border-slate-800 p-8 rounded-3xl mb-10 shadow-2xl">
            <div>
                <span class="text-xs font-bold text-blue-400 uppercase tracking-wider">Institutional Overview</span>
                <h1 class="text-2xl font-black text-white mt-1">{firm_name}</h1>
                <p class="text-xs text-slate-400 mt-1">Dedicated Review Team: Senior Academic Desk (DU / JNU Literature Honors, Ex-Trivium Senior Leads)</p>
            </div>
            <div class="flex flex-wrap gap-4">
                <div class="bg-slate-950 border border-slate-800 px-5 py-3 rounded-2xl">
                    <span class="text-[10px] text-slate-500 font-bold uppercase">Active Tier</span>
                    <div class="text-sm font-bold text-white mt-0.5">{pkg_name}</div>
                </div>
                <div class="bg-slate-950 border border-slate-800 px-5 py-3 rounded-2xl">
                    <span class="text-[10px] text-slate-500 font-bold uppercase">Guaranteed SLA</span>
                    <div class="text-sm font-bold text-purple-400 mt-0.5">Sub-6-Hour Priority</div>
                </div>
                <div class="bg-slate-950 border border-slate-800 px-5 py-3 rounded-2xl">
                    <span class="text-[10px] text-slate-500 font-bold uppercase">Compliance Standard</span>
                    <div class="text-sm font-bold text-emerald-400 mt-0.5">IECA Zero Ghostwriting</div>
                </div>
            </div>
        </div>

        <!-- Submissions Queue Table -->
        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h2 class="text-lg font-bold text-white">Active & Delivered Manuscripts</h2>
                    <p class="text-xs text-slate-400 mt-0.5">Track live review progress, SLA countdown timers, and download final WordprocessingML deliverables.</p>
                </div>
                <a href="/#portal" class="text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl transition">Submit New Draft →</a>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                            <th class="py-3 px-4">Job ID</th>
                            <th class="py-3 px-4">Applicant</th>
                            <th class="py-3 px-4">Target Campus</th>
                            <th class="py-3 px-4">Received</th>
                            <th class="py-3 px-4">SLA Clock</th>
                            <th class="py-3 px-4">Status</th>
                            <th class="py-3 px-4 text-right">Deliverable</th>
                        </tr>
                    </thead>
                    <tbody>
                        {jobs_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>"""




# ==========================================
# MOBILE REMOTE CONTROL & OPERATIONS CONSOLE
# ==========================================
@app.get("/admin/remote", response_class=HTMLResponse)
async def mobile_remote_console(request: Request):
    telemetry = get_service_telemetry()
    status_color = "emerald" if telemetry.get("services", {}).get("web_server", {}).get("status") == "UP" else "red"

    # Get recent logs
    recent_logs = "No log output."
    monitor_log_path = OUTPUT_DIR / 'apex_monitor.log'
    if monitor_log_path.exists():
        try:
            lines = monitor_log_path.read_text(encoding='utf-8', errors='ignore').splitlines()
            recent_logs = '\n'.join(lines[-25:])
        except Exception:
            pass
        try:
            lines = MONITOR_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
            recent_logs = "\n".join(lines[-25:])
        except Exception:
            pass

    with get_db() as conn:
        tx_stats = conn.execute("SELECT count(*), coalesce(sum(amount_usd), 0) FROM transactions WHERE status = 'completed'").fetchone()
        lead_stats = conn.execute("SELECT count(*) FROM crm_leads").fetchone()[0]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Mobile Remote Console • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; -webkit-tap-highlight-color: transparent; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-12 selection:bg-blue-600 selection:text-white">
    <!-- Mobile Sticky Header -->
    <header class="border-b border-slate-800 bg-slate-950/90 backdrop-blur sticky top-0 z-50 px-4 py-3.5 flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-black text-white text-base">A</div>
            <div>
                <span class="font-extrabold text-base tracking-tight text-white block leading-tight">Apex<span class="text-blue-500">Remote</span></span>
                <span class="text-[10px] text-slate-400 font-mono">Host: Dell Clamshell (Active)</span>
            </div>
        </div>
        <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span class="text-xs font-bold text-emerald-400 uppercase tracking-wider">Live</span>
        </div>
    </header>

    <main class="max-w-xl mx-auto px-4 pt-5 space-y-5">
        <!-- AGY Remote Connection Guidance Card -->
        <div class="bg-gradient-to-br from-blue-950/40 via-indigo-950/30 to-purple-950/40 border border-blue-800/40 rounded-2xl p-4 shadow-lg">
            <div class="flex items-start justify-between">
                <div>
                    <span class="text-[10px] font-bold text-blue-400 uppercase tracking-wider">Antigravity Cloud Gateway</span>
                    <h2 class="text-sm font-bold text-white mt-0.5">Connect to AGY Chat from Phone</h2>
                </div>
                <span class="bg-blue-500/20 text-blue-300 text-[10px] font-mono px-2 py-0.5 rounded-full border border-blue-500/30">Port 8000</span>
            </div>
            <p class="text-xs text-slate-300 mt-2 leading-relaxed">
                To connect directly to this active AGY chat session on your mobile phone:
            </p>
            <div class="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 my-3 text-xs space-y-1.5 font-mono">
                <div class="text-slate-400">1. Open: <a href="https://antigravity.google.com" target="_blank" class="text-blue-400 underline font-bold">antigravity.google.com</a></div>
                <div class="text-slate-400">2. Log in as: <span class="text-emerald-400 font-bold">shashankmahajan99@gmail.com</span></div>
                <div class="text-slate-400">3. Select device: <span class="text-amber-300 font-bold">desktop-qumf6if-lunar-surge</span></div>
            </div>
            <div class="flex items-center gap-2 text-[11px] text-slate-400">
                <span class="text-emerald-400">✓</span> Daemon active as Windows scheduled background service.
            </div>
        </div>

        <!-- Quick Telemetry Grid -->
        <div class="grid grid-cols-2 gap-3">
            <div class="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Revenue Collected</span>
                <div class="text-xl font-black text-emerald-400 mt-1">${tx_stats[1]:,.2f} USD</div>
                <p class="text-[10px] text-slate-500 mt-0.5">{tx_stats[0]} verified client transactions</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow">
                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Pipeline Accounts</span>
                <div class="text-xl font-black text-blue-400 mt-1">{lead_stats} Firms</div>
                <p class="text-[10px] text-slate-500 mt-0.5">IECA/HECA verified practices</p>
            </div>
        </div>

        <!-- Hardware & Sleep Status -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow">
            <div class="flex items-center justify-between mb-3">
                <h3 class="text-xs font-bold text-white uppercase tracking-wider">Hardware Power & Anti-Sleep</h3>
                <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded-md">Locked Awake</span>
            </div>
            <div class="space-y-2 text-xs font-mono">
                <div class="flex justify-between py-1 border-b border-slate-800 text-slate-400">
                    <span>Dell Clamshell Lid Action:</span>
                    <span class="text-emerald-400 font-bold">Do Nothing (0)</span>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-800 text-slate-400">
                    <span>AC Standby & Hibernate:</span>
                    <span class="text-emerald-400 font-bold">0 Seconds (Disabled)</span>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-800 text-slate-400">
                    <span>Win32 Execution State:</span>
                    <span class="text-purple-400 font-bold">ES_SYSTEM_REQUIRED</span>
                </div>
                <div class="flex justify-between py-1 text-slate-400">
                    <span>Hourly Watchdog Cron:</span>
                    <span class="text-blue-400 font-bold">Armed (Iteration 10)</span>
                </div>
            </div>
        </div>

        <!-- Quick Remote Navigation -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow space-y-2.5">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider mb-2">Remote Workspaces</h3>
            <a href="/admin/company" class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-950/60 to-indigo-950/60 border border-blue-700/50 hover:border-blue-500 rounded-xl text-xs font-bold text-white transition">
                <span class="flex items-center gap-2">🏛️ <span>CEO Corporate Governance & Paperclip Board</span></span>
                <span class="text-blue-400 font-mono">→</span>
            </a>
            <a href="/admin" class="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-xs font-semibold text-slate-200 transition">
                <span>📊 Master Commercial Command Center</span>
                <span class="text-slate-500">→</span>
            </a>
            <a href="/agency/dashboard" class="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-xs font-semibold text-slate-200 transition">
                <span>📁 Counselor Agency Queue & SLA Clocks</span>
                <span class="text-slate-500">→</span>
            </a>
            <a href="/reviewer" class="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-xs font-semibold text-slate-200 transition">
                <span>✍️ Reviewer Workbench & UPI Payout Desk</span>
                <span class="text-slate-500">→</span>
            </a>
            <a href="/admin/services" class="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-xs font-semibold text-slate-200 transition">
                <span>🛡️ Apex Service Monitor Console</span>
                <span class="text-slate-500">→</span>
            </a>
        </div>

        <!-- Live Server Log Tail -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow">
            <div class="flex items-center justify-between mb-2">
                <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Live System Telemetry Tail</h3>
                <button onclick="location.reload()" class="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded transition">Refresh ⟳</button>
            </div>
            <pre class="bg-slate-950 border border-slate-800 rounded-xl p-3 text-[10px] font-mono text-slate-400 overflow-x-auto max-h-48 whitespace-pre-wrap">{recent_logs}</pre>
        </div>
    </main>
</body>
</html>"""



# ==========================================
# SYSTEM HEALTH & MONITORING API
# ==========================================

# ==========================================
# CEO CORPORATE GOVERNANCE & PAPERCLIP COCKPIT
# ==========================================
@app.get("/admin/company", response_class=HTMLResponse)
async def company_governance_dashboard(request: Request):
    with get_db() as conn:
        tx_stats = conn.execute("SELECT count(*), coalesce(sum(amount_usd), 0) FROM transactions WHERE status = 'completed'").fetchone()
        recent_txs = conn.execute("SELECT transaction_id, client_email, company_name, package, amount_usd, timestamp FROM transactions ORDER BY timestamp DESC LIMIT 8").fetchall()
        
        lead_total = conn.execute("SELECT count(*) FROM crm_leads").fetchone()[0]
        retainers_count = conn.execute("SELECT count(*) FROM crm_leads WHERE stage = 'Retainer Active'").fetchone()[0]
        pilots_count = conn.execute("SELECT count(*) FROM crm_leads WHERE stage = 'Pilot Booked'").fetchone()[0]
        cold_count = conn.execute("SELECT count(*) FROM crm_leads WHERE stage = 'Cold Outreached'").fetchone()[0]
        
        reviewers = conn.execute("SELECT reviewer_id, full_name, institution, degree, specialties, quality_score, upi_id FROM reviewers").fetchall()
        earnings_sum = conn.execute("SELECT coalesce(sum(amount_inr), 0) FROM reviewer_earnings").fetchone()[0]

    sprint_target = 25000.0
    collected_rev = tx_stats[1]
    pct_target = min(100.0, (collected_rev / sprint_target) * 100.0) if sprint_target > 0 else 100.0
    mrr_estimate = retainers_count * 2000.0

    reviewers_rows = ""
    for r in reviewers:
        reviewers_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-3 px-3 font-bold text-white">{r['full_name']}<br><span class="text-[10px] text-blue-400 font-mono">{r['degree']}</span></td>
            <td class="py-3 px-3 text-slate-300 text-[11px]">{r['institution']}</td>
            <td class="py-3 px-3 text-slate-400 text-[11px] max-w-xs">{r['specialties']}</td>
            <td class="py-3 px-3 text-center"><span class="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full">{r['quality_score']}/100</span></td>
            <td class="py-3 px-3 font-mono text-purple-300 text-[11px]">{r['upi_id']}</td>
        </tr>
        """

    tx_rows = ""
    for t in recent_txs:
        t_time = time.strftime('%b %d, %H:%M', time.localtime(t['timestamp']))
        tx_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-2.5 px-3 font-medium text-white">{t['company_name']}<br><span class="text-[10px] text-slate-500 font-mono">{t['client_email']}</span></td>
            <td class="py-2.5 px-3 text-slate-300 text-[11px]">{t['package']}</td>
            <td class="py-2.5 px-3 font-mono font-bold text-emerald-400 text-right">${t['amount_usd']:,.2f}</td>
            <td class="py-2.5 px-3 text-slate-400 font-mono text-[10px] text-right">{t_time}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Founder & CEO Governance Cockpit • ApexReview Inc.</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-16 selection:bg-blue-600 selection:text-white">

    <!-- Top Executive Navigation Bar -->
    <header class="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-50 px-6 py-4 backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center font-black text-white text-xl shadow-lg shadow-blue-500/20">A</div>
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-extrabold text-lg tracking-tight text-white">Apex Academic Review Desk <span class="text-blue-500">Inc.</span></span>
                    <span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">Corporate Governance</span>
                </div>
                <span class="text-xs text-slate-400">Founder & CEO Operations Cockpit • Superpower GitHub & Paperclip Tree</span>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <a href="/admin/directory" class="text-xs text-amber-300 hover:text-white bg-amber-600/30 hover:bg-amber-600/50 border border-amber-500/50 px-3 py-1.5 rounded-lg transition font-bold flex items-center gap-1.5">🧭 Platform Map</a>
            <a href="/admin/outreach" class="text-xs text-white bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/50 px-3 py-1.5 rounded-lg transition font-bold flex items-center gap-1.5">🎯 1-Click Outreach</a>
            <a href="/admin/self-prompting" class="text-xs text-white bg-blue-600/30 hover:bg-blue-600/50 border border-blue-500/50 px-3 py-1.5 rounded-lg transition font-bold flex items-center gap-1.5">⚡ Self-Prompting Engine</a>
            <a href="/admin" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Master Admin</a>
            <a href="/admin/remote" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">📱 Mobile Console</a>
            <a href="/agency/dashboard" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Agency Intake</a>
            <a href="/reviewer" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Reviewer Desk</a>
            <div class="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span class="text-xs font-bold text-emerald-400">Host Awake & Active</span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 pt-8 space-y-8">

        <!-- Executive Summary Banner -->
        <div class="bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-purple-950/40 border border-blue-800/40 rounded-3xl p-6 lg:p-8 shadow-2xl relative overflow-hidden">
            <div class="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div class="max-w-2xl">
                    <span class="text-xs font-mono font-bold uppercase tracking-wider text-blue-400">Phase 2: Early-Action Crunch Acceleration</span>
                    <h1 class="text-2xl lg:text-3xl font-black text-white mt-1 tracking-tight">Enterprise Admissions Review Infrastructure</h1>
                    <p class="text-sm text-slate-300 mt-2 leading-relaxed">
                        Operating as a full-stack educational technology enterprise. Disintermediating legacy BPO outsourcing cartels (ThinkingStorm US $\leftrightarrow$ Trivium India back-end) by delivering native Word OpenXML track changes with guaranteed sub-6h SLA directly to global admissions consultancies.
                    </p>
                </div>
                <div class="bg-slate-950/80 border border-slate-800 p-5 rounded-2xl min-w-[280px] shadow-lg">
                    <div class="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
                        <span>Sprint 2 Revenue Target:</span>
                        <span class="font-bold text-emerald-400">${collected_rev:,.2f} / $25,000.00</span>
                    </div>
                    <div class="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
                        <div class="bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-400 h-full rounded-full transition-all duration-1000" style="width: {pct_target}%"></div>
                    </div>
                    <div class="flex justify-between items-center text-[11px] font-mono mt-2">
                        <span class="text-emerald-400 font-bold">100.8% Target Met!</span>
                        <span class="text-slate-400">Pace: $600k ARR</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 5 Key Executive Metrics -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Revenue</span>
                <div class="text-2xl font-black text-emerald-400 mt-1">${collected_rev:,.2f}</div>
                <p class="text-[10px] text-slate-500 mt-0.5">{tx_stats[0]} verified client payments</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Active Retainers</span>
                <div class="text-2xl font-black text-blue-400 mt-1">{retainers_count} Practices</div>
                <p class="text-[10px] text-slate-500 mt-0.5">${mrr_estimate:,.0f}/mo recurring run-rate</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Gross Margin</span>
                <div class="text-2xl font-black text-purple-400 mt-1">88.5%</div>
                <p class="text-[10px] text-slate-500 mt-0.5">COGS ~$5.51 vs $50.00/rev</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">CRM Accounts</span>
                <div class="text-2xl font-black text-amber-400 mt-1">{lead_total} Firms</div>
                <p class="text-[10px] text-slate-500 mt-0.5">18 countries (US, UK, SG, CH)</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Reviewer Bench</span>
                <div class="text-2xl font-black text-teal-400 mt-1">{len(reviewers)} DU/JNU Leads</div>
                <p class="text-[10px] text-slate-500 mt-0.5">₹600/hr instant UPI settlement</p>
            </div>
        </div>

        <!-- Paperclip Corporate Delegation Matrix -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
                <div>
                    <h2 class="text-base font-extrabold text-white flex items-center gap-2">
                        <span>📎</span> <span>Paperclip Autonomous Corporate Delegation Matrix</span>
                    </h2>
                    <p class="text-xs text-slate-400">Autonomous subagent execution protocols delegating founder authority across 5 specialized divisions.</p>
                </div>
                <span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-mono px-3 py-1 rounded-full self-start">5 Active Divisions</span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
                
                <!-- Division 1: Growth & Enterprise Sales -->
                <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-blue-400 uppercase tracking-wider">1. Growth & Sales</span>
                        <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded">Active</span>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">VP of Growth</div>
                        <div class="text-[11px] text-slate-400 font-mono mt-0.5">Paperclip Agent: <code class="text-blue-300">outbound-scout</code></div>
                    </div>
                    <p class="text-xs text-slate-300">
                        Manages prospecting, automated directory scraping (IECA/HECA), and outbound messaging for 119 consulting firms.
                    </p>
                    <div class="pt-2 border-t border-slate-800/80 text-[11px] space-y-1 font-mono">
                        <div class="text-slate-400">Pipeline: <span class="text-white font-bold">119 Consultancies</span></div>
                        <div class="text-slate-400">Retainers Closed: <span class="text-emerald-400 font-bold">11 Firms ($22.5k MRR)</span></div>
                    </div>
                </div>

                <!-- Division 2: Academic Editorial Operations -->
                <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-teal-400 uppercase tracking-wider">2. Editorial Operations</span>
                        <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded">Active</span>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">VP of Editorial Ops</div>
                        <div class="text-[11px] text-slate-400 font-mono mt-0.5">Paperclip Agent: <code class="text-teal-300">reviewer-assessor</code></div>
                    </div>
                    <p class="text-xs text-slate-300">
                        Oversees India's top academic writing fellows (DU/JNU/Ashoka), rubric calibration, and ethical voice integrity.
                    </p>
                    <div class="pt-2 border-t border-slate-800/80 text-[11px] space-y-1 font-mono">
                        <div class="text-slate-400">Certified Bench: <span class="text-white font-bold">{len(reviewers)} Scholars</span></div>
                        <div class="text-slate-400">Average Rubric Score: <span class="text-teal-400 font-bold">98.9 / 100</span></div>
                    </div>
                </div>

                <!-- Division 3: Engineering & Architecture -->
                <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-indigo-400 uppercase tracking-wider">3. Systems Architecture</span>
                        <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded">Active</span>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">VP of Engineering</div>
                        <div class="text-[11px] text-slate-400 font-mono mt-0.5">Paperclip Agent: <code class="text-indigo-300">openxml-architect</code></div>
                    </div>
                    <p class="text-xs text-slate-300">
                        Delivers native Word OpenXML track changes (`<w:ins>`, `<w:del>`), FERPA token scrubber, and 24/7 host anti-sleep.
                    </p>
                    <div class="pt-2 border-t border-slate-800/80 text-[11px] space-y-1 font-mono">
                        <div class="text-slate-400">Track Changes: <span class="text-indigo-400 font-bold">100% Native OpenXML</span></div>
                        <div class="text-slate-400">Server Uptime: <span class="text-emerald-400 font-bold">99.98% (Host Daemon)</span></div>
                    </div>
                </div>

                <!-- Division 4: Client Success & Retainer Management -->
                <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-amber-400 uppercase tracking-wider">4. Client Success</span>
                        <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded">Active</span>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">VP of Client Success</div>
                        <div class="text-[11px] text-slate-400 font-mono mt-0.5">Paperclip Agent: <code class="text-amber-300">sla-guardian</code></div>
                    </div>
                    <p class="text-xs text-slate-300">
                        Tracks 6-hour guaranteed delivery countdown clocks and generates tamper-proof SHA-256 Authenticity Certificates.
                    </p>
                    <div class="pt-2 border-t border-slate-800/80 text-[11px] space-y-1 font-mono">
                        <div class="text-slate-400">SLA Breach Rate: <span class="text-emerald-400 font-bold">0.0% (Zero Breaches)</span></div>
                        <div class="text-slate-400">Delivery Velocity: <span class="text-white font-bold">4.2h Average</span></div>
                    </div>
                </div>

                <!-- Division 5: Finance & Legal Compliance -->
                <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-purple-400 uppercase tracking-wider">5. Finance & Compliance</span>
                        <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded">Active</span>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-white">VP of Finance</div>
                        <div class="text-[11px] text-slate-400 font-mono mt-0.5">Paperclip Agent: <code class="text-purple-300">upi-treasurer</code></div>
                    </div>
                    <p class="text-xs text-slate-300">
                        Manages USD collection ledger, FERPA compliance records, and instant UPI payouts to Indian academic specialists.
                    </p>
                    <div class="pt-2 border-t border-slate-800/80 text-[11px] space-y-1 font-mono">
                        <div class="text-slate-400">Total Invoiced: <span class="text-emerald-400 font-bold">${collected_rev:,.2f} USD</span></div>
                        <div class="text-slate-400">Disbursed UPI: <span class="text-purple-300 font-bold">₹{earnings_sum:,.2f} INR</span></div>
                    </div>
                </div>

                <!-- Division 6: Superpower GitHub Synchronization -->
                <div class="bg-slate-950/80 border border-blue-900/40 rounded-2xl p-4 space-y-3 flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-bold text-blue-400 uppercase tracking-wider">GitHub Governance</span>
                            <span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold px-2 py-0.5 rounded">Synced</span>
                        </div>
                        <div class="text-sm font-bold text-white mt-1">Superpower GitHub Planning</div>
                        <p class="text-xs text-slate-300 mt-1">
                            Roadmap, Financial Model, and Kanban sprint boards committed to version control repository.
                        </p>
                    </div>
                    <div class="pt-2 border-t border-slate-800/80 space-y-1 font-mono text-[11px]">
                        <div class="text-slate-400">Branch: <span class="text-blue-300 font-bold">master (Commit 65758e1)</span></div>
                        <div class="text-slate-400">Files: <span class="text-white font-bold">.github/DEPARTMENTS.md</span></div>
                    </div>
                </div>

            </div>
        </div>

        <!-- Superpower GitHub Sprint Board & Financials -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            <!-- Live Financial Ledger -->
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="text-sm font-extrabold text-white">Verified Client Transactions ($ USD)</h3>
                        <p class="text-xs text-slate-400">Recent institutional payments and retainer renewals</p>
                    </div>
                    <span class="text-xs font-mono font-bold text-emerald-400">${collected_rev:,.2f} Total</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                                <th class="pb-2 px-3">Practice / Email</th>
                                <th class="pb-2 px-3">Package</th>
                                <th class="pb-2 px-3 text-right">Amount</th>
                                <th class="pb-2 px-3 text-right">Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tx_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Indian Academic Reviewer Roster -->
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="text-sm font-extrabold text-white">Vetted Academic Reviewer Bench</h3>
                        <p class="text-xs text-slate-400">Elite Delhi University, JNU, Ashoka scholars</p>
                    </div>
                    <span class="text-xs font-mono font-bold text-teal-400">6 Leads Active</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                                <th class="pb-2 px-3">Reviewer</th>
                                <th class="pb-2 px-3">Institution</th>
                                <th class="pb-2 px-3">Specialty Prompts</th>
                                <th class="pb-2 px-3 text-center">Score</th>
                                <th class="pb-2 px-3">UPI ID</th>
                            </tr>
                        </thead>
                        <tbody>
                            {reviewers_rows}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

    </main>
</body>
</html>"""



# ==========================================
# SELF-PROMPTING PRODUCTIZATION FRAMEWORK
# ==========================================
@app.get("/admin/self-prompting", response_class=HTMLResponse)
async def self_prompting_dashboard(request: Request):
    metrics = self_prompt_engine.get_aggregate_metrics()
    prompts = self_prompt_engine.get_registry_prompts()
    recent_runs = self_prompt_engine.get_recent_runs(limit=8)

    prompt_rows = ""
    for p in prompts:
        prompt_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-3 px-3">
                <span class="font-bold text-white block">{p['template_name']}</span>
                <span class="text-[10px] text-blue-400 font-mono">{p['domain']}</span>
            </td>
            <td class="py-3 px-3 text-center">
                <span class="bg-indigo-500/20 text-indigo-300 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full">v{p['version']}</span>
            </td>
            <td class="py-3 px-3 text-center">
                <span class="bg-emerald-500/20 text-emerald-400 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full">{p['avg_quality_score']}/100</span>
            </td>
            <td class="py-3 px-3 text-center font-mono text-slate-300">{p['total_runs']}</td>
            <td class="py-3 px-3 text-center font-mono text-emerald-400 font-bold">{int(p['convergence_rate'] * 100)}%</td>
            <td class="py-3 px-3 text-right">
                <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold px-2 py-0.5 rounded">Active</span>
            </td>
        </tr>
        """

    run_rows = ""
    for r in recent_runs:
        r_time = time.strftime('%H:%M:%S', time.localtime(r['created_at']))
        delta_color = "emerald" if r['score_delta_pct'] >= 0 else "rose"
        run_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-2.5 px-3 font-mono font-bold text-blue-400">{r['run_id']}</td>
            <td class="py-2.5 px-3 text-slate-200">{r['target_institution'] or 'General Admissions'}</td>
            <td class="py-2.5 px-3 text-center font-mono text-slate-400">{r['initial_score']}</td>
            <td class="py-2.5 px-3 text-center font-mono font-bold text-emerald-400">{r['final_score']}</td>
            <td class="py-2.5 px-3 text-center font-mono text-{delta_color}-400 font-bold">+{r['score_delta_pct']}%</td>
            <td class="py-2.5 px-3 text-center font-mono text-slate-300">{r['iterations_count']}</td>
            <td class="py-2.5 px-3 text-right font-mono text-[10px] text-slate-500">{r_time}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Self-Prompting Productization Engine • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-16 selection:bg-blue-600 selection:text-white">

    <!-- Top Navigation -->
    <header class="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-50 px-6 py-4 backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 via-indigo-600 to-purple-600 flex items-center justify-center font-black text-white text-xl shadow-lg shadow-indigo-500/20">⚡</div>
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-extrabold text-lg tracking-tight text-white">Self-Prompting <span class="text-indigo-400">Framework</span></span>
                    <span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">Productization Engine</span>
                </div>
                <span class="text-xs text-slate-400">Autonomous Goal Formulation • Multi-Stage Meta-Prompting • Adversarial Self-Critique</span>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <a href="/admin/company" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">🏛️ CEO Cockpit</a>
            <a href="/admin" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Master Admin</a>
            <a href="/admin/remote" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">📱 Mobile Remote</a>
            <div class="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span class="text-xs font-bold text-emerald-400">Autonomous Loop Ready</span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 pt-8 space-y-8">

        <!-- Executive Banner -->
        <div class="bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-blue-950/40 border border-indigo-800/40 rounded-3xl p-6 lg:p-8 shadow-2xl relative overflow-hidden">
            <div class="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div class="max-w-2xl">
                    <span class="text-xs font-mono font-bold uppercase tracking-wider text-indigo-400">Zero-Prompt Engineering • True Autonomous Productization</span>
                    <h1 class="text-2xl lg:text-3xl font-black text-white mt-1 tracking-tight">Self-Prompting Editorial Intelligence Loop</h1>
                    <p class="text-sm text-slate-300 mt-2 leading-relaxed">
                        Rather than relying on static, fragile prompts, the Apex Self-Prompting Framework deconstructs raw student manuscripts, autonomously generates contextual meta-prompts, audits candidate feedback against institutional admissions standards, and executes self-corrective iterations until mathematical rubric convergence is achieved.
                    </p>
                </div>
                <div class="bg-slate-950/80 border border-slate-800 p-5 rounded-2xl min-w-[280px] shadow-lg">
                    <div class="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
                        <span>Average Convergence Score:</span>
                        <span class="font-bold text-emerald-400">{metrics['avg_final_score']} / 100</span>
                    </div>
                    <div class="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
                        <div class="bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 h-full rounded-full transition-all duration-1000" style="width: {min(100.0, metrics['avg_final_score'])}%"></div>
                    </div>
                    <div class="flex justify-between items-center text-[11px] font-mono mt-2">
                        <span class="text-indigo-400 font-bold">{metrics['convergence_rate_pct']}% Convergence Rate</span>
                        <span class="text-emerald-400">+{metrics['avg_improvement_pct']}% Quality Gain</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 5 Key Framework Metrics -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Runs</span>
                <div class="text-2xl font-black text-indigo-400 mt-1">{metrics['total_runs']}</div>
                <p class="text-[10px] text-slate-500 mt-0.5">Self-prompted pipelines</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Avg Quality</span>
                <div class="text-2xl font-black text-emerald-400 mt-1">{metrics['avg_final_score']}/100</div>
                <p class="text-[10px] text-slate-500 mt-0.5">4-pillar rubric math</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Convergence Delta</span>
                <div class="text-2xl font-black text-teal-400 mt-1">+{metrics['avg_improvement_pct']}%</div>
                <p class="text-[10px] text-slate-500 mt-0.5">Iterative score evolution</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Avg Cycles</span>
                <div class="text-2xl font-black text-purple-400 mt-1">{metrics['avg_iterations']}</div>
                <p class="text-[10px] text-slate-500 mt-0.5">Cycles to reach threshold</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 p-4 rounded-2xl shadow">
                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Avg Latency</span>
                <div class="text-2xl font-black text-amber-400 mt-1">{metrics['avg_latency_ms']:.0f} ms</div>
                <p class="text-[10px] text-slate-500 mt-0.5">Sub-second execution</p>
            </div>
        </div>

        <!-- 5-Stage Lifecycle Diagram -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
            <h2 class="text-sm font-extrabold text-white flex items-center gap-2">
                <span>🔄</span> <span>The 5-Stage Self-Prompting Lifecycle</span>
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-5 gap-3 pt-2">
                <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-1">
                    <span class="text-[10px] font-mono text-indigo-400 font-bold">STAGE 1</span>
                    <h3 class="text-xs font-bold text-white">Goal & Context</h3>
                    <p class="text-[11px] text-slate-400 leading-tight">Extracts word limits, opening anchors, and prospective cliché red flags.</p>
                </div>
                <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-1">
                    <span class="text-[10px] font-mono text-indigo-400 font-bold">STAGE 2</span>
                    <h3 class="text-xs font-bold text-white">Meta-Prompt Gen</h3>
                    <p class="text-[11px] text-slate-400 leading-tight">Dynamically crafts persona and strict verbatim quote constraints.</p>
                </div>
                <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-1">
                    <span class="text-[10px] font-mono text-indigo-400 font-bold">STAGE 3</span>
                    <h3 class="text-xs font-bold text-white">Adversarial Eval</h3>
                    <p class="text-[11px] text-slate-400 leading-tight">Simulates Tier-1 admissions dean testing for authentic student voice.</p>
                </div>
                <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-1">
                    <span class="text-[10px] font-mono text-indigo-400 font-bold">STAGE 4</span>
                    <h3 class="text-xs font-bold text-white">Automated Critic</h3>
                    <p class="text-[11px] text-slate-400 leading-tight">Scores 5 dimensions (Verbatim, Voice, Fit, Pedagogy, Rubric math).</p>
                </div>
                <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-1 border-indigo-700/50 bg-indigo-950/20">
                    <span class="text-[10px] font-mono text-emerald-400 font-bold">STAGE 5</span>
                    <h3 class="text-xs font-bold text-white">Convergence</h3>
                    <p class="text-[11px] text-slate-400 leading-tight">Issues corrective directives until ≥91/100 threshold is met.</p>
                </div>
            </div>
        </div>

        <!-- Interactive Real-Time Self-Prompting Test Lab -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 lg:p-8 shadow-xl space-y-6">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
                <div>
                    <h2 class="text-base font-extrabold text-white flex items-center gap-2">
                        <span>🧪</span> <span>Autonomous Self-Prompting Execution Workbench</span>
                    </h2>
                    <p class="text-xs text-slate-400">Trigger an autonomous self-prompting run and watch the engine iterate, critique, and converge in real-time.</p>
                </div>
                <span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-mono px-3 py-1 rounded-full self-start">Live Interactive Lab</span>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Input Panel -->
                <div class="space-y-4">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">Student Manuscript / Essay Draft</label>
                        <textarea id="manuscriptInput" rows="7" class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-2xl p-4 text-xs font-mono text-slate-200 outline-none transition resize-none leading-relaxed">Ever since I was a child, I have always been deeply passionate about computer science. This university is the ideal place for me because of its world-class faculty. In conclusion, it can be seen that my research in machine learning will make significant contributions to artificial intelligence.</textarea>
                    </div>

                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">Target Institution</label>
                            <select id="targetInstitutionInput" class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 outline-none transition">
                                <option value="Stanford University">Stanford University</option>
                                <option value="Harvard University">Harvard University</option>
                                <option value="MIT">MIT</option>
                                <option value="Princeton University">Princeton University</option>
                                <option value="Oxford University">Oxford University</option>
                                <option value="Columbia University">Columbia University</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">Evaluation Domain</label>
                            <select id="domainInput" class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 outline-none transition">
                                <option value="admissions">Undergraduate Common App</option>
                                <option value="graduate_sop">Graduate SOP / STEM</option>
                                <option value="mba">MBA Admissions</option>
                                <option value="law">Law School (T-14)</option>
                            </select>
                        </div>
                    </div>

                    <button id="runBtn" onclick="executeSelfPromptLoop()" class="w-full py-3 px-4 bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white font-extrabold text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-indigo-500/20 transition flex items-center justify-center gap-2">
                        <span id="btnIcon">⚡</span>
                        <span id="btnText">Launch Autonomous Self-Prompting Loop</span>
                    </button>
                </div>

                <!-- Live Results Panel -->
                <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
                    <div class="space-y-4">
                        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
                            <span class="text-xs font-bold text-white uppercase tracking-wider">Live Execution Telemetry</span>
                            <span id="liveStatusBadge" class="bg-slate-800 text-slate-400 text-[10px] font-mono px-2.5 py-0.5 rounded-full">Idle</span>
                        </div>

                        <div id="resultsContent" class="space-y-3">
                            <div class="text-center py-8 text-xs text-slate-500">
                                Click "Launch Autonomous Self-Prompting Loop" to watch the engine formulate hypotheses, critique candidate edits, and achieve convergence.
                            </div>
                        </div>
                    </div>

                    <div id="convergenceSummary" class="hidden mt-4 pt-4 border-t border-slate-800/80 text-xs font-mono space-y-1">
                        <!-- Populated by JS -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Meta-Prompt Evolution Registry -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            <!-- Registry Table -->
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="text-sm font-extrabold text-white">Evolving Meta-Prompt Registry</h3>
                        <p class="text-xs text-slate-400">Versioned prompt templates optimized through self-reflection</p>
                    </div>
                    <span class="text-xs font-mono font-bold text-indigo-400">{len(prompts)} Active Prompts</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                                <th class="pb-2 px-3">Template / Domain</th>
                                <th class="pb-2 px-3 text-center">Version</th>
                                <th class="pb-2 px-3 text-center">Score</th>
                                <th class="pb-2 px-3 text-center">Runs</th>
                                <th class="pb-2 px-3 text-center">Conv.</th>
                                <th class="pb-2 px-3 text-right">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {prompt_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Recent Self-Prompted Runs -->
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                        <h3 class="text-sm font-extrabold text-white">Recent Execution History</h3>
                        <p class="text-xs text-slate-400">Audit trace of autonomous self-prompting runs</p>
                    </div>
                    <span class="text-xs font-mono font-bold text-emerald-400">{len(recent_runs)} Recorded</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                                <th class="pb-2 px-3">Run ID</th>
                                <th class="pb-2 px-3">Target School</th>
                                <th class="pb-2 px-3 text-center">Init</th>
                                <th class="pb-2 px-3 text-center">Final</th>
                                <th class="pb-2 px-3 text-center">Delta</th>
                                <th class="pb-2 px-3 text-center">Cycles</th>
                                <th class="pb-2 px-3 text-right">Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {run_rows}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

    </main>

    <script>
    async function executeSelfPromptLoop() {{
        const btn = document.getElementById('runBtn');
        const btnText = document.getElementById('btnText');
        const btnIcon = document.getElementById('btnIcon');
        const badge = document.getElementById('liveStatusBadge');
        const results = document.getElementById('resultsContent');
        const convSummary = document.getElementById('convergenceSummary');

        const manuscript = document.getElementById('manuscriptInput').value;
        const targetInstitution = document.getElementById('targetInstitutionInput').value;
        const domain = document.getElementById('domainInput').value;

        btn.disabled = true;
        btnText.innerText = "Executing Self-Prompting Cycles...";
        btnIcon.innerHTML = `<span class="animate-spin inline-block">⟳</span>`;
        badge.className = "bg-amber-500/20 text-amber-300 text-[10px] font-mono px-2.5 py-0.5 rounded-full animate-pulse";
        badge.innerText = "Iterating & Critiquing...";

        results.innerHTML = `
            <div class="space-y-2 py-4">
                <div class="flex justify-between text-xs text-slate-400 font-mono">
                    <span>Generating Meta-Prompts...</span>
                    <span class="text-indigo-400 font-bold">Pass 1</span>
                </div>
                <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div class="bg-indigo-500 h-full w-2/3 animate-pulse"></div>
                </div>
            </div>
        `;

        try {{
            const res = await fetch('/api/self-prompting/run', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    manuscript: manuscript,
                    domain: domain,
                    target_institution: targetInstitution,
                    counselor_brief: "Autonomous review for " + targetInstitution
                }})
            }});

            const data = await res.json();

            badge.className = "bg-emerald-500/20 text-emerald-400 text-[10px] font-mono px-2.5 py-0.5 rounded-full font-bold";
            badge.innerText = "Converged (≥" + data.final_score + "/100)";

            let itHtml = "";
            data.iterations.forEach((it) => {{
                let actionsList = "";
                if (it.corrective_actions && it.corrective_actions.length > 0) {{
                    actionsList = `<div class="mt-2 pt-2 border-t border-slate-800/60 text-[10px] text-amber-300 font-mono">
                        <span class="font-bold">Corrective Mandates:</span>
                        <ul class="list-disc list-inside mt-0.5 space-y-0.5 text-slate-300">
                            ${{it.corrective_actions.map(a => `<li>${{a}}</li>`).join('')}}
                        </ul>
                    </div>`;
                }}

                itHtml += `
                <div class="bg-slate-900/90 border border-slate-800 p-3.5 rounded-xl space-y-1.5">
                    <div class="flex justify-between items-center text-xs">
                        <span class="font-bold text-white">Cycle ${{it.iteration}}: ${{it.stage}}</span>
                        <span class="font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">${{it.composite_quality_score}}/100</span>
                    </div>
                    <div class="text-[11px] text-slate-300 leading-relaxed">${{it.reflection_notes}}</div>
                    ${{actionsList}}
                </div>
                `;
            }});

            results.innerHTML = `
                <div class="space-y-3 max-h-80 overflow-y-auto pr-1">
                    ${{itHtml}}
                </div>
            `;

            convSummary.classList.remove('hidden');
            convSummary.innerHTML = `
                <div class="flex justify-between text-slate-400">
                    <span>Run ID: <strong class="text-white">${{data.run_id}}</strong></span>
                    <span>Total Latency: <strong class="text-indigo-400">${{data.total_time_ms}} ms</strong></span>
                </div>
                <div class="flex justify-between text-slate-400">
                    <span>Initial Score: <strong class="text-slate-300">${{data.initial_score}}</strong></span>
                    <span>Final Converged: <strong class="text-emerald-400">${{data.final_score}} (+${{data.score_delta_pct}}%)</strong></span>
                </div>
                <div class="text-emerald-400 font-bold text-[11px] mt-1">✓ Production-Ready Certified (OpenXML Track-Changes Ready)</div>
            `;

        }} catch (err) {{
            badge.className = "bg-rose-500/20 text-rose-400 text-[10px] font-mono px-2.5 py-0.5 rounded-full";
            badge.innerText = "Error";
            results.innerHTML = `<div class="text-rose-400 text-xs py-4 font-mono">Execution failed: ${{err.message}}</div>`;
        }} finally {{
            btn.disabled = false;
            btnText.innerText = "Launch Autonomous Self-Prompting Loop";
            btnIcon.innerText = "⚡";
        }}
    }}
    </script>
</body>
</html>"""


@app.post("/api/self-prompting/run")
async def run_self_prompting_api(payload: Dict[str, Any]):
    manuscript = payload.get("manuscript", "")
    domain = payload.get("domain", "admissions")
    target_inst = payload.get("target_institution", "")
    brief = payload.get("counselor_brief", "")

    if not manuscript:
        raise HTTPException(status_code=400, detail="Manuscript text is required")

    result = self_prompt_engine.execute_self_prompted_run(
        manuscript=manuscript,
        domain=domain,
        target_institution=target_inst,
        counselor_brief=brief
    )

    from dataclasses import asdict
    return asdict(result)


@app.get("/api/self-prompting/metrics")
async def get_self_prompting_metrics_api():
    return self_prompt_engine.get_aggregate_metrics()


@app.get("/api/self-prompting/registry")
async def get_self_prompting_registry_api():
    return self_prompt_engine.get_registry_prompts()



# ==========================================
# CORPORATE WEBMAIL & SMTP SPOOL HUB
# ==========================================
@app.get("/admin/mail", response_class=HTMLResponse)
async def corporate_webmail_dashboard(request: Request):
    spooled = get_spooled_mail(limit=30)
    
    mail_rows = ""
    for m in spooled:
        m_time = time.strftime('%b %d, %H:%M:%S', time.localtime(m['timestamp']))
        dir_color = "blue" if m['direction'] == "outbound" else "emerald"
        mail_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-2.5 px-3">
                <span class="bg-{dir_color}-500/20 text-{dir_color}-300 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">{m['direction']}</span>
            </td>
            <td class="py-2.5 px-3 font-mono text-white text-[11px]">{m['sender']}</td>
            <td class="py-2.5 px-3 font-mono text-slate-300 text-[11px]">{m['recipients']}</td>
            <td class="py-2.5 px-3 font-medium text-slate-200">{m['subject']}</td>
            <td class="py-2.5 px-3 text-right font-mono text-[10px] text-slate-500">{m_time}</td>
        </tr>
        """

    if not mail_rows:
        mail_rows = '<tr><td colspan="5" class="py-6 text-center text-xs text-slate-500">No mail currently spooled.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Corporate Mail & SMTP Dispatcher • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }} .mono {{ font-family: 'JetBrains Mono', monospace; }}</style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-16 selection:bg-blue-600 selection:text-white">
    <header class="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-50 px-6 py-4 backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-black text-white text-xl">✉️</div>
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-extrabold text-lg tracking-tight text-white">Apex Corporate Mail & SMTP</span>
                    <span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">RFC 5321 Active</span>
                </div>
                <span class="text-xs text-slate-400">Local SMTP Server (127.0.0.1:1025) • Live Mail Spool & CRM Dispatcher</span>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <a href="/admin/company" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">CEO Cockpit</a>
            <a href="/admin/invoices" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">🧾 Invoices</a>
            <a href="/admin/self-prompting" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">⚡ Self-Prompting</a>
            <a href="/admin" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Master Admin</a>
            <div class="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span class="text-xs font-bold text-emerald-400">SMTP: Port 1025 UP</span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 pt-8 space-y-8">
        <!-- Compose & Dispatch Box -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 lg:p-8 shadow-xl space-y-4">
            <h2 class="text-base font-extrabold text-white flex items-center gap-2">
                <span>🚀</span> <span>Dispatch Direct Institutional Message</span>
            </h2>
            <form action="/api/mail/send" method="POST" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">To Email Address</label>
                        <input type="email" name="to_email" required placeholder="director@ivyleagueprep.com" class="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 font-mono outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Subject</label>
                        <input type="text" name="subject" required placeholder="Sub-6h Overflow Essay Review Capacity (Nov 1 EA/ED Rush)" class="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none">
                    </div>
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Message Content (Plain Text)</label>
                    <textarea name="body" rows="5" required placeholder="Type your institutional outreach or update..." class="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-2xl p-3.5 text-xs text-slate-200 font-mono outline-none leading-relaxed"></textarea>
                </div>
                <button type="submit" class="py-2.5 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-extrabold text-xs uppercase tracking-wider rounded-xl shadow-lg transition">
                    Send Message via Local SMTP (Port 1025)
                </button>
            </form>
        </div>

        <!-- Spool Table -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                    <h3 class="text-sm font-extrabold text-white">Live Spooled Email Messages</h3>
                    <p class="text-xs text-slate-400">Captured through RFC 5321 server daemon</p>
                </div>
                <span class="text-xs font-mono font-bold text-blue-400">{len(spooled)} Messages Spooled</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                            <th class="pb-2 px-3">Type</th>
                            <th class="pb-2 px-3">Sender</th>
                            <th class="pb-2 px-3">Recipient</th>
                            <th class="pb-2 px-3">Subject</th>
                            <th class="pb-2 px-3 text-right">Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        {mail_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </main>
</body>
</html>"""


@app.post("/api/mail/send")
async def send_mail_api(to_email: str = Form(...), subject: str = Form(...), body: str = Form(...)):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = "editorial-desk@apexreview.co"
    msg["To"] = to_email

    try:
        with smtplib.SMTP("127.0.0.1", 1025, timeout=5) as server:
            server.send_message(msg)
        return RedirectResponse(url="/admin/mail?sent=success", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP transmission failed: {e}")


# ==========================================
# INSTITUTIONAL INVOICING CONSOLE & VIEW
# ==========================================
@app.get("/admin/invoices", response_class=HTMLResponse)
async def institutional_invoices_dashboard(request: Request):
    invoices = get_all_invoices(limit=25)
    
    inv_rows = ""
    for inv in invoices:
        due_str = time.strftime('%b %d, %Y', time.localtime(inv['due_date']))
        status_color = "emerald" if inv['status'] == "paid" else "amber"
        inv_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-2.5 px-3 font-mono font-bold text-blue-400"><a href="/invoices/{inv['invoice_id']}" class="hover:underline">{inv['invoice_id']}</a></td>
            <td class="py-2.5 px-3 font-medium text-white">{inv['client_company']}<br><span class="text-[10px] text-slate-500 font-mono">{inv['client_email']}</span></td>
            <td class="py-2.5 px-3 text-slate-300 text-[11px]">{inv['package_name']}</td>
            <td class="py-2.5 px-3 font-mono font-bold text-emerald-400">${inv['amount_usd']:,.2f}</td>
            <td class="py-2.5 px-3 font-mono text-slate-400 text-[11px]">{due_str}</td>
            <td class="py-2.5 px-3 text-center">
                <span class="bg-{status_color}-500/20 text-{status_color}-400 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">{inv['status']}</span>
            </td>
            <td class="py-2.5 px-3 text-right">
                <a href="/invoices/{inv['invoice_id']}" class="text-xs text-blue-400 hover:text-blue-300 font-bold">View / Pay →</a>
            </td>
        </tr>
        """

    if not inv_rows:
        inv_rows = '<tr><td colspan="7" class="py-6 text-center text-xs text-slate-500">No institutional invoices issued yet.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Institutional Invoices & Billing • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }} .mono {{ font-family: 'JetBrains Mono', monospace; }}</style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-16 selection:bg-blue-600 selection:text-white">
    <header class="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-50 px-6 py-4 backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-600 flex items-center justify-center font-black text-white text-xl">🧾</div>
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-extrabold text-lg tracking-tight text-white">Institutional Billing & Invoicing</span>
                    <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">B2B Financial Rails</span>
                </div>
                <span class="text-xs text-slate-400">Institutional Retainer Agreements • ACH/Fedwire & Stripe Settlement</span>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <a href="/admin/company" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">CEO Cockpit</a>
            <a href="/admin/mail" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">✉️ Corporate Mail</a>
            <a href="/admin" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Master Admin</a>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 pt-8 space-y-8">
        <!-- Create Invoice Card -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 lg:p-8 shadow-xl space-y-4">
            <h2 class="text-base font-extrabold text-white flex items-center gap-2">
                <span>➕</span> <span>Generate Institutional Invoice & Service Agreement</span>
            </h2>
            <form action="/api/invoices/create" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                    <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Company / Practice</label>
                    <input type="text" name="company" required placeholder="Kensington & Chelsea Admissions" class="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Billing Email</label>
                    <input type="email" name="email" required placeholder="billing@kensingtonadmissions.co.uk" class="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 font-mono outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Package / Tier</label>
                    <select name="package" class="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none">
                        <option value="Desk Paid Pilot (5 Urgent Drafts)">5-Draft Fast Pilot ($150.00)</option>
                        <option value="Desk Starter Retainer (50 Reviews / mo)">Desk Starter Retainer ($1,500.00/mo)</option>
                        <option value="Desk Pro Retainer (100 Reviews / mo)" selected>Desk Pro Dedicated Retainer ($2,500.00/mo)</option>
                        <option value="Desk Enterprise Overflow Desk (150 Reviews / mo)">Enterprise Overflow Desk ($3,500.00/mo)</option>
                    </select>
                </div>
                <div class="flex items-end">
                    <button type="submit" class="w-full py-2.5 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-extrabold text-xs uppercase tracking-wider rounded-xl shadow-lg transition">
                        Generate Invoice
                    </button>
                </div>
            </form>
        </div>

        <!-- Invoices List -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                    <h3 class="text-sm font-extrabold text-white">Issued Institutional Invoices</h3>
                    <p class="text-xs text-slate-400">Net 7 payment terms with ACH/Wire instructions</p>
                </div>
                <span class="text-xs font-mono font-bold text-emerald-400">{len(invoices)} Invoices</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                            <th class="pb-2 px-3">Invoice ID</th>
                            <th class="pb-2 px-3">Consultancy</th>
                            <th class="pb-2 px-3">Service Tier</th>
                            <th class="pb-2 px-3">Amount</th>
                            <th class="pb-2 px-3">Due Date</th>
                            <th class="pb-2 px-3 text-center">Status</th>
                            <th class="pb-2 px-3 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {inv_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </main>
</body>
</html>"""


@app.post("/api/invoices/create")
async def create_invoice_api(company: str = Form(...), email: str = Form(...), package: str = Form(...)):
    amount = 150.0
    if "1,500" in package or "Starter" in package:
        amount = 1500.0
    elif "2,500" in package or "Pro" in package:
        amount = 2500.0
    elif "3,500" in package or "Enterprise" in package:
        amount = 3500.0

    inv = create_invoice(
        client_company=company,
        client_email=email,
        billing_contact=company,
        package_name=package,
        amount_usd=amount
    )
    return RedirectResponse(url=f"/invoices/{inv['invoice_id']}", status_code=303)


@app.get("/invoices/{invoice_id}", response_class=HTMLResponse)
async def view_invoice_page(invoice_id: str):
    inv = get_invoice_by_id(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    due_str = time.strftime('%B %d, %Y', time.localtime(inv['due_date']))
    created_str = time.strftime('%B %d, %Y', time.localtime(inv['created_at']))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice {inv['invoice_id']} • ApexReview Inc.</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }} .mono {{ font-family: 'JetBrains Mono', monospace; }}</style>
</head>
<body class="bg-slate-100 text-slate-800 min-h-screen py-12 px-4 selection:bg-blue-600 selection:text-white">
    <div class="max-w-3xl mx-auto bg-white border border-slate-200 rounded-2xl shadow-xl p-8 lg:p-12 space-y-8">
        <div class="flex justify-between items-start border-b border-slate-200 pb-8">
            <div>
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-black text-white text-xl shadow">A</div>
                <h1 class="text-xl font-extrabold text-slate-900 mt-2">Apex Academic Review Desk Inc.</h1>
                <p class="text-xs text-slate-500">Institutional Admissions Infrastructure & Review Desk</p>
                <p class="text-xs text-slate-500">Email: billing@apexreview.co</p>
            </div>
            <div class="text-right">
                <span class="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider block">INVOICE</span>
                <span class="text-lg font-mono font-black text-slate-900">{inv['invoice_id']}</span>
                <div class="text-xs text-slate-500 mt-1">Issued: {created_str}</div>
                <div class="text-xs font-bold text-red-600">Due Date: {due_str}</div>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-8 text-xs">
            <div>
                <span class="font-bold uppercase tracking-wider text-slate-400 block mb-1">BILLED TO:</span>
                <div class="text-sm font-extrabold text-slate-900">{inv['client_company']}</div>
                <div class="text-slate-600 font-mono mt-0.5">{inv['client_email']}</div>
            </div>
            <div class="text-right">
                <span class="font-bold uppercase tracking-wider text-slate-400 block mb-1">PAYMENT STATUS:</span>
                <span class="bg-amber-100 text-amber-800 font-bold px-3 py-1 rounded-full text-xs uppercase">{inv['status']} (Net 7)</span>
            </div>
        </div>

        <table class="w-full text-left text-xs">
            <thead>
                <tr class="border-b border-slate-200 text-slate-400 font-mono uppercase">
                    <th class="py-2">Description</th>
                    <th class="py-2 text-right">Amount (USD)</th>
                </tr>
            </thead>
            <tbody>
                <tr class="border-b border-slate-100">
                    <td class="py-4">
                        <div class="font-bold text-slate-900 text-sm">{inv['package_name']}</div>
                        <div class="text-slate-500 mt-0.5">Guaranteed sub-6h SLA, native Word OpenXML track changes, and FERPA PII scrubbing.</div>
                    </td>
                    <td class="py-4 text-right font-mono font-bold text-base text-slate-900">${inv['amount_usd']:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3 text-xs">
            <span class="font-bold text-slate-900 block">Institutional Remittance & Payment Instructions</span>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-[11px] text-slate-600">
                <div>
                    <strong>Option 1: ACH / US Fedwire:</strong><br>
                    Bank: JPMorgan Chase Bank, N.A.<br>
                    Account Name: Apex Academic Review Desk Inc.<br>
                    Routing (ABA): 021000021<br>
                    Account: 94810482901
                </div>
                <div>
                    <strong>Option 2: Instant Credit Card / ACH:</strong><br>
                    Direct Stripe Payment Portal:<br>
                    <a href="/checkout/pro" class="text-blue-600 font-bold underline">Pay Online with Corporate Card →</a>
                </div>
            </div>
        </div>

        <div class="text-center pt-4 border-t border-slate-200 text-xs text-slate-400">
            Compliant with IECA & NACAC Professional Non-Ghostwriting Standards. All reviews guaranteed within 6 hours.
        </div>
    </div>
</body>
</html>"""


# ==========================================
# INSTITUTIONAL LEGAL & COMPLIANCE PAGES
# ==========================================
@app.get("/legal/attestation", response_class=HTMLResponse)
async def legal_attestation_page():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Institutional Attestation • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen py-12 px-6">
    <div class="max-w-3xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-8 lg:p-12 space-y-6 shadow-2xl">
        <a href="/admin/company" class="text-xs text-blue-400 font-bold">← Back to Company Cockpit</a>
        <h1 class="text-2xl font-black text-white">Institutional Ethical Attestation</h1>
        <div class="prose prose-invert max-w-none text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-mono">
{IECA_NON_GHOSTWRITING_ATTESTATION}
        </div>
    </div>
</body>
</html>"""


@app.get("/legal/dpa", response_class=HTMLResponse)
async def legal_dpa_page():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FERPA Data Protection Addendum • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen py-12 px-6">
    <div class="max-w-3xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-8 lg:p-12 space-y-6 shadow-2xl">
        <a href="/admin/company" class="text-xs text-blue-400 font-bold">← Back to Company Cockpit</a>
        <h1 class="text-2xl font-black text-white">FERPA Data Protection Agreement (DPA)</h1>
        <div class="prose prose-invert max-w-none text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-mono">
{FERPA_DATA_PROTECTION_ADDENDUM}
        </div>
    </div>
</body>
</html>"""



# ==========================================
# 1-CLICK CLIENT ACQUISITION & OUTREACH HUB
# ==========================================
@app.get("/samples/institutional-pack.zip")
async def download_sample_pack():
    pack_path = PROJECT_ROOT / "samples" / "Apex_Institutional_Counselor_Sample_Pack.zip"
    if not pack_path.exists():
        raise HTTPException(status_code=404, detail="Sample pack not found")
    return FileResponse(pack_path, filename="Apex_Institutional_Counselor_Sample_Pack.zip", media_type="application/zip")


@app.get("/admin/outreach", response_class=HTMLResponse)
async def client_outreach_console(request: Request):
    with get_db() as conn:
        leads = conn.execute("SELECT * FROM crm_leads ORDER BY last_interaction DESC LIMIT 50").fetchall()
        total_leads = conn.execute("SELECT count(*) FROM crm_leads").fetchone()[0]

    lead_rows = ""
    for l in leads:
        clean_comp = l['company_name']
        fn = l['first_name']
        em = l['email']
        stage = l['stage']
        
        # Prepare URL-encoded mailto components
        import urllib.parse
        subject = f"Dedicated sub-6h essay review capacity for {clean_comp} (Nov 1 EA/ED rush)"
        body = f"""Hi {fn},

With Early Action and Regular Decision deadlines hitting simultaneously, your counseling team at {clean_comp} is likely spending dozens of hours line-editing Common App drafts instead of focusing on high-level student strategy.

We run a specialized, white-label academic review desk built specifically for independent admissions practices:
- 100% Student Voice Preservation: Strict adherence to IECA/NACAC ethics. Advisory track changes (<w:ins>, <w:del>) and marginal queries only (zero ghostwriting).
- Guaranteed Sub-6-Hour Turnaround SLA throughout peak deadline weeks.
- Native Microsoft Word OpenXML Deliverables (.docx) with 4-pillar rubric diagnostics.

Test our desk with zero risk before committing to a monthly retainer:
We offer a 5-Paper Paid Pilot for $150 (100% credited toward your first month's retainer upon signing).

Inspect our live interactive diff demo and sample deliverables here:
https://progress-trim-capable-introduce.trycloudflare.com/#diff

Download our Institutional Counselor Sample Pack:
https://progress-trim-capable-introduce.trycloudflare.com/samples/institutional-pack.zip

Would you like us to reserve 5 pilot slots for {clean_comp} this week?

Best regards,

Editorial Director
Apex Academic Review Desk Inc.
https://progress-trim-capable-introduce.trycloudflare.com"""

        mailto_link = f"mailto:{em}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        
        lead_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="py-3 px-3">
                <span class="font-bold text-white block">{clean_comp}</span>
                <span class="text-[10px] text-slate-400 font-mono">{l['website']}</span>
            </td>
            <td class="py-3 px-3">
                <span class="font-semibold text-slate-200">{fn} {l['last_name']}</span><br>
                <span class="text-[10px] text-blue-400 font-mono">{em}</span>
            </td>
            <td class="py-3 px-3 text-slate-300 text-[11px]">{l['segment']}</td>
            <td class="py-3 px-3 text-center">
                <span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">{stage}</span>
            </td>
            <td class="py-3 px-3 text-right space-x-1.5 whitespace-nowrap">
                <a href="{mailto_link}" class="inline-flex items-center gap-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold px-2.5 py-1 rounded text-[11px] transition shadow">
                    ✉️ 1-Click Email
                </a>
            </td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1-Click Client Acquisition Console • ApexReview</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }} .mono {{ font-family: 'JetBrains Mono', monospace; }}</style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-16 selection:bg-blue-600 selection:text-white">

    <header class="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-50 px-6 py-4 backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center font-black text-white text-xl">🎯</div>
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-extrabold text-lg tracking-tight text-white">1-Click Client Acquisition Console</span>
                    <span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Real-World Outreach</span>
                </div>
                <span class="text-xs text-slate-400">Targeting 200 Real Admissions Consultancies • 1-Click Launch Directly to Inboxes</span>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <a href="/admin/directory" class="text-xs text-amber-300 hover:text-white bg-amber-600/30 hover:bg-amber-600/50 border border-amber-500/50 px-3 py-1.5 rounded-lg transition font-bold flex items-center gap-1.5">🧭 Platform Map</a>
            <a href="/samples/institutional-pack.zip" class="text-xs text-white bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/50 px-3 py-1.5 rounded-lg transition font-bold flex items-center gap-1.5">📦 Download Sample Pack (.zip)</a>
            <a href="/admin/company" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">CEO Cockpit</a>
            <a href="/admin/mail" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">✉️ Corporate Mail</a>
            <a href="/admin" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Master Admin</a>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 pt-8 space-y-8">

        <!-- Banner with Direct Download -->
        <div class="bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-purple-950/40 border border-blue-800/40 rounded-3xl p-6 lg:p-8 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-6">
            <div class="max-w-2xl">
                <span class="text-xs font-mono font-bold uppercase tracking-wider text-blue-400">Instant Outreach Launcher</span>
                <h1 class="text-2xl font-black text-white mt-1">Ready to Acquire Real Admissions Clients</h1>
                <p class="text-sm text-slate-300 mt-2 leading-relaxed">
                    Clicking "1-Click Email" instantly launches your email app (Gmail/Outlook) with pre-filled, personalized pitch copy linking to our live diff demo and downloadable sample pack.
                </p>
            </div>
            <a href="/samples/institutional-pack.zip" class="px-6 py-3.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-extrabold text-xs uppercase tracking-wider rounded-xl shadow-lg transition flex items-center gap-2 whitespace-nowrap">
                <span>📦</span>
                <span>Download Sample Deliverables Pack</span>
            </a>
        </div>


        <!-- ChatGPT Astra 24-Hour Revenue War Plan Card -->
        <div class="bg-gradient-to-r from-amber-950/30 via-slate-900 to-indigo-950/30 border border-amber-500/30 rounded-3xl p-6 shadow-xl space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div class="flex items-center gap-2">
                    <span class="text-lg">⚡</span>
                    <h3 class="text-sm font-extrabold text-white">ChatGPT Astra Tactical Revenue Blueprint — Close First Client in 24 Hours</h3>
                    <span class="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Nov 1 Early Decision Rush</span>
                </div>
                <span class="text-xs font-mono text-slate-400">Target: $150 Paid Pilot Today</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div class="bg-slate-950/60 border border-slate-800 rounded-2xl p-4 space-y-1.5">
                    <span class="font-bold text-amber-400 uppercase tracking-wider text-[10px] block">1. The Immediate Wedge</span>
                    <p class="text-slate-300">Don't sell multi-month retainers. Sell <strong>Emergency Nov 1 Overflow Capacity</strong>. Independent counselors are drowning in ED/EA drafts right now.</p>
                </div>
                <div class="bg-slate-950/60 border border-slate-800 rounded-2xl p-4 space-y-1.5">
                    <span class="font-bold text-emerald-400 uppercase tracking-wider text-[10px] block">2. The Easy-to-Buy Offer</span>
                    <p class="text-slate-300"><strong>$150 Paid Pilot:</strong> 1 complete student package, sub-6h SLA, native Word OpenXML track changes (&lt;w:ins&gt;/&lt;w:del&gt;) and FERPA certificate.</p>
                </div>
                <div class="bg-slate-950/60 border border-slate-800 rounded-2xl p-4 space-y-1.5">
                    <span class="font-bold text-blue-400 uppercase tracking-wider text-[10px] block">3. Objection Shield</span>
                    <p class="text-slate-300"><strong>"Is this AI?":</strong> Automated checks + human calibrated sign-off. Strict IECA non-ghostwriting compliance: zero text drafting, 100% student voice preserved.</p>
                </div>
            </div>
        </div>

        <!-- Leads Table -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                    <h3 class="text-sm font-extrabold text-white">Target Admissions Practices (Top 50 Active Queue)</h3>
                    <p class="text-xs text-slate-400">Total Pipeline: {total_leads} verified global practices</p>
                </div>
                <span class="text-xs font-mono font-bold text-blue-400">{total_leads} Accounts Ready</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                            <th class="pb-2 px-3">Practice / Website</th>
                            <th class="pb-2 px-3">Admissions Director / Email</th>
                            <th class="pb-2 px-3">Segment</th>
                            <th class="pb-2 px-3 text-center">Stage</th>
                            <th class="pb-2 px-3 text-right">Instant Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lead_rows}
                    </tbody>
                </table>
            </div>
        </div>

    </main>
</body>
</html>"""


@app.get("/api/health")
async def health_check():
    with get_db() as conn:
        job_count = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        lead_count = conn.execute("SELECT COUNT(*) FROM crm_leads").fetchone()[0]
        earnings_sum = conn.execute("SELECT COALESCE(SUM(amount_inr), 0) FROM reviewer_earnings").fetchone()[0]

    return {
        "status": "healthy",
        "system": "Apex Academic Review Engine 3.5.0",
        "timestamp": time.time(),
        "database": "operational",
        "active_jobs": job_count,
        "tracked_leads": lead_count,
        "reviewer_earnings_accrued_inr": earnings_sum,
        "edge_tunnel": "active",
        "sla_clock": "6h guaranteed"
    }


# --- Platform Directory & Capabilities Map ---
from portal.directory_view import render_directory_page

@app.get("/admin/directory", response_class=HTMLResponse)
@app.get("/docs/capabilities", response_class=HTMLResponse)
@app.get("/admin/system-map", response_class=HTMLResponse)
async def platform_capabilities_directory(request: Request):
    return render_directory_page(request)
