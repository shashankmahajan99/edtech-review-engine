"""
Production launcher for the Apex Academic Review Portal & Workbench.
Uses direct uvicorn.run() to ensure clean detached host execution.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ["PYTHONPATH"] = str(BASE_DIR)
os.environ["PYTHONIOENCODING"] = "utf-8"
from engine.review_runtime import apply_runtime_defaults
apply_runtime_defaults()

import uvicorn

if __name__ == "__main__":
    print("Starting Apex FastAPI Server via direct uvicorn on http://127.0.0.1:8000 ...", flush=True)
    uvicorn.run(
        "portal.server:app",
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
