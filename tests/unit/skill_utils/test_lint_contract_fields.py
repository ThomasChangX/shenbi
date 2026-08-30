"""Spec #28: lint_contract_fields multi-sample any-match semantics."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = REPO_ROOT / "scripts" / "lint_contract_fields.py"


def _load():
    spec = importlib.util.spec_from_file_location("lint_contract_fields", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_samples_collects_all_existing_candidates(monkeypatch, tmp_path):
    mod = _load()
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("## X\n", encoding="utf-8")
    b.write_text("## Y\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(
        mod,
        "EXAMPLE_FIXTURES",
        {"truth/current_state.md": [a, b]},
        raising=False,
    )
    samples = mod.resolve_samples("truth/current_state.md")
    assert samples == [a, b]  # both collected, not first-match


def test_resolve_samples_empty_when_none_exist(monkeypatch, tmp_path):
    mod = _load()
    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(mod, "EXAMPLE_FIXTURES", {}, raising=False)
    assert mod.resolve_samples("truth/nope.md") == []


def test_check_read_item_any_match_pass(monkeypatch, tmp_path):
    """Declaration hitting ANY sample passes (spec #28 R1 any-match)."""
    mod = _load()
    sample_a = tmp_path / "old.md"
    sample_a.write_text("## 主角状态\n", encoding="utf-8")
    sample_b = tmp_path / "prod.md"
    sample_b.write_text("## 系统演化阶段\n## 参数当前位置\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve_samples", lambda p: [sample_a, sample_b])
    item = {"file": "truth/current_state.md", "fields": ["系统演化阶段"]}
    assert mod._check_read_item("test-skill", item) is None


def test_check_read_item_fails_when_no_sample_matches(monkeypatch, tmp_path):
    mod = _load()
    sample = tmp_path / "s.md"
    sample.write_text("## 别的节\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve_samples", lambda p: [sample])
    item = {"file": "truth/current_state.md", "fields": ["系统演化阶段"]}
    issue = mod._check_read_item("test-skill", item)
    assert issue is not None and "系统演化阶段" in issue


def test_check_read_item_skips_when_zero_samples(monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "resolve_samples", lambda p: [])
    item = {"file": "truth/nothing.md", "fields": ["whatever"]}
    assert mod._check_read_item("test-skill", item) is None


def test_volume_map_sample_filled():
    """R2: the None skip hole for outline/volume_map.md is filled."""
    mod = _load()
    assert mod.EXAMPLE_FIXTURES["outline/volume_map.md"] is not None
