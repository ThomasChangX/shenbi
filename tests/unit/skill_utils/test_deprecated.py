"""Shared DEPRECATED-skill detection (spec #59 T1/T3 single source)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.skill_utils.deprecated import deprecated_skill_names, is_deprecated_skill

REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "skills"


def _mk(root: Path, name: str, body: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")


@pytest.mark.unit
def test_detects_html_comment_banner(tmp_path: Path) -> None:
    _mk(
        tmp_path,
        "shenbi-x",
        "---\nname: shenbi-x\n---\n<!-- DEPRECATED: Superseded by y. -->\nbody",
    )
    assert is_deprecated_skill(tmp_path, "shenbi-x") is True


@pytest.mark.unit
def test_detects_hash_banner(tmp_path: Path) -> None:
    _mk(tmp_path, "shenbi-x", "# DEPRECATED: Superseded by y.\nbody")
    assert is_deprecated_skill(tmp_path, "shenbi-x") is True


@pytest.mark.unit
def test_live_skill_negative(tmp_path: Path) -> None:
    _mk(
        tmp_path,
        "shenbi-x",
        "---\nname: shenbi-x\n---\nbody mentions DEPRECATED_CONTEXT nowhere",
    )
    assert is_deprecated_skill(tmp_path, "shenbi-x") is False


@pytest.mark.unit
def test_missing_dir_is_not_deprecated(tmp_path: Path) -> None:
    assert is_deprecated_skill(tmp_path, "shenbi-ghost") is False


@pytest.mark.unit
def test_real_repo_baseline_15() -> None:
    # 回归钉：真仓当前 15 个 DEPRECATED（驳斥复核 2026-09-12 实况）
    names = deprecated_skill_names(SKILLS)
    assert "shenbi-foreshadowing-plant" in names
    assert "shenbi-review-continuity" in names
    assert len(names) == 15
