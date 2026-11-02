"""Forward chaining (data-driven inference).

Algorithm (matches the PRD):

1.  Initialise working memory from the selected initial facts.
2.  Initialise an empty fired-rules set (refractoriness scope = one run).
3.  Evaluate every rule that has not fired against the current snapshot.
4.  Mark each IF condition TRUE / FALSE individually.
5.  A rule is READY when its IF side is satisfied: *all* conditions TRUE
    for AND rules, or *at least one* condition TRUE for OR rules.
6.  Collect READY rules into the conflict set.
7.  If the conflict set is empty, terminate.
8.  Rank the conflict set (salience -> specificity -> numeric rule id).
9.  Select the highest priority rule and mark it FIRED.
10. Add it to the fired set (refractoriness).
11. Add the conclusion to working memory when not already present.
12. Record the full iteration trace.
13. Repeat until no eligible rules remain.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from ..models import (
    ConditionEvaluation,
    ForwardResult,
    IterationTrace,
    Rule,
    RuleEvaluation,
    RuleStatus,
)
from ..normalization import normalize
from ..working_memory import WorkingMemory
from .conflict_resolution import rank_rules, selection_reason

DEFAULT_MAX_ITERATIONS = 1000


def _evaluate_rule(
    rule: Rule, wm: WorkingMemory, iteration: int
) -> RuleEvaluation:
    """Evaluate every IF condition of ``rule`` against ``wm``."""
    condition_results: List[ConditionEvaluation] = []
    for condition in rule.conditions:
        ok = wm.contains(condition)
        explanation = (
            f"'{condition}' ditemukan di working memory."
            if ok
            else f"'{condition}' tidak ditemukan di working memory."
        )
        condition_results.append(
            ConditionEvaluation(condition=condition, status=ok, explanation=explanation)
        )

    if rule.connector == "OR":
        satisfied = any(c.status for c in condition_results)
        if satisfied:
            reason = "Minimal satu kondisi IF bernilai TRUE (operator OR)."
        else:
            reason = "Semua kondisi IF bernilai FALSE (operator OR)."
    else:
        satisfied = all(c.status for c in condition_results)
        if satisfied:
            reason = "Semua kondisi IF bernilai TRUE (operator AND)."
        else:
            missing = ", ".join(c.condition for c in condition_results if not c.status)
            reason = (
                "Minimal satu kondisi FALSE (operator AND) — "
                f"tidak tersedia: {missing}."
            )

    status = RuleStatus.READY if satisfied else RuleStatus.NOT_READY

    return RuleEvaluation(
        rule_id=rule.id,
        iteration=iteration,
        condition_results=condition_results,
        status=status,
        reason=reason,
        salience=rule.salience,
        specificity=rule.specificity,
        conclusion=rule.conclusion,
        connector=rule.connector,
    )


def run_forward_chaining(
    rules: Sequence[Rule],
    initial_facts: Iterable[str],
    goal: Optional[str] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> ForwardResult:
    """Run forward chaining and return a fully recorded trace.

    ``goal`` is optional: when supplied the result reports whether the goal
    ended up in the final working memory.
    """
    rules = list(rules)
    wm = WorkingMemory(list(initial_facts))
    initial_snapshot = wm.facts()

    fired: List[str] = []
    fired_lookup: set[str] = set()
    fired_order: List[str] = []
    iterations: List[IterationTrace] = []
    terminated_reason = "Conflict set kosong — inferensi berhenti."

    for iteration in range(1, max_iterations + 1):
        facts_before = wm.facts()

        evaluations: List[RuleEvaluation] = []
        ready_rules: List[Rule] = []

        for rule in rules:
            if rule.id in fired_lookup:
                evaluations.append(
                    RuleEvaluation(
                        rule_id=rule.id,
                        iteration=iteration,
                        condition_results=[],
                        status=RuleStatus.REFRACTORY,
                        reason=(
                            "Sudah FIRED pada eksekusi ini — dikeluarkan oleh "
                            "refractoriness."
                        ),
                        salience=rule.salience,
                        specificity=rule.specificity,
                        conclusion=rule.conclusion,
                        connector=rule.connector,
                    )
                )
                continue

            evaluation = _evaluate_rule(rule, wm, iteration)
            evaluations.append(evaluation)
            if evaluation.status == RuleStatus.READY:
                ready_rules.append(rule)

        # No ready rule -> terminate and record the final iteration.
        if not ready_rules:
            iterations.append(
                IterationTrace(
                    iteration=iteration,
                    facts_before=facts_before,
                    evaluations=evaluations,
                    conflict_set=[],
                    ranking=[],
                    selected_rule=None,
                    selection_reason="Tidak ada aturan siap — conflict set kosong.",
                    conclusion=None,
                    conclusion_added=None,
                    facts_after=wm.facts(),
                )
            )
            terminated_reason = "Conflict set kosong — inferensi berhenti."
            break

        # Rank the conflict set (refractory rules already excluded above).
        conflict_set = rank_rules(ready_rules)
        conflict_ids = [r.id for r in conflict_set]
        selected = conflict_set[0]

        # Update the recorded statuses now that we know the outcome.
        for evaluation in evaluations:
            if evaluation.rule_id == selected.id:
                evaluation.status = RuleStatus.FIRED
                evaluation.reason = "Dipilih oleh conflict resolution dan ditembakkan."
            elif evaluation.status == RuleStatus.READY:
                evaluation.status = RuleStatus.READY_NOT_SELECTED
                evaluation.reason = (
                    f"Siap jalan (kondisi IF terpenuhi) tetapi kalah conflict "
                    f"resolution dari {selected.id}."
                )

        reason = selection_reason(selected, conflict_set)

        # Refractoriness + working memory update.
        fired_lookup.add(selected.id)
        fired.append(selected.id)
        fired_order.append(selected.id)
        conclusion_added = wm.add(selected.conclusion)

        iterations.append(
            IterationTrace(
                iteration=iteration,
                facts_before=facts_before,
                evaluations=evaluations,
                conflict_set=conflict_ids,
                ranking=conflict_ids,
                selected_rule=selected.id,
                selection_reason=reason,
                conclusion=selected.conclusion,
                conclusion_added=conclusion_added,
                facts_after=wm.facts(),
            )
        )
    else:  # pragma: no cover - safety net for pathological rule sets
        terminated_reason = "Batas iterasi maksimum tercapai."

    final_facts = wm.facts()
    initial_keys = {normalize(f) for f in initial_snapshot}
    derived_facts = [
        fact for fact in final_facts if normalize(fact) not in initial_keys
    ]

    goal_proven: Optional[bool] = None
    if goal:
        goal_proven = wm.contains(goal)

    return ForwardResult(
        initial_facts=initial_snapshot,
        iterations=iterations,
        fired_rules=fired_order,
        derived_facts=derived_facts,
        final_facts=final_facts,
        goal=goal,
        goal_proven=goal_proven,
        terminated_reason=terminated_reason,
    )
