"""Tests for the forward-chaining engine.

These tests assert the *actual* expected values, not merely that functions run.
"""

from src.inference import run_forward_chaining
from src.knowledge_base import default_facts, default_rules
from src.models import Rule, RuleStatus


# ---------------------------------------------------------------------------
# Baseline assignment scenario
# ---------------------------------------------------------------------------
def test_default_firing_order_is_r5_r4_r1_r7():
    result = run_forward_chaining(default_rules(), default_facts())
    assert result.fired_rules == ["R5", "R4", "R1", "R7"]


def test_default_conflict_sets_match_assignment():
    result = run_forward_chaining(default_rules(), default_facts())
    conflict_sets = [it.conflict_set for it in result.iterations]
    assert conflict_sets == [
        ["R5", "R1"],
        ["R4", "R1", "R7"],
        ["R1", "R7"],
        ["R7"],
        [],
    ]


def test_default_final_working_memory():
    result = run_forward_chaining(default_rules(), default_facts())
    assert result.derived_facts == [
        "Gangguan Provider",
        "Lapor ke Provider",
        "Cek Router",
        "Gunakan Tethering Sementara",
    ]
    assert set(result.final_facts) == {
        "Semua Situs Tidak Bisa Dibuka",
        "Perangkat Lain Juga Offline",
        "Tagihan Sudah Dibayar",
        "Gangguan Provider",
        "Lapor ke Provider",
        "Cek Router",
        "Gunakan Tethering Sementara",
    }
    # Iteration 5 terminates with an empty conflict set.
    assert result.iterations[-1].iteration == 5
    assert result.iterations[-1].selected_rule is None


def test_each_condition_has_explicit_true_false_status():
    result = run_forward_chaining(default_rules(), default_facts())
    first = result.iterations[0]
    statuses = {
        ev.rule_id: [c.status for c in ev.condition_results] for ev in first.evaluations
    }
    assert statuses["R1"] == [True]
    assert statuses["R2"] == [False]
    assert statuses["R3"] == [False]
    assert statuses["R4"] == [False, True]   # Gangguan Provider absent, Tagihan present
    assert statuses["R5"] == [True]
    assert statuses["R6"] == [True, False]   # Hanya Laptop Ini Bermasalah absent
    assert statuses["R7"] == [False]
    assert statuses["R8"] == [False, False]  # Cek Router and Router Terasa Panas absent


def test_r6_is_not_ready_and_shows_failed_branch():
    result = run_forward_chaining(default_rules(), default_facts())
    first = result.iterations[0]
    r6 = first.evaluation_for("R6")
    assert r6.status == RuleStatus.NOT_READY
    assert r6.condition_results[1].condition == "Hanya Laptop Ini Bermasalah"
    assert r6.condition_results[1].status is False


def test_r8_is_not_ready_without_router_temperature():
    result = run_forward_chaining(default_rules(), default_facts())
    first = result.iterations[0]
    r8 = first.evaluation_for("R8")
    assert r8.status == RuleStatus.NOT_READY
    assert r8.condition_results[1].condition == "Router Terasa Panas"
    assert r8.condition_results[1].status is False


def test_r2_and_r3_not_ready_in_baseline():
    result = run_forward_chaining(default_rules(), default_facts())
    first = result.iterations[0]
    assert first.evaluation_for("R2").status == RuleStatus.NOT_READY
    assert first.evaluation_for("R3").status == RuleStatus.NOT_READY


def test_ready_but_not_selected_is_distinct_from_not_ready():
    result = run_forward_chaining(default_rules(), default_facts())
    first = result.iterations[0]
    # R1 was ready but R5 won on salience.
    assert first.evaluation_for("R1").status == RuleStatus.READY_NOT_SELECTED
    # R6 failed because a condition was missing.
    assert first.evaluation_for("R6").status == RuleStatus.NOT_READY
    assert first.evaluation_for("R1").status != first.evaluation_for("R6").status


# ---------------------------------------------------------------------------
# Refractoriness
# ---------------------------------------------------------------------------
def test_refractoriness_prevents_second_firing():
    result = run_forward_chaining(default_rules(), default_facts())
    assert result.fired_rules.count("R5") == 1
    # R5 fired in iteration 1 and is REFRACTORY from iteration 2 onward.
    for iteration in result.iterations[1:]:
        r5 = iteration.evaluation_for("R5")
        assert r5.status == RuleStatus.REFRACTORY


