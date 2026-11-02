"""Pytest configuration — makes the project root importable and provides fixtures."""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.knowledge_base import KnowledgeBase, default_facts, default_rules  # noqa: E402


@pytest.fixture
def facts():
    return default_facts()


@pytest.fixture
def rules():
    return default_rules()


@pytest.fixture
def kb():
    return KnowledgeBase()