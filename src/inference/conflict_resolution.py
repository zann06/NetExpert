"""Conflict resolution for the NetExpert inference engine.

Priority order (mandatory):

1. **Salience**     — higher value wins.
2. **Specificity**  — when salience ties, the rule with more IF conditions wins.
3. **Rule number**  — when salience and specificity tie, the lower numeric rule
   id wins (``R2`` before ``R10``; ids are compared numerically, not
   alphabetically).

Refractoriness is enforced by the caller (forward chaining) through the
``exclude`` set: rules that already fired are removed from the conflict set for
the remainder of the run.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

from ..models import Rule, salience_label

_NUMBER_RE = re.compile(r"(\d+)")


def rule_number(rule_id: str) -> int:
    """Extract the numeric component of a rule id.

    ``"R2" -> 2``, ``"R10" -> 10``.  Ids without a number sort last.  The
    numeric comparison is what makes ``R2`` come before ``R10``.
    """
    match = _NUMBER_RE.search(rule_id or "")
    if not match:
        return 10**9
    return int(match.group(1))


def sort_key(rule: Rule) -> Tuple[int, int, int, str]:
    """Sort key implementing the three-level conflict resolution order."""
    return (
        -int(rule.salience),      # 1. salience descending
        -len(rule.conditions),    # 2. specificity descending
        rule_number(rule.id),     # 3. numeric rule id ascending
        (rule.id or "").casefold(),
    )


def rank_rules(rules: Iterable[Rule]) -> List[Rule]:
    """Return the rules ordered by conflict-resolution priority."""
    return sorted(rules, key=sort_key)


def build_conflict_set(
    rules: Iterable[Rule], exclude: Iterable[str] | None = None
) -> List[Rule]:
    """Return ready rules minus ``exclude`` (refractory rules), ranked.

    ``exclude`` is normally the set of rule ids that already fired during the
    current run.
    """
    excluded = {str(item).casefold().strip() for item in (exclude or [])}
    candidates = [r for r in rules if r.id.casefold().strip() not in excluded]
    return rank_rules(candidates)


def selection_reason(selected: Rule, conflict_set: Sequence[Rule]) -> str:
    """Explain why ``selected`` won the conflict set."""
    others = [r for r in conflict_set if r.id != selected.id]
    base = (
        f"{selected.id} dipilih: salience {selected.salience} "
        f"({salience_label(selected.salience)}) dengan {selected.specificity} kondisi."
    )
    if not others:
        return base + " Hanya aturan ini yang siap pada iterasi ini."

    tie_reasons = []
    for other in others:
        if other.salience != selected.salience:
            tie_reasons.append(
                f"salience lebih tinggi dari {other.id} ({other.salience})"
            )
        elif other.specificity != selected.specificity:
            tie_reasons.append(
                f"spesifisitas lebih tinggi dari {other.id} "
                f"({selected.specificity} vs {other.specificity} kondisi)"
            )
        else:
            tie_reasons.append(
                f"nomor aturan lebih kecil dari {other.id} "
                f"({rule_number(selected.id)} vs {rule_number(other.id)})"
            )
    return base + " Menang karena " + "; ".join(tie_reasons) + "."


def describe_ranking(conflict_set: Sequence[Rule]) -> List[dict]:
    """Return ranking rows for the UI (position, rule metadata, reason)."""
    rows: List[dict] = []
    for position, rule in enumerate(conflict_set, start=1):
        reasons: List[str] = []
        if position == 1:
            reasons.append("Peringkat 1 — aturan terpilih")
        else:
            prev = conflict_set[position - 2]
            if rule.salience != prev.salience:
                reasons.append(f"salience {rule.salience} < {prev.salience}")
            elif rule.specificity != prev.specificity:
                reasons.append(
                    f"spesifisitas {rule.specificity} < {prev.specificity}"
                )
            else:
                reasons.append(
                    f"nomor aturan {rule_number(rule.id)} > {rule_number(prev.id)}"
                )
        rows.append(
            {
                "peringkat": position,
                "id": rule.id,
                "salience": rule.salience,
                "salience_label": salience_label(rule.salience),
                "specificity": rule.specificity,
                "rule_number": rule_number(rule.id),
                "reason": "; ".join(reasons),
            }
        )
    return rows
