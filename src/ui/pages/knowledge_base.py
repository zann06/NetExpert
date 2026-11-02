"""Knowledge base management page: search, add, edit and delete rules."""

from __future__ import annotations

from typing import List

import streamlit as st

from ...models import SUPPORTED_CONNECTORS, Rule, salience_label
from .. import components as c
from ..state import get_kb, get_rules, store_kb

SALIENCE_OPTIONS = [1, 2, 3, 4]


def _next_rule_id() -> str:
    numbers = []
    for rule in get_rules():
        digits = "".join(ch for ch in rule.id if ch.isdigit())
        if digits:
            numbers.append(int(digits))
    return f"R{max(numbers, default=0) + 1}"


def _split_conditions(text: str) -> List[str]:
    return [line.strip() for line in str(text).splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def _add_rule_callback() -> None:
    rule = Rule(
        id=st.session_state.get("add_id", ""),
        conditions=_split_conditions(st.session_state.get("add_conditions", "")),
        conclusion=st.session_state.get("add_conclusion", ""),
        salience=st.session_state.get("add_salience", 1),
        connector=st.session_state.get("add_connector", "AND"),
    )
    kb = get_kb()
    errors = kb.add(rule)
    if errors:
        st.session_state.add_errors = errors
        return
    store_kb(kb)
    st.session_state.add_errors = None
    st.session_state.flash = f"Aturan {rule.id} berhasil ditambahkan."
    # Reset the add-form widgets (safe inside a callback, before the rerun).
    st.session_state.add_id = _next_rule_id()
    st.session_state.add_conditions = ""
    st.session_state.add_conclusion = ""
    st.session_state.add_salience = 2
    st.session_state.add_connector = "AND"


def _update_rule_callback(original_id: str) -> None:
    rule = Rule(
        id=st.session_state.get(f"edit_id_{original_id}", ""),
        conditions=_split_conditions(
            st.session_state.get(f"edit_cond_{original_id}", "")
        ),
        conclusion=st.session_state.get(f"edit_concl_{original_id}", ""),
        salience=st.session_state.get(f"edit_sal_{original_id}", 1),
        connector=st.session_state.get(f"edit_conn_{original_id}", "AND"),
    )
    kb = get_kb()
    errors = kb.update(original_id, rule)
    if errors:
        st.session_state.edit_errors = errors
        return
    store_kb(kb)
    st.session_state.edit_errors = None
    st.session_state.flash = f"Aturan {original_id} berhasil diperbarui."
    # Keep the selectbox pointing at the (possibly renamed) rule.
    st.session_state.edit_rule_select = rule.id
    st.session_state.edit_form_version = st.session_state.get("edit_form_version", 0) + 1


def _delete_rule_callback(rule_id: str) -> None:
    kb = get_kb()
    if kb.delete(rule_id):
        store_kb(kb)
        st.session_state.flash = f"Aturan {rule_id} berhasil dihapus."
        remaining = [rule.id for rule in kb.rules]
        st.session_state.edit_rule_select = remaining[0] if remaining else None
    else:
        st.session_state.edit_errors = [f"Aturan {rule_id} tidak ditemukan."]


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    c.page_head(
        "Knowledge Base",
        "Kelola aturan produksi IF–THEN. Beberapa kondisi dalam satu aturan "
        "dapat dihubungkan dengan logika AND atau OR.",
    )

    _render_flash()
    _render_info_cards()

    tab_list, tab_add, tab_edit = st.tabs(
        ["Daftar Aturan", "Tambah Aturan", "Edit / Hapus"]
    )
    with tab_list:
        _render_rule_list()
    with tab_add:
        _render_add_form()
    with tab_edit:
        _render_edit_panel()


def _render_flash() -> None:
    flash = st.session_state.get("flash")
    if flash:
        st.success(flash)
        st.session_state.flash = None


def _render_info_cards() -> None:
    c.html_block(
        '<div class="nx-card">'
        '<div class="nx-card-title">Konvensi basis pengetahuan</div>'
        '<div class="nx-card-sub">'
        "Setiap aturan memiliki satu ID unik, minimal satu kondisi IF, satu kesimpulan THEN, "
        "salience 1–4, dan operator AND atau OR. Spesifisitas dihitung otomatis "
        "dari jumlah kondisi IF."
        "</div>"
        '<div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.25rem">'
        '<span class="nx-chip amber">1 — Rendah</span>'
        '<span class="nx-chip amber">2 — Sedang</span>'
        '<span class="nx-chip amber">3 — Tinggi</span>'
        '<span class="nx-chip amber">4 — Tertinggi</span>'
        "</div>"
        "</div>"
    )


def _render_rule_list() -> None:
    kb = get_kb()
    search_col, salience_col = st.columns([3, 1])
    with search_col:
        query = st.text_input(
            "Cari aturan",
            placeholder="Cari ID, kondisi, atau kesimpulan…",
            key="kb_search",
        )
    with salience_col:
        salience_filter = st.selectbox(
            "Filter salience",
            options=["Semua", *SALIENCE_OPTIONS],
            key="kb_salience_filter",
            format_func=lambda value: value
            if value == "Semua"
            else f"{value} — {salience_label(value)}",
        )

    salience = None if salience_filter == "Semua" else int(salience_filter)
    results = kb.search(query, salience)

    st.caption(f"Menampilkan {len(results)} dari {len(kb)} aturan.")
    if not results:
        c.empty_state(
            "Tidak ada aturan yang cocok",
            "Ubah kata kunci pencarian atau filter salience, atau tambahkan aturan baru.",
        )
        return

    c.html_block(c.rules_table(results))


def _render_add_form() -> None:
    c.section_title(
        "Tambah aturan produksi",
        "Tulis satu kondisi per baris, lalu pilih operator AND atau OR.",
    )

    errors = st.session_state.get("add_errors")
    if errors:
        for error in errors:
            st.error(error)
        st.session_state.add_errors = None

    ss = st.session_state
    if "add_id" not in ss:
        ss.add_id = _next_rule_id()
    if "add_conditions" not in ss:
        ss.add_conditions = ""
    if "add_conclusion" not in ss:
        ss.add_conclusion = ""
    if "add_salience" not in ss:
        ss.add_salience = 2
    if "add_connector" not in ss:
        ss.add_connector = "AND"

    with st.form("add_rule_form"):
        st.text_input("ID Aturan", key="add_id")
        st.text_area(
            "Kondisi IF (satu per baris)",
            key="add_conditions",
            placeholder="Semua Situs Tidak Bisa Dibuka\nHanya Laptop Ini Bermasalah",
            height=120,
        )
        st.selectbox(
            "Operator kondisi",
            options=list(SUPPORTED_CONNECTORS),
            key="add_connector",
        )
        st.text_input(
            "Kesimpulan THEN",
            key="add_conclusion",
            placeholder="Contoh: Masalah pada Laptop",
        )
        st.selectbox(
            "Salience",
            options=SALIENCE_OPTIONS,
            key="add_salience",
            format_func=lambda value: f"{value} — {salience_label(value)}",
        )
        st.form_submit_button(
            "Tambah aturan",
            type="primary",
            on_click=_add_rule_callback,
        )


def _render_edit_panel() -> None:
    kb = get_kb()
    rules = kb.rules
    if not rules:
        c.empty_state(
            "Knowledge base kosong",
            "Tambahkan aturan terlebih dahulu melalui tab Tambah Aturan.",
        )
        return

    options = [rule.id for rule in rules]
    if st.session_state.get("edit_rule_select") not in options:
        st.session_state.edit_rule_select = options[0]

    selected_id = st.selectbox(
        "Pilih aturan yang akan diedit",
        options=options,
        key="edit_rule_select",
    )
    rule = kb.get(selected_id)
    if rule is None:
        return

    errors = st.session_state.get("edit_errors")
    if errors:
        for error in errors:
            st.error(error)
        st.session_state.edit_errors = None

    c.html_block(
        '<div class="nx-card" style="background:#F8FAFC">'
        f'<div class="nx-kv">ID <b>{c.esc(rule.id)}</b> · '
        f'Salience <b>{rule.salience} ({c.esc(salience_label(rule.salience))})</b> · '
        f"Spesifisitas <b>{rule.specificity} kondisi</b> · "
        f"Operator <b>{c.esc(rule.connector)}</b></div>"
        "</div>"
    )

    version = st.session_state.get("edit_form_version", 0)
    with st.form(f"edit_rule_form_{selected_id}_{version}"):
        new_id = st.text_input("ID Aturan", value=rule.id, key=f"edit_id_{selected_id}")
        conditions_text = st.text_area(
            "Kondisi IF (satu per baris)",
            value="\n".join(rule.conditions),
            key=f"edit_cond_{selected_id}",
            height=120,
        )
        st.selectbox(
            "Operator kondisi",
            options=list(SUPPORTED_CONNECTORS),
            index=list(SUPPORTED_CONNECTORS).index(rule.connector)
            if rule.connector in SUPPORTED_CONNECTORS
            else 0,
            key=f"edit_conn_{selected_id}",
        )
        conclusion = st.text_input(
            "Kesimpulan THEN",
            value=rule.conclusion,
            key=f"edit_concl_{selected_id}",
        )
        salience = st.selectbox(
            "Salience",
            options=SALIENCE_OPTIONS,
            index=SALIENCE_OPTIONS.index(rule.salience)
            if rule.salience in SALIENCE_OPTIONS
            else 0,
            key=f"edit_sal_{selected_id}",
            format_func=lambda value: f"{value} — {salience_label(value)}",
        )
        st.form_submit_button(
            "Simpan perubahan",
            type="primary",
            on_click=_update_rule_callback,
            args=(selected_id,),
        )

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            '<div class="nx-card-title" style="color:#B91C1C">Hapus aturan</div>'
            '<div class="nx-card-sub">Tindakan ini tidak dapat dibatalkan. '
            "Hasil inferensi yang ada akan direset.</div>",
            unsafe_allow_html=True,
        )
        confirm = st.checkbox(
            f"Saya yakin ingin menghapus {selected_id}",
            key=f"confirm_delete_{selected_id}",
        )
        st.button(
            "Hapus aturan",
            disabled=not confirm,
            on_click=_delete_rule_callback,
            args=(selected_id,),
        )