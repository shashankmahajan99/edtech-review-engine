"""Humanizer edits must not silently damage facts, advice or Word structure."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time

import pytest

from engine.feedback_humanizer import HumanizerUnavailable, LocalHumanizer
from engine.review.humanization import RejectedRewrite, TruncatedRewrite, mask_facts, validate_rewrite, humanize_review
from engine.review.pipeline import PipelineError, review_document
from engine.review_runtime import apply_runtime_defaults

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps({'model': 'thinkingstorm-humanizer', 'base_url': 'http://127.0.0.1:11437',
                               'prompt_path': str(ROOT / 'vendor/humanizer/prompt_format.json')}))
    return path


def test_raw_prompt_and_sampling_match_upstream(config, monkeypatch):
    h = LocalHumanizer(config)
    assert hashlib.sha256(h.prompt('X').encode()).hexdigest()[:16] == 'cc51d66b4c593fbe'
    h._active = True
    calls = []
    def request(path, payload):
        calls.append((path, payload))
        return {'content': 'A preserved rewrite.'}
    monkeypatch.setattr(h, '_request', request)
    assert h('X') == 'A preserved rewrite.'
    path, payload = calls[0]
    assert path == '/completion'
    assert payload['prompt'] == h.prompt('X')
    assert {k: payload[k] for k in ['temperature', 'top_p', 'top_k', 'min_p', 'repeat_penalty']} == dict(temperature=1.0, top_p=.95, top_k=0, min_p=0, repeat_penalty=1.0)
    assert 'stop' not in payload and 'messages' not in payload


@pytest.mark.parametrize('change', [{'base_url': 'https://example.com'}, {'budget_seconds': 181}, {'extra': True}])
def test_invalid_or_remote_config_is_rejected(config, change):
    cfg = json.loads(config.read_text()); cfg.update(change); config.write_text(json.dumps(cfg))
    with pytest.raises(HumanizerUnavailable):
        LocalHumanizer(config)


@pytest.mark.parametrize('provider', ['completion', 'instruct'])
def test_truncated_output_is_not_delivered(config, monkeypatch, provider):
    if provider == 'instruct':
        cfg = json.loads(config.read_text())
        cfg.update(provider='instruct', model='thinkingstorm-editor', prompt_path=str(ROOT / 'vendor/humanizer/editor_prompt.txt'))
        config.write_text(json.dumps(cfg))
    h = LocalHumanizer(config); h._active = True
    reply = ({'content': 'Incomplete', 'stopped_limit': True} if provider == 'completion' else
             {'choices': [{'finish_reason': 'length', 'message': {'content': 'Incomplete'}}]})
    monkeypatch.setattr(h, '_request', lambda *args: reply)
    with pytest.raises(TruncatedRewrite, match='truncated'):
        h('Some feedback for the student.')


def test_repeated_truncation_retains_valid_feedback_and_releases_word_document(tmp_path):
    source = ROOT / 'tests/fixtures/andrea_raw.docx'
    baseline = review_document(source, tmp_path / 'baseline', backend='rules')
    def cutoff(text):
        raise TruncatedRewrite('Humanizer rewrite was truncated at its output limit.')
    result = review_document(source, tmp_path / 'edited', backend='rules', feedback_rewriter=cutoff)
    assert result.validation.ok
    assert [c['body'] for c in result.comments] == [c['body'] for c in baseline.comments]
    assert result.endnote == baseline.endnote
    audit = result.generation['humanization']
    assert audit['retained'] > 0
    assert audit['truncated_attempts'] == 2 * audit['retained']
    assert audit['retries'] == audit['retained']
    assert result.quality['needs_review'] and any('Humanizer retained' in m for m in result.quality['messages'])


def test_truncated_first_attempt_can_recover_without_retaining_the_passage(tmp_path):
    attempts = 0
    def recover(text):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TruncatedRewrite('Humanizer rewrite was truncated at its output limit.')
        return text
    result = review_document(ROOT / 'tests/fixtures/andrea_raw.docx', tmp_path,
                             backend='rules', feedback_rewriter=recover)
    audit = result.generation['humanization']
    assert result.validation.ok
    assert audit['truncated_attempts'] == 1 and audit['retries'] == 1 and audit['retained'] == 0


def test_deadline_exhaustion_rejects_instead_of_queuing(config):
    h = LocalHumanizer(config); h.deadline = time.monotonic() - 1
    with pytest.raises(HumanizerUnavailable, match='time budget'):
        h._request('/completion', {})


def test_nonblocking_lock_prevents_competing_review_sessions(config, tmp_path, monkeypatch):
    import engine.feedback_humanizer as transport
    monkeypatch.setattr(transport, 'ROOT', tmp_path)
    a, b = LocalHumanizer(config), LocalHumanizer(config)
    def status(path, payload=None):
        return {'data': [{'id': a.model}]} if path == '/v1/models' else [{'is_processing': False}]
    monkeypatch.setattr(a, '_request', status)
    with a.session():
        with pytest.raises(HumanizerUnavailable, match='busy'):
            with b.session():
                pytest.fail('a competing session was admitted')


def test_abandoned_busy_slot_is_not_admitted(config, tmp_path, monkeypatch):
    import engine.feedback_humanizer as transport
    monkeypatch.setattr(transport, 'ROOT', tmp_path)
    h = LocalHumanizer(config)
    monkeypatch.setattr(h, '_request', lambda p: {'data': [{'id': h.model}]} if p == '/v1/models' else [{'is_processing': True}])
    with pytest.raises(HumanizerUnavailable, match='slot is still busy'):
        with h.session():
            pytest.fail('busy slot admitted')


def test_quotes_names_urls_units_and_placeholder_like_input_round_trip():
    body = 'Check Smith and MLA against “37  percent” at https://example.org/a. Keep [[KEEP_1]] and the 25 kg figure unchanged.'
    masked, facts, nonce = mask_facts(body)
    assert '37  percent' not in masked and 'https://' not in masked and 'Smith' not in masked
    assert validate_rewrite(body, masked, facts, nonce) == body


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'unknown'])
def test_damaged_placeholders_are_rejected(change):
    body = 'The finding from Smith needs a citation before the reader can check it.'
    masked, facts, nonce = mask_facts(body); first = next(iter(facts))
    candidate = masked.replace(first, '') if change == 'missing' else masked + ' ' + (first if change == 'duplicate' else f'HZ{nonce}X999Z')
    with pytest.raises(RejectedRewrite, match='protected fact'):
        validate_rewrite(body, candidate, facts, nonce)


@pytest.mark.parametrize('before,after', [
    ('This claim may need support before the reader can judge it.', 'This claim needs support before the reader can judge it.'),
    ('Change this wording only if the source uses a different term.', 'Change this wording because the source uses a different term.'),
    ('Keep this heading unless the section focus changes.', 'Keep this heading when the section focus changes.'),
    ('Do not remove this example because it explains the central claim.', 'Remove this example because it explains the central claim.'),
    ('Add an example that explains how the source supports your central claim.', 'Remove an example that explains how the source supports your central claim.'),
    ('Explain how this example supports the claim for the reader.', 'I would explain how this example supports the claim for the reader.'),
    ('Explain how this example supports the claim for the reader.', 'Explain how this example supports the claim for 90 readers.'),
])
def test_uncertainty_negation_advice_person_and_numbers_are_guarded(before, after):
    masked, facts, nonce = mask_facts(before)
    # These examples contain no protected terms, so the replacement is plain prose.
    assert not facts
    with pytest.raises(RejectedRewrite):
        validate_rewrite(before, after, facts, nonce)


def test_imperative_advice_allows_natural_modal_and_conditional_recasting():
    before = 'If the source supports this point, you may add a short explanation to connect the quote.'
    after = 'Add a short explanation to connect the quote and show how the source supports this point.'
    masked, facts, nonce = mask_facts(before)
    assert not facts
    assert validate_rewrite(before, after, facts, nonce) == after


def test_no_contractions_are_added_to_prose_or_expanded_inside_quotes():
    before = 'You do not need to change “don\'t do that” because it is a source quotation.'
    masked, facts, nonce = mask_facts(before)
    assert validate_rewrite(before, masked.replace('do not', "don't"), facts, nonce) == before


def test_pipeline_keeps_anchors_and_letter_structure_with_injected_editor(tmp_path):
    source = ROOT / 'tests/fixtures/andrea_raw.docx'
    baseline = review_document(source, tmp_path / 'baseline', backend='rules')
    edited = review_document(source, tmp_path / 'edited', backend='rules', feedback_rewriter=lambda text: text)
    assert edited.validation.ok
    assert [(c['quote'], c['paragraph'], c['category']) for c in edited.comments] == [(c['quote'], c['paragraph'], c['category']) for c in baseline.comments]
    assert edited.endnote == baseline.endnote
    assert edited.generation['humanization']['rewritten'] == 0
    assert edited.generation['humanization']['retained'] == 0


def test_unavailable_humanizer_does_not_silently_fall_back(tmp_path):
    def broken(text):
        raise HumanizerUnavailable('runtime unavailable')
    with pytest.raises(PipelineError, match='runtime unavailable'):
        review_document(ROOT / 'tests/fixtures/andrea_raw.docx', tmp_path, backend='rules', feedback_rewriter=broken)
    assert not list(tmp_path.glob('*commented.docx'))


def test_rejected_edits_keep_original_prose_and_force_visible_review(tmp_path):
    result = review_document(ROOT / 'tests/fixtures/andrea_raw.docx', tmp_path,
        backend='rules', feedback_rewriter=lambda text: '<script>unsafe</script>')
    audit = result.generation['humanization']
    assert audit['retained'] > 0 and audit['retries'] == audit['retained']
    assert result.quality['needs_review']
    assert any('Humanizer retained' in m for m in result.quality['messages'])
    assert audit['rewritten'] + audit['unchanged'] + audit['retained'] == audit['attempted']


def test_profile_defaults_and_explicit_overrides(tmp_path, monkeypatch):
    import os
    profile = tmp_path / 'profile.json'
    profile.write_text(json.dumps({'backend': 'rules', 'humanizer': 'local', 'humanizer_config': str(tmp_path / 'humanizer.json')}))
    env = {'TS_RUNTIME_PROFILE': str(profile), 'TS_REVIEW_BACKEND': 'local', 'TS_HUMANIZER': 'off'}
    monkeypatch.setattr(os, 'environ', env)
    apply_runtime_defaults()
    assert env['TS_REVIEW_BACKEND'] == 'local' and env['TS_HUMANIZER'] == 'off'
    del env['TS_REVIEW_BACKEND']; del env['TS_HUMANIZER']
    apply_runtime_defaults()
    assert env['TS_REVIEW_BACKEND'] == 'rules' and env['TS_HUMANIZER'] == 'local'


def test_comment_collision_with_original_letter_rolls_back_all_changes(monkeypatch):
    from types import SimpleNamespace
    import engine.review.humanization as module
    from engine.review.endnote import Endnote
    before = 'Add a short explanation that connects the evidence to your paragraph claim.'
    after = 'Add a sentence explaining how the evidence supports the claim in this paragraph.'
    item = SimpleNamespace(category='SENTENCE CLARITY', finding=SimpleNamespace(rule_id='test'))
    paragraphs = ['Dear Student,', 'Focus this revision on the relationship between evidence and claims.',
                  'Evidence:', ('The revision plan asks you to check each claim against its source. ' * 11) + after,
                  'Use these steps to guide your next revision.', 'All the best.', 'Reviewer']
    note = Endnote(paragraphs, ['Evidence'], len(' '.join(paragraphs).split()), [])
    def rewrite(text):
        return after if text == before else text
    comments, letter, audit, warnings = humanize_review(None, [(item, before)], note, rewrite)
    assert comments[0][1] == before and letter.paragraphs == paragraphs
    assert audit['rewritten'] == 0 and audit['retained'] == 1 and warnings


def test_instruct_editor_disables_reasoning_and_keeps_prose_contract(config, monkeypatch):
    cfg = json.loads(config.read_text())
    cfg.update(provider='instruct', model='thinkingstorm-editor', prompt_path=str(ROOT / 'vendor/humanizer/editor_prompt.txt'))
    config.write_text(json.dumps(cfg))
    h = LocalHumanizer(config); h._active = True
    seen = []
    def request(path, payload):
        seen.append((path, payload))
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': 'The edited paragraph.'}}]}
    monkeypatch.setattr(h, '_request', request)
    assert h('The original paragraph.') == 'The edited paragraph.'
    path, payload = seen[0]
    assert path == '/v1/chat/completions'
    assert payload['temperature'] == .72
    assert payload['top_p'] == .92
    assert 'repeat_penalty' not in payload
    assert payload['chat_template_kwargs']['enable_thinking'] is False
    assert payload['messages'][-1]['content'] == 'The original paragraph.'

    assert h('The original paragraph.', retry=True) == 'The edited paragraph.'
    _, retry_payload = seen[1]
    assert retry_payload['temperature'] == .35
    assert retry_payload['top_p'] == .90


def test_legacy_helpers_never_invent_reviewer_diagnoses_or_change_quotes():
    from engine.anti_ai_humanizer import inject_human_burstiness, humanize_editorial_comment, sanitize_ai_vocabulary
    sentences = ['This is a long explanation about an actual draft issue, with enough detail that the old helper could randomly append an unrelated tense warning.', 'Preserve this sentence.']
    assert inject_human_burstiness(sentences) == sentences
    source = 'Do not change “pivotal” because this is the quoted wording being discussed.'
    assert humanize_editorial_comment(source) == source
    assert sanitize_ai_vocabulary(source) == source


def test_word_replacement_instruction_is_protected_as_one_fact():
    source = 'Change “reflect” to “reflects” and explain what the phrase means.'
    masked, facts, nonce = mask_facts(source)
    assert 'Change “reflect” to “reflects”' in facts.values()
    assert validate_rewrite(source, masked, facts, nonce) == source


def test_full_date_and_quoted_terminal_punctuation_round_trip():
    source = 'Use 20 Feb. 2026 and the title “A study.” This gives the reader the source details.'
    masked, facts, nonce = mask_facts(source)
    assert '20 Feb. 2026' in facts.values()
    assert validate_rewrite(source, masked, facts, nonce) == source
    title_marker = next(key for key, value in facts.items() if value == '“A study.”')
    with pytest.raises(RejectedRewrite, match='punctuation'):
        validate_rewrite(source, masked.replace(title_marker + '.', title_marker + ','), facts, nonce)


def test_recommendation_is_not_upgraded_to_a_requirement():
    original = 'The heading should match the name and date lines in this draft.'
    candidate = 'The heading must match the name and date lines in this draft.'
    _, facts, nonce = mask_facts(original)
    assert validate_rewrite(original, candidate, facts, nonce) == original


def test_quoted_comma_is_not_duplicated_by_surrounding_prose():
    source = 'Replace the phrase with “passive wish,” and explain the source connection.'
    masked, facts, nonce = mask_facts(source)
    assert validate_rewrite(source, masked, facts, nonce) == source


def test_sentence_opening_imperatives_and_common_nouns_are_not_masked_as_names():
    text = 'Dates follow this convention. Apply it throughout the source list. Could you name the intended idea? Attach the phrase to a complete sentence.'
    masked, facts, nonce = mask_facts(text)
    assert masked == text and not facts
    text = 'Taylor should check the date before submitting the next draft.'
    masked, facts, nonce = mask_facts(text, {'Taylor'})
    assert 'Taylor' not in masked and 'Taylor' in facts.values()


def test_revision_instructions_cannot_become_a_claim_that_edits_are_done():
    source = 'Read the paragraph as a sequence of main point, evidence and explanation. Mark a break where a separate point begins.'
    candidate = 'The paragraph presents a sequence of main point, evidence and explanation. A break is marked where a separate point begins.'
    _, facts, nonce = mask_facts(source)
    with pytest.raises(RejectedRewrite, match='instructions|completed'):
        validate_rewrite(source, candidate, facts, nonce)


def test_precise_date_correction_never_swaps_current_and_suggested_values():
    from types import SimpleNamespace
    from engine.review.endnote import Endnote
    body = 'Dates in MLA run day-month-year. Set this one as 15 October 2026.'
    item = SimpleNamespace(category='MLA', finding=SimpleNamespace(rule_id='mla_date_numeric'))
    paragraphs = ['Dear Student,', 'This revision needs a clear plan for the next draft.', 'Evidence:',
                  'Connect the evidence to the claim before moving to the next point. ' * 12,
                  'Use these steps to guide the next revision.', 'All the best.', 'Reviewer']
    note = Endnote(paragraphs, ['Evidence'], len(' '.join(paragraphs).split()), [])
    def rewrite(text):
        assert 'day-month-year' not in text
        return text
    comments, _, audit, _ = humanize_review(None, [(item, body)], note, rewrite)
    assert comments[0][1] == body
    assert audit['pieces'][0]['status'] == 'unchanged'
    assert audit['pieces'][0]['reason'] == 'precise date-format correction preserved'
