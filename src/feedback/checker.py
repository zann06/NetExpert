"""Deterministic comparison between a student's answer and the engine trace.

The checker re-runs forward chaining on the *current* knowledge base and
initial facts, then compares each claimed iteration with the real trace:

* **conflict set** — the READY rules of that iteration (after refraction);
* **selected rule** — the winner of salience -> specificity -> rule number;
* **conclusion** — the fired rule's THEN part.

Every mismatch produces an :class:`~src.feedback.models.Issue` whose
explanation cites the concrete criterion (salience value, condition count, or
numeric rule id), so the student learns *why* a step is wrong, not just *that*
it is wrong.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..inference import run_forward_chaining
from ..inference.conflict_resolution import rule_number
from ..models import ForwardResult, Rule
from ..normalization import normalize
from .models import FieldCheck, FeedbackReport, Issue, SubmittedIteration, SubmittedIterations


def _format_ids(ids: Optional[List[str]]) -> str:
    if not ids:
        return "— (kosong)"
    return ", ".join(ids)


def _explain_selection(selected: Rule, conflict_set: List[Rule]) -> str:
    """Explain why ``selected`` wins over every other ready rule."""
    reasons = []
    for other in conflict_set:
        if other.id == selected.id:
            continue
        if other.salience != selected.salience:
            reasons.append(
                f"salience {selected.id}={selected.salience} > {other.id}={other.salience}"
            )
        elif other.specificity != selected.specificity:
            reasons.append(
                f"spesifisitas {selected.id}={selected.specificity} kondisi "
                f"> {other.id}={other.specificity} kondisi"
            )
        else:
            reasons.append(
                f"nomor aturan {selected.id}={rule_number(selected.id)} "
                f"< {other.id}={rule_number(other.id)}"
            )
    return (
        f"{selected.id} menang conflict resolution: "
        + ("; ".join(reasons) if reasons else "satu-satunya aturan yang siap.")
    )


def _compare_conflict_set(
    claimed: List[str], actual_ids: List[str]
) -> FieldCheck:
    claimed_norm = [normalize(c) for c in claimed if normalize(c)]
    actual_norm = [normalize(a) for a in actual_ids]
    ok = claimed_norm == actual_norm
    claim_text = _format_ids(claimed) if claimed else "— (tidak dituliskan)"
    return FieldCheck(
        field="conflict_set",
        ok=ok,
        claim=claim_text,
        expected=_format_ids(actual_ids),
    )


def _compare_selected(
    claimed: Optional[str], actual_id: Optional[str]
) -> FieldCheck:
    ok = bool(claimed) and bool(actual_id) and normalize(claimed) == normalize(actual_id)
    return FieldCheck(
        field="selected_rule",
        ok=ok,
        claim=claimed or "— (tidak dituliskan)",
        expected=actual_id or "— (berhenti)",
    )


def _compare_conclusion(
    claimed: Optional[str], actual: Optional[str]
) -> FieldCheck:
    ok = bool(claimed) and bool(actual) and normalize(claimed) == normalize(actual)
    return FieldCheck(
        field="conclusion",
        ok=ok,
        claim=claimed or "— (tidak dituliskan)",
        expected=actual or "—",
    )


def check_answer(
    submitted: SubmittedIterations,
    rules: List[Rule],
    initial_facts: List[str],
) -> FeedbackReport:
    """Compare ``submitted`` with a fresh forward-chaining run."""
    result: ForwardResult = run_forward_chaining(rules, initial_facts)
    actual_iters: Dict[int, object] = {
        t.iteration: t for t in result.iterations if t.selected_rule is not None
    }
    # The trace records a final empty-conflict-set iteration (STOP).
    stop_iteration: Optional[int] = next(
        (
            t.iteration
            for t in result.iterations
            if t.selected_rule is None and not t.conflict_set
        ),
        None,
    )

    issues: List[Issue] = []
    per_iteration: List[dict] = []
    correct_count = 0
    total_fields = 0

    submitted_map: Dict[int, SubmittedIteration] = {}
    for it in submitted.iterations:
        if it.iteration in submitted_map:
            issues.append(
                Issue(
                    iteration=it.iteration,
                    field="extra",
                    claim=f"Iterasi {it.iteration} dituliskan dua kali",
                    expected="satu baris per iterasi",
                    explanation=(
                        "Nomor iterasi duplikat pada jawaban. Gunakan satu baris "
                        "per iterasi agar jejak dapat dibandingkan."
                    ),
                )
            )
            continue
        submitted_map[it.iteration] = it

    # A STOP claim is correct when the engine really stops at that iteration.
    for number, claimed in list(submitted_map.items()):
        if claimed.stop and number == stop_iteration:
            total_fields += 1
            correct_count += 1
            per_iteration.append(
                {
                    "iteration": number,
                    "checks": [
                        FieldCheck(
                            field="stop",
                            ok=True,
                            claim="STOP",
                            expected="STOP — conflict set kosong",
                        )
                    ],
                    "ok": True,
                }
            )
            del submitted_map[number]

    # Matched iterations, compared field by field.
    for number in sorted(set(submitted_map) | set(actual_iters)):
        claimed = submitted_map.get(number)
        actual = actual_iters.get(number)

        if claimed is not None and actual is None:
            issues.append(
                Issue(
                    iteration=number,
                    field="extra",
                    claim=f"Iterasi {number} tidak ada pada jejak engine",
                    expected=(
                        f"engine hanya mencatat {len(actual_iters)} iterasi firing "
                        "(iterasi terakhir adalah STOP dengan conflict set kosong)"
                    ),
                    explanation=(
                        "Periksa kembali: engine berhenti ketika tidak ada aturan "
                        "yang READY. Iterasi dengan firing di luar jejak biasanya "
                        "berasal dari kesalahan menghitung urutan."
                    ),
                )
            )
            continue

        if claimed is None and actual is not None:
            issues.append(
                Issue(
                    iteration=number,
                    field="missing",
                    claim="— (tidak dituliskan)",
                    expected=(
                        f"iterasi {number}: conflict set "
                        f"{_format_ids(actual.conflict_set)}, dipilih {actual.selected_rule}, "
                        f"kesimpulan {actual.conclusion}"
                    ),
                    explanation=(
                        "Ada iterasi firing pada jejak engine yang belum dibahas "
                        "dalam jawaban."
                    ),
                )
            )
            continue

        rules_by_id = {r.id: r for r in rules}
        actual_ready = [
            rules_by_id[rid]
            for rid in actual.conflict_set
            if rid in rules_by_id
        ]

        checks = [
            _compare_conflict_set(claimed.conflict_set, actual.conflict_set),
            _compare_selected(claimed.selected_rule, actual.selected_rule),
            _compare_conclusion(claimed.conclusion, actual.conclusion),
        ]
        total_fields += len(checks)
        ok_fields = sum(1 for c in checks if c.ok)
        correct_count += ok_fields

        row = {
            "iteration": number,
            "checks": checks,
            "ok": all(c.ok for c in checks),
        }
        per_iteration.append(row)

        for check in checks:
            if check.ok:
                continue
            issues.append(
                Issue(
                    iteration=number,
                    field=check.field,
                    claim=check.claim,
                    expected=check.expected,
                    explanation=_explanation_for(check.field, actual, actual_ready),
                )
            )

    score = round(correct_count / total_fields * 100) if total_fields else 0
    return FeedbackReport(
        correct=correct_count,
        total=total_fields,
        issues=issues,
        per_iteration=per_iteration,
        score_percent=score,
    )


def _explanation_for(
    field: str,
    actual: object,
    actual_ready: List[Rule],
) -> str:
    """Build a teaching explanation citing the concrete criterion."""
    selected = next((r for r in actual_ready if r.id == actual.selected_rule), None)

    if field == "conflict_set":
        # Rules marked REFRACTORY in this iteration's evaluations were ready
        # by their conditions but already fired — hence excluded.
        fired_before = [
            ev.rule_id
            for ev in actual.evaluations
            if ev.status.value == "REFRACTORY"
        ]
        parts = [
            "Conflict set iterasi ini adalah aturan-aturan yang READY (semua "
            "kondisi IF terpenuhi) dan belum refractory.",
        ]
        if actual.conflict_set:
            parts.append(f"Engine menemukan: {_format_ids(actual.conflict_set)}.")
        else:
            parts.append("Tidak ada aturan yang siap — inferensi berhenti.")
        if fired_before:
            parts.append(
                f"Aturan berikut sudah pernah fired pada iterasi sebelumnya, "
                f"sehingga dikeluarkan dari conflict set oleh refractoriness: "
                f"{', '.join(fired_before)}."
            )
        parts.append(
            "Ingat urutan pertimbangan: salience → spesifisitas → nomor aturan."
        )
        return " ".join(parts)

    if field == "selected_rule" and selected is not None:
        return _explain_selection(selected, actual_ready)

    if field == "conclusion":
        return (
            f"Kesimpulan iterasi ini adalah THEN dari aturan terpilih "
            f"({actual.selected_rule}): “{actual.conclusion}”."
        )

    return "Bandingkan dengan jejak iterasi pada engine."
