"""A1 (千万字卷层批): keyed-merge for the outline ledger files.

volume_map / thread_map are volume-boundary TriggerStep writers whose
contracts said ``create_or_overwrite`` — whole-file rewrites that pin the
output cap as the files grow (~10KB/volume; locations/relationships hit the
wall around volume 50, volume_map/thread_map not far behind). The fix is
the pool's proven shape: section increments merged by key.

Locator discipline: volume/thread sections are located by heading level +
编号 (``## 第N卷`` / ``### A1``), NOT by exact heading line — a retitled
heading must replace its section, not append a duplicate (the exact-match
``_replace_section`` seam).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import IncrementShapeError
from shenbi.pipeline.dispatch_helper import _write_parsed_outputs
from shenbi.pipeline.truth_io import touch_frontmatter_updated_at, upsert_markdown_row

_VOLUME_MAP = """---
total_chapters: 118
updated_at: "2026-10-06T13:51:59Z"
---

# 分卷地图

> 章数预算骨架序言。

## 第一卷：哑脉藏火（第 1-23 章）

**Objective**: 卷一目标。

#### KR1: 骨架

- 章节节点表。

## 第二卷：入港（第 24-47 章）

**Objective**: 卷二旧目标。
"""


def test_volume_section_increment_replaces_by_number_despite_retitle() -> None:
    out = upsert_markdown_row(
        _VOLUME_MAP,
        "## 第二卷：新港名（第 24-47 章）\n\n**Objective**: 卷二新目标。\n",
        "volume",
    )
    assert "卷二新目标" in out
    assert "卷二旧目标" not in out, "retitled section replaced, not duplicated"
    assert out.count("## 第二卷") == 1, "no duplicate section"
    assert "第一卷：哑脉藏火" in out, "sibling volumes untouched"
    assert "> 章数预算骨架序言。" in out, "preamble untouched"


def test_new_volume_section_appends_after_last_volume() -> None:
    out = upsert_markdown_row(
        _VOLUME_MAP,
        "## 第三卷：潮汛（第 48-71 章）\n\n**Objective**: 卷三目标。\n",
        "volume",
    )
    assert "## 第三卷：潮汛" in out
    assert out.index("## 第二卷") < out.index("## 第三卷"), "appended in order"


def test_thread_section_increment_locates_by_id() -> None:
    base = """# 线索地图

## 线索详情

### A1: 灵印

