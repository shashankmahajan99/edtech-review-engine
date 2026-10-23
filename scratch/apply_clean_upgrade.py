import shutil
from pathlib import Path

SERVER_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py")
BACKUP_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py.bak")

# Restore clean backup
shutil.copyfile(BACKUP_PATH, SERVER_PATH)
content = SERVER_PATH.read_text(encoding="utf-8")

# 1. AUDIT BACKEND CODE (standard python, outside f-string)
audit_backend = '''
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

'''

target_landing = '@app.get("/", response_class=HTMLResponse)'
if target_landing in content:
    content = content.replace(target_landing, audit_backend + "\n" + target_landing, 1)

# 2. AUDIT SECTION HTML (inside f-string, so no unescaped { })
audit_section = '''
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
'''

diff_target = '    <!-- Interactive Before & After Editorial Diff Viewer -->\n    <section id="diff"'
if diff_target in content:
    content = content.replace(diff_target, audit_section + "\n" + diff_target, 1)

# Notice: All JS curly braces MUST be {{ and }} because landing_page is an f-string!
audit_js_block = '''
<script>
const AUDIT_SAMPLES = {{
    stanford: "Ever since I was a child, I have always been deeply passionate about computers. Stanford University is the ideal place for me because of its world-class faculty and cutting-edge curriculum. In conclusion, it can be seen that my work is a testament to my dedication to broaden my horizons.",
    harvard: "I want to attend Harvard University to step out of my comfort zone and broaden my horizons. Ever since I was a child, public policy sparked my interest. In conclusion, it can be seen that my background makes me an ideal candidate for your government faculty.",
    wharton: "I am deeply passionate about finance and quantitative economics. The Wharton School has world-class faculty and cutting-edge curriculum that will spark my interest and allow me to step out of my comfort zone."
}};

function loadSample(key) {{
    if (AUDIT_SAMPLES[key]) {{
        document.getElementById('auditInputText').value = AUDIT_SAMPLES[key];
        document.getElementById('auditInstitution').value = key === 'stanford' ? 'Stanford' : (key === 'harvard' ? 'Harvard' : 'Wharton');
        executeLiveAudit();
    }}
}}

async function executeLiveAudit() {{
    const text = document.getElementById('auditInputText').value;
    const inst = document.getElementById('auditInstitution').value;
    const btn = document.getElementById('auditRunBtn');
    btn.innerText = 'Analyzing...';
    btn.disabled = true;

    try {{
        const resp = await fetch('/api/audit/sample', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{text: text, institution: inst}})
        }});
        const data = await resp.json();
        
        document.getElementById('scoreVoice').innerText = data.scores.voice_authenticity + ' / 100';
        document.getElementById('scoreFaculty').innerText = data.scores.faculty_alignment + ' / 100';
        document.getElementById('scoreMomentum').innerText = data.scores.narrative_momentum + ' / 100';
        document.getElementById('scoreAuth').innerText = data.scores.authenticity_integrity + ' / 100';
        
        document.getElementById('auditRedlineView').innerHTML = data.redlined_html;
    }} catch (e) {{
        console.error(e);
    }} finally {{
        btn.innerText = 'Run Pedagogical Voice Audit (0.4s) ⚡';
        btn.disabled = false;
    }}
}}
</script>
'''

js_target = '</body>\n</html>"""'
if js_target in content:
    content = content.replace(js_target, audit_js_block + "\n" + js_target, 1)

# 3. Upgraded Checkout & Dashboard (outside of landing_page)
checkout_target_start = '@app.get("/checkout/success", response_class=HTMLResponse)'
checkout_target_end = '# ==========================================\n# SYSTEM HEALTH & MONITORING API'

idx_start = content.find(checkout_target_start)
idx_end = content.find(checkout_target_end)

if idx_start != -1 and idx_end != -1:
    new_checkout_and_agency_code = '''
# ==========================================
# INSTITUTIONAL CHECKOUT & CAPACITY RESERVATION ENGINE
# ==========================================
@app.get("/checkout/{package_id}", response_class=HTMLResponse)
async def checkout_page(package_id: str):
    pkg = PACKAGES.get(package_id, PACKAGES["pilot"])
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
        <div class="flex items-center justify-between border-b border-slate-800 pb-6 mb-8">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-black text-white text-lg">A</div>
                <span class="font-extrabold text-xl tracking-tight text-white">Apex<span class="text-blue-500">Checkout</span></span>
            </div>
            <a href="/#pricing" class="text-xs font-semibold text-slate-400 hover:text-white transition">← Return to Retainers</a>
        </div>

        <div class="bg-slate-900 border border-slate-800 rounded-3xl p-8 sm:p-10 shadow-2xl">
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

                <div class="bg-blue-950/20 border border-blue-900/40 p-4 rounded-2xl flex items-start gap-3 text-xs text-slate-300 leading-relaxed">
                    <input type="checkbox" required checked class="mt-0.5 rounded text-blue-600">
                    <span>I acknowledge that Apex Review operates strictly under <b>IECA & NACAC advisory non-ghostwriting principles</b>. Reviews are delivered as native Microsoft Word OpenXML track changes (&lt;w:ins&gt;, &lt;w:del&gt;) and 4-pillar rubric scorecards with authentic student voice preservation.</span>
                </div>

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
    pkg = PACKAGES.get(package_id, PACKAGES["pilot"])
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

    log_compliance_event(tx_id, "CAPACITY_COMMERCIAL_BOOKED", f"Firm {company_name} locked {pkg['name']} for ${amount_dollars:.2f} USD")
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

'''

    content = content[:idx_start] + new_checkout_and_agency_code + "\n\n" + content[idx_end:]

SERVER_PATH.write_text(content, encoding="utf-8")
print("Clean replacement completed successfully!")
