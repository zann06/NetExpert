"""NetExpert — Internet Troubleshooting Expert System.

Streamlit entry point.  Run with::

    streamlit run app.py

All inference logic lives in :mod:`src.inference` and is independent of
Streamlit; this file only wires state, navigation and pages together.
"""

from __future__ import annotations

import streamlit as st

from src.ui import components as c
from src.ui.pages import diagnosis, guide, knowledge_base, overview, report, tree
from src.ui.state import PAGES, init_state, navigate, reset_application
from src.ui.styles import inject_styles

st.set_page_config(
    page_title="NetExpert — Internet Troubleshooting Expert System",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
init_state()

RENDERERS = {
    "Overview": overview.render,
    "Diagnosis": diagnosis.render,
    "Knowledge Base": knowledge_base.render,
    "Inference Tree": tree.render,
    "Laporan": report.render,
    "Guide": guide.render,
}


with st.sidebar:
    c.brand()
    st.markdown('<div class="nx-side-label">Workspace</div>', unsafe_allow_html=True)
    st.radio(
        "Navigasi",
        PAGES,
        key="nav",
        label_visibility="collapsed",
    )
    st.markdown('<div class="nx-side-label" style="margin-top:1rem">Aksi</div>', unsafe_allow_html=True)
    with st.popover("Reset ke dataset tugas", width="stretch"):
        st.write(
            "Kembalikan 8 aturan dan 3 fakta awal ke dataset assignment, "
            "serta hapus semua hasil inferensi."
        )
        confirmed = st.checkbox("Saya yakin ingin mereset", key="confirm_reset_app")
        st.button(
            "Reset sekarang",
            type="primary",
            disabled=not confirmed,
            on_click=reset_application,
            width="stretch",
        )
    c.sidebar_footer()

page = st.session_state.get("nav", "Overview")

# Top bar: breadcrumb + reset shortcut.
left, right = st.columns([6, 1], vertical_alignment="center")
with left:
    st.markdown(
        f'<div class="nx-muted" style="font-size:0.71rem;letter-spacing:0.09em;'
        f'text-transform:uppercase;padding-top:0.35rem">'
        f"NetExpert&nbsp;&nbsp;/&nbsp;&nbsp;{c.esc(page)}</div>",
        unsafe_allow_html=True,
    )
with right:
    if page != "Overview":
        st.button(
            "Overview",
            on_click=navigate,
            args=("Overview",),
            width="stretch",
        )

flash = st.session_state.get("flash")
if flash:
    st.success(flash)
    st.session_state.flash = None

RENDERERS.get(page, overview.render)()