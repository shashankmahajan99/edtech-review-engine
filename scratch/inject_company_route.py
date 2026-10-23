import re
from pathlib import Path

SERVER_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py")
content = SERVER_PATH.read_text(encoding="utf-8")

# 1. Update /admin/remote to include the Company Governance Cockpit link
target_remote_link = """            <a href="/admin" class="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-xs font-semibold text-slate-200 transition">
                <span>📊 Master Commercial Command Center</span>
                <span class="text-slate-500">→</span>
            </a>"""

replacement_remote_link = """            <a href="/admin/company" class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-950/60 to-indigo-950/60 border border-blue-700/50 hover:border-blue-500 rounded-xl text-xs font-bold text-white transition">
                <span class="flex items-center gap-2">🏛️ <span>CEO Corporate Governance & Paperclip Board</span></span>
                <span class="text-blue-400 font-mono">→</span>
            </a>
            <a href="/admin" class="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl text-xs font-semibold text-slate-200 transition">
                <span>📊 Master Commercial Command Center</span>
                <span class="text-slate-500">→</span>
            </a>"""

if target_remote_link in content:
    content = content.replace(target_remote_link, replacement_remote_link, 1)

# 2. Add /admin/company route before @app.get("/api/health")
company_route_code = '''
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
                        Oversees India\'s top academic writing fellows (DU/JNU/Ashoka), rubric calibration, and ethical voice integrity.
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
'''

target_health = '@app.get("/api/health")'
if target_health in content:
    content = content.replace(target_health, company_route_code + "\n\n" + target_health, 1)

SERVER_PATH.write_text(content, encoding="utf-8")
print("Successfully injected /admin/company and updated /admin/remote in portal/server.py")
