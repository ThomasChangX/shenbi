"""Plan A read-slicing extractors (adjudication 096 / 191-PENDING 方案A).

Six TDD points from the esc#4 opinion §2.2:

1. hooks_audit_scoped: 总览 kept full + ONLY the plan/audit-named hook
   detail sections, with an omission sentinel (plan named MH02 while the
   audit named CP-001 — union grounding).
2. hooks_audit_scoped: no grounding sources resolvable -> "" (the dispatch
   loop falls back to full text + WARN, never a silent drop).
3. hooks_audit_scoped: chapter=None (genesis) -> "" — the genesis dispatch
   needs the full pool view (same fallthrough discipline as volume_chapter).
4. recent_increments table form: preamble (frontmatter/title/table header)
   + last-3 chapter rows + omission sentinel — chapter_summaries shape.
5. recent_increments section form: preamble + last-3 ``### 第N章`` sections
   with the nearest ``##`` group heading re-attached — audit_drift shape.
6. chapter-keyed budget truncation keeps head + tail units and cuts the
   middle with a sentinel (the old head-only clip produced a 残篇 that
   orphaned table rows — the ch58 input-flood root).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from shenbi.pipeline.read_extractors import (
    chapter_scoped_head_tail,
    extract_hooks_audit_scoped,
    extract_recent_increments,
)

pytestmark = pytest.mark.unit


_PENDING_HOOKS = """---
type: truth
category: state
status: filled
---

# 伏笔池

## 总览

| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance | 升级曲线 |
|------|------|------|------|------|------|------|------|
| MH01（灵印） | RELEVANT | 4 | 118（五卷） | MYSTERY | 0.5 | 10 | STAIRCASE |
| MH02（灵誓） | PLANTED | 38 | 104（五卷） | RULE | 0.5 | 12 | RISING |
| CP-001（册末空格） | RESOLVED | 3 | 17 | ITEM | 0.4 | 14 | STAIRCASE |

## 详情

### MH01（灵印）

- lifecycle_state: RELEVANT
- 证据: 第4章断脉塌方首次显形。

### MH02（灵誓）

- lifecycle_state: PLANTED
- 证据: 第38章议桌落成。

### CP-001（册末空格）

