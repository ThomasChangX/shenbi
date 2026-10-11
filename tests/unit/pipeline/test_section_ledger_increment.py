"""A2 (千万字卷层批): keyed-merge for the section-ledger files.

world/locations.md (``## 地点:<名>`` entries, 49KB at 118 ch) and
characters/relationships.md (``## 关系对:A - B`` sections + the derived
关系矩阵, 44KB) were create_or_overwrite whole-file rewrites — the first
walls at ~50 volumes. The fix: ``##``-boundary section increments (embedded
功能事件 tables stay ATOMIC — the generic row splitter would shred them),
plus the GO① derivation for the 关系矩阵 (each pair section carries a
``**矩阵格**:`` line; the merge reflects it into both matrix cells and
grows rows/columns for new characters). relationship-map's
truth/character_matrix.md update joins the existing composite-key row
channel (the same target state-settling already declares).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import IncrementShapeError
from shenbi.pipeline.dispatch_helper import _section_ledger_units, _write_parsed_outputs
from shenbi.pipeline.truth_io import sync_relationship_matrix, upsert_markdown_row

_LOCATIONS = """# 地点图谱

> 生成时间：2026-10-10T03:39:40Z
> 本文件由 `shenbi-location-builder` 更新。

---

## 核心地点（承接世界观构建，描述原文保留）

- **苍麓城**：中枢之城。

---

## 地点：哑脉采掘场

**类型**: 矿场（采掘场）
**首次出场**: 第1章

### 空间布局

矿道铺开。

### 功能事件

| 章节 | 事件 | 功能类型 |
|------|------|---------|
| 第1章 | 深脉里递灯 | 情感 |
| 第4章 | 本能引灵救同伴 | 转折 |
"""

_RELATIONSHIPS = """---
name: relationships
---

# 关系图谱

> 本文件是角色关系的权威源。

---

## 关系矩阵（角色 × 角色）

| 角色 | 阿烬 | 阿石 |
|------|------|------|
| 阿烬 | — | 养育/师徒→遗志 |
| 阿石 | 养育/师徒→遗志 | — |

> 表中「无」表示二者在卷纲范围内无直接关系对，非敌对。

---

## 关系对：阿烬 - 阿石

**类型**: 养育 / 师徒
**矩阵格**: 养育/师徒→遗志
**信息边界**: ASYMMETRIC

---

## 第47章扩容复核（卷二卷终）

