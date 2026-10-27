"""Offline guards for an injected feedback rewriter; no inference or network here."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib
import inspect
import re
import time

from .anti_ai_patterns import audit_ai_tells, scrub_ai_tells
from .coverage import copied_comment_sentences
from .style_guard import banned_hits
from .progress import emit_progress

QUALIFIERS = re.compile(r'\b(?:not|no|never|without|cannot|may|might|could|likely|possibly|if|unless)\b', re.I)
NEGATIONS = re.compile(r'\b(?:not|no|never|without|cannot|unless)\b', re.I)
STRICT_CONDITIONALS = re.compile(r'\b(?:only\s+if|unless)\b', re.I)
ANY_CONDITIONAL = re.compile(r'\b(?:if|unless|when|where|whether)\b', re.I)
UNCERTAINTY = re.compile(r'\b(?:may|might|could|likely|possibly)\b', re.I)
ADVICE_START = re.compile(r'(?:^|[.!?;]\s+)(?:Please\s+)?(?:Add|Apply|Attach|Check|Choose|Clarify|Compare|Connect|Consider|Correct|Define|Develop|Discuss|Distinguish|Explain|Give|Identify|Include|Introduce|Keep|Limit|Make|Mark|Move|Name|Narrow|Place|Put|Read|Remove|Replace|Return|Review|Revise|Rewrite|Separate|Set|Show|Specify|State|Support|Use|Verify)\b', re.I)
STARTERS = set('The This That These Those Your You It In On At For To A An As And But Or If When While With Without Read Add Keep Use Remove Explain Revise Check Consider Make Write Replace Change Rewrite Narrow Correct Expand Define Simplify Consolidate Introduce Summarize Qualify Limit Strengthen Start End Show Support Name Choose Connect Identify Compare Clarify Avoid Give Ask First Next Then Finally Before After Each Both Dear All Best MLA APA Which What How Where Why Does Do Is Are Since Because Instead Once Focus Try Acknowledge Distinguish Link Develop Describe Specify Discuss State Refer Cite Set Put Move Spell Capitalize Reorder Include Separate Format Say Allow Ensure Begin Prioritize Preserve Verify Maintain Ground Refine Review Also Note'.split())
FACTS = re.compile(
    r'(?:Change|Replace)\s+(?:“[^”]*”|"[^"\n]*")\s+(?:to|with)\s+(?:“[^”]*”|"[^"\n]*")|'
    r'“[^”]*”|"[^"\n]*"|‘(?:[^’]|(?<=\w)’(?=\w))*’|https?://[^\s<>]+|'
    r'\[\[KEEP_[^\]]+\]\]|'
    r'\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{4}\b|'
    r'(?:[$£€]\s*)?\b\d+(?:[.,]\d+)*(?:\s*(?:%|percent\b|mg\b|kg\b|km\b|cm\b|mm\b|miles?\b|hours?\b|days?\b|months?\b|years?\b))?|'
    r'\b[A-Z][A-Za-z]*(?:[-\'][A-Z][A-Za-z]*)?\b')
CONTRACTIONS = {"can't": 'cannot', "won't": 'will not', "don't": 'do not',
                "doesn't": 'does not', "isn't": 'is not', "aren't": 'are not',
                "shouldn't": 'should not', "couldn't": 'could not', "wouldn't": 'would not',
                "it's": 'it is', "you're": 'you are', "that's": 'that is',
                "there's": 'there is', "you'll": 'you will', "you've": 'you have'}


class RejectedRewrite(ValueError):
    pass


class TruncatedRewrite(RejectedRewrite):
    """An incomplete candidate can be retried, but must never be delivered."""


def _expand(text):
    def expand(match):
        value = CONTRACTIONS[match.group().lower().replace('’', "'")]
        return value[0].upper() + value[1:] if match.group()[0].isupper() else value
    return re.sub(r'\b(?:' + '|'.join(re.escape(k).replace("'", "['’]") for k in CONTRACTIONS) + r')\b', expand, text, flags=re.I)


def mask_facts(text, known_names=()):
    """Keep quoted specimens, names, URLs and numeric facts byte-for-byte."""
    nonce = hashlib.sha256(text.encode()).hexdigest()[:10]
    while 'HZ' + nonce in text:
        nonce += 'x'
    protected, output, cursor = {}, [], 0
    for match in FACTS.finditer(text):
        value = match.group()
        if value in STARTERS and not value.isupper():
            continue
        if value.isalpha() and not (value.isupper() and len(value) > 1) and value not in known_names:
            preceding = text[:match.start()]
            if not preceding.strip() or re.search(r'[.!?:;][”\"’]?\s*$', preceding):
                # Sentence capitalization is not evidence of a proper name.
                # Masking an ordinary imperative makes the model misread it as
                # an opaque entity and can turn its instruction into a fragment.
                continue
        suffix = value[-2] if len(value) >= 2 and value[-1] in {'”', '"', '’'} and value[-2] in '.!?,;:' else ''
        key = f'HZ{nonce}X{len(protected)}Z'
        output.extend([_expand(text[cursor:match.start()]), key + suffix])
        protected[key] = value
        cursor = match.end()
    output.append(_expand(text[cursor:]))
    return ''.join(output), protected, nonce


def _outside_quotes(text):
    return re.sub(r'“[^”]*”|"[^"\n]*"|‘(?:[^’]|(?<=\w)’(?=\w))*’', '', text)


def validate_rewrite(original, candidate, protected, nonce, *, developmental=False, comment=True):
    if not isinstance(candidate, str) or not candidate.strip():
        raise RejectedRewrite('empty rewrite')
    markers = re.findall(r'HZ' + re.escape(nonce) + r'X\d+Z', candidate)
    if Counter(markers) != Counter(protected.keys()):
        raise RejectedRewrite('a protected fact was lost, duplicated or invented')
    candidate = re.sub(r'\s+', ' ', _expand(candidate)).strip()
    original_prose = _outside_quotes(original)
    # Undo newly introduced formal synonyms when the source already chose the
    # plain equivalent. Protected quotations and names are still placeholders.
    for formal, plain_word in {'individuals': 'people', 'requires': 'needs',
                               'demonstrate': 'show', 'demonstrates': 'shows',
                               'provides': 'gives', 'provide': 'give',
                               'incorporate': 'add', 'therefore': 'so',
                               'constitutes': 'counts as'}.items():
        if re.search(r'\b' + re.escape(plain_word) + r'\b', original_prose, re.I) and not re.search(r'\b' + formal + r'\b', original_prose, re.I):
            candidate = re.sub(r'\b' + formal + r'\b', lambda m: plain_word.capitalize() if m.group()[0].isupper() else plain_word, candidate, flags=re.I)
    # An editor may recast "should check" as "check" without changing advice.
    # It must not upgrade an ordinary recommendation to a mandatory requirement.
    if re.search(r'\bshould\b', original, re.I) and not re.search(r'\bmust\b', original, re.I):
        candidate = re.sub(r'\bmust\b', 'should', candidate, flags=re.I)
    elif not re.search(r'\bmust\b', original, re.I) and re.search(r'\bmust\b', candidate, re.I):
        raise RejectedRewrite('new mandatory requirement')
    for marker, literal in protected.items():
        if literal.startswith(('Change ', 'Replace ')) and original.startswith(literal) and not candidate.startswith(marker):
            raise RejectedRewrite('explicit word-replacement advice moved into another claim')
        if len(literal) >= 2 and literal[-1] in {'”', '"', '’'} and literal[-2] in '.!?,;:':
            if literal[-2] in '.!?' and re.search(re.escape(marker) + r'[,;:]', candidate):
                raise RejectedRewrite('conflicting punctuation added after a quotation')
            candidate = candidate.replace(marker + literal[-2], marker)
        candidate = candidate.replace(marker, literal)
    candidate = scrub_ai_tells(candidate, seed=nonce)
    plain, before = _outside_quotes(candidate), _outside_quotes(original)
    if ADVICE_START.search(before) and not (ADVICE_START.search(plain) or re.search(r'\b(?:should|could|may|might)\b|\byou\s+(?:need|can|must)\b', plain, re.I)):
        raise RejectedRewrite('revision instructions became a description instead of advice')
    completed = r'\b(?:has|have|was|were|is|are|been)\s+(?:already\s+)?(?:added|removed|marked|corrected|inserted|revised|replaced|rewritten)\b'
    if re.search(completed, plain, re.I) and not re.search(completed, before, re.I):
        raise RejectedRewrite('a suggested change was falsely described as completed')
    numeric = lambda text: Counter(re.sub(r'\s+', '', number) for number in re.findall(r'\d+(?:[.,]\d+)*\s*%?', text))
    if numeric(candidate) != numeric(original):
        raise RejectedRewrite('numeric facts changed')
    quotes = lambda text: Counter(re.findall(r'“[^”]*”|"[^"\n]*"|‘(?:[^’]|(?<=\w)’(?=\w))*’', text))
    if quotes(candidate) != quotes(original):
        raise RejectedRewrite('quotation wording or punctuation changed')
    if re.search(r'[.!?][”\"’],', candidate) and not re.search(r'[.!?][”\"’],', original):
        raise RejectedRewrite('conflicting punctuation added after a quotation')
    if re.search(r'^(?:Rewrite|Revise|Change|Replace)\s+[^.!?]{0,70}\b(?:ensures|makes|allows|gives)\b', candidate) and not re.search(r'\b(?:so|that|which)\b', candidate.split('.')[0], re.I):
        raise RejectedRewrite('imperative sentence became ungrammatical')
    expanded_plain, expanded_before = _expand(plain), _expand(before)
    if Counter(s.lower() for s in NEGATIONS.findall(expanded_plain)) != Counter(s.lower() for s in NEGATIONS.findall(expanded_before)):
        raise RejectedRewrite('negation, conditions or uncertainty changed')
    if STRICT_CONDITIONALS.search(expanded_before) and not ANY_CONDITIONAL.search(expanded_plain):
        raise RejectedRewrite('negation, conditions or uncertainty changed')
    if UNCERTAINTY.search(expanded_before) and not ADVICE_START.search(plain) and not UNCERTAINTY.search(expanded_plain):
        raise RejectedRewrite('negation, conditions or uncertainty changed')
    if len(re.findall(r'\b(?:I|me|my|we|our)\b', plain, re.I)) > len(re.findall(r'\b(?:I|me|my|we|our)\b', before, re.I)):
        raise RejectedRewrite('new first-person claim')
    if re.search(r'<[^>]+>|```|^\s*#|\b(?:fuck|shit|bullshit)\b', candidate, re.I):
        raise RejectedRewrite('markup or register changed')
    if any(phrase in plain.lower() and phrase not in before.lower() for phrase in ['you really need', 'throw in', 'what is this all about', 'make it pop', 'then maybe', 'probably just']):
        raise RejectedRewrite('informal filler added')
    original_names = {word.casefold() for word in re.findall(r'\b[A-Za-z]+\b', original)}
    new_names = {m.group() for m in re.finditer(r'\b[A-Z][a-zA-Z]+\b', candidate) if m.group() not in STARTERS}
    if {word.casefold() for word in new_names} - original_names:
        raise RejectedRewrite('new named term')
    groups = [r'\b(?:add|include|insert|provide)\b', r'\b(?:remove|delete|omit|cut)\b']
    for group, opposing in zip(groups, reversed(groups)):
        if re.search(group, before, re.I) and not re.search(opposing, before, re.I) and re.search(opposing, plain, re.I):
            raise RejectedRewrite('advice direction changed')
    count, old_count = len(candidate.split()), len(original.split())
    if not max(6, old_count * .65) <= count <= min(95 if comment else 250, old_count * 1.6):
        raise RejectedRewrite('rewrite is too short or too long')
    if developmental and old_count >= 25 and count < 25:
        raise RejectedRewrite('developmental advice became too short')
    if not re.search(r'[.!?\"”]$', candidate) or banned_hits(candidate) or audit_ai_tells(candidate):
        raise RejectedRewrite('unfinished sentence or stock phrasing')
    return candidate


def narrative_indices(endnote):
    return [i for i in range(1, len(endnote.paragraphs) - 2) if not endnote.paragraphs[i].endswith(':')]


def feedback_piece_count(composed, endnote):
    return len(composed) + len(narrative_indices(endnote))


def humanize_review(model, composed, endnote, rewrite, progress=None):
    started = time.monotonic()
    original_comments, original_letter = list(composed), list(endnote.paragraphs)
    pieces = []
    retries = 0
    truncated_attempts = 0
    total_passages = feedback_piece_count(composed, endnote)
    completed_passages = 0
    try:
        accepts_retry = 'retry' in inspect.signature(rewrite).parameters
    except (TypeError, ValueError):
        accepts_retry = False

    def report(stage):
        elapsed = time.monotonic() - started
        eta = (elapsed / completed_passages * (total_passages - completed_passages)
               if completed_passages >= 3 and elapsed >= 1 and completed_passages < total_passages else None)
        emit_progress(progress, stage, completed_passages=completed_passages,
                      total_passages=total_passages, editing_eta_seconds=eta)

    report('humanizing')
    known_names = set(re.findall(r'\b[A-Z][a-z]+\b', endnote.paragraphs[0] + ' ' + endnote.paragraphs[-1])) - STARTERS
    for paragraph in getattr(model, 'paragraphs', []):
        if paragraph.region == 'references':
            known_names.update(re.findall(r'\b[A-Z][a-z]+(?=,)', paragraph.text))

    def edit_candidate(body, kind, index, developmental=False, preserve_reason=''):
        nonlocal retries, truncated_attempts
        item = {'kind': kind, 'index': index, 'status': 'unchanged', 'reason': ''}
        pieces.append(item)
        if preserve_reason:
            item['reason'] = preserve_reason
            return body
        if len(body.split()) < 6:
            item['reason'] = 'short narrative retained'
            return body
        masked, protected, nonce = mask_facts(body, known_names)
        for attempt in range(2):
            try:
                raw_candidate = rewrite(masked, retry=attempt > 0) if accepts_retry else rewrite(masked)
                value = validate_rewrite(body, raw_candidate, protected, nonce,
                                         developmental=developmental, comment=kind == 'comment')
                if re.findall(r'\w+', value.lower()) == re.findall(r'\w+', body.lower()):
                    item['reason'] = ''
                    return body
                item['status'] = 'rewritten'
                item['reason'] = ''
                return value
            except RejectedRewrite as exc:
                truncated_attempts += int(isinstance(exc, TruncatedRewrite))
                item['reason'] = str(exc)
                retries += int(attempt == 0)
                if attempt == 0:
                    report('retry')
        item['status'] = 'retained'
        return body

    def edit(body, kind, index, developmental=False, preserve_reason=''):
        nonlocal completed_passages
        report('humanizing')
        result = edit_candidate(body, kind, index, developmental, preserve_reason)
        completed_passages += 1
        report('humanizing')
        return result

    from .selection import RHETORICAL
    from .analysis import ANALYSIS, STATISTICS
    developmental_categories = RHETORICAL | {ANALYSIS, STATISTICS}
    composed = [(item, edit(body, 'comment', i, item.category.split(' AND ')[0] in developmental_categories,
                           'precise date-format correction preserved' if item.finding.rule_id in {'mla_date_numeric', 'apa_date_numeric'} else ''))
                for i, (item, body) in enumerate(composed)]
    paragraphs = list(endnote.paragraphs)
    for i in narrative_indices(endnote):
        paragraphs[i] = edit(paragraphs[i], 'letter', i)
    note = replace(endnote, paragraphs=paragraphs, word_count=len(' '.join(paragraphs).split()))

    def rollback(kind, reason):
        for item in pieces:
            if (kind is None or item['kind'] == kind) and item['status'] == 'rewritten':
                item.update(status='retained', reason=reason)

    if not 138 <= note.word_count <= 382:
        note = endnote
        rollback('letter', 'closing note length changed beyond the reference range')
    normalize = lambda sentence: re.sub(r'\s+', ' ', sentence).casefold()
    baseline = {normalize(s) for s in copied_comment_sentences(original_comments, endnote)}
    if {normalize(s) for s in copied_comment_sentences(composed, note)} - baseline:
        composed, note = original_comments, endnote
        rollback(None, 'new margin sentences repeated in the closing note')
    counts = Counter(item['status'] for item in pieces)
    metadata = {'enabled': True, 'mode': 'guarded', 'provider': 'local-humanizer', 'model': getattr(rewrite, 'model_name', getattr(rewrite, 'model', 'injected')),
                'elapsed_seconds': round(time.monotonic() - started, 2), 'attempted': len(pieces),
                'rewritten': counts['rewritten'], 'unchanged': counts['unchanged'], 'retained': counts['retained'],
                'retries': retries, 'truncated_attempts': truncated_attempts,
                'pieces': pieces, 'detector_score': None}
    warnings = ([f"Humanizer retained {counts['retained']} passage(s) because their rewrites did not pass preservation checks; review the original prose."]
                if counts['retained'] else [])
    return composed, note, metadata, warnings