- lifecycle_state: RESOLVED
- 证据: 第17章行署当众指向。
"""


def _project_with_grounding(tmp_path: Path, plan: str | None, audit: str | None) -> Path:
    if plan is not None:
        (tmp_path / "plans").mkdir(exist_ok=True)
        (tmp_path / "plans" / "chapter-57-plan.md").write_text(plan, encoding="utf-8")
    if audit is not None:
        (tmp_path / "audits").mkdir(exist_ok=True)
        (tmp_path / "audits" / "chapter-57-foreshadowing.md").write_text(audit, encoding="utf-8")
    return tmp_path


def test_hooks_audit_scoped_keeps_overview_and_named_sections(tmp_path: Path) -> None:
    plan = "## 7. 本章 hook 账\n\n| ID | 操作 |\n|----|------|\n| MH02 | advance |\n"
    audit = "本章触及 CP-001 的收束确认。"
    project = _project_with_grounding(tmp_path, plan, audit)

    out = extract_hooks_audit_scoped(project, 57, _PENDING_HOOKS)

    # 总览 full (all three rows survive the slice)
    assert "MH01（灵印） | RELEVANT" in out
    assert "MH02（灵誓） | PLANTED" in out
    assert "CP-001（册末空格） | RESOLVED" in out
    # named detail sections kept (union of plan MH02 + audit CP-001)
    assert "### MH02（灵誓）" in out
    assert "### CP-001（册末空格）" in out
    # unnamed detail section dropped, with a disclosure sentinel
    assert "### MH01（灵印）" not in out
    assert "第4章断脉塌方首次显形" not in out
    assert "省略" in out and "MH01" in out


def test_hooks_audit_scoped_staging_twin_grounding_wins(tmp_path: Path) -> None:
    """F-3 parity: settle reads may run while the audit exists only under
    staging/ — the grounding lookup must be staging-first.
    """
    (tmp_path / "staging" / "audits").mkdir(parents=True)
    (tmp_path / "staging" / "audits" / "chapter-57-foreshadowing.md").write_text(
        "触及 MH01。", encoding="utf-8"
    )
    (tmp_path / "audits").mkdir()
    (tmp_path / "audits" / "chapter-57-foreshadowing.md").write_text(
        "触及 MH02。", encoding="utf-8"
    )
    (tmp_path / "plans").mkdir()
    (tmp_path / "plans" / "chapter-57-plan.md").write_text(
        "## 7. 本章 hook 账\n\n| ID |\n|----|\n| 无 |\n", encoding="utf-8"
    )

    out = extract_hooks_audit_scoped(tmp_path, 57, _PENDING_HOOKS)
    assert "### MH01（灵印）" in out
    assert "### MH02（灵誓）" not in out


def test_hooks_audit_scoped_no_grounding_returns_empty(tmp_path: Path) -> None:
    assert extract_hooks_audit_scoped(tmp_path, 57, _PENDING_HOOKS) == ""


def test_hooks_audit_scoped_genesis_chapter_none_returns_empty(tmp_path: Path) -> None:
    project = _project_with_grounding(tmp_path, "| MH02 | advance |", None)
    assert extract_hooks_audit_scoped(project, None, _PENDING_HOOKS) == ""


def _pool_with_triggered() -> str:
    """Same pool with MH02 flipped to TRIGGERED (volume-boundary shape)."""
    return _PENDING_HOOKS.replace("| MH02（灵誓） | PLANTED |", "| MH02（灵誓） | TRIGGERED |")


def test_hooks_inventory_scoped_keeps_overview_and_triggered_details() -> None:
    from shenbi.pipeline.read_extractors import extract_hooks_inventory_scoped

    out = extract_hooks_inventory_scoped(_pool_with_triggered())

    # 总览 full — every hook's lifecycle row survives the slice (the
    # inventory's authoritative surface)
    assert "MH01（灵印） | RELEVANT" in out
    assert "MH02（灵誓） | TRIGGERED" in out
    assert "CP-001（册末空格） | RESOLVED" in out
    # TRIGGERED detail section kept (the resolve candidates)
    assert "### MH02（灵誓）" in out
    assert "第38章议桌落成" in out
    # non-TRIGGERED details dropped, with a disclosure sentinel
    assert "### MH01（灵印）" not in out
    assert "### CP-001（册末空格）" not in out
    assert "省略" in out and "MH01" in out and "CP-001" in out


def test_hooks_inventory_scoped_no_triggered_returns_empty() -> None:
    from shenbi.pipeline.read_extractors import extract_hooks_inventory_scoped

    assert extract_hooks_inventory_scoped(_PENDING_HOOKS) == ""


def test_hooks_inventory_scoped_malformed_shape_returns_empty() -> None:
    from shenbi.pipeline.read_extractors import extract_hooks_inventory_scoped

    no_overview = _pool_with_triggered().replace("## 总览", "## 池", 1)
    assert extract_hooks_inventory_scoped(no_overview) == ""
    no_details = _pool_with_triggered().replace("## 详情", "## 细", 1)
    assert extract_hooks_inventory_scoped(no_details) == ""
    assert extract_hooks_inventory_scoped("prose only\nno shape at all\n") == ""


def test_recent_increments_table_form_keeps_head_and_last_rows() -> None:
    rows = "\n".join(
        f"| 第 {n} 章 | 第{n}章事件{'长' * 20} | 出场 | 支线 | 伏笔 | 钩子 |" for n in range(1, 11)
    )
    text = (
        "---\ntype: truth\ncategory: state\n---\n\n# 逐章摘要\n\n"
        "| 章节 | 一句话事件 | 出场角色 | 推进的支线 | 新增／回收伏笔 | 结尾钩子 |\n"
        "|---|---|---|---|---|---|\n" + rows + "\n"
    )

    out = extract_recent_increments(text, keep=3)

    assert "| 章节 | 一句话事件" in out  # header block survives
    assert "第 8 章" in out and "第 9 章" in out and "第 10 章" in out  # last 3 rows
    assert "第 1 章" not in out and "第 5 章" not in out  # middle dropped
    assert "省略" in out and "第1–7章" in out  # sentinel names the omitted span


def test_recent_increments_section_form_keeps_group_headings() -> None:
    text = (
        "---\ntype: truth\n---\n\n# 纠偏台账\n\n"
        "## 逐章纠偏（targeted_chapter=4）\n\n### 第 1 章\n\n旧账一。\n\n### 第 2 章\n\n旧账二。\n\n"
        "## 共鸣短板（resonance）\n\n### 第 3 章\n\n近账一。\n\n### 第 4 章\n\n近账二。\n"
    )

    out = extract_recent_increments(text, keep=2)

    assert "### 第 3 章" in out and "### 第 4 章" in out  # last 2 sections
    assert "### 第 1 章" not in out and "### 第 2 章" not in out
    assert "## 共鸣短板（resonance）" in out  # nearest group heading re-attached
    assert "近账一" in out and "近账二" in out
    assert "旧账" not in out
    assert "省略" in out


def test_recent_increments_unexpected_shape_returns_empty() -> None:
    assert extract_recent_increments("just prose\nno chapter units\n", keep=3) == ""


def test_budget_truncation_keeps_head_and_tail_units() -> None:
    rows = "\n".join(f"| 第 {n} 章 | {'x' * 200} |" for n in range(1, 31))
    text = "---\ntype: truth\n---\n\n# 台账\n\n| 章节 | 内容 |\n|---|---|\n" + rows + "\n"

    out = chapter_scoped_head_tail(text, budget=2000)

    assert out is not None
    assert "| 章节 | 内容 |" in out  # head block
    assert "第 30 章" in out and "第 29 章" in out  # tail units kept
    assert "第 5 章 |" not in out  # middle cut
    assert "TRUNCATED" in out  # cap-proof sentinel (F361 discipline)
    assert len(out) <= 2000 + 200  # head+tail+sentinel within budget + one unit slack


def test_budget_truncation_non_chapter_file_returns_none() -> None:
    assert chapter_scoped_head_tail("prose only\n" * 500, budget=100) is None


# --- Wiring (registry / dispatch loop / budget truncation) ------------------


def test_read_extractor_registry_closed_and_extended() -> None:
    from shenbi.contracts.loader import READ_EXTRACTORS

    assert (
        frozenset(
            {
                "volume_chapter",
                "hooks_audit_scoped",
                "recent_increments",
                "hooks_inventory_scoped",
                "hooks_overview",
                "threads_overview",
                "relationships_overview",
                "locations_overview",
            }
        )
        == READ_EXTRACTORS
    )


def test_real_settle_contract_wires_plan_a_extractors() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-state-settling")
    ex = c["read_extractors"]
    assert ex["truth/pending_hooks.md"] == "hooks_audit_scoped"
    for table in (
        "truth/chapter_summaries.md",
        "truth/current_state.md",
        "truth/particle_ledger.md",
        "truth/emotional_arcs.md",
        "truth/subplot_board.md",
    ):
        assert ex[table] == "recent_increments", table
    # volume_summaries 补读: compact mid-range context the slices lose
    assert "truth/volume_summaries.md" in c["reads"]


def test_real_lifecycle_contract_wires_hooks_extractor() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-foreshadowing-lifecycle")
    assert c["read_extractors"]["truth/pending_hooks.md"] == "hooks_audit_scoped"


def test_real_resolve_contract_wires_inventory_extractor() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-foreshadowing-resolve")
    ex = c["read_extractors"]
    assert ex["truth/pending_hooks.md"] == "hooks_inventory_scoped"
    assert ex["truth/chapter_summaries.md"] == "recent_increments"
    # 卷级摘要补读: compact mid-range context the slices lose (模式同 settle)
    assert "truth/volume_summaries.md" in c["reads"]


def _resolve_project(tmp_path: Path) -> Path:
    """Resolve-shaped synthetic project: pool with a TRIGGERED hook + the
    cumulative summaries the boundary inventory also reads.
    """
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "pending_hooks.md").write_text(_pool_with_triggered(), encoding="utf-8")
    rows = "\n".join(f"| 第 {n} 章 | 第{n}章事件{'长' * 20} |" for n in range(1, 30))
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "---\ntype: truth\n---\n\n# 逐章摘要\n\n| 章节 | 事件 |\n|---|---|\n" + rows + "\n",
        encoding="utf-8",
    )
    (tmp_path / "truth" / "volume_summaries.md").write_text(
        "---\ntype: truth\n---\n\n# 卷级摘要\n\n## 第2卷: 卷名 (第24-46章)\n\n卷二摘要。\n",
        encoding="utf-8",
    )
    (tmp_path / "novel.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_dispatch_loop_serves_sliced_resolve_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shenbi.pipeline import dispatch_helper as dh
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    project = _resolve_project(tmp_path)
    warned: list[str] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append(event)

    monkeypatch.setattr(dh.log, "warning", _spy)

    _, user_prompt, _, _ = _build_skill_prompt(
        "shenbi-foreshadowing-resolve", project, "resolve 卷三清点", chapter=69
    )

    # pending_hooks: 总览 full + TRIGGERED detail only, sentinel travels
    assert "### MH02（灵誓）" in user_prompt
    assert "第4章断脉塌方首次显形" not in user_prompt
    assert "hooks_inventory_scoped" in user_prompt
    # volume_summaries 补读 arrives whole
    assert "卷级摘要" in user_prompt
    # chapter_summaries: only the last-3 rows survive
    assert "第 29 章" in user_prompt and "第 5 章" not in user_prompt
    # happy path is WARN-free (spec §7)
    assert "extractor_failed_fulltext" not in warned


def _settle_project(tmp_path: Path) -> Path:
    """Settle-shaped synthetic project: growing truth tables + ch57 grounding."""
    (tmp_path / "truth").mkdir()
    (tmp_path / "plans").mkdir()
    (tmp_path / "audits").mkdir()
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "story_frame.md").write_text("frame", encoding="utf-8")
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-57.md").write_text("# 第57章\n\n正文。\n", encoding="utf-8")
    (tmp_path / "plans" / "chapter-57-plan.md").write_text(
        "## 7. 本章 hook 账\n\n| ID | 操作 |\n|----|------|\n| MH02 | advance |\n",
        encoding="utf-8",
    )
    (tmp_path / "audits" / "chapter-57-foreshadowing.md").write_text(
        "触及 MH02。", encoding="utf-8"
    )
    (tmp_path / "truth" / "pending_hooks.md").write_text(_PENDING_HOOKS, encoding="utf-8")
    rows = "\n".join(
        f"| 第 {n} 章 | 第{n}章事件{'长' * 40} | 出场 | 支线 | 伏笔 | 钩子 |" for n in range(1, 41)
    )
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "---\ntype: truth\n---\n\n# 逐章摘要\n\n"
        "| 章节 | 一句话事件 | 出场角色 | 推进的支线 | 新增／回收伏笔 | 结尾钩子 |\n"
        "|---|---|---|---|---|---|\n" + rows + "\n",
        encoding="utf-8",
    )
    for name, header in (
        ("current_state.md", "| 章节 | 位置 | 时间锚 |"),
        ("particle_ledger.md", "| 章节 | 变动项 | 收支 |"),
        ("emotional_arcs.md", "| 章节 | 角色 | 本章情感弧线 |"),
        ("subplot_board.md", "| 章节 | 支线 | 起始章 |"),
    ):
        trows = "\n".join(f"| 第 {n} 章 | {'y' * 60} | {'z' * 30} |" for n in range(1, 41))
        (tmp_path / "truth" / name).write_text(
            f"---\ntype: truth\n---\n\n# {name}\n\n{header}\n|---|---|---|\n{trows}\n",
            encoding="utf-8",
        )
    (tmp_path / "truth" / "volume_summaries.md").write_text(
        "---\ntype: truth\n---\n\n# 卷级摘要\n\n## 第1卷: 卷名 (第1-23章)\n\n卷一摘要。\n",
        encoding="utf-8",
    )
    (tmp_path / "truth" / "character_matrix.md").write_text(
        "---\ntype: truth\n---\n\n# 矩阵\n\n| 角色A | 角色B | 关系 |\n|---|---|---|\n| 阿烬 | 沉砚 | 对峙 |\n",
        encoding="utf-8",
    )
    (tmp_path / "truth" / "state-settling-decisions.json").write_text("{}", encoding="utf-8")
    (tmp_path / "novel.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_dispatch_loop_serves_sliced_settle_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shenbi.pipeline import dispatch_helper as dh
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    project = _settle_project(tmp_path)
    warned: list[str] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append(event)

    monkeypatch.setattr(dh.log, "warning", _spy)

    _, user_prompt, _, _ = _build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )

    # pending_hooks: named detail kept, unnamed detail + its 证据 dropped
    assert "### MH02（灵誓）" in user_prompt
    assert "第4章断脉塌方首次显形" not in user_prompt
    assert "hooks_audit_scoped" in user_prompt  # sentinel travels with the text
    # chapter_summaries: only the last-3 rows survive
    assert "第 39 章" in user_prompt and "第 40 章" in user_prompt
    assert "第 20 章" not in user_prompt
    # the five chapter-keyed tables sliced the same way
    assert "recent_increments" in user_prompt
    # volume_summaries 补读 arrives whole
    assert "卷级摘要" in user_prompt
    # happy path is WARN-free (spec §7)
    assert "extractor_failed_fulltext" not in warned


def test_dispatch_loop_hooks_extractor_without_grounding_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shenbi.pipeline import dispatch_helper as dh
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    project = _settle_project(tmp_path)
    (project / "plans" / "chapter-57-plan.md").unlink()
    (project / "audits" / "chapter-57-foreshadowing.md").unlink()
    warned: list[str] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append(event)

    monkeypatch.setattr(dh.log, "warning", _spy)

    _, user_prompt, _, _ = _build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )
    # full-text fallback: the unnamed detail IS served now
    assert "第4章断脉塌方首次显形" in user_prompt
    assert "extractor_failed_fulltext" in warned


def test_budgeted_truncate_keeps_tail_units_for_chapter_keyed_files() -> None:
    from shenbi.pipeline.dispatch_helper import _budgeted_truncate

    rows = "\n".join(f"| 第 {n} 章 | {'x' * 300} |" for n in range(1, 31))
    text = "---\ntype: truth\n---\n\n# 台账\n\n| 章节 | 内容 |\n|---|---|\n" + rows + "\n"
    sliced, records = _budgeted_truncate({"truth/x.md": text}, budget=3000)
    out = sliced["truth/x.md"]
    assert "| 章节 | 内容 |" in out  # head block survives
    assert "第 30 章" in out  # newest unit survives (settle needs recency)
    assert "TRUNCATED" in out
    assert records and records[0].file == "truth/x.md"


def test_hooks_inventory_scoped_appends_lifecycle_anchor_digest() -> None:
    """T0 follow-up (adjudication 233 watch 1): the vol-3 boundary CP
    worksheet had 9/10 time_since_plant values unanchored (overview carries
    no last_reinforced column; non-TRIGGERED details are sliced away — one
    row even matched the SKILL template example verbatim). The slice now
    appends a PRECOMPUTED per-hook anchor digest so the resolve never
    improvises the parameter.
    """
    from shenbi.pipeline.read_extractors import extract_hooks_inventory_scoped

    pool = _pool_with_triggered().replace(
        "### MH01（灵印）\n\n- lifecycle_state: RELEVANT",
        "### MH01（灵印）\n\n- lifecycle_state: RELEVANT\n- last_reinforced: 第 62 章",
        1,
    )

    out = extract_hooks_inventory_scoped(pool)

    assert "生命周期锚点" in out
    assert "MH01: plant 4 | last_reinforced 62" in out  # parsed from details
    assert "边界章 − last_reinforced" in out  # the pinned CP 口径 travels with the digest
    # hooks WITHOUT a last_reinforced field surface as 未强化 (never silently dropped)
    assert "MH02: plant 38 | last_reinforced 未强化" in out


def test_hooks_inventory_scoped_partial_rows_are_candidates() -> None:
    """GO① widening (phase3 终报): PARTIAL hooks (CP-005/CP-007 shape) carry
    an open payoff disposition at volume boundaries — the resolve audit
    could not see them because the candidate set was TRIGGERED-only, and the
    ch94 dispositions only landed via a driver modify. PARTIAL rows' detail
    sections now ride along.
    """
    from shenbi.pipeline.read_extractors import extract_hooks_inventory_scoped

    pool = _PENDING_HOOKS.replace(
        "| CP-001（册末空格） | RESOLVED |", "| CP-001（册末空格） | PARTIAL |"
    )
    out = extract_hooks_inventory_scoped(pool)

    assert "### CP-001（册末空格）" in out, "PARTIAL detail section is a boundary candidate"
    assert "TRIGGERED/PARTIAL" in out, "sentinel discloses the widened candidate rule"


def test_hooks_overview_slices_details_with_sentinel() -> None:
    """GO③: overview-only consumers (planning/composing/boundary chain) get
    the lifecycle table without the detail evidence bulk (94KB at ch118 —
    the file had outgrown every full read it served).
    """
    from shenbi.pipeline.read_extractors import extract_hooks_overview

    out = extract_hooks_overview(_PENDING_HOOKS)

    assert "| MH01（灵印） | RELEVANT |" in out
    assert "## 详情" in out
    assert "### MH01（灵印）" not in out, "detail sections omitted"
    assert "hooks_overview" in out and "省略" in out, "omission disclosed"
    # frontmatter survives (frontmatter presence is a program invariant)
    assert out.startswith("---\n")


def test_hooks_overview_malformed_shape_returns_empty() -> None:
    from shenbi.pipeline.read_extractors import extract_hooks_overview

    assert extract_hooks_overview("## 总览\n\n无详情段文件\n") == ""
    assert extract_hooks_overview("### MH01（灵印）\n- lifecycle_state: PLANTED\n") == ""


def test_hooks_overview_carries_archived_tombstone_index() -> None:
    """GO2 x GO3 interaction defect (session31 self-review): pool_archive
    moves terminal sections to tombstones + drops overview rows, while
    hooks_overview serves ONLY the overview table — so archived hook ids
    became invisible to chapter planning, which could re-plant a semantic
    duplicate. The slice now appends a compact tombstone index so planning
    keeps seeing every id that ever existed.
    """
    from shenbi.pipeline.read_extractors import extract_hooks_overview

    pool = _PENDING_HOOKS.replace(
        "### CP-001（册末空格）\n\n- lifecycle_state: RESOLVED\n",
        "### CP-001（册末空格）\n\n- lifecycle_state: RESOLVED\n"
        "- resolve_chapter: 17\n- archived_to: truth/pending_hooks_archive.md\n",
        1,
    )
    out = extract_hooks_overview(pool)

    assert "已归档钩索引" in out
    assert "CP-001" in out, "archived id stays planning-visible"
    assert "RESOLVED" in out and "17" in out
    # live hooks unaffected: the index lists tombstones only
    idx_block = out.split("已归档钩索引", 1)[1]
    assert "MH01" not in idx_block, "non-tombstoned hooks stay out of the index"


# --- threads_overview (B 批: thread_map windowed read) -----------------------

_THREAD_MAP = """---
total_chapters: 118
updated_at: "2026-10-10T03:43:56Z"
---

