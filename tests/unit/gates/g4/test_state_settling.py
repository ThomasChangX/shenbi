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

from shenbi.gates.g4.state_settling import _validate_character_matrix, g4_state_settling


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
    """state_settling prevents parameter agent names in character_matrix.

    Phrase-level detection (probe27 #019 fix): parameter agents must be
    tagged with the explicit `_param:` prefix when introduced in
    character_matrix. Bare agent-name words are tolerated as common Chinese
    vocabulary. The fixture uses the `_param:` tag to exercise the
    genuine-leak path.
    """
    content = """---
update_mode: replace
---

# Character Matrix

## 角色定义
- 林烽: 主角
- 陈为民: 配角

## Ch50 State
- _param:冷: 参数化存在
- _param:光: 格式层出现
"""
    issues = _validate_character_matrix(
        content, known_parameter_agents={"冷", "光", "安静", "缺口"}
    )
    assert len(issues) > 0
    assert "parameter_agent" in issues[0].lower()


def test_character_matrix_common_word_quekou_is_not_a_parameter_agent():
    """probe27 #019: '缺口' (deficit/gap) is a common Chinese word used freely
    in accounting prose; the G4 gate must NOT treat every standalone
    occurrence as a parameter agent leak.

    Phrase-level detection: a parameter agent is only flagged when introduced
    with the explicit `_param:` prefix (the LLM is now expected to use that
    prefix when introducing a parameter role name in character_matrix).
    """
    content = """---
update_mode: replace
---

# Character Matrix

## 角色定义
- 林烽: 主角
- 陈为民: 配角

## Ch5 State
- 端木泠: 出场——以盐引、灵能、数目核账的人；缺口「得去别处对」
- 最近更新章: 5
"""
    issues = _validate_character_matrix(
        content, known_parameter_agents={"冷", "光", "安静", "缺口"}
    )
    # '缺口' is a common Chinese word (deficit/shortage) used in accounting
    # context here — must NOT be flagged unless introduced with `_param:` prefix.
    assert issues == [], (
        f"Common-word '缺口' (deficit) must not be flagged as parameter agent "
        f"without the `_param:` tag prefix. Got issues: {issues}"
    )


def test_character_matrix_param_agent_with_prefix_still_flagged():
    """A parameter agent with the `_param:` tag prefix MUST still be flagged
    when introduced outside the 角色定义 section — phrase-level only filters
    out the common-word false positives, not legitimate tagged uses.
    """
    content = """---
update_mode: replace
---

# Character Matrix

## 角色定义
- 林烽: 主角

## Ch5 State
- _param:缺口: 参数化存在
- 最近更新章: 5
"""
    issues = _validate_character_matrix(
        content, known_parameter_agents={"冷", "光", "安静", "缺口"}
    )
    assert len(issues) > 0
    assert "parameter_agent" in issues[0].lower()
    assert "缺口" in issues[0]


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


# ---------------------------------------------------------------------------
# #52 (probe21 adjudication #008): selections-coverage reconciliation
# ---------------------------------------------------------------------------
_SSC_TARGETS = (
    "current_state",
    "particle_ledger",
    "emotional_arcs",
    "subplot_board",
    "pending_hooks",
    "chapter_summaries",
    "character_matrix",
)


def _staged_settle_project(tmp_path: Path, declared: tuple[str, ...]) -> list[str]:
    """Staging/truth with the probe21 seven-target set + a sidecar whose
    selections declare only *declared* targets (by filename).
    """
    staging = tmp_path / "staging" / "truth"
    staging.mkdir(parents=True, exist_ok=True)
    fps: list[str] = []
    for name in _SSC_TARGETS:
        f = staging / f"{name}.md"
        content = "# x\n"
        if name == "current_state":
            content = "## 位置\n南仓\n"
        elif name == "chapter_summaries" or name == "emotional_arcs":
            content = "## 第 1 章\n摘要\n"
        elif name == "particle_ledger":
            content = (
                "## 资源账本\n| 章节 | 变动项 | 收支 |\n|---|---|---|\n| 第 1 章 | 灰木牌 | +1 |\n"
            )
        elif name == "character_matrix":
            content = "## 角色\n主角\n"
        elif name == "pending_hooks":
            content = "## 钩子\n- lifecycle_state: PLANTED\n"
        f.write_text(content, encoding="utf-8")
        fps.append(f"staging/truth/{f.name}")
    selections = [
        {
            "target": f"truth/{name}.md",
            "selected": ["x"],
            "basis": "adjacent_to_target_chapter",
            "severity": "low",
            "omitted": [],
        }
        for name in declared
    ]
    (staging / "state-settling-decisions.json").write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 1,
                "produced_at": "2026-10-03T07:11:22Z",
                "selections": selections,
                "adjustments": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return fps


