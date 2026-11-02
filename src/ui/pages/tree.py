"""Inference tree viewer: dynamic Graphviz tree, legend, filters and fallback."""

from __future__ import annotations

import streamlit as st

from ...visualization import (
    FILTER_ALL,
    FILTER_FAILED,
    FILTER_FIRED,
    FILTER_LABELS,
    FILTER_READY_NOT_SELECTED,
    backward_condition_rows,
    backward_tree_dot,
    forward_condition_rows,
    forward_tree_dot,
)
from .. import components as c
from ..state import get_rules, navigate


def render() -> None:
    c.page_head(
        "Inference Tree",
        "Pohon dibangun langsung dari trace eksekusi — bukan ilustrasi statis. "
        "Setiap kondisi menampilkan TRUE atau FALSE.",
    )

    forward = st.session_state.forward_result
    backward = st.session_state.backward_result

    if not forward and not backward:
        c.empty_state(
            "Belum ada inference tree",
            "Jalankan forward chaining atau backward chaining terlebih dahulu. "
            "Pohon akan dibuat dari trace hasil eksekusi.",
        )
        st.button(
            "Buka diagnosis workspace",
            type="primary",
            on_click=navigate,
            args=("Diagnosis",),
        )
        return

    if forward and backward:
        forward_tab, backward_tab = st.tabs(["Forward Chaining", "Backward Chaining"])
        with forward_tab:
            _render_forward_tree(forward)
        with backward_tab:
            _render_backward_tree(backward)
    elif forward:
        _render_forward_tree(forward)
    else:
        _render_backward_tree(backward)


# ---------------------------------------------------------------------------
# Forward
# ---------------------------------------------------------------------------
def _render_forward_tree(result) -> None:
    filter_col, download_col = st.columns([3, 1], vertical_alignment="bottom")
    with filter_col:
        filter_mode = st.segmented_control(
            "Filter evaluasi",
            options=[FILTER_ALL, FILTER_FIRED, FILTER_FAILED, FILTER_READY_NOT_SELECTED],
            format_func=lambda value: FILTER_LABELS.get(value, value),
            default=st.session_state.get("tree_filter", FILTER_ALL),
            key="tree_filter",
        )
    if filter_mode is None:
        filter_mode = FILTER_ALL

    dot = forward_tree_dot(result, filter_mode)
    with download_col:
        st.download_button(
            "Unduh graph (.dot)",
            data=dot,
            file_name="netexpert_forward_tree.dot",
            mime="text/vnd.graphviz",
            width="stretch",
            key="download_forward_dot",
        )

    try:
        st.graphviz_chart(
            dot,
            width="stretch",
            alt="Forward chaining inference tree with TRUE/FALSE condition labels",
        )
    except Exception as exc:  # pragma: no cover - defensive for renderer issues
        st.error(f"Gagal merender graph: {exc}. Gunakan tabel alternatif di bawah.")

    info_col, legend_col = st.columns([2, 1])
    with info_col:
        c.banner(
            "blue",
            f"Filter aktif: {FILTER_LABELS.get(filter_mode, filter_mode)}",
            "Klik dan drag untuk pan, gunakan kontrol di kanan atas grafik untuk zoom "
            "dan fit-to-screen. Warna selalu disertai label teks.",
        )
        c.metric_grid(
            [
                {"label": "Iterasi", "value": len(result.iterations), "accent": "blue"},
                {"label": "Aturan fired", "value": len(result.fired_rules), "accent": "green"},
                {"label": "Fakta akhir", "value": len(result.final_facts), "accent": "blue"},
            ]
        )
    with legend_col:
        c.legend_html()

    with st.expander("Tabel evaluasi kondisi (alternatif aksesibel)", expanded=False):
        st.dataframe(
            forward_condition_rows(result),
            width="stretch",
            hide_index=True,
        )

    _render_forward_inspector(result)


