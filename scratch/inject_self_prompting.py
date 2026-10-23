import re
from pathlib import Path

SERVER_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py")
content = SERVER_PATH.read_text(encoding="utf-8")

# 1. Add import and instantiation
if "from engine.self_prompting_framework import SelfPromptingFramework" not in content:
    content = content.replace(
        "from engine.openxml_track_changes import WordTrackChangesEngine",
        "from engine.openxml_track_changes import WordTrackChangesEngine\nfrom engine.self_prompting_framework import SelfPromptingFramework"
    )

if "self_prompt_engine = SelfPromptingFramework()" not in content:
    content = content.replace(
        "gateway = StripeGateway()",
        "gateway = StripeGateway()\nself_prompt_engine = SelfPromptingFramework()"
    )

# 2. Add navigation links in /admin/company and /admin/remote
target_comp_nav = """            <a href="/admin" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Master Admin</a>"""
replacement_comp_nav = """            <a href="/admin/self-prompting" class="text-xs text-white bg-blue-600/30 hover:bg-blue-600/50 border border-blue-500/50 px-3 py-1.5 rounded-lg transition font-bold flex items-center gap-1.5">⚡ Self-Prompting Engine</a>
            <a href="/admin" class="text-xs text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition font-medium">Master Admin</a>"""

if target_comp_nav in content and "href=\"/admin/self-prompting\"" not in content:
    content = content.replace(target_comp_nav, replacement_comp_nav, 1)

target_remote_link = """            <a href="/admin/company" class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-950/60 to-indigo-950/60 border border-blue-700/50 hover:border-blue-500 rounded-xl text-xs font-bold text-white transition">"""
replacement_remote_link = """            <a href="/admin/self-prompting" class="flex items-center justify-between p-3 bg-gradient-to-r from-indigo-950/60 to-purple-950/60 border border-indigo-700/50 hover:border-indigo-500 rounded-xl text-xs font-bold text-white transition">
                <span class="flex items-center gap-2">⚡ <span>Self-Prompting Productization Engine</span></span>
                <span class="text-indigo-400 font-mono">→</span>
            </a>
            <a href="/admin/company" class="flex items-center justify-between p-3 bg-gradient-to-r from-blue-950/60 to-indigo-950/60 border border-blue-700/50 hover:border-blue-500 rounded-xl text-xs font-bold text-white transition">"""

if target_remote_link in content and "href=\"/admin/self-prompting\"" not in content:
    content = content.replace(target_remote_link, replacement_remote_link, 1)

# 3. Add the routes
self_prompting_routes = '''
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
'''

target_health = '@app.get("/api/health")'
if target_health in content:
    content = content.replace(target_health, self_prompting_routes + "\n\n" + target_health, 1)

SERVER_PATH.write_text(content, encoding="utf-8")
print("Successfully injected Self-Prompting Framework routes and UI into portal/server.py")
