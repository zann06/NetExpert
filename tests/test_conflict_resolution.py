"""Tests for the three-level conflict resolution order."""

from src.inference.conflict_resolution import (
    build_conflict_set,
    describe_ranking,
    rank_rules,
    rule_number,
    selection_reason,
)
from src.models import Rule


def test_rule_number_is_numeric_not_alphabetic():
    assert rule_number("R2") == 2
    assert rule_number("R10") == 10
    assert rule_number("rule-007") == 7
    assert rule_number("alpha") == 10**9


def test_salience_priority():
    low = Rule("R1", ["A"], "X", 1)
    high = Rule("R2", ["A"], "Y", 3)
    ranked = rank_rules([low, high])
    assert [r.id for r in ranked] == ["R2", "R1"]


def test_specificity_priority_when_salience_ties():
    generic = Rule("R1", ["A"], "X", 2)
    specific = Rule("R2", ["A", "B"], "Y", 2)
    ranked = rank_rules([generic, specific])
    assert [r.id for r in ranked] == ["R2", "R1"]


def test_numeric_rule_id_priority_when_salience_and_specificity_tie():
    r10 = Rule("R10", ["A"], "X", 1)
    r2 = Rule("R2", ["B"], "Y", 1)
    ranked = rank_rules([r10, r2])
    assert [r.id for r in ranked] == ["R2", "R10"]


def test_full_order_salience_then_specificity_then_number():
    rules = [
        Rule("R1", ["A"], "X", 1),
        Rule("R10", ["A"], "X", 1),
        Rule("R2", ["A", "B"], "X", 1),
        Rule("R3", ["A"], "X", 3),
        Rule("R4", ["A", "B", "C"], "X", 3),
    ]
    ranked = rank_rules(rules)
    # salience 3 first (specific 3 conditions before 1), then salience 1
    # (2 conditions first, then R1 before R10).
    assert [r.id for r in ranked] == ["R4", "R3", "R2", "R1", "R10"]


def test_build_conflict_set_excludes_refractory_rules():
    a = Rule("R1", ["A"], "X", 2)
    b = Rule("R2", ["A"], "Y", 1)
    result = build_conflict_set([a, b], exclude={"R1"})
    assert [r.id for r in result] == ["R2"]


def test_selection_reason_mentions_priority_basis():
    winner = Rule("R5", ["A"], "X", 2)
    loser = Rule("R1", ["A"], "Y", 1)
    reason = selection_reason(winner, [winner, loser])
    assert "R5" in reason
    assert "salience" in reason


def test_describe_ranking_rows_are_ordered():
    rules = rank_rules(
        [
            Rule("R1", ["A"], "X", 1),
            Rule("R5", ["A"], "Y", 3),
        ]
    )
    rows = describe_ranking(rules)
    assert rows[0]["peringkat"] == 1
    assert rows[0]["id"] == "R5"
    assert rows[1]["id"] == "R1"