"""Input validation for rules and facts.

All functions return a list of human readable error strings (empty list means
valid) so the UI can display them inline.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .models import Rule
from .normalization import display, normalize

MIN_SALIENCE = 1
MAX_SALIENCE = 4


def validate_salience(value) -> Optional[str]:
    """Return an error message when ``value`` is not a valid salience."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "Salience harus berupa angka bulat 1-4."
    if number < MIN_SALIENCE or number > MAX_SALIENCE:
        return "Salience harus berada di antara 1 dan 4."
    return None


def validate_condition(condition: str) -> Optional[str]:
    if not display(condition):
        return "Kondisi tidak boleh kosong."
    return None


def validate_conclusion(conclusion: str) -> Optional[str]:
    if not display(conclusion):
        return "Kesimpulan (THEN) tidak boleh kosong."
    return None


def validate_rule_id(
    rule_id: str,
    existing_rules: Iterable[Rule],
    original_id: Optional[str] = None,
) -> Optional[str]:
    """Validate the rule identifier, rejecting empty and duplicate ids.

    When editing, pass ``original_id`` so the rule does not clash with itself.
    """
    clean = display(rule_id)
    if not clean:
        return "ID aturan tidak boleh kosong."
    original = normalize(original_id) if original_id else None
    for rule in existing_rules:
        if normalize(rule.id) == normalize(clean) and normalize(rule.id) != original:
            return f"ID '{clean}' sudah dipakai oleh aturan lain."
    return None


def validate_rule(
    rule: Rule,
    existing_rules: Iterable[Rule],
    original_id: Optional[str] = None,
) -> List[str]:
    """Validate a full rule and return all error messages."""
    errors: List[str] = []

    id_error = validate_rule_id(rule.id, existing_rules, original_id)
    if id_error:
        errors.append(id_error)

    if not rule.conditions:
        errors.append("Aturan harus memiliki minimal satu kondisi IF.")
    else:
        for condition in rule.conditions:
            condition_error = validate_condition(condition)
            if condition_error:
                errors.append(condition_error)

    conclusion_error = validate_conclusion(rule.conclusion)
    if conclusion_error:
        errors.append(conclusion_error)

    salience_error = validate_salience(rule.salience)
    if salience_error:
        errors.append(salience_error)

    return errors


def validate_fact(fact: str, existing_facts: Iterable[str] | None = None) -> List[str]:
    """Validate a manually entered fact."""
    errors: List[str] = []
    clean = display(fact)
    if not clean:
        errors.append("Fakta tidak boleh kosong.")
        return errors
    if existing_facts is not None:
        for existing in existing_facts:
            if normalize(existing) == normalize(clean):
                errors.append(f"Fakta '{clean}' sudah ada.")
                break
    return errors
