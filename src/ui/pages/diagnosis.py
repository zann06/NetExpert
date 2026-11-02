"""Diagnosis workspace: facts, inference controls, results and iteration log."""

from __future__ import annotations

import streamlit as st

from ...inference import run_backward_chaining, run_forward_chaining
from ...inference.conflict_resolution import describe_ranking
from ...models import BackwardResult, ForwardResult, RuleStatus
from .. import components as c
from ..state import (
    add_custom_fact,
    clear_facts,
    clear_results,
    fact_catalog,
    get_initial_facts,
    get_rules,
    navigate,
    restore_default_facts,
    run_sample_diagnosis,
    save_backward_result,
    save_forward_result,
    set_initial_facts,
)


# ---------------------------------------------------------------------------
# Callbacks (run before the next script rerun, so widget state is safe to set)
# ---------------------------------------------------------------------------
def _add_fact_callback() -> None:
    raw = st.session_state.get("fact_input", "")
    clean = " ".join(str(raw).split())
    if not clean:
        st.session_state.fact_error = "Fakta tidak boleh kosong."
        return

    catalog_keys = {f.casefold() for f in fact_catalog()}
    if clean.casefold() not in catalog_keys:
        add_custom_fact(clean)

    current = get_initial_facts()
    if clean.casefold() not in {f.casefold() for f in current}:
        current.append(clean)
    st.session_state.facts_select = current
    set_initial_facts(current)
    st.session_state.fact_input = ""
    st.session_state.fact_error = None


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    c.page_head(
        "Diagnosis Workspace",
        "Pilih fakta awal, tentukan metode inferensi, lalu jalankan penalaran. "
        "Semua keputusan conflict resolution dan evaluasi kondisi dicatat.",
    )

    left, right = st.columns([1.35, 0.65], gap="large")
    with left:
        _render_facts_panel()
    with right:
        _render_controls_panel()

    _render_results()


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------
def _render_facts_panel() -> None:
    c.section_title(
        "Fakta Awal",
        "Fakta dianggap TRUE bila berada di working memory. Pencocokan memakai teks ternormalisasi.",
    )

    catalog = fact_catalog()
    for fact in get_initial_facts():
        if fact not in catalog:
            catalog.append(fact)

    if "facts_select" not in st.session_state:
        st.session_state.facts_select = get_initial_facts()
    # Guard against stale selections that are no longer in the catalog.
    valid = [f for f in st.session_state.facts_select if f in catalog]
    if valid != st.session_state.facts_select:
        st.session_state.facts_select = valid

    selected = st.multiselect(
        "Fakta awal terpilih",
        options=catalog,
        key="facts_select",
        help="Pilih satu atau lebih fakta. Anda juga dapat menambahkan fakta manual di bawah.",
    )
    set_initial_facts(selected)

    if st.session_state.get("fact_error"):
        st.error(st.session_state.fact_error)
        st.session_state.fact_error = None

    st.markdown(
        '<div class="nx-card-sub" style="margin-top:0.55rem">Tambah fakta manual</div>',
        unsafe_allow_html=True,
    )
    input_col, button_col = st.columns([3, 1], vertical_alignment="bottom")
    with input_col:
        st.text_input(
            "Fakta baru",
            key="fact_input",
            placeholder="Contoh: Router Terasa Panas",
            label_visibility="collapsed",
        )
    with button_col:
        st.button(
            "Tambah",
            width="stretch",
            on_click=_add_fact_callback,
        )

    reset_col, clear_col = st.columns(2)
    with reset_col:
        st.button(
            "Muat fakta default",
            width="stretch",
            on_click=restore_default_facts,
        )
    with clear_col:
        st.button(
            "Kosongkan fakta",
            width="stretch",
            on_click=clear_facts,
        )

    st.markdown(
        '<div style="margin-top:0.7rem"><span class="nx-metric-label">Initial facts</span></div>',
        unsafe_allow_html=True,
    )
    c.html_block(c.chips(get_initial_facts(), "blue"))

    forward = st.session_state.forward_result
    if forward and forward.derived_facts:
        st.markdown(
            '<div style="margin-top:0.55rem"><span class="nx-metric-label">Derived facts</span></div>',
            unsafe_allow_html=True,
        )
        c.html_block(c.chips(forward.derived_facts, "green"))


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
def _render_controls_panel() -> None:
    c.section_title(
        "Kontrol Inferensi",
        "Forward bersifat data-driven; backward bersifat goal-driven.",
    )

    method = st.radio(
        "Metode inferensi",
        ["Forward Chaining", "Backward Chaining"],
        horizontal=True,
        key="method",
    )

    if method == "Backward Chaining":
        st.text_input(
            "Goal yang ingin dibuktikan",
            value="Lapor ke Provider",
            key="goal_input",
            help="Contoh: Lapor ke Provider",
        )
        st.caption(
            "Backward chaining mencari aturan yang THEN-nya sama dengan goal, "
            "lalu membuktikan setiap kondisi IF sebagai subgoal."
        )
    else:
        st.text_input(
            "Goal opsional (forward)",
            value="",
            key="forward_goal",
            help="Kosongkan bila hanya ingin melihat semua kesimpulan.",
        )
        st.caption(
            "Forward chaining menembakkan aturan siap sampai conflict set kosong."
        )

    st.button(
        "Jalankan inferensi",
        type="primary",
        width="stretch",
        on_click=_execute,
        args=(method,),
    )
    st.button(
        "Reset hasil",
        width="stretch",
        on_click=clear_results,
    )
    st.button(
        "Jalankan skenario contoh",
        width="stretch",
        on_click=run_sample_diagnosis,
    )


