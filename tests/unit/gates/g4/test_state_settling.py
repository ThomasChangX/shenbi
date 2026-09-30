"""Bespoke error-path tests for g4_state_settling.

state_settling dispatches checks based on filenames containing
keywords: current_state, character_matrix, etc. Each test exercises
one business rule by naming the test file appropriately.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.state_settling import g4_state_settling


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_state_settling(fps, rd))


@pytest.mark.unit
def test_fails_when_current_state_missing_position(tmp_path: Path) -> None:
    """File named current_state without position markers -> WARN G4.ss.position (relaxed from FAIL)."""
    f = tmp_path / "current_state.md"
    f.write_text("# State\n\nNo position info.\n", encoding="utf-8")
    result = _run([str(f)])
    # Position check is now a WARN quality target, check ID renamed
    assert any(
        c["id"] == "G4.ss.position" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.ss.position WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_passes_when_current_state_has_position(tmp_path: Path) -> None:
    """File named current_state with ## 位置 -> PASS G4.ss.position."""
    f = tmp_path / "current_state.md"
    f.write_text("# State\n\n## 位置\n森林深处\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.position" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_character_matrix_missing_chars(tmp_path: Path) -> None:
    """File named character_matrix without character sections -> WARN G4.ss.characters (relaxed from FAIL)."""
    f = tmp_path / "character_matrix.md"
    f.write_text("# Matrix\nNo characters here.\n", encoding="utf-8")
    result = _run([str(f)])
    # Character check is now a WARN quality target, check ID renamed
    assert any(
        c["id"] == "G4.ss.characters" and c["s"] == "WARN" for c in result.get("checks", [])
    ), f"Expected G4.ss.characters WARN in checks, got {result.get('checks', [])}"


@pytest.mark.unit
def test_passes_when_character_matrix_has_chars(tmp_path: Path) -> None:
    """File named character_matrix with ## 角色 -> PASS."""
    f = tmp_path / "character_matrix.md"
    f.write_text("# Matrix\n\n## 角色\n主角\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.characters" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_fails_when_pending_hooks_missing_state_keyword(tmp_path: Path) -> None:
    """File named pending_hooks without 'state' keyword -> FAIL."""
    f = tmp_path / "pending_hooks.md"
    f.write_text("# Hooks\n\ndraft content\n", encoding="utf-8")
    result = _run([str(f)])
    assert result["status"] == "FAIL"
    assert any("G4.ss.no_hook_state" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_fails_when_file_not_found(tmp_path: Path) -> None:
    """Missing file -> FAIL G4.ss.not_found."""
    result = _run([str(tmp_path / "nonexistent.md")])
    assert result["status"] == "FAIL"
    assert any("G4.ss.not_found" in mf for mf in result["must_fix"])


@pytest.mark.unit
def test_skips_on_empty_fps(tmp_path: Path) -> None:
    """Empty fps list -> SKIP."""
    result = _run([])
    assert any(c["id"] == "G4.ss" and c["s"] == "SKIP" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_all_conditions_met(tmp_path: Path) -> None:
    """current_state + character_matrix + pending_hooks all valid -> PASS."""
    d = tmp_path / "sub"
    d.mkdir()
    cs = d / "current_state.md"
    cs.write_text("## 位置变化\n移动\n", encoding="utf-8")
    cm = d / "character_matrix.md"
    cm.write_text("## 已登场角色\n英雄\n", encoding="utf-8")
    ph = d / "pending_hooks.md"
    ph.write_text("state: active\n", encoding="utf-8")
    result = _run([str(cs), str(cm), str(ph)])
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_passes_when_chapter_summaries_has_chapter_headings(tmp_path: Path) -> None:
    """chapter_summaries with '## 第N章' -> PASS G4.ss.summaries (covers g4 40-43)."""
    f = tmp_path / "chapter_summaries.md"
    f.write_text("# Summaries\n\n## 第1章\n内容概括。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.summaries" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_emotional_arcs_has_chapter_headings(tmp_path: Path) -> None:
    """emotional_arcs with '### 第N章' -> PASS G4.ss.arcs (covers g4 46-49)."""
    f = tmp_path / "emotional_arcs.md"
    f.write_text("# Arcs\n\n### 第1章\n情感变化。\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.arcs" and c["s"] == "PASS" for c in result["checks"])


@pytest.mark.unit
def test_passes_when_particle_ledger_has_particle_section(tmp_path: Path) -> None:
    """particle_ledger with '## 粒子账本' -> PASS G4.ss.particle_ledger (covers g4 52-55)."""
    f = tmp_path / "particle_ledger.md"
    f.write_text("# Ledger\n\n## 粒子账本\n- 粒子甲\n", encoding="utf-8")
    result = _run([str(f)])
    assert any(c["id"] == "G4.ss.particle_ledger" and c["s"] == "PASS" for c in result["checks"])


# ── Task 6: Character Matrix Write-Protection ──────────────────────────────


@pytest.mark.unit
def test_state_settling_character_matrix_protection():
    """state_settling prevents parameter agent names in character_matrix."""
    from shenbi.gates.g4.state_settling import _validate_character_matrix

    content = """---
update_mode: replace
---

# Character Matrix

## 角色定义
- 林烽: 主角
- 陈为民: 配角

## Ch50 State
- 冷: 参数化存在
- 光: 格式层出现
"""
    issues = _validate_character_matrix(
        content, known_parameter_agents={"冷", "光", "安静", "缺口"}
    )
    assert len(issues) > 0
    assert "parameter_agent" in issues[0].lower()


# ── Task 9: Character Matrix Template & arc_log ──────────────────────────


def test_character_matrix_template_has_slug_column():
    matrix_path = (
        Path(__file__).resolve().parents[4] / "_templates" / "truth" / "character_matrix.md"
    )
    assert matrix_path.exists(), "character_matrix.md must exist (F712: stale skip)"
    content = matrix_path.read_text(encoding="utf-8")
    assert "Slug" in content
    assert "Current State" in content
    assert "Arc Stage" in content
    assert "Last Updated Ch" in content


def test_state_settling_skill_mentions_character_matrix():
    skill_path = (
        Path(__file__).resolve().parents[4] / "skills" / "shenbi-state-settling" / "SKILL.md"
    )
    content = skill_path.read_text(encoding="utf-8")
    assert "character_matrix" in content


def test_state_settling_skill_mentions_arc_log():
    skill_path = (
        Path(__file__).resolve().parents[4] / "skills" / "shenbi-state-settling" / "SKILL.md"
    )
    content = skill_path.read_text(encoding="utf-8")
    assert "arc_log" in content
    # F870 (spec #58): the out-of-contract protagonist.md write instruction
    # is removed — arc progression lands in character_matrix only.
    assert "append an `arc_log` entry" not in content


# ---------------------------------------------------------------------------
# Probe session 2026-09-29 (Stage 2 friction): character_matrix template
# regeneration burned 12 settle cycles (live 100+ lines collapsed to 24-40
# line templates — 信息边界 R1-R28 and all Re-sync history deleted) while
# G4 PASSed vacuously; produced_at was fabricated four times (12:00:00Z
# placeholders, a future-dated 2026-10-04) with zero capture.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fails_when_staged_matrix_collapses_vs_live(tmp_path: Path) -> None:
    """A staged character_matrix with <90% of the live file's non-empty
    lines is a template regeneration, not an increment — fail loud.
    """
    live = tmp_path / "truth" / "character_matrix.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        "---\ntype: truth\n---\n\n## 角色定义\n\n角色行×12\n\n## 信息边界\n\nR1-R28\n\n## 第3章 Re-sync\n"
        + "\n".join(f"行 {i}" for i in range(120)),
        encoding="utf-8",
    )
    staged = tmp_path / "staging" / "truth" / "character_matrix.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "---\ntype: truth\n---\n\n## 角色\n\n角色行×3\n\n## 本章新知\n", encoding="utf-8"
    )

    result = _run([str(staged)], str(tmp_path))
    mf = result.get("must_fix", [])

    assert result["status"] == "FAIL"
    assert any("G4.ss.matrix_structure" in m and "line_collapse" in m for m in mf)


@pytest.mark.unit
def test_fails_when_staged_matrix_drops_boundary_or_resync(tmp_path: Path) -> None:
    """Same line count but the 信息边界 section or Re-sync history vanished
    — structure loss the line-count ratio alone cannot see.
    """
    body = "\n".join(f"行 {i}" for i in range(80))
    live = tmp_path / "truth" / "character_matrix.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        f"---\ntype: truth\n---\n\n## 角色定义\n\n{body}\n\n## 信息边界\n\nR1..R28\n\n## 第3章 Re-sync 记录\n\n## 第4章 Re-sync 记录\n",
        encoding="utf-8",
    )
    staged = tmp_path / "staging" / "truth" / "character_matrix.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        f"---\ntype: truth\n---\n\n## 角色定义\n\n{body}\n\n## 本章增量\n\nR1..R28 压缩为一段散文填充行数。\n",
        encoding="utf-8",
    )

    result = _run([str(staged)], str(tmp_path))
    mf = result.get("must_fix", [])

    assert any("G4.ss.matrix_structure" in m and "content_dropped" in m for m in mf)


@pytest.mark.unit
def test_passes_when_staged_matrix_is_structural_increment(tmp_path: Path) -> None:
    """Live + new chapter rows + one more Re-sync heading passes."""
    body = "\n".join(f"行 {i}" for i in range(80))
    live = tmp_path / "truth" / "character_matrix.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        f"---\ntype: truth\n---\n\n## 角色定义\n\n{body}\n\n## 信息边界\n\nR1..R28\n\n## 第3章 Re-sync 记录\n",
        encoding="utf-8",
    )
    staged = tmp_path / "staging" / "truth" / "character_matrix.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        f"---\ntype: truth\n---\n\n## 角色定义\n\n{body}\n新章角色行\n\n## 信息边界\n\nR1..R28\n\n## 第3章 Re-sync 记录\n\n## 第4章 Re-sync 记录\n",
        encoding="utf-8",
    )

    result = _run([str(staged)], str(tmp_path))
    assert not any("G4.ss.matrix_structure" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_fails_on_placeholder_produced_at(tmp_path: Path) -> None:
    """12:00:00Z / 00:00:00Z whole-hour placeholders are the four-times
    fabricated form — fail loud.
    """
    dec = tmp_path / "staging" / "truth" / "state-settling-decisions.json"
    dec.parent.mkdir(parents=True)
    dec.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 5,
                "produced_at": "2026-09-28T12:00:00Z",
                "selections": [],
            }
        ),
        encoding="utf-8",
    )

    result = _run([str(dec)], str(tmp_path))
    assert any("G4.ss.produced_at" in m and "placeholder" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_fails_on_future_produced_at(tmp_path: Path) -> None:
    """A produced_at in the future (probe: 2026-10-04 while running
    2026-09-28) is fabricated.
    """
    dec = tmp_path / "staging" / "truth" / "state-settling-decisions.json"
    dec.parent.mkdir(parents=True)
    dec.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 5,
                "produced_at": "2099-01-01T01:02:03Z",
                "selections": [],
            }
        ),
        encoding="utf-8",
    )

    result = _run([str(dec)], str(tmp_path))
    assert any("G4.ss.produced_at" in m and "future" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_passes_on_real_produced_at(tmp_path: Path) -> None:
    dec = tmp_path / "staging" / "truth" / "state-settling-decisions.json"
    dec.parent.mkdir(parents=True)
    dec.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 5,
                "produced_at": "2026-09-29T05:37:46Z",
                "selections": [],
            }
        ),
        encoding="utf-8",
    )

    result = _run([str(dec)], str(tmp_path))
    assert not any("G4.ss.produced_at" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_fails_when_staged_matrix_replaces_sections_same_size(tmp_path: Path) -> None:
    """Fixcheck ch1/ch2: a same-size-or-bigger FORMAT REPLACEMENT passes the
    0.9x line check while dropping every live section — the settle writer
    restructured the matrix into a self-invented schema three times. The
    staged file must preserve the live H2 section set (appends allowed).
    """
    live = tmp_path / "truth" / "character_matrix.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        "---\ntype: truth\n---\n\n## 一、角色交互总表\n\n"
        + "\n".join(f"角色对 {i}" for i in range(23))
        + "\n\n## 三、信息边界矩阵（权威）\n\n"
        + "\n".join(f"边界 {i}" for i in range(23))
        + "\n\n## 四、待追踪的信息差清单\n\n"
        + "\n".join(f"信息差 {i}" for i in range(11)),
        encoding="utf-8",
    )
    # replacement schema: MORE lines than live, zero live sections
    staged = tmp_path / "staging" / "truth" / "character_matrix.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "---\ntype: truth\n---\n\n## 角色定义\n\n"
        + "\n".join(f"定义 {i}" for i in range(40))
        + "\n\n## 状态追踪表\n\n"
        + "\n".join(f"状态 {i}" for i in range(40)),
        encoding="utf-8",
    )

    result = _run([str(staged)], str(tmp_path))
    mf = result.get("must_fix", [])
    assert result["status"] == "FAIL"
    assert any("G4.ss.matrix_structure" in m and "content_dropped" in m for m in mf)


