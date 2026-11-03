"""Tests for the feedback feature: parser, checker, and their guarantees.

The feedback feature must be deterministic (no AI): a pasted answer is parsed
into claimed iterations and compared with a fresh forward-chaining run.
"""

import pytest

from src.feedback import check_answer, parse_answer
from src.feedback.models import SubmittedIteration, SubmittedIterations
from src.knowledge_base import default_facts, default_rules


def _check(text: str):
    parsed, unrecognized = parse_answer(text)
    report = check_answer(parsed, default_rules(), default_facts())
    return parsed, unrecognized, report


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def test_parse_markdown_table_correct_answer():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| --- | --- | --- | --- |
| 1 | R5, R1 | R5 | Gangguan Provider |
| 2 | R4, R1, R7 | R4 | Lapor ke Provider |
| 3 | R1, R7 | R1 | Cek Router |
| 4 | R7 | R7 | Gunakan Tethering Sementara |
| 5 | — | STOP | — |"""
    parsed, unrecognized = parse_answer(text)
    assert unrecognized == []
    assert [it.iteration for it in parsed] == [1, 2, 3, 4, 5]
    assert parsed.iterations[0].conflict_set == ["R5", "R1"]
    assert parsed.iterations[0].selected_rule == "R5"
    assert parsed.iterations[0].conclusion == "Gangguan Provider"
    assert parsed.iterations[4].stop is True


def test_parse_labelled_free_lines():
    text = (
        "Iterasi 1: conflict set R5, R1 -> R5 dipilih, kesimpulan Gangguan Provider\n"
        "Iterasi 2: conflict set R4, R1, R7 -> R4 dipilih, kesimpulan Lapor ke Provider\n"
        "Iterasi 3: conflict set R1, R7 -> R1 dipilih, kesimpulan Cek Router\n"
        "Iterasi 4: conflict set R7 -> R7 dipilih, kesimpulan Gunakan Tethering Sementara"
    )
    parsed, unrecognized = parse_answer(text)
    assert unrecognized == []
    assert len(parsed) == 4
    assert parsed.iterations[1].conflict_set == ["R4", "R1", "R7"]
    assert parsed.iterations[1].selected_rule == "R4"
    assert parsed.iterations[3].conclusion == "Gunakan Tethering Sementara"


def test_parse_ordered_list_positional():
    text = "1. R5 -> Gangguan Provider\n2. R4 -> Lapor ke Provider"
    parsed, _ = parse_answer(text)
    assert parsed.iterations[0].selected_rule == "R5"
    assert parsed.iterations[0].conclusion == "Gangguan Provider"
    assert parsed.iterations[1].selected_rule == "R4"


def test_parse_normalizes_rule_ids():
    text = "Iterasi 1: conflict set r5, r1 -> r5 dipilih"
    parsed, _ = parse_answer(text)
    assert parsed.iterations[0].conflict_set == ["R5", "R1"]
    assert parsed.iterations[0].selected_rule == "R5"


def test_parse_empty_answer_yields_nothing():
    parsed, unrecognized = parse_answer("")
    assert len(parsed) == 0
    assert unrecognized == []
    parsed, _ = parse_answer("halo ini jawaban tanpa iterasi")
    assert len(parsed) == 0


# ---------------------------------------------------------------------------
# Checker — correct answers
# ---------------------------------------------------------------------------
def test_check_correct_table_scores_100():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R5 | Gangguan Provider |
| 2 | R4, R1, R7 | R4 | Lapor ke Provider |
| 3 | R1, R7 | R1 | Cek Router |
| 4 | R7 | R7 | Gunakan Tethering Sementara |
| 5 | — | STOP | — |"""
    _, unrecognized, report = _check(text)
    assert unrecognized == []
    assert report.all_correct
    assert report.score_percent == 100


def test_check_matches_current_dataset_not_hardcoded():
    """The checker re-runs the engine, so a modified KB changes the expectation."""
    from src.models import Rule

    rules = [Rule("R1", ["A"], "X", 1), Rule("R2", ["B"], "Y", 2)]
    parsed = SubmittedIterations(
        iterations=[
            SubmittedIteration(iteration=1, conflict_set=["R2", "R1"],
                               selected_rule="R2", conclusion="Y"),
            SubmittedIteration(iteration=2, conflict_set=["R1"],
                               selected_rule="R1", conclusion="X"),
        ]
    )
    report = check_answer(parsed, rules, ["A", "B"])
    assert report.all_correct


