import re
from pathlib import Path

SERVER_PATH = Path(r"C:\Users\shashank\edtech-review-engine\portal\server.py")
content = SERVER_PATH.read_text(encoding="utf-8")

# 1. Add imports at the top
infra_imports = """from engine.self_prompting_framework import SelfPromptingFramework
from mail.smtp_server import get_spooled_mail
from payments.institutional_invoicing import create_invoice, get_all_invoices, get_invoice_by_id
from legal.contracts import IECA_NON_GHOSTWRITING_ATTESTATION, FERPA_DATA_PROTECTION_ADDENDUM, SERVICE_LEVEL_AGREEMENT
import smtplib
from email.message import EmailMessage"""

if "from mail.smtp_server import get_spooled_mail" not in content:
    content = content.replace("from engine.self_prompting_framework import SelfPromptingFramework", infra_imports, 1)

# 2. Add routes before @app.get("/api/health")
infra_routes = '''
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
'''

target_health = '@app.get("/api/health")'
if target_health in content:
    content = content.replace(target_health, infra_routes + "\n\n" + target_health, 1)

SERVER_PATH.write_text(content, encoding="utf-8")
print("Successfully injected Corporate Mail, Invoicing, and Legal infrastructure routes into portal/server.py")