@pytest.mark.unit
def test_passes_when_staged_matrix_keeps_sections_and_appends(tmp_path: Path) -> None:
    """Superset semantics: live sections verbatim + a new appended section
    (e.g. the ch1-approved 逐章角色状态) must pass.
    """
    body = "\n".join(f"行 {i}" for i in range(60))
    live = tmp_path / "truth" / "character_matrix.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        "---\ntype: truth\n---\n\n## 二、角色交互总表\n\n"
        f"{body}\n\n## 三、信息边界矩阵（权威）\n\n"
        "| 边界 | 状态 |\n|---|---|\n| R1..R28 | 已核 |\n",
        encoding="utf-8",
    )
    staged = tmp_path / "staging" / "truth" / "character_matrix.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "---\ntype: truth\n---\n\n## 二、角色交互总表\n\n"
        f"{body}\n增量行\n\n## 三、信息边界矩阵（权威）\n\n"
        "| 边界 | 状态 |\n|---|---|\n| R1..R28 | 已核+本章差 |\n| R29 | 新增 |\n\n"
        "## 五、逐章角色状态\n\n本章行×3\n",
        encoding="utf-8",
    )

    result = _run([str(staged)], str(tmp_path))
    assert not any("G4.ss.matrix_structure" in m for m in result.get("must_fix", []))


