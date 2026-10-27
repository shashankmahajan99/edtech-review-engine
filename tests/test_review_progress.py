"""Progress counts real completed work and never changes the review's outcome."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
from threading import Event
import time

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from portal.review_progress import ReviewProgressRegistry
from engine.review.pipeline import review_document

ROOT = Path(__file__).resolve().parents[1]
TOKEN = '1' * 32


def test_counts_retry_and_completion_are_real_and_monotonic():
    clock = [0.0]
    registry = ReviewProgressRegistry(clock=lambda: clock[0])
    update = registry.start(TOKEN)
    assert registry.snapshot(TOKEN)['percent'] is None
    update({'stage': 'reviewing'})
    update({'stage': 'feedback_ready', 'total_passages': 5, 'completed_passages': 0})
    assert registry.snapshot(TOKEN)['completed_units'] == 2
    update({'stage': 'humanizing', 'total_passages': 5, 'completed_passages': 3, 'editing_eta_seconds': 4.2})
    snapshot = registry.snapshot(TOKEN)
    assert snapshot['remaining_passages'] == 2 and snapshot['percent'] == 55
    assert snapshot['editing_eta_seconds'] == 5
    update({'stage': 'retry', 'total_passages': 5, 'completed_passages': 3})
    assert registry.snapshot(TOKEN)['percent'] == 55
    update({'stage': 'humanizing', 'total_passages': 5, 'completed_passages': 2})
    assert registry.snapshot(TOKEN)['completed_passages'] == 3
    update({'stage': 'humanizing', 'total_passages': 5, 'completed_passages': 5})
    update({'stage': 'document'})
    assert registry.snapshot(TOKEN)['editing_eta_seconds'] is None
    update({'stage': 'document_ready'})
    assert registry.snapshot(TOKEN)['percent'] == 88
    registry.finish(TOKEN, True)
    assert registry.snapshot(TOKEN)['percent'] == 100
    update({'stage': 'reading', 'text': 'private manuscript'})
    assert registry.snapshot(TOKEN)['stage'] == 'complete'
    assert 'private manuscript' not in json.dumps(registry.snapshot(TOKEN))


def test_failure_never_reports_100_percent():
    registry = ReviewProgressRegistry()
    update = registry.start(TOKEN)
    update({'stage': 'feedback_ready', 'total_passages': 0, 'completed_passages': 0})
    registry.finish(TOKEN, False)
    assert registry.snapshot(TOKEN)['status'] == 'failed'
    assert registry.snapshot(TOKEN)['percent'] == 50


def test_registry_bounds_duplicates_expiry_and_private_tokens():
    clock = [0.0]
    registry = ReviewProgressRegistry(clock=lambda: clock[0], capacity=1)
    with pytest.raises(HTTPException) as error:
        registry.start('guessable')
    assert error.value.status_code == 400
    registry.start(TOKEN)
    with pytest.raises(HTTPException) as error:
        registry.start(TOKEN)
    assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        registry.start('2' * 32)
    assert error.value.status_code == 503
    registry.finish(TOKEN, True)
    registry.start('2' * 32)  # Evict the oldest terminal record at capacity.
    with pytest.raises(HTTPException):
        registry.snapshot(TOKEN)
    registry.finish('2' * 32, False)
    clock[0] = 901
    with pytest.raises(HTTPException):
        registry.snapshot('2' * 32)
    registry.start(TOKEN)
    clock[0] += 7201
    with pytest.raises(HTTPException):
        registry.snapshot(TOKEN)


def test_pipeline_progress_matches_actual_passage_count_and_ignores_observer_errors(tmp_path):
    events = []
    result = review_document(ROOT / 'tests/fixtures/andrea_raw.docx', tmp_path / 'observed',
        backend='rules', feedback_rewriter=lambda text: text, progress=events.append)
    audit = result.generation['humanization']
    passage_events = [event for event in events if event['stage'] == 'humanizing']
    counts = [event['completed_passages'] for event in passage_events]
    assert counts == sorted(counts)
    assert counts[-1] == audit['attempted']
    assert all(event['total_passages'] == audit['attempted'] for event in passage_events)
    assert events[0]['stage'] == 'reviewing' and events[-1]['stage'] == 'document_ready'
    def broken_observer(event):
        raise RuntimeError('observer failed')
    result = review_document(ROOT / 'tests/fixtures/andrea_raw.docx', tmp_path / 'unobserved',
                             backend='rules', progress=broken_observer)
    assert result.validation.ok


@pytest.mark.parametrize('blocking_stage', ['reviewing', 'document_ready'])
def test_progress_endpoint_responds_during_blocking_work_and_records_terminal_state(monkeypatch, blocking_stage):
    from portal import server
    registry = ReviewProgressRegistry()
    monkeypatch.setattr(server, 'review_progress', registry)
    entered, release = Event(), Event()
    def work(*args):
        progress = args[-1]
        progress({'stage': 'reviewing'})
        if blocking_stage == 'document_ready':
            progress({'stage': 'feedback_ready', 'total_passages': 0, 'completed_passages': 0})
            progress({'stage': 'document_ready'})
        entered.set()
        assert release.wait(5)
        return {'job_id': 'test-job'}
    monkeypatch.setattr(server, '_execute_thinkingstorm_pipeline', work)
    with TestClient(server.app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.post, '/api/thinkingstorm/execute', data={'progress_id': TOKEN})
        try:
            assert entered.wait(3)
            start = time.monotonic()
            response = client.get('/api/thinkingstorm/progress/' + TOKEN)
            assert response.status_code == 200 and time.monotonic() - start < 1
            assert response.headers['cache-control'] == 'no-store'
            assert response.json()['stage'] == blocking_stage
            assert response.json()['percent'] != 100
        finally:
            release.set()
        assert future.result(timeout=3).status_code == 200
        assert client.get('/api/thinkingstorm/progress/' + TOKEN).json()['percent'] == 100


def test_route_failure_and_missing_tracking(monkeypatch):
    from portal import server
    registry = ReviewProgressRegistry()
    monkeypatch.setattr(server, 'review_progress', registry)
    def fail(*args):
        raise HTTPException(422, 'Expected test refusal')
    monkeypatch.setattr(server, '_execute_thinkingstorm_pipeline', fail)
    with TestClient(server.app) as client:
        assert client.get('/api/thinkingstorm/progress/' + TOKEN).status_code == 404
        assert client.post('/api/thinkingstorm/execute', data={'progress_id': TOKEN}).status_code == 422
        assert client.get('/api/thinkingstorm/progress/' + TOKEN).json()['status'] == 'failed'
        assert client.post('/api/thinkingstorm/execute').status_code == 422


def test_client_poll_timeout_recovery_and_stale_response_cleanup():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is not installed')
    path = ROOT / 'portal/static/review-progress.js'
    script = r'''
const assert = require('node:assert/strict');
require(process.argv[1]);
(async () => {
  let calls = 0, failures = 0, poll;
  await new Promise((resolve, reject) => {
    const deadline = setTimeout(() => reject(new Error('poll did not recover')), 1000);
    poll = ReviewProgress.start({id:'a', intervalMs:2, timeoutMs:10,
      fetch: async (_url, {signal}) => {
        calls++;
        if (calls === 1) return new Promise((_, fail) => signal.addEventListener('abort', () => fail(new Error('timeout'))));
        return {ok:true, status:200, json:async () => ({status:'complete', percent:100})};
      }, onUnavailable:() => failures++, onUpdate:data => {assert.equal(data.percent,100); clearTimeout(deadline); resolve();}});
  });
  poll.stop();
  await new Promise(resolve => setTimeout(resolve, 30));
  assert.equal(calls, 2); assert.equal(failures, 1);
  let deliver, updates = 0;
  const stale = ReviewProgress.start({id:'b', timeoutMs:100,
    fetch:() => new Promise(resolve => deliver=resolve), onUpdate:() => updates++, onUnavailable:() => {}});
  stale.stop();
  deliver({ok:true,status:200,json:async () => ({status:'running',percent:50})});
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(updates,0);
})().catch(error => {console.error(error); process.exitCode=1;});
'''
    result = subprocess.run([node, '-e', script, str(path)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
