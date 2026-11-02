"""Tests for the backward-chaining engine."""

from src.inference import run_backward_chaining
from src.knowledge_base import default_facts, default_rules
from src.models import NodeStatus, Rule


def _find(node, predicate):
    if predicate(node):
        return node
    for child in node.children:
        found = _find(child, predicate)
        if found is not None:
            return found
    return None


def test_backward_chaining_proves_lapor_ke_provider():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Lapor ke Provider"
    )
    assert result.proven is True
    assert result.root.status == NodeStatus.PROVEN
    assert "R4" in result.proof_path
    assert "R5" in result.proof_path


def test_backward_chaining_uses_r4_with_two_subgoals():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Lapor ke Provider"
    )
    r4 = _find(result.root, lambda n: n.kind == "RULE" and n.label == "R4")
    assert r4 is not None
    assert r4.status == NodeStatus.PROVEN
    subgoal_labels = [child.label for child in r4.children]
    assert "Gangguan Provider" in subgoal_labels
    assert "Tagihan Sudah Dibayar" in subgoal_labels


def test_backward_chaining_shows_failed_alternatives_for_subgoal():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Lapor ke Provider"
    )
    gangguan = _find(result.root, lambda n: n.label == "Gangguan Provider" and n.kind == "GOAL")
    assert gangguan is not None
    branch_status = {child.label: child.status for child in gangguan.children}
    # R2 and R3 fail, R5 succeeds.
    assert branch_status["R2"] == NodeStatus.UNPROVEN
    assert branch_status["R3"] == NodeStatus.UNPROVEN
    assert branch_status["R5"] == NodeStatus.PROVEN


def test_backward_chaining_failure():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Masalah pada Laptop"
    )
    assert result.proven is False
    assert result.root.status == NodeStatus.UNPROVEN
    # The failing condition must remain visible.
    missing = _find(
        result.root, lambda n: n.label == "Hanya Laptop Ini Bermasalah"
    )
    assert missing is not None
    assert missing.status == NodeStatus.UNPROVEN


def test_backward_chaining_unknown_goal():
    result = run_backward_chaining(default_rules(), default_facts(), "Langit Berwarna Hijau")
    assert result.proven is False
    assert result.root.status == NodeStatus.UNPROVEN
    assert "Tidak ada aturan" in result.root.detail


def test_backward_chaining_goal_already_a_fact():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Tagihan Sudah Dibayar"
    )
    assert result.proven is True
    assert result.root.source == "FACT"


def test_cycle_detection_prevents_infinite_recursion():
    rules = [
        Rule("R1", ["B"], "A", 1),
        Rule("R2", ["A"], "B", 1),
    ]
    result = run_backward_chaining(rules, [], "A")
    assert result.proven is False
    assert result.cycle_detected is True
    cycle_node = _find(result.root, lambda n: n.status == NodeStatus.CYCLE)
    assert cycle_node is not None


def test_backward_candidate_rules_are_ranked_by_priority():
    # Two rules prove the same goal; the higher salience one should be the
    # recorded proof path, while both remain visible.
    rules = [
        Rule("R1", ["A"], "Goal", 1),
        Rule("R2", ["B"], "Goal", 4),
    ]
    result = run_backward_chaining(rules, ["A", "B"], "Goal")
    assert result.proven is True
    assert result.proof_path[0] == "R2"
    goal_node = result.root
    branch_order = [child.label for child in goal_node.children]
    assert branch_order[0] == "R2"


def test_backward_chaining_custom_chain():
    rules = [
        Rule("R1", ["A"], "B", 1),
        Rule("R2", ["B", "C"], "D", 2),
    ]
    result = run_backward_chaining(rules, ["A", "C"], "D")
    assert result.proven is True
    assert set(result.proof_path) == {"R2", "R1"}


def test_backward_requires_non_empty_goal():
    import pytest

    with pytest.raises(ValueError):
        run_backward_chaining(default_rules(), default_facts(), "   ")