"""Working memory — the set of facts currently believed to be TRUE.

A fact is TRUE when it exists in working memory.  Matching uses normalized
exact string comparison (see :mod:`src.normalization`).
"""

from __future__ import annotations

from typing import Iterable, List

from .normalization import display, normalize


class WorkingMemory:
    """Ordered, de-duplicated set of facts.

    Insertion order is preserved so the UI can show facts in a stable,
    meaningful order (initial facts first, derived facts after).
    """

    def __init__(self, facts: Iterable[str] | None = None) -> None:
        self._items: List[str] = []
        self._index: dict[str, str] = {}
        if facts:
            for fact in facts:
                self.add(fact)

    # -- mutation ----------------------------------------------------------
    def add(self, fact: str) -> bool:
        """Add ``fact``.  Returns ``True`` only when it was newly added."""
        clean = display(fact)
        key = normalize(clean)
        if not key:
            return False
        if key in self._index:
            return False
        self._index[key] = clean
        self._items.append(clean)
        return True

    def extend(self, facts: Iterable[str]) -> List[str]:
        added: List[str] = []
        for fact in facts:
            if self.add(fact):
                added.append(display(fact))
        return added

    # -- queries -----------------------------------------------------------
    def contains(self, fact: str) -> bool:
        return normalize(fact) in self._index

    def facts(self) -> List[str]:
        """Return facts in insertion order (a copy)."""
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __contains__(self, fact: str) -> bool:  # pragma: no cover - sugar
        return self.contains(fact)

    def snapshot(self) -> List[str]:
        return self.facts()
