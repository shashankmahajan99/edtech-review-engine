/* Explicit feedback saves: the Word download always follows the saved revision. */
((root) => {
  'use strict';
  const MARKER_RE = /^\s*(?:\[(\d+)\]|Comment\s+(\d+)\s*[:.)]|(\d+)[.)])\s+(.*)$/i;
  function splitCommentBlock(rawText, expectedCount = 0) {
    const normalized = String(rawText ?? '').replace(/\r\n?/g, '\n').trim();
    if (!normalized) return [];
    const lines = normalized.split('\n');
    const markerHits = [];
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(MARKER_RE);
      if (m) {
        const num = Number(m[1] || m[2] || m[3]);
        markerHits.push({lineIndex: i, num, rest: m[4]});
      }
    }
    if (markerHits.length >= 2 && markerHits.every((h, idx) => h.num === idx + 1)) {
      return markerHits.map((hit, idx) => {
        const endLine = idx + 1 < markerHits.length ? markerHits[idx + 1].lineIndex : lines.length;
        const tail = lines.slice(hit.lineIndex + 1, endLine);
        return [hit.rest, ...tail].join(' ').replace(/\s+/g, ' ').trim();
      }).filter(Boolean);
    }
    const stripSequentialMarkers = blocks => {
      const parsed = blocks.map(b => b.replace(/\s+/g, ' ').trim()).filter(Boolean);
      const matches = parsed.map(b => b.match(MARKER_RE));
      if (matches.length >= 2 && matches.every((m, idx) => m && Number(m[1] || m[2] || m[3]) === idx + 1)) {
        return matches.map(m => m[4].replace(/\s+/g, ' ').trim());
      }
      if (matches.length === 1 && matches[0] && /^\s*(?:\[1\]|Comment\s+1\s*[:.)])\s+/i.test(parsed[0])) {
        return [matches[0][4].replace(/\s+/g, ' ').trim()];
      }
      return parsed;
    };
    const paraBlocks = stripSequentialMarkers(normalized.split(/\n\s*\n+/));
    if (paraBlocks.length > 1 || expectedCount <= 1) return paraBlocks;
    return stripSequentialMarkers(lines);
  }
  function mount({document: doc, getData, onSaved, onDirty = () => {}, fetch: request = root.fetch.bind(root)}) {
    const $ = id => doc.getElementById(id);
    const fields = () => [...doc.querySelectorAll('[data-feedback-index]')];
    let saving = false;
    let issues = [];
    function issueField(issue) {
      if (issue.field === 'endnote') return $('endnoteEdit');
      if (issue.field === 'comment') {
        const index = getData()?.comments.findIndex(c => c.feedback_id === issue.comment_id) ?? -1;
        return fields()[index];
      }
      return null;
    }
    function showIssues(next) {
      issues = next;
      const host = $('feedbackSaveErrors');
      for (const field of [...fields(), $('endnoteEdit')].filter(Boolean)) {
        field.removeAttribute('aria-invalid'); field.removeAttribute('aria-errormessage');
      }
      if (!host) return;
      host.replaceChildren();
      host.hidden = !issues.length;
      if (!issues.length) return;
      const title = doc.createElement('p');
      title.textContent = 'Feedback was not saved. Review these issues, then try Save again:';
      const list = doc.createElement('ul');
      for (const issue of issues) {
        const item = doc.createElement('li');
        const field = issueField(issue);
        if (field) {
          field.setAttribute('aria-invalid', 'true');
          field.setAttribute('aria-errormessage', 'feedbackSaveErrors');
          const jump = doc.createElement('button');
          jump.type = 'button'; jump.className = 'feedback-issue-link'; jump.textContent = issue.message;
          jump.addEventListener('click', () => {
            $(issue.field === 'endnote' ? 'endnoteTab' : 'commentsTab')?.click();
            field.focus(); field.scrollIntoView?.({block: 'center'});
          });
          item.appendChild(jump);
        } else item.textContent = issue.message;
        list.appendChild(item);
      }
      host.replaceChildren(title, list);
    }
    function readDraft() {
      const data = getData();
      if (!data) return {comments: [], endnote_text: ''};
      const inputs = fields();
      return {comments: data.comments.map((comment, i) => ({...comment,
        comment_text: inputs[i]?.value ?? comment.comment_text})),
        endnote_text: $('endnoteEdit')?.value ?? data.endnote_text ?? ''};
    }
    function isDirty() {
      const data = getData();
      if (!data?.editing_available) return false;
      const draft = readDraft();
      return draft.endnote_text !== data.endnote_text || draft.comments.some((c, i) => c.comment_text !== data.comments[i].comment_text);
    }
    function refresh(message) {
      const data = getData();
      const dirty = isDirty();
      $('saveFeedbackBtn').disabled = saving || !dirty || !data?.editing_available;
      $('discardFeedbackBtn').disabled = saving || !dirty;
      for (const input of [...fields(), $('endnoteEdit'), $('bulkCommentsInput'), $('applyBulkCommentsBtn')].filter(Boolean)) {
        input.disabled = saving || !data?.editing_available;
      }
      const link = $('commentedDownload');
      if (link) {
        const url = data?.commented_docx_url || '';
        if (dirty || saving || !/^\/download\/commented\/ts-[a-f0-9]{6,32}(?:\?revision=[a-f0-9]{64})?$/.test(url)) {
          link.removeAttribute('href'); link.setAttribute('aria-disabled', 'true'); link.tabIndex = -1;
        } else { link.href = url; link.removeAttribute('aria-disabled'); link.removeAttribute('tabindex'); }
      }
      $('feedbackSaveStatus').textContent = message || (data?.editing_available
        ? dirty ? 'Unsaved changes — save before downloading the commented DOCX.' : 'Feedback matches the commented DOCX.'
        : data?.editing_unavailable_reason || 'Run a new review to edit feedback.');
      onDirty(dirty, saving);
    }
    function reset(message) {
      showIssues([]);
      const data = getData();
      fields().forEach((input, i) => { input.value = data?.comments[i]?.comment_text || ''; });
      if ($('endnoteEdit')) $('endnoteEdit').value = data?.endnote_text || '';
      if ($('bulkCommentsInput')) $('bulkCommentsInput').value = '';
      refresh(message);
    }
    $('results').addEventListener('input', event => {
      if (event.target.matches('[data-feedback-index], #endnoteEdit')) {
        showIssues(issues.filter(issue => issueField(issue) !== event.target));
        refresh();
      }
    });
    $('discardFeedbackBtn').addEventListener('click', () => { if (!saving) reset('Unsaved edits discarded. The commented DOCX is unchanged.'); });
    $('saveFeedbackBtn').addEventListener('click', async () => {
      const data = getData();
      if (saving || !data?.editing_available || !isDirty()) return;
      const draft = readDraft();
      showIssues([]);
      saving = true;
      refresh('Saving feedback and checking the Word file…');
      try {
        const response = await request(`/api/thinkingstorm/feedback/${encodeURIComponent(data.job_id)}`, {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({edit_token: data.edit_token, revision: data.feedback_revision,
            comments: draft.comments.map(c => ({id: c.feedback_id, body: c.comment_text})),
            endnote_text: draft.endnote_text})});
        const result = await response.json();
        if (!response.ok) {
          const error = new Error(typeof result.detail === 'string' ? result.detail : 'Feedback could not be saved.');
          error.issues = Array.isArray(result.issues) ? result.issues.filter(issue => issue && typeof issue.message === 'string') : [];
          throw error;
        }
        onSaved(result);
        saving = false;
        reset('Saved to DOCX. Download the commented file above.');
      } catch (error) {
        saving = false;
        showIssues(error.issues || []);
        const explanation = issues.length && $('feedbackSaveErrors') ? 'Review the save issues below and try again.' : error.message || 'Could not reach the save service.';
        refresh(`${explanation} Your edits are still here; the download stays blocked until you save or discard them.`);
        if (issues.length && $('feedbackSaveErrors')) {
          $('feedbackSaveErrors').focus();
          $('feedbackSaveErrors').scrollIntoView?.({block: 'center'});
        }
      }
    });
    $('applyBulkCommentsBtn')?.addEventListener('click', async () => {
      const data = getData();
      if (saving || !data?.editing_available) return;
      const inputs = fields();
      const blocks = splitCommentBlock($('bulkCommentsInput')?.value || '', inputs.length);
      if (blocks.length !== inputs.length) {
        showIssues([{
          field: 'document',
          message: `Expected ${inputs.length} comments, but found ${blocks.length} paragraphs in the pasted block. Separate each comment with a blank line before applying.`
        }]);
        $('feedbackSaveStatus').textContent = 'Comment count mismatch — fix before saving.';
        if ($('feedbackSaveErrors')) {
          $('feedbackSaveErrors').focus();
          $('feedbackSaveErrors').scrollIntoView?.({block: 'center'});
        }
        return;
      }
      inputs.forEach((input, i) => { input.value = blocks[i]; });
      showIssues([]);
      refresh();
      await $('saveFeedbackBtn')?.click();
    });
    return {reset, readDraft, isDirty, isSaving: () => saving};
  }
  const api = {mount, splitCommentBlock};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FeedbackEditor = api;
})(typeof window === 'undefined' ? globalThis : window);
