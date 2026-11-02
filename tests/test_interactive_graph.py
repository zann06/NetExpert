"""Tests for the clickable Cytoscape adapters used by the interactive graph.

These tests do not require Streamlit: the element builders only depend on the
trace models.  The style helpers are optional and skipped when
``st-link-analysis`` is not installed.
"""

import pytest

from src.inference import run_backward_chaining, run_forward_chaining
from src.knowledge_base import default_facts, default_rules
from src.visualization import (
    BACKWARD_LAYOUT,
    FORWARD_LAYOUT,
    backward_elements,
    backward_summary,
    forward_iteration_elements,
    forward_summary,
)


def _forward():
    return run_forward_chaining(default_rules(), default_facts())


def test_forward_iteration_elements_expose_clickable_nodes():
    result = _forward()
    iteration = result.iterations[0]
    rules = {rule.id: rule for rule in default_rules()}
    elements, lookup = forward_iteration_elements(iteration, rules)

    node_ids = {node["data"]["id"] for node in elements["nodes"]}
    assert "snapshot" in node_ids
    assert "rule_R5" in node_ids
    assert "rule_R5_c0" in node_ids
    assert "conclusion" in node_ids

    assert lookup["snapshot"]["kind"] == "snapshot"
    assert lookup["rule_R5"]["kind"] == "rule"
    assert lookup["rule_R5"]["evaluation"].rule_id == "R5"
    assert lookup["rule_R5"]["rule"].id == "R5"
    assert lookup["rule_R5_c0"]["kind"] == "condition"
    assert lookup["conclusion"]["kind"] == "conclusion"


def test_forward_condition_groups_reflect_true_false():
    result = _forward()
    iteration = result.iterations[0]
    elements, _ = forward_iteration_elements(iteration, {})
    groups = {node["data"]["id"]: node["data"]["label"] for node in elements["nodes"]}
    assert groups["rule_R5_c0"] == "condition_true"
    assert groups["rule_R6_c1"] == "condition_false"


def test_forward_edges_connect_snapshot_rule_and_condition():
    result = _forward()
    elements, _ = forward_iteration_elements(result.iterations[0], {})
    edges = {edge["data"]["id"]: edge["data"] for edge in elements["edges"]}
    assert edges["e_snap_0"]["source"] == "snapshot"
    assert edges["e_snap_0"]["target"] == "rule_R1"
    assert edges["rule_R1_c0_edge"]["source"] == "rule_R1"
    assert edges["rule_R1_c0_edge"]["target"] == "rule_R1_c0"
    assert edges["e_conclusion"]["label"] == "conclusion"


def test_forward_stop_iteration_has_a_stop_node():
    result = _forward()
    last = result.iterations[-1]
    elements, lookup = forward_iteration_elements(last, {})
    node_ids = {node["data"]["id"] for node in elements["nodes"]}
    assert "stop" in node_ids
    assert lookup["stop"]["kind"] == "stop"


def test_forward_elements_one_iteration_at_a_time():
    result = _forward()
    first, _ = forward_iteration_elements(result.iterations[0], {})
    ids = {node["data"]["id"] for node in first["nodes"]}
    # Rule ids are not prefixed by an iteration number, so only one iteration
    # can be present at a time.
    assert "rule_R5" in ids
    assert not any(node_id.startswith("it2_") for node_id in ids)


def test_backward_elements_cover_every_node_with_a_lookup_entry():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Lapor ke Provider"
    )
    elements, lookup = backward_elements(result)
    assert len(elements["nodes"]) == len(lookup)
    assert all(entry["kind"] == "backward" for entry in lookup.values())
    # A tree with N nodes has exactly N - 1 edges.
    assert len(elements["edges"]) == len(elements["nodes"]) - 1


def test_backward_elements_include_rule_and_fact_groups():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Lapor ke Provider"
    )
    elements, _ = backward_elements(result)
    labels = {node["data"]["label"] for node in elements["nodes"]}
    assert "fact" in labels
    assert "rule_proven" in labels
    assert "rule_unproven" in labels


def test_backward_edges_carry_connector_label():
    result = run_backward_chaining(
        default_rules(), default_facts(), "Lapor ke Provider"
    )
    elements, _ = backward_elements(result)
    captions = {edge["data"]["caption"] for edge in elements["edges"]}
    assert "AND" in captions


def test_summaries_describe_the_current_graph():
    forward = _forward()
    assert "Iterasi 1" in forward_summary(forward, forward.iterations[0])
    backward = run_backward_chaining(
        default_rules(), default_facts(), "Lapor ke Provider"
    )
    assert "PROVEN" in backward_summary(backward)


def test_layouts_are_cytoscape_dagre():
    assert FORWARD_LAYOUT["name"] == "dagre"
    assert FORWARD_LAYOUT["rankDir"] == "LR"
    assert BACKWARD_LAYOUT["name"] == "dagre"
    assert BACKWARD_LAYOUT["rankDir"] == "TB"


def test_style_helpers_emit_border_and_caption_when_available():
    pytest.importorskip("st_link_analysis")
    from src.visualization import edge_styles, node_styles

    nodes = node_styles()
    edges = edge_styles()
    assert nodes and edges

    dumped = nodes[0].dump()
    assert dumped["selector"].startswith("node[label=")
    assert dumped["style"]["border-color"]
    assert dumped["style"]["shape"] == "round-rectangle"

    dumped_edge = edges[0].dump()
    assert dumped_edge["selector"].startswith("edge[label=")
    assert dumped_edge["style"]["target-arrow-shape"] == "triangle"