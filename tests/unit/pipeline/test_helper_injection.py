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
    monkeypatch.setattr(
        "shenbi.pipeline.helper_injection.load_executor_config",
        lambda: {"helper_injection_disabled": ["shenbi-style-learning"]},
    )
    user = _build_style_prompt(project_dir)
    assert "## Helper Precompute" not in user


def test_disabled_config_malformed_value_warns(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shenbi.pipeline import helper_injection

    monkeypatch.setattr(
        "shenbi.pipeline.helper_injection.load_executor_config",
        lambda: {"helper_injection_disabled": "oops"},
    )
    assert helper_injection._helper_injection_disabled() == frozenset()
    user = _build_style_prompt(project_dir)
    assert "## Helper Precompute (style stats, deterministic)" in user


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


def test_injection_window_is_numeric_last_ten(project_dir: Path) -> None:
    # 12 chapters total: lexicographic trap (chapter-10 sorts before chapter-2).
    # The window must be chapters 3..12 (numeric tail), asserted via the
    # disclosed window size in the block header.
    for n in range(4, 13):
        (project_dir / "chapters" / f"chapter-{n}.md").write_text("正文" * 200, encoding="utf-8")
    from shenbi.pipeline.helper_injection import _style_stats_block

    block = _style_stats_block(project_dir)
    assert block is not None
    assert "窗口=最近 10 章" in block


def test_pre_revision_backups_excluded_from_window(project_dir: Path) -> None:
    backup = project_dir / "chapters" / "chapter-1-pre-rev.md"
    backup.write_text("旧稿" * 100, encoding="utf-8")
    from shenbi.pipeline.helper_injection import _style_stats_block

    block = _style_stats_block(project_dir)
    assert block is not None
    assert "chapter-1-pre-rev.md" not in block  # backup must not skew stats
