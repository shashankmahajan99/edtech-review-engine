import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from zipfile import ZipFile

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from engine.review.pipeline import review_document
from engine.review.validate import _anchors, _comment_body, W
from lxml import etree
from portal.feedback_editor import register_review, save_feedback, digest, _letter
from engine.review.letter_format import is_endnote_heading, parse_reviewer_letter

ROOT = Path(__file__).resolve().parents[1]
JOB = 'ts-123abc'

HUMANIZED_TAYLOR_LETTER = '''Dear Taylor,
Thanks for submitting your draft.

Thesis
The introduction needs to have a thesis statement here. At the moment it goes up until ‘It is impossible to ignore and not use even if you went...’. Before you rewrite the introduction write a short list of points made in the body. What conclusion does this lead to? The central claim would be this so make sure you put it into your introduction as you move from providing background information to stating your argument.

Evidence & Analysis
The sentence ‘Seeing how much we rely on it and connect to it now,...’ would become clearer if you explained why you think this. What specific words/points did you take from the source to come to your conclusion? Discuss what you took from the source before expanding on your answer. This will help to clearly show the difference between what was said in the source and what your conclusion was.

Specific issues & links
The generalised wording ‘As much as there are people with concern for these things like...’ should be specific. Write down what specific issue this relates to. What point are you going to make in this paragraph? Read through the evidence and analysis. If they have formed a more specific idea, base your rewrite around this idea.

Use the comments in the margin to find the relevant parts.

Best wishes,
Raunak Banga'''


def test_reported_humanized_letter_saves_without_rewriting_words(editable):
    root, _, path, _, payload = editable
    with ZipFile(path) as archive:
        original_manuscript = archive.read('word/document.xml')
    payload['endnote_text'] = HUMANIZED_TAYLOR_LETTER
    saved = save_feedback(root, JOB, payload)
    assert saved['validation']['ok']
    assert saved['validation']['metrics']['endnote_sections'] == 3
    assert saved['endnote_text'].split() == HUMANIZED_TAYLOR_LETTER.split()
    assert 'Thesis:' not in saved['endnote_text']
    with ZipFile(path) as archive:
        assert archive.read('word/document.xml') == original_manuscript
        note = etree.fromstring(archive.read('word/endnotes.xml'))
        assert _letter(note) == parse_reviewer_letter(HUMANIZED_TAYLOR_LETTER)
        headings = [p for p in note.findall(f"{W}endnote[@{W}id='1']/{W}p")
                    if is_endnote_heading(''.join(t.text or '' for t in p.iter(f'{W}t')))]
        assert len(headings) == 3
        assert all(p.find(f'.//{W}b') is not None for p in headings)


def test_save_feedback_auto_scrubs_ai_tells_and_expands_contractions_outside_quotes(editable):
    root, _, _, _, payload = editable
    payload['comments'][0]['body'] = (
        "Don't leave 'don't' unexplained; furthermore, this section delves into the claim and plays a crucial role in your argument."
    )
    saved = save_feedback(root, JOB, payload)
    assert saved['validation']['ok']
    body0 = saved['comments'][0]['body']
    assert "Do not leave 'don't' unexplained" in body0
    assert "delves into" not in body0
    assert "crucial role" not in body0


def test_heading_recognition_is_whole_line_and_handles_mixed_format():
    for heading in ['Thesis', ' Evidence & ANALYSIS ', 'Specific issues & links', 'Custom section:']:
        assert is_endnote_heading(heading)
    for prose in ['The thesis needs a clearer claim.', 'Thesis\nExplain the claim.', 'Evidence & Analysis should connect.']:
        assert not is_endnote_heading(prose)
    assert parse_reviewer_letter('Dear Student,\nThanks.\n\nThesis\nThe claim needs support.\n\nEvidence & Analysis:\nExplain your example.') == [
        'Dear Student,', 'Thanks.', 'Thesis', 'The claim needs support.', 'Evidence & Analysis:', 'Explain your example.']


