"""Adapters that turn inference traces into clickable Cytoscape elements.

The static :mod:`inference_tree` module still produces Graphviz DOT for the
detailed/export view.  This module produces the data consumed by
``st-link-analysis`` so a node click can be sent back to Streamlit.

The module only depends on the trace models.  Streamlit itself is imported by
the UI layer, keeping the adapter unit-testable.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..models import (
    BackwardNode,
    BackwardResult,
    ForwardResult,
    IterationTrace,
    NodeStatus,
    Rule,
    RuleStatus,
    salience_label,
)

# ---------------------------------------------------------------------------
# Palette (same semantic colours as the DOT renderer)
# ---------------------------------------------------------------------------
BLUE_FILL, BLUE_BORDER = "#EFF6FF", "#2563EB"
GREEN_FILL, GREEN_BORDER = "#F0FDF4", "#16A34A"
RED_FILL, RED_BORDER = "#FEF2F2", "#DC2626"
AMBER_FILL, AMBER_BORDER = "#FFFBEB", "#D97706"
GRAY_FILL, GRAY_BORDER = "#F1F5F9", "#94A3B8"

TEXT = "#0F172A"
MUTED = "#64748B"

# Node style groups: name -> (fill, border, width, height, font size)
NODE_GROUPS = {
    "wm": (BLUE_FILL, BLUE_BORDER, 200, 68, 10),
    "snapshot": (BLUE_FILL, BLUE_BORDER, 200, 68, 10),
    "iteration": (GRAY_FILL, GRAY_BORDER, 120, 34, 10),
    "fired": (GREEN_FILL, GREEN_BORDER, 160, 42, 10),
    "not_ready": (RED_FILL, RED_BORDER, 160, 42, 10),
    "ready_not_selected": (AMBER_FILL, AMBER_BORDER, 160, 42, 10),
    "ready": (AMBER_FILL, AMBER_BORDER, 160, 42, 10),
    "refractory": (GRAY_FILL, GRAY_BORDER, 160, 42, 10),
    "condition_true": (GREEN_FILL, GREEN_BORDER, 180, 50, 10),
    "condition_false": (RED_FILL, RED_BORDER, 180, 50, 10),
    "conclusion": (GREEN_FILL, GREEN_BORDER, 190, 48, 10),
    "stop": (GRAY_FILL, GRAY_BORDER, 130, 36, 10),
    "goal_proven": (GREEN_FILL, GREEN_BORDER, 200, 58, 10),
    "goal_unproven": (RED_FILL, RED_BORDER, 200, 58, 10),
    "fact": (GREEN_FILL, GREEN_BORDER, 190, 48, 10),
    "rule_proven": (GREEN_FILL, GREEN_BORDER, 130, 40, 10),
    "rule_unproven": (RED_FILL, RED_BORDER, 130, 40, 10),
    "rule_ready": (AMBER_FILL, AMBER_BORDER, 130, 40, 10),
    "cycle": (AMBER_FILL, AMBER_BORDER, 170, 42, 10),
}

EDGE_GROUPS = {
    "flow": "#94A3B8",
    "true": GREEN_BORDER,
    "false": RED_BORDER,
    "conclusion": GREEN_BORDER,
    "candidate": "#94A3B8",
    "proven": GREEN_BORDER,
    "unproven": RED_BORDER,
    "cycle": AMBER_BORDER,
}

# Standard Cytoscape layout used by every interactive graph.
FORWARD_LAYOUT = {
    "name": "dagre",
    "rankDir": "LR",
    "rankSep": 60,
    "nodeSep": 8,
    "edgeSep": 4,
    "animate": False,
    "fit": True,
    "padding": 16,
    "nodeDimensionsIncludeLabels": True,
}

BACKWARD_LAYOUT = {
    "name": "dagre",
    "rankDir": "TB",
    "rankSep": 50,
    "nodeSep": 10,
    "edgeSep": 4,
    "animate": False,
    "fit": True,
    "padding": 16,
    "nodeDimensionsIncludeLabels": True,
}


# ---------------------------------------------------------------------------
# Element helpers
# ---------------------------------------------------------------------------
def _node(node_id: str, group: str, name: str, **extra) -> dict:
    data = {"id": node_id, "label": group, "name": name}
    data.update(extra)
    return {"data": data}


def _edge(edge_id: str, source: str, target: str, group: str, label: str = "") -> dict:
    return {
        "data": {
            "id": edge_id,
            "source": source,
            "target": target,
            "label": group,
            "caption": label,
        }
    }


def _forward_group(status: RuleStatus) -> str:
    return {
        RuleStatus.FIRED: "fired",
        RuleStatus.NOT_READY: "not_ready",
        RuleStatus.READY_NOT_SELECTED: "ready_not_selected",
        RuleStatus.READY: "ready",
        RuleStatus.REFRACTORY: "refractory",
    }.get(status, "refractory")


# ---------------------------------------------------------------------------
# Forward chaining: one iteration at a time (keeps the graph readable)
# ---------------------------------------------------------------------------
def forward_iteration_elements(
    iteration: IterationTrace,
    rules: Optional[Dict[str, Rule]] = None,
) -> Tuple[dict, Dict[str, dict]]:
    """Build clickable elements for a single forward-chaining iteration.

    Returns ``(elements, lookup)`` where ``lookup`` maps a node id to the
    trace object that should be shown when the node is clicked.
    """
    rules = rules or {}
    nodes: List[dict] = []
    edges: List[dict] = []
    lookup: Dict[str, dict] = {}

    facts = iteration.facts_before or []
    snapshot_name = "Working memory\n" + (
        "\n".join(f"• {fact}" for fact in facts) if facts else "(kosong)"
    )
    nodes.append(_node("snapshot", "snapshot", snapshot_name))
    lookup["snapshot"] = {"kind": "snapshot", "iteration": iteration}

    for position, evaluation in enumerate(iteration.evaluations):
        rule_key = f"rule_{evaluation.rule_id}"
        status_group = _forward_group(evaluation.status)
        nodes.append(
            _node(
                rule_key,
                status_group,
                f"{evaluation.rule_id}\n{evaluation.status.label}",
                rule_id=evaluation.rule_id,
            )
        )
        edges.append(
            _edge(f"e_snap_{position}", "snapshot", rule_key, "flow", "evaluasi")
        )
        lookup[rule_key] = {
            "kind": "rule",
            "evaluation": evaluation,
            "rule": rules.get(evaluation.rule_id),
            "iteration": iteration,
        }

        for cond_position, condition in enumerate(evaluation.condition_results):
            cond_key = f"{rule_key}_c{cond_position}"
            cond_group = (
                "condition_true" if condition.status else "condition_false"
            )
            nodes.append(
                _node(
                    cond_key,
                    cond_group,
                    f"{condition.condition}\n{condition.label}",
                )
            )
            edge_group = "true" if condition.status else "false"
            edges.append(
                _edge(
                    f"{cond_key}_edge",
                    rule_key,
                    cond_key,
                    edge_group,
                    condition.label,
                )
            )
            lookup[cond_key] = {
                "kind": "condition",
                "evaluation": evaluation,
                "condition": condition,
                "rule": rules.get(evaluation.rule_id),
                "iteration": iteration,
            }

        if evaluation.status == RuleStatus.FIRED and iteration.conclusion:
            nodes.append(
                _node(
                    "conclusion",
                    "conclusion",
                    f"THEN\n{iteration.conclusion}",
                )
            )
            edges.append(
                _edge(
                    "e_conclusion",
                    rule_key,
                    "conclusion",
                    "conclusion",
                    "menghasilkan",
                )
            )
            lookup["conclusion"] = {
                "kind": "conclusion",
                "iteration": iteration,
                "evaluation": evaluation,
            }

    if not iteration.selected_rule:
        nodes.append(_node("stop", "stop", "STOP\nConflict set kosong"))
        edges.append(
            _edge("e_stop", "snapshot", "stop", "flow", "tidak ada aturan siap")
        )
        lookup["stop"] = {"kind": "stop", "iteration": iteration}

    return {"nodes": nodes, "edges": edges}, lookup


# ---------------------------------------------------------------------------
# Backward chaining: the whole proof tree
# ---------------------------------------------------------------------------
def _backward_group(node: BackwardNode) -> str:
    if node.status == NodeStatus.CYCLE:
        return "cycle"
    if node.kind == "FACT":
        return "fact"
    if node.kind == "RULE":
        if node.status == NodeStatus.PROVEN:
            return "rule_proven"
        if node.status == NodeStatus.UNPROVEN:
            return "rule_unproven"
        return "rule_ready"
    if node.status == NodeStatus.PROVEN:
        return "goal_proven"
    if node.status == NodeStatus.UNPROVEN:
        return "goal_unproven"
    return "goal_proven"


def _backward_name(node: BackwardNode) -> str:
    if node.kind == "GOAL":
        return f"GOAL\n{node.label}\n{node.status.value}"
    if node.kind == "FACT":
        return f"FAKTA\n{node.label}\nTRUE"
    if node.kind == "RULE":
        connector = f"\noperator {node.connector}" if node.connector else ""
        return f"{node.label}\n{node.status.value}{connector}"
    return f"{node.label}\n{node.status.value}"


def backward_elements(
    result: BackwardResult,
) -> Tuple[dict, Dict[str, dict]]:
    """Build clickable elements for the whole backward proof tree."""
    nodes: List[dict] = []
    edges: List[dict] = []
    lookup: Dict[str, dict] = {}
    counter = {"n": 0}

    def walk(node: BackwardNode) -> str:
        node_id = f"b{counter['n']}"
        counter["n"] += 1
        nodes.append(_node(node_id, _backward_group(node), _backward_name(node)))
        lookup[node_id] = {"kind": "backward", "node": node}

        for child in node.children:
            child_id = walk(child)
            if node.kind == "GOAL" and child.kind == "RULE":
                edge_group, label = "candidate", "kandidat"
            elif node.kind == "RULE":
                edge_group = "proven"
                label = node.connector or "AND"
            elif child.status == NodeStatus.PROVEN:
                edge_group, label = "proven", "PROVEN"
            elif child.status == NodeStatus.CYCLE:
                edge_group, label = "cycle", "CYCLE"
            else:
                edge_group, label = "unproven", "UNPROVEN"
            edges.append(
                _edge(f"{node_id}_{child_id}", node_id, child_id, edge_group, label)
            )
        return node_id

    walk(result.root)
    return {"nodes": nodes, "edges": edges}, lookup


# ---------------------------------------------------------------------------
# Cytoscape styles (kept here so the UI does not duplicate palette knowledge)
# ---------------------------------------------------------------------------
def node_styles():
    """Return ``st_link_analysis`` NodeStyle objects for every node group."""
    from st_link_analysis import NodeStyle

    class _StyledNode(NodeStyle):
        def __init__(self, group: str):
            fill, border, width, height, font_size = NODE_GROUPS[group]
            super().__init__(group, color=fill, caption="name")
            self._border = border
            self._width = width
            self._height = height
            self._font_size = font_size

        def dump(self) -> dict:
            data = super().dump()
            data["style"].update(
                {
                    "shape": "round-rectangle",
                    "width": self._width,
                    "height": self._height,
                    "border-width": 1.5,
                    "border-color": self._border,
                    "color": TEXT,
                    "font-size": self._font_size,
                    "font-family": "Inter",
                    "text-valign": "center",
                    "text-halign": "center",
                    "text-wrap": "wrap",
                    "text-max-width": self._width - 20,
                    "padding": 6,
                }
            )
            return data

    return [_StyledNode(group) for group in NODE_GROUPS]


def edge_styles():
    """Return ``st_link_analysis`` EdgeStyle objects for every edge group."""
    from st_link_analysis import EdgeStyle

    class _StyledEdge(EdgeStyle):
        def __init__(self, group: str, color: str):
            super().__init__(
                group,
                color=color,
                caption="caption",
                directed=True,
                labeled=None,
            )

        def dump(self) -> dict:
            data = super().dump()
            data["style"].update(
                {
                    "width": 1.3,
                    "curve-style": "bezier",
                    "font-size": 8,
                    "color": MUTED,
                    "text-background-color": "#FFFFFF",
                    "text-background-opacity": 0.92,
                    "text-background-padding": "2px",
                }
            )
            return data

    return [_StyledEdge(group, color) for group, color in EDGE_GROUPS.items()]


def forward_summary(result: ForwardResult, iteration: IterationTrace) -> str:
    """Short caption shown above the interactive forward graph."""
    if iteration.selected_rule:
        return (
            f"Iterasi {iteration.iteration}: {iteration.selected_rule} terpilih "
            f"dari conflict set {{{', '.join(iteration.conflict_set)}}}."
        )
    return f"Iterasi {iteration.iteration}: conflict set kosong — inferensi berhenti."


def backward_summary(result: BackwardResult) -> str:
    status = "PROVEN" if result.proven else "UNPROVEN"
    return (
        f"Goal '{result.goal}' {status} · proof path "
        f"{' → '.join(result.proof_path) if result.proof_path else '—'}."
    )


__all__ = [
    "NODE_GROUPS",
    "EDGE_GROUPS",
    "FORWARD_LAYOUT",
    "BACKWARD_LAYOUT",
    "forward_iteration_elements",
    "backward_elements",
    "node_styles",
    "edge_styles",
    "forward_summary",
    "backward_summary",
]