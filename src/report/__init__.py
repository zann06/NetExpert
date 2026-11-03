"""Professional report generation (UI-independent).

The package turns the current inference trace plus optional user metadata into
a print-ready, black & white report.  It has no Streamlit imports so the
renderers can be unit-tested in isolation.
"""

from .models import ReportMeta, TeamMember
from .render import build_cover, build_sections, render_html, render_markdown

__all__ = [
    "ReportMeta",
    "TeamMember",
    "build_cover",
    "build_sections",
    "render_html",
    "render_markdown",
]
