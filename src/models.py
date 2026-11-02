"""Structured data models shared by the inference engine, the tree renderer and
the Streamlit UI.

These models contain *no* inference behaviour beyond trivial helpers.  They are
plain dataclasses so they can be serialised, copied and unit-tested easily.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .normalization import display, normalize


# ---------------------------------------------------------------------------
# Status enums
# ---------------------------------------------------------------------------
class RuleStatus(str, Enum):
    """Status of a rule during a forward-chaining iteration."""

    READY = "READY"
    NOT_READY = "NOT_READY"
    FIRED = "FIRED"
    READY_NOT_SELECTED = "READY_NOT_SELECTED"
    REFRACTORY = "REFRACTORY"

    @property
    def label(self) -> str:
        """Human readable label (Indonesian UI wording)."""
        return {
            RuleStatus.READY: "READY",
            RuleStatus.NOT_READY: "NOT READY",
            RuleStatus.FIRED: "FIRED",
            RuleStatus.READY_NOT_SELECTED: "READY BUT NOT SELECTED",
            RuleStatus.REFRACTORY: "REFRACTORY",
        }[self]


class NodeStatus(str, Enum):
    """Status used by both forward and backward inference tree nodes."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    PROVEN = "PROVEN"
    UNPROVEN = "UNPROVEN"
    FIRED = "FIRED"
    READY = "READY"
    NOT_READY = "NOT_READY"
    READY_NOT_SELECTED = "READY_NOT_SELECTED"
    REFRACTORY = "REFRACTORY"
    CYCLE = "CYCLE"
    NEUTRAL = "NEUTRAL"


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
SUPPORTED_CONNECTORS = ("AND", "OR")


@dataclass
class Rule:
    """A single IF-THEN production rule.

    ``conditions`` are joined with logical ``AND`` or ``OR`` according to
    ``connector``.  The default is ``AND`` so the assignment dataset keeps its
    original semantics.
    """

    id: str
    conditions: List[str]
    conclusion: str
    salience: int = 1
    connector: str = "AND"

    def __post_init__(self) -> None:
        # Defensive copies / normalization of user supplied values.
        self.id = display(self.id)
        self.conditions = [display(c) for c in self.conditions if display(c)]
        self.conclusion = display(self.conclusion)
        try:
            self.salience = int(self.salience)
        except (TypeError, ValueError):
            self.salience = 0
        connector = str(self.connector or "AND").strip().upper()
        self.connector = connector if connector in SUPPORTED_CONNECTORS else "AND"

    @property
    def joined_conditions(self) -> str:
        """Human readable condition list using the rule's connector."""
        return f" {self.connector} ".join(self.conditions)

    # -- derived helpers ---------------------------------------------------
    @property
    def specificity(self) -> int:
        """Number of IF conditions.  Higher = more specific."""
        return len(self.conditions)

    @property
    def salience_label(self) -> str:
        return salience_label(self.salience)

    def matches_conclusion(self, fact: str) -> bool:
        return normalize(self.conclusion) == normalize(fact)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conditions": list(self.conditions),
            "conclusion": self.conclusion,
            "salience": self.salience,
            "connector": self.connector,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        return cls(
            id=data.get("id", ""),
            conditions=list(data.get("conditions", [])),
            conclusion=data.get("conclusion", ""),
            salience=data.get("salience", 1),
            connector=data.get("connector", "AND"),
        )

    def copy(self) -> "Rule":
        return Rule(
            self.id,
            list(self.conditions),
            self.conclusion,
            self.salience,
            self.connector,
        )


SALIENCE_LABELS = {
    1: "Rendah",
    2: "Sedang",
    3: "Tinggi",
    4: "Tertinggi",
}


def salience_label(value: int) -> str:
    return SALIENCE_LABELS.get(int(value), "Tidak diketahui")


# ---------------------------------------------------------------------------
# Forward chaining trace
# ---------------------------------------------------------------------------
@dataclass
class ConditionEvaluation:
    """Result of evaluating a single IF condition against working memory."""

    condition: str
    status: bool
    explanation: str = ""

    @property
    def label(self) -> str:
        return "TRUE" if self.status else "FALSE"


@dataclass
class RuleEvaluation:
    """Result of evaluating one rule during one iteration."""

    rule_id: str
    iteration: int
    condition_results: List[ConditionEvaluation]
    status: RuleStatus
    reason: str = ""
    salience: int = 0
    specificity: int = 0
    conclusion: str = ""
    connector: str = "AND"

    @property
    def status_label(self) -> str:
        return self.status.label

    @property
    def all_conditions_true(self) -> bool:
        return all(c.status for c in self.condition_results)

    @property
    def satisfied(self) -> bool:
        """Whether the IF side is satisfied under this rule's connector."""
        if not self.condition_results:
            return False
        if self.connector == "OR":
            return any(c.status for c in self.condition_results)
        return all(c.status for c in self.condition_results)

    @property
    def failed_conditions(self) -> List[ConditionEvaluation]:
        return [c for c in self.condition_results if not c.status]


@dataclass
class IterationTrace:
    """A complete snapshot of one forward-chaining iteration."""

    iteration: int
    facts_before: List[str]
    evaluations: List[RuleEvaluation]
    conflict_set: List[str]
    ranking: List[str]
    selected_rule: Optional[str]
    selection_reason: str
    conclusion: Optional[str]
    conclusion_added: Optional[bool]
    facts_after: List[str]

    def evaluation_for(self, rule_id: str) -> Optional[RuleEvaluation]:
        for ev in self.evaluations:
            if ev.rule_id == rule_id:
                return ev
        return None


@dataclass
class ForwardResult:
    """Full result of a forward-chaining run."""

    initial_facts: List[str]
    iterations: List[IterationTrace]
    fired_rules: List[str]
    derived_facts: List[str]
    final_facts: List[str]
    goal: Optional[str] = None
    goal_proven: Optional[bool] = None
    terminated_reason: str = ""

    @property
    def rules_fired(self) -> int:
        return len(self.fired_rules)


# ---------------------------------------------------------------------------
# Backward chaining trace
# ---------------------------------------------------------------------------
@dataclass
class BackwardNode:
    """A node in the backward-chaining proof tree.

    ``kind`` is one of ``GOAL``, ``RULE``, ``CONDITION`` or ``FACT``.
    ``status`` is a :class:`NodeStatus` value.
    """

    label: str
    kind: str
    status: NodeStatus = NodeStatus.NEUTRAL
    depth: int = 0
    rule_id: Optional[str] = None
    detail: str = ""
    source: str = ""
    connector: str = ""
    children: List["BackwardNode"] = field(default_factory=list)

    @property
    def status_label(self) -> str:
        return self.status.value


@dataclass
class BackwardResult:
    """Full result of a backward-chaining run."""

    goal: str
    proven: bool
    root: BackwardNode
    initial_facts: List[str]
    proof_path: List[str] = field(default_factory=list)
    cycle_detected: bool = False
    log: List[str] = field(default_factory=list)
    terminated_reason: str = ""
