"""ThinkingStorm Studio page.

One screen, one flow: add a manuscript, run the review, download the files.
Everything the engine can do is visible without hidden modes.
"""


def get_thinkingstorm_studio_html(user=None) -> str:
    signed_in = (user or {}).get("email", "guest")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ThinkingStorm Studio</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  body {{ font-family: 'Inter', sans-serif; }}
  .card {{ background: #0f172a; border: 1px solid #1e293b; }}
  .field {{ background: #020617; border: 1px solid #1e293b; color: #e2e8f0; }}
  .field:focus {{ outline: none; border-color: #7c3aed; }}
  .tab-active {{ background: #312e81; color: #c7d2fe; }}
  .comment-body {{ white-space: pre-wrap; }}
</style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">

<header class="border-b border-slate-800 bg-slate-950/95 sticky top-0 z-20">
  <div class="max-w-7xl mx-auto px-5 h-14 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <span class="text-lg font-extrabold tracking-tight">Apex Review</span>
      <span class="text-[10px] font-bold uppercase tracking-widest text-purple-300 bg-purple-950/50 border border-purple-800 px-2 py-0.5 rounded-full">Studio</span>
    </div>
    <nav class="flex items-center gap-5 text-sm">
      <a href="/" class="text-slate-400 hover:text-white">Home</a>
      <a href="/reviewer" class="text-slate-400 hover:text-white">Reviewer Desk</a>
      <a href="/thinkingstorm" class="text-white font-semibold">Studio</a>
      <span class="text-slate-600">|</span>
      <span class="text-xs text-slate-500">{signed_in}</span>
    </nav>
  </div>
</header>

<main class="max-w-7xl mx-auto px-5 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6">

  <!-- ============ 1. INPUT ============ -->
  <section class="lg:col-span-5 space-y-4">
    <div class="card rounded-2xl p-6">
      <h1 class="text-xl font-bold">Review a manuscript</h1>
      <p class="text-sm text-slate-400 mt-1">
        Upload the student's file or paste the text. You get the same document back,
        unchanged, with comments in the margin and the endnote letter at the end.
      </p>

      <form id="reviewForm" class="mt-6 space-y-5">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-400 mb-2">1 · Manuscript</label>
          <label for="fileInput" id="dropZone"
                 class="flex flex-col items-center justify-center gap-1 border-2 border-dashed border-slate-700 hover:border-purple-500 rounded-xl px-4 py-7 cursor-pointer transition text-center">
            <span class="text-2xl">📄</span>
            <span id="fileName" class="text-sm font-semibold text-slate-200">Choose a .docx, .pdf or .txt</span>
            <span class="text-[11px] text-slate-500">The original formatting is preserved.</span>
          </label>
          <input type="file" id="fileInput" name="file" accept=".docx,.pdf,.txt,.md" class="hidden">
        </div>

        <div class="flex items-center gap-3 text-[11px] uppercase tracking-widest text-slate-600">
          <span class="h-px flex-1 bg-slate-800"></span>or paste text<span class="h-px flex-1 bg-slate-800"></span>
        </div>

        <div>
          <textarea id="manuscriptText" name="text" rows="6" placeholder="Paste the essay here…"
                    class="field w-full rounded-xl p-3 text-sm leading-relaxed"></textarea>
          <div class="flex justify-between text-[11px] text-slate-500 mt-1">
            <span>Paste only if you are not uploading a file.</span>
            <span><span id="wordCount">0</span> words</span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wide text-slate-400 mb-1">Student</label>
            <input id="studentName" name="student_name" value="Student" class="field w-full rounded-lg px-3 py-2 text-sm">
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wide text-slate-400 mb-1">Style</label>
            <select id="academicStyle" name="academic_style" class="field w-full rounded-lg px-3 py-2 text-sm">
              <option value="auto">Auto-detect</option>
              <option value="mla">MLA</option>
              <option value="apa">APA</option>
              <option value="admissions">Admissions</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wide text-slate-400 mb-1">Reviewer</label>
            <input id="reviewerName" name="reviewer_name" value="Raunak Banga" class="field w-full rounded-lg px-3 py-2 text-sm">
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wide text-slate-400 mb-1">Initials</label>
            <input id="reviewerInitials" name="reviewer_initials" value="RB" class="field w-full rounded-lg px-3 py-2 text-sm">
          </div>
        </div>

        <details class="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
          <summary class="text-xs font-bold uppercase tracking-wide text-slate-400 cursor-pointer">
            Advanced · inject exact comments or an endnote
          </summary>
          <p class="text-[11px] text-slate-500 mt-2">
            Fill either box to use your own text instead of the generated review.
            Leave both empty for the automatic review.
          </p>
          <textarea id="customComments" name="custom_comments_text" rows="4"
                    placeholder='Quote: "…"&#10;Feedback: THESIS STATEMENT …'
                    class="field w-full rounded-lg p-3 text-xs mt-3"></textarea>
          <textarea id="customEndnote" name="custom_endnote_text" rows="4"
                    placeholder="Dear Student, …"
                    class="field w-full rounded-lg p-3 text-xs mt-3"></textarea>
        </details>

        <button id="runBtn" type="submit"
                class="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-bold py-3 rounded-xl transition">
          Run complete review
        </button>
        <p id="statusLine" class="text-xs text-slate-500 text-center">
          Deterministic engine · no model calls · usually under 2 seconds
        </p>
      </form>
    </div>

    <div class="card rounded-2xl p-5 text-xs text-slate-400 leading-relaxed">
      <div class="font-bold text-slate-300 mb-1">What you get</div>
      <ul class="space-y-1 list-disc list-inside">
        <li><b class="text-slate-200">Commented .docx</b> — your original file with margin comments and the endnote letter. Nothing else changes.</li>
        <li><b class="text-slate-200">Tracked changes .docx</b> — the same original with mechanical edits as Word revisions.</li>
        <li><b class="text-slate-200">Report .html</b> — rubric scores, priority actions and the summary.</li>
      </ul>
    </div>
  </section>

  <!-- ============ 2. OUTPUT ============ -->
  <section class="lg:col-span-7">
    <div id="errorBanner" class="hidden mb-4 rounded-xl border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-200"></div>
    <div id="warningBanner" class="hidden mb-4 rounded-xl border border-amber-800 bg-amber-950/40 px-4 py-3 text-xs text-amber-200"></div>

    <div id="emptyState" class="card rounded-2xl p-10 text-center">
      <div class="text-3xl">🗂️</div>
      <div class="font-bold text-slate-300 mt-3">No review yet</div>
      <p class="text-sm text-slate-500 mt-2 max-w-sm mx-auto">
        Add a manuscript on the left and run the review. Results, downloads and the
        comment list will appear here.
      </p>
    </div>

    <div id="results" class="hidden space-y-4">
      <div class="card rounded-2xl p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="flex items-center gap-2">
              <span class="text-emerald-400 text-lg">✓</span>
              <h2 class="text-lg font-bold">Review complete</h2>
            </div>
            <p class="text-xs text-slate-500 mt-1">Job <span id="jobId" class="font-mono"></span> · <span id="studentLabel"></span></p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-extrabold text-purple-300"><span id="overallScore">–</span><span class="text-sm text-slate-500">/100</span></div>
            <div class="text-[10px] uppercase tracking-widest text-slate-500">Rubric</div>
          </div>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5" id="statsGrid"></div>

        <p id="summary" class="text-sm text-slate-300 leading-relaxed mt-5"></p>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3" id="downloads"></div>
      </div>

      <div class="card rounded-2xl overflow-hidden">
        <div class="flex items-center gap-1 border-b border-slate-800 px-3 pt-3">
          <button data-tab="comments" class="tab-btn tab-active text-xs font-bold px-4 py-2 rounded-t-lg">Comments <span id="commentCount" class="opacity-70"></span></button>
          <button data-tab="endnote" class="tab-btn text-xs font-bold px-4 py-2 rounded-t-lg text-slate-400 hover:text-white">Endnote</button>
          <button data-tab="rubric" class="tab-btn text-xs font-bold px-4 py-2 rounded-t-lg text-slate-400 hover:text-white">Rubric</button>
        </div>

        <div id="tab-comments" class="tab-panel p-4 space-y-3 max-h-[36rem] overflow-y-auto"></div>
        <div id="tab-endnote" class="tab-panel hidden p-5 space-y-3 max-h-[36rem] overflow-y-auto"></div>
        <div id="tab-rubric" class="tab-panel hidden p-5 max-h-[36rem] overflow-y-auto"></div>
      </div>
    </div>
  </section>
</main>

<script>
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));

$('fileInput').addEventListener('change', (e) => {{
  const f = e.target.files[0];
  if (f) {{
    $('fileName').textContent = f.name + " · " + Math.round(f.size / 1024) + " KB";
    $('dropZone').classList.add('border-purple-500');
  }}
}});

const textarea = $('manuscriptText');
textarea.addEventListener('input', () => {{
  const words = textarea.value.trim() ? textarea.value.trim().split(/\\s+/).length : 0;
  $('wordCount').textContent = words;
}});

document.querySelectorAll('.tab-btn').forEach((btn) => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab-btn').forEach((b) => {{
      b.classList.remove('tab-active');
      b.classList.add('text-slate-400');
    }});
    btn.classList.add('tab-active');
    btn.classList.remove('text-slate-400');
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));
    $('tab-' + btn.dataset.tab).classList.remove('hidden');
  }});
}});

