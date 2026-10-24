from __future__ import annotations

"""ThinkingStorm deterministic review pipeline.

Public surface: :func:`review_document` plus the CLI/watcher entry points.
Everything in this package is offline and model-free so a submission can be
processed for zero tokens on any machine that has Python and python-docx.
"""

__version__ = "2.0.0"