# 线索地图

**全书预计**: 118 章

---

## 线索总览表

| ID | 名称 | 优先级 | 类型 | max_gap | 起始章 | 终点章 | 状态 |
|----|------|--------|------|---------|--------|--------|------|
| A1 | 灵印与《灵律》残句 | P0 | 长线 | 2 | 1 | 118 | RELEVANT |
| B1 | 断魂水道同源 | P1 | 中线 | 4 | 27 | 109 | PAYING_OFF |
| C1 | 册上多报的名字 | P2 | 短线 | 8 | 3 | 17 | RESOLVED |

---

## 线索详情

### A1: 灵印与《灵律》残句

- **状态**: RELEVANT
- **跨度**: 第1章 - 第118章
- **优先级**: P0
- **备注**: 全书主脉。

### B1: 断魂水道同源

- **状态**: PAYING_OFF
- **跨度**: 第27章 - 第109章
- **优先级**: P1

### C1: 册上多报的名字

- **状态**: RESOLVED
- **跨度**: 第3章 - 第17章
- **优先级**: P2

### C2: 拦船验牌

- **状态**: RESOLVED
- **跨度**: 第4章 - 第13章
- **优先级**: P2
- archived_to: outline/thread_map_archive.md

---

## 章节线索推进表

| 章节区间 | 主推 | 副推 | 备注 |
|---------|------|------|------|
| 1-8（一卷 KR1） | A1 | C1 | 开局 |
| 9-16（一卷 KR2） | A2 | B3 | 追索收紧 |
| 17-23（一卷 KR3） | A1 | C1 | 顶罪与清算 |
| 24-31（二卷 KR1） | A1 | B1 | 落脚 |
| 32-39（二卷 KR2） | A1 | B2 | 公开示范 |
| 95-102（五卷 KR1） | A2 | B1 | 终局对撞 |

