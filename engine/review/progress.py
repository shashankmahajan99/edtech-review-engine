"""Optional, offline progress notifications; observation must not break a review."""


def emit_progress(callback, stage, **fields):
    if callback is not None:
        try:
            callback({'stage': stage, **fields})
        except Exception:
            # A UI observer is not part of document correctness or generation.
            pass