def _execute(method: str) -> None:
    rules = get_rules()
    facts = get_initial_facts()
    goal_key = "goal_input" if method == "Backward Chaining" else "forward_goal"
    goal = str(st.session_state.get(goal_key, "")).strip()

    if not rules:
        st.session_state.flash_error = "Knowledge base kosong — tambahkan minimal satu aturan."
        return
    if not facts:
        st.session_state.flash_error = "Pilih minimal satu fakta awal sebelum menjalankan inferensi."
        return

    if method == "Backward Chaining":
        if not goal:
            st.session_state.flash_error = "Goal wajib diisi untuk backward chaining."
            return
        result = run_backward_chaining(rules, facts, goal)
        save_backward_result(result)
    else:
        result = run_forward_chaining(rules, facts, goal=goal or None)
        save_forward_result(result, goal)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
def _render_results() -> None:
    if st.session_state.get("flash_error"):
        st.error(st.session_state.flash_error)
        st.session_state.flash_error = None

    forward = st.session_state.forward_result
    backward = st.session_state.backward_result

    if not forward and not backward:
        c.empty_state(
            "Belum ada hasil inferensi",
            "Pilih fakta awal lalu tekan Jalankan inferensi. Conflict set, evaluasi "
            "TRUE/FALSE, dan iteration log akan tampil di sini.",
        )
        return

    if forward:
        _render_forward_result(forward)
    elif backward:
        _render_backward_result(backward)


def _render_forward_result(result: ForwardResult) -> None:
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    c.section_title(
        "Hasil Forward Chaining",
        "Data-driven inference dengan refractoriness dan conflict resolution.",
    )

    if result.goal:
        tone = "green" if result.goal_proven else "red"
        title = (
            f"Goal '{result.goal}' PROVEN"
            if result.goal_proven
            else f"Goal '{result.goal}' UNPROVEN"
        )
        message = (
            "Goal ditemukan pada working memory akhir."
            if result.goal_proven
            else "Goal tidak ditemukan pada working memory akhir setelah semua aturan siap ditembakkan."
        )
        c.banner(tone, title, message)
    else:
        c.banner(
            "green",
            "Inferensi selesai",
            f"{result.terminated_reason} {len(result.fired_rules)} aturan fired, "
            f"{len(result.derived_facts)} fakta turunan dihasilkan.",
        )

    c.metric_grid(
        [
            {"label": "Fired rules", "value": len(result.fired_rules), "accent": "green"},
            {"label": "Derived facts", "value": len(result.derived_facts), "accent": "blue"},
            {"label": "Iterations", "value": len(result.iterations), "accent": "amber"},
            {"label": "Working memory", "value": len(result.final_facts), "accent": "blue"},
        ]
    )

    firing = "".join(
        ("" if index == 0 else '<span class="nx-muted"> → </span>')
        + c.chip(rule_id, "green", mono=True)
        for index, rule_id in enumerate(result.fired_rules)
    ) or '<span class="nx-muted">Tidak ada aturan yang fired.</span>'
    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-metric-label">Urutan firing</div>'
        f'<div style="margin:0.3rem 0 0.65rem 0">{firing}</div>'
        '<div class="nx-metric-label">Derived facts</div>'
        f"<div>{c.chips(result.derived_facts, 'green')}</div>"
        "</div>"
    )

    _render_iteration_summary(result)
    _render_failed_branches(result)

    st.markdown(
        '<div class="nx-card-title" style="margin-top:0.5rem">Iteration log</div>'
        '<div class="nx-card-sub">Setiap iterasi memakai snapshot working memory pada awal iterasi.</div>',
        unsafe_allow_html=True,
    )
    rules_map = {rule.id: rule for rule in get_rules()}
    for iteration in result.iterations:
        ready_rules = [
            rules_map[rule_id]
            for rule_id in iteration.conflict_set
            if rule_id in rules_map
        ]
        ranking_rows = describe_ranking(ready_rules)
        title = (
            f"Iterasi {iteration.iteration} — FIRED {iteration.selected_rule}"
            if iteration.selected_rule
            else f"Iterasi {iteration.iteration} — STOP"
        )
        with st.expander(title, expanded=(iteration.iteration == 1)):
            st.markdown(
                c.iteration_detail(iteration, ranking_rows),
                unsafe_allow_html=True,
            )

    st.button(
        "Lihat inference tree",
        width="stretch",
        on_click=navigate,
        args=("Inference Tree",),
    )


