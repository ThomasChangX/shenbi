"""settle 双写写侧——facts_ops 应用（spec #80 §1.1/§6 P1，T8）。

两阶段事务（audit-T8 C2）：先在内存中逐维 apply **全部** sidecar 的全部
op，任一拒收/结构非法 ⇒ ``FactsOpRejectedError`` 上抛且**不写任何文件**
（跨维、跨 sidecar 的零写入契约）；全部合法后才统一落盘。写走 T2 的
**无锁内层** ``_write_facts_unlocked``（R3-C1：同进程 flock 跨 fd 无重入）。
幂等重放（audit-T8 I6）：同章同键 op 已在 ops_log ⇒ 跳过，at-least-once
提交窗口重放不双计。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NoReturn

from pydantic import ValidationError

from shenbi.exceptions import FactsOpRejectedError
from shenbi.facts.enums import FactsDim
from shenbi.facts.schemas import (
    FACTS_SCHEMA,
    CounterEvent,
    FactsFile,
    IdentityEvent,
    PropTransferEvent,
)
from shenbi.facts.store import (
    apply_counter_op,
    apply_identity_op,
    apply_prop_op,
    op_in_log,
)
from shenbi.facts.store import _write_facts_unlocked  # pyright: ignore[reportPrivateUsage] — R3-C1 锁边界
from shenbi.pipeline.truth_io import truth_file_flock

# 章内幂等键集：props/counter 按实体+op+章；identity 按全指纹（无章字段）
_PROP_REPLAY_KEYS: tuple[str, ...] = ("prop", "op", "chapter")
_COUNTER_REPLAY_KEYS: tuple[str, ...] = ("name", "op", "chapter")
_IDENTITY_REPLAY_KEYS: tuple[str, ...] = ("op", "new_name", "alias", "from_ch")


def _reject(reason: str) -> NoReturn:
    raise FactsOpRejectedError(reason)


def _load_sidecar_facts_ops(sidecar_path: Path) -> dict[str, Any]:
    """读单个 sidecar 的 ``facts_ops``；结构非法统一折算为拒收（audit-T8 I5）。"""
    try:
        doc: dict[str, Any] = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FactsOpRejectedError(f"sidecar 不可读/非法 JSON: {sidecar_path}: {exc}") from exc
    facts_ops: Any = doc.get("facts_ops")
    if facts_ops is None:
        return {}
    if not isinstance(facts_ops, dict):
        _reject(f"facts_ops 必须是对象（props/counters/identity），得到 {type(facts_ops).__name__}")
    return facts_ops


def _apply_props(file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    for raw in ops:
        try:
            ev = PropTransferEvent.model_validate(raw)
        except ValidationError as exc:
            _reject(f"props op 结构非法: {exc.error_count()} 处（{exc.errors()[0]['loc']}）")
        if op_in_log(file.ops_log, ev.model_dump(by_alias=True), _PROP_REPLAY_KEYS):
            continue  # 章内幂等重放——跳过
        file = apply_prop_op(file, ev)
    return file


def _apply_counters(file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    for raw in ops:
        try:
            ev = CounterEvent.model_validate(raw)
        except ValidationError as exc:
            _reject(f"counters op 结构非法: {exc.error_count()} 处（{exc.errors()[0]['loc']}）")
        entry = {"name": ev.name, "op": ev.op.value, "delta": ev.delta, "chapter": ev.chapter}
        if op_in_log(file.ops_log, entry, _COUNTER_REPLAY_KEYS):
            continue  # 章内幂等重放——跳过（同章同计数器同 op 只计一次）
        file = apply_counter_op(file, ev.name, ev.op.value, delta=ev.delta, chapter=ev.chapter)
    return file


def _apply_identity(file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    for raw in ops:
        try:
            ev = IdentityEvent.model_validate(raw)
        except ValidationError as exc:
            _reject(f"identity op 结构非法: {exc.error_count()} 处（{exc.errors()[0]['loc']}）")
        entry = {
            "op": ev.op.value,
            "new_name": ev.new_name,
            "alias": ev.alias,
            "from_ch": ev.from_ch,
        }
        if op_in_log(file.ops_log, entry, _IDENTITY_REPLAY_KEYS):
            continue  # 幂等重放——跳过（rename 重放不再回弹名字）
        file = apply_identity_op(
            file,
            ev.op.value,
            new_name=ev.new_name,
            alias=ev.alias,
            from_ch=ev.from_ch,
        )
    return file


def apply_sidecar_ops(project_dir: Path, *sidecar_paths: Path) -> None:
    """读各 sidecar ``facts_ops`` → 逐维在内存 apply → **全部合法后**统一落盘。

    无 ``facts_ops`` 键（旧 settle 兼容期）⇒ no-op。任一 op 拒收/结构非法
    ⇒ ``FactsOpRejectedError`` 上抛、零写入（跨维跨 sidecar）。
    """
    per_dim_ops: dict[FactsDim, list[dict[str, Any]]] = {}
    for sp in sidecar_paths:
        facts_ops = _load_sidecar_facts_ops(sp)
        for dim in FactsDim:
            ops = facts_ops.get(dim.value) or []
            if ops:
                per_dim_ops.setdefault(dim, []).extend(ops)
    if not per_dim_ops:
        return
    appliers = {
        FactsDim.PROPS: _apply_props,
        FactsDim.COUNTERS: _apply_counters,
        FactsDim.IDENTITY: _apply_identity,
    }
    # 阶段 1：逐维持锁读现态 + 内存 apply——拒收在任何写之前上抛
    staged_writes: list[tuple[Path, FactsFile]] = []
    for dim, ops in per_dim_ops.items():
        path = project_dir / "truth" / "facts" / f"{dim.value}.json"
        with truth_file_flock(path):
            if path.is_file():
                current = FactsFile.model_validate_json(path.read_text(encoding="utf-8"))
            else:
                current = FactsFile.model_validate(
                    {"$schema": FACTS_SCHEMA, "dim": dim, "facts": {}}
                )
            updated = appliers[dim](current, ops)
        staged_writes.append((path, updated))
    # 阶段 2：全部维度合法 ⇒ 统一落盘
    for path, updated in staged_writes:
        with truth_file_flock(path):
            _write_facts_unlocked(path, updated)
