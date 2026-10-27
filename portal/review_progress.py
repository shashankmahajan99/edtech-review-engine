"""Bounded, thread-safe progress for this single-process local portal."""
from collections import OrderedDict
import math
import re
from threading import Lock
import time

from fastapi import HTTPException

MESSAGES = {'reading': 'Reading your manuscript', 'reviewing': 'Preparing comments and closing note',
            'feedback_ready': 'Preparing feedback editing', 'humanizing': 'Checking feedback passages',
            'retry': 'Retrying a feedback passage', 'document': 'Preparing your Word document',
            'document_ready': 'Preparing your downloads', 'complete': 'Your review files are ready',
            'failed': 'Review stopped. See the error message for details.'}


class ReviewProgressRegistry:
    def __init__(self, clock=time.monotonic, capacity=256):
        self.clock, self.capacity = clock, capacity
        self.lock = Lock()
        self.jobs = OrderedDict()

    def _prune(self, now):
        expired = [key for key, row in self.jobs.items()
                   if now - row['updated'] > (7200 if row['status'] == 'running' else 900)]
        for key in expired:
            del self.jobs[key]

    def start(self, token):
        if token is None:
            return None
        if not re.fullmatch(r'[0-9a-f]{32}', token):
            raise HTTPException(400, 'Invalid progress identifier.')
        now = self.clock()
        with self.lock:
            self._prune(now)
            if token in self.jobs:
                raise HTTPException(409, 'This progress identifier is already in use.')
            if len(self.jobs) >= self.capacity:
                terminal = next((key for key, row in self.jobs.items() if row['status'] != 'running'), None)
                if terminal is None:
                    raise HTTPException(503, 'Too many reviews are active. Try again shortly.')
                del self.jobs[terminal]
            self.jobs[token] = dict(status='running', stage='reading', started=now, updated=now,
                                    completed_units=0, total_units=None, completed_passages=0,
                                    total_passages=None, editing_eta_seconds=None)
        return lambda event: self.update(token, event)

    def update(self, token, event):
        now = self.clock()
        stage = event.get('stage')
        if stage not in MESSAGES:
            return
        with self.lock:
            row = self.jobs.get(token)
            if not row or row['status'] != 'running':
                return
            row.update(stage=stage, updated=now, editing_eta_seconds=None)
            if stage == 'reviewing':
                row['completed_units'] = max(1, row['completed_units'])
            if stage in {'feedback_ready', 'humanizing', 'retry'}:
                total = event.get('total_passages')
                done = event.get('completed_passages', 0)
                if type(total) is int and total >= 0 and type(done) is int and 0 <= done <= total:
                    if row['total_passages'] is None:
                        row.update(total_passages=total, total_units=total + 4)
                    if total == row['total_passages']:
                        row['completed_passages'] = max(row['completed_passages'], done)
                        row['completed_units'] = max(row['completed_units'], 2 + row['completed_passages'])
                        eta = event.get('editing_eta_seconds')
                        if stage == 'humanizing' and done < total and type(eta) in {int, float} and math.isfinite(eta) and eta >= 0:
                            row['editing_eta_seconds'] = math.ceil(eta)
            if stage == 'document_ready':
                row['completed_units'] = max(row['completed_units'], (row['total_passages'] or 0) + 3)

    def finish(self, token, success):
        if token is None:
            return
        with self.lock:
            row = self.jobs.get(token)
            if not row or row['status'] != 'running':
                return
            row.update(status='complete' if success else 'failed', stage='complete' if success else 'failed',
                       updated=self.clock(), editing_eta_seconds=None)
            if success:
                row['total_units'] = row['total_units'] or 4
                row['completed_units'] = row['total_units']

    def snapshot(self, token):
        now = self.clock()
        with self.lock:
            self._prune(now)
            row = self.jobs.get(token)
            if row is None:
                raise HTTPException(404, 'Progress is not available.')
            total, done = row['total_units'], row['completed_units']
            percent = min(100 if row['status'] == 'complete' else 99, math.floor(100 * done / total)) if total else None
            passages = row['total_passages']
            return {key: row[key] for key in ['status', 'stage', 'completed_units', 'total_units',
                    'completed_passages', 'total_passages', 'editing_eta_seconds']} | {
                    'message': MESSAGES[row['stage']], 'percent': percent,
                    'remaining_passages': max(0, passages - row['completed_passages']) if passages is not None else None,
                    'elapsed_seconds': max(0, round(now - row['started']))}


review_progress = ReviewProgressRegistry()
