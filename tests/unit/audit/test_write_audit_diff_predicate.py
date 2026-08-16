"""C32 R2 回归（F502/F503/F508/F515）：写审计 diff 谓词完备化五形态。

spec: docs/superpowers/specs/2026-08-16-c32-write-audit-mechanism-design.md R2

- F502 (P0): OWNERSHIP 管控文件整体删除 → record 级与 field 级均直接违规
  （此前 FileChange 产出 status="deleted" 但 check_write_ownership 不消费，
  删除整个 truth 文件逃过 OWNERSHIP 审计）
- F515 (P1): 删除+重建（同路径 added）按 field 级键集校验——added 分支此前
  changed_top_keys 恒空，空键集 ⊆ 任何 write_keys → 整体替换零违规
- F503 (P1): 非法 JSON（JSONDecodeError）与顶层类型变化（dict→list/null）
  产生违规而非静默 ()（哨兵键不在任何 write_keys 内）
- F508 (P2): 未变更/双 None → status="unchanged"（不再误标 modified）

fixture 用真实技能产物（G0.9）：genre-config-example.json 顶层键恰为
OWNERSHIP _GENRE_KEYS 九键；pending-hooks-example.md 记录段 3 条 hook 且
cross-section drift 为空。
"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.snapshot import (
    TOP_LEVEL_TYPE_CHANGED_KEY,
    UNPARSEABLE_JSON_KEY,
    compute_file_change,
)
from shenbi.audit.write_audit import audit_writes

PROJECT = Path(__file__).resolve().parents[3]
GENRE_FIXTURE = PROJECT / "tests" / "fixtures" / "genre-config-example.json"
HOOKS_FIXTURE = PROJECT / "tests" / "fixtures" / "pending-hooks-example.md"


# —— 形态一：整体删除（F502）——


def test_diff_predicate_delete_blocks_ownership_files() -> None:
    """OWNERSHIP 管控文件被整体删除：record 级与 field 级审计均不得豁免。"""
    hooks = HOOKS_FIXTURE.read_text(encoding="utf-8")
    # record 级：track 对 pending_hooks.md 仅有 record_field 写权
    res_record = audit_writes(
        "shenbi-foreshadowing-track",
        {"truth/pending_hooks.md": hooks},
        {"truth/pending_hooks.md": None},
    )
    assert res_record.violations
    assert any("删除" in v and "pending_hooks" in v for v in res_record.violations)
    # field 级：genre-config 整体删除同样违规（status 消费不分级豁免）
    cfg = GENRE_FIXTURE.read_text(encoding="utf-8")
    res_field = audit_writes(
        "shenbi-genre-config", {"genre-config.json": cfg}, {"genre-config.json": None}
    )
    assert res_field.violations
    assert any("genre-config" in v for v in res_field.violations)


# —— 形态二：删除+重建 / added 键集校验（F515）——


def test_diff_predicate_delete_rebuild_added_checked_by_keyset() -> None:
    """同路径删除后重建落 added：按 post 顶层键集过 field 审计，不走空键旁路。"""
    cfg = json.loads(GENRE_FIXTURE.read_text(encoding="utf-8"))
    rebuilt = {**cfg, "rogueRebuildKey": "整体替换私货"}
    pre: dict[str, str | None] = {"genre-config.json": None}  # 声明面内不存在（已删）
    post: dict[str, str | None] = {"genre-config.json": json.dumps(rebuilt, ensure_ascii=False)}
    res = audit_writes("shenbi-genre-config", pre, post)
    assert any("rogueRebuildKey" in v for v in res.violations)
    # 合法键集重建（与 genesis 首建同形）：全部键 ∈ write_keys → 无违规
    res_legal = audit_writes(
        "shenbi-genre-config",
        {"genre-config.json": None},
        {"genre-config.json": json.dumps(cfg, ensure_ascii=False)},
    )
    assert res_legal.violations == ()
    # 重建为非法 JSON / 非对象顶层：added 分支同样走哨兵键（F503 × F515 交点，
    # 整体替换成垃圾内容不落回空载荷旁路）
    res_garbage = audit_writes(
        "shenbi-genre-config",
        {"genre-config.json": None},
        {"genre-config.json": "garbage not json"},
    )
    assert any(UNPARSEABLE_JSON_KEY in v for v in res_garbage.violations)
    res_list = audit_writes(
        "shenbi-genre-config",
        {"genre-config.json": None},
        {"genre-config.json": json.dumps(["不是对象"])},
    )
    assert any(TOP_LEVEL_TYPE_CHANGED_KEY in v for v in res_list.violations)
    # record 侧对称：track 重建 pending_hooks.md → 全部记录按"新增"判越权
    hooks = HOOKS_FIXTURE.read_text(encoding="utf-8")
    res_track = audit_writes(
        "shenbi-foreshadowing-track",
        {"truth/pending_hooks.md": None},
        {"truth/pending_hooks.md": hooks},
    )
    assert any("新增记录" in v and "hook-ch1-001" in v for v in res_track.violations)
    # plant（record_create）重建/首建合法：新增记录是其声明写权
    res_plant = audit_writes(
        "shenbi-foreshadowing-plant",
        {"truth/pending_hooks.md": None},
        {"truth/pending_hooks.md": hooks},
    )
    assert res_plant.violations == ()


# —— 形态三：非法 JSON 替换（F503）——


def test_diff_predicate_illegal_json_replacement_violates() -> None:
    """合法 JSON 被垃圾文本替换：哨兵键产生违规而非静默空键集。"""
    cfg = GENRE_FIXTURE.read_text(encoding="utf-8")
    res = audit_writes(
        "shenbi-genre-config",
        {"genre-config.json": cfg},
        {"genre-config.json": "garbage not json"},
    )
    assert res.violations
    assert any(UNPARSEABLE_JSON_KEY in v for v in res.violations)


# —— 形态四：顶层类型变化（F503）——


def test_diff_predicate_top_level_type_swap_violates() -> None:
    """dict→list / dict→null 顶层类型替换：哨兵键产生违规而非静默 ()。"""
    cfg = GENRE_FIXTURE.read_text(encoding="utf-8")
    res_list = audit_writes(
        "shenbi-genre-config",
        {"genre-config.json": cfg},
        {"genre-config.json": json.dumps(["不是", "对象"])},
    )
    assert res_list.violations
    assert any(TOP_LEVEL_TYPE_CHANGED_KEY in v for v in res_list.violations)
    # 顶层 null 同为类型替换形态（spec 目标"五种形态"的 null 键变体）
    res_null = audit_writes(
        "shenbi-genre-config", {"genre-config.json": cfg}, {"genre-config.json": "null"}
    )
    assert any(TOP_LEVEL_TYPE_CHANGED_KEY in v for v in res_null.violations)


# —— 形态五：未变更/双 None 不标 modified（F508）——


def test_diff_predicate_unchanged_not_marked_modified() -> None:
    """未变更与双 None → status="unchanged"，且不产生违规（无假阳性）。"""
    assert compute_file_change("genre-config.json", None, None).status == "unchanged"
    cfg = GENRE_FIXTURE.read_text(encoding="utf-8")
    assert compute_file_change("genre-config.json", cfg, cfg).status == "unchanged"
    res = audit_writes(
        "shenbi-genre-config", {"genre-config.json": cfg}, {"genre-config.json": cfg}
    )
    assert res.violations == ()
