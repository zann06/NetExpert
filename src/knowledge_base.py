"""Knowledge base management: default assignment data, CRUD and search.

The default rules and facts reproduce the assignment dataset exactly.  The
inference engines never special-case these eight rules — they work with any
user-supplied rule set.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .models import Rule
from .normalization import display, normalize
from .validation import validate_rule

# ---------------------------------------------------------------------------
# Default assignment dataset
# ---------------------------------------------------------------------------
DEFAULT_FACTS: List[str] = [
    "Semua Situs Tidak Bisa Dibuka",
    "Perangkat Lain Juga Offline",
    "Tagihan Sudah Dibayar",
]


def default_rules() -> List[Rule]:
    """Return a fresh copy of the eight assignment rules."""
    return [
        Rule("R1", ["Semua Situs Tidak Bisa Dibuka"], "Cek Router", 1),
        Rule("R2", ["Lampu Internet Router Merah"], "Gangguan Provider", 2),
        Rule("R3", ["Kecepatan Sangat Lambat"], "Gangguan Provider", 2),
        Rule(
            "R4",
            ["Gangguan Provider", "Tagihan Sudah Dibayar"],
            "Lapor ke Provider",
            3,
        ),
        Rule("R5", ["Perangkat Lain Juga Offline"], "Gangguan Provider", 2),
        Rule(
            "R6",
            ["Semua Situs Tidak Bisa Dibuka", "Hanya Laptop Ini Bermasalah"],
            "Masalah pada Laptop",
            3,
        ),
        Rule("R7", ["Gangguan Provider"], "Gunakan Tethering Sementara", 1),
        Rule(
            "R8",
            ["Cek Router", "Router Terasa Panas"],
            "Matikan Router 10 Menit",
            4,
        ),
    ]


def default_facts() -> List[str]:
    """Return a fresh copy of the three default initial facts."""
    return list(DEFAULT_FACTS)


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
class KnowledgeBase:
    """A mutable ordered collection of production rules."""

    def __init__(self, rules: Optional[Iterable[Rule]] = None) -> None:
        self._rules: List[Rule] = [r.copy() for r in (rules or default_rules())]

    # -- access ------------------------------------------------------------
    @property
    def rules(self) -> List[Rule]:
        return list(self._rules)

    def __len__(self) -> int:
        return len(self._rules)

    def __iter__(self):
        return iter(self._rules)

    def get(self, rule_id: str) -> Optional[Rule]:
        for rule in self._rules:
            if normalize(rule.id) == normalize(rule_id):
                return rule
        return None

    def exists(self, rule_id: str) -> bool:
        return self.get(rule_id) is not None

    # -- mutation ----------------------------------------------------------
    def add(self, rule: Rule) -> List[str]:
        """Validate and add a rule.  Returns validation errors (empty = ok)."""
        errors = validate_rule(rule, self._rules)
        if errors:
            return errors
        self._rules.append(rule.copy())
        return []

    def update(self, rule_id: str, updated: Rule) -> List[str]:
        """Validate and replace an existing rule, matched by ``rule_id``."""
        index = None
        for i, rule in enumerate(self._rules):
            if normalize(rule.id) == normalize(rule_id):
                index = i
                break
        if index is None:
            return [f"Aturan dengan ID '{rule_id}' tidak ditemukan."]

        errors = validate_rule(updated, self._rules, original_id=rule_id)
        if errors:
            return errors
        self._rules[index] = updated.copy()
        return []

    def delete(self, rule_id: str) -> bool:
        for i, rule in enumerate(self._rules):
            if normalize(rule.id) == normalize(rule_id):
                del self._rules[i]
                return True
        return False

    def replace_all(self, rules: Iterable[Rule]) -> None:
        self._rules = [r.copy() for r in rules]

    # -- search & helpers --------------------------------------------------
    def search(self, query: str = "", salience: Optional[int] = None) -> List[Rule]:
        """Filter rules by free text (id/conditions/conclusion) and salience."""
        needle = normalize(query)
        results: List[Rule] = []
        for rule in self._rules:
            if salience is not None and rule.salience != salience:
                continue
            if needle:
                haystack = normalize(
                    " ".join([rule.id, rule.conclusion, *rule.conditions])
                )
                if needle not in haystack:
                    continue
            results.append(rule)
        return results

    def all_facts(self) -> List[str]:
        """Every fact mentioned in the knowledge base (conditions + conclusions)."""
        seen: List[str] = []
        keys: set[str] = set()
        for rule in self._rules:
            for fact in [*rule.conditions, rule.conclusion]:
                key = normalize(fact)
                if key and key not in keys:
                    keys.add(key)
                    seen.append(display(fact))
        return seen

    def fact_catalog(self, extra: Optional[Iterable[str]] = None) -> List[str]:
        """Catalog of known facts for the fact selector.

        Combines default facts, facts used by the current knowledge base and any
        ``extra`` facts the user previously entered.
        """
        seen: List[str] = []
        keys: set[str] = set()
        sources: List[str] = [*DEFAULT_FACTS, *self.all_facts(), *(extra or [])]
        for fact in sources:
            key = normalize(fact)
            if key and key not in keys:
                keys.add(key)
                seen.append(display(fact))
        return seen

    def to_dicts(self) -> List[dict]:
        return [r.to_dict() for r in self._rules]
