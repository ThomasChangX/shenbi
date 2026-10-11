"""B 批: ledger-generic rolling archival — the thread ledger variant.

outline/thread_map.md accumulates per-weave detail history (交叉点/高潮窗口
grow every volume); at 千万字 scale the ledger is as unbounded as the pool
was. ``archive_ledger(THREAD_SPEC)`` moves RESOLVED thread sections whose
跨度 end is at/below the window verbatim into
``outline/thread_map_archive.md``, leaving a three-bullet tombstone and
dropping the 线索总览表 row — one engine, both ledgers (pool_archive is now
a thin wrapper over the same code path).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.ledger_archive import (
    POOL_SPEC,
    THREAD_SPEC,
    archive_all,
    archive_ledger,
    main,
)

_THREAD_MAP = """---
total_chapters: 118
updated_at: "2026-10-10T03:43:56Z"
---

# 线索地图

---

## 线索总览表

| ID | 名称 | 优先级 | 类型 | max_gap | 起始章 | 终点章 | 状态 |
|----|------|--------|------|---------|--------|--------|------|
| A1 | 灵印与《灵律》残句 | P0 | 长线 | 2 | 1 | 118 | RELEVANT |
| B1 | 断魂水道同源 | P1 | 中线 | 4 | 27 | 109 | PAYING_OFF |
| C1 | 册上多报的名字 | P2 | 短线 | 8 | 3 | 17 | RESOLVED |
| C2 | 拦船验牌 | P2 | 短线 | 8 | 4 | 13 | RESOLVED |
| C3 | 开价与不卖的东西 | P2 | 短线 | 8 | 5 | 14 | RESOLVED |

---

## 线索详情

### A1: 灵印与《灵律》残句

- **状态**: RELEVANT
- **跨度**: 第1章 - 第118章
- **优先级**: P0

### B1: 断魂水道同源

- **状态**: PAYING_OFF
- **跨度**: 第27章 - 第109章
- **优先级**: P1

### C1: 册上多报的名字

- **状态**: RESOLVED
- **跨度**: 第3章 - 第17章
- **优先级**: P2
- **备注**: 替她填名字与替她压格是同一笔债的两面。

### C2: 拦船验牌

- **状态**: RESOLVED
- **跨度**: 第4章 - 第13章
- **优先级**: P2

### C3: 开价与不卖的东西

- **状态**: RESOLVED
- **跨度**: 第5章 - 全书末
- **优先级**: P2

---

## 章节线索推进表

