"""
Production runner for Autonomous Poller Daemon with guaranteed sys.path and UTF-8 encoding.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.environ["PYTHONPATH"] = str(BASE_DIR)
os.environ["PYTHONIOENCODING"] = "utf-8"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from orchestrator.poller_daemon import run_poller_daemon

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_poller_daemon(interval)
