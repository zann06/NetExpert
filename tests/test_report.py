"""Tests for the professional report renderer.

The report must be monochrome, print-ready, tolerant of empty optional fields,
and consistent with the actual inference trace.
"""

from src.inference import run_backward_chaining, run_forward_chaining
from src.knowledge_base import default_facts, default_rules
from src.models import Rule
from src.report import ReportMeta, TeamMember, build_sections, render_html, render_markdown


def _forward():
    return run_forward_chaining(default_rules(), default_facts())


def _backward():
    return run_backward_chaining(default_rules(), default_facts(), "Lapor ke Provider")


def _meta(**overrides):
    data = {
        "title": "Laporan Uji Sistem Pakar",
        "course": "Sistem Pakar",
        "group_name": "Kelompok 4",
        "group_number": "04",
        "lecturer": "Dr. Nama Dosen",
        "institution": "Universitas Contoh",
        "city": "Bandung",
        "date": "3 November 2026",
        "members": [
            TeamMember("Budi Santoso", "21.11.0001", "Ketua"),
            TeamMember("Ani Lestari", "21.11.0002", "Anggota"),
        ],
    }
    data.update(overrides)
    return ReportMeta(**data)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------
def test_report_contains_professional_sections():
    html = render_html(
        _meta(),
        forward=_forward(),
        rules=default_rules(),
        initial_facts=default_facts(),
        generated_at="3 November 2026",
    )
    for heading in (
        "Ringkasan Eksekutif",
        "Pendahuluan",
        "Basis Pengetahuan dan Fakta Awal",
        "Hasil Forward Chaining",
        "Kesimpulan dan Rekomendasi",
        "Lampiran",
    ):
        assert heading in html
    assert html.strip().startswith("<!doctype html>")
    assert html.strip().endswith("</html>")


def test_report_is_monochrome_and_print_ready():
    html = render_html(_meta(), rules=default_rules(), initial_facts=default_facts())
    # No application accent colours may leak into the document.
    assert "#2563EB" not in html
    assert "#16A34A" not in html
    assert "#DC2626" not in html
    assert "#D97706" not in html
    assert "#000000" in html
    assert "Times New Roman" in html
    assert "@page" in html
    assert "size: A4" in html
    assert "@media print" in html


def test_identity_fields_and_members_are_rendered():
    html = render_html(_meta())
    assert "Kelompok 4 (04)" in html
    assert "Dr. Nama Dosen" in html
    assert "Universitas Contoh" in html
    assert "Budi Santoso — NIM 21.11.0001 — Ketua" in html
    assert "Ani Lestari — NIM 21.11.0002 — Anggota" in html


def test_empty_optional_fields_are_hidden():
    html = render_html(ReportMeta(title="Laporan Minimal"))
    assert "Laporan Minimal" in html
    # No empty identity rows are emitted.
    assert "Anggota Kelompok" not in html
    assert "Dosen Pengampu" not in html
    assert "Fakultas" not in html


def test_user_input_is_escaped():
    html = render_html(
        _meta(title="<script>alert(1)</script>", group_name="A & B")
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html


def test_logo_is_embedded_as_data_url():
    html = render_html(_meta(logo_data_url="data:image/png;base64,AAAA"))
    assert 'src="data:image/png;base64,AAAA"' in html


# ---------------------------------------------------------------------------
# Trace consistency
# ---------------------------------------------------------------------------
def test_forward_section_matches_the_trace():
    forward = _forward()
    html = render_html(_meta(), forward=forward, rules=default_rules())
    assert "R5 → R4 → R1 → R7" in html
    for iteration in forward.iterations:
        assert f"<td>{iteration.iteration}</td>" in html
    assert "Fakta turunan (derived facts)" in html
    assert "Working memory akhir" in html


def test_backward_section_matches_the_trace():
    backward = _backward()
    html = render_html(_meta(), backward=backward)
    assert "Hasil Backward Chaining" in html
    assert "Lapor ke Provider" in html
    assert "PROVEN" in html
    assert "Jalur Pembuktian" in html


def test_or_connector_appears_in_rule_table():
    rules = [Rule("R1", ["A", "B"], "C", 1, connector="OR")]
    html = render_html(_meta(), rules=rules)
    assert "A OR B" in html
    assert "<td>OR</td>" in html


def test_build_sections_numbers_follow_available_results():
    sections = build_sections(_meta(), forward=_forward(), rules=default_rules())
    titles = [section["title"] for section in sections]
    assert titles[0] == "Ringkasan Eksekutif"
    assert "Hasil Forward Chaining" in titles
    assert "Hasil Backward Chaining" not in titles
    assert titles[-1].startswith("Lampiran")


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def test_markdown_contains_sections_and_tables():
    markdown = render_markdown(
        _meta(),
        forward=_forward(),
        rules=default_rules(),
        initial_facts=default_facts(),
        generated_at="3 November 2026",
    )
    assert markdown.startswith("# Laporan Uji Sistem Pakar")
    assert "## 1. Ringkasan Eksekutif" in markdown
    assert "| ID | Operator | IF (Kondisi) | THEN (Kesimpulan) | Salience |" in markdown
    assert "R5 → R4 → R1 → R7" in markdown
    assert "Budi Santoso — NIM 21.11.0001 — Ketua" in markdown
    assert "Dokumen ini dihasilkan otomatis oleh NetExpert" in markdown


def test_markdown_escapes_pipes_in_table_cells():
    rules = [Rule("R1", ["A | B"], "C", 1)]
    markdown = render_markdown(_meta(), rules=rules)
    assert "A \\| B" in markdown
