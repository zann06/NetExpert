"""Inference engines for NetExpert.

* :mod:`src.inference.forward_chaining`  — data-driven reasoning.
* :mod:`src.inference.backward_chaining` — goal-driven reasoning.
* :mod:`src.inference.conflict_resolution` — the three-level priority order.
"""

from .backward_chaining import run_backward_chaining
from .conflict_resolution import (
    build_conflict_set,
    describe_ranking,
    rank_rules,
    rule_number,
    selection_reason,
    sort_key,
)
from .forward_chaining import run_forward_chaining

__all__ = [
    "run_forward_chaining",
    "run_backward_chaining",
    "build_conflict_set",
    "rank_rules",
    "rule_number",
    "selection_reason",
    "describe_ranking",
    "sort_key",
]