- **状态**: PLANTED
"""
    out = upsert_markdown_row(base, "### A1: 灵印之律\n\n- **状态**: RESOLVED\n", "thread")
    assert "- **状态**: RESOLVED" in out
    assert "PLANTED" not in out
    assert out.count("### A1") == 1


def test_touch_frontmatter_updated_at_rewrites_only_that_line() -> None:
    touched = touch_frontmatter_updated_at(_VOLUME_MAP, "2026-10-12T00:00:00Z")
    assert 'updated_at: "2026-10-12T00:00:00Z"' in touched
    assert "total_chapters: 118" in touched, "other frontmatter fields untouched"
    assert touched.count("updated_at") == 1


def test_touch_without_frontmatter_is_noop() -> None:
    assert (
        touch_frontmatter_updated_at("# 无 frontmatter\n", "2026-10-12T00:00:00Z")
        == "# 无 frontmatter\n"
    )


def _outline_project(tmp_path: Path) -> Path:
    (tmp_path / "outline").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outline" / "volume_map.md").write_text(_VOLUME_MAP, encoding="utf-8")
    return tmp_path


def test_dispatch_routes_outline_increment_through_keyed_merge(tmp_path: Path) -> None:
    """The dispatch write path must merge (not whole-file replace) the
    outline target, and mechanically touch the frontmatter updated_at the
    increment no longer carries.
    """
    _outline_project(tmp_path)
    _write_parsed_outputs(
        response=(
            "### FILE: outline/volume_map.md\n"
            "## 第一卷：哑脉藏火·修订（第 1-23 章）\n\n**Objective**: 卷一修订目标。\n"
        ),
        output_paths=["outline/volume_map.md"],
        project_dir=tmp_path,
        skill="shenbi-volume-outlining",
    )
    merged = (tmp_path / "outline" / "volume_map.md").read_text(encoding="utf-8")
    assert "卷一修订目标" in merged
    assert merged.count("## 第一卷") == 1
    assert "## 第二卷" in merged, "other volumes preserved by the merge"
    assert "updated_at" in merged


def test_outline_increment_scaffold_rejected(tmp_path: Path) -> None:
    """Frontmatter / H1 / non-headed prose units are base-destroying
    scaffold for keyed outline targets — reject before any write.
    """
    _outline_project(tmp_path)
    before = (tmp_path / "outline" / "volume_map.md").read_text(encoding="utf-8")
    with pytest.raises(IncrementShapeError):
        _write_parsed_outputs(
            response=(
                "### FILE: outline/volume_map.md\n---\ntotal_chapters: 118\n---\n\n"
                "# 分卷地图\n\n## 第一卷：整档重发\n"
            ),
            output_paths=["outline/volume_map.md"],
            project_dir=tmp_path,
            skill="shenbi-volume-outlining",
        )
    assert (tmp_path / "outline" / "volume_map.md").read_text(encoding="utf-8") == before


def test_outline_increment_prose_unit_rejected(tmp_path: Path) -> None:
    """A unit that is not a keyed section (bare prose) would append at EOF
    and corrupt the file shape — rejected with pointed feedback.
    """
    _outline_project(tmp_path)
    with pytest.raises(IncrementShapeError, match=r"第N卷|卷区段"):
        _write_parsed_outputs(
            response="### FILE: outline/volume_map.md\n裸散文单元，不属于任何卷。\n",
            output_paths=["outline/volume_map.md"],
            project_dir=tmp_path,
            skill="shenbi-volume-outlining",
        )


def test_replay_differential_on_live_volume_map() -> None:
    """A1 replay: the keyed-merge path applied to the REAL 118-chapter
    volume_map must equal a hand-performed section replacement (the
    Phase-3 lesson — production shapes beat synthetic fixtures).
    """
    live = (
        Path(__file__).resolve().parents[3] / "novel-xinghuo-phase3" / "outline" / "volume_map.md"
    )
    if not live.exists():
        pytest.skip("live phase3 project not present")
    import re

    text = live.read_text(encoding="utf-8")
    vols = list(re.finditer(r"^## 第[一二三四五六七八九十\d]+卷：.*$", text, re.MULTILINE))
    assert vols, "live volume_map carries volume sections"
    last_heading = vols[-1].group()
    start = vols[-1].start()
    revised = last_heading.replace("：", "·修订：", 1) + "\n\n**Objective**: 重放差分目标。\n"

    merged = upsert_markdown_row(text, revised, "volume")
    # equivalence: retitled heading replaced in place, everything else identical
    assert merged.count("·修订：") == 1
    assert merged.count(last_heading) == 0, "old heading replaced"
    assert merged[: vols[-2].start()] == text[: vols[-2].start()], "earlier volumes byte-identical"


def test_replay_differential_on_live_thread_map() -> None:
    live = (
        Path(__file__).resolve().parents[3] / "novel-xinghuo-phase3" / "outline" / "thread_map.md"
    )
    if not live.exists():
        pytest.skip("live phase3 project not present")

    text = live.read_text(encoding="utf-8")
    assert "### A1: " in text
    revised = "### A1: 灵印·私修引灵（重放差分）\n\n- **状态**: RESOLVED\n- **当前进度**: 100%\n"

    merged = upsert_markdown_row(text, revised, "thread")
    assert merged.count("### A1: ") == 1, "no duplicate thread section"
    assert "重放差分" in merged
    assert "### A2: " in merged, "sibling threads untouched"


# --- B 批: 推进表区间行 + 总览行禁区 ------------------------------------------

_THREAD_LEDGER = """---
total_chapters: 118
updated_at: "2026-10-10T03:43:56Z"
---

# 线索地图

## 线索总览表

| ID | 名称 | 优先级 | 类型 | max_gap | 起始章 | 终点章 | 状态 |
|----|------|--------|------|---------|--------|--------|------|
| A1 | 灵印 | P0 | 长线 | 2 | 1 | 118 | RELEVANT |

## 线索详情

### A1: 灵印

- **状态**: RELEVANT
- **跨度**: 第1章 - 第118章
- **优先级**: P0

---

## 章节线索推进表