---

## 约束检查表

| 卷 | 线程ID | 违规Y/N |
|----|--------|---------|
| 1 | A1 | N |

## 线索编织汇总

**写入文件**: `outline/thread_map.md`
"""


def test_threads_overview_slices_to_active_details_plus_window() -> None:
    """B 批: planning/weaver get the 总览表 FULL + active sections + the
    chapter's 推进表 interval ± 1 — RESOLVED details and validator
    snapshots are omitted with disclosure.
    """
    from shenbi.pipeline.read_extractors import extract_threads_overview

    out = extract_threads_overview(_THREAD_MAP, 5)

    assert out.startswith("---\n"), "frontmatter survives"
    assert "| A1 | 灵印与《灵律》残句 |" in out, "总览表 rides along full"
    assert "### A1: 灵印与《灵律》残句" in out, "active section kept"
    assert "### B1: 断魂水道同源" in out
    assert "### C1: 册上多报的名字" not in out, "RESOLVED detail omitted"
    assert "已归档线索索引" in out and "C2" in out, "tombstone index present"
    assert "1-8（一卷 KR1）" in out, "anchor interval kept"
    assert "9-16（一卷 KR2）" in out, "neighbor interval kept"
    assert "17-23（一卷 KR3）" not in out, "far intervals cut"
    assert "95-102（五卷 KR1）" not in out
    assert "窗口裁剪" in out and "threads_overview" in out, "omission disclosed"
    assert "## 约束检查表" not in out, "validator snapshot omitted"
    assert "| 卷 | 线程ID" not in out
    assert "## 线索编织汇总" not in out
    assert "校验快照" in out, "trailing omission disclosed by name"


def test_threads_overview_chapter_none_keeps_all_intervals() -> None:
    """Genesis weaver (chapter=None): every planned interval rides along."""
    from shenbi.pipeline.read_extractors import extract_threads_overview

    out = extract_threads_overview(_THREAD_MAP, None)

    assert "1-8（一卷 KR1）" in out
    assert "95-102（五卷 KR1）" in out


def test_threads_overview_chapter_outside_planned_intervals_degrades() -> None:
    """A chapter inside NO interval is a re-budget seam — the whole file
    must be served ("" -> full text + WARN), never a silently mis-cut slice.
    """
    from shenbi.pipeline.read_extractors import extract_threads_overview

    assert extract_threads_overview(_THREAD_MAP, 500) == ""


def test_threads_overview_malformed_shape_returns_empty() -> None:
    from shenbi.pipeline.read_extractors import extract_threads_overview

    assert extract_threads_overview("## 线索详情\n\n无总览表\n") == ""
    assert extract_threads_overview("# 线索地图\n\n只有总览\n") == ""


def test_real_planning_contract_wires_threads_extractor() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-chapter-planning")
    assert c["read_extractors"]["outline/thread_map.md"] == "threads_overview"


def test_real_weaver_contract_wires_threads_and_hooks_extractors() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-plot-thread-weaver")
    assert c["read_extractors"]["outline/thread_map.md"] == "threads_overview"
    assert c["read_extractors"]["truth/pending_hooks.md"] == "hooks_overview"


# --- relationships_overview / locations_overview (千万字读面挂账清偿) ---------


_RELATIONSHIPS = """---
total_chapters: 118
---

