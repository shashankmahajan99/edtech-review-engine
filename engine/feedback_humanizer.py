"""Dedicated local raw-completion transport, separate from offline review logic."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.request import Request, build_opener, ProxyHandler

from engine.review.humanization import TruncatedRewrite

ROOT = Path(__file__).resolve().parents[1]
PROMPT_FINGERPRINT = 'cc51d66b4c593fbe'


class HumanizerUnavailable(RuntimeError):
    pass


class LocalHumanizer:
    def __init__(self, path=None):
        path = Path(path or os.environ.get('TS_HUMANIZER_CONFIG', ROOT / 'output/humanizer/config.json'))
        try:
            cfg = json.loads(path.read_text(encoding='utf-8-sig'))
            allowed = {'base_url', 'model', 'model_name', 'prompt_path', 'budget_seconds', 'call_timeout_seconds', 'provider'}
            if set(cfg) - allowed or not {'base_url', 'model', 'prompt_path'} <= set(cfg):
                raise ValueError('invalid configuration keys')
            parsed = urlparse(cfg['base_url'])
            if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'} or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'', '/'}:
                raise ValueError('humanizer requires a loopback HTTP origin')
            self.model = cfg['model']
            self.model_name = cfg.get('model_name', self.model)
            if not isinstance(self.model_name, str) or not self.model_name:
                raise ValueError('invalid model display name')
            self.provider = cfg.get('provider', 'completion')
            if self.provider not in {'completion', 'instruct'} or self.model != ('thinkingstorm-editor' if self.provider == 'instruct' else 'thinkingstorm-humanizer'):
                raise ValueError('expected the dedicated model alias for this provider')
            self.budget = cfg.get('budget_seconds', 180)
            self.call_timeout = cfg.get('call_timeout_seconds', 30)
            if type(self.budget) not in {int, float} or not 1 <= self.budget <= 180 or type(self.call_timeout) not in {int, float} or not 1 <= self.call_timeout <= 30:
                raise ValueError('invalid timeout budget')
            if not Path(cfg['prompt_path']).is_absolute():
                raise ValueError('prompt_path must be absolute')
            prompt_text = Path(cfg['prompt_path']).read_text(encoding='utf8')
            if self.provider == 'completion':
                fmt = json.loads(prompt_text)
                self.instruction, self.separator = fmt['instr'], fmt['sep']
                if hashlib.sha256(self.prompt('X').encode()).hexdigest()[:16] != PROMPT_FINGERPRINT:
                    raise ValueError('the pinned humanizer prompt fingerprint does not match')
            else:
                self.instruction, self.separator = prompt_text.strip(), ''
                if not self.instruction:
                    raise ValueError('empty editorial prompt')
            self.base_url = cfg['base_url'].rstrip('/')
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise HumanizerUnavailable('Invalid local humanizer configuration: ' + str(exc)) from exc
        self.deadline = None
        self._active = False

    def prompt(self, text):
        return self.instruction + '\n\n' + text.strip() + self.separator

    def _request(self, path, payload=None):
        remaining = (self.deadline - time.monotonic()) if self.deadline else self.call_timeout
        if remaining <= 0:
            raise HumanizerUnavailable('Humanizer exceeded its review time budget; no deliverable was released.')
        req = Request(self.base_url + path, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Content-Type': 'application/json'})
        try:
            with build_opener(ProxyHandler({})).open(req, timeout=min(self.call_timeout, remaining)) as response:
                return json.load(response)
        except Exception as exc:
            raise HumanizerUnavailable('Local humanizer request failed; check that the dedicated runtime is ready (' + type(exc).__name__ + ').') from exc

    @contextmanager
    def session(self):
        self.deadline = time.monotonic() + self.budget
        lock_dir = ROOT / 'output/humanizer'
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock = (lock_dir / 'review.lock').open('a+b')
        locked = False
        try:
            if lock.seek(0, 2) == 0:
                lock.write(b'0'); lock.flush()
            lock.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError as exc:
                raise HumanizerUnavailable('The humanizer is busy with another review. Try again after it finishes.') from exc
            models = self._request('/v1/models')
            if not isinstance(models, dict) or self.model not in {m.get('id') for m in models.get('data', []) if isinstance(m, dict)}:
                raise HumanizerUnavailable('The local endpoint is serving a different model.')
            slots = self._request('/slots')
            if not isinstance(slots, list) or not slots or any(not isinstance(slot, dict) or slot.get('is_processing', True) for slot in slots):
                raise HumanizerUnavailable('The humanizer slot is still busy. Try again after it finishes.')
            self._active = True
            yield self
        finally:
            self._active = False
            if locked:
                lock.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()

    def __call__(self, text, retry=False):
        if not self._active:
            with self.session():
                return self(text, retry=retry)
        if len(text.encode()) > 6000:
            raise HumanizerUnavailable('Feedback passage is too long for the short-context humanizer.')
        limit = min(2048, max(256, math.ceil(4 * len(text.split()))))
        if self.provider == 'instruct':
            result = self._request('/v1/chat/completions', {'model': self.model,
                'messages': [{'role': 'system', 'content': self.instruction}, {'role': 'user', 'content': text}],
                'temperature': .35 if retry else .72, 'top_p': .90 if retry else .92,
                'max_tokens': limit, 'stream': False,
                'chat_template_kwargs': {'enable_thinking': False}})
            choices = result.get('choices') if isinstance(result, dict) else None
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                raise HumanizerUnavailable('Humanizer returned an invalid completion response.')
            choice = choices[0]
            if choice.get('finish_reason') == 'length':
                raise TruncatedRewrite('Humanizer rewrite was truncated at its output limit.')
            message = choice.get('message')
            content = message.get('content') if isinstance(message, dict) else None
        else:
            result = self._request('/completion', {'prompt': self.prompt(text), 'temperature': 1.0,
                'top_p': .95, 'top_k': 0, 'min_p': 0, 'repeat_penalty': 1.0, 'n_predict': limit,
                'stream': False, 'cache_prompt': True})
            if not isinstance(result, dict):
                raise HumanizerUnavailable('Humanizer returned an invalid completion response.')
            content = result.get('content')
        if result.get('truncated') or result.get('stopped_limit') or result.get('stop_type') == 'limit':
            raise TruncatedRewrite('Humanizer rewrite was truncated at its output limit.')
        if not isinstance(content, str) or not content.strip():
            raise HumanizerUnavailable('Humanizer returned no prose.')
        return content.strip()


def configured_rewriter():
    mode = os.environ.get('TS_HUMANIZER', 'off')
    if mode == 'off':
        return None
    if mode != 'local':
        raise HumanizerUnavailable('TS_HUMANIZER must be off or local.')
    return LocalHumanizer()
