"""Inference tree visualisation.

The trees are generated from the *actual* inference traces returned by the
engine — nothing is hard-coded.  Each function returns a Graphviz DOT string so
the renderer stays independent of Streamlit, and Streamlit's
``st.graphviz_chart`` (which renders with Graphviz compiled to WebAssembly)
consumes the DOT string directly.

Accessibility helpers producing structured tables are provided as well, because
the PRD requires a text alternative for the graph.
"""

from __future__ import annotations

from typing import List, Optional

from ..models import (
    BackwardNode,
    BackwardResult,
    ForwardResult,
    NodeStatus,
    RuleStatus,
    salience_label,
)

# ---------------------------------------------------------------------------
# Palette (kept in sync with DESIGN_REFERENCE.md)
# ---------------------------------------------------------------------------
BLUE_FILL, BLUE_BORDER = "#EFF6FF", "#2563EB"
GREEN_FILL, GREEN_BORDER = "#F0FDF4", "#16A34A"
RED_FILL, RED_BORDER = "#FEF2F2", "#DC2626"
AMBER_FILL, AMBER_BORDER = "#FFFBEB", "#D97706"
GRAY_FILL, GRAY_BORDER = "#F1F5F9", "#94A3B8"
TEXT = "#0F172A"

FONT = "Segoe UI, Inter, Helvetica, sans-serif"

FILTER_ALL = "all"
FILTER_FIRED = "fired"
FILTER_FAILED = "failed"
FILTER_READY_NOT_SELECTED = "ready_not_selected"

FILTER_LABELS = {
    FILTER_ALL: "Semua evaluasi",
    FILTER_FIRED: "Hanya FIRED",
    FILTER_FAILED: "Kondisi gagal (NOT READY)",
    FILTER_READY_NOT_SELECTED: "READY BUT NOT SELECTED",
}