def test_save_api_identifies_fields_and_explains_humanization_failures(editable, monkeypatch):
    from portal import server
    root, _, path, state, payload = editable
    monkeypatch.setattr(server, 'OUTPUT_DIR', root)
    before = path.read_bytes()
    payload['comments'][0]['body'] = 'word ' * 96 + '.'
    payload['endnote_text'] = 'Dear Student,\n\nA closing note without any recognised section titles.\n\nRaunak Banga'
    with TestClient(server.app) as client:
        response = client.post(f'/api/thinkingstorm/feedback/{JOB}', json=payload)
    assert response.status_code == 422
    data = response.json()
    assert isinstance(data['detail'], str)  # Existing open pages get the explanation too.
    assert 'Comment 1' in data['detail'] and 'humanizer' in data['detail']
    assert 'own line' in data['detail'] and 'Endnote' in data['detail']
    assert 'at least 120 words' not in data['detail']  # Section count must be known first.
    assert any(i['field'] == 'comment' and i['comment_id'] == state['comments'][0]['feedback_id'] for i in data['issues'])
    assert any(i['field'] == 'endnote' for i in data['issues'])
    assert path.read_bytes() == before


@pytest.fixture
def editable(tmp_path):
    raw = tmp_path / f'{JOB}_raw.docx'
    raw.write_bytes((ROOT / 'tests/fixtures/andrea_raw.docx').read_bytes())
    review = review_document(str(raw), str(tmp_path), backend='rules')
    docx = tmp_path / f'{JOB}_paper_commented.docx'
    Path(review.output_path).replace(docx)
    comments = [{'comment_text': c['body'], 'target_text': c['quote']} for c in review.comments]
    state = register_review(tmp_path, JOB, raw, docx, comments, 'Raunak Banga')
    assert state['editing_available'], state
    payload = {'edit_token': state['edit_token'], 'revision': state['feedback_revision'],
               'comments': [{'id': c['feedback_id'], 'body': c['comment_text']} for c in state['comments']],
               'endnote_text': state['endnote_text']}
    return tmp_path, raw, docx, state, payload


def test_saved_edits_preserve_all_manuscript_parts_and_survive_subsequent_save(editable):
    root, raw, docx, state, payload = editable
    original = docx.read_bytes()
    payload['comments'][0]['body'] = 'Please connect this point to the main claim. Explain how this detail supports the position you want your reader to accept.'
    payload['comments'][1]['body'] = 'This section needs a specific example from your evidence. Explain what that example reveals before moving to the next point.'
    payload['endnote_text'] += '\n\nPlease read each margin note before you revise the paper.'
    saved = save_feedback(root, JOB, payload)
    assert saved['validation']['ok']
    assert saved['feedback_revision'] == digest(docx.read_bytes()) != payload['revision']
    import io
    with ZipFile(io.BytesIO(original)) as before, ZipFile(docx) as after:
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name not in {'word/comments.xml', 'word/endnotes.xml'}:
                assert before.read(name) == after.read(name), name
        native = etree.fromstring(after.read('word/comments.xml'))
        assert [_comment_body(n) for n in native] == [c['body'] for c in saved['comments']]
        assert _letter(etree.fromstring(after.read('word/endnotes.xml'))) == payload['endnote_text'].split('\n\n')
        assert _anchors(etree.fromstring(before.read('word/document.xml'))) == _anchors(etree.fromstring(after.read('word/document.xml')))
    qa = json.loads((root / saved['qa_report_url'].split('/')[-1]).read_text())
    assert qa['editorial_source'] == 'reviewer_edited' and qa['detector_score'] is None
    assert 'edit_token' not in qa and state['edit_token'] not in (root/'feedback-editor'/f'{JOB}.json').read_text()
    # A fresh save call loads all state from disk, not an in-memory review session.
    payload['revision'] = saved['feedback_revision']
    payload['comments'][0]['body'] = 'Use this paragraph to develop one clear point. Give the reader enough evidence to see why the point supports your claim.'
    assert save_feedback(root, JOB, payload)['validation']['ok']


@pytest.mark.parametrize('mutation,status', [
    ('token', 403), ('token_surrogate',403), ('revision',409), ('duplicate',422), ('unknown',422),
    ('empty',422), ('short',422), ('letter',422), ('control',422), ('surrogate',422), ('oversize',422)])
