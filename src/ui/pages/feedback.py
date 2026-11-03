"""Feedback page: check a student's forward-chaining answer against the engine.

The student pastes an answer (for example copied from an AI chat) or fills the
structured form.  The comparison is fully deterministic: the app re-runs
forward chaining on the current knowledge base and compares conflict set,
selected rule and conclusion for every iteration, citing the exact
conflict-resolution criterion for each mistake.
"""

from __future__ import annotations

import streamlit as st

from ...feedback import check_answer, parse_answer
from ...models import ForwardResult
from .. import components as c
from ..state import get_initial_facts, get_rules

_SAMPLE_ANSWER = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| --- | --- | --- | --- |
| 1 | R5, R1 | R5 | Gangguan Provider |
| 2 | R4, R1, R7 | R4 | Lapor ke Provider |
| 3 | R1, R7 | R1 | Cek Router |
| 4 | R7 | R7 | Gunakan Tethering Sementara |
| 5 | — | STOP | — |"""


def render() -> None:
    c.page_head(
        "Feedback Jawaban",
        "Tempel jawaban tugas (mis. hasil diskusi dengan AI) dan netExpert akan "
        "memeriksa setiap iterasi terhadap jejak engine — deterministik, tanpa AI.",
    )

    forward: ForwardResult = st.session_state.get("forward_result")
    if forward is None:
        c.banner(
            "blue",
            "Belum ada hasil inferensi",
            "Pemeriksaan memakai dataset saat ini. Jalankan diagnosis terlebih "
            "dahulu bila Anda memakai fakta atau aturan kustom.",
        )

    tab_paste, tab_form = st.tabs(["Tempel Jawaban", "Form Terstruktur"])

    with tab_paste:
        _render_paste_tab()
    with tab_form:
        _render_form_tab()

    error = st.session_state.get("feedback_error")
    if error:
        st.error(error)

    report = st.session_state.get("feedback_report")
    if report is not None:
        _render_report(report)


# ---------------------------------------------------------------------------
# Input tabs
# ---------------------------------------------------------------------------
def _fill_sample_answer() -> None:
    """Callback: runs before the next rerun, so the text_area key is safe to set."""
    st.session_state.feedback_answer_text = _SAMPLE_ANSWER


def _add_form_row() -> None:
    """Callback: append one structured-form row (max 12)."""
    current = st.session_state.get("feedback_form_rows", 5)
    if current < 12:
        st.session_state.feedback_form_rows = current + 1


def _render_paste_tab() -> None:
    st.text_area(
        "Jawaban soal (a) — forward chaining",
        key="feedback_answer_text",
        height=260,
        placeholder=_SAMPLE_ANSWER,
        help=(
            "Format bebas: tabel markdown, baris 'Iterasi 1: ...', atau daftar "
            "bernomor. Pemeriksaan membandingkan conflict set, aturan terpilih, "
            "dan kesimpulan per iterasi."
        ),
    )
    columns = st.columns([1, 1, 3])
    with columns[0]:
        if st.button(
            "Periksa jawaban",
            type="primary",
            width="stretch",
            disabled=not st.session_state.get("feedback_answer_text"),
        ):
            _run_check(text=st.session_state.feedback_answer_text)
    with columns[1]:
        st.button(
            "Isi contoh jawaban",
            width="stretch",
            on_click=_fill_sample_answer,
        )


def _render_form_tab() -> None:
    st.markdown(
        '<div class="nx-card-sub" style="margin-bottom:0.4rem">'
        "Isi tabel berikut; kolom kosong dianggap tidak dituliskan.</div>",
        unsafe_allow_html=True,
    )

    engine_rows = 5
    if "feedback_form_rows" not in st.session_state:
        st.session_state.feedback_form_rows = engine_rows

    header = st.columns([0.6, 2.2, 1.2, 2.2])
    for col, label in zip(header, ("Iterasi", "Conflict Set", "Terpilih", "Kesimpulan")):
        col.markdown(f"**{label}**")

    rows = st.session_state.feedback_form_rows
    values = {}
    for i in range(rows):
        row = st.columns([0.6, 2.2, 1.2, 2.2])
        with row[0]:
            values[i] = {
                "iteration": st.number_input(
                    "Iter",
                    min_value=0,
                    value=i + 1,
                    key=f"fb_iter_{i}",
                    label_visibility="collapsed",
                ),
            }
        with row[1]:
            values[i]["conflict"] = st.text_input(
                "CS", key=f"fb_cs_{i}", placeholder="R5, R1",
                label_visibility="collapsed",
            )
        with row[2]:
            values[i]["selected"] = st.text_input(
                "Sel", key=f"fb_sel_{i}", placeholder="R5",
                label_visibility="collapsed",
            )
        with row[3]:
            values[i]["conclusion"] = st.text_input(
                "Kon", key=f"fb_con_{i}", placeholder="Gangguan Provider",
                label_visibility="collapsed",
            )

    below = st.columns([1, 3])
    with below[0]:
        st.button(
            "+ Baris",
            width="stretch",
            disabled=rows >= 12,
            on_click=_add_form_row,
        )

    if st.button("Periksa form", type="primary"):
        lines = []
        for i in range(rows):
            v = values[i]
            conflict = v["conflict"].strip()
            selected = v["selected"].strip()
            conclusion = v["conclusion"].strip()
            if not (conflict or selected or conclusion):
                continue
            parts = [f"Iterasi {int(v['iteration'])}:"]
            if conflict:
                parts.append(f"conflict set {conflict}")
            if selected:
                parts.append(f"dipilih {selected}")
            if conclusion:
                parts.append(f"kesimpulan {conclusion}")
            lines.append(" ".join(parts))
        if lines:
            _run_check(text="\n".join(lines))
        else:
            st.warning("Isi minimal satu baris terlebih dahulu.")


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------
def _run_check(text: str) -> None:
    parsed, unrecognized = parse_answer(text)
    st.session_state.feedback_parsed_count = len(parsed)
    st.session_state.feedback_unrecognized = unrecognized
    if not len(parsed):
        st.session_state.feedback_report = None
        st.session_state.feedback_error = (
            "Tidak ada iterasi yang bisa dibaca dari jawaban. Gunakan format "
            "seperti pada contoh."
        )
        return
    st.session_state.feedback_error = None
    st.session_state.feedback_report = check_answer(
        parsed, get_rules(), get_initial_facts()
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------
def _render_report(report) -> None:
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    if report.all_correct:
        c.banner(
            "green",
            f"Semua langkah benar — skor {report.score_percent}%",
            f"{report.correct}/{report.total} pemeriksaan cocok dengan jejak engine.",
        )
    else:
        tone = "amber" if report.score_percent >= 60 else "red"
        c.banner(
            tone,
            f"Skor {report.score_percent}% ({report.correct}/{report.total} pemeriksaan cocok)",
            "Perhatikan catatan per iterasi di bawah. Urutan pertimbangan: "
            "salience → spesifisitas → nomor aturan; refraction berlaku sepanjang proses.",
        )

    unrecognized = st.session_state.get("feedback_unrecognized") or []
    if unrecognized:
        with st.expander(
            f"Bagian yang tidak bisa dibaca ({len(unrecognized)})", expanded=False
        ):
            for fragment in unrecognized:
                st.markdown(f"- {c.esc(fragment)}")

    # Summary table: claim vs engine per field.
    rows = []
    for entry in report.per_iteration:
        for check in entry["checks"]:
            rows.append(
                {
                    "Iterasi": entry["iteration"],
                    "Aspek": _FIELD_LABELS.get(check.field, check.field),
                    "Jawaban": check.claim,
                    "Engine": check.expected,
                    "Status": "✓ Benar" if check.ok else "✗ Keliru",
                }
            )
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)

    if report.issues:
        c.section_title(
            "Penjelasan langkah yang keliru",
            "Setiap catatan mengutip kriteria conflict resolution yang menentukan.",
        )
        for issue in report.issues:
            tone = "amber" if issue.severity == "warning" else "red"
            title = f"Iterasi {issue.iteration} — {_FIELD_LABELS.get(issue.field, issue.field)}"
            with st.container():
                st.markdown(
                    f'<div class="nx-card" style="border-left:3px solid '
                    f'{"#D97706" if tone == "amber" else "#DC2626"};padding:0.8rem 1rem">'
                    f'<div class="nx-card-title" style="font-size:0.9rem">{c.esc(title)}</div>'
                    f'<div class="nx-kv" style="margin:0.25rem 0"><b>Jawaban:</b> '
                    f"{c.esc(issue.claim)}</div>"
                    f'<div class="nx-kv" style="margin:0.25rem 0"><b>Seharusnya:</b> '
                    f"{c.esc(issue.expected)}</div>"
                    f'<div class="nx-eval-reason">{c.esc(issue.explanation)}</div>'
                    "</div>",
                    unsafe_allow_html=True,
                )


_FIELD_LABELS = {
    "conflict_set": "Conflict set",
    "selected_rule": "Aturan terpilih",
    "conclusion": "Kesimpulan",
    "missing": "Iterasi hilang",
    "extra": "Iterasi berlebih",
    "stop": "Stop",
}
