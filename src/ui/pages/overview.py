"""Overview / dashboard page."""

from __future__ import annotations

import streamlit as st

from .. import components as c
from ..state import (
    derived_facts_count,
    fired_rules_count,
    get_initial_facts,
    get_kb,
    get_rules,
    navigate,
    run_sample_diagnosis,
)
from ...knowledge_base import default_facts


def render() -> None:
    c.hero(
        "Rule-Based Expert System",
        "Internet Diagnosis Workspace",
        "Simulator sistem pakar untuk mendiagnosis gangguan internet dengan Forward "
        "Chaining dan Backward Chaining. Setiap keputusan inferensi dapat diaudit "
        "melalui conflict set, evaluasi TRUE/FALSE, dan inference tree.",
    )

    rules = get_rules()
    facts = get_initial_facts()
    forward = st.session_state.forward_result

    c.metric_grid(
        [
            {
                "label": "Knowledge Rules",
                "value": len(rules),
                "hint": "Aturan produksi IF–THEN aktif",
                "accent": "blue",
            },
            {
                "label": "Initial Facts",
                "value": len(facts),
                "hint": "Fakta awal di working memory",
                "accent": "blue",
            },
            {
                "label": "Derived Facts",
                "value": derived_facts_count(),
                "hint": "Fakta hasil inferensi terakhir",
                "accent": "green",
            },
            {
                "label": "Fired Rules",
                "value": fired_rules_count(),
                "hint": "Aturan yang telah ditembakkan",
                "accent": "amber",
            },
        ]
    )

    left, right = st.columns([1.55, 1], gap="large")

    with left:
        c.section_title(
            "Bagaimana NetExpert bekerja",
            "Alur penalaran yang deterministik dan dapat ditelusuri.",
        )
        c.steps(
            [
                (
                    "01",
                    "Working memory",
                    "Fakta awal dimuat sebagai himpunan fakta yang dianggap TRUE.",
                ),
                (
                    "02",
                    "Rule matching",
                    "Setiap kondisi IF dievaluasi TRUE atau FALSE terhadap snapshot fakta.",
                ),
                (
                    "03",
                    "Conflict resolution",
                    "Salience → spesifisitas → nomor aturan memilih satu aturan siap.",
                ),
                (
                    "04",
                    "Firing & trace",
                    "Kesimpulan ditambahkan, aturan menjadi refractory, jejak dicatat.",
                ),
            ]
        )

        st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)

        c.section_title(
            "Skenario contoh (data tugas)",
            "Delapan aturan dan tiga fakta awal sesuai spesifikasi assignment.",
        )
        st.markdown(
            '<div style="margin:0.2rem 0 0.55rem 0">'
            '<span class="nx-metric-label">Fakta awal</span><br>'
            + c.chips(default_facts(), "blue")
            + "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="margin:0.2rem 0 0.7rem 0">'
            '<span class="nx-metric-label">Urutan firing yang diharapkan</span><br>'
            '<span class="nx-chip green mono">R5</span>'
            '<span class="nx-muted"> → </span>'
            '<span class="nx-chip green mono">R4</span>'
            '<span class="nx-muted"> → </span>'
            '<span class="nx-chip green mono">R1</span>'
            '<span class="nx-muted"> → </span>'
            '<span class="nx-chip green mono">R7</span>'
            "</div>",
            unsafe_allow_html=True,
        )

    with right:
        c.section_title("Mulai cepat", "Jalankan skenario atau buka workspace.")
        st.button(
            "Jalankan diagnosis contoh",
            type="primary",
            width="stretch",
            on_click=run_sample_diagnosis,
        )
        st.button(
            "Buka diagnosis workspace",
            width="stretch",
            on_click=navigate,
            args=("Diagnosis",),
        )
        st.button(
            "Kelola knowledge base",
            width="stretch",
            on_click=navigate,
            args=("Knowledge Base",),
        )

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        if forward:
            c.banner(
                "green",
                f"Run terakhir: {len(forward.fired_rules)} aturan fired",
                "Buka halaman Inference Tree untuk menelusuri setiap cabang TRUE/FALSE.",
            )
            st.button(
                "Lihat inference tree",
                width="stretch",
                on_click=navigate,
                args=("Inference Tree",),
            )
        else:
            c.banner(
                "blue",
                "Engine siap",
                "Inference engine berjalan lokal tanpa LLM atau API eksternal.",
            )

        c.section_title("Ringkasan engine", "Status modul penalaran.")
        kb = get_kb()
        facts_catalog = kb.fact_catalog(st.session_state.custom_facts)
        st.markdown(
            '<div class="nx-card">'
            f'<div class="nx-kv">Total aturan <b>{len(rules)}</b></div>'
            f'<div class="nx-kv">Fakta dikenal <b>{len(facts_catalog)}</b></div>'
            f'<div class="nx-kv">Katalog fakta <b>{len(st.session_state.custom_facts)} custom</b></div>'
            '<div class="nx-kv">Metode <b>Forward & Backward</b></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    c.section_title(
        "Knowledge base aktif",
        "Semua kondisi dalam satu aturan digabung dengan logika AND.",
    )
    c.html_block(c.rules_table(rules))