@pytest.mark.unit
def test_fails_when_selections_under_report_staged_targets(tmp_path: Path) -> None:
    """probe21 #008 shape: sidecar declared 1/7 while seven files were staged
    — the review surface could not see what the settle touched.
    """
    fps = _staged_settle_project(tmp_path, declared=("pending_hooks",))
    result = _run(fps, str(tmp_path))
    mf = result.get("must_fix", [])
    assert result["status"] == "FAIL"
    uncovered = [m for m in mf if "selections_uncovered" in m]
    assert len(uncovered) == 6, mf
    assert any("particle_ledger" in m for m in uncovered)
    assert not any("pending_hooks" in m for m in uncovered)  # declared → covered


@pytest.mark.unit
def test_passes_when_selections_cover_all_staged_targets(tmp_path: Path) -> None:
    """probe21 #006 standard: 7/7 coverage — no findings."""
    fps = _staged_settle_project(tmp_path, declared=_SSC_TARGETS)
    result = _run(fps, str(tmp_path))
    assert not any("selections_uncovered" in m for m in result.get("must_fix", [])), result.get(
        "must_fix", []
    )


@pytest.mark.unit
def test_selections_coverage_ignores_co_writer_staged_files(tmp_path: Path) -> None:
    """#52 scope fix (probe22 adjudication #005): the obligation set is the
    skill's OWN contract targets, not every file in the shared staging dir —
    foreshadowing-lifecycle's bridge_tracker.md rides the same staging/truth
    glob into the settle G4 file list, and demanding the SETTLE sidecar
    declare it is a false positive (declaring it would be the false report;
    the feedback loop is mathematically unsatisfiable — 3 deterministic
    escalation deaths in probe22 ch1).
    """
    fps = _staged_settle_project(tmp_path, declared=_SSC_TARGETS)
    co_writer = tmp_path / "staging" / "truth" / "bridge_tracker.md"
    co_writer.write_text("| bridge_id | 章节 |\n|---|---|\n| BR-01 | 第 1 章 |\n", encoding="utf-8")
    fps.append("staging/truth/bridge_tracker.md")

    result = _run(fps, str(tmp_path))
    assert not any("selections_uncovered" in m for m in result.get("must_fix", [])), result.get(
        "must_fix", []
    )


@pytest.mark.unit
def test_selections_coverage_still_catches_own_undeclared_target(tmp_path: Path) -> None:
    """The narrowed scope must still catch the probe21 #008 shape: one of the
    skill's OWN contract targets staged but undeclared.
    """
    half = _SSC_TARGETS[:4]  # declare 4 of 7
    fps = _staged_settle_project(tmp_path, declared=half)
    co_writer = tmp_path / "staging" / "truth" / "bridge_tracker.md"
    co_writer.write_text("| bridge_id | 章节 |\n|---|---|\n", encoding="utf-8")
    fps.append("staging/truth/bridge_tracker.md")

    result = _run(fps, str(tmp_path))
    uncovered = [m for m in result.get("must_fix", []) if "selections_uncovered" in m]
    assert len(uncovered) == 3, uncovered  # the 3 undeclared OWN targets
    assert not any("bridge_tracker" in m for m in uncovered)


@pytest.mark.unit
def test_state_settling_skill_declares_selections_must_cover_all_update_targets():
    """Batch #21 fix (probe28 ch4 selections_uncovered recurrence): the
    state-settling SKILL.md must explicitly require selections[] to cover
    EVERY update target declared in the frontmatter writes/updates.

    probe28: state-settling's example sidecar only listed ONE selection
    (current_state.md), causing G4.ss.selections_uncovered to fail on the
    4 undeclared update targets (chapter_summaries / emotional_arcs /
    particle_ledger / subplot_board). The contract must be unambiguous.
    """
    skill_path = (
        Path(__file__).resolve().parents[4] / "skills" / "shenbi-state-settling" / "SKILL.md"
    )
    content = skill_path.read_text(encoding="utf-8")

    # Must contain an explicit declaration that selections must cover all
    # update targets declared in the frontmatter contract.
    expected_patterns = [
        "selections",
        "all",
        "update",
        "writes",
    ]
    found = [p for p in expected_patterns if p.lower() in content.lower()]
    assert found, (
        "state-settling SKILL.md must explicitly require selections to "
        "cover all update targets. Found none of the unambiguous patterns."
    )

    # Must contain an explicit "selections must include" or
    # "selections must cover" or equivalent binding language.
    import re as _re

    binding_patterns = [
        r"selections?[^.]*(?:must|should|必)[^.]*(?:cover|include|contain|含|覆盖)[^.]*(?:all|每个|全部)[^.]*(?:update|write|target|触达|目标)",
        r"(?:all|每个|全部)[^.]*(?:update|write|target)[^.]*(?:必须|must|必)[^.]*(?:含|cover|申报)",
    ]
    found_binding = any(
        _re.search(p, content, _re.IGNORECASE | _re.DOTALL) for p in binding_patterns
    )
    assert found_binding, (
        "state-settling SKILL.md must contain explicit binding language "
        "requiring selections[] to cover ALL update targets. None of the "
        "binding patterns matched."
    )


