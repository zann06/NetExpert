"""Report page: compose a print-ready, black & white report from the trace.

All identity fields are optional.  The preview is rendered in an isolated
iframe so the report keeps its own monochrome document styles instead of
inheriting the application theme.
"""

from __future__ import annotations

import base64
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from ...report import ReportMeta, TeamMember, render_html, render_markdown
from .. import components as c
from ..state import get_initial_facts, get_rules

_MONTHS = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]


def _today_id() -> str:
    today = date.today()
    return f"{today.day} {_MONTHS[today.month - 1]} {today.year}"


def _init_defaults() -> None:
    ss = st.session_state
    ss.setdefault("report_title", "Laporan Hasil Diagnosis Gangguan Internet")
    ss.setdefault("report_date", _today_id())


def _parse_members(text: str) -> list[TeamMember]:
    """Parse ``Nama | NIM | Peran`` lines into team members."""
    members: list[TeamMember] = []
    for line in str(text).splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        while len(parts) < 3:
            parts.append("")
        members.append(TeamMember(name=parts[0], nim=parts[1], role=parts[2]))
    return members


def _logo_data_url(uploaded) -> str:
    if not uploaded:
        return ""
    try:
        raw = uploaded.getvalue()
    except Exception:  # pragma: no cover - defensive for file-like objects
        raw = uploaded.read()
    mime = getattr(uploaded, "type", "") or "image/png"
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _render_identity_form() -> ReportMeta:
    ss = st.session_state
    c.section_title(
        "Identitas laporan",
        "Semua kolom opsional — isi yang perlu saja. Bagian kosong otomatis disembunyikan.",
    )

    with st.expander("Identitas & kelompok", expanded=True):
        st.text_input("Judul laporan", key="report_title")
        st.text_input(
            "Judul tugas / topik",
            key="report_assignment",
            placeholder="Contoh: Sistem Pakar Diagnosis Gangguan Internet",
        )
        st.text_input(
            "Mata kuliah",
            key="report_course",
            placeholder="Contoh: Sistem Pakar",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input(
                "Nama kelompok",
                key="report_group_name",
                placeholder="Contoh: Kelompok 4",
            )
        with col_b:
            st.text_input(
                "Nomor / kode kelompok",
                key="report_group_number",
                placeholder="Contoh: 04",
            )
        st.text_area(
            "Anggota kelompok",
            key="report_members",
            height=118,
            placeholder=(
                "Satu anggota per baris, format: Nama | NIM | Peran\n"
                "Budi Santoso | 21.11.0001 | Ketua\n"
                "Ani Lestari | 21.11.0002 | Anggota"
            ),
            help="Pemisah antar kolom adalah tanda pipa (|). NIM dan peran boleh dikosongkan.",
        )
        col_c, col_d = st.columns(2)
        with col_c:
            st.text_input(
                "Dosen pengampu",
                key="report_lecturer",
                placeholder="Contoh: Dr. Nama Dosen, M.Kom.",
            )
        with col_d:
            st.text_input(
                "Asisten / pembimbing",
                key="report_assistant",
                placeholder="Opsional",
            )
        col_e, col_f = st.columns(2)
        with col_e:
            st.text_input("Program studi", key="report_program_study")
        with col_f:
            st.text_input("Jurusan / departemen", key="report_department")
        st.text_input("Fakultas", key="report_faculty")
        st.text_input(
            "Institusi / universitas",
            key="report_institution",
            placeholder="Contoh: Universitas Contoh",
        )
        col_g, col_h = st.columns(2)
        with col_g:
            st.text_input("Kota", key="report_city")
        with col_h:
            st.text_input("Tanggal", key="report_date")
        st.file_uploader(
            "Logo institusi (opsional)",
            type=["png", "jpg", "jpeg"],
            key="report_logo",
            help="Logo akan ditempatkan di bagian atas halaman sampul.",
        )

    with st.expander("Narasi tambahan (opsional)", expanded=False):
        st.text_area(
            "Ringkasan eksekutif",
            key="report_summary",
            height=100,
            placeholder="Kosongkan untuk ringkasan otomatis dari hasil inferensi.",
        )
        st.text_area(
            "Latar belakang / pendahuluan",
            key="report_background",
            height=110,
            placeholder="Kosongkan untuk paragraf pendahuluan standar.",
        )
        st.text_area(
            "Kesimpulan / rekomendasi tambahan",
            key="report_conclusion",
            height=100,
            placeholder="Kosongkan untuk kesimpulan otomatis dari aturan yang fired.",
        )

    uploaded = ss.get("report_logo")
    return ReportMeta(
        title=ss.get("report_title", ""),
        assignment=ss.get("report_assignment", ""),
        course=ss.get("report_course", ""),
        group_name=ss.get("report_group_name", ""),
        group_number=ss.get("report_group_number", ""),
        members=_parse_members(ss.get("report_members", "")),
        lecturer=ss.get("report_lecturer", ""),
        assistant=ss.get("report_assistant", ""),
        program_study=ss.get("report_program_study", ""),
        department=ss.get("report_department", ""),
        faculty=ss.get("report_faculty", ""),
        institution=ss.get("report_institution", ""),
        city=ss.get("report_city", ""),
        date=ss.get("report_date", ""),
        logo_data_url=_logo_data_url(uploaded),
        summary=ss.get("report_summary", ""),
        background=ss.get("report_background", ""),
        conclusion=ss.get("report_conclusion", ""),
    )


def _render_preview(meta: ReportMeta, forward, backward) -> None:
    rules = get_rules()
    facts = get_initial_facts()
    generated = _today_id()

    html_doc = render_html(
        meta,
        forward=forward,
        backward=backward,
        rules=rules,
        initial_facts=facts,
        generated_at=generated,
    )
    md_doc = render_markdown(
        meta,
        forward=forward,
        backward=backward,
        rules=rules,
        initial_facts=facts,
        generated_at=generated,
    )

    st.markdown(
        '<div class="nx-card-title" style="margin-top:0.2rem">Pratinjau laporan</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Layout dokumen A4 hitam-putih. Unduh HTML lalu buka di browser untuk "
        "mencetak atau menyimpan sebagai PDF."
    )
    if hasattr(st, "iframe"):
        st.iframe(html_doc, height=780)
    else:  # pragma: no cover - compatibility with Streamlit < 1.65
        components.html(html_doc, height=780, scrolling=True)

    col_html, col_md = st.columns(2)
    with col_html:
        st.download_button(
            "Unduh laporan (.html)",
            data=html_doc,
            file_name="laporan_netexpert.html",
            mime="text/html",
            width="stretch",
            key="download_report_html",
        )
    with col_md:
        st.download_button(
            "Unduh laporan (.md)",
            data=md_doc,
            file_name="laporan_netexpert.md",
            mime="text/markdown",
            width="stretch",
            key="download_report_md",
        )
    st.caption(
        "Tips cetak: buka file HTML di browser → **Ctrl/Cmd + P** → "
        "**Save as PDF** → aktifkan **Background graphics** agar garis tabel ikut tercetak."
    )


def render() -> None:
    c.page_head(
        "Laporan",
        "Susun laporan profesional hitam-putih dari hasil diagnosis. Identitas "
        "kelompok, anggota, NIM, dan narasi bersifat opsional.",
    )

    forward = st.session_state.forward_result
    backward = st.session_state.backward_result
    if not forward and not backward:
        c.banner(
            "amber",
            "Belum ada hasil inferensi",
            "Laporan tetap dapat dibuat, tetapi bagian hasil akan kosong sampai "
            "kamu menjalankan forward atau backward chaining di halaman Diagnosis.",
        )

    _init_defaults()

    form_col, preview_col = st.columns([0.85, 1.15], gap="large")
    with form_col:
        meta = _render_identity_form()
    with preview_col:
        _render_preview(meta, forward, backward)
