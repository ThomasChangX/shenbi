"""Tests for pre-dispatch helper precompute injection (spec #33 T1a)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.dispatch_helper import _build_skill_prompt


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Project with real chapter fixtures copied in (real skill outputs)."""
    fixtures = Path("tests/fixtures")
    chapters = sorted(fixtures.glob("chapter-*-draft.md"))[:3]
    assert chapters, "chapter fixtures missing"
    (tmp_path / "chapters").mkdir()
    for ch in chapters:
        (tmp_path / "chapters" / ch.name).write_text(
            ch.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return tmp_path


def _build_style_prompt(project_dir: Path) -> str:
    system, user, _outputs = _build_skill_prompt(
        skill="shenbi-style-learning",
        project_dir=project_dir,
        prompt="generate style profile",
        chapter=None,
    )
    assert system  # system prompt non-empty
    return user


def test_stats_block_injected_for_style_learning(project_dir: Path) -> None:
    user = _build_style_prompt(project_dir)
    assert "## Helper Precompute (style stats, deterministic)" in user
    # JSON block carries real compute_all_stats keys over real chapter text
    start = user.index("```json", user.index("## Helper Precompute"))
    end = user.index("```", start + 7)
    stats = json.loads(user[start + 7 : end])
    assert "sentence" in stats or "percentiles" in stats or "ttr" in stats


def test_switch_off_disables_injection(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from shenbi.pipeline import helper_injection

    monkeypatch.setattr(
        helper_injection, "_helper_injection_disabled", lambda: frozenset({"shenbi-style-learning"})
    )
    user = _build_style_prompt(project_dir)
    assert "## Helper Precompute" not in user


def test_other_skills_untouched(project_dir: Path) -> None:
    system, user, _outputs = _build_skill_prompt(
        skill="shenbi-worldbuilding",
        project_dir=project_dir,
        prompt="generate worldbuilding",
        chapter=None,
    )
    assert "## Helper Precompute" not in user


def test_no_chapters_no_injection(tmp_path: Path) -> None:
    user = _build_style_prompt(tmp_path)
    assert "## Helper Precompute" not in user


def test_injection_reads_at_most_ten_chapters(project_dir: Path) -> None:
    # Add 20 more chapter files; the block must still build (bounded window).
    for n in range(11, 31):
        (project_dir / "chapters" / f"chapter-{n}.md").write_text("正文" * 200, encoding="utf-8")
    user = _build_style_prompt(project_dir)
    assert "## Helper Precompute (style stats, deterministic)" in user
