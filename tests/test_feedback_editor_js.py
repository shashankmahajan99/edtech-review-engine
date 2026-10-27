"""Client draft/save state, with no browser or Word service dependency."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_feedback_editor_draft_save_failure_discard_and_download_lifecycle():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    script = r'''
const assert = require('node:assert/strict');
const {mount} = require('./portal/static/feedback-editor.js');
class Element {
  constructor() { this.value=''; this.attrs={}; this.handlers={}; this.children=[]; }
  addEventListener(name, cb) { this.handlers[name]=cb; }
  removeAttribute(name) { delete this.attrs[name]; }
  setAttribute(name, value) { this.attrs[name]=value; }
  matches() { return true; }
  async click() { this.clicked=true; if (this.handlers.click) await this.handlers.click(); }
  appendChild(child) { this.children.push(child); }
  replaceChildren(...children) { this.children=children; }
  focus() { this.focused=true; }
  scrollIntoView() {}
}
const data = {job_id:'ts-123abc', editing_available:true, edit_token:'capability', feedback_revision:'old',
  commented_docx_url:'/download/commented/ts-123abc', comments:[
    {feedback_id:'0', comment_text:'First saved body.',target_text:'Keep the quoted passage.'},
    {feedback_id:'1', comment_text:'Second saved body.',target_text:'Another anchor.'}], endnote_text:'Saved letter.'};
const nodes = Object.fromEntries(['results','saveFeedbackBtn','discardFeedbackBtn','feedbackSaveStatus',
  'commentedDownload','endnoteEdit','feedbackSaveErrors','endnoteTab','commentsTab'].map(id => [id,new Element()]));
const inputs = [new Element(),new Element()];
let fail = false, captured, dirtyState, resolveSave;
const editor = mount({document:{getElementById:id=>nodes[id],querySelectorAll:()=>inputs,createElement:()=>new Element()},getData:()=>data,
  onDirty:(dirty,saving)=>{dirtyState={dirty,saving};},
  fetch:async (url, request)=>{
    captured={url,payload:JSON.parse(request.body)};
    if (resolveSave === 'block') await new Promise(resolve=>{resolveSave=resolve;});
    return {ok:!fail, json:async()=>fail ? {detail:'Validation rejected this draft.',issues:[
      {field:'comment',comment_id:'0',message:'Comment 1 needs more explanation.'},
      {field:'endnote',message:'Endnote needs section headings.'}]} : {
      comments:captured.payload.comments, endnote_text:captured.payload.endnote_text,
      feedback_revision:'a'.repeat(64), commented_docx_url:'/download/commented/ts-123abc?revision='+'a'.repeat(64)}};
  }, onSaved:saved=>{
    data.comments=data.comments.map((c,i)=>({...c,comment_text:saved.comments[i].body}));
    data.endnote_text=saved.endnote_text;
    data.feedback_revision=saved.feedback_revision;
    data.commented_docx_url=saved.commented_docx_url;
  }});
(async()=>{
  editor.reset();
  assert.equal(editor.isDirty(),false);
  assert.equal(nodes.commentedDownload.href,'/download/commented/ts-123abc');
  assert.equal(nodes.saveFeedbackBtn.disabled,true);
  inputs[0].value='A humanized body.';
  nodes.results.handlers.input({target:inputs[0]});
  assert.equal(editor.isDirty(),true);
  assert.equal(nodes.commentedDownload.attrs['aria-disabled'],'true');
  assert.equal(editor.readDraft().comments[0].target_text,'Keep the quoted passage.');
  assert.equal(editor.readDraft().comments[0].comment_text,'A humanized body.');
  await nodes.saveFeedbackBtn.click();
  assert.equal(captured.url,'/api/thinkingstorm/feedback/ts-123abc');
  assert.deepEqual(captured.payload.comments[0],{id:'0',body:'A humanized body.'});
  assert.equal(editor.isDirty(),false);
  assert.match(nodes.commentedDownload.href,/revision=/);
  assert.match(nodes.feedbackSaveStatus.textContent,/Saved to/);
  fail=true;
  nodes.endnoteEdit.value='Edited letter.';
  nodes.results.handlers.input({target:nodes.endnoteEdit});
  await nodes.saveFeedbackBtn.click();
  assert.equal(editor.isDirty(),true);
  assert.equal(nodes.endnoteEdit.value,'Edited letter.');
  assert.match(nodes.feedbackSaveStatus.textContent,/save issues/);
  assert.equal(nodes.feedbackSaveErrors.hidden,false);
  assert.equal(inputs[0].attrs['aria-invalid'],'true');
  assert.equal(nodes.endnoteEdit.attrs['aria-invalid'],'true');
  const issueList=nodes.feedbackSaveErrors.children[1];
  await issueList.children[1].children[0].click();
  assert.equal(nodes.endnoteTab.clicked,true);
  assert.equal(nodes.endnoteEdit.focused,true);
  nodes.endnoteEdit.value='Corrected letter.';
  nodes.results.handlers.input({target:nodes.endnoteEdit});
  assert.equal(nodes.endnoteEdit.attrs['aria-invalid'],undefined);
  assert.equal(inputs[0].attrs['aria-invalid'],'true'); // Other field's error stays visible.
  assert.equal(nodes.feedbackSaveErrors.children[1].children.length,1);
  await nodes.discardFeedbackBtn.click();
  assert.equal(nodes.feedbackSaveErrors.hidden,true);
  assert.equal(inputs[0].attrs['aria-invalid'],undefined);
  assert.equal(editor.isDirty(),false);
  assert.equal(nodes.endnoteEdit.value,'Saved letter.');
  fail=false; resolveSave='block';
  inputs[1].value='Another revised body.';
  const pending=nodes.saveFeedbackBtn.click();
  assert.equal(editor.isSaving(),true);
  assert.equal(inputs[0].disabled,true);
  assert.equal(nodes.discardFeedbackBtn.disabled,true);
  assert.deepEqual(dirtyState,{dirty:true,saving:true});
  resolveSave(); await pending;
  assert.equal(editor.isSaving(),false);
  assert.equal(inputs[0].disabled,false);
  assert.equal(editor.isDirty(),false);
  data.editing_available=false;
  data.editing_unavailable_reason='Anchor could not be matched.';
  editor.reset();
  assert.equal(inputs[0].disabled,true);
  assert.match(nodes.feedbackSaveStatus.textContent,/Anchor/);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([node, '-e', script], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_split_comment_block_and_bulk_paste_count_guard():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    script = r'''
const assert = require('node:assert/strict');
const {mount, splitCommentBlock} = require('./portal/static/feedback-editor.js');

assert.deepEqual(splitCommentBlock('', 2), []);
assert.deepEqual(
  splitCommentBlock('[1] First humanized comment.\n\n[2] Second humanized comment with 20 Feb. 2026 inside.', 2),
  ['First humanized comment.', 'Second humanized comment with 20 Feb. 2026 inside.']
);
assert.deepEqual(
  splitCommentBlock('1. First comment without blank line.\n2. Second comment on next line.', 2),
  ['First comment without blank line.', 'Second comment on next line.']
);
// Stage 1 numbered input with K != N must not fall back to blank-line splitting on multi-paragraph comment
assert.deepEqual(
  splitCommentBlock('[1] First comment paragraph one.\n\nFirst comment paragraph two.\n\n[2] Second comment.', 3),
  ['First comment paragraph one. First comment paragraph two.', 'Second comment.']
);
assert.deepEqual(
  splitCommentBlock('20 Feb. 2026 needs day-month-year format.\n\nExplain how this quote supports the thesis.', 2),
  ['20 Feb. 2026 needs day-month-year format.', 'Explain how this quote supports the thesis.']
);
assert.deepEqual(
  splitCommentBlock('First single-line comment.\nSecond single-line comment.', 2),
  ['First single-line comment.', 'Second single-line comment.']
);

class Element {
  constructor() { this.value=''; this.attrs={}; this.handlers={}; this.children=[]; }
  addEventListener(name, cb) { this.handlers[name]=cb; }
  removeAttribute(name) { delete this.attrs[name]; }
  setAttribute(name, value) { this.attrs[name]=value; }
  matches() { return true; }
  async click() { this.clicked=true; if (this.handlers.click) await this.handlers.click(); }
  appendChild(child) { this.children.push(child); }
  replaceChildren(...children) { this.children=children; }
  focus() { this.focused=true; }
  scrollIntoView() {}
}
const data = {job_id:'ts-123abc', editing_available:true, edit_token:'capability', feedback_revision:'old',
  commented_docx_url:'/download/commented/ts-123abc', comments:[
    {feedback_id:'0', comment_text:'Original comment 1.', target_text:'Anchor 1'},
    {feedback_id:'1', comment_text:'Original comment 2.', target_text:'Anchor 2'}], endnote_text:'Saved letter.'};
const nodes = Object.fromEntries(['results','saveFeedbackBtn','discardFeedbackBtn','feedbackSaveStatus',
  'commentedDownload','endnoteEdit','feedbackSaveErrors','endnoteTab','commentsTab',
  'bulkCommentsPanel','bulkCommentsInput','applyBulkCommentsBtn'].map(id => [id,new Element()]));
const inputs = [new Element(),new Element()];
let saveCalls = 0;
const editor = mount({
  document:{getElementById:id=>nodes[id],querySelectorAll:()=>inputs,createElement:()=>new Element()},
  getData:()=>data,
  fetch:async (url, request)=>{
    saveCalls++;
    const payload = JSON.parse(request.body);
    return {ok:true, json:async()=>({
      comments:payload.comments, endnote_text:payload.endnote_text,
      feedback_revision:'b'.repeat(64), commented_docx_url:'/download/commented/ts-123abc?revision='+'b'.repeat(64)
    })};
  },
  onSaved:saved=>{
    data.comments=data.comments.map((c,i)=>({...c,comment_text:saved.comments[i].body}));
  }
});

(async()=>{
  editor.reset();
  // Count mismatch (M=1, N=2) must reject without altering inputs or calling save
  nodes.bulkCommentsInput.value = 'Only one paragraph pasted.';
  await nodes.applyBulkCommentsBtn.click();
  assert.equal(saveCalls, 0);
  assert.equal(inputs[0].value, 'Original comment 1.');
  assert.equal(inputs[1].value, 'Original comment 2.');
  assert.equal(nodes.feedbackSaveErrors.hidden, false);
  assert.match(nodes.feedbackSaveErrors.children[1].children[0].textContent, /Expected 2 comments, but found 1/);

  // Exact match (M=2, N=2) populates inputs and saves to DOCX
  nodes.bulkCommentsInput.value = '[1] Humanized comment one.\n\n[2] Humanized comment two.';
  await nodes.applyBulkCommentsBtn.click();
  assert.equal(saveCalls, 1);
  assert.equal(inputs[0].value, 'Humanized comment one.');
  assert.equal(inputs[1].value, 'Humanized comment two.');
  assert.equal(nodes.bulkCommentsInput.value, '');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([node, '-e', script], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
