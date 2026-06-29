"""写所有权矩阵 + 写越权检查接口（spec 支柱四 Tier B）。

粒度由文件格式决定（spec N1）：JSON→field；markdown truth→record；chapter/report→file。
本文件含参考 OWNERSHIP 条目（genre-config.json 真实 9 顶层键 + pending_hooks.md
plant/track/resolve/state-settling 写键集），均经 tests/fixtures/ 亲手核对（v5 C1/New-A/B）。

注：完整 69 技能 OWNERSHIP 迁移是「支柱一续」；本矩阵是 Tier B 审计消费的接口 +
参考 fixture 条目。审计粒度为 per-skill-per-file（New-H），非 per-record；值正确性不在范围。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class FileChange:
    """单个被审文件的变更描述（snapshot 产出，ownership 消费）。"""

    relpath: str
    status: Literal["added", "deleted", "modified"]
    changed_top_keys: tuple[str, ...] = ()  # JSON field-level
    new_record_ids: tuple[str, ...] = ()  # markdown record-level（新增记录）
    deleted_record_ids: tuple[str, ...] = ()  # 删除记录
    modified_record_keys: tuple[tuple[str, frozenset[str]], ...] = ()  # (id, 改动键集)


@dataclass(frozen=True)
class FileOwnership:
    level: Literal["field", "record_create", "record_field"]
    write_keys: frozenset[str] = field(default_factory=frozenset)
    read_keys: frozenset[str] = field(default_factory=frozenset)


# —— 参考 OWNERSHIP 条目（Tier B 审计消费；完整迁移见「支柱一续」）——
# genre-config.json：真实 9 顶层键（fixture 亲手核对，见计划「fixture 核对」节）
_GENRE_KEYS = frozenset(
    {
        "approval",
        "auditDimensions",
        "chapterTypes",
        "customRules",
        "fatigueWords",
        "pacing",
        "tropeInventory",
        "updated",
        "version",
    }
)
# pending_hooks.md 新记录键（fixture ## hooks 16 键；state 非 status，亲手核对）
_HOOK_KEYS_NEW_RECORD = frozenset(
    {
        "id",
        "state",
        "operation",
        "type",
        "dimension",
        "content",
        "subtlety",
        "plant_chapter",
        "cultivation_interval",
        "last_reinforced",
        "max_distance",
        "escalation_curve",
        "depends_on",
        "core_hook",
        "promoted",
        "notes",
    }
)

OWNERSHIP: dict[tuple[str, str], FileOwnership] = {
    ("shenbi-genre-config", "genre-config.json"): FileOwnership(
        level="field", write_keys=_GENRE_KEYS
    ),
    # foundation-review 读 tropeInventory（声明 read；写集为空）
    ("shenbi-foundation-review", "genre-config.json"): FileOwnership(
        level="field", read_keys=frozenset({"tropeInventory"})
    ),
    # pending_hooks.md 分工（state-settling SKILL.md 权威声明；track 服从）
    ("shenbi-foreshadowing-plant", "truth/pending_hooks.md"): FileOwnership(
        level="record_create", write_keys=_HOOK_KEYS_NEW_RECORD
    ),
    ("shenbi-foreshadowing-track", "truth/pending_hooks.md"): FileOwnership(
        level="record_field", write_keys=frozenset({"state"})
    ),
    ("shenbi-foreshadowing-resolve", "truth/pending_hooks.md"): FileOwnership(
        level="record_field", write_keys=frozenset({"state"})
    ),
    ("shenbi-state-settling", "truth/pending_hooks.md"): FileOwnership(
        level="record_field", write_keys=frozenset({"last_reinforced", "subtlety"})
    ),
}


def get_ownership(skill: str, relpath: str) -> FileOwnership | None:
    return OWNERSHIP.get((skill, relpath))


def check_write_ownership(skill: str, change: FileChange) -> list[str]:
    """检查单个文件的写越权。返回 violations（空=合规）。

    - field（JSON）：改动顶层键 ⊆ write_keys；
    - record_create（plant）：新增记录允许；改/删已有记录 → 越权；
    - record_field（track/resolve/state-settling）：已有记录仅可改 write_keys 内字段；
      新增/删除记录 → 越权。
    无 OWNERSHIP 条目 → 返回 []，由调用方（write_audit）做 file-level 声明写入检查。
    """
    own = get_ownership(skill, change.relpath)
    if own is None:
        return []
    v: list[str] = []
    if own.level == "field":
        bad = [k for k in change.changed_top_keys if k not in own.write_keys]
        if bad:
            v.append(
                f"{change.relpath}: 越权改 field {sorted(bad)}（允许 {sorted(own.write_keys)}）"
            )
    elif own.level == "record_create":
        if change.deleted_record_ids:
            v.append(f"{change.relpath}: 不允许删除记录 {list(change.deleted_record_ids)}")
        for rid, _keys in change.modified_record_keys:
            v.append(f"{change.relpath}: 不允许修改已有记录 id={rid}（plant 仅创建）")
    elif own.level == "record_field":
        if change.new_record_ids:
            v.append(f"{change.relpath}: 不允许新增记录 {list(change.new_record_ids)}")
        if change.deleted_record_ids:
            v.append(f"{change.relpath}: 不允许删除记录 {list(change.deleted_record_ids)}")
        for rid, keys in change.modified_record_keys:
            bad = [k for k in keys if k not in own.write_keys]
            if bad:
                v.append(
                    f"{change.relpath}: id={rid} 越权改字段 {sorted(bad)}（允许 {sorted(own.write_keys)}）"
                )
    return v
