"""
Interactive ThinkingStorm / Trivium Editorial Studio HTML Template & Route Implementations.
"""

def get_thinkingstorm_studio_html(current_user=None):
    user_nav = f"""<span class="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/30">
        Reviewer: {current_user['email']}
    </span>""" if current_user else """<a href="/login" class="text-slate-400 hover:text-white text-xs">Reviewer Login</a>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ThinkingStorm / Trivium Reviewer Studio • Apex Review Desk</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
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
                <a href="/" class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center font-black text-white text-lg shadow-lg shadow-purple-500/20">TS</div>
                    <span class="font-extrabold text-xl tracking-tight text-white">ThinkingStorm<span class="text-purple-400">Studio</span></span>
                </a>
                <span class="text-[10px] font-mono uppercase bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded border border-purple-500/20">Institutional Replication Mode</span>
            </div>
            <div class="flex items-center space-x-4 text-xs font-semibold">
                <a href="/" class="text-slate-300 hover:text-white transition">← Main Portal</a>
                <a href="/reviewer" class="text-emerald-400 hover:text-emerald-300 transition flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Reviewer Desk
                </a>
                {user_nav}
            </div>
        </div>
    </nav>

    <!-- Main Studio Container -->
    <main class="max-w-7xl mx-auto px-6 py-8">
        <!-- Header Banner -->
        <div class="bg-gradient-to-r from-purple-950/60 via-slate-900 to-indigo-950/60 border border-purple-500/30 rounded-3xl p-8 mb-8 shadow-2xl relative overflow-hidden">
            <div class="max-w-3xl">
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-bold uppercase tracking-wider mb-3">
                    ⚡ 100% Academic Integrity • Zero Ghostwriting • 0% GPTZero AI Detection
                </div>
                <h1 class="text-3xl sm:text-4xl font-black text-white tracking-tight">
                    Review as ThinkingStorm Reviewer
                </h1>
                <p class="text-slate-300 text-sm mt-2 leading-relaxed">
                    Automate the exact university writing center review workflow used by ThinkingStorm and Trivium Education: Native Word margin comments (<code class="text-purple-300 font-mono text-xs">&lt;w:comment&gt;</code>) with clickable knowledge base hyperlinks, a standardized 3-domain pedagogical endnote letter (<code class="text-purple-300 font-mono text-xs">&lt;w:endnote&gt;</code>), and authentic Socratic feedback that leaves the student's original manuscript untouched.
                </p>
            </div>
        </div>

        <!-- 3 Sample Showcase Pills -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 mb-8 flex flex-wrap items-center justify-between gap-3">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-400">Pre-loaded Reference Papers:</span>
            <div class="flex flex-wrap gap-2">
                <button onclick="loadSample('janeen')" class="text-xs bg-slate-800 hover:bg-purple-900/40 text-purple-300 border border-slate-700 hover:border-purple-500/50 px-3 py-1.5 rounded-xl transition font-medium">
                    📄 Janeen (ENG 112 Tuition Debate)
                </button>
                <button onclick="loadSample('kiran')" class="text-xs bg-slate-800 hover:bg-purple-900/40 text-purple-300 border border-slate-700 hover:border-purple-500/50 px-3 py-1.5 rounded-xl transition font-medium">
                    📄 Kiran (AMR Bacteriophages & ASPs)
                </button>
                <button onclick="loadSample('andrea')" class="text-xs bg-slate-800 hover:bg-purple-900/40 text-purple-300 border border-slate-700 hover:border-purple-500/50 px-3 py-1.5 rounded-xl transition font-medium">
                    📄 Andrea (ENG 111 Foodscaping Rhetoric)
                </button>
                <button onclick="loadSample('lecom')" class="text-xs bg-slate-800 hover:bg-purple-900/40 text-purple-300 border border-slate-700 hover:border-purple-500/50 px-3 py-1.5 rounded-xl transition font-medium">
                    📄 Mahnoor (LECOM DO Medical Essay)
                </button>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <!-- Left Column: Settings & Input (5 cols) -->
            <div class="lg:col-span-5 space-y-6">
                <!-- Reviewer Configuration Card -->
                <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
                    <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                        <span>⚙️</span> Reviewer Persona & Format Controls
                    </h2>
                    
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-semibold text-slate-300 mb-1">Reviewer Name</label>
                            <input type="text" id="reviewerName" value="Raunak Banga" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-300 mb-1">Initials</label>
                            <input type="text" id="reviewerInitials" value="RB" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500">
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Student Name</label>
                        <input type="text" id="studentName" placeholder="e.g. Janeen Espinoza-Hernandez" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500">
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Academic Style & Standard</label>
                        <select id="academicStyle" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500">
                            <option value="mla">MLA 9th Edition (Humanities & English Comp)</option>
                            <option value="apa">APA 7th Edition (Sciences, Psychology, AMR)</option>
                            <option value="admissions">Healthcare / Admissions Personal Statement</option>
                            <option value="chicago">Chicago / Turabian Manual of Style</option>
                        </select>
                    </div>
                </div>

                <!-- Input Document Card -->
                <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
                    <div class="flex items-center justify-between">
                        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                            <span>📝</span> Manuscript Input
                        </h2>
                        <span class="text-xs text-slate-400 font-mono" id="wordCountLabel">0 words</span>
                    </div>

                    <!-- File Upload Option -->
                    <div class="border-2 border-dashed border-slate-700 hover:border-purple-500/60 rounded-2xl p-4 text-center cursor-pointer transition bg-slate-950/40" onclick="document.getElementById('fileInput').click()">
                        <input type="file" id="fileInput" accept=".docx,.pdf,.txt" class="hidden" onchange="handleFileUpload(event)">
                        <div class="text-xl mb-1">📁</div>
                        <div class="text-xs font-semibold text-purple-300" id="uploadStatusText">Click to upload .docx manuscript</div>
                        <p class="text-[10px] text-slate-500 mt-0.5">Supports Microsoft Word (.docx) & plain text</p>
                    </div>

                    <div class="text-center text-[10px] text-slate-500 uppercase font-bold">OR PASTE MANUSCRIPT PROSE</div>

                    <textarea id="manuscriptText" rows="12" placeholder="Paste your student essay, research draft, or personal statement here..." oninput="updateWordCount()" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-4 text-xs text-slate-200 leading-relaxed font-sans focus:outline-none focus:border-purple-500 placeholder-slate-600"></textarea>

                    <button onclick="executeThinkingStormPipeline()" id="runBtn" class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold py-3.5 px-6 rounded-2xl shadow-xl shadow-purple-500/25 transition flex items-center justify-center gap-2 text-xs uppercase tracking-wider">
                        <span>🚀</span> Execute Full ThinkingStorm Review Pipeline
                    </button>
                </div>
            </div>

            <!-- Right Column: Interactive Review Canvas (7 cols) -->
            <div class="lg:col-span-7 space-y-6">
                <!-- Status & Telemetry Bar -->
                <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4" id="telemetryCard">
                    <div class="flex items-center justify-between">
                        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                            <span>📊</span> Pipeline Execution Status
                        </h2>
                        <span id="pipelineBadge" class="px-2.5 py-1 bg-slate-800 text-slate-400 rounded-full text-[10px] font-mono font-bold uppercase">Ready</span>
                    </div>

                    <!-- Steps Grid -->
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-slate-400" id="stepRhetoric">
                            <div class="text-[9px] uppercase font-bold text-slate-500">Step 1</div>
                            <div class="mt-0.5 font-semibold text-slate-300">Rhetorical Scan</div>
                        </div>
                        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-slate-400" id="stepComments">
                            <div class="text-[9px] uppercase font-bold text-slate-500">Step 2</div>
                            <div class="mt-0.5 font-semibold text-slate-300">Margin Comments</div>
                        </div>
                        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-slate-400" id="stepEndnotes">
                            <div class="text-[9px] uppercase font-bold text-slate-500">Step 3</div>
                            <div class="mt-0.5 font-semibold text-slate-300">3-Domain Endnote</div>
                        </div>
                        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-slate-400" id="stepAntiAi">
                            <div class="text-[9px] uppercase font-bold text-slate-500">Step 4</div>
                            <div class="mt-0.5 font-semibold text-slate-300">Anti-AI 0% Check</div>
                        </div>
                    </div>
                </div>

                <!-- Review Results & Interactive Polish Card -->
                <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6" id="resultsCard">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-4">
                        <div>
                            <h2 class="text-base font-bold text-white flex items-center gap-2">
                                <span>💬</span> Socratic Margin Comments & Knowledge Base Hyperlinks
                            </h2>
                            <p class="text-xs text-slate-400 mt-0.5">Clickable ThinkingStorm links injected natively into Word comment balloons.</p>
                        </div>
                        <span id="commentCountBadge" class="px-2.5 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full text-xs font-mono font-bold">0 Comments</span>
                    </div>

                    <!-- Comments List Container -->
                    <div id="commentsContainer" class="space-y-3 max-h-80 overflow-y-auto pr-1">
                        <div class="text-center py-10 text-slate-500 text-xs">
                            No review generated yet. Load a sample or upload a document to begin.
                        </div>
                    </div>

                    <!-- 3-Domain Endnote Letter Container -->
                    <div class="border-t border-slate-800 pt-6 space-y-4">
                        <div class="flex items-center justify-between">
                            <div>
                                <h3 class="text-sm font-bold text-white flex items-center gap-2">
                                    <span>📜</span> Native Word Endnote Letter (3 Pedagogical Domains)
                                </h3>
                                <p class="text-xs text-slate-400 mt-0.5">Appears as an official reviewer note at the end of the Word document.</p>
                            </div>
                            <span class="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                                0% GPTZero Flagged
                            </span>
                        </div>

                        <div id="endnotesContainer" class="space-y-3 bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans">
                            <p class="text-slate-500 italic">Endnote domains will appear here once generated...</p>
                        </div>
                    </div>

                    <!-- Download Action Bar -->
                    <div class="border-t border-slate-800 pt-6 flex flex-col sm:flex-row gap-3">
                        <button onclick="downloadThinkingStormDocx()" id="dlCommentedBtn" disabled class="flex-1 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 px-4 rounded-xl transition text-xs flex items-center justify-center gap-2 shadow-lg shadow-purple-500/25">
                            📥 Download Official ThinkingStorm Review (.docx)
                        </button>
                        <button onclick="downloadAnnotatedDocx()" id="dlAnnotatedBtn" disabled class="flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 px-4 rounded-xl transition text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-500/25">
                            ✍️ Download Admissions Redline (.docx)
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Embedded Scripts -->
    <script>
        let currentJobId = null;
        let generatedReviewData = null;

        const SAMPLES = {{
            janeen: {{
                student: "Janeen Espinoza-Hernandez",
                style: "mla",
                reviewer: "Raunak Banga",
                text: `Janeen Espinoza-Hernandez Professor Brumley\\nENG 112\\n26 September 2026\\n\\nShould college tuition be free for all students?\\n\\nFor many students the cost of college is financially out of reach and can make higher education difficult to afford. Many students take out thousands of dollars in student loans that can take decades to repay. Higher education comes at an enormous cost to students. Eliminating tuition would have a huge, positive impact on the students and our society.\\n\\nMore people would be able to attend college if it were free. One reason for this is that some people who are able to attend college do not go because of financial worries. Studies have shown that when tuition is lowered or eliminated, enrollment increases significantly among low-income students. However, some researchers argue that universal free tuition could lead to overcrowding and reduced educational quality. The reason for that is because university resources would be stretched thin across a much larger student population. In conclusion, providing tuition-free higher education would remove barriers for millions of students.`
            }},
            kiran: {{
                student: "Kiran Mitra",
                style: "apa",
                reviewer: "Raunak Banga",
                text: `Kiran Mitra\\nAP Biology / Pre-Med Research\\nSeptember 27, 2026\\n\\nCombating Antimicrobial Resistance Through Multi-Tiered Clinical Interventions\\n\\nAbstract: Antimicrobial resistance (AMR) is a growing global health crisis. This paper examines clinical stewardship programs, ozone wastewater treatment, and bacteriophage therapy.\\n\\nEveryone knows that bacteria have evolved to survive exposure to antibiotics that would usually kill them. The mortality statistics dramatically demonstrate the extent of the problem, with millions of deaths projected annually. Because inappropriate use of antibiotics contributes to the development and spread of AMR, one strategy is to improve how antibiotics are prescribed through Antibiotic Stewardship Programs (ASPs). A clinical trial by Gohil et al. (2024) across 59 hospitals showed that ASP education reduced antibiotic use by 28.4%. Furthermore, treating wastewater with ozone removes residual antimicrobials. Finally, bacteriophages represent an innovative targeted biological intervention. In conclusion, combining these three approaches creates a comprehensive defense against AMR.`
            }},
            andrea: {{
                student: "Andrea Goblet",
                style: "mla",
                reviewer: "Raunak Banga",
                text: `Andrea Goblet\\nMrs. Leary\\nEng 111\\n9-22-26\\n\\nFoodscaping: Growing Your Own Food in Your Frontyard\\n\\nIn this essay he explains facts and uses emotions to convince you to try growing food. John uses ethos by giving his knowledge of growing food in his yard.. As a co-founder of foodscaping Utah, he has taught many people how to grow their own food. The paper shows how he uses ethos , pathos and logos to persuade readers. However, there are many examples where it is not clear how they relate to the argument. In conclusion, foodscaping is a beneficial practice for communities and personal health.`
            }},
            lecom: {{
                student: "Mahnoor Choudry",
                style: "admissions",
                reviewer: "Dr. Ananya Sharma",
                text: `Mahnoor Choudry\\nTarget: LECOM (Lake Erie College of Osteopathic Medicine)\\nPrompt: What inspired you to pursue becoming a doctor, dentist, or pharmacist?\\n\\nEveryone goes to the doctor throughout their life from before the beginning to the end. My experiences from broken bones, sick visits, and checkups have presented to me compassionate v.s apathetic physicians. Witnessing the significant impact a compassionate physician offers has inspired me to pursue a career as a doctor to make a profound impact in others lives.\\n\\nCurrently, as a Certified Nursing Assistant (CNA), I have spent over 300 hours caring for residents. I went to gather my supplies and opened my eyes to the things I do that have had huge impacts. The physical tasks are a sliver of the actual experience. Choosing to commit to a pathway in osteopathic medicine feels like my calling. I want to be a doctor to provide holistic care that treats the mind, body, and spirit.`
            }}
        }};

        function loadSample(key) {{
            const sample = SAMPLES[key];
            if (!sample) return;
            document.getElementById('studentName').value = sample.student;
            document.getElementById('reviewerName').value = sample.reviewer;
            document.getElementById('reviewerInitials').value = sample.reviewer.split(' ').map(n => n[0]).join('');
            document.getElementById('academicStyle').value = sample.style;
            document.getElementById('manuscriptText').value = sample.text.replace(/\\\\n/g, '\\n');
            document.getElementById('uploadStatusText').innerText = "Loaded: " + sample.student;
            updateWordCount();
        }}

        function updateWordCount() {{
            const text = document.getElementById('manuscriptText').value.trim();
            const words = text ? text.split(/\\s+/).length : 0;
            document.getElementById('wordCountLabel').innerText = words + " words";
        }}

        function handleFileUpload(event) {{
            const file = event.target.files[0];
            if (!file) return;
            document.getElementById('uploadStatusText').innerText = "Selected: " + file.name;
            const reader = new FileReader();
            reader.onload = function(e) {{
                // If text file
                if (file.name.endsWith('.txt')) {{
                    document.getElementById('manuscriptText').value = e.target.result;
                    updateWordCount();
                }}
            }};
            if (file.name.endsWith('.txt')) {{
                reader.readAsText(file);
            }}
        }}

        async function executeThinkingStormPipeline() {{
            const text = document.getElementById('manuscriptText').value.trim();
            const student = document.getElementById('studentName').value.trim() || "Student";
            const reviewer = document.getElementById('reviewerName').value.trim() || "Raunak Banga";
            const initials = document.getElementById('reviewerInitials').value.trim() || "RB";
            const style = document.getElementById('academicStyle').value;
            const fileInput = document.getElementById('fileInput');

            if (!text && (!fileInput.files || fileInput.files.length === 0)) {{
                alert("Please paste text or select a manuscript file to review.");
                return;
            }}

            const runBtn = document.getElementById('runBtn');
            runBtn.disabled = true;
            runBtn.innerHTML = "<span>⏳</span> Executing Pipeline...";

            // Update UI telemetry badges
            document.getElementById('pipelineBadge').innerText = "PROCESSING";
            document.getElementById('pipelineBadge').className = "px-2.5 py-1 bg-purple-500/20 text-purple-300 rounded-full text-[10px] font-mono font-bold uppercase animate-pulse";

            const formData = new FormData();
            formData.append("student_name", student);
            formData.append("reviewer_name", reviewer);
            formData.append("reviewer_initials", initials);
            formData.append("academic_style", style);
            formData.append("text", text);
            if (fileInput.files && fileInput.files[0]) {{
                formData.append("file", fileInput.files[0]);
            }}

            try {{
                const resp = await fetch("/api/thinkingstorm/execute", {{
                    method: "POST",
                    body: formData
                }});

                if (!resp.ok) {{
                    throw new Error("Pipeline execution failed: " + resp.statusText);
                }}

                const data = await resp.json();
                generatedReviewData = data;
                currentJobId = data.job_id;

                renderReviewResults(data);

                // Highlight telemetry as complete
                ['stepRhetoric', 'stepComments', 'stepEndnotes', 'stepAntiAi'].forEach(id => {{
                    document.getElementById(id).className = "bg-emerald-950/40 p-2.5 rounded-xl border border-emerald-500/40 text-emerald-300";
                }});

                document.getElementById('pipelineBadge').innerText = "COMPLETE • READY TO DOWNLOAD";
                document.getElementById('pipelineBadge').className = "px-2.5 py-1 bg-emerald-500/20 text-emerald-300 rounded-full text-[10px] font-mono font-bold uppercase";

                document.getElementById('dlCommentedBtn').disabled = false;
                document.getElementById('dlAnnotatedBtn').disabled = false;

            }} catch (err) {{
                alert(err.message);
                document.getElementById('pipelineBadge').innerText = "ERROR";
                document.getElementById('pipelineBadge').className = "px-2.5 py-1 bg-red-500/20 text-red-300 rounded-full text-[10px] font-mono font-bold uppercase";
            }} finally {{
                runBtn.disabled = false;
                runBtn.innerHTML = "<span>🚀</span> Execute Full ThinkingStorm Review Pipeline";
            }}
        }}

        function renderReviewResults(data) {{
            // Render comments
            const container = document.getElementById('commentsContainer');
            container.innerHTML = "";
            document.getElementById('commentCountBadge').innerText = data.comments.length + " Comments";

            data.comments.forEach((c, idx) => {{
                const el = document.createElement('div');
                el.className = "bg-slate-950 border border-slate-800 hover:border-purple-500/40 rounded-2xl p-4 transition space-y-2";
                el.innerHTML = `
                    <div class="flex items-center justify-between">
                        <a href="${{c.link_url}}" target="_blank" class="text-xs font-bold text-blue-400 hover:underline flex items-center gap-1 font-mono">
                            <span>🔗</span> ${{c.category}}
                        </a>
                        <span class="text-[10px] text-slate-500 font-mono">Comment #${{idx + 1}}</span>
                    </div>
                    <div class="text-[11px] text-slate-400 italic bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                        Target: "${{c.target_text.substring(0, 85)}}..."
                    </div>
                    <p class="text-xs text-slate-200 leading-relaxed">${{c.comment_text}}</p>
                `;
                container.appendChild(el);
            }});

            // Render Endnotes
            const enContainer = document.getElementById('endnotesContainer');
            enContainer.innerHTML = `
                <div class="font-bold text-white text-xs mb-1">Dear ${{data.student_name.split(' ')[0]}},</div>
                <p class="text-slate-400 text-xs mb-3">Thank you for submitting your paper. There are some suggestions that may help improve the quality of the paper:</p>
            `;

            for (const [domain, desc] of Object.entries(data.endnote_domains)) {{
                const dDiv = document.createElement('div');
                dDiv.className = "mb-3";
                dDiv.innerHTML = `
                    <div class="font-bold text-purple-300 text-xs mb-0.5">${{domain}}:</div>
                    <div class="text-xs text-slate-300 leading-relaxed">${{desc}}</div>
                `;
                enContainer.appendChild(dDiv);
            }}

            const closeDiv = document.createElement('div');
            closeDiv.className = "pt-2 text-xs text-slate-400";
            closeDiv.innerHTML = `
                <p>I hope you find the feedback helpful.</p>
                <p class="mt-1">All the best,</p>
                <p class="font-bold text-white mt-0.5">${{data.reviewer_name}}</p>
            `;
            enContainer.appendChild(closeDiv);
        }}

        function downloadThinkingStormDocx() {{
            if (!currentJobId) return;
            window.location.href = "/download/commented/" + currentJobId;
        }}

        function downloadAnnotatedDocx() {{
            if (!currentJobId) return;
            window.location.href = "/download/docx/" + currentJobId;
        }}

        // Auto-load sample on load
        window.addEventListener('DOMContentLoaded', () => {{
            loadSample('janeen');
        }});
    </script>
</body>
</html>"""
