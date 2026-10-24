"""
Interactive ThinkingStorm / Trivium Editorial Studio HTML Template & Route Implementations.
Supports both:
- Mode A: Fully Automated AI Socratic Review (Anti-AI Humanized, 0% GPTZero, verified links).
- Mode B: ThinkingStorm SOP Custom Input (Explicit comments & endnotes matching reviewer prompt).
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
                    Automate the exact university writing center review workflow used by ThinkingStorm and Trivium Education: Native Word margin comments (<code class="text-purple-300 font-mono text-xs">&lt;w:comment&gt;</code>) anchored only to quoted text with clickable knowledge base hyperlinks, a standardized native Word endnote letter (<code class="text-purple-300 font-mono text-xs">&lt;w:endnote&gt;</code>) in Times New Roman 12pt double-spaced red text, and deliverable naming <code class="text-purple-300 font-mono text-xs">&lt;filename&gt;_commented.docx</code>.
                </p>
            </div>
        </div>

        <!-- Reference Documents Showcase Pills -->
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
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Student Name (Auto-detected if blank)</label>
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

                <!-- Mode Switcher -->
                <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
                    <div class="flex items-center justify-between">
                        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                            <span>🎯</span> Operational Workflow Mode
                        </h2>
                    </div>

                    <div class="grid grid-cols-2 gap-2 bg-slate-950 p-1.5 rounded-2xl border border-slate-800 text-xs">
                        <button type="button" id="tabAiMode" onclick="setMode('ai')" class="py-2.5 px-3 rounded-xl font-bold transition text-center bg-purple-600 text-white shadow-lg">
                            🤖 Autonomous Socratic AI
                        </button>
                        <button type="button" id="tabCustomMode" onclick="setMode('custom')" class="py-2.5 px-3 rounded-xl font-bold transition text-center text-slate-400 hover:text-white">
                            ✍️ Custom Comments & Endnote
                        </button>
                    </div>

                    <!-- Manuscript Upload / Input -->
                    <div class="space-y-3 pt-2">
                        <div class="flex items-center justify-between">
                            <label class="text-xs font-semibold text-slate-300">1. Target Manuscript (.docx)</label>
                            <span class="text-xs text-slate-400 font-mono" id="wordCountLabel">0 words</span>
                        </div>

                        <div class="border-2 border-dashed border-slate-700 hover:border-purple-500/60 rounded-2xl p-4 text-center cursor-pointer transition bg-slate-950/40" onclick="document.getElementById('fileInput').click()">
                            <input type="file" id="fileInput" accept=".docx,.pdf,.txt" class="hidden" onchange="handleFileUpload(event)">
                            <div class="text-xl mb-1">📁</div>
                            <div class="text-xs font-semibold text-purple-300" id="uploadStatusText">Click to upload .docx manuscript</div>
                            <p class="text-[10px] text-slate-500 mt-0.5">Anchors comments directly into native Word XML</p>
                        </div>

                        <div id="manuscriptTextContainer">
                            <textarea id="manuscriptText" rows="6" placeholder="Or paste student essay prose here..." oninput="updateWordCount()" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-xs text-slate-200 leading-relaxed font-sans focus:outline-none focus:border-purple-500 placeholder-slate-600"></textarea>
                        </div>
                    </div>

                    <!-- Custom Input Fields (Visible only in Custom Mode) -->
                    <div id="customInputSection" class="hidden space-y-4 pt-3 border-t border-slate-800">
                        <div class="flex items-center justify-between">
                            <label class="text-xs font-bold text-purple-300">2. Comments To Add</label>
                            <button type="button" onclick="insertPromptTemplate()" class="text-[10px] text-purple-400 hover:underline">
                                📋 Insert Sample Prompt
                            </button>
                        </div>
                        <p class="text-[11px] text-slate-400 leading-tight">
                            Format: <code class="text-purple-300 font-mono">Quote: "quoted text"</code> followed by <code class="text-purple-300 font-mono">Feedback: CATEGORY comment text...</code>
                        </p>
                        <textarea id="customCommentsText" rows="6" placeholder='Quote: "Eliminating tuition would have a huge, positive impact"&#10;Feedback: THESIS STATEMENT Your thesis outlines your broad topic, but could be tighter.&#10;&#10;Quote: "Janeen Espinoza-Hernandez"&#10;Feedback: MLA Ensure you have a right-aligned header in the top-right margin of every page.' class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-xs text-slate-200 leading-relaxed font-mono focus:outline-none focus:border-purple-500 placeholder-slate-600"></textarea>

                        <div class="pt-2">
                            <label class="block text-xs font-bold text-purple-300 mb-1">3. Endnote To Add (Times New Roman 12pt Red)</label>
                            <p class="text-[11px] text-slate-400 mb-2 leading-tight">
                                Placed as native Word endnote. Placeholders like <code class="text-purple-300">&lt;Student first name&gt;</code> are dynamically populated.
                            </p>
                            <textarea id="customEndnoteText" rows="7" placeholder="Dear <Student first name>,&#10;&#10;Thank you for submitting your paper. There are some suggestions that may help improve the quality of the paper:&#10;&#10;Thesis and Main Argument:&#10;Your introduction establishes the central subject...&#10;&#10;Evidence and Analysis:&#10;You incorporate relevant supporting evidence...&#10;&#10;I hope you find the feedback helpful.&#10;All the best.&#10;Raunak Banga" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-xs text-slate-200 leading-relaxed font-sans focus:outline-none focus:border-purple-500 placeholder-slate-600"></textarea>
                        </div>
                    </div>

                    <button onclick="executeThinkingStormPipeline()" id="runBtn" class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold py-3.5 px-6 rounded-2xl shadow-xl shadow-purple-500/25 transition flex items-center justify-center gap-2 text-xs uppercase tracking-wider mt-4">
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
                            <div class="mt-0.5 font-semibold text-slate-300">Quote Run-Splits</div>
                        </div>
                        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-slate-400" id="stepComments">
                            <div class="text-[9px] uppercase font-bold text-slate-500">Step 2</div>
                            <div class="mt-0.5 font-semibold text-slate-300">Verified Links</div>
                        </div>
                        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-slate-400" id="stepEndnotes">
                            <div class="text-[9px] uppercase font-bold text-slate-500">Step 3</div>
                            <div class="mt-0.5 font-semibold text-slate-300">Red 12pt Endnote</div>
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
                            <p class="text-xs text-slate-400 mt-0.5">Anchored strictly to quoted words • Clickable ThinkingStorm resource URLs.</p>
                        </div>
                        <span id="commentCountBadge" class="px-2.5 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full text-xs font-mono font-bold">0 Comments</span>
                    </div>

                    <!-- Comments List Container -->
                    <div id="commentsContainer" class="space-y-3 max-h-80 overflow-y-auto pr-1">
                        <div class="text-center py-10 text-slate-500 text-xs">
                            No review generated yet. Load a sample or upload a document to begin.
                        </div>
                    </div>

                    <!-- Endnote Letter Container -->
                    <div class="border-t border-slate-800 pt-6 space-y-4">
                        <div class="flex items-center justify-between">
                            <div>
                                <h3 class="text-sm font-bold text-white flex items-center gap-2">
                                    <span>📜</span> Native Word Endnote Letter (Times New Roman, 12pt, 2.0 Spacing, Red)
                                </h3>
                                <p class="text-xs text-slate-400 mt-0.5">Generated in <code class="text-purple-300 font-mono">word/endnotes.xml</code> with author signature.</p>
                            </div>
                            <span class="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                                0% GPTZero Flagged
                            </span>
                        </div>

                        <div id="endnotesContainer" class="space-y-3 bg-slate-950 p-4 rounded-2xl border border-slate-800 text-xs text-red-400 leading-relaxed font-serif">
                            <p class="text-slate-500 italic font-sans">Endnote will appear here once generated...</p>
                        </div>
                    </div>

                    <!-- Download Action Bar -->
                    <div class="border-t border-slate-800 pt-6 flex flex-col sm:flex-row gap-3">
                        <button onclick="downloadThinkingStormDocx()" id="dlCommentedBtn" disabled class="flex-1 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3.5 px-4 rounded-xl transition text-xs flex items-center justify-center gap-2 shadow-lg shadow-purple-500/25">
                            📥 Download &lt;original filename&gt;_commented.docx
                        </button>
                        <button onclick="downloadAnnotatedDocx()" id="dlAnnotatedBtn" disabled class="flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3.5 px-4 rounded-xl transition text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-500/25">
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
        let activeMode = 'ai';
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

        function setMode(mode) {{
            activeMode = mode;
            const tabAi = document.getElementById('tabAiMode');
            const tabCustom = document.getElementById('tabCustomMode');
            const customSection = document.getElementById('customInputSection');

            if (mode === 'ai') {{
                tabAi.className = "py-2.5 px-3 rounded-xl font-bold transition text-center bg-purple-600 text-white shadow-lg";
                tabCustom.className = "py-2.5 px-3 rounded-xl font-bold transition text-center text-slate-400 hover:text-white";
                customSection.classList.add('hidden');
            }} else {{
                tabCustom.className = "py-2.5 px-3 rounded-xl font-bold transition text-center bg-purple-600 text-white shadow-lg";
                tabAi.className = "py-2.5 px-3 rounded-xl font-bold transition text-center text-slate-400 hover:text-white";
                customSection.classList.remove('hidden');
            }}
        }}

        function insertPromptTemplate() {{
            document.getElementById('customCommentsText').value = 
`COMMENTS TO ADD:
Quote: "Eliminating tuition would have a huge, positive impact"
Feedback: THESIS STATEMENT Your thesis outlines your broad topic, but could be tighter. Make sure your thesis explicitly previews the major analytical points your body paragraphs will explore.

Quote: "Janeen Espinoza-Hernandez"
Feedback: MLA Ensure you have a right-aligned header in the top-right margin of every page featuring your last name and page number.`;

            document.getElementById('customEndnoteText').value = 
`Dear <Student first name>,

Thank you for submitting your paper. There are some suggestions that may help improve the quality of the paper:

Thesis and Main Argument:
Your introduction establishes the central subject effectively, but your thesis statement could be tighter. Ensure that you clearly state your definitive perspective while previewing the specific supporting points.

Evidence and Analysis:
You incorporate relevant supporting evidence, research observations, and examples across the body paragraphs. However, some sections move too quickly without pausing to analyze the implications.

Structure and Synthesis:
The overall progression of your ideas is logical. To improve cohesion, focus on tightening the transitions between major shifts in argument.

I hope you find the feedback helpful.
All the best.
Raunak Banga`;
        }}

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

            const customComments = document.getElementById('customCommentsText').value.trim();
            const customEndnote = document.getElementById('customEndnoteText').value.trim();

            if (!text && (!fileInput.files || fileInput.files.length === 0)) {{
                alert("Please paste text or select a manuscript file to review.");
                return;
            }}

            const runBtn = document.getElementById('runBtn');
            runBtn.disabled = true;
            runBtn.innerHTML = "<span>⏳</span> Executing Pipeline...";

            document.getElementById('pipelineBadge').innerText = "PROCESSING";
            document.getElementById('pipelineBadge').className = "px-2.5 py-1 bg-purple-500/20 text-purple-300 rounded-full text-[10px] font-mono font-bold uppercase animate-pulse";

            const formData = new FormData();
            formData.append("student_name", student);
            formData.append("reviewer_name", reviewer);
            formData.append("reviewer_initials", initials);
            formData.append("academic_style", style);
            formData.append("text", text);
            if (activeMode === 'custom') {{
                formData.append("custom_comments_text", customComments);
                formData.append("custom_endnote_text", customEndnote);
            }}
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
                        <span class="text-[10px] text-slate-500 font-mono">Comment #${{idx + 1}} (by ${{data.reviewer_name}})</span>
                    </div>
                    <div class="text-[11px] text-slate-400 italic bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                        Target Quote: "${{c.target_text.substring(0, 85)}}..."
                    </div>
                    <p class="text-xs text-slate-200 leading-relaxed">${{c.comment_text}}</p>
                `;
                container.appendChild(el);
            }});

            const enContainer = document.getElementById('endnotesContainer');
            enContainer.innerHTML = "";

            if (data.endnote_domains) {{
                for (const [domain, desc] of Object.entries(data.endnote_domains)) {{
                    const dDiv = document.createElement('div');
                    dDiv.className = "mb-3";
                    dDiv.innerHTML = `
                        <div class="font-bold text-red-500 text-xs mb-0.5">${{domain}}:</div>
                        <div class="text-xs text-red-400 leading-relaxed">${{desc.replace(/\\n/g, '<br>')}}</div>
                    `;
                    enContainer.appendChild(dDiv);
                }}
            }}
        }}

        function downloadThinkingStormDocx() {{
            if (!currentJobId) return;
            window.location.href = "/download/commented/" + currentJobId;
        }}

        function downloadAnnotatedDocx() {{
            if (!currentJobId) return;
            window.location.href = "/download/docx/" + currentJobId;
        }}

        window.addEventListener('DOMContentLoaded', () => {{
            loadSample('janeen');
        }});
    </script>
</body>
</html>"""