@pytest.mark.unit
def test_fails_when_staged_matrix_swaps_prose_under_kept_headings(tmp_path: Path) -> None:
    """Fixcheck ch3 failure #4: the H2-superset check was bypassed by
    KEEPING every live heading while rewriting the prose under them. The
    content guard must require live prose/bullet lines to survive, not
    just the headings.
    """
    live = tmp_path / "truth" / "character_matrix.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        "---\ntype: truth\n---\n\n## 一、格式约定\n\n"
        "以角色对为单位记录。\n- 同一对角色只保留一条记录。\n- 信任度与最近互动章节均为全书口径。\n\n"
        "## 四、待追踪的信息差清单\n\n条目见下表。",
        encoding="utf-8",
    )
    staged = tmp_path / "staging" / "truth" / "character_matrix.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "---\ntype: truth\n---\n\n## 一、格式约定\n\n"
        "以角色为中心记录。\n- 每个角色一张卡。\n- 状态字段全集见模板。\n\n"
        "## 四、待追踪的信息差清单\n\n条目改由角色卡承载。",
        encoding="utf-8",
    )

    result = _run([str(staged)], str(tmp_path))
    mf = result.get("must_fix", [])
    assert result["status"] == "FAIL"
    assert any("G4.ss.matrix_structure" in m and "content_dropped" in m for m in mf)


