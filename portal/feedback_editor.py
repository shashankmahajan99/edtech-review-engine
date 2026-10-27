"""Save reviewer-authored feedback while leaving manuscript/anchors untouched."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
from threading import RLock
import uuid
from zipfile import ZipFile

from fastapi import HTTPException
from lxml import etree

from engine.review.anti_ai_patterns import audit_ai_tells, scrub_ai_tells
from engine.review.docmodel import load_document
from engine.review.validate import W, R, _anchors, _comment_body, validate_deliverable
from engine.review.writer import _comment_element, _build_endnotes
from engine.review.letter_format import is_endnote_heading, parse_reviewer_letter
from engine.review.style_guard import banned_hits

LOCK = RLock()  # The deployed portal runs one process; saves execute in workers.
MAX_BODY = 128 * 1024
_SIGNOFF_RE = re.compile(
    r"^(?:All the best|Best wishes|Best regards|Warm regards|Sincerely|Thanks|Thank you)\b",
    re.IGNORECASE,
)


class FeedbackSaveError(HTTPException):
    def __init__(self, issues):
        self.issues = issues
        super().__init__(422, 'Feedback was not saved. ' + ' '.join(i['message'] for i in issues))


def _combined_tells(text: str) -> list[str]:
    return list(dict.fromkeys(banned_hits(text) + audit_ai_tells(text)))


def _save_issues(errors, ids, edits, letter, reviewer):
    """Turn release-gate diagnostics into instructions for the actual field."""
    issues = []
    for error in errors:
        match = re.match(r'^comment (\S+): (.*)', error)
        if match and match[1] in ids:
            cid, reason = match.groups()
            label = f'Comment {ids.index(cid) + 1}'
            issue = {'field': 'comment', 'comment_id': cid}
            count = re.match(r'(\d+) words outside 6-95', reason)
            if count:
                action = 'Add enough explanation to reach' if int(count[1]) < 6 else 'Shorten it to'
                message = f'{label} has {count[1]} words. {action} 6–95 words. A humanizer may change the length.'
            elif reason == 'empty body':
                message = f'{label} is empty. Add the feedback before saving.'
            elif 'terminal punctuation' in reason:
                message = f'{label} needs closing punctuation. Add a period, question mark or exclamation mark.'
            elif 'banned phrasing' in reason:
                message = f'{label}: rephrase these terms excluded by the feedback style check: {reason.removeprefix("banned phrasing ")}.'
            elif 'repeats its category label' in reason:
                message = f'{label}: remove the category heading from the body. Its linked heading is already kept separately.'
            elif reason == 'double space':
                message = f'{label}: remove repeated spaces in the feedback.'
            else:
                issue = {'field': 'document'}
                message = f'{label} failed a Word integrity check ({reason}). Retry saving; changing your wording will not repair an anchor or file-format problem.'
        elif error.startswith('comments: banned'):
            for cid in ids:
                hits = _combined_tells(edits[cid])
                if hits and not any(i.get('comment_id') == cid for i in issues):
                    issues.append({'field': 'comment', 'comment_id': cid,
                        'message': f'Comment {ids.index(cid) + 1}: rephrase these terms excluded by the feedback style check: {hits}.'})
            continue
        elif error.startswith('endnote has '):
            issue = {'field': 'endnote'}
            count = int(re.search(r'\d+', error)[0])
            if count > 3:
                message = f'Endnote has {count} section headings; keep 1–3 revision areas. A rewrite may repeat headings. Combine related sections and keep their explanations.'
            else:
                message = ('Endnote: we could not identify any revision headings. Humanizing may merge or rename them. '
                           'Put 1–3 headings on their own lines, such as Thesis, Evidence & Analysis, or Specific issues & links. '
                           'Other heading names can end in a colon. Follow each heading with its explanation.')
        elif error.startswith('endnote shorter than '):
            issue = {'field': 'endnote'}
            minimum = re.search(r'\d+', error)[0]
            message = f'Endnote has {len(" ".join(letter).split())} words; it needs at least {minimum} words for its revision sections. Restore any explanation removed during rewriting.'
        elif error == 'endnote does not open with a greeting':
            issue = {'field': 'endnote'}
            message = 'Endnote: restore the opening greeting, for example “Dear Student,”. A humanizer may have removed it.'
        elif error == 'endnote missing reviewer signature':
            issue = {'field': 'endnote'}
            message = f'Endnote: restore the reviewer signature “{reviewer}” at the end. A humanizer may have changed or removed it.'
        elif error.startswith('endnote:'):
            issue = {'field': 'endnote'}
            if 'banned' in error:
                hits = _combined_tells(" ".join(letter))
                message = f'Endnote: rephrase these terms excluded by the feedback style check: {hits}.'
            elif 'average sentence too long' in error:
                message = 'Endnote: some sentences became too long after rewriting. Split long sentences while keeping the advice intact.'
            else:
                message = f'Endnote: review this feedback check before saving: {error}.'
        else:
            issue = {'field': 'document'}
            message = f'The Word document failed an integrity check ({error}). Retry saving; your previous file and draft edits are preserved.'
        issues.append(dict(issue, message=message))
    return issues


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _job(job):
    if not re.fullmatch(r'ts-[a-f0-9]{6,32}', job):
        raise HTTPException(400, 'Invalid review identifier.')
    return job


def _file(root, name):
    if not isinstance(name, str) or '/' in name or '\\' in name or name in {'', '.', '..'}:
        raise HTTPException(400, 'Invalid review file.')
    path = root / name
    if path.resolve().parent != root.resolve():
        raise HTTPException(400, 'Invalid review file.')
    return path


def _parts(path):
    with ZipFile(path) as z:
        return (z.read('word/document.xml'), etree.fromstring(z.read('word/comments.xml')),
                etree.fromstring(z.read('word/endnotes.xml')))


def _letter(root):
    note = root.find(f"{W}endnote[@{W}id='1']")
    if note is None:
        raise ValueError('Missing native closing note.')
    lines = [''.join(t.text or '' for t in p.iter(f'{W}t'))
             for p in note.findall(f'{W}p')]
    if lines:
        lines[0] = lines[0].removeprefix(' ')
    return lines


def register_review(root, job, raw_path, docx_path, comments, reviewer_name):
    """Return editing capability only after checking display-to-native mapping."""
    root = Path(root)
    _job(job)
    try:
        document, native, notes = _parts(docx_path)
        anchors = _anchors(etree.fromstring(document))
        nodes = native.findall(f'{W}comment')
        if len(nodes) != len(comments) or not nodes:
            raise ValueError('The displayed comments do not match the native Word comments.')
        expected = []
        canonical = []
        for node, comment in zip(nodes, comments):
            cid = node.get(f'{W}id')
            ranges = anchors.get(cid, [])
            body = _comment_body(node)
            if len(ranges) != 1 or re.sub(r'\s+', ' ', ranges[0][2]).strip() != re.sub(r'\s+', ' ', comment['target_text']).strip() or body != comment['comment_text'].strip():
                raise ValueError('A displayed comment could not be matched to its Word anchor.')
            expected.append({'id': cid, 'quote': ranges[0][2]})
            canonical.append(dict(comment, feedback_id=cid, comment_text=body))
        if len({item['id'] for item in expected}) != len(expected):
            raise ValueError('The Word comment identifiers are ambiguous.')
        letter = '\n\n'.join(_letter(notes))
        token = secrets.token_urlsafe(32)
        state = {'raw': raw_path.name, 'docx': docx_path.name, 'reviewer': reviewer_name,
                 'token_hash': digest(token.encode()), 'anchors': expected,
                 'document_hash': digest(document), 'raw_hash': digest(raw_path.read_bytes())}
        _file(root, state['raw'])
        _file(root, state['docx'])
        directory = root / 'feedback-editor'
        directory.mkdir(exist_ok=True)
        (directory / f'{job}.json').write_text(json.dumps(state), encoding='utf8')
        return {'editing_available': True, 'edit_token': token,
                'feedback_revision': digest(docx_path.read_bytes()),
                'comments': canonical, 'endnote_text': letter}
    except (ValueError, KeyError, OSError) as exc:
        return {'editing_available': False,
                'editing_unavailable_reason': 'Editing is unavailable for this review: ' + str(exc)}


def _text(value, limit):
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(422, 'Feedback must be nonempty text within the field size limit.')
    if any(not (ord(c) in {9, 10, 13} or 32 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        raise HTTPException(422, 'Feedback contains a character Word cannot store.')
    if len(value.encode('utf8')) > limit:
        raise HTTPException(422, 'Feedback exceeds the field size limit.')
    return value.strip()


def _normalize_letter_paragraphs(letter: list[str], reviewer: str) -> list[str]:
    normalized: list[str] = []
    reviewer_low = reviewer.lower()
    for idx, para in enumerate(letter):
        if (
            (idx == 0 and para.lower().startswith('dear '))
            or is_endnote_heading(para)
            or reviewer_low in para.lower()
            or _SIGNOFF_RE.match(para)
        ):
            normalized.append(para)
        else:
            normalized.append(scrub_ai_tells(para, seed=f'en-{idx}'))
    return normalized


def save_feedback(root, job, payload):
    root = Path(root)
    _job(job)
    if not isinstance(payload, dict) or set(payload) != {'edit_token', 'revision', 'comments', 'endnote_text'}:
        raise HTTPException(400, 'Invalid feedback save request.')
    with LOCK:
        state_path = root / 'feedback-editor' / f'{job}.json'
        if not state_path.is_file():
            raise HTTPException(404, 'This review does not support editing. Run a new review first.')
        state = json.loads(state_path.read_text(encoding='utf8'))
        token = payload['edit_token']
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token) or not hmac.compare_digest(digest(token.encode()), state['token_hash']):
            raise HTTPException(403, 'The editing permission for this review is invalid.')
        path, raw = _file(root, state['docx']), _file(root, state['raw'])
        revision = digest(path.read_bytes())
        if payload['revision'] != revision:
            raise HTTPException(409, 'This DOCX changed since it was opened. Keep a copy of your edits and run a fresh review before saving.')
        document, native, notes = _parts(path)
        ids = [item['id'] for item in state['anchors']]
        if digest(document) != state['document_hash'] or digest(raw.read_bytes()) != state['raw_hash'] or [n.get(f'{W}id') for n in native.findall(f'{W}comment')] != ids:
            raise HTTPException(409, 'The manuscript or its comment anchors changed. No feedback was saved.')
        submitted = payload['comments']
        if not isinstance(submitted, list) or len(submitted) != len(ids) or any(not isinstance(c, dict) or set(c) != {'id', 'body'} or not isinstance(c['id'], str) for c in submitted):
            raise HTTPException(422, 'Save must include every existing comment and its identifier.')
        if len({c['id'] for c in submitted}) != len(ids) or {c['id'] for c in submitted} != set(ids):
            raise HTTPException(422, 'Comment identifiers do not match this review.')
        edits, preflight = {}, []
        for c in submitted:
            try:
                edits[c['id']] = scrub_ai_tells(' '.join(_text(c['body'], 10000).split()), seed=c['id'])
            except HTTPException as exc:
                preflight.append({'field': 'comment', 'comment_id': c['id'],
                    'message': f'Comment {ids.index(c["id"]) + 1}: {exc.detail}'})
        try:
            letter = _normalize_letter_paragraphs(
                parse_reviewer_letter(_text(payload['endnote_text'], 32000)),
                state['reviewer'],
            )
        except HTTPException as exc:
            preflight.append({'field': 'endnote', 'message': f'Endnote: {exc.detail}'})
        if preflight:
            raise FeedbackSaveError(preflight)
        for node in list(native.findall(f'{W}comment')):
            cid = node.get(f'{W}id')
            link = node.find(f'.//{W}hyperlink')
            label = ''.join(t.text or '' for t in link.iter(f'{W}t')) if link is not None else None
            replacement = _comment_element(int(cid), node.get(f'{W}author', state['reviewer']),
                node.get(f'{W}initials', ''), node.get(f'{W}date', ''), label, edits[cid],
                link.get(f'{R}id') if link is not None else None)
            native.replace(node, replacement)
        _build_endnotes(notes, letter, state['reviewer'])
        serialize = lambda node: etree.tostring(node, xml_declaration=True, encoding='UTF-8', standalone=True)
        replacements = {'word/comments.xml': serialize(native), 'word/endnotes.xml': serialize(notes)}
        temporary = state_path.parent / f'{uuid.uuid4().hex}.docx'
        try:
            with ZipFile(path) as source, ZipFile(temporary, 'w') as target:
                for part in source.infolist():
                    target.writestr(part, replacements.get(part.filename, source.read(part.filename)))
            validation = validate_deliverable(str(temporary), load_document(str(raw)),
                [(item['id'], item['quote']) for item in state['anchors']],
                [edits[cid] for cid in ids], letter, reviewer_name=state['reviewer'])
            if not validation.ok:
                raise FeedbackSaveError(_save_issues(validation.errors, ids, edits, letter, state['reviewer']))
            new_revision = digest(temporary.read_bytes())
            qa_name = f'{job}_saved_{new_revision[:16]}.json'
            result = {'comments': [{'id': cid, 'body': edits[cid]} for cid in ids],
                'endnote_text': '\n\n'.join(letter), 'feedback_revision': new_revision,
                'commented_docx_url': f'/download/commented/{job}?revision={new_revision}',
                'qa_report_url': f'/download/{qa_name}', 'saved_feedback': True,
                'validation': {'ok': True, 'errors': [], 'warnings': validation.warnings, 'metrics': validation.metrics}}
            (root / qa_name).write_text(json.dumps(dict(result, editorial_source='reviewer_edited', detector_score=None), indent=2), encoding='utf8')
            temporary.replace(path)  # Publish only a validated package; readers see old or new.
            return result
        finally:
            temporary.unlink(missing_ok=True)