# 关系图谱

## 关系矩阵（角色 × 角色）

|  | 阿烬 | 阿石 |
|---|---|---|
| 阿烬 | — | 养育 |
| 阿石 | 养育 | — |

## 关系对：阿烬 - 阿石

**类型**: 养育 / 师徒
**利益根基**: 矿上一辈子的相守。
**阵营关系**: 同阵营
**信息边界**: ASYMMETRIC
**起始状态**: 第1章——他把她当自家孩子。
**演化轨迹**:
- 第4章: 他看见她指腹的暗痕，不点破。
- 第8章: 他第一次替她遮掩。
- 第18章: 他把最重的罪名认在自己名下。
- 第23章: 她把他的绳结系在腕上。
- 第70章: 卷终，灯绳成为结绳之册的册头。
- 第118章: 终章，绳账册头的那一结未解。
**预期终态**: 破裂（遗志）

---

## 关系对：阿石 - 阿鹭

**类型**: 看顾
**起始状态**: 第1章——看顾。
**演化轨迹**:
- 第19章: 阿石被押走。
**预期终态**: 破裂

---

## 第47章扩容复核（卷二卷终）

**复核结论**: 不新增角色。

---

## 第118章扩容复核（卷五收束段）

**复核结论**: 收束段不新增角色。

