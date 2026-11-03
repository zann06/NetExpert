"""Data models for the answer-feedback feature.

A student pastes a free-form answer (or fills a structured form) describing
the forward-chaining iterations of the assignment.  :mod:`src.feedback.parser`
turns that text into :class:`SubmittedIterations`, and
:mod:`src.feedback.checker` compares it against the real engine trace.

Everything here is deterministic Python - no LLM, no external API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SubmittedIteration:
    """One iteration as claimed by the student."""

    iteration: int = 0
    conflict_set: List[str] = field(default_factory=list)
    selected_rule: Optional[str] = None
    conclusion: Optional[str] = None
    stop: bool = False  # student claims the run stops here (empty conflict set)
    source_line: Optional[int] = None  # line number in the pasted answer


@dataclass
class SubmittedIterations:
    """The parsed answer: an ordered list of claimed iterations."""

    iterations: List[SubmittedIteration] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.iterations)

    def __iter__(self):
        return iter(self.iterations)

    def __getitem__(self, index):
        return self.iterations[index]


@dataclass
class Issue:
    """One discrepancy between the answer and the engine trace."""

    iteration: int
    field: str  # "conflict_set" | "selected_rule" | "conclusion" | "missing" | "extra"
    claim: str
    expected: str
    explanation: str

    @property
    def severity(self) -> str:
        """``error`` for wrong content, ``warning`` for structural problems."""
        return "warning" if self.field in {"missing", "extra"} else "error"


@dataclass
class FieldCheck:
    """Result of checking one field of one iteration."""

    field: str
    ok: bool
    claim: str
    expected: str


@dataclass
class FeedbackReport:
    """Full comparison result for rendering in the UI."""

    correct: int
    total: int
    issues: List[Issue] = field(default_factory=list)
    per_iteration: List[dict] = field(default_factory=list)
    score_percent: int = 0

    @property
    def all_correct(self) -> bool:
        return self.total > 0 and not self.issues