本界不新增关系对。
"""


def test_section_ledger_units_keep_embedded_tables_atomic() -> None:
    units = _section_ledger_units(_LOCATIONS.split("---", 2)[2])
    loc_units = [u for u in units if u.startswith("## 地点：")]
    assert len(loc_units) == 1, "one location section"
    assert "| 第1章 | 深脉里递灯 | 情感 |" in loc_units[0], "embedded table stays in-section"
    assert "| 第4章 |" in loc_units[0]


def test_location_section_increment_replaces_and_appends(tmp_path: Path) -> None:
    (tmp_path / "world").mkdir(parents=True)
    (tmp_path / "world" / "locations.md").write_text(_LOCATIONS, encoding="utf-8")
    before_core = "- **苍麓城**：中枢之城。"

    _write_parsed_outputs(
        response=(
            "### FILE: world/locations.md\n"
            "## 地点：哑脉采掘场\n\n**类型**: 矿场（采掘场）\n**首次出场**: 第1章\n\n"
            "### 功能事件\n\n| 章节 | 事件 | 功能类型 |\n|------|------|---------|\n"
            "| 第1章 | 深脉里递灯 | 情感 |\n| 第4章 | 本能引灵救同伴 | 转折 |\n| 第9章 | 封深脉 | 升级 |\n\n"
            "## 地点：鹄港\n\n**类型**: 港口\n**首次出场**: 第24章\n"
        ),
        output_paths=["world/locations.md"],
        project_dir=tmp_path,
        skill="shenbi-location-builder",
    )
    merged = (tmp_path / "world" / "locations.md").read_text(encoding="utf-8")

    assert merged.count("## 地点：哑脉采掘场") == 1, "existing entry replaced, not duplicated"
    assert "| 第9章 | 封深脉 | 升级 |" in merged, "table history preserved + appended"
    assert "| 第1章 | 深脉里递灯 |" in merged
    assert "## 地点：鹄港" in merged, "new entry appended"
    assert before_core in merged, "genesis-static core block untouched"
    assert "生成时间" in merged, "preamble untouched"


def test_location_scaffold_rejected(tmp_path: Path) -> None:
    (tmp_path / "world").mkdir(parents=True)
    (tmp_path / "world" / "locations.md").write_text(_LOCATIONS, encoding="utf-8")
    before = (tmp_path / "world" / "locations.md").read_text(encoding="utf-8")
    with pytest.raises(IncrementShapeError):
        _write_parsed_outputs(
            response=(
                "### FILE: world/locations.md\n# 地点图谱\n\n## 核心地点（重发）\n\n- **x**：y。\n"
            ),
            output_paths=["world/locations.md"],
            project_dir=tmp_path,
            skill="shenbi-location-builder",
        )
    assert (tmp_path / "world" / "locations.md").read_text(encoding="utf-8") == before


def test_relation_pair_section_updates_matrix_both_directions() -> None:
    out = upsert_markdown_row(
        _RELATIONSHIPS,
        "## 关系对：阿烬 - 阿石\n\n**类型**: 养育 / 师徒\n**矩阵格**: 养育→同盟\n**信息边界**: SYMMETRIC\n",
        "relation",
    )
    assert "| 阿烬 | — | 养育→同盟 |" in out
    assert "| 阿石 | 养育→同盟 | — |" in out
    assert "表中「无」表示" in out, "post-table note preserved"


def test_new_pair_grows_matrix_row_and_column(tmp_path: Path) -> None:
    (tmp_path / "characters").mkdir(parents=True)
    (tmp_path / "characters" / "relationships.md").write_text(_RELATIONSHIPS, encoding="utf-8")

    _write_parsed_outputs(
        response=(
            "### FILE: characters/relationships.md\n"
            "## 关系对：阿烬 - 桑渡\n\n**类型**: 暗中间谋\n**矩阵格**: 暗中间谋（敌手起头）\n"
        ),
        output_paths=["characters/relationships.md"],
        project_dir=tmp_path,
        skill="shenbi-relationship-map",
    )
    merged = (tmp_path / "characters" / "relationships.md").read_text(encoding="utf-8")

    header = next(l for l in merged.splitlines() if l.startswith("| 角色 |"))
    assert header.count("桑渡") == 1 and header.rstrip().endswith("桑渡 |"), "column appended"
    sang_row = next(l for l in merged.splitlines() if l.startswith("| 桑渡 |"))
    cells = [c.strip() for c in sang_row.strip().strip("|").split("|")]
    assert cells[1] == "暗中间谋（敌手起头）", "new pair cell derived"
    assert cells[3] == "—", "diagonal stays —"
    shi_row = next(l for l in merged.splitlines() if l.startswith("| 阿石 |"))
    assert shi_row.rstrip().endswith("| 无 |"), "existing rows grow the new column with 无"
    assert merged.count("## 关系对：阿烬 - 桑渡") == 1


def test_matrix_emission_rejected(tmp_path: Path) -> None:
    (tmp_path / "characters").mkdir(parents=True)
    (tmp_path / "characters" / "relationships.md").write_text(_RELATIONSHIPS, encoding="utf-8")
    before = (tmp_path / "characters" / "relationships.md").read_text(encoding="utf-8")
    with pytest.raises(IncrementShapeError):
        _write_parsed_outputs(
            response=(
                "### FILE: characters/relationships.md\n"
                "## 关系矩阵（角色 × 角色）\n\n| 角色 | 阿烬 |\n|------|------|\n| 阿烬 | — |\n"
            ),
            output_paths=["characters/relationships.md"],
            project_dir=tmp_path,
            skill="shenbi-relationship-map",
        )
    assert (tmp_path / "characters" / "relationships.md").read_text(encoding="utf-8") == before


def test_boundary_review_section_appends_once(tmp_path: Path) -> None:
    (tmp_path / "characters").mkdir(parents=True)
    (tmp_path / "characters" / "relationships.md").write_text(_RELATIONSHIPS, encoding="utf-8")
    _write_parsed_outputs(
        response=(
            "### FILE: characters/relationships.md\n"
            "## 第70章扩容复核（卷三卷终 · 弧五）\n\n本界不新增命名角色。\n"
        ),
        output_paths=["characters/relationships.md"],
        project_dir=tmp_path,
        skill="shenbi-relationship-map",
    )
    merged = (tmp_path / "characters" / "relationships.md").read_text(encoding="utf-8")
    assert "## 第70章扩容复核（卷三卷终 · 弧五）" in merged
    assert "## 第47章扩容复核（卷二卷终）" in merged, "prior review preserved"


def test_character_matrix_row_increment_merges_composite_key(tmp_path: Path) -> None:
    (tmp_path / "truth").mkdir(parents=True)
    (tmp_path / "truth" / "character_matrix.md").write_text(
        "---\ntype: truth\ncategory: character\n---\n\n# 角色交互矩阵\n\n## 交互总表\n\n"
        "| 角色A | 角色B | 关系 | 最近交互 | 最近变化 |\n|-------|-------|------|---------|---------|\n"
        "| 阿烬 | 阿石 | 养育 | 第18章 顶罪 | 灯绳系腕 |\n",
        encoding="utf-8",
    )
    _write_parsed_outputs(
        response=(
            "### FILE: truth/character_matrix.md\n"
            "| 阿烬 | 阿石 | 养育 | 第18章 顶罪；第75章 灯边打结 | 灯绳系腕；绳账记日常 |\n"
        ),
        output_paths=["truth/character_matrix.md"],
        project_dir=tmp_path,
        skill="shenbi-relationship-map",
    )
    merged = (tmp_path / "truth" / "character_matrix.md").read_text(encoding="utf-8")
    assert merged.count("| 阿烬 | 阿石 |") == 1, "composite-key row replaced in place"
    assert "第75章 灯边打结" in merged


def test_sync_relationship_matrix_noop_without_cell_fields() -> None:
    live_like = _RELATIONSHIPS.replace("**矩阵格**: 养育/师徒→遗志\n", "")
    assert sync_relationship_matrix(live_like) == live_like


def test_sync_relationship_matrix_noop_without_matrix_table() -> None:
    no_matrix = "# 关系图谱\n\n## 关系对：阿烬 - 阿石\n\n**矩阵格**: x\n"
    assert sync_relationship_matrix(no_matrix) == no_matrix


def test_replay_on_live_section_ledgers() -> None:
    """Idempotence on the REAL 118-chapter ledgers: the live files carry no
    矩阵格 fields yet (pre-A2 genesis output), so the derivation must be a
    byte-identical no-op, and a section replaced with itself must not
    duplicate (production shapes beat synthetic fixtures).
    """
    root = Path(__file__).resolve().parents[3] / "novel-xinghuo-phase3"
    rel = root / "characters" / "relationships.md"
    loc = root / "world" / "locations.md"
    if not rel.exists() or not loc.exists():
        pytest.skip("live phase3 project not present")

    rel_text = rel.read_text(encoding="utf-8")
    assert sync_relationship_matrix(rel_text) == rel_text

    import re

    headings = list(re.finditer(r"^## 地点：.+$", loc.read_text(encoding="utf-8"), re.MULTILINE))
    assert headings, "live locations carry entry sections"
    loc_text = loc.read_text(encoding="utf-8")
    first = headings[0].group()
    section = loc_text[loc_text.find(first) : loc_text.find("\n## ", loc_text.find(first))]
    merged = upsert_markdown_row(loc_text, section.rstrip() + "\n", "location")
    assert merged.count(first) == 1, "self-replacement does not duplicate"
    assert len(merged) >= len(loc_text) - 2