---

## 关系图谱更新汇总

### 关系对统计

- 总关系对: 2

### 演化轨迹待兑现

| 关系对 | 起始 | 当前 | 预期终态 | 章节跨度 |
|--------|------|------|---------|---------|
| 阿烬-阿石 | 养育 | 册头一结未解 | 破裂 | 第1-118章 |

### 编年一致性检查

- 一致。
"""


def test_relationships_overview_windows_trajectory_and_old_reviews() -> None:
    """挂账 A: planning gets 矩阵 + 待兑现 + LATEST 扩容复核 + every pair
    with its 演化轨迹 bounded to the recent bullets — pair texture fields
    (信息边界/利益根基/预期终态) survive whole, older volume-boundary
    reviews and per-pair deep history are omitted with disclosure.
    """
    from shenbi.pipeline.read_extractors import extract_relationships_overview

    out = extract_relationships_overview(_RELATIONSHIPS)

    assert out.startswith("---\n"), "frontmatter survives"
    assert "## 关系矩阵（角色 × 角色）" in out and "| 养育 |" in out
    assert "## 关系对：阿烬 - 阿石" in out and "## 关系对：阿石 - 阿鹭" in out
    assert "**信息边界**: ASYMMETRIC" in out, "pair fields ride along whole"
    assert "**预期终态**: 破裂（遗志）" in out
    assert "- 第70章:" in out and "- 第118章:" in out, "recent trajectory kept"
    assert "- 第4章:" not in out and "- 第8章:" not in out, "old trajectory cut"
    assert "- 第19章: 阿石被押走。" in out, "short trajectory untouched"
    assert "## 第118章扩容复核" in out, "latest volume review kept"
    assert "## 第47章扩容复核" not in out, "older volume review omitted"
    assert "第47章扩容复核" in out, "dropped review named in the sentinel"
    assert "### 演化轨迹待兑现" in out, "pending-payoff table kept"
    assert "### 编年一致性检查" not in out, "validator snapshot omitted"
    assert "relationships_overview" in out and "裁剪" in out, "omission disclosed"


def test_relationships_overview_malformed_shape_returns_empty() -> None:
    from shenbi.pipeline.read_extractors import extract_relationships_overview

    assert extract_relationships_overview("# 空文件\n\n正文。\n") == ""
    assert extract_relationships_overview("") == ""


_LOCATIONS = """---
total_chapters: 118
---

