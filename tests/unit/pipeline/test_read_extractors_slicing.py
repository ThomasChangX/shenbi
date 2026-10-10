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
