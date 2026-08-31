"""Tests for tools/lint_helper_usage.py (spec #33 T4)."""

from __future__ import annotations

from pathlib import Path

from tools.lint_helper_usage import CAPABILITY_PATTERNS, lint_skill


def _mk(tmp_path: Path, body: str) -> Path:
    skill = tmp_path / "shenbi-fake-skill" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(body, encoding="utf-8")
    return skill


def test_dead_python_m_instruction_flagged(tmp_path: Path) -> None:
    skill = _mk(tmp_path, "流程：先运行 `python -m shenbi.skill_utils.style_learning` 取统计。\n")
    assert len(lint_skill(skill)) == 1


def test_clean_reference_not_flagged(tmp_path: Path) -> None:
    skill = _mk(tmp_path, "直接引用框架注入的 Helper Precompute 统计块，不要重算。\n")
    assert lint_skill(skill) == []


def test_out_of_scope_drift_instruction_not_flagged(tmp_path: Path) -> None:
    # drift-guidance's dead instruction is a recorded T5 candidate, not in
    # this lint's capability list.
    skill = _mk(tmp_path, "运行 `python -m shenbi.skill_utils.drift_detection`。\n")
    assert lint_skill(skill) == []


def test_allowed_exemption_suppresses(tmp_path: Path, monkeypatch) -> None:
    import tools.lint_helper_usage as mod

    monkeypatch.setattr(mod, "ALLOWED", {"shenbi-fake-skill": [1]})
    skill = _mk(tmp_path, "运行 `python -m shenbi.skill_utils.calibration --reported high`\n")
    assert lint_skill(skill) == []


def test_patterns_cover_transition_recurrence(tmp_path: Path) -> None:
    assert any(p.search("LLM 需自行计算转折词密度") for p in CAPABILITY_PATTERNS)


def test_prohibition_wording_not_flagged(tmp_path: Path) -> None:
    skill = _mk(tmp_path, "不要自行计算转折词密度——读注入块。\n")
    assert lint_skill(skill) == []