def _render_iteration_summary(result: ForwardResult) -> None:
    rows = []
    for iteration in result.iterations:
        conflict = ", ".join(iteration.conflict_set) if iteration.conflict_set else "—"
        selected = iteration.selected_rule or "STOP"
        conclusion = iteration.conclusion or "—"
        added = (
            "Ya"
            if iteration.conclusion_added
            else ("Tidak (sudah ada)" if iteration.conclusion_added is False else "—")
        )
        rows.append(
            "<tr>"
            f'<td class="nx-num">{iteration.iteration}</td>'
            f"<td>{c.chip(conflict, 'gray', mono=True) if conflict != '—' else '—'}</td>"
            f"<td>{c.chip(selected, 'green' if iteration.selected_rule else 'gray', mono=True)}</td>"
            f"<td>{c.chip(conclusion, 'green') if conclusion != '—' else '—'}</td>"
            f"<td>{added}</td>"
            "</tr>"
        )
    c.html_block(
        '<div class="nx-table-wrap"><table class="nx-table"><thead><tr>'
        "<th>Iterasi</th><th>Conflict set</th><th>Terpilih</th>"
        "<th>Kesimpulan</th><th>Fakta baru</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _render_failed_branches(result: ForwardResult) -> None:
    fired = set(result.fired_rules)
    rules = get_rules()
    failed_evaluations = []
    for rule in rules:
        if rule.id in fired:
            continue
        # Use the most recent evaluation for this rule (still NOT READY).
        best = None
        for iteration in result.iterations:
            evaluation = iteration.evaluation_for(rule.id)
            if evaluation and evaluation.status == RuleStatus.NOT_READY:
                best = evaluation
        if best is not None:
            failed_evaluations.append(best)

    if not failed_evaluations:
        return

    ids = ", ".join(ev.rule_id for ev in failed_evaluations)
    with st.expander(f"Cabang gagal — aturan yang tidak pernah fired ({ids})", expanded=False):
        st.caption(
            "Aturan berikut tidak pernah masuk conflict set karena kondisi IF tidak "
            "memenuhi operator aturannya (AND/OR). Cabang ini tetap disimpan agar "
            "penalaran dapat diaudit."
        )
        st.markdown(c.evaluation_cards(failed_evaluations), unsafe_allow_html=True)


def _render_backward_result(result: BackwardResult) -> None:
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    c.section_title(
        "Hasil Backward Chaining",
        "Goal-driven inference dengan pencatatan cabang berhasil dan gagal.",
    )

    if result.proven:
        c.banner(
            "green",
            f"Goal '{result.goal}' PROVEN",
            f"Dibuktikan melalui aturan {result.root.rule_id}. "
            "Kondisi pada jalur bukti memenuhi operator aturan.",
        )
    else:
        message = "Tidak ada aturan kandidat yang berhasil membuktikan seluruh subgoal."
        if result.cycle_detected:
            message += " Siklus terdeteksi pada salah satu cabang."
        c.banner("red", f"Goal '{result.goal}' UNPROVEN", message)

    c.metric_grid(
        [
            {
                "label": "Status goal",
                "value": "PROVEN" if result.proven else "UNPROVEN",
                "accent": "green" if result.proven else "red",
            },
            {"label": "Proof path", "value": len(result.proof_path), "accent": "blue"},
            {"label": "Initial facts", "value": len(result.initial_facts), "accent": "blue"},
            {
                "label": "Cycle detected",
                "value": "Ya" if result.cycle_detected else "Tidak",
                "accent": "amber" if result.cycle_detected else "blue",
            },
        ]
    )

    proof = "".join(
        ("" if index == 0 else '<span class="nx-muted"> → </span>')
        + c.chip(rule_id, "green", mono=True)
        for index, rule_id in enumerate(result.proof_path)
    ) or '<span class="nx-muted">Tidak ada jalur bukti.</span>'
    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-metric-label">Proof path (subgoal → goal)</div>'
        f'<div style="margin:0.3rem 0 0">{proof}</div>'
        "</div>"
    )

    with st.expander("Log penalaran backward", expanded=True):
        if result.log:
            for line in result.log:
                tone = "green" if line.startswith("[PROVEN]") else (
                    "red" if line.startswith(("[UNPROVEN]", "[FAILED]")) else "amber"
                )
                st.markdown(c.badge(line.split("]")[0].strip("["), tone) + " " + c.esc(line.split("]", 1)[1]), unsafe_allow_html=True)
        else:
            st.caption("Tidak ada catatan.")

    st.markdown(
        '<div class="nx-card-title" style="margin-top:0.4rem">Struktur pohon pembuktian</div>'
        '<div class="nx-card-sub">Semua cabang, termasuk alternatif yang gagal, ditampilkan.</div>',
        unsafe_allow_html=True,
    )
    from ...visualization import backward_condition_rows

    st.dataframe(
        backward_condition_rows(result),
        width="stretch",
        hide_index=True,
    )

    st.button(
        "Lihat inference tree",
        width="stretch",
        on_click=navigate,
        args=("Inference Tree",),
    )