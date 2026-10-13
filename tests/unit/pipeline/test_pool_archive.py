"""GO② rolling archival for the pending_hooks evidence pool (phase3 终报:
池内证据滚动归档——千万字时池无界).

The pool's detail sections accumulate per-reinforcement evidence history
without bound (MH01 alone carried thousands of chars of 证据/notes by
ch118; file 94KB at 118 chapters). Terminal hooks (RESOLVED, past the
keep-window) move verbatim to ``truth/pending_hooks_archive.md``, leaving a
three-bullet tombstone + dropping the overview row. Deterministic code, not
an LLM discipline — the same design precedent as drift-guidance's
audit_drift_archive window.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.pool_archive import archive_pool

_POOL = """---
type: truth
category: state
status: active
---

# 伏笔池

## 总览

| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |
|------|------|------|------|------|------|------|------|
| MH01（灵印） | RESOLVED | 4 | 30 | MYSTERY | 0.5 | 10 | STAIRCASE |
| MH02（灵誓） | RESOLVED | 38 | 95 | RULE | 0.5 | 12 | RISING |
| MH03（回声） | PARTIAL | 36 |  | INFORMATION | 0.6 | 12 | STAIRCASE |
| CP-001（册末空格） | RESOLVED | 3 | 17 | INFORMATION | 0.5 | 14 | STAIRCASE |

## 详情

### MH01（灵印）

- type: MYSTERY
- lifecycle_state: RESOLVED
- plant_chapter: 4
- resolve_chapter: 30
- 证据: 第4章种植。第12章强化。第30章兑现。

### MH02（灵誓）

- type: RULE
- lifecycle_state: RESOLVED
- plant_chapter: 38
- resolve_chapter: 95

### MH03（回声）

- type: INFORMATION
- lifecycle_state: PARTIAL
- plant_chapter: 36

### CP-001（册末空格）

- type: INFORMATION
- lifecycle_state: RESOLVED
- plant_chapter: 3
- resolve_chapter: 17
"""


def _write_pool(tmp_path: Path) -> None:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "pending_hooks.md").write_text(_POOL, encoding="utf-8")


def test_archive_moves_terminal_sections_past_window(tmp_path: Path) -> None:
    _write_pool(tmp_path)
    archived = archive_pool(tmp_path, resolved_through=90)

    # MH01 (resolve 30 <= 90) and CP-001 (17 <= 90) archived; MH02 (95) and
    # the PARTIAL MH03 stay live.
    assert archived == ["MH1", "CP1"]  # canon_hook_id form

    live = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
    assert "| MH01（灵印） |" not in live, "archived hook's overview row dropped"
    assert "| CP-001（册末空格） |" not in live
    assert "| MH02（灵誓） | RESOLVED |" in live
    assert "- 证据: 第4章种植。" not in live, "evidence bulk left the live pool"
    tomb = next(l for l in live.splitlines() if l.startswith("### MH01"))
    assert tomb == "### MH01（灵印）"
    mh01_block = live.split("### MH01（灵印）", 1)[1].split("###", 1)[0]
    assert "- lifecycle_state: RESOLVED" in mh01_block
    assert "- resolve_chapter: 30" in mh01_block
    assert "- archived_to: truth/pending_hooks_archive.md" in mh01_block
    assert "已归档" in live, "archive count note under 总览"


def test_archive_file_carries_sections_verbatim(tmp_path: Path) -> None:
    _write_pool(tmp_path)
    archive_pool(tmp_path, resolved_through=90)

    archive = (tmp_path / "truth" / "pending_hooks_archive.md").read_text(encoding="utf-8")
    assert archive.startswith("---\n"), "frontmatter present (program invariant)"
    assert "### MH01（灵印）" in archive
    assert "- 证据: 第4章种植。第12章强化。第30章兑现。" in archive, "verbatim move, not summary"
    assert "### CP-001（册末空格）" in archive


def test_archive_is_idempotent(tmp_path: Path) -> None:
    _write_pool(tmp_path)
    assert archive_pool(tmp_path, resolved_through=90) == ["MH1", "CP1"]
    live_before = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
    arc_before = (tmp_path / "truth" / "pending_hooks_archive.md").read_text(encoding="utf-8")

    assert archive_pool(tmp_path, resolved_through=90) == []
    assert (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8") == live_before
    assert (tmp_path / "truth" / "pending_hooks_archive.md").read_text(
        encoding="utf-8"
    ) == arc_before


def test_growing_window_archives_more_without_duplicating(tmp_path: Path) -> None:
    _write_pool(tmp_path)
    archive_pool(tmp_path, resolved_through=90)
    assert archive_pool(tmp_path, resolved_through=95) == ["MH2"]

    archive = (tmp_path / "truth" / "pending_hooks_archive.md").read_text(encoding="utf-8")
    assert archive.count("### MH01（灵印）") == 1, "no duplicate on window growth"


def test_malformed_pool_raises(tmp_path: Path) -> None:
    (tmp_path / "truth").mkdir(parents=True)
    (tmp_path / "truth" / "pending_hooks.md").write_text("no sections here\n", encoding="utf-8")
    import pytest

    with pytest.raises(ValueError, match="总览"):
        archive_pool(tmp_path, resolved_through=90)
