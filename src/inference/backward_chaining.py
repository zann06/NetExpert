"""Backward chaining (goal-driven inference).

Algorithm (matches the PRD):

1.  Accept a goal from the user.
2.  If the goal already exists in the initial facts -> PROVEN.
3.  Otherwise find rules whose THEN matches the goal (candidate rules).
4.  Rank candidates with the same conflict resolution order.
5.  Turn each IF condition of a candidate rule into a subgoal.
6.  Recursively attempt to prove every subgoal.
7.  If *all* conditions of a candidate rule are proven, that rule proves the
    goal.
8.  If every candidate rule fails, the goal is UNPROVEN.
9.  Successful *and* failed branches are recorded (both stay visible).
10. Cycles are detected so recursion always terminates.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from ..models import BackwardNode, BackwardResult, NodeStatus, Rule, salience_label
from ..normalization import normalize
from ..working_memory import WorkingMemory
from .conflict_resolution import rank_rules

DEFAULT_MAX_DEPTH = 60
DEFAULT_MAX_NODES = 4000


class _Prover:
    def __init__(self, rules: Sequence[Rule], facts: Iterable[str], max_depth: int, max_nodes: int):
        self.rules = list(rules)
        self.wm = WorkingMemory(list(facts))
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.node_count = 0
        self.cycle_detected = False
        self.proof_path: List[str] = []
        self.log: List[str] = []

        self.by_conclusion: Dict[str, List[Rule]] = {}
        for rule in self.rules:
            self.by_conclusion.setdefault(normalize(rule.conclusion), []).append(rule)

    # -- helpers -----------------------------------------------------------
    def _candidates(self, goal: str) -> List[Rule]:
        return rank_rules(self.by_conclusion.get(normalize(goal), []))

    def _new_node(self, **kwargs) -> Optional[BackwardNode]:
        self.node_count += 1
        if self.node_count > self.max_nodes:
            return None
        return BackwardNode(**kwargs)

    # -- recursion ---------------------------------------------------------
    def prove(self, goal: str, stack: frozenset, depth: int = 0) -> BackwardNode:
        key = normalize(goal)
        node = self._new_node(label=goal, kind="GOAL", depth=depth)
        if node is None:  # node budget exhausted
            return BackwardNode(
                label=goal,
                kind="GOAL",
                depth=depth,
                status=NodeStatus.UNPROVEN,
                detail="Batas node tercapai.",
            )

        # 1. Direct fact?
        if self.wm.contains(goal):
            node.kind = "FACT"
            node.status = NodeStatus.PROVEN
            node.source = "FACT"
            node.detail = "Fakta tersedia di fakta awal / working memory."
            self.log.append(f"[PROVEN] '{goal}' tersedia sebagai fakta.")
            return node

        # 2. Cycle?
        if key in stack:
            node.status = NodeStatus.CYCLE
            node.source = "CYCLE"
            node.detail = "CYCLE DETECTED — goal ini sudah sedang dibuktikan pada jalur yang sama."
            self.cycle_detected = True
            self.log.append(f"[CYCLE]  '{goal}' terdeteksi berulang — rekursi dihentikan.")
            return node

        # 3. Depth guard.
        if depth > self.max_depth:
            node.status = NodeStatus.UNPROVEN
            node.source = "NONE"
            node.detail = "Batas kedalaman rekursi tercapai."
            self.log.append(f"[LIMIT]  '{goal}' melewati batas kedalaman.")
            return node

        # 4. Candidate rules.
        candidates = self._candidates(goal)
        if not candidates:
            node.status = NodeStatus.UNPROVEN
            node.source = "NONE"
            node.detail = "Tidak ada aturan yang menghasilkan goal ini dan goal bukan fakta."
            self.log.append(f"[UNPROVEN] '{goal}' tidak memiliki aturan pendukung.")
            return node

        next_stack = stack | {key}
        successful_branch: Optional[BackwardNode] = None

        for rule in candidates:
            branch = self._new_node(
                label=rule.id,
                kind="RULE",
                depth=depth + 1,
                rule_id=rule.id,
                detail=(
                    f"IF {' AND '.join(rule.conditions)} THEN {rule.conclusion} "
                    f"(salience {rule.salience} / {salience_label(rule.salience)}, "
                    f"{len(rule.conditions)} kondisi)"
                ),
            )
            if branch is None:
                branch = BackwardNode(
                    label=rule.id,
                    kind="RULE",
                    depth=depth + 1,
                    rule_id=rule.id,
                    status=NodeStatus.UNPROVEN,
                    detail="Batas node tercapai.",
                )
                node.children.append(branch)
                continue

            branch.status = NodeStatus.READY
            all_proven = True
            for condition in rule.conditions:
                child = self.prove(condition, next_stack, depth + 2)
                branch.children.append(child)
                if child.status != NodeStatus.PROVEN:
                    all_proven = False

            if all_proven:
                branch.status = NodeStatus.PROVEN
                self.log.append(
                    f"[PROVEN] '{goal}' dibuktikan melalui {rule.id} "
                    f"(semua kondisi terpenuhi)."
                )
            else:
                branch.status = NodeStatus.UNPROVEN
                failed = [c.label for c in branch.children if c.status != NodeStatus.PROVEN]
                self.log.append(
                    f"[FAILED]  {rule.id} gagal membuktikan '{goal}' "
                    f"(kondisi gagal: {', '.join(failed)})."
                )

            node.children.append(branch)

            # Keep the first successful branch as the winning proof path, but
            # continue so alternative (failed) branches stay visible.
            if all_proven and successful_branch is None:
                successful_branch = branch

        if successful_branch is not None:
            node.status = NodeStatus.PROVEN
            node.source = "RULE"
            node.rule_id = successful_branch.rule_id
            node.detail = f"Dibuktikan melalui {successful_branch.rule_id}."
            if successful_branch.rule_id not in self.proof_path:
                self.proof_path.append(successful_branch.rule_id)
        else:
            node.status = NodeStatus.UNPROVEN
            node.source = "NONE"
            node.detail = "Semua aturan kandidat gagal membuktikan goal."
            self.log.append(f"[UNPROVEN] '{goal}' gagal — tidak ada kandidat yang berhasil.")

        return node


def run_backward_chaining(
    rules: Sequence[Rule],
    initial_facts: Iterable[str],
    goal: str,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> BackwardResult:
    """Prove ``goal`` using backward chaining and return the proof tree."""
    if not goal or not goal.strip():
        raise ValueError("Goal tidak boleh kosong untuk backward chaining.")

    prover = _Prover(rules, initial_facts, max_depth, max_nodes)
    root = prover.prove(goal, frozenset(), depth=0)
    proven = root.status == NodeStatus.PROVEN

    return BackwardResult(
        goal=goal,
        proven=proven,
        root=root,
        initial_facts=prover.wm.facts(),
        proof_path=prover.proof_path,
        cycle_detected=prover.cycle_detected,
        log=prover.log,
        terminated_reason=(
            "Goal terbukti." if proven else "Goal tidak dapat dibuktikan."
        ),
    )
