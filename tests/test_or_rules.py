"""Tests for AND/OR rule connectors and their effects on the traces.

The default assignment dataset must remain AND-only and behaviour-identical;
OR is an *additive* feature usable through the Knowledge Base page or the
engine API.
"""

from src.inference import run_backward_chaining, run_forward_chaining
from src.knowledge_base import KnowledgeBase, default_facts, default_rules
from src.models import SUPPORTED_CONNECTORS, NodeStatus, Rule, RuleStatus
from src.validation import validate_connector, validate_rule
from src.visualization import backward_tree_dot, forward_tree_dot


def _find(node, predicate):
    if predicate(node):
        return node
    for child in node.children:
        found = _find(child, predicate)
        if found is not None:
            return found
    return None


# ---------------------------------------------------------------------------
# Model + validation
# ---------------------------------------------------------------------------
def test_default_rules_are_and_only():
    assert all(rule.connector == "AND" for rule in default_rules())


def test_default_dataset_behaviour_is_unchanged():
    result = run_forward_chaining(default_rules(), default_facts())
    assert result.fired_rules == ["R5", "R4", "R1", "R7"]


def test_supported_connectors():
    assert SUPPORTED_CONNECTORS == ("AND", "OR")


def test_connector_is_normalised_and_safe():
    assert Rule("R1", ["A"], "B", 1, connector="or").connector == "OR"
    assert Rule("R1", ["A"], "B", 1, connector="  and ").connector == "AND"
    # Unknown values fall back to the assignment default.
    assert Rule("R1", ["A"], "B", 1, connector="xor").connector == "AND"
    assert Rule("R1", ["A"], "B", 1).connector == "AND"


def test_joined_conditions_uses_connector():
    assert Rule("R1", ["A", "B"], "C", 1).joined_conditions == "A AND B"
    assert (
        Rule("R1", ["A", "B"], "C", 1, connector="OR").joined_conditions
        == "A OR B"
    )


def test_rule_dict_round_trip_keeps_connector():
    rule = Rule("R1", ["A", "B"], "C", 2, connector="OR")
    restored = Rule.from_dict(rule.to_dict())
    assert restored.connector == "OR"
    assert restored.joined_conditions == "A OR B"


def test_validate_connector():
    assert validate_connector("AND") is None
    assert validate_connector("or") is None
    assert validate_connector("XOR") is not None
    assert validate_connector("") is not None


def test_validate_rule_flags_bad_connector():
    rule = Rule("R9", ["A"], "B", 1, connector="AND")
    # Rule normalises the connector, so fabricate an invalid one explicitly.
    rule.connector = "XOR"
    errors = validate_rule(rule, [])
    assert any("AND atau OR" in error for error in errors)


def test_knowledge_base_accepts_an_or_rule(kb):
    errors = kb.add(Rule("R9", ["A", "B"], "C", 2, connector="OR"))
    assert errors == []
    assert kb.get("R9").connector == "OR"


# ---------------------------------------------------------------------------
# Forward chaining with OR
# ---------------------------------------------------------------------------
def test_or_rule_fires_when_one_condition_true():
    rules = [Rule("R1", ["A", "B"], "C", 1, connector="OR")]
    result = run_forward_chaining(rules, ["A"])
    first = result.iterations[0]
    evaluation = first.evaluation_for("R1")
    assert evaluation.status == RuleStatus.FIRED
    assert evaluation.satisfied is True
    assert first.selected_rule == "R1"
    assert "C" in result.final_facts


def test_or_rule_not_ready_when_all_conditions_false():
    rules = [Rule("R1", ["A", "B"], "C", 1, connector="OR")]
    result = run_forward_chaining(rules, ["Z"])
    evaluation = result.iterations[0].evaluation_for("R1")
    assert evaluation.status == RuleStatus.NOT_READY
    assert evaluation.satisfied is False
    assert "C" not in result.final_facts


def test_or_rule_marks_each_untouched_condition_true_false():
    rules = [Rule("R1", ["A", "B", "C"], "D", 1, connector="OR")]
    result = run_forward_chaining(rules, ["B"])
    evaluation = result.iterations[0].evaluation_for("R1")
    assert [c.status for c in evaluation.condition_results] == [False, True, False]
    assert evaluation.satisfied is True


def test_and_rule_still_requires_every_condition():
    rules = [Rule("R1", ["A", "B"], "C", 1, connector="AND")]
    result = run_forward_chaining(rules, ["A"])
    assert result.iterations[0].evaluation_for("R1").status == RuleStatus.NOT_READY


# ---------------------------------------------------------------------------
# Backward chaining with OR
# ---------------------------------------------------------------------------
def test_backward_or_rule_proven_with_one_subgoal():
    rules = [
        Rule(
            "R1",
            ["Gangguan Provider", "Ping Gagal"],
            "Masalah Jaringan",
            1,
            connector="OR",
        )
    ]
    result = run_backward_chaining(rules, ["Ping Gagal"], "Masalah Jaringan")
    assert result.proven is True
    assert result.root.status == NodeStatus.PROVEN
    assert "R1" in result.proof_path

    rule_node = _find(result.root, lambda n: n.kind == "RULE" and n.label == "R1")
    assert rule_node.connector == "OR"
    assert rule_node.status == NodeStatus.PROVEN
    statuses = {child.label: child.status for child in rule_node.children}
    assert statuses["Ping Gagal"] == NodeStatus.PROVEN
    assert statuses["Gangguan Provider"] == NodeStatus.UNPROVEN


def test_backward_or_rule_unproven_when_all_subgoals_fail():
    rules = [
        Rule("R1", ["Fakta X", "Fakta Y"], "Goal", 1, connector="OR")
    ]
    result = run_backward_chaining(rules, [], "Goal")
    assert result.proven is False
    rule_node = _find(result.root, lambda n: n.kind == "RULE" and n.label == "R1")
    assert rule_node.status == NodeStatus.UNPROVEN


def test_backward_and_rule_unproven_with_one_subgoal():
    rules = [
        Rule("R1", ["Fakta X", "Fakta Y"], "Goal", 1, connector="AND")
    ]
    result = run_backward_chaining(rules, ["Fakta X"], "Goal")
    assert result.proven is False
    rule_node = _find(result.root, lambda n: n.kind == "RULE" and n.label == "R1")
    assert rule_node.status == NodeStatus.UNPROVEN


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def test_forward_tree_renders_connector_for_or_rule():
    rules = [Rule("R1", ["A", "B"], "C", 1, connector="OR")]
    result = run_forward_chaining(rules, ["A"])
    dot = forward_tree_dot(result)
    assert "kondisi · OR" in dot


def test_backward_tree_renders_or_edge_label():
    rules = [
        Rule("R1", ["Gangguan Provider", "Ping Gagal"], "Masalah Jaringan", 1, connector="OR")
    ]
    result = run_backward_chaining(rules, ["Ping Gagal"], "Masalah Jaringan")
    dot = backward_tree_dot(result)
    assert "operator OR" in dot
    assert '"OR"' in dot