@pytest.mark.unit
def test_state_settling_skill_declares_character_matrix_append_only():
    """Batch #22 fix (probe29 ch4 matrix_structure content_dropped): the
    state-settling SKILL.md must contain EXPLICIT binding language that
    character_matrix.md uses append-only semantics — output ONLY this
    chapter's increment rows, NEVER modify or rewrite existing rows.

    probe29 ch4: state-settling's re-emit rewrote live rows (e.g.,
    `- 当前位置: 九面采掘队·工棚 (白日在护坡下稽查登记点)`),
    triggering G4.ss.matrix_structure content_dropped with attempts=3
    exhausted. The contract must be unambiguous: append, never replace.
    """
    import re as _re

    skill_path = (
        Path(__file__).resolve().parents[4] / "skills" / "shenbi-state-settling" / "SKILL.md"
    )
    content = skill_path.read_text(encoding="utf-8")

    # Must contain an explicit "append" / "append-only" / "append_dedup"
    # declaration that EXPLICITLY forbids modifying existing rows.
    found_patterns = []
    if _re.search(
        r"append\s*[_-]?only|append_dedup|append\s*,?\s*never\s+replace", content, _re.IGNORECASE
    ):
        found_patterns.append("append-only declaration")
    if _re.search(
        r"never\s+(?:modify|rewrite|replace|reproduce)\s+existing\s+rows?", content, _re.IGNORECASE
    ):
        found_patterns.append("never modify existing rows")
    if _re.search(
        r"do\s+not\s+(?:modify|rewrite|replace)\s+(?:existing|the)\s+rows?", content, _re.IGNORECASE
    ):
        found_patterns.append("do not modify existing rows")
    if _re.search(r"output\s+only\s+(?:the\s+)?(?:current\s+)?chapter", content, _re.IGNORECASE):
        found_patterns.append("output only current chapter")

    assert len(found_patterns) >= 2, (
        f"state-settling SKILL.md must contain explicit append-only / "
        f"never-replace-existing-rows binding language for character_matrix. "
        f"Found: {found_patterns}"
    )


@pytest.mark.unit
def test_state_settling_skill_append_constraint_in_prominent_location():
    """Batch #22 fix (probe29 ch4 matrix_structure content_dropped): the
    state-settling SKILL.md must place the character_matrix append-only
    HARD CONSTRAINT in a PROMINENT location (within first 100 lines of
    body, BEFORE the Truth File Update Mode Rules details), with very
    explicit "ABSOLUTELY NEVER modify" language.

    The detailed rule at line 75 is buried inside a bullet list and is
    ignored by the LLM (probe29 ch4). A higher-prominence HARD CONSTRAINT
    block at the top of the file is needed to make the rule unmissable.
    """
    skill_path = (
        Path(__file__).resolve().parents[4] / "skills" / "shenbi-state-settling" / "SKILL.md"
    )
    content = skill_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Find the first 100 body lines (after frontmatter and auto-gen blocks)
    # where the constraint should appear with explicit "NEVER modify existing
    # rows" binding language.
    body_start = 0
    in_fm = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
                continue
            in_fm = False
            body_start = i + 1
            break

    search_window = "\n".join(lines[body_start : body_start + 100])

    import re as _re

    # Must contain explicit binding language about NOT modifying existing
    # rows in the FIRST 100 lines after frontmatter.
    binding_patterns = [
        r"ABSOLUTELY\s+NEVER\s+modify",
        r"NEVER\s+(?:modify|rewrite|replace)\s+(?:the\s+)?(?:existing|live)\s+rows?",
        r"hard\s*[-_ ]?\s*rule.*append",
        r"append\s*[-_ ]?\s*only",
    ]
    found = [p for p in binding_patterns if _re.search(p, search_window, _re.IGNORECASE)]
    assert found, (
        f"state-settling SKILL.md must place character_matrix append-only "
        f"HARD CONSTRAINT in the first 100 lines of body with explicit "
        f"binding language. Searched patterns: {binding_patterns}, "
        f"found: {found}, body_start={body_start}"
    )