# ---------------------------------------------------------------------------
# Checker — wrong answers and explanations
# ---------------------------------------------------------------------------
def test_check_wrong_selected_rule_cites_salience():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R1 | Cek Router |"""
    _, _, report = _check(text)
    assert not report.all_correct
    selected_issue = next(i for i in report.issues if i.field == "selected_rule")
    assert selected_issue.claim == "R1"
    assert selected_issue.expected == "R5"
    assert "salience" in selected_issue.explanation
    assert "R5=2" in selected_issue.explanation and "R1=1" in selected_issue.explanation


def test_check_wrong_conflict_set_reports_missing_member():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5 | R5 | Gangguan Provider |"""
    _, _, report = _check(text)
    cs_issue = next(i for i in report.issues if i.field == "conflict_set")
    assert "R1" in cs_issue.expected
    assert "READY" in cs_issue.explanation


def test_check_missing_iterations_reported():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R5 | Gangguan Provider |"""
    _, _, report = _check(text)
    missing = [i for i in report.issues if i.field == "missing"]
    assert {i.iteration for i in missing} == {2, 3, 4}


def test_check_extra_iteration_reported():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R5 | Gangguan Provider |
| 2 | R4, R1, R7 | R4 | Lapor ke Provider |
| 3 | R1, R7 | R1 | Cek Router |
| 4 | R7 | R7 | Gunakan Tethering Sementara |
| 5 | R9 | R9 | Faktanya salah |"""
    _, _, report = _check(text)
    extra = [i for i in report.issues if i.field == "extra"]
    assert extra and extra[0].iteration == 5


def test_check_duplicate_iteration_flagged():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R5 | Gangguan Provider |
| 1 | R5, R1 | R5 | Gangguan Provider |"""
    _, _, report = _check(text)
    assert any(i.field == "extra" for i in report.issues)


def test_check_wrong_conclusion_cites_then_part():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R5 | Cek Router |"""
    _, _, report = _check(text)
    conclusion_issue = next(i for i in report.issues if i.field == "conclusion")
    assert conclusion_issue.expected == "Gangguan Provider"
    assert "THEN" in conclusion_issue.explanation


def test_check_refraction_explained_when_rule_excluded():
    """After R5 fires, iteration 2's conflict set must exclude R5 (refraction)."""
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R5 | Gangguan Provider |
| 2 | R5, R4, R1, R7 | R4 | Lapor ke Provider |"""
    _, _, report = _check(text)
    cs_issue = next(
        i for i in report.issues if i.field == "conflict_set" and i.iteration == 2
    )
    assert "refractory" in cs_issue.explanation.lower()
    assert "R5" in cs_issue.explanation


# ---------------------------------------------------------------------------
# Guarantees
# ---------------------------------------------------------------------------
def test_score_is_deterministic():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R1 | Cek Router |"""
    report_a = _check(text)[2]
    report_b = _check(text)[2]
    assert report_a.score_percent == report_b.score_percent
    assert [i.field for i in report_a.issues] == [i.field for i in report_b.issues]


def test_severity_warning_only_for_structure():
    text = """| Iterasi | Conflict Set | Aturan Terpilih | Kesimpulan |
| 1 | R5, R1 | R1 | Cek Router |"""
    _, _, report = _check(text)
    for issue in report.issues:
        if issue.field in {"missing", "extra"}:
            assert issue.severity == "warning"
        else:
            assert issue.severity == "error"


@pytest.mark.parametrize(
    "text",
    [
        "Iterasi 1: R5 dipilih",
        "| Iterasi | Conflict Set |\n| 1 | R5, R1 |",
        "1. R5",
    ],
)
def test_partial_answers_never_crash(text):
    parsed, _ = parse_answer(text)
    report = check_answer(parsed, default_rules(), default_facts())
    assert isinstance(report.score_percent, int)