@pytest.mark.unit
def test_passes_when_staged_matrix_upserts_rows_and_touches_volatile_lines(tmp_path: Path) -> None:
    """Legitimate increment: table-row upsert (same key, updated cells),
    appended rows/sections, refreshed frontmatter timestamps and a
    rewritten `>` annotation line (清单计数) must all pass the guard.
    """
    live = tmp_path / "truth" / "character_matrix.md"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        "---\ntype: truth\nproduced_at: 2026-09-29T10:00:00Z\n---\n\n"
        "# 角色交互矩阵\n\n## 二、角色交互总表\n\n"
        "| 角色对 | 关系性质 | 信任度 |\n|---|---|---|\n"
        "| 陆昭-柯小满 | 陌生 | 1 |\n| 陆昭-阿水 | 跟班 | 2 |\n\n"
        "## 四、待追踪的信息差清单\n\n> 本清单共 11 条。\n\n"
        "| # | 信息差 |\n|---|---|\n| 1 | 铁盒抄本 |\n",
        encoding="utf-8",
    )
    staged = tmp_path / "staging" / "truth" / "character_matrix.md"
    staged.parent.mkdir(parents=True)
    staged.write_text(
        "---\ntype: truth\nproduced_at: 2026-09-29T20:15:30Z\n---\n\n"
        "# 角色交互矩阵\n\n## 二、角色交互总表\n\n"
        "| 角色对 | 关系性质 | 信任度 |\n|---|---|---|\n"
        "| 陆昭-柯小满 | 师生/识才 | 3 |\n| 陆昭-阿水 | 跟班 | 2 |\n\n"
        "## 四、待追踪的信息差清单\n\n> 本清单共 12 条。\n\n"
        "| # | 信息差 |\n|---|---|\n| 1 | 铁盒抄本 |\n| 12 | 新增条目 |\n\n"
        "## 第2章状态增量\n\n- 陆昭识出柯小满的题眼\n",
        encoding="utf-8",
    )

    result = _run([str(staged)], str(tmp_path))
    assert not any("G4.ss.matrix_structure" in m for m in result.get("must_fix", [])), result.get(
        "must_fix", []
    )
