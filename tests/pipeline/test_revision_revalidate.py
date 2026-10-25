"""spec #72 T7: post-revision revalidation + G6 pre-rev exclusion (G0.9 §4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.chapter_loop import _revalidate_revised_chapter

CW = json.dumps({"chapter_word": {"default": 3200, "min": 2800, "max": 4000}})
HOOK1 = "他把数目又数了一遍？"
HOOK2 = "门在身后合上了，他为什么没回头？"


def _mk(
    tmp_path: Path,
    body_scenes: list[tuple[int, str]],
    markers: int | None = None,
    plan_hooks: list[str] | None = None,
) -> Path:
    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    d = tmp_path / "chapters"
    d.mkdir(exist_ok=True)
    parts = ["## PRE_WRITE_CHECK", "", "- x", "", "# 第1章", "# 章题", ""]
    for i, (size, hook) in enumerate(body_scenes):
        if markers is None or i < markers:
            parts.append("<!--SCENE-->")
        parts += ["灯" * size, hook, ""]
    parts += ["## POST_WRITE_SELF_CHECK", "", "- y", ""]
    ch = d / "chapter-1.md"
    ch.write_text("\n".join(parts), encoding="utf-8")
    if plan_hooks:
        pd = tmp_path / "plans"
        pd.mkdir(exist_ok=True)
        lines = ["# 备忘", ""]
        lines += ["### 场景预算与收束钩（#72 粒度契约）", ""]
        for i, h in enumerate(plan_hooks, 1):
            lines.append(f"- 场景{i}: 1900字｜独立型｜收束钩：{h}")
        (pd / "chapter-1-plan.md").write_text("\n".join(lines), encoding="utf-8")
    return ch


@pytest.mark.unit
def test_clean_revision_passes(tmp_path: Path) -> None:
    ch = _mk(tmp_path, [(1900, HOOK1), (1900, HOOK2)], plan_hooks=[HOOK1, HOOK2])
    backup = tmp_path / "chapters" / "chapter-1-pre-rev.md"
    backup.write_text(ch.read_text(encoding="utf-8"), encoding="utf-8")
    assert _revalidate_revised_chapter(tmp_path, 1) == []


@pytest.mark.unit
def test_marker_deleted_fails(tmp_path: Path) -> None:
    ch = _mk(tmp_path, [(1900, HOOK1), (1900, HOOK2)])
    backup = tmp_path / "chapters" / "chapter-1-pre-rev.md"
    backup.write_text(ch.read_text(encoding="utf-8"), encoding="utf-8")
    # 修订后删一个标记
    revised = ch.read_text(encoding="utf-8").replace("<!--SCENE-->", "", 1)
    ch.write_text(revised, encoding="utf-8")
    issues = _revalidate_revised_chapter(tmp_path, 1)
    assert any("标记数变化" in i for i in issues)


@pytest.mark.unit
def test_hook_line_rewritten_fails(tmp_path: Path) -> None:
    ch = _mk(tmp_path, [(1900, HOOK1), (1900, HOOK2)], plan_hooks=[HOOK1, HOOK2])
    backup = tmp_path / "chapters" / "chapter-1-pre-rev.md"
    backup.write_text(ch.read_text(encoding="utf-8"), encoding="utf-8")
    revised = ch.read_text(encoding="utf-8").replace(HOOK1, "完全不同的改写句？")
    ch.write_text(revised, encoding="utf-8")
    issues = _revalidate_revised_chapter(tmp_path, 1)
    assert any("钩被改写" in i for i in issues)


@pytest.mark.unit
def test_band_drift_fails(tmp_path: Path) -> None:
    ch = _mk(tmp_path, [(1900, HOOK1), (1900, HOOK2)])
    backup = tmp_path / "chapters" / "chapter-1-pre-rev.md"
    backup.write_text(ch.read_text(encoding="utf-8"), encoding="utf-8")
    # 修订把正文缩到带外（merge_prose 删减模拟）
    revised = ch.read_text(encoding="utf-8").replace("灯" * 1900, "灯" * 900)
    ch.write_text(revised, encoding="utf-8")
    issues = _revalidate_revised_chapter(tmp_path, 1)
    assert any("字数带漂移" in i for i in issues)


@pytest.mark.unit
def test_g6_excludes_pre_rev_backups(tmp_path: Path) -> None:
    """R4-I6 via the REAL gate: backups must not inflate G6.1 nor duplicate
    ids in G6.2 (tautology-free -- reverting the filter in g6.py turns red).
    """
    import json as _json

    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    (tmp_path / "novel.json").write_text(
        _json.dumps({"target_word_count": 10_000_000}), encoding="utf-8"
    )
    d = tmp_path / "chapters"
    d.mkdir()
    (d / "chapter-1.md").write_text("# 第1章\n\n灯" * 100, encoding="utf-8")
    (d / "chapter-1-pre-rev.md").write_text("# 第1章\n\n灯" * 100, encoding="utf-8")
    from shenbi.gates.g6 import gate_G6

    result = gate_G6("long-form", str(tmp_path), str(tmp_path))
    parsed = json.loads(result)
    mfs = [str(m) for m in parsed.get("must_fix", [])]
    # 计数 = 1（备份不计入；过滤还原则 G6.1 变 2<… 或 G6.2 重复章号违例）
    assert any(m.startswith("G6.1:1<") for m in mfs)
    assert not any(m.startswith("G6.2:") for m in mfs)


@pytest.mark.unit
def test_scene_body_swap_fails_hook_order(tmp_path: Path) -> None:
    """Scene-body swap (observable marker-reorder variant): hook-order
    mismatch must be caught by revalidation.
    """
    ch = _mk(tmp_path, [(1900, HOOK1), (1900, HOOK2)], plan_hooks=[HOOK1, HOOK2])
    backup = tmp_path / "chapters" / "chapter-1-pre-rev.md"
    backup.write_text(ch.read_text(encoding="utf-8"), encoding="utf-8")
    text = ch.read_text(encoding="utf-8")
    s1 = "灯" * 1900 + "\n" + HOOK1
    s2 = "灯" * 1900 + "\n" + HOOK2
    revised = text.replace(s1, "@@TMP@@").replace(s2, s1).replace("@@TMP@@", s2)
    ch.write_text(revised, encoding="utf-8")
    issues = _revalidate_revised_chapter(tmp_path, 1)
    assert any("钩" in i for i in issues)