function showError(message) {{
  const banner = $('errorBanner');
  banner.textContent = message;
  banner.classList.remove('hidden');
}}

function clearBanners() {{
  $('errorBanner').classList.add('hidden');
  $('warningBanner').classList.add('hidden');
}}

function stat(label, value) {{
  return `<div class="rounded-xl bg-slate-900 border border-slate-800 px-3 py-2">
    <div class="text-lg font-extrabold text-white">${{esc(value)}}</div>
    <div class="text-[10px] uppercase tracking-widest text-slate-500">${{esc(label)}}</div>
  </div>`;
}}

function render(data) {{
  $('emptyState').classList.add('hidden');
  $('results').classList.remove('hidden');

  $('jobId').textContent = data.job_id;
  $('studentLabel').textContent = data.student_name;
  $('overallScore').textContent = data.overall_score ?? '–';
  $('summary').textContent = data.executive_summary || '';

  const cov = data.coverage || {{}};
  $('statsGrid').innerHTML =
    stat('Words', data.word_count) +
    stat('Comments', data.comments.length) +
    stat('Paragraphs', cov.paragraphs ? cov.commented + '/' + cov.paragraphs : '–') +
    stat('Endnote', Object.values(data.endnote_domains || {{}}).join(' ').split(/\\s+/).filter(Boolean).length + 'w');

  const dl = [
    ['Commented .docx', data.commented_docx_url, 'Your original file + comments + endnote', 'bg-purple-600 hover:bg-purple-500'],
    ['Tracked changes .docx', data.annotated_docx_url, 'Original formatting, edits as revisions', 'bg-slate-700 hover:bg-slate-600'],
    ['Report .html', data.report_url, 'Rubric, actions, summary', 'bg-slate-800 hover:bg-slate-700 border border-slate-700'],
  ];
  if (data.qa_report_url) {{
    dl.push(['QA report .json', data.qa_report_url, 'Every finding and gate metric', 'bg-slate-800 hover:bg-slate-700 border border-slate-700']);
  }}
  $('downloads').innerHTML = dl.map(([label, href, hint, cls]) => `
    <a href="${{href}}" class="block rounded-xl px-4 py-3 text-center text-white transition ${{cls}}">
      <div class="text-sm font-bold">${{label}}</div>
      <div class="text-[10px] opacity-70 mt-0.5">${{hint}}</div>
    </a>`).join('');

  $('commentCount').textContent = '(' + data.comments.length + ')';
  $('tab-comments').innerHTML = data.comments.map((c, i) => `
    <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div class="flex items-center justify-between gap-3">
        <a href="${{esc(c.link_url)}}" target="_blank" class="text-[11px] font-bold text-purple-300 hover:underline uppercase tracking-wide">${{esc(c.category)}}</a>
        <span class="text-[10px] text-slate-600 font-mono">#${{i + 1}}</span>
      </div>
      <div class="text-xs italic text-slate-400 bg-slate-950/70 border border-slate-800 rounded-lg px-3 py-2 mt-2 comment-body">“${{esc(c.target_text)}}”</div>
      <p class="text-sm text-slate-200 leading-relaxed mt-2 comment-body">${{esc(c.comment_text)}}</p>
    </div>`).join('');

  $('tab-endnote').innerHTML = Object.entries(data.endnote_domains || {{}}).map(([title, body]) => `
    <div>
      <div class="text-xs font-bold text-red-400 uppercase tracking-wide">${{esc(title)}}</div>
      <p class="text-sm text-red-200/90 leading-relaxed mt-1 comment-body">${{esc(body)}}</p>
    </div>`).join('');

  const rubric = data.rubric || {{}};
  $('tab-rubric').innerHTML = `
    <table class="w-full text-sm">
      <thead><tr class="text-[10px] uppercase tracking-widest text-slate-500">
        <th class="text-left pb-2">Domain</th><th class="text-left pb-2 w-16">Score</th><th class="text-left pb-2">Verdict</th>
      </tr></thead>
      <tbody>${{Object.entries(rubric).map(([key, v]) => `
        <tr class="border-t border-slate-800">
          <td class="py-2 pr-3 font-semibold text-slate-200">${{esc(v.label || key)}}</td>
          <td class="py-2 pr-3 text-purple-300 font-bold">${{v.score}}/25</td>
          <td class="py-2 text-slate-400">${{esc(v.verdict)}}</td>
        </tr>`).join('')}}</tbody>
    </table>`;

  if (data.warning) {{
    $('warningBanner').textContent = 'Fallback used: ' + data.warning;
    $('warningBanner').classList.remove('hidden');
  }}
}}

$('reviewForm').addEventListener('submit', async (e) => {{
  e.preventDefault();
  clearBanners();
  const file = $('fileInput').files[0];
  const text = textarea.value.trim();
  if (!file && !text) {{
    showError('Add a .docx/.pdf file or paste the manuscript text first.');
    return;
  }}

  const btn = $('runBtn');
  btn.disabled = true;
  btn.textContent = 'Reviewing…';
  $('statusLine').textContent = 'Running the deterministic review…';

  const formData = new FormData();
  formData.append('student_name', $('studentName').value || 'Student');
  formData.append('reviewer_name', $('reviewerName').value || 'Raunak Banga');
  formData.append('reviewer_initials', $('reviewerInitials').value || 'RB');
  formData.append('academic_style', $('academicStyle').value);
  formData.append('text', text);
  formData.append('custom_comments_text', $('customComments').value);
  formData.append('custom_endnote_text', $('customEndnote').value);
  if (file) formData.append('file', file);

  try {{
    const resp = await fetch('/api/thinkingstorm/execute', {{ method: 'POST', body: formData }});
    if (!resp.ok) {{
      let reason = resp.statusText || ('HTTP ' + resp.status);
      try {{
        const payload = await resp.json();
        if (payload && payload.detail) {{
          reason = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
        }}
      }} catch (ignored) {{}}
      showError(reason);
      $('statusLine').textContent = 'Review failed — see the message above.';
      return;
    }}
    const data = await resp.json();
    render(data);
    $('statusLine').textContent = 'Done · ' + data.comments.length + ' comments · ' + data.word_count + ' words';
  }} catch (err) {{
    showError('Network error: ' + err.message);
    $('statusLine').textContent = 'Review failed.';
  }} finally {{
    btn.disabled = false;
    btn.textContent = 'Run complete review';
  }}
}});
</script>
</body>
</html>"""