| 章节区间 | 主推 | 备注 |
|---------|------|------|
| 1-8（一卷 KR1） | A1 | 开局 |
"""


def _project(tmp_path: Path) -> Path:
    (tmp_path / "outline").mkdir(parents=True)
    (tmp_path / "outline" / "thread_map.md").write_text(_THREAD_MAP, encoding="utf-8")
    return tmp_path


def test_thread_archive_moves_resolved_sections_verbatim(tmp_path: Path) -> None:
    project = _project(tmp_path)

    archived = archive_ledger(project, 20, THREAD_SPEC)

    # C1 (end 17 ≤ 20) and C2 (end 13 ≤ 20) archive; A1/B1 non-terminal stay;
    # C3's span end is unparseable (全书末) — never archived on a guess.
    assert archived == ["C1", "C2"]
    live = (project / "outline" / "thread_map.md").read_text(encoding="utf-8")
    arc = (project / "outline" / "thread_map_archive.md").read_text(encoding="utf-8")

    assert "### A1: 灵印与《灵律》残句" in live
    # tombstones KEEP the heading (id stays planning-visible) but shed the body
    assert "替她填名字" not in live, "terminal section body removed"
    assert live.count("- **优先级**: P2") == 1, "only C3's section keeps its body"
    assert "- archived_to: outline/thread_map_archive.md" in live, "tombstone left"
    assert "| C1 |" not in live and "| C2 |" not in live, "overview rows dropped"
    assert "| A1 |" in live and "| C3 |" in live

    assert arc.startswith("---\n"), "archive bootstraps frontmatter"
    assert "# 线索地图 · 已归档详情" in arc
    assert "### C1: 册上多报的名字" in arc and "替她填名字" in arc, "verbatim move"
    assert "### C2: 拦船验牌" in arc
    assert "### C3" not in arc

    # rebudget-drill find: the LAST archived entry's span must NOT swallow
    # the sections after 线索详情 — 推进表 and friends must survive.
    assert "## 章节线索推进表" in live
    assert "| 1-8（一卷 KR1） | A1 | 开局 |" in live


def test_thread_archive_is_idempotent(tmp_path: Path) -> None:
    project = _project(tmp_path)
    first = archive_ledger(project, 20, THREAD_SPEC)
    second = archive_ledger(project, 20, THREAD_SPEC)

    assert first == ["C1", "C2"]
    assert second == []


def test_thread_archive_rejects_abnormal_layout(tmp_path: Path) -> None:
    (tmp_path / "outline").mkdir(parents=True)
    (tmp_path / "outline" / "thread_map.md").write_text("# 线索地图\n\n只有 H1\n", encoding="utf-8")
    try:
        archive_ledger(tmp_path, 100, THREAD_SPEC)
    except ValueError as exc:
        assert "线索总览表" in str(exc)
    else:
        raise AssertionError("abnormal layout must degrade loudly")


def test_archive_all_services_both_ledgers(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "truth").mkdir()
    (project / "truth" / "pending_hooks.md").write_text(
        "---\ntype: truth\n---\n\n# 伏笔池\n\n## 总览\n\n| Hook ID（钩子名） | 当前生命周期 | 种植章 |\n"
        "| MH01（灵印） | RESOLVED | 4 |\n\n## 详情\n\n### MH01（灵印）\n\n"
        "- lifecycle_state: RESOLVED\n- resolve_chapter: 30\n",
        encoding="utf-8",
    )

    results = archive_all(project, 40)

    assert results["truth/pending_hooks.md"] == ["MH1"]
    assert results["outline/thread_map.md"] == ["C1", "C2"]
    assert (project / "truth" / "pending_hooks_archive.md").exists()
    assert (project / "outline" / "thread_map_archive.md").exists()


def test_cli_archives_both_ledgers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = _project(tmp_path)
    (project / "truth").mkdir()
    (project / "truth" / "pending_hooks.md").write_text(
        "---\ntype: truth\n---\n\n# 伏笔池\n\n## 总览\n\n| Hook ID（钩子名） | 当前生命周期 |\n"
        "| MH01（灵印） | RESOLVED |\n\n## 详情\n\n### MH01（灵印）\n\n"
        "- lifecycle_state: RESOLVED\n- resolve_chapter: 30\n",
        encoding="utf-8",
    )

    rc = main([str(project), "--resolved-through", "40"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "truth/pending_hooks.md: archived 1: MH1" in out
    assert "outline/thread_map.md: archived 2: C1, C2" in out


def test_archive_last_section_without_trailing_newline(tmp_path: Path) -> None:
    """Review Important #2: the historical replace-by-text silently missed
    when the final archived section had no trailing newline — the row was
    dropped but NO tombstone landed, and every later run re-archived the
    same section into the archive. Span splicing is newline-shape-proof.
    """
    project = _project(tmp_path)
    pool = project / "truth" / "pending_hooks.md"
    pool.parent.mkdir(parents=True, exist_ok=True)
    # terminal hook, file ends WITHOUT trailing newline
    pool.write_text(
        "---\ntype: truth\n---\n\n# 伏笔池\n\n## 总览\n\n| Hook ID（钩子名） | 当前生命周期 |\n"
        "| MH09（回声） | RESOLVED |\n\n## 详情\n\n### MH09（回声）\n\n"
        "- lifecycle_state: RESOLVED\n- resolve_chapter: 30",
        encoding="utf-8",
    )

    first = archive_ledger(project, 40, POOL_SPEC)
    second = archive_ledger(project, 40, POOL_SPEC)

    assert first == ["MH9"]
    assert second == [], "tombstone landed — idempotent on re-run"
    live = pool.read_text(encoding="utf-8")
    assert "- archived_to: truth/pending_hooks_archive.md" in live
    assert "| MH09" not in live
    arc = (project / "truth" / "pending_hooks_archive.md").read_text(encoding="utf-8")
    assert arc.count("### MH09（回声）") == 1, "no duplicate archive entries"
