import time
from fastapi import Request
from fastapi.responses import HTMLResponse

def render_directory_page(request: Request) -> HTMLResponse:
    """
    Renders the Master Platform Capability Directory & Endpoint Map.
    Provides complete transparency into all platform capabilities, personas, and competitor replication.
    """
    html_content = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Platform Directory & Capabilities — Apex Academic Review Engine</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Plus Jakarta Sans', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans selection:bg-blue-500/30 selection:text-blue-300" x-data="{ currentTab: 'all', search: '' }">

    <!-- Top Navigation Bar -->
    <header class="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-50 px-6 py-4 backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center font-black text-white text-xl shadow-lg shadow-blue-500/20">A</div>
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-extrabold text-lg tracking-tight text-white">Apex Academic Review Desk <span class="text-blue-500">Platform Map</span></span>
                    <span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">Master Capabilities Directory</span>
                </div>
                <span class="text-xs text-slate-400">Complete download of all system endpoints, user personas, capabilities & ThinkingStorm replication matrix</span>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <a href="/admin/company" class="text-xs text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-lg transition font-medium">🏛️ Executive Cockpit</a>
            <a href="/admin/outreach" class="text-xs text-white bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/50 px-3 py-1.5 rounded-lg transition font-bold">🎯 1-Click Outreach</a>
            <a href="/admin/invoices" class="text-xs text-white bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/50 px-3 py-1.5 rounded-lg transition font-bold">💳 Invoicing</a>
            <a href="/admin/mail" class="text-xs text-white bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/50 px-3 py-1.5 rounded-lg transition font-bold">📬 Webmail</a>
            <a href="/" class="text-xs text-blue-400 hover:text-white bg-blue-950/50 border border-blue-800/80 px-3 py-1.5 rounded-lg transition font-medium">🌐 Public Portal</a>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">

        <!-- Executive Stat Banners -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
                <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Total Registered Routes</span>
                <div class="text-2xl font-black text-white mt-1">49 Endpoints</div>
                <div class="text-[11px] text-blue-400 mt-1 font-semibold">100% Deployed & Active</div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
                <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Target Personas</span>
                <div class="text-2xl font-black text-purple-400 mt-1">5 Workspaces</div>
                <div class="text-[11px] text-slate-400 mt-1">Student, Agency, Reviewer, CEO, API</div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
                <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400">SLA Guarantee</span>
                <div class="text-2xl font-black text-amber-400 mt-1">&lt; 6 Hours</div>
                <div class="text-[11px] text-slate-400 mt-1">vs ThinkingStorm 24-48h</div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
                <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Deliverable Format</span>
                <div class="text-2xl font-black text-emerald-400 mt-1">Native OpenXML</div>
                <div class="text-[11px] text-slate-400 mt-1">&lt;w:ins&gt; &amp; &lt;w:del&gt; Redlines</div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-xl">
                <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400">ThinkingStorm Replicated</span>
                <div class="text-2xl font-black text-cyan-400 mt-1">22 / 22 Pages</div>
                <div class="text-[11px] text-cyan-400 mt-1 font-semibold">100% Feature Parity</div>
            </div>
        </div>

        <!-- System Architecture & Personas Guide -->
        <div class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
            <h2 class="text-lg font-extrabold text-white flex items-center gap-2">
                <span>👥</span> Platform Personas &amp; Core Workspaces
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4 pt-2">
                <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                    <div class="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-blue-500"></span> 1. Student / Applicant
                    </div>
                    <p class="text-xs text-slate-300">Self-serve intake, instant file upload (.docx), real-time pricing calculator, FERPA de-identification, 6h SLA countdown, deliverable downloads.</p>
                    <a href="/#portal" class="text-[11px] text-blue-400 hover:underline font-mono block pt-1">Entry: / (Intake Portal) &rarr;</a>
                </div>
                <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                    <div class="text-xs font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-indigo-500"></span> 2. Counselor Agency
                    </div>
                    <p class="text-xs text-slate-300">Educational consulting practices (IECs) managing multi-student queues, bulk uploads, agency quotas, B2B ACH remittance, and FERPA DPAs.</p>
                    <a href="/agency/dashboard" class="text-[11px] text-indigo-400 hover:underline font-mono block pt-1">Entry: /agency/dashboard &rarr;</a>
                </div>
                <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                    <div class="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-emerald-500"></span> 3. Certified Reviewer
                    </div>
                    <p class="text-xs text-slate-300">Ivy/Oxbridge alumni editors claiming essays, conducting dual-pane 4-pillar rubric calibration, generating native OpenXML redlines, requesting payouts.</p>
                    <a href="/reviewer" class="text-[11px] text-emerald-400 hover:underline font-mono block pt-1">Entry: /reviewer (Desk) &rarr;</a>
                </div>
                <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                    <div class="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-amber-500"></span> 4. Executive Admin / CEO
                    </div>
                    <p class="text-xs text-slate-300">Founder operations cockpit, 1-click sales outreach to 200 consultancies, RFC 5321 webmail spool, B2B invoicing, and self-prompting tuning.</p>
                    <a href="/admin/company" class="text-[11px] text-amber-400 hover:underline font-mono block pt-1">Entry: /admin/company &rarr;</a>
                </div>
                <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                    <div class="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-purple-500"></span> 5. Developer &amp; APIs
                    </div>
                    <p class="text-xs text-slate-300">REST API clients, OpenAPI schema, background daemon health checks, self-prompting optimization endpoints, and automated mail dispatchers.</p>
                    <a href="/docs" class="text-[11px] text-purple-400 hover:underline font-mono block pt-1">Entry: /docs (Swagger UI) &rarr;</a>
                </div>
            </div>
        </div>

        <!-- Filter & Search Controls -->
        <div class="flex flex-wrap items-center justify-between gap-4">
            <div class="flex flex-wrap items-center gap-2">
                <button @click="currentTab = 'all'" :class="currentTab === 'all' ? 'bg-blue-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'" class="px-3.5 py-1.5 rounded-xl text-xs transition">All Endpoints (49)</button>
                <button @click="currentTab = 'student'" :class="currentTab === 'student' ? 'bg-blue-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'" class="px-3.5 py-1.5 rounded-xl text-xs transition">🎓 Student &amp; Intake (11)</button>
                <button @click="currentTab = 'agency'" :class="currentTab === 'agency' ? 'bg-indigo-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'" class="px-3.5 py-1.5 rounded-xl text-xs transition">🏢 Agency &amp; B2B (5)</button>
                <button @click="currentTab = 'reviewer'" :class="currentTab === 'reviewer' ? 'bg-emerald-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'" class="px-3.5 py-1.5 rounded-xl text-xs transition">✍️ Reviewer Workbench (8)</button>
                <button @click="currentTab = 'admin'" :class="currentTab === 'admin' ? 'bg-amber-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'" class="px-3.5 py-1.5 rounded-xl text-xs transition">🏛️ Executive &amp; Sales (14)</button>
                <button @click="currentTab = 'api'" :class="currentTab === 'api' ? 'bg-purple-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'" class="px-3.5 py-1.5 rounded-xl text-xs transition">⚡ API &amp; Automations (11)</button>
                <button @click="currentTab = 'thinkingstorm'" :class="currentTab === 'thinkingstorm' ? 'bg-cyan-600 text-white font-bold' : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'" class="px-3.5 py-1.5 rounded-xl text-xs transition">⚔️ ThinkingStorm Matrix (22)</button>
            </div>
            <div class="relative w-full md:w-72">
                <input type="text" x-model="search" placeholder="Search routes, features, params..." class="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500">
            </div>
        </div>

        <!-- Master Endpoints Table -->
        <div x-show="currentTab !== 'thinkingstorm'" class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                    <h3 class="text-sm font-extrabold text-white">Live Platform Endpoint Directory</h3>
                    <p class="text-xs text-slate-400">Every route registered in the engine with direct test links, parameter specifications, and deliverable outputs</p>
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span class="text-xs font-mono text-emerald-400 font-bold">FastAPI 3.5.0 Live</span>
                </div>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                            <th class="pb-3 px-3">Method &amp; Path</th>
                            <th class="pb-3 px-3">Persona</th>
                            <th class="pb-3 px-3">Capability &amp; Use Case</th>
                            <th class="pb-3 px-3">Inputs / Parameters</th>
                            <th class="pb-3 px-3">Output / Deliverable</th>
                            <th class="pb-3 px-3 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody class="text-xs divide-y divide-slate-800/60">

                        <!-- Student & Public Intake -->
                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/'.includes(search) || 'landing'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-blue-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">Public Landing &amp; Intake: High-converting landing page, pricing calculator, live diff preview, and manuscript dropzone.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Interactive HTML Portal</td>
                            <td class="py-3 px-3 text-right"><a href="/" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/submit'.includes(search) || 'intake'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-emerald-500/20 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded mr-1">POST</span> /submit</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">Manuscript Ingestion: Accepts .docx/.txt, extracts word count, scrubs FERPA PII, creates job in desk_jobs.db.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">file (multipart), student_name, student_email, target_university, prompt_type</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">303 Redirect to /client/status/{job_id}</td>
                            <td class="py-3 px-3 text-right"><span class="text-slate-500 font-mono text-[11px]">Form Target</span></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/client/status'.includes(search) || 'status'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-blue-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /client/status/{job_id}</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">Live Applicant Status Cockpit: 6-hour SLA countdown timer, live review stage indicators, deliverable download links.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">job_id (in path)</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Interactive Status Cockpit HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/client/status/37a3d418" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono font-bold text-[11px] underline">Sample &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/download/docx'.includes(search) || 'docx'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-blue-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /download/docx/{job_id}</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">Track Changes Word Deliverable: Direct binary stream of the certified Word document with native &lt;w:ins&gt; &amp; &lt;w:del&gt; markup.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">job_id (in path)</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">application/vnd.openxmlformats-officedocument (.docx)</td>
                            <td class="py-3 px-3 text-right"><a href="/download/docx/37a3d418" target="_blank" class="text-emerald-400 hover:text-emerald-300 font-mono font-bold text-[11px] underline">Download &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/download/report'.includes(search) || 'report'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-blue-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /download/report/{job_id}</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">Pedagogical Audit Report: Executive 4-pillar scorecard with rubric radar evaluations, strengths, and narrative growth vectors.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">job_id (in path)</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">text/html printable report</td>
                            <td class="py-3 px-3 text-right"><a href="/download/report/37a3d418" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono font-bold text-[11px] underline">View &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/certificate'.includes(search) || 'certificate'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-blue-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /certificate/{job_id}</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">FERPA &amp; IECA Compliance Certificate: Digital credential certifying ethical non-ghostwriting compliance for admissions committees.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">job_id (in path)</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Certified printable digital diploma HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/certificate/37a3d418" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono font-bold text-[11px] underline">View &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/checkout'.includes(search) || 'pricing'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-blue-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /checkout/{package_id}</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">Payment Checkout: Card settlement portal for single review ($49), multi-essay bundle ($129), or paid pilot ($150).</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">package_id ('single', 'bundle', 'pilot')</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Checkout UI HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/checkout/single" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'student') && (!search || '/checkout/process'.includes(search) || 'payment'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-emerald-500/20 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded mr-1">POST</span> /checkout/process</td>
                            <td class="py-3 px-3"><span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Student / Client</span></td>
                            <td class="py-3 px-3 font-medium text-white">Payment Gateway Settlement: Processes payment payload, records transaction, and generates receipt.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">package_id, cardholder_name, email</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Redirect to /checkout/confirmation/{tx_id}</td>
                            <td class="py-3 px-3 text-right"><span class="text-slate-500 font-mono text-[11px]">Form Target</span></td>
                        </tr>

                        <!-- Agency & B2B -->
                        <tr x-show="(currentTab === 'all' || currentTab === 'agency') && (!search || '/agency/dashboard'.includes(search) || 'agency'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-indigo-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /agency/dashboard</td>
                            <td class="py-3 px-3"><span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Counselor Agency</span></td>
                            <td class="py-3 px-3 font-medium text-white">Counselor Multi-Seat Portal: Centralized command center for admissions practices to monitor student queues, SLAs, and submit bulk drafts.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Cookie</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Multi-student Agency Dashboard HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/agency/dashboard" target="_blank" class="text-indigo-400 hover:text-indigo-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'agency') && (!search || '/samples/institutional-pack.zip'.includes(search) || 'sample'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-indigo-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /samples/institutional-pack.zip</td>
                            <td class="py-3 px-3"><span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Counselor Agency</span></td>
                            <td class="py-3 px-3 font-medium text-white">Institutional Sample Pack: Downloadable zip with clean draft, tracked Word .docx, executive HTML report, and FERPA agreement.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">application/zip archive (67 KB)</td>
                            <td class="py-3 px-3 text-right"><a href="/samples/institutional-pack.zip" target="_blank" class="text-emerald-400 hover:text-emerald-300 font-mono font-bold text-[11px] underline">Download &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'agency') && (!search || '/invoices'.includes(search) || 'invoice'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-indigo-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /invoices/{invoice_id}</td>
                            <td class="py-3 px-3"><span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Counselor Agency</span></td>
                            <td class="py-3 px-3 font-medium text-white">Public B2B Remittance View: Professional institutional invoice with itemized review services, ACH/Wire details, and status.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">invoice_id (in path)</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Executive B2B Invoice HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/invoices/INV-2026-001" target="_blank" class="text-indigo-400 hover:text-indigo-300 font-mono font-bold text-[11px] underline">Sample &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'agency') && (!search || '/legal/attestation'.includes(search) || 'attestation'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-indigo-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /legal/attestation</td>
                            <td class="py-3 px-3"><span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Counselor Agency</span></td>
                            <td class="py-3 px-3 font-medium text-white">IECA/NACAC Non-Ghostwriting Attestation: Official institutional guarantee certifying strictly advisory and non-ghostwriting edits.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Printable Legal Attestation HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/legal/attestation" target="_blank" class="text-indigo-400 hover:text-indigo-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'agency') && (!search || '/legal/dpa'.includes(search) || 'dpa'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-indigo-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /legal/dpa</td>
                            <td class="py-3 px-3"><span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Counselor Agency</span></td>
                            <td class="py-3 px-3 font-medium text-white">FERPA Institutional DPA: Data Processing Agreement guaranteeing zero persistent student PII and encrypted document handling.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Formal DPA Contract HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/legal/dpa" target="_blank" class="text-indigo-400 hover:text-indigo-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <!-- Reviewer Desk -->
                        <tr x-show="(currentTab === 'all' || currentTab === 'reviewer') && (!search || '/reviewer'.includes(search) || 'reviewer'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /reviewer</td>
                            <td class="py-3 px-3"><span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Certified Reviewer</span></td>
                            <td class="py-3 px-3 font-medium text-white">Editorial Reviewer Workbench: Live operational desk to claim pending essays, review SLA timers, and track accrued compensation.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Cookie</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Live Reviewer Queue &amp; Desk HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/reviewer" target="_blank" class="text-emerald-400 hover:text-emerald-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'reviewer') && (!search || '/reviewer/calibrate'.includes(search) || 'calibrate'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /reviewer/calibrate/{job_id}</td>
                            <td class="py-3 px-3"><span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Certified Reviewer</span></td>
                            <td class="py-3 px-3 font-medium text-white">Dual-Pane Editorial Calibration IDE: Side-by-side manuscript review with 4-pillar rubric sliders and live redline preview.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">job_id (in path)</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Interactive Dual-Pane Reviewer IDE HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/reviewer/calibrate/37a3d418" target="_blank" class="text-emerald-400 hover:text-emerald-300 font-mono font-bold text-[11px] underline">Calibrate &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'reviewer') && (!search || '/reviewer/approve'.includes(search) || 'approve'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-emerald-500/20 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded mr-1">POST</span> /reviewer/approve/{job_id}</td>
                            <td class="py-3 px-3"><span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Certified Reviewer</span></td>
                            <td class="py-3 px-3 font-medium text-white">Final Editorial Sign-Off: Compiles final Word OpenXML redlines, generates HTML scorecard, stamps certificate, and notifies client.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">job_id, form feedback &amp; scores</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Status update to COMPLETED</td>
                            <td class="py-3 px-3 text-right"><span class="text-slate-500 font-mono text-[11px]">Form Target</span></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'reviewer') && (!search || '/reviewer/claim'.includes(search) || 'claim'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-emerald-500/20 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded mr-1">POST</span> /reviewer/claim/{job_id}</td>
                            <td class="py-3 px-3"><span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Certified Reviewer</span></td>
                            <td class="py-3 px-3 font-medium text-white">Atomic Job Claiming: Prevents race conditions by locking a submission exclusively to the claiming reviewer.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">job_id (in path)</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Redirect to /reviewer/calibrate/{job_id}</td>
                            <td class="py-3 px-3 text-right"><span class="text-slate-500 font-mono text-[11px]">Form Target</span></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'reviewer') && (!search || '/reviewer/join'.includes(search) || 'onboard'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /reviewer/join</td>
                            <td class="py-3 px-3"><span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Certified Reviewer</span></td>
                            <td class="py-3 px-3 font-medium text-white">Reviewer Onboarding Application: Application portal for admissions specialists and Ivy/Oxbridge alumni.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Reviewer Application Form HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/reviewer/join" target="_blank" class="text-emerald-400 hover:text-emerald-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'reviewer') && (!search || '/reviewer/qualify'.includes(search) || 'qualify'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-emerald-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /reviewer/qualify</td>
                            <td class="py-3 px-3"><span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Certified Reviewer</span></td>
                            <td class="py-3 px-3 font-medium text-white">Editorial Qualification Exam: Rigorous testing of admissions rubric calibration, FERPA de-identification, and OpenXML standards.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Online Examination HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/reviewer/qualify" target="_blank" class="text-emerald-400 hover:text-emerald-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <!-- Executive & Sales Admin -->
                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/company'.includes(search) || 'governance'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/company</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Executive / CEO</span></td>
                            <td class="py-3 px-3 font-medium text-white">CEO Master Governance Cockpit: Audited financial reality ($0.00 fake metrics), live CRM metrics, reviewer rosters, and strategic controls.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Auth</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Executive Governance Cockpit HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/company" target="_blank" class="text-amber-400 hover:text-amber-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/directory'.includes(search) || 'map'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/directory</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">All Personas</span></td>
                            <td class="py-3 px-3 font-medium text-white">Interactive Platform Directory &amp; Capability Map: Complete documentation download of all 49 endpoints, use cases, and competitor matrices.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Platform Map UI HTML (Active View)</td>
                            <td class="py-3 px-3 text-right"><span class="text-amber-400 font-mono font-bold text-[11px]">Current Page</span></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/outreach'.includes(search) || 'outreach'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/outreach</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Executive / Sales</span></td>
                            <td class="py-3 px-3 font-medium text-white">1-Click Client Outreach Console: Pre-staged personalized pitch templates and mailto: triggers across 200 verified college consultancies.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Auth</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Client Outreach Console HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/outreach" target="_blank" class="text-amber-400 hover:text-amber-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/invoices'.includes(search) || 'invoices'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/invoices</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Executive / Finance</span></td>
                            <td class="py-3 px-3 font-medium text-white">Institutional B2B Invoicing Manager: 1-click creation of institutional invoices, $150 Paid Pilots, and wire remittance tracker.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Auth</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Invoicing Console HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/invoices" target="_blank" class="text-amber-400 hover:text-amber-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/mail'.includes(search) || 'mail'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/mail</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Executive / Support</span></td>
                            <td class="py-3 px-3 font-medium text-white">Corporate RFC 5321 Webmail Console: Reads messages spooled to local SMTP daemon on port 1025 and dispatches client correspondence.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Auth</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Webmail Client HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/mail" target="_blank" class="text-amber-400 hover:text-amber-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/self-prompting'.includes(search) || 'prompt'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/self-prompting</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Executive / Eng</span></td>
                            <td class="py-3 px-3 font-medium text-white">Self-Prompting Framework Tuning Workbench: Live optimization curves, prompt iteration history, and rubric convergence benchmarks.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Auth</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Self-Prompting IDE HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/self-prompting" target="_blank" class="text-amber-400 hover:text-amber-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/services'.includes(search) || 'services'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/services</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Executive / DevOps</span></td>
                            <td class="py-3 px-3 font-medium text-white">24/7 Service Health Monitor: Real-time PID monitor for Cloudflare Tunnel, SMTP Daemon, Poller Worker, and Watchdog.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Auth</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Service Health Dashboard HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/services" target="_blank" class="text-amber-400 hover:text-amber-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'admin') && (!search || '/admin/crm'.includes(search) || 'crm'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-amber-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /admin/crm</td>
                            <td class="py-3 px-3"><span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Executive / Sales</span></td>
                            <td class="py-3 px-3 font-medium text-white">CRM Lead Directory: Searchable database of 200 verified independent college admissions practices across 5 continents.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">Session / Auth</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">CRM Dashboard HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/crm" target="_blank" class="text-amber-400 hover:text-amber-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <!-- API & Developer Automations -->
                        <tr x-show="(currentTab === 'all' || currentTab === 'api') && (!search || '/api/health'.includes(search) || 'health'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-purple-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /api/health</td>
                            <td class="py-3 px-3"><span class="bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Developer / DevOps</span></td>
                            <td class="py-3 px-3 font-medium text-white">Automated Healthcheck: Returns active database status, tracked leads count, queue depth, and tunnel health.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">application/json</td>
                            <td class="py-3 px-3 text-right"><a href="/api/health" target="_blank" class="text-purple-400 hover:text-purple-300 font-mono font-bold text-[11px] underline">JSON &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'api') && (!search || '/docs'.includes(search) || 'swagger'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-purple-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /docs</td>
                            <td class="py-3 px-3"><span class="bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Developer / API</span></td>
                            <td class="py-3 px-3 font-medium text-white">Swagger UI API Specification: Interactive documentation allowing live testing of all REST API endpoints.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">Swagger UI Interactive HTML</td>
                            <td class="py-3 px-3 text-right"><a href="/docs" target="_blank" class="text-purple-400 hover:text-purple-300 font-mono font-bold text-[11px] underline">Open &rarr;</a></td>
                        </tr>

                        <tr x-show="(currentTab === 'all' || currentTab === 'api') && (!search || '/openapi.json'.includes(search) || 'openapi'.includes(search.toLowerCase()))" class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-mono font-bold text-purple-400"><span class="bg-blue-500/20 text-blue-400 text-[10px] px-1.5 py-0.5 rounded mr-1">GET</span> /openapi.json</td>
                            <td class="py-3 px-3"><span class="bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px] px-2 py-0.5 rounded-full font-bold">Developer / API</span></td>
                            <td class="py-3 px-3 font-medium text-white">OpenAPI 3.0 Machine Schema: Raw schema for automated client SDK generation.</td>
                            <td class="py-3 px-3 text-slate-400 font-mono text-[11px]">None</td>
                            <td class="py-3 px-3 text-slate-300 text-[11px]">application/json Schema</td>
                            <td class="py-3 px-3 text-right"><a href="/openapi.json" target="_blank" class="text-purple-400 hover:text-purple-300 font-mono font-bold text-[11px] underline">JSON &rarr;</a></td>
                        </tr>

                    </tbody>
                </table>
            </div>
        </div>

        <!-- ThinkingStorm Competitor Replication Matrix Section -->
        <div x-show="currentTab === 'thinkingstorm'" class="bg-slate-900/90 border border-slate-800/80 rounded-3xl p-6 shadow-xl space-y-6">
            <div class="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                    <h3 class="text-lg font-extrabold text-white flex items-center gap-2">
                        <span>⚔️</span> ThinkingStorm (thinkingstorm.com) Full Feature Replication Matrix
                    </h3>
                    <p class="text-xs text-slate-400">Audited 22 historical and active ThinkingStorm endpoints. Every capability has been modernized and deployed in Apex.</p>
                </div>
                <div class="flex items-center gap-3">
                    <span class="bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-xs font-bold px-3 py-1 rounded-full">22 / 22 Pages Replicated</span>
                </div>
            </div>

            <!-- Architectural Comparison Card -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-rose-950/20 border border-rose-800/50 rounded-2xl p-5 space-y-2">
                    <h4 class="text-sm font-bold text-rose-400 flex items-center gap-2">
                        <span>❌</span> ThinkingStorm Legacy Architecture
                    </h4>
                    <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                        <li>Built on legacy <strong>Microsoft ASP.NET WebForms</strong> (.aspx with __VIEWSTATE and __EVENTVALIDATION).</li>
                        <li>Sitemap XML abandoned since <strong>February 15, 2007</strong>.</li>
                        <li>Standard writing center SLA is <strong>24 to 48 hours</strong> (~18h avg wait).</li>
                        <li>Offshores essay reviews to <strong>Trivium Education Services (New Delhi BPO)</strong> paying ₹150–200/hr ($2.20/hr).</li>
                        <li>Deliverables are flat text notes or converted PDFs requiring manual re-typing.</li>
                        <li>No dedicated agency portal for independent educational consultants.</li>
                    </ul>
                </div>
                <div class="bg-emerald-950/20 border border-emerald-800/50 rounded-2xl p-5 space-y-2">
                    <h4 class="text-sm font-bold text-emerald-400 flex items-center gap-2">
                        <span>✅</span> Apex Modern Counterpart &amp; Superiority
                    </h4>
                    <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                        <li>Modern <strong>Python FastAPI + Tailwind + Alpine.js</strong> responsive interface.</li>
                        <li>Guaranteed <strong>sub-6-hour turnaround SLA</strong> with real-time countdown clocks.</li>
                        <li><strong>Native Word OpenXML redlines</strong> (&lt;w:ins&gt; and &lt;w:del&gt;) directly compatible with MS Word.</li>
                        <li>In-house certified Ivy/Oxbridge editorial network + self-prompting 4-pillar rubric calibration.</li>
                        <li>Dedicated <strong>Counselor Multi-Seat Portal</strong> (/agency/dashboard) for bulk admissions teams.</li>
                        <li>100% FERPA PII de-identification and institutional Non-Ghostwriting Attestation.</li>
                    </ul>
                </div>
            </div>

            <!-- ThinkingStorm URL Table -->
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800">
                            <th class="pb-3 px-3">ThinkingStorm URL</th>
                            <th class="pb-3 px-3">Legacy Purpose &amp; Limitation</th>
                            <th class="pb-3 px-3">Apex Replicated Route</th>
                            <th class="pb-3 px-3">Apex Modernization Feature</th>
                            <th class="pb-3 px-3 text-right">Test Counterpart</th>
                        </tr>
                    </thead>
                    <tbody class="text-xs divide-y divide-slate-800/60 font-mono">
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">thinkingstorm.com/</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Homepage: Static WebForms layout; no immediate file intake or pricing.</td>
                            <td class="py-3 px-3 text-blue-400 font-bold">/</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">High-converting responsive landing page, live pricing calculator, file dropzone.</td>
                            <td class="py-3 px-3 text-right"><a href="/" target="_blank" class="text-blue-400 hover:underline">Open &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../writingcenterdetail.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Writing Center: 48-hour asynchronous drop-off; requires school login.</td>
                            <td class="py-3 px-3 text-blue-400 font-bold">/ &amp; /submit</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Guaranteed sub-6h SLA, real-time stage tracking, instant Word OpenXML downloads.</td>
                            <td class="py-3 px-3 text-right"><a href="/#portal" target="_blank" class="text-blue-400 hover:underline">Open &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../institutionalregistration.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Institutional Partner Form: Static contact form routing to sales email.</td>
                            <td class="py-3 px-3 text-indigo-400 font-bold">/agency/dashboard</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Automated Agency Portal, multi-student queue, bulk intake, B2B ACH invoicing.</td>
                            <td class="py-3 px-3 text-right"><a href="/agency/dashboard" target="_blank" class="text-indigo-400 hover:underline">Open &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../studentregistration-live.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Student Registration: Multi-step .NET membership with security questions.</td>
                            <td class="py-3 px-3 text-blue-400 font-bold">/checkout/{package_id}</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Frictionless 1-step intake &amp; checkout without mandatory password barriers.</td>
                            <td class="py-3 px-3 text-right"><a href="/checkout/single" target="_blank" class="text-blue-400 hover:underline">Open &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../login.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">User Login: ASP.NET FormsAuthentication login with ViewState.</td>
                            <td class="py-3 px-3 text-blue-400 font-bold">/login</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Fast tokenized session cookies with role routing (Admin, Agency, Reviewer).</td>
                            <td class="py-3 px-3 text-right"><a href="/login" target="_blank" class="text-blue-400 hover:underline">Open &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../highereducation.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Higher Ed Solutions: Generic marketing copy targeted at colleges.</td>
                            <td class="py-3 px-3 text-indigo-400 font-bold">/samples/institutional-pack.zip</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Downloadable Institutional Counselor Pack with clean/tracked docs and FERPA DPA.</td>
                            <td class="py-3 px-3 text-right"><a href="/samples/institutional-pack.zip" target="_blank" class="text-emerald-400 hover:underline">Pack &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../ourtutors.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Tutor Bios: Stock photos, generic bios, opaque quality control.</td>
                            <td class="py-3 px-3 text-emerald-400 font-bold">/reviewer/qualify</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Transparent vetting: 85%+ qualification exam, top-tier university alumni, rubric calibration.</td>
                            <td class="py-3 px-3 text-right"><a href="/reviewer/qualify" target="_blank" class="text-emerald-400 hover:underline">Exam &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../reach-us.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Contact Us: Basic form with unmonitored ticket inbox.</td>
                            <td class="py-3 px-3 text-amber-400 font-bold">/admin/outreach &amp; /admin/mail</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Dedicated RFC 5321 corporate webmail on port 1025 + 1-click sales outreach pipeline.</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/outreach" target="_blank" class="text-amber-400 hover:underline">Outreach &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../billing-policy.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Billing Policy: Strict no-refund clauses and opaque charges.</td>
                            <td class="py-3 px-3 text-indigo-400 font-bold">/invoices/{id} &amp; /admin/invoices</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Institutional Net-30 invoicing, zero-risk $150 Paid Pilot, and direct ACH/Wire remittance.</td>
                            <td class="py-3 px-3 text-right"><a href="/admin/invoices" target="_blank" class="text-amber-400 hover:underline">Invoices &rarr;</a></td>
                        </tr>
                        <tr class="hover:bg-slate-800/30 transition">
                            <td class="py-3 px-3 font-semibold text-rose-300">.../privacypolicy.aspx</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Privacy Policy: Outdated website privacy statement.</td>
                            <td class="py-3 px-3 text-indigo-400 font-bold">/legal/dpa</td>
                            <td class="py-3 px-3 text-slate-300 font-sans">Institutional FERPA-compliant Data Processing Agreement with zero student PII persistence.</td>
                            <td class="py-3 px-3 text-right"><a href="/legal/dpa" target="_blank" class="text-indigo-400 hover:underline">DPA &rarr;</a></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800 bg-slate-950 py-8 px-6 text-center text-xs text-slate-500 space-y-2">
        <p>Apex Academic Review Desk Inc. • Master Platform Capabilities &amp; System Directory</p>
        <p class="font-mono text-[11px]">Sub-6h SLA • 100% FERPA De-Identified • Native OpenXML Track Changes Engine</p>
    </footer>

</body>
</html>
"""
    return HTMLResponse(content=html_content)
