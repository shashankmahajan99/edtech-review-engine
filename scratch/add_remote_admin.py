from pathlib import Path

SERVER_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py")
content = SERVER_PATH.read_text(encoding="utf-8")

remote_admin_code = '''
# ==========================================
# MOBILE REMOTE CONTROL & OPERATIONS CONSOLE
# ==========================================
@app.get("/admin/remote", response_class=HTMLResponse)
async def mobile_remote_console(request: Request):
    telemetry = get_service_telemetry()
    status_color = "emerald" if telemetry.get("services", {}).get("web_server", {}).get("status") == "UP" else "red"

    # Get recent logs
    recent_logs = "No log output."
    if MONITOR_LOG.exists():
        try:
            lines = MONITOR_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
            recent_logs = "\\n".join(lines[-25:])
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

'''

# Inject right before # SYSTEM HEALTH & MONITORING API
target = "# ==========================================\n# SYSTEM HEALTH & MONITORING API"
if target in content and "/admin/remote" not in content:
    content = content.replace(target, remote_admin_code + "\n\n" + target, 1)
    SERVER_PATH.write_text(content, encoding="utf-8")
    print("Injected /admin/remote successfully!")
else:
    print("/admin/remote already present or target not found.")
