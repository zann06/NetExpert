"""Session-state helpers for the Streamlit application.

All mutable application state lives here so pages stay declarative.
"""

from __future__ import annotations

from typing import List, Optional

import streamlit as st

from ..inference import run_forward_chaining
from ..knowledge_base import KnowledgeBase, default_facts, default_rules
from ..models import BackwardResult, ForwardResult, Rule

PAGES = [
    "Overview",
    "Diagnosis",
    "Knowledge Base",
    "Inference Tree",
    "Laporan",
    "Feedback",
    "Guide",
]


def init_state() -> None:
    ss = st.session_state
    if "rules" not in ss:
        ss.rules = default_rules()
    if "initial_facts" not in ss:
        ss.initial_facts = default_facts()
    if "custom_facts" not in ss:
        ss.custom_facts = []
    if "forward_result" not in ss:
        ss.forward_result = None
    if "backward_result" not in ss:
        ss.backward_result = None
    if "last_method" not in ss:
        ss.last_method = None
    if "last_goal" not in ss:
        ss.last_goal = ""
    if "tree_filter" not in ss:
        ss.tree_filter = "all"
    if "nav" not in ss:
        ss.nav = "Overview"
    if "flash" not in ss:
        ss.flash = None


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
def navigate(page: str) -> None:
    """Callback used by buttons to switch pages safely (runs before rerun)."""
    if page in PAGES:
        st.session_state.nav = page


# ---------------------------------------------------------------------------
# Rules / knowledge base
# ---------------------------------------------------------------------------
def get_rules() -> List[Rule]:
    return list(st.session_state.rules)


def get_kb() -> KnowledgeBase:
    return KnowledgeBase(st.session_state.rules)


def store_kb(kb: KnowledgeBase) -> None:
    st.session_state.rules = kb.rules
    clear_results()


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------
def get_initial_facts() -> List[str]:
    return list(st.session_state.initial_facts)


def set_initial_facts(facts: List[str]) -> bool:
    """Update initial facts; returns True when they actually changed."""
    cleaned: List[str] = []
    for fact in facts:
        fact = " ".join(str(fact).split())
        if fact and fact not in cleaned:
            cleaned.append(fact)
    if cleaned != st.session_state.initial_facts:
        st.session_state.initial_facts = cleaned
        clear_results()
        return True
    return False


def fact_catalog() -> List[str]:
    kb = get_kb()
    return kb.fact_catalog(st.session_state.custom_facts)


def add_custom_fact(fact: str) -> None:
    """Register a custom fact in the catalog (selection handled by caller)."""
    clean = " ".join(str(fact).split())
    if not clean:
        return
    catalog_keys = {f.casefold() for f in fact_catalog()}
    if clean.casefold() not in catalog_keys:
        st.session_state.custom_facts.append(clean)


def restore_default_facts() -> None:
    st.session_state.initial_facts = default_facts()
    st.session_state.facts_select = default_facts()
    clear_results()


def clear_facts() -> None:
    st.session_state.initial_facts = []
    st.session_state.facts_select = []
    clear_results()


def reset_application() -> None:
    """Restore the original assignment dataset and clear all transient state."""
    ss = st.session_state
    ss.rules = default_rules()
    ss.initial_facts = default_facts()
    ss.custom_facts = []
    ss.facts_select = default_facts()
    ss.forward_result = None
    ss.backward_result = None
    ss.last_method = None
    ss.last_goal = ""
    ss.flash = "Aplikasi direset ke dataset tugas."
    for key in ("add_id", "add_conditions", "add_conclusion", "add_salience"):
        if key in ss:
            del ss[key]
    ss.confirm_reset_app = False


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
def clear_results() -> None:
    st.session_state.forward_result = None
    st.session_state.backward_result = None
    st.session_state.last_method = None


def save_forward_result(result: ForwardResult, goal: str = "") -> None:
    st.session_state.forward_result = result
    st.session_state.backward_result = None
    st.session_state.last_method = "forward"
    st.session_state.last_goal = goal


def save_backward_result(result: BackwardResult) -> None:
    st.session_state.backward_result = result
    st.session_state.forward_result = None
    st.session_state.last_method = "backward"
    st.session_state.last_goal = result.goal


def run_sample_diagnosis() -> None:
    """Overview quick action: run forward chaining with the current state."""
    kb = get_kb()
    result = run_forward_chaining(kb.rules, get_initial_facts())
    save_forward_result(result)
    st.session_state.nav = "Diagnosis"


# ---------------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------------
def derived_facts_count() -> int:
    result: Optional[ForwardResult] = st.session_state.forward_result
    return len(result.derived_facts) if result else 0


def fired_rules_count() -> int:
    result: Optional[ForwardResult] = st.session_state.forward_result
    return len(result.fired_rules) if result else 0