def test_refractory_rule_not_in_conflict_set():
    result = run_forward_chaining(default_rules(), default_facts())
    for iteration in result.iterations[1:]:
        assert "R5" not in iteration.conflict_set


# ---------------------------------------------------------------------------
# Duplicate conclusions
# ---------------------------------------------------------------------------
def test_duplicate_conclusion_is_not_added_twice():
    rules = [
        Rule("R2", ["Lampu Internet Router Merah"], "Gangguan Provider", 2),
        Rule("R5", ["Perangkat Lain Juga Offline"], "Gangguan Provider", 2),
        Rule("R7", ["Gangguan Provider"], "Gunakan Tethering Sementara", 1),
    ]
    result = run_forward_chaining(
        rules,
        ["Lampu Internet Router Merah", "Perangkat Lain Juga Offline"],
    )
    # R2 fires first (lower numeric id, same salience/specificity).
    assert result.fired_rules == ["R2", "R5", "R7"]
    assert result.final_facts.count("Gangguan Provider") == 1

    # The second firing is recorded but flagged as not adding a new fact.
    r5_iteration = next(it for it in result.iterations if it.selected_rule == "R5")
    assert r5_iteration.conclusion == "Gangguan Provider"
    assert r5_iteration.conclusion_added is False


# ---------------------------------------------------------------------------
# Custom / user rules must be honoured
# ---------------------------------------------------------------------------
def test_engine_works_with_custom_rules():
    rules = [
        Rule("R1", ["A", "B"], "C", 1),
        Rule("R2", ["C"], "D", 4),
    ]
    result = run_forward_chaining(rules, ["a", "b"])
    assert result.fired_rules == ["R1", "R2"]
    assert "C" in result.final_facts
    assert "D" in result.final_facts


def test_salience_decides_between_ready_rules():
    rules = [
        Rule("R1", ["A"], "Low", 1),
        Rule("R2", ["A"], "High", 4),
    ]
    result = run_forward_chaining(rules, ["A"])
    assert result.fired_rules[0] == "R2"
    assert "High" in result.final_facts


def test_specificity_decides_when_salience_ties():
    rules = [
        Rule("R1", ["A"], "Generic", 2),
        Rule("R2", ["A", "B"], "Specific", 2),
    ]
    result = run_forward_chaining(rules, ["A", "B"])
    assert result.fired_rules[0] == "R2"


def test_numeric_rule_order_decides_ties():
    rules = [
        Rule("R10", ["A"], "Ten", 1),
        Rule("R2", ["B"], "Two", 1),
    ]
    result = run_forward_chaining(rules, ["A", "B"])
    assert result.fired_rules == ["R2", "R10"]


# ---------------------------------------------------------------------------
# R8 becomes eligible when its conditions exist
# ---------------------------------------------------------------------------
def test_r8_fires_when_router_is_hot():
    result = run_forward_chaining(
        default_rules(),
        [*default_facts(), "Router Terasa Panas"],
    )
    assert "R8" in result.fired_rules
    assert "Matikan Router 10 Menit" in result.final_facts


def test_r6_fires_when_laptop_only_fact_added():
    result = run_forward_chaining(
        default_rules(),
        [*default_facts(), "Hanya Laptop Ini Bermasalah"],
    )
    assert "R6" in result.fired_rules
    assert "Masalah pada Laptop" in result.final_facts


# ---------------------------------------------------------------------------
# Goal checking + termination data
# ---------------------------------------------------------------------------
def test_forward_goal_reports_proven():
    result = run_forward_chaining(
        default_rules(), default_facts(), goal="Lapor ke Provider"
    )
    assert result.goal_proven is True


def test_forward_goal_reports_unproven():
    result = run_forward_chaining(
        default_rules(), default_facts(), goal="Masalah pada Laptop"
    )
    assert result.goal_proven is False


def test_every_iteration_records_snapshot_and_after_state():
    result = run_forward_chaining(default_rules(), default_facts())
    for iteration in result.iterations:
        assert iteration.facts_before
        assert iteration.facts_after
    # Iteration 2 starts from iteration 1's working memory.
    assert result.iterations[1].facts_before == result.iterations[0].facts_after