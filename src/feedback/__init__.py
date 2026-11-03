"""Deterministic feedback for student answers (no AI, no LLM).

A student pastes an answer (for example copied from an AI chat) describing
the forward-chaining iterations.  The parser extracts the claimed iterations
and the checker compares them with the real engine trace, citing the exact
conflict-resolution criterion for every mistake.
"""

from .checker import check_answer
from .models import (
    FieldCheck,
    FeedbackReport,
    Issue,
    SubmittedIteration,
    SubmittedIterations,
)
from .parser import parse_answer

__all__ = [
    "check_answer",
    "parse_answer",
    "FieldCheck",
    "FeedbackReport",
    "Issue",
    "SubmittedIteration",
    "SubmittedIterations",
]
