"""Explicit deployment defaults for launchers; direct pipeline calls stay offline."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply_runtime_defaults():
    path = Path(os.environ.get('TS_RUNTIME_PROFILE', ROOT / 'output/review-runtime.json'))
    if path.is_file():
        try:
            cfg = json.loads(path.read_text(encoding='utf-8-sig'))
            if set(cfg) - {'backend', 'humanizer', 'humanizer_config'} or cfg['backend'] not in {'rules', 'local'} or cfg['humanizer'] not in {'off', 'local'}:
                raise ValueError('invalid profile values')
            if cfg['humanizer'] == 'local' and not Path(cfg['humanizer_config']).is_absolute():
                raise ValueError('humanizer_config must be an absolute path')
            os.environ.setdefault('TS_REVIEW_BACKEND', cfg['backend'])
            os.environ.setdefault('TS_HUMANIZER', cfg['humanizer'])
            if cfg.get('humanizer_config'):
                os.environ.setdefault('TS_HUMANIZER_CONFIG', cfg['humanizer_config'])
        except (ValueError, TypeError, KeyError) as exc:
            raise RuntimeError('Invalid review runtime profile: ' + str(exc)) from exc
    elif 'TS_RUNTIME_PROFILE' in os.environ:
        raise RuntimeError('Configured review runtime profile does not exist.')
    elif (ROOT / 'output/local-model/config.json').is_file():
        os.environ.setdefault('TS_REVIEW_BACKEND', 'local')
