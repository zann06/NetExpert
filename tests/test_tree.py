"""Tests for the inference-tree renderer and its consistency with the trace."""

from src.inference import run_backward_chaining, run_forward_chaining
from src.knowledge_base import default_facts, default_rules
from src.visualization import (
    FILTER_FAILED,
    FILTER_FIRED,
    FILTER_READY_NOT_SELECTED,
    backward_condition_rows,
    backward_tree_dot,
    forward_condition_rows,
    forward_tree_dot,
)


def _forward_result():
    return run_forward_chaining(default_rules(), default_facts())


def test_forward_tree_contains_every_iteration():
    result = _forward_result()
    dot = forward_tree_dot(result)
    for iteration in result.iterations:
        assert f"ITERASI {iteration.iteration}" in dot
    assert dot.strip().startswith("digraph")
    assert dot.strip().endswith("}")


def test_forward_tree_contains_true_and_false_labels():
    dot = forward_tree_dot(_forward_result())
    assert "TRUE" in dot
    assert "FALSE" in dot


def test_forward_tree_contains_failed_rule_r6_and_r8():
    dot = forward_tree_dot(_forward_result())
    assert "R6 — NOT READY" in dot
    assert "R8 — NOT READY" in dot


def test_forward_tree_distinguishes_ready_but_not_selected():
    dot = forward_tree_dot(_forward_result())
    assert "READY BUT NOT SELECTED" in dot
    assert "FIRED" in dot
    assert "REFRACTORY" in dot


def test_forward_tree_condition_count_matches_trace():
    result = _forward_result()
    expected = sum(
        len(ev.condition_results)
        for it in result.iterations
        for ev in it.evaluations
    )
    rows = forward_condition_rows(result)
    assert len(rows) == expected
    assert all(row["Status"] in {"TRUE", "FALSE"} for row in rows)


def test_fired_filter_only_contains_fired_rules():
    dot = forward_tree_dot(_forward_result(), FILTER_FIRED)
    assert "R5 — FIRED" in dot
    assert "R6 — NOT READY" not in dot


def test_failed_filter_only_contains_not_ready_rules():
    dot = forward_tree_dot(_forward_result(), FILTER_FAILED)
    assert "R6 — NOT READY" in dot
    assert "R5 — FIRED" not in dot


def test_ready_not_selected_filter():
    dot = forward_tree_dot(_forward_result(), FILTER_READY_NOT_SELECTED)
    assert "READY BUT NOT SELECTED" in dot
    assert "R6 — NOT READY" not in dot


def test_forward_tree_selected_rules_match_trace():
    result = _forward_result()
    dot = forward_tree_dot(result)
    selected = {it.selected_rule for it in result.iterations if it.selected_rule}
    for rule_id in selected:
        assert f"{rule_id} — FIRED" in dot
    assert selected == set(result.fired_rules)


def test_backward_tree_contains_root_goal_and_statuses():
    result = run_backward_chaining(default_rules(), default_facts(), "Lapor ke Provider")
    dot = backward_tree_dot(result)
    assert "Lapor ke Provider" in dot
    assert "PROVEN" in dot
    assert "UNPROVEN" in dot
    assert "R4" in dot
    assert "R5" in dot


def test_backward_tree_keeps_failed_alternatives():
    result = run_backward_chaining(default_rules(), default_facts(), "Lapor ke Provider")
    dot = backward_tree_dot(result)
    assert "R2" in dot
    assert "R3" in dot


def test_backward_tree_marks_cycle():
    from src.models import Rule

    rules = [
        Rule("R1", ["B"], "A", 1),
        Rule("R2", ["A"], "B", 1),
    ]
    result = run_backward_chaining(rules, [], "A")
    dot = backward_tree_dot(result)
    assert "CYCLE" in dot


def test_backward_rows_match_tree_node_count():
    result = run_backward_chaining(default_rules(), default_facts(), "Lapor ke Provider")
    rows = backward_condition_rows(result)
    node_count = 0

    def count(node):
        nonlocal node_count
        node_count += 1
        for child in node.children:
            count(child)

    count(result.root)
    assert len(rows) == node_count