/* ThinkingStorm workspace: explicit inputs, accessible states, safe previews. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const form = $('reviewForm');
  const textarea = $('manuscriptText');
  const fileInput = $('fileInput');
  let mode = 'upload';
  let busy = false;
  let lastData = null;
  let copyTimer;
  let dragDepth = 0;
  let originalFeedback = null;
  let originalRequest = null;
  let originalSequence = 0;
  let reviewProgressPoll = null;
  let cleverWidget = null;
  let feedbackEditor = null;
  let cleverReviewCurrent = false;
  function invalidateCleverFeedback() {
    cleverReviewCurrent = false;
    cleverWidget?.clear();
  }
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
  const words = value => value.trim() ? value.trim().split(/\s+/).length : 0;
  const setShown = (id, shown) => { $(id).hidden = !shown; };

  function setProgress(stage) {
    ['stepManuscript', 'stepReview', 'stepDownload'].forEach((id, i) => {
      $(id).classList.toggle('current', i === stage);
      $(id).classList.toggle('done', i < stage);
      if (i === stage) $(id).setAttribute('aria-current', 'step');
      else $(id).removeAttribute('aria-current');
    });
  }

  function resetReviewProgress() {
    reviewProgressPoll?.stop();
    reviewProgressPoll = null;
    $('reviewProgress').removeAttribute('value');
    $('progressPercent').textContent = 'Starting…';
    $('progressTitle').textContent = 'Uploading your manuscript';
    $('progressDetails').textContent = 'Waiting for the review to start.';
    $('progressEstimate').textContent = '';
  }

  function showReviewProgress(data) {
    $('progressTitle').textContent = data.message || 'Review in progress';
    if (Number.isFinite(data.percent)) {
      $('reviewProgress').value = data.percent;
      $('progressPercent').textContent = `${data.percent}%`;
    }
    const editing = ['feedback_ready', 'humanizing', 'retry'].includes(data.stage);
    $('progressDetails').textContent = editing && Number.isInteger(data.total_passages) && data.total_passages > 0
      ? `${data.completed_passages} of ${data.total_passages} feedback passages checked · ${data.remaining_passages ? `${data.remaining_passages} left` : 'file checks follow'}${data.stage === 'retry' ? ' · retry in progress' : ''}`
      : data.stage === 'failed' ? 'See the review error for details.' : data.stage === 'complete' ? 'All review files are ready.' : data.stage === 'document' || data.stage === 'document_ready'
        ? 'Feedback is ready. Preparing and checking your download files.' : 'Reading the draft and preparing your feedback.';
    const elapsed = Number.isFinite(data.elapsed_seconds) ? `${data.elapsed_seconds}s elapsed` : '';
    const eta = editing && Number.isFinite(data.editing_eta_seconds)
      ? `About ${data.editing_eta_seconds}s of feedback editing left; file checks follow.` : '';
    $('progressEstimate').textContent = [elapsed, eta].filter(Boolean).join(' · ');
  }

  function trackReviewProgress(data) {
    resetReviewProgress();
    if (!globalThis.crypto?.getRandomValues || !globalThis.ReviewProgress) {
      $('progressEstimate').textContent = 'Live progress is unavailable. Your review will continue.';
      return;
    }
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    const id = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
    data.append('progress_id', id);
    reviewProgressPoll = ReviewProgress.start({id, onUpdate: showReviewProgress,
      onUnavailable: () => { $('progressEstimate').textContent = 'Live updates interrupted. Your review is still running.'; }});
  }

  function clearErrors() {
    setShown('inputError', false);
    setShown('errorBanner', false);
    setShown('warningBanner', false);
    textarea.removeAttribute('aria-invalid');
    fileInput.removeAttribute('aria-invalid');
    $('chooseFileBtn').removeAttribute('aria-invalid');
  }

  function inputError(message, target) {
    $('inputError').textContent = message;
    setShown('inputError', true);
    target.setAttribute('aria-invalid', 'true');
    target.focus();
  }

  function activateMode(nextMode, focus = false) {
    if (mode !== nextMode) invalidateCleverFeedback();
    mode = nextMode;
    clearErrors();
    ['upload', 'paste'].forEach(value => {
      const tab = $(value + 'Mode');
      tab.setAttribute('aria-selected', String(value === mode));
      tab.tabIndex = value === mode ? 0 : -1;
      setShown(value + 'Panel', value === mode);
    });
    if (focus) $(nextMode + 'Mode').focus();
  }

  document.querySelectorAll('[data-mode]').forEach(tab => {
    tab.addEventListener('click', () => activateMode(tab.dataset.mode));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      activateMode(event.key === 'Home' ? 'upload' : event.key === 'End' ? 'paste' : mode === 'upload' ? 'paste' : 'upload', true);
    });
  });

  function updateFile() {
    invalidateCleverFeedback();
    const file = fileInput.files[0];
    $('dropZone').classList.toggle('has-file', Boolean(file));
    $('fileName').textContent = file ? file.name : 'Your next draft starts here';
    $('fileHint').textContent = file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · ready to review` : 'Drop a manuscript here, or choose a file below.';
    $('chooseFileBtn').innerHTML = (file ? 'Change file' : 'Choose a file') + ' <span aria-hidden="true">↗</span>';
    setShown('fileControls', Boolean(file));
    loadOriginalFeedback(file);
  }

  function originalCopyAvailability() {
    $('copyOriginalCommentsBtn').disabled = busy || !originalFeedback?.comments_text?.trim();
    $('copyOriginalEndnoteBtn').disabled = busy || !originalFeedback?.endnote_text?.trim();
  }

  function showOriginalFeedback(data) {
    originalFeedback = data;
    originalCopyAvailability();
    $('originalFeedbackStatus').textContent = `${data.comment_count || 0} original comments found · ${data.endnote_text?.trim() ? 'Original endnote found' : 'No original endnote found'}`;
  }

  async function loadOriginalFeedback(file) {
    const sequence = ++originalSequence;
    originalRequest?.abort();
    originalFeedback = null;
    originalCopyAvailability();
    const supported = Boolean(file && /\.docx$/i.test(file.name));
    setShown('originalFeedbackPanel', supported);
    if (!supported) return;
    $('originalFeedbackStatus').textContent = 'Reading existing feedback…';
    originalRequest = new AbortController();
    const data = new FormData();
    data.append('file', file);
    try {
      const response = await fetch('/api/thinkingstorm/original-feedback', {method: 'POST', body: data, signal: originalRequest.signal});
      if (!response.ok) throw new Error('Original feedback could not be read. Try selecting the DOCX again.');
      const payload = await response.json();
      if (sequence !== originalSequence) return;
      showOriginalFeedback(payload);
    } catch (error) {
      if (sequence !== originalSequence || error.name === 'AbortError') return;
      $('originalFeedbackStatus').textContent = error.message || 'Original feedback could not be read.';
    }
  }

  function validFile(file) {
    if (!file) return false;
    if (!/\.(docx|pdf|txt|md)$/i.test(file.name)) {
      inputError('Choose a DOCX, PDF, TXT or Markdown file. For an older .doc file, save it as .docx first.', $('chooseFileBtn'));
      return false;
    }
    if (file.size === 0) {
      inputError('This file is empty. Choose a manuscript with readable text.', $('chooseFileBtn'));
      return false;
    }
    if (file.size > 20 * 1024 * 1024) {
      inputError('Choose a file smaller than 20 MB, or paste its text instead.', $('chooseFileBtn'));
      return false;
    }
    return true;
  }

  $('chooseFileBtn').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    clearErrors();
    if (fileInput.files[0] && !validFile(fileInput.files[0])) fileInput.value = '';
    updateFile();
  });
  $('removeFileBtn').addEventListener('click', () => {
    fileInput.value = '';
    clearErrors();
    updateFile();
    $('chooseFileBtn').focus();
  });
  const dropZone = $('dropZone');
  dropZone.addEventListener('dragenter', event => { event.preventDefault(); if (!busy) { dragDepth++; dropZone.classList.add('is-dragging'); } });
  dropZone.addEventListener('dragover', event => { event.preventDefault(); event.dataTransfer.dropEffect = busy ? 'none' : 'copy'; });
  dropZone.addEventListener('dragleave', event => { event.preventDefault(); if (--dragDepth <= 0) { dragDepth = 0; dropZone.classList.remove('is-dragging'); } });
  dropZone.addEventListener('drop', event => {
    event.preventDefault();
    dragDepth = 0;
    dropZone.classList.remove('is-dragging');
    if (busy) return;
    clearErrors();
    if (event.dataTransfer.files.length !== 1) {
      inputError('Choose one manuscript at a time so the feedback stays together.', $('chooseFileBtn'));
      return;
    }
    if (!validFile(event.dataTransfer.files[0])) return;
    fileInput.files = event.dataTransfer.files;
    updateFile();
  });
  textarea.addEventListener('input', () => { invalidateCleverFeedback(); $('wordCount').textContent = words(textarea.value); textarea.removeAttribute('aria-invalid'); setShown('inputError', false); });
  const updateReviewer = () => { $('reviewerSummary').textContent = `${$('reviewerName').value.trim() || 'Raunak Banga'} · ${$('reviewerInitials').value.trim() || 'RB'}`; };
  $('reviewerName').addEventListener('input', updateReviewer);
  $('reviewerInitials').addEventListener('input', updateReviewer);

  function selectFeedbackTab(name, focus = false) {
    document.querySelectorAll('[data-tab]').forEach(tab => {
      const selected = tab.dataset.tab === name;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      setShown('tab-' + tab.dataset.tab, selected);
      if (selected && focus) tab.focus();
    });
  }
  document.querySelectorAll('[data-tab]').forEach(tab => {
    tab.addEventListener('click', () => selectFeedbackTab(tab.dataset.tab));
    tab.addEventListener('keydown', event => {
      const names = ['comments', 'endnote', 'rubric'];
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const index = names.indexOf(tab.dataset.tab);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (index + (event.key === 'ArrowRight' ? 1 : 2)) % 3;
      selectFeedbackTab(names[next], true);
    });
  });

  function downloadPath(value) {
    try {
      const url = new URL(value, window.location.origin);
      return url.origin === window.location.origin && url.pathname.startsWith('/download/') ? url.pathname + url.search : '';
    } catch { return ''; }
  }

  function knowledgeURL(value) {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && url.hostname === 'knowledge.thinkingstorm.com' ? url.href : '';
    } catch { return ''; }
  }

  function endnoteText(data) {
    return data.endnote_text?.trim() || Object.entries(data.endnote_domains || {}).map(([heading, body]) => heading + ':\n' + body).join('\n\n');
  }

  function render(data) {
    cleverWidget?.clear();
    cleverReviewCurrent = true;
    if (!Array.isArray(data.comments) || !data.job_id) throw new Error('The server returned an incomplete review. Please try again.');
    lastData = data;
    if (mode === 'upload' && data.original_feedback) showOriginalFeedback(data.original_feedback);
    $('studentLabel').textContent = data.student_name || 'Student';
    $('jobId').textContent = data.job_id;
    const quality = data.review_quality || {};
    $('resultStatus').textContent = quality.needs_review ? 'REVIEW NEEDS ATTENTION' : '✓ REVIEW GENERATED';
    setShown('reviewCoverage', Boolean(quality.page_count));
    if (quality.page_count) {
      const layout = quality.layout_method === 'word_rendered' ? 'Microsoft Word page layout' : quality.layout_method === 'cached_rendered_markers' ? 'Word’s saved page markers' : quality.page_count_is_estimate ? 'estimated from word count' : 'explicit page breaks';
      const distribution = (quality.comments_by_page || []).map(item => `Page ${item.page}: ${item.comments}`).join(' · ');
      $('reviewCoverage').textContent = `${distribution}. Target: 3–4 supported comments per page (${layout}). Developmental comments average ${quality.developmental_words_mean} words. ${(quality.messages || []).join(' ')}`;
      $('reviewCoverage').classList.toggle('warning-banner', Boolean(quality.needs_review));
    }
    $('summary').textContent = data.executive_summary || '';
    const statistics = [['Comments', data.comments.length], ['Words reviewed', data.word_count ?? '—'], ['Revision areas', Object.keys(data.endnote_domains || {}).length]];
    $('statsGrid').innerHTML = statistics.map(([label, value]) => `<div class="review-stat"><strong>${esc(value)}</strong><small>${esc(label)}</small></div>`).join('');
    const downloads = [
      ['Commented .docx', data.commented_docx_url, 'Original draft, margin comments & endnote', 'DOC', 'primary'],
      ['Tracked changes .docx', data.annotated_docx_url, 'Suggested mechanical edits as Word revisions', 'DOC', ''],
      ['Report .html', data.report_url, 'Rubric, summary & revision priorities', 'WEB', '']
    ];
    $('downloads').innerHTML = downloads.filter(([, path]) => downloadPath(path)).map(([title, path, hint, type, cls]) => `<a ${cls === 'primary' ? 'id="commentedDownload"' : ''} class="download-link ${cls}" href="${esc(downloadPath(path))}"><span class="download-file-icon" aria-hidden="true">${type}</span><div><strong>${title}</strong><small>${hint}</small></div><span class="download-arrow" aria-hidden="true">↓</span></a>`).join('');
    const qa = downloadPath(data.qa_report_url);
    $('qaDownload').hidden = !qa;
    if (qa) $('qaDownload').href = qa;
    else $('qaDownload').removeAttribute('href');
    $('commentCount').textContent = data.comments.length;
    $('tab-comments').innerHTML = data.comments.length ? data.comments.map((comment, i) => {
      const link = knowledgeURL(comment.link_url);
      const category = link ? `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(comment.category || 'Feedback')} ↗</a>` : `<span class="comment-category">${esc(comment.category || 'Feedback')}</span>`;
      return `<article class="comment-item"><div class="comment-heading">${category}<span>${String(i + 1).padStart(2, '0')}</span></div><blockquote>${esc(comment.target_text)}</blockquote><label class="comment-editor-label" for="commentEdit${i}">Edit comment ${i + 1}</label><textarea id="commentEdit${i}" data-feedback-index="${i}" rows="4" maxlength="10000" aria-describedby="feedbackSaveStatus">${esc(comment.comment_text)}</textarea></article>`;
    }).join('') : '<p class="field-note">No margin comments were returned for this review.</p>';
    $('tab-endnote').innerHTML = '<label class="comment-editor-label" for="endnoteEdit">Edit endnote</label><p class="field-note">Keep the greeting and reviewer signature. Put section headings on their own lines; headings such as Thesis or Evidence &amp; Analysis work with or without colons. Separate paragraphs with a blank line.</p><textarea id="endnoteEdit" rows="20" maxlength="32000" aria-describedby="feedbackSaveStatus"></textarea>';
    $('endnoteEdit').value = endnoteText(data);
    const score = Number(data.overall_score);
    const scoreText = data.overall_score != null && Number.isFinite(score) ? `${score}/100` : 'Not scored';
    $('tab-rubric').innerHTML = `<div class="rubric-score">Overall rubric <strong>${esc(scoreText)}</strong></div><table class="rubric-table"><caption class="sr-only">Review rubric scores and findings</caption><thead><tr><th scope="col">Area</th><th scope="col">Score</th><th scope="col">Feedback</th></tr></thead><tbody>${Object.entries(data.rubric || {}).map(([key, value]) => `<tr><td>${esc(value.label || key)}</td><td>${esc(value.score ?? '—')}/25</td><td>${esc(value.verdict)}</td></tr>`).join('')}</tbody></table>`;
    if (data.warning) { $('warningBanner').textContent = data.warning; setShown('warningBanner', true); }
    selectFeedbackTab('comments');
    feedbackEditor?.reset();
  }

  function setBusy(value) {
    busy = value;
    cleverWidget?.setBusy(value);
    form.querySelectorAll('button, input, select, textarea').forEach(control => { control.disabled = value; });
    $('feedbackPanel').setAttribute('aria-busy', String(value));
    $('runBtnLabel').textContent = value ? 'Reviewing your draft…' : 'Run complete review';
    setShown('loadingState', value);
    originalCopyAvailability();
  }

  function showReady() {
    setShown('results', Boolean(lastData));
    setShown('emptyState', !lastData);
    $('workspaceStatus').innerHTML = `<span></span> ${lastData?.review_quality?.needs_review ? 'Review needs attention' : lastData ? 'Review generated' : 'Ready for a manuscript'}`;
    setProgress(lastData ? 2 : 0);
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy) return;
    if (feedbackEditor?.isSaving()) return;
    if (feedbackEditor?.isDirty()) return inputError('Save or discard your feedback edits before running another review.', $('saveFeedbackBtn'));
    clearErrors();
    const file = mode === 'upload' ? fileInput.files[0] : null;
    const text = mode === 'paste' ? textarea.value.trim() : '';
    const custom = $('customComments').value.trim() || $('customEndnote').value.trim();
    if (mode === 'upload' && !file) return inputError('Choose a manuscript file, or switch to Paste text.', $('chooseFileBtn'));
    if (file && !validFile(file)) return;
    if (mode === 'paste' && !text) return inputError('Paste the manuscript you would like to review.', textarea);
    if (text && words(text) < 80 && !custom) return inputError(`This draft has ${words(text)} words. Add at least 80 words for an automatic review.`, textarea);
    const data = new FormData();
    data.append('student_name', $('studentName').value.trim() || 'Student');
    data.append('reviewer_name', $('reviewerName').value.trim() || 'Raunak Banga');
    data.append('reviewer_initials', $('reviewerInitials').value.trim() || 'RB');
    data.append('academic_style', $('academicStyle').value);
    data.append('text', text);
    data.append('custom_comments_text', $('customComments').value);
    data.append('custom_endnote_text', $('customEndnote').value);
    if (file) data.append('file', file);
    setShown('emptyState', false);
    setShown('results', false);
    setBusy(true);
    trackReviewProgress(data);
    setProgress(1);
    $('loadingState').scrollIntoView({block: 'nearest'});
    $('workspaceStatus').innerHTML = '<span></span> Review in progress';
    $('statusLine').textContent = 'Reading your draft, checking the feedback, and preparing review files…';
    try {
      const response = await fetch('/api/thinkingstorm/execute', {method: 'POST', body: data});
      if (!response.ok) {
        let reason = `The review could not be completed (HTTP ${response.status}).`;
        try { const payload = await response.json(); if (typeof payload.detail === 'string') reason = payload.detail; } catch { /* Preserve the readable HTTP error. */ }
        throw new Error(reason);
      }
      render(await response.json());
      showReviewProgress({stage: 'complete', status: 'complete', percent: 100, message: 'Your review files are ready'});
      $('statusLine').textContent = `${lastData.review_quality?.needs_review ? 'Review needs attention' : 'Review generated'} · ${lastData.comments.length} comments · ${lastData.word_count} words`;
      if (lastData.review_quality?.generation?.model) $('statusLine').textContent += ` · Local ${lastData.review_quality.generation.model}`;
      const humanization = lastData.review_quality?.generation?.humanization;
      if (humanization?.enabled) $('statusLine').textContent += ` · ${humanization.rewritten} passages rewritten${humanization.retained ? ` · ${humanization.retained} retained for review` : ''}`;
      setBusy(false);
      showReady();
      $('results').tabIndex = -1;
      $('results').setAttribute('aria-label', `${lastData.review_quality?.needs_review ? 'Review needs attention' : 'Review generated'} for ${lastData.student_name || 'Student'}`);
      $('results').focus({preventScroll: true});
      $('feedbackPanel').scrollIntoView({block: 'start'});
    } catch (error) {
      setBusy(false);
      showReady();
      const message = error instanceof TypeError ? 'We could not reach the review service. Check your connection and try again.' : error.message || 'Connection interrupted. Please check your connection and try again.';
      $('errorBanner').textContent = `${message}${lastData ? ' Your previous review is still shown below.' : ''}`;
      setShown('errorBanner', true);
      $('errorBanner').focus();
      $('statusLine').textContent = 'Review not completed. Check the message and try again.';
    } finally {
      reviewProgressPoll?.stop();
      reviewProgressPoll = null;
    }
  });

  $('newReviewBtn').addEventListener('click', () => {
    if (busy) return;
    if (feedbackEditor?.isSaving()) return;
    if (feedbackEditor?.isDirty()) {
      $('feedbackSaveStatus').textContent = 'Save or discard your edits before starting a new review.';
      $('saveFeedbackBtn').focus();
      return;
    }
    lastData = null;
    feedbackEditor?.reset();
    form.reset();
    resetReviewProgress();
    clearErrors();
    updateFile();
    updateReviewer();
    $('wordCount').textContent = '0';
    $('copyState').textContent = '';
    $('statusLine').textContent = 'Your original manuscript stays intact.';
    activateMode('upload');
    showReady();
    $('chooseFileBtn').focus();
  });

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; }
    catch {
      const previous = document.activeElement;
      const area = document.createElement('textarea');
      area.value = text;
      area.className = 'sr-only';
      document.body.appendChild(area);
      area.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch { /* Tell the user if both clipboard methods fail. */ }
      area.remove();
      previous?.focus();
      return copied;
    }
  }
  async function copy(kind) {
    if (!lastData) return;
    const draft = feedbackEditor?.readDraft() || lastData;
    const text = kind === 'endnote' ? endnoteText(draft) : draft.comments.map((comment, i) => `[${i + 1}] ${String(comment.comment_text || '').trim()}`).join('\n\n');
    const copied = await copyText(text);
    clearTimeout(copyTimer);
    $('copyState').textContent = copied ? `${kind === 'endnote' ? 'Endnote' : 'Comments'} copied` : 'Copy unavailable. Select the text to copy it manually.';
    copyTimer = setTimeout(() => { $('copyState').textContent = ''; }, 4000);
  }
  $('copyCommentsBtn').addEventListener('click', () => copy('comments'));
  $('copyEndnoteBtn').addEventListener('click', () => copy('endnote'));
  async function copyOriginal(kind) {
    const text = originalFeedback?.[kind + '_text']?.trim();
    if (!text || busy) return;
    const copied = await copyText(text);
    $('originalFeedbackStatus').textContent = copied ? `Original ${kind === 'comments' ? 'comments' : 'endnote'} copied` : 'Copy unavailable. Try again or copy from Word.';
  }
  $('copyOriginalCommentsBtn').addEventListener('click', () => copyOriginal('comments'));
  $('copyOriginalEndnoteBtn').addEventListener('click', () => copyOriginal('endnote'));
  if ($('cleverOrigin')) $('cleverOrigin').textContent = window.location.origin;
  let cleverStorage;
  try { cleverStorage = window.localStorage; } catch { /* Private browsers can block storage. */ }
  cleverWidget = window.CleverWidget.mount({document, storage: cleverStorage, copyText,
    readFeedback: source => busy ? '' : window.CleverWidget.feedbackText(source,
      cleverReviewCurrent ? feedbackEditor?.readDraft() || lastData : null, mode === 'upload' ? originalFeedback : null, endnoteText)});
  feedbackEditor = window.FeedbackEditor.mount({document, getData: () => lastData,
    onDirty: (dirty, saving) => {
      $('runBtn').disabled = busy || saving;
      $('newReviewBtn').disabled = saving;
      if (dirty) cleverWidget?.clear();
    },
    onSaved: saved => {
      const bodies = new Map(saved.comments.map(comment => [comment.id, comment.body]));
      lastData.comments = lastData.comments.map(comment => ({...comment, comment_text: bodies.get(comment.feedback_id)}));
      lastData.endnote_text = saved.endnote_text;
      lastData.feedback_revision = saved.feedback_revision;
      lastData.commented_docx_url = saved.commented_docx_url;
      lastData.qa_report_url = saved.qa_report_url;
      const qa = downloadPath(saved.qa_report_url);
      $('qaDownload').hidden = !qa;
      if (qa) $('qaDownload').href = qa;
      if (lastData.review_quality?.page_count) $('reviewCoverage').textContent += ' Saved edits passed document checks; the coverage summary describes the original automated review.';
      cleverWidget?.clear();
    }});
  window.addEventListener('beforeunload', event => {
    if (feedbackEditor.isDirty() || feedbackEditor.isSaving()) { event.preventDefault(); event.returnValue = ''; }
  });
  window.CleverWidget.mountDetector({document});
})();
