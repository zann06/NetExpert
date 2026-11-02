"""Tests for knowledge base CRUD and input validation."""

from src.knowledge_base import KnowledgeBase, default_facts, default_rules
from src.models import Rule
from src.validation import validate_fact, validate_rule, validate_salience


def test_default_dataset_matches_assignment():
    rules = default_rules()
    assert [r.id for r in rules] == [f"R{i}" for i in range(1, 9)]
    assert len(rules) == 8
    assert rules[0].conditions == ["Semua Situs Tidak Bisa Dibuka"]
    assert rules[0].conclusion == "Cek Router"
    assert rules[0].salience == 1
    assert rules[3].conditions == ["Gangguan Provider", "Tagihan Sudah Dibayar"]
    assert rules[3].conclusion == "Lapor ke Provider"
    assert rules[3].salience == 3
    assert rules[7].id == "R8"
    assert rules[7].salience == 4
    assert default_facts() == [
        "Semua Situs Tidak Bisa Dibuka",
        "Perangkat Lain Juga Offline",
        "Tagihan Sudah Dibayar",
    ]


def test_add_rule(kb):
    errors = kb.add(Rule("R9", ["Cek Router"], "Hubungi Teknisi", 2))
    assert errors == []
    assert kb.get("R9").conclusion == "Hubungi Teknisi"
    assert len(kb) == 9


def test_duplicate_rule_id_is_rejected(kb):
    errors = kb.add(Rule("R1", ["Fakta Baru"], "Kesimpulan", 2))
    assert errors
    assert any("sudah dipakai" in e for e in errors)
    assert len(kb) == 8


def test_case_insensitive_duplicate_id_is_rejected(kb):
    errors = kb.add(Rule("r1", ["Fakta Baru"], "Kesimpulan", 2))
    assert errors


def test_update_rule(kb):
    errors = kb.update("R4", Rule("R4", ["Gangguan Provider"], "Lapor ke Provider", 3))
    assert errors == []
    assert kb.get("R4").conditions == ["Gangguan Provider"]


def test_update_can_change_id(kb):
    errors = kb.update("R4", Rule("R40", ["Baru"], "Hasil", 1))
    assert errors == []
    assert kb.get("R40") is not None
    assert kb.get("R4") is None


def test_update_rejects_collision_with_other_rule(kb):
    errors = kb.update("R4", Rule("R5", ["Baru"], "Hasil", 1))
    assert errors
    assert kb.get("R4") is not None


def test_delete_rule(kb):
    assert kb.delete("R1") is True
    assert kb.get("R1") is None
    assert kb.delete("R1") is False


def test_rule_requires_at_least_one_condition():
    errors = validate_rule(Rule("R9", [], "Hasil", 1), [])
    assert any("minimal satu kondisi" in e for e in errors)


def test_rule_requires_non_empty_conclusion():
    errors = validate_rule(Rule("R9", ["A"], "   ", 1), [])
    assert any("Kesimpulan" in e for e in errors)


def test_salience_must_be_1_to_4():
    assert validate_salience(1) is None
    assert validate_salience(4) is None
    assert validate_salience(0) is not None
    assert validate_salience(5) is not None
    assert validate_salience("abc") is not None


def test_search_by_text_and_salience(kb):
    assert [r.id for r in kb.search("provider")] == ["R2", "R3", "R4", "R5", "R7"]
    assert [r.id for r in kb.search("", salience=4)] == ["R8"]
    assert [r.id for r in kb.search("laptop")] == ["R6"]


def test_all_facts_and_catalog(kb):
    all_facts = kb.all_facts()
    assert "Cek Router" in all_facts
    assert "Gangguan Provider" in all_facts
    catalog = kb.fact_catalog()
    for fact in default_facts():
        assert fact in catalog


def test_validate_fact_rejects_empty_and_duplicate():
    assert validate_fact("   ")
    assert validate_fact("Cek Router", ["Cek Router"])
    assert validate_fact("Fakta Baru", ["Cek Router"]) == []


def test_knowledge_base_is_independent_of_default_data():
    kb = KnowledgeBase()
    kb.delete("R1")
    assert len(default_rules()) == 8  # default_rules() returns a fresh copy


def test_rule_normalizes_whitespace():
    rule = Rule("  R9 ", ["  Kondisi   A ", ""], "  Hasil  ", 2)
    assert rule.id == "R9"
    assert rule.conditions == ["Kondisi A"]
    assert rule.conclusion == "Hasil"