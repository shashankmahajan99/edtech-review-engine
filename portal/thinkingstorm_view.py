"""ThinkingStorm Studio, using the shared workspace design foundation."""
from pathlib import Path

from portal.ui import workspace_page

STUDIO_TEMPLATE = Path(__file__).resolve().parent / "static" / "studio.html"


def get_thinkingstorm_studio_html(user=None) -> str:
    return workspace_page(
        "ThinkingStorm Studio", STUDIO_TEMPLATE.read_text(encoding="utf-8"),
        user=user, active="studio", scripts=("review-progress.js", "clever-widget.js", "feedback-editor.js", "studio.js"),
    )
