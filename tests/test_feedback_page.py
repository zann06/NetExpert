"""Regression tests for the Feedback page rendering.

These use Streamlit's AppTest to actually execute the page (including
``_render_report``), which catches attribute/dict mix-ups such as accessing
``FieldCheck`` objects with ``check["field"]``.
"""

import pytest

from src.feedback import check_answer, parse_answer
from src.knowledge_base import default_facts, default_rules

CORRECT_TABLE = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| --- | --- | --- | --- |
| 1 | R5, R1 | R5 | Gangguan Provider |
| 2 | R4, R1, R7 | R4 | Lapor ke Provider |
| 3 | R1, R7 | R1 | Cek Router |
| 4 | R7 | R7 | Gunakan Tethering Sementara |
| 5 | — | STOP | — |"""

WRONG_TABLE = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| --- | --- | --- | --- |
| 1 | R5, R1 | R1 | Cek Router |"""


def _report(text: str):
    parsed, _ = parse_answer(text)
    return check_answer(parsed, default_rules(), default_facts())


def _app_test(report):
    """Build an AppTest that renders only the feedback report."""
    from streamlit.testing.v1 import AppTest

    def script():
        import streamlit as st

        from src.ui.pages.feedback import _render_report

        _render_report(st.session_state["_report"])

    at = AppTest.from_function(script, default_timeout=30)
    at.session_state["_report"] = report
    return at


def test_render_report_correct_answer_no_exception():
    at = _app_test(_report(CORRECT_TABLE)).run()
    assert not at.exception, [str(e) for e in at.exception]


def test_render_report_wrong_answer_no_exception():
    at = _app_test(_report(WRONG_TABLE)).run()
    assert not at.exception, [str(e) for e in at.exception]
    # The summary dataframe must be present and populated.
    assert len(at.dataframe) == 1
    frame = at.dataframe[0].value
    assert list(frame.columns) == ["Iterasi", "Aspek", "Jawaban", "Engine", "Status"]
    assert len(frame) >= 1
    assert frame.iloc[0]["Aspek"] in {"Conflict set", "Aturan terpilih", "Kesimpulan"}


def test_render_report_shows_every_issue_explanation():
    report = _report(WRONG_TABLE)
    at = _app_test(report).run()
    assert not at.exception
    rendered = " ".join(m.value for m in at.markdown)
    for issue in report.issues:
        assert issue.explanation[:40] in rendered


@pytest.mark.parametrize("text", [CORRECT_TABLE, WRONG_TABLE, "Iterasi 1: R5"])
def test_report_rendering_is_stable(text):
    report = _report(text)
    for _ in range(2):
        at = _app_test(report).run()
        assert not at.exception