# ---------------------------------------------------------------------------
# DOT helpers
# ---------------------------------------------------------------------------
def _esc(text: str) -> str:
    """Escape a string for use inside a DOT quoted label."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


def _node(
    node_id: str,
    label: str,
    fill: str,
    border: str,
    *,
    fontcolor: str = TEXT,
    shape: str = "box",
    style: str = "rounded,filled",
    peripheries: int = 1,
    fontsize: int = 10,
) -> str:
    return (
        f'  {node_id} [label="{_esc(label)}", fillcolor="{fill}", '
        f'color="{border}", fontcolor="{fontcolor}", shape={shape}, '
        f'style="{style}", fontsize={fontsize}, peripheries={peripheries}];'
    )


def _edge(source: str, target: str, label: str = "", color: str = "#94A3B8") -> str:
    if label:
        return (
            f'  {source} -> {target} [label="{_esc(label)}", color="{color}", '
            f'fontcolor="{color}", fontsize=9];'
        )
    return f'  {source} -> {target} [color="{color}"];'


def _dot_header(graph_name: str, rankdir: str = "TB") -> List[str]:
    return [
        f"digraph {graph_name} {{",
        f'  rankdir={rankdir};',
        '  bgcolor="#FFFFFF";',
        '  compound=true;',
        f'  node [shape=box, style="rounded,filled", fontname="{FONT}", '
        f'fontsize=10, color="{GRAY_BORDER}"];',
        f'  edge [color="{GRAY_BORDER}", fontname="{FONT}", fontsize=9];',
    ]


# ---------------------------------------------------------------------------
# Forward chaining tree
# ---------------------------------------------------------------------------
def _rule_colors(status: RuleStatus):
    if status == RuleStatus.FIRED:
        return GREEN_FILL, GREEN_BORDER
    if status == RuleStatus.NOT_READY:
        return RED_FILL, RED_BORDER
    if status == RuleStatus.READY_NOT_SELECTED:
        return AMBER_FILL, AMBER_BORDER
    if status == RuleStatus.READY:
        return AMBER_FILL, AMBER_BORDER
    return GRAY_FILL, GRAY_BORDER  # REFRACTORY


def _include_rule(status: RuleStatus, filter_mode: str) -> bool:
    if filter_mode == FILTER_FIRED:
        return status == RuleStatus.FIRED
    if filter_mode == FILTER_FAILED:
        return status == RuleStatus.NOT_READY
    if filter_mode == FILTER_READY_NOT_SELECTED:
        return status == RuleStatus.READY_NOT_SELECTED
    return True


def forward_tree_dot(result: ForwardResult, filter_mode: str = FILTER_ALL) -> str:
    """Build the forward-chaining DOT graph from the recorded trace."""
    lines = _dot_header("ForwardChaining")
    lines.append("  {")
    lines.append('    rank=same;')

    root_facts = "\n".join(f"• {fact}" for fact in result.initial_facts) or "(kosong)"
    lines.append(
        _node(
            "wm_root",
            f"WORKING MEMORY AWAL\n{root_facts}",
            BLUE_FILL,
            BLUE_BORDER,
            fontsize=11,
        )
    )
    lines.append("  }")

    previous_anchor: Optional[str] = "wm_root"
    for iteration in result.iterations:
        index = iteration.iteration
        cid = f"cluster_it{index}"
        lines.append(f'  subgraph {cid} {{')
        lines.append(f'    label="ITERASI {index}";')
        lines.append('    style="rounded";')
        lines.append(f'    color="{GRAY_BORDER}";')
        lines.append(f'    fontcolor="{AMBER_BORDER}";')
        lines.append('    fontsize=11;')

        snap_id = f"it{index}_snap"
        facts_lines = "\n".join(f"• {fact}" for fact in iteration.facts_before) or "(kosong)"
        lines.append(
            _node(
                snap_id,
                f"Snapshot sebelum firing\n{facts_lines}",
                BLUE_FILL,
                BLUE_BORDER,
            )
        )
        if previous_anchor:
            lines.append(_edge(previous_anchor, snap_id, "working memory", BLUE_BORDER))

        selected_ids = {iteration.selected_rule} if iteration.selected_rule else set()

        for evaluation in iteration.evaluations:
            if not _include_rule(evaluation.status, filter_mode):
                continue

            rule_id = f"it{index}_{evaluation.rule_id}"
            fill, border = _rule_colors(evaluation.status)
            rule_label = (
                f"{evaluation.rule_id} — {evaluation.status.label}\n"
                f"salience {evaluation.salience} "
                f"({salience_label(evaluation.salience)}) · "
                f"{evaluation.specificity} kondisi · "
                f"{evaluation.connector}"
            )
            if evaluation.status == RuleStatus.FIRED:
                rule_label += "\n→ TERPILIH"
            lines.append(_node(rule_id, rule_label, fill, border, fontsize=10))
            lines.append(
                _edge(
                    snap_id,
                    rule_id,
                    "evaluasi",
                    border,
                )
            )

            for position, condition in enumerate(evaluation.condition_results):
                cond_id = f"it{index}_{evaluation.rule_id}_c{position}"
                cfill, cborder = (
                    (GREEN_FILL, GREEN_BORDER) if condition.status else (RED_FILL, RED_BORDER)
                )
                cond_label = f"{condition.condition}\n{condition.label}"
                lines.append(_node(cond_id, cond_label, cfill, cborder, fontsize=9))
                lines.append(
                    _edge(rule_id, cond_id, condition.label, cborder)
                )

            if evaluation.status == RuleStatus.FIRED and iteration.conclusion:
                concl_id = f"it{index}_conclusion"
                added = iteration.conclusion_added
                added_text = (
                    "ditambahkan ke working memory"
                    if added
                    else "sudah ada — tidak diduplikasi"
                )
                lines.append(
                    _node(
                        concl_id,
                        f"THEN\n{iteration.conclusion}\n({added_text})",
                        GREEN_FILL,
                        GREEN_BORDER,
                        fontsize=10,
                    )
                )
                lines.append(
                    _edge(rule_id, concl_id, "menghasilkan", GREEN_BORDER)
                )
                previous_anchor = concl_id

        if not iteration.selected_rule:
            stop_id = f"it{index}_stop"
            lines.append(
                _node(
                    stop_id,
                    "STOP\nConflict set kosong",
                    GRAY_FILL,
                    GRAY_BORDER,
                )
            )
            lines.append(_edge(snap_id, stop_id, "tidak ada aturan siap", GRAY_BORDER))
            previous_anchor = None

        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backward chaining tree
# ---------------------------------------------------------------------------
def _backward_colors(node: BackwardNode):
    status = node.status
    if status == NodeStatus.CYCLE:
        return AMBER_FILL, AMBER_BORDER
    if node.kind == "FACT" or status == NodeStatus.PROVEN:
        return GREEN_FILL, GREEN_BORDER
    if status == NodeStatus.UNPROVEN:
        return RED_FILL, RED_BORDER
    if status == NodeStatus.READY:
        return AMBER_FILL, AMBER_BORDER
    return GRAY_FILL, GRAY_BORDER


def _backward_label(node: BackwardNode) -> str:
    if node.kind == "GOAL":
        return f"GOAL\n{node.label}\n{node.status.value}"
    if node.kind == "FACT":
        return f"FAKTA\n{node.label}\nTRUE"
    if node.kind == "RULE":
        connector = f"\noperator {node.connector}" if node.connector else ""
        return f"{node.label}\n{node.status.value}{connector}"
    return f"{node.label}\n{node.status.value}"


def backward_tree_dot(result: BackwardResult) -> str:
    """Build the backward-chaining DOT graph from the proof tree."""
    lines = _dot_header("BackwardChaining", rankdir="TB")
    counter = {"n": 0}

    def walk(node: BackwardNode) -> str:
        node_id = f"b{counter['n']}"
        counter["n"] += 1
        fill, border = _backward_colors(node)
        shape = "box"
        peripheries = 2 if node.kind == "GOAL" else 1
        lines.append(
            _node(
                node_id,
                _backward_label(node),
                fill,
                border,
                shape=shape,
                peripheries=peripheries,
                fontsize=10,
            )
        )
        for child in node.children:
            child_id = walk(child)
            edge_label = ""
            if node.kind == "GOAL" and child.kind == "RULE":
                edge_label = "kandidat"
            elif node.kind == "RULE":
                edge_label = node.connector or "AND"
            elif node.kind == "FACT":
                edge_label = ""
            elif child.status == NodeStatus.PROVEN:
                edge_label = "PROVEN"
            elif child.status == NodeStatus.CYCLE:
                edge_label = "CYCLE"
            elif child.status == NodeStatus.UNPROVEN:
                edge_label = "UNPROVEN"
            lines.append(_edge(node_id, child_id, edge_label, border))
        return node_id

    walk(result.root)
    lines.append("}")
    return "\n".join(lines)


def legend_dot() -> str:
    """A small standalone legend graph used in the UI."""
    lines = _dot_header("Legend", rankdir="LR")
    entries = [
        ("Fakta / Working Memory", BLUE_FILL, BLUE_BORDER),
        ("TRUE / PROVEN", GREEN_FILL, GREEN_BORDER),
        ("FALSE / UNPROVEN", RED_FILL, RED_BORDER),
        ("Sedang dievaluasi / READY", AMBER_FILL, AMBER_BORDER),
        ("Refractory / netral", GRAY_FILL, GRAY_BORDER),
    ]
    for index, (label, fill, border) in enumerate(entries):
        node_id = f"legend{index}"
        lines.append(_node(node_id, label, fill, border, fontsize=10))
        if index:
            lines.append(f"  legend{index - 1} -> {node_id} [style=invis];")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Accessibility: structured table rows
# ---------------------------------------------------------------------------
def forward_condition_rows(result: ForwardResult) -> List[dict]:
    """Flat rows for every evaluated condition (text fallback for the graph)."""
    rows: List[dict] = []
    for iteration in result.iterations:
        for evaluation in iteration.evaluations:
            for condition in evaluation.condition_results:
                rows.append(
                    {
                        "Iterasi": iteration.iteration,
                        "Aturan": evaluation.rule_id,
                        "Logika": evaluation.connector,
                        "Kondisi": condition.condition,
                        "Status": condition.label,
                        "Status aturan": evaluation.status.label,
                    }
                )
    return rows


def backward_condition_rows(result: BackwardResult) -> List[dict]:
    """Flat rows describing every backward-chaining branch."""
    rows: List[dict] = []

    def walk(node: BackwardNode, path: str):
        current = f"{path} > {node.label}" if path else node.label
        rows.append(
            {
                "Jalur": current,
                "Tipe": node.kind,
                "Status": node.status.value,
                "Keterangan": node.detail,
            }
        )
        for child in node.children:
            walk(child, current)

    walk(result.root, "")
    return rows