# 地点图谱

## 核心地点（承接世界观构建，描述原文保留）

- 哑脉山系：全书地理骨架。

## 地点：哑脉采掘场

**类型**: 矿场
**功能定位**: 起点
**最近地标**: 黑脉渊
**距离最近地标**: 约一百八十里
**行程时间**: 步行约三日

### 空间布局

主矿道沿枯脉走向东西铺开，宽处两人并行。矿工的下处是贴着山根搭的窝棚。

### 感官锚点

深脉里凿石的回声一顿一顿，像有谁在地底敲门。

### 时间光色

清晨，井口那方天光灰白。

### 功能事件

| 章节 | 事件 | 功能类型 |
|------|------|---------|
| 第1章 | 递灯、背筐、分口粮 | 情感 |
| 第2章 | 按编号登记口粮 | 信息 |
| 第7章 | 编号被挪进未结案一栏 | 信息 |
| 第18章 | 阿石认下最重罪名 | 情感 |
| 第21章 | 断脉深处第一次听见对面喊话 | 转折 |
| 第23章 | 卷终，阿烬离岸 | 情感 |

&gt; **近脉附注（地脉私塾）**：渠老在哑脉近脉改建的地脉私塾，不另立条目。

### 地理位置

- **相邻地点A**: 黑脉渊（东北, 约一百八十里, 步行约三日）
- **相邻地点B**: 苍麓城（东南, 约二百五十里, 车马约四日）

---

## 地点：哑口夜渡

**类型**: 渡口
**功能定位**: 中转

### 空间布局

一条乌篷船横在断口两岸。

### 地理位置

