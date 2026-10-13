"""#18-8 (probe24 adjudication #005/#006): first-fill exemptions.

Two deterministic false positives blocked the probe24 ch1 re-dispatch queue:

* #18-8a — the foreshadowing-LIFECYCLE report (``# Foreshadowing Lifecycle
  Report``, step 7's tracking report) landed at ``audits/chapter-N-
  foreshadowing.md`` with no verdict marker BY DESIGN; the integrity
  completeness check treated it as an audit verdict document, journaled
  ``G4.ac.no_verdict``, and the G4 replay re-failed every later dispatch
  against the sticky journal entry.
* #18-8b — the initialized shells carry `[待填充]` placeholder prose
  inside section spans; the model's contract-sanctioned first-fill
  (full-table escape) consumed the placeholder via _replace_section, and
  the base-preservation guard flagged the consumption as content_dropped.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.gates.g4.state_settling import _dropped_content_lines, _dropped_hook_rows
from shenbi.pipeline.llm_output_integrity import check_audit_completeness


def test_lifecycle_report_is_exempt_from_verdict_check(tmp_path: Path) -> None:
    f = tmp_path / "chapter-1-foreshadowing.md"
    f.write_text(
        "# Foreshadowing Lifecycle Report (Chapter 1)\n\n"
        "生成时间: 2026-10-04T20:09:06Z\n"
        "执行: shenbi-foreshadowing-lifecycle（逐章模式）\n\n"
        "## 总览\n\n| MH02（残缺真名与真名束誓） | OPEN/REINFORCE | PLANTED | RELEVANT |\n",
        encoding="utf-8",
    )
    assert check_audit_completeness(f) == []


def test_real_audit_without_verdict_still_flagged(tmp_path: Path) -> None:
    f = tmp_path / "chapter-1-continuity.md"
    f.write_text(
        "# 连续性审计\n\n## 发现\n\n- 时间锚矛盾：改价码后与工簿对不上。\n",
        encoding="utf-8",
    )
    issues = check_audit_completeness(f)
    assert any("no_verdict" in i for i in issues)


def test_placeholder_prose_consumption_is_not_content_dropped() -> None:
    live = (
        "---\nstatus: initialized\n---\n\n"
        "# 角色交互矩阵\n\n"
        "（待填充：角色两两关系、信任度、信息不对等、当前张力。）\n"
        "## 交互总表\n"
    )
    staged = (
        "---\nstatus: initialized\n---\n\n"
        "# 角色交互矩阵\n\n"
        "## 交互总表\n\n"
        "| 沈烬 | 扁担汉子 | 交易／雇佣 | 初建 | 双方知悉 | 中 | 第1章 |\n"
    )
    assert _dropped_content_lines(live, staged) == []


def test_real_content_loss_still_flagged() -> None:
    """Prose/headings are base mass (table rows are the upsert surface and
    intentionally outside this guard).
    """
    live = (
        "# 角色交互矩阵\n\n"
        "## 信任度初值\n\n"
        "- 沈烬 → 扁担汉子: 初建（由拒到托）\n"
        "- 沈烬 → 老人: 无\n"
    )
    staged = "# 角色交互矩阵\n\n## 信任度初值\n\n- 沈烬 → 扁担汉子: 初建（由拒到托）\n"
    issues = _dropped_content_lines(live, staged)
    assert issues and "content_dropped" in issues[0]


#: #25-1 (probe25 adjudication #006): the lifecycle's ch1 write appended the
#: CP-001/CP-002 registry rows AFTER the ### detail sections — a headerless
#: continuation region. `_live_lifecycle_columns` scopes its exemption to
#: rows directly under a detected header, so the CP rows' lifecycle cell
#: (PLANTED→RELEVANT, a legitimate step-7 transition) read as a stable-column
#: rewrite on the settle's G4 — three identical failures, one escalation.
def test_hook_rows_in_headerless_continuation_table_exempt() -> None:
    live = (
        "| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |\n"
        "|------|------|------|------|------|------|------|------|\n"
        "| MH02（穹顶裂缝在变宽） | PLANTED | 1 | 96（五卷） | EVENT | 0.5 | 14 | RISING |\n"
        "\n"
        "### MH02（穹顶裂缝在变宽）\n\n"
        "- type: EVENT\n"
        "- lifecycle_state: PLANTED\n"
        "\n"
        "| CP-001（无主之名） | PLANTED | 1 | 100（五卷） | SYMBOLIC | 0.7 | 14 | STAIRCASE |\n"
    )
    staged = live.replace("| CP-001（无主之名） | PLANTED |", "| CP-001（无主之名） | RELEVANT |")
    assert _dropped_hook_rows(live, staged) == []


def test_stable_column_rewrite_still_flagged_in_continuation_table() -> None:
    live = (
        "| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |\n"
        "|------|------|------|------|------|------|------|------|\n"
        "| MH02（穹顶裂缝在变宽） | PLANTED | 1 | 96（五卷） | EVENT | 0.5 | 14 | RISING |\n"
        "\n"
        "### MH02（穹顶裂缝在变宽）\n"
        "| CP-001（无主之名） | PLANTED | 1 | 100（五卷） | SYMBOLIC | 0.7 | 14 | STAIRCASE |\n"
    )
    # 兑现章 (a genuinely stable planning column) rewritten → must fire
    staged = live.replace("100（五卷）", "90（四卷）")
    issues = _dropped_hook_rows(live, staged)
    assert issues and "hook_row_stable_columns_rewritten" in issues[0]