def test_rejected_save_keeps_last_valid_download(editable, mutation, status):
    root, _, path, _, payload = editable
    before = path.read_bytes()
    if mutation == 'token': payload['edit_token'] = 'wrong'
    if mutation == 'token_surrogate': payload['edit_token'] = '\ud800'
    if mutation == 'revision': payload['revision'] = 'stale'
    if mutation == 'duplicate': payload['comments'][1]['id'] = payload['comments'][0]['id']
    if mutation == 'unknown': payload['comments'][0]['id'] = '99999'
    if mutation == 'empty': payload['comments'][0]['body'] = ''
    if mutation == 'short': payload['comments'][0]['body'] = 'Too short.'
    if mutation == 'letter': payload['endnote_text'] = 'A letter without the required structure.'
    if mutation == 'control': payload['comments'][0]['body'] += '\x00'
    if mutation == 'surrogate': payload['comments'][0]['body'] += '\ud800'
    if mutation == 'oversize': payload['comments'][0]['body'] = 'word ' * 3000
    with pytest.raises(HTTPException) as exc: save_feedback(root, JOB, payload)
    assert exc.value.status_code == status
    assert path.read_bytes() == before
    assert not list((root/'feedback-editor').glob('*.docx'))


def test_native_mapping_tampering_and_concurrent_saves(editable):
    root, raw, path, state, payload = editable
    def attempt():
        try:
            edited = copy.deepcopy(payload)
            edited['comments'][0]['body'] = 'Explain how this example supports your argument. A short connection here would help readers follow the purpose of the paragraph.'
            return save_feedback(root, JOB, edited)['validation']['ok']
        except HTTPException as exc: return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results.count(True) == 1 and results.count(409) == 1
    comments = copy.deepcopy(state['comments'])
    comments[0]['target_text'] = 'a different anchor'
    assert not register_review(root, 'ts-000000', raw, path, comments, 'Raunak Banga')['editing_available']
    payload['revision'] = digest(path.read_bytes())
    raw.write_bytes(raw.read_bytes() + b'tampered')
    with pytest.raises(HTTPException) as exc: save_feedback(root, JOB, payload)
    assert exc.value.status_code == 409


def test_api_round_trip_limits_and_download(editable, monkeypatch):
    from portal import server
    root, _, path, _, payload = editable
    monkeypatch.setattr(server, 'OUTPUT_DIR', root)
    payload['comments'][0]['body'] = 'Please explain the connection between this point and the main claim. This would help readers understand why the example belongs here.'
    with TestClient(server.app) as client:
        response = client.post(f'/api/thinkingstorm/feedback/{JOB}', json=payload)
        assert response.status_code == 200, response.text
        download = client.get(response.json()['commented_docx_url'])
        assert download.status_code == 200 and download.content == path.read_bytes()
        assert download.headers['cache-control'] == 'no-store'
        assert client.post(f'/api/thinkingstorm/feedback/{JOB}', content=b'x'*131073).status_code == 413
        assert client.post(f'/api/thinkingstorm/feedback/{JOB}', content=b'bad json').status_code == 400
        assert client.post(f'/api/thinkingstorm/feedback/{JOB}', content=json.dumps(dict(payload, edit_token='\ud800')).encode(), headers={'Content-Type': 'application/json'}).status_code == 403
        assert client.get('/download/feedback-editor%5Cts-123abc.json').status_code == 404
        assert client.post('/api/thinkingstorm/feedback/unsafe', json=payload).status_code == 400


def test_reviewer_supplied_feedback_can_be_edited_without_changing_manuscript(editable):
    from engine.thinkingstorm_engine import ThinkingStormAutomator
    root, raw, _, state, payload = editable
    manual = root / f'{JOB}_manual_commented.docx'
    comment = state['comments'][0]
    ThinkingStormAutomator().generate_reviewed_docx(str(raw), str(manual),
        student_name='Student', custom_comments=[dict(comment, category='THESIS STATEMENT')],
        custom_endnote_text=state['endnote_text'])
    # Use the delivered native body, independent of legacy field normalization.
    with ZipFile(manual) as z:
        native = etree.fromstring(z.read('word/comments.xml'))
        comment['comment_text'] = _comment_body(native.find(f'{W}comment'))
    registered = register_review(root, JOB, raw, manual, [comment], 'Raunak Banga')
    assert registered['editing_available'], registered
    payload.update(edit_token=registered['edit_token'], revision=registered['feedback_revision'],
                   endnote_text=registered['endnote_text'], comments=[{
                       'id':registered['comments'][0]['feedback_id'],
                       'body':'Explain how this example supports the main claim. The reader needs a clear connection between the evidence and the point you are making.'}])
    before = manual.read_bytes()
    saved = save_feedback(root, JOB, payload)
    assert saved['validation']['ok']
    import io
    with ZipFile(io.BytesIO(before)) as original, ZipFile(manual) as updated:
        assert original.read('word/document.xml') == updated.read('word/document.xml')
