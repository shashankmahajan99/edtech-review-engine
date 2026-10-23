import re
from pathlib import Path

SERVER_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py")
content = SERVER_PATH.read_text(encoding="utf-8")

outreach_routes = '''
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
'''

target_health = '@app.get("/api/health")'
if target_health in content:
    content = content.replace(target_health, outreach_routes + "\n\n" + target_health, 1)

# Also add link to /admin/outreach in the top of /admin/company
target_comp_nav = '<a href="/admin/self-prompting"'
comp_addition = '<a href="/admin/outreach" class="text-xs text-white bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/50 px-3 py-1.5 rounded-lg transition font-bold flex items-center gap-1.5">🎯 1-Click Outreach</a>\n            '
if target_comp_nav in content and "href=\"/admin/outreach\"" not in content:
    content = content.replace(target_comp_nav, comp_addition + target_comp_nav, 1)

SERVER_PATH.write_text(content, encoding="utf-8")
print("SUCCESS: Injected 1-Click Client Acquisition Console and Sample Pack download into portal/server.py")
