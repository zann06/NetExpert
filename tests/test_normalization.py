"""Tests for text normalization and working memory."""

from src.normalization import display, normalize, same
from src.working_memory import WorkingMemory


def test_normalize_trims_and_collapses_spaces():
    assert normalize("  Cek   Router  ") == "cek router"


def test_normalize_is_case_insensitive():
    assert same("Cek Router", "cek router")
    assert same("  Gangguan   Provider ", "GANGGUAN PROVIDER")


def test_display_keeps_case_but_tidies_whitespace():
    assert display("  Cek   Router  ") == "Cek Router"


def test_working_memory_deduplicates():
    wm = WorkingMemory(["Cek Router", " cek   router ", "OK"])
    assert wm.facts() == ["Cek Router", "OK"]
    assert len(wm) == 2


def test_working_memory_add_returns_true_only_for_new_fact():
    wm = WorkingMemory()
    assert wm.add("Fakta A") is True
    assert wm.add("fakta a") is False
    assert wm.facts() == ["Fakta A"]


def test_working_memory_ignores_empty_facts():
    wm = WorkingMemory(["", "   ", "Real"])
    assert wm.facts() == ["Real"]
    assert wm.contains("") is False