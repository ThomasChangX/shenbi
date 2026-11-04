"""Spec #95 T6b (R8): reject scope symmetric with commit — follower joins."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from shenbi.pipeline import cli
from shenbi.pipeline.state import CheckpointData, CheckpointType


def _memo_cp(chapter: int) -> CheckpointData:
    cp = MagicMock(spec=CheckpointData)
    cp.type = CheckpointType.CHAPTER_MEMO
    cp.chapter = chapter
    return cp


def _project_with_bundle(tmp_path: Path, leader: int, follower: int) -> Path:
    # plans 双章 + sidecar 形状（bundle_chapters 从 staged/live plan 探测束集）
    plans = tmp_path / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    for n in (leader, follower):
        (plans / f"chapter-{n}-plan.md").write_text(f"# 第{n}章 备忘\n", encoding="utf-8")
    st = tmp_path / "staging" / "plans"
    st.mkdir(parents=True, exist_ok=True)
    for n in (leader, follower):
        (st / f"chapter-{n}-plan.md").write_text(f"# 第{n}章 备忘\n", encoding="utf-8")
        (st / f"chapter-{n}-plan-decisions.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_reject_targets_include_follower(tmp_path: Path, monkeypatch) -> None:
    project = _project_with_bundle(tmp_path, 41, 42)
    monkeypatch.setattr("shenbi.pipeline.chapter_loop.bundle_chapters", lambda pd, ch: [ch, 42])
    targets = cli._checkpoint_staging_targets(project, _memo_cp(41))
    assert "plans/chapter-41-plan.md" in targets
    # follower 双件（plan 本体+sidecar）入清理清单——精确名断言（子串会被
    # sidecar 名糊过：chapter-42-plan ⊂ chapter-42-plan-decisions.json）
    assert "plans/chapter-42-plan.md" in targets, targets
    assert "plans/chapter-42-plan-decisions.json" in targets, targets


def test_reject_scope_symmetric_with_commit(tmp_path: Path, monkeypatch) -> None:
    """Symmetry assertion: reject and commit list the same chapter set."""
    import inspect

    project = _project_with_bundle(tmp_path, 41, 42)
    monkeypatch.setattr("shenbi.pipeline.chapter_loop.bundle_chapters", lambda pd, ch: [ch, 42])
    reject_chapters = {
        t.split("chapter-")[1].split("-")[0]
        for t in cli._checkpoint_staging_targets(project, _memo_cp(41))
        if "chapter-" in t and "-plan" in t
    }
    assert reject_chapters == {"41", "42"}
    # commit 分支的 follower 循环源码在场（对称实现锚——两函数同源 bundle_chapters）
    src = inspect.getsource(cli._commit_staging_for_checkpoint)
    assert "bundle_chapters" in src
    src_r = inspect.getsource(cli._checkpoint_staging_targets)
    assert "bundle_chapters" in src_r