def _render_forward_inspector(result) -> None:
    st.markdown(
        '<div class="nx-card-title" style="margin-top:0.4rem">Inspeksi node</div>'
        '<div class="nx-card-sub">Pilih evaluasi aturan untuk melihat detail kondisi dan alasan status.</div>',
        unsafe_allow_html=True,
    )
    entries = []
    for iteration in result.iterations:
        for evaluation in iteration.evaluations:
            entries.append(
                (
                    f"Iterasi {iteration.iteration} · {evaluation.rule_id} · "
                    f"{evaluation.status.label}",
                    evaluation,
                )
            )
    if not entries:
        st.caption("Tidak ada evaluasi.")
        return

    labels = [label for label, _ in entries]
    selected = st.selectbox("Node aturan", labels, label_visibility="collapsed")
    evaluation = dict(entries)[selected]
    c.html_block(c.evaluation_card(evaluation))

    rules = {rule.id: rule for rule in get_rules()}
    rule = rules.get(evaluation.rule_id)
    if rule:
        c.html_block(
            '<div class="nx-card" style="padding:0.7rem 0.9rem">'
            f'<div class="nx-kv">IF <b>{c.esc(" AND ".join(rule.conditions))}</b></div>'
            f'<div class="nx-kv">THEN <b>{c.esc(rule.conclusion)}</b></div>'
            f'<div class="nx-kv">Salience <b>{rule.salience} '
            f"({c.esc(rule.salience_label)})</b> · "
            f"Spesifisitas <b>{rule.specificity}</b></div>"
            "</div>"
        )


# ---------------------------------------------------------------------------
# Backward
# ---------------------------------------------------------------------------
def _render_backward_tree(result) -> None:
    dot = backward_tree_dot(result)
    download_col, _ = st.columns([1, 4], vertical_alignment="bottom")
    with download_col:
        st.download_button(
            "Unduh graph (.dot)",
            data=dot,
            file_name="netexpert_backward_tree.dot",
            mime="text/vnd.graphviz",
            width="stretch",
            key="download_backward_dot",
        )

    try:
        st.graphviz_chart(
            dot,
            width="stretch",
            alt="Backward chaining proof tree with PROVEN and UNPROVEN branches",
        )
    except Exception as exc:  # pragma: no cover - defensive for renderer issues
        st.error(f"Gagal merender graph: {exc}. Gunakan tabel alternatif di bawah.")

    info_col, legend_col = st.columns([2, 1])
    with info_col:
        tone = "green" if result.proven else "red"
        c.banner(
            tone,
            f"Goal '{result.goal}' {'PROVEN' if result.proven else 'UNPROVEN'}",
            "Cabang yang gagal tetap ditampilkan. Node CYCLE menandakan deteksi siklus.",
        )
        c.metric_grid(
            [
                {
                    "label": "Status",
                    "value": "PROVEN" if result.proven else "UNPROVEN",
                    "accent": "green" if result.proven else "red",
                },
                {"label": "Proof path", "value": len(result.proof_path), "accent": "blue"},
                {
                    "label": "Cycle",
                    "value": "Ya" if result.cycle_detected else "Tidak",
                    "accent": "amber" if result.cycle_detected else "blue",
                },
            ]
        )
    with legend_col:
        c.legend_html()

    rows = backward_condition_rows(result)
    with st.expander("Tabel pembuktian (alternatif aksesibel)", expanded=False):
        st.dataframe(rows, width="stretch", hide_index=True)

    st.markdown(
        '<div class="nx-card-title" style="margin-top:0.4rem">Inspeksi node</div>'
        '<div class="nx-card-sub">Setiap baris mewakili satu node pada pohon pembuktian.</div>',
        unsafe_allow_html=True,
    )
    if rows:
        labels = [
            f"{index + 1}. {row['Jalur']} · {row['Status']}"
            for index, row in enumerate(rows)
        ]
        selected = st.selectbox(
            "Node pembuktian", labels, label_visibility="collapsed"
        )
        row = rows[labels.index(selected)]
        status_tone = (
            "green"
            if row["Status"] in {"PROVEN", "TRUE"}
            else "red"
            if row["Status"] == "UNPROVEN"
            else "amber"
            if row["Status"] == "CYCLE"
            else "gray"
        )
        c.html_block(
            '<div class="nx-card">'
            f'<div class="nx-card-title">{c.esc(row["Jalur"])}</div>'
            f'<div style="margin:0.35rem 0">{c.badge(row["Status"], status_tone)} '
            f'{c.badge(row["Tipe"], "gray")}</div>'
            f'<div class="nx-eval-reason">{c.esc(row["Keterangan"])}</div>'
            "</div>"
        )