- **相邻地点A**: 哑脉采掘场（西北, 约六十里, 步行约一日）
"""


def test_locations_overview_keeps_headers_geography_recent_events() -> None:
    """挂账 C: location-builder keeps every location's identity header +
    地理位置 (cross-location consistency) + 功能事件 recent rows; the prose
    texture subsections (布局/锚点/光色) are omitted with disclosure.
    """
    from shenbi.pipeline.read_extractors import extract_locations_overview

    out = extract_locations_overview(_LOCATIONS)

    assert out.startswith("---\n"), "frontmatter survives"
    assert "## 核心地点" in out and "哑脉山系" in out, "core preamble kept"
    assert "## 地点：哑脉采掘场" in out and "## 地点：哑口夜渡" in out
    assert "**最近地标**: 黑脉渊" in out and "**行程时间**: 步行约三日" in out
    assert "### 地理位置" in out and "相邻地点B" in out
    assert "| 第23章 | 卷终，阿烬离岸 | 情感 |" in out, "recent event rows kept"
    assert "| 第1章 | 递灯、背筐、分口粮 | 情感 |" not in out, "old event rows cut"
    assert "近脉附注" in out, "free-form note survives"
    assert "主矿道沿枯脉走向东西铺开" not in out, "布局 prose omitted"
    assert "凿石的回声" not in out, "锚点 prose omitted"
    assert "井口那方天光灰白" not in out, "光色 prose omitted"
    assert "locations_overview" in out and "裁剪" in out, "omission disclosed"


def test_locations_overview_malformed_shape_returns_empty() -> None:
    from shenbi.pipeline.read_extractors import extract_locations_overview

    assert extract_locations_overview("# 地点图谱\n\n尚无地点。\n") == ""
    assert extract_locations_overview("") == ""


# --- Live differentials (B 批 lesson: synthetic fixtures miss real shapes) ---


def _live_snapshot(rel: str) -> str:
    return (
        Path(__file__).resolve().parents[2] / "fixtures" / "snapshots" / "chapter-118" / rel
    ).read_text(encoding="utf-8")


def test_relationships_overview_live_differential() -> None:
    from shenbi.pipeline.read_extractors import extract_relationships_overview

    live = _live_snapshot("characters/relationships.md")
    out = extract_relationships_overview(live)

    assert out and len(out) < len(live), "window is strictly smaller"
    assert "## 关系矩阵" in out
    assert "### 演化轨迹待兑现" in out
    assert "## 第118章扩容复核" in out
    assert live.count("## 关系对：") == out.count("## 关系对："), "every pair visible"
    assert "## 第47章扩容复核" not in out
    assert "relationships_overview" in out


def test_locations_overview_live_differential() -> None:
    from shenbi.pipeline.read_extractors import extract_locations_overview

    live = _live_snapshot("world/locations.md")
    out = extract_locations_overview(live)

    assert out and len(out) < len(live), "window is strictly smaller"
    assert live.count("## 地点：") == out.count("## 地点："), "every location visible"
    assert out.count("### 地理位置") == live.count("### 地理位置")
    assert "### 功能事件" in out
    assert "### 空间布局" not in out
    assert "locations_overview" in out


def test_recent_increments_live_matrix_differential() -> None:
    """挂账 B: character_matrix (per-chapter 状态增量 growth) reuses the
    recent_increments machinery — 交互总表/信息边界 head + last 3 increments.
    """
    from shenbi.pipeline.read_extractors import extract_recent_increments

    live = _live_snapshot("truth/character_matrix.md")
    out = extract_recent_increments(live)

    assert out and len(out) < len(live)
    assert "## 交互总表" in out and "## 信息边界" in out
    assert "## 第118章状态增量" in out
    assert "## 第110章状态增量" not in out, "old increments cut"
    assert "recent_increments" in out, "omission disclosed"


def test_real_planning_contract_wires_relationships_extractor() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-chapter-planning")
    assert c["read_extractors"]["characters/relationships.md"] == "relationships_overview"


def test_real_location_builder_contract_wires_locations_extractor() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-location-builder")
    assert c["read_extractors"]["world/locations.md"] == "locations_overview"


def test_real_composing_contract_wires_matrix_extractor() -> None:
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-context-composing")
    assert c["read_extractors"]["truth/character_matrix.md"] == "recent_increments"


def test_dispatch_loop_serves_windowed_reference_ledgers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dispatch face (live 118-chapter shapes): the three reference-ledger
    reads arrive windowed through _build_skill_prompt, WARN-free — the
    wiring is not contract-declaration-only.
    """
    from shenbi.pipeline import dispatch_helper as dh
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    snap = Path(__file__).resolve().parents[2] / "fixtures" / "snapshots" / "chapter-118"
    for sub in ("world", "characters", "truth"):
        (tmp_path / sub).mkdir()
    shutil.copy(snap / "world" / "locations.md", tmp_path / "world" / "locations.md")
    shutil.copy(
        snap / "characters" / "relationships.md", tmp_path / "characters" / "relationships.md"
    )
    shutil.copy(snap / "truth" / "character_matrix.md", tmp_path / "truth" / "character_matrix.md")
    (tmp_path / "novel.json").write_text("{}", encoding="utf-8")

    warned: list[str] = []
    monkeypatch.setattr(dh.log, "warning", lambda event, **kw: warned.append(event))

    _, plan_prompt, _, _ = _build_skill_prompt(
        "shenbi-chapter-planning", tmp_path, "规划第118章", chapter=118
    )
    assert "relationships_overview" in plan_prompt, "windowed serve disclosed"
    assert "## 第47章扩容复核" not in plan_prompt, "old volume review sliced out"

    _, loc_prompt, _, _ = _build_skill_prompt(
        "shenbi-location-builder", tmp_path, "设计新地点", chapter=None
    )
    assert "locations_overview" in loc_prompt
    assert "### 空间布局" not in loc_prompt, "prose texture sliced out"

    _, ctx_prompt, _, _ = _build_skill_prompt(
        "shenbi-context-composing", tmp_path, "组态第118章", chapter=118
    )
    assert "recent_increments" in ctx_prompt
    assert "## 交互总表" in ctx_prompt, "current-state table rides along"
    assert "## 第110章状态增量" not in ctx_prompt, "old increments sliced out"

    assert "extractor_failed_fulltext" not in warned
