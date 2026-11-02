"""Inference tree viewer.

Two complementary views are offered for the same trace:

* **Graph interaktif** — a clickable Cytoscape graph (``st-link-analysis``).
  Clicking a node shows its detail inline; forward chaining shows one
  iteration at a time so the graph stays readable.
* **Graph statis (DOT)** — the Graphviz diagram (pan/zoom, downloadable
  ``.dot``) used as an export/static view.

Both views are generated from the *actual* inference trace, and accessible
tables plus a selectbox inspector remain available as a text fallback.
"""

from __future__ import annotations

import streamlit as st

from ...visualization import (
    BACKWARD_LAYOUT,
    FILTER_ALL,
    FILTER_FAILED,
    FILTER_FIRED,
    FILTER_LABELS,
    FILTER_READY_NOT_SELECTED,
    FORWARD_LAYOUT,
    backward_condition_rows,
    backward_elements,
    backward_summary,
    backward_tree_dot,
    edge_styles,
    forward_condition_rows,
    forward_iteration_elements,
    forward_summary,
    forward_tree_dot,
    node_styles,
)
from .. import components as c
from ..state import get_rules, navigate


def render() -> None:
    c.page_head(
        "Inference Tree",
        "Pohon dibangun langsung dari trace eksekusi — bukan ilustrasi statis. "
        "Klik node pada graph interaktif untuk melihat detailnya.",
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
# Interactive graph helpers (shared by forward and backward)
# ---------------------------------------------------------------------------
def _node_click_events():
    """Return the node-click event list, or ``None`` when unavailable."""
    try:
        from st_link_analysis import Event
    except Exception:  # pragma: no cover - optional dependency
        return None
    return [Event("node_click", "click tap", "node")]


def _render_interactive_graph(
    elements,
    layout,
    *,
    height: int,
    key: str,
):
    """Render the clickable graph; returns the raw component value or ``None``."""
    events = _node_click_events()
    if events is None:
        st.info(
            "Graph interaktif membutuhkan paket `st-link-analysis`. "
            "Gunakan tab **Graph statis (DOT)** sebagai alternatif."
        )
        return None
    try:
        from st_link_analysis import st_link_analysis
    except Exception:  # pragma: no cover - optional dependency
        st.info(
            "Graph interaktif membutuhkan paket `st-link-analysis`. "
            "Gunakan tab **Graph statis (DOT)** sebagai alternatif."
        )
        return None

    try:
        return st_link_analysis(
            elements=elements,
            layout=layout,
            node_styles=node_styles(),
            edge_styles=edge_styles(),
            height=height,
            key=key,
            events=events,
        )
    except Exception as exc:  # pragma: no cover - defensive for renderer issues
        st.warning(
            f"Graph interaktif gagal dirender: {exc}. "
            "Gunakan tab Graph statis (DOT) atau tabel alternatif di bawah."
        )
        return None


def _clicked_id(value) -> str:
    """Extract ``target_id`` from a st-link-analysis node-click payload."""
    if isinstance(value, dict) and value.get("action") == "node_click":
        data = value.get("data") or {}
        return data.get("target_id")
    return None


def _rule_info_card(rule) -> None:
    if not rule:
        return
    c.html_block(
        '<div class="nx-card" style="padding:0.7rem 0.9rem">'
        f'<div class="nx-kv">IF <b>{c.esc(rule.joined_conditions)}</b></div>'
        f'<div class="nx-kv">THEN <b>{c.esc(rule.conclusion)}</b></div>'
        f'<div class="nx-kv">Salience <b>{rule.salience} '
        f"({c.esc(rule.salience_label)})</b> · "
        f"Spesifisitas <b>{rule.specificity}</b> · "
        f"Operator <b>{c.esc(rule.connector)}</b></div>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Forward
# ---------------------------------------------------------------------------
def _render_forward_tree(result) -> None:
    interactive_tab, static_tab = st.tabs(
        ["Graph interaktif", "Graph statis (DOT)"]
    )
    with interactive_tab:
        _render_forward_interactive(result)
    with static_tab:
        _render_forward_static(result)

    with st.expander("Tabel evaluasi kondisi (alternatif aksesibel)", expanded=False):
        st.dataframe(
            forward_condition_rows(result),
            width="stretch",
            hide_index=True,
        )

    _render_forward_inspector(result)


def _render_forward_interactive(result) -> None:
    iterations = result.iterations
    if not iterations:
        st.caption("Tidak ada iterasi pada trace forward chaining.")
        return

    labels = [
        f"Iterasi {it.iteration} · {it.selected_rule or 'STOP — conflict set kosong'}"
        for it in iterations
    ]
    index = st.selectbox(
        "Pilih iterasi",
        options=list(range(len(iterations))),
        format_func=lambda i: labels[i],
        key="forward_graph_iteration",
    )
    iteration = iterations[index]

    rules = {rule.id: rule for rule in get_rules()}
    elements, lookup = forward_iteration_elements(iteration, rules)

    c.banner(
        "blue",
        forward_summary(result, iteration),
        "Klik node untuk melihat detailnya di bawah graph. Warna selalu disertai label teks.",
    )

    value = _render_interactive_graph(
        elements, FORWARD_LAYOUT, height=720, key="forward_graph"
    )
    target = _clicked_id(value)
    if target and target in lookup:
        st.session_state.forward_graph_selected = target

    selected = st.session_state.get("forward_graph_selected")
    if selected and selected in lookup:
        _render_forward_node_detail(lookup[selected], iteration)
    else:
        st.caption(
            "Klik salah satu node pada graph untuk melihat detailnya di sini."
        )


def _render_forward_node_detail(entry, iteration) -> None:
    kind = entry.get("kind")
    st.markdown(
        '<div class="nx-card-title" style="margin-top:0.5rem">Detail node</div>',
        unsafe_allow_html=True,
    )

    if kind == "snapshot":
        facts = iteration.facts_before
        ranking = " → ".join(iteration.ranking) if iteration.ranking else "—"
        c.html_block(
            '<div class="nx-card">'
            f'<div class="nx-card-title">Snapshot working memory · '
            f"Iterasi {iteration.iteration}</div>"
            f'<div style="margin:0.35rem 0">{c.chips(facts, "blue")}</div>'
            f'<div class="nx-kv">Conflict set <b>'
            f'{c.esc(", ".join(iteration.conflict_set) or "—")}</b></div>'
            f'<div class="nx-kv">Ranking <b>{c.esc(ranking)}</b></div>'
            f'<div class="nx-eval-reason">{c.esc(iteration.selection_reason)}</div>'
            "</div>"
        )
        return

    if kind == "rule":
        evaluation = entry["evaluation"]
        c.html_block(c.evaluation_card(evaluation))
        _rule_info_card(entry.get("rule"))
        return

    if kind == "condition":
        condition = entry["condition"]
        evaluation = entry["evaluation"]
        tone = "green" if condition.status else "red"
        c.html_block(
            '<div class="nx-card">'
            f'<div class="nx-card-title">Kondisi · {c.esc(evaluation.rule_id)}</div>'
            f'<div style="margin:0.35rem 0">{c.badge(condition.label, tone)} '
            f'{c.badge(evaluation.connector + " rule", "gray")}</div>'
            f'<div class="nx-kv"><b>{c.esc(condition.condition)}</b></div>'
            f'<div class="nx-eval-reason">'
            f"{c.esc(condition.explanation or 'Tidak ada penjelasan tambahan.')}"
            "</div>"
            f'<div class="nx-eval-reason">Status aturan: '
            f"<b>{c.esc(evaluation.status.label)}</b> — {c.esc(evaluation.reason)}</div>"
            "</div>"
        )
        return

    if kind == "conclusion":
        evaluation = entry["evaluation"]
        added = iteration.conclusion_added
        added_text = (
            "ditambahkan ke working memory"
            if added
            else "sudah ada — tidak diduplikasi"
        )
        c.html_block(
            '<div class="nx-card">'
            '<div class="nx-card-title">Kesimpulan (THEN)</div>'
            f'<div style="margin:0.35rem 0">{c.chip(iteration.conclusion or "", "green")}'
            f'{c.badge(added_text, "gray")}</div>'
            f'<div class="nx-kv">Dihasilkan oleh <b>{c.esc(evaluation.rule_id)}</b></div>'
            "</div>"
        )
        return

    if kind == "stop":
        c.html_block(
            '<div class="nx-card">'
            '<div class="nx-card-title">STOP</div>'
            f'<div class="nx-eval-reason">Iterasi {iteration.iteration}: '
            "conflict set kosong — tidak ada aturan siap, inferensi berhenti.</div>"
            "</div>"
        )
        return

    st.caption("Node tanpa detail tambahan.")


def _render_forward_static(result) -> None:
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
    _rule_info_card(rules.get(evaluation.rule_id))


# ---------------------------------------------------------------------------
# Backward
# ---------------------------------------------------------------------------
def _render_backward_tree(result) -> None:
    interactive_tab, static_tab = st.tabs(
        ["Graph interaktif", "Graph statis (DOT)"]
    )
    with interactive_tab:
        _render_backward_interactive(result)
    with static_tab:
        _render_backward_static(result)

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
        status_tone = _node_tone(row["Status"])
        c.html_block(
            '<div class="nx-card">'
            f'<div class="nx-card-title">{c.esc(row["Jalur"])}</div>'
            f'<div style="margin:0.35rem 0">{c.badge(row["Status"], status_tone)} '
            f'{c.badge(row["Tipe"], "gray")}</div>'
            f'<div class="nx-eval-reason">{c.esc(row["Keterangan"])}</div>'
            "</div>"
        )


def _node_tone(status: str) -> str:
    if status in {"PROVEN", "TRUE"}:
        return "green"
    if status == "UNPROVEN":
        return "red"
    if status == "CYCLE":
        return "amber"
    return "gray"


def _render_backward_interactive(result) -> None:
    elements, lookup = backward_elements(result)

    c.banner(
        "green" if result.proven else "red",
        backward_summary(result),
        "Klik node untuk melihat detailnya di bawah graph. "
        "Cabang gagal tetap ditampilkan.",
    )

    value = _render_interactive_graph(
        elements, BACKWARD_LAYOUT, height=680, key="backward_graph"
    )
    target = _clicked_id(value)
    if target and target in lookup:
        st.session_state.backward_graph_selected = target

    selected = st.session_state.get("backward_graph_selected")
    if selected and selected in lookup:
        _render_backward_node_detail(lookup[selected])
    else:
        st.caption(
            "Klik salah satu node pada graph untuk melihat detailnya di sini."
        )


def _render_backward_node_detail(entry) -> None:
    node = entry["node"]
    st.markdown(
        '<div class="nx-card-title" style="margin-top:0.5rem">Detail node</div>',
        unsafe_allow_html=True,
    )
    c.html_block(
        '<div class="nx-card">'
        f'<div class="nx-card-title">{c.esc(node.label)}</div>'
        f'<div style="margin:0.35rem 0">'
        f'{c.badge(node.status.value, _node_tone(node.status.value))} '
        f'{c.badge(node.kind, "gray")} '
        f'{c.badge(f"depth {node.depth}", "gray")}</div>'
        f'<div class="nx-kv">Sumber: '
        f'<b>{c.esc(node.source or "—")}</b></div>'
        f'<div class="nx-kv">Aturan <b>{c.esc(node.rule_id or "—")}</b> · '
        f'Operator <b>{c.esc(node.connector or "—")}</b></div>'
        f'<div class="nx-eval-reason">'
        f"{c.esc(node.detail or 'Tidak ada keterangan tambahan.')}</div>"
        "</div>"
    )


def _render_backward_static(result) -> None:
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