| 章节区间 | 主推 | 副推 | 备注 |
|---------|------|------|------|
| 1-8（一卷 KR1） | A1 | C1 | 开局 |
| 9-16（一卷 KR2） | A2 | B3 | 追索收紧 |
"""


def _thread_project(tmp_path: Path) -> Path:
    (tmp_path / "outline").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outline" / "thread_map.md").write_text(_THREAD_LEDGER, encoding="utf-8")
    return tmp_path


def test_thread_interval_row_increment_merges_in_place(tmp_path: Path) -> None:
    """B 批: the weaver's sanctioned second form — re-emitting an existing
    interval row replaces it in place (dedup on the interval cell); a NEW
    volume's interval row lands in the table without disturbing siblings.
    """
    _thread_project(tmp_path)
    _write_parsed_outputs(
        response=(
            "### FILE: outline/thread_map.md\n"
            "| 9-16（一卷 KR2） | A2 | B3、B5 | 修订后的追索收紧 |\n"
            "| 17-23（一卷 KR3） | A1 | C1 | 顶罪与清算 |\n"
        ),
        output_paths=["outline/thread_map.md"],
        project_dir=tmp_path,
        skill="shenbi-plot-thread-weaver",
    )
    merged = (tmp_path / "outline" / "thread_map.md").read_text(encoding="utf-8")
    assert merged.count("| 9-16（一卷 KR2） |") == 1, "existing interval replaced, not duplicated"
    assert "修订后的追索收紧" in merged
    assert "| 17-23（一卷 KR3） |" in merged, "new interval row appended"
    assert "| 1-8（一卷 KR1） | A1 | C1 | 开局 |" in merged, "sibling rows untouched"
    assert "updated_at" in merged, "frontmatter mechanically touched"
    assert "### A1: 灵印" in merged, "detail sections untouched by row increments"


def test_thread_overview_row_increment_still_rejected(tmp_path: Path) -> None:
    """The 线索总览表 row is derivation-owned — a writer-emitted overview
    row must be rejected (it would bypass the mechanical mirror the merge
    layer applies from the detail section).
    """
    _thread_project(tmp_path)
    before = (tmp_path / "outline" / "thread_map.md").read_text(encoding="utf-8")
    with pytest.raises(IncrementShapeError):
        _write_parsed_outputs(
            response=(
                "### FILE: outline/thread_map.md\n"
                "| B7 | 新开的商路 | P1 | 中线 | 4 | 50 | 80 | PLANTED |\n"
            ),
            output_paths=["outline/thread_map.md"],
            project_dir=tmp_path,
            skill="shenbi-plot-thread-weaver",
        )
    assert (tmp_path / "outline" / "thread_map.md").read_text(encoding="utf-8") == before


def test_volume_target_rejects_interval_row(tmp_path: Path) -> None:
    """The interval-row allowance is key-gated to the thread ledger — the
    same row form in a volume_map increment stays a shape violation.
    """
    _outline_project(tmp_path)
    with pytest.raises(IncrementShapeError):
        _write_parsed_outputs(
            response=("### FILE: outline/volume_map.md\n| 24-31（二卷 KR1） | A1 | 落脚 |\n"),
            output_paths=["outline/volume_map.md"],
            project_dir=tmp_path,
            skill="shenbi-volume-outlining",
        )


def test_thread_section_increment_derives_overview_row_via_dispatch(tmp_path: Path) -> None:
    """End-to-end derivation: a dispatched thread section lands through the
    keyed merge and its 线索总览表 row appears mechanically.
    """
    _thread_project(tmp_path)
    _write_parsed_outputs(
        response=(
            "### FILE: outline/thread_map.md\n"
            "### B7: 新开的商路\n\n- **状态**: PLANTED\n- **跨度**: 第50章 - 第80章\n"
            "- **优先级**: P1\n- **max_gap**: 4\n"
        ),
        output_paths=["outline/thread_map.md"],
        project_dir=tmp_path,
        skill="shenbi-plot-thread-weaver",
    )
    merged = (tmp_path / "outline" / "thread_map.md").read_text(encoding="utf-8")
    row = next(l for l in merged.splitlines() if l.startswith("| B7"))
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    assert cells[0] == "B7" and cells[1] == "新开的商路"
    assert cells[5] == "50" and cells[6] == "80" and cells[7] == "PLANTED"
