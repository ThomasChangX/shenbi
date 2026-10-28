"""settle 双写写侧——facts_ops 应用（spec #80 §1.1/§6 P1，T8）。

两阶段事务（audit-T8 C2）：先在内存中逐维 apply **全部** sidecar 的全部
op，任一拒收/结构非法 ⇒ ``FactsOpRejectedError`` 上抛且**不写任何文件**
（跨维、跨 sidecar 的零写入契约）；全部合法后才统一落盘。写走 T2 的
**无锁内层** ``_write_facts_unlocked``（R3-C1：同进程 flock 跨 fd 无重入）。
幂等重放（audit-T8 I6 + round2 #1 多重集修正）：全指纹 + 批内序位判定，
at-least-once 提交窗口重放不双计，同章合法重复指纹（二跳转移/同 delta
双计）不误吞。
"""

from __future__ import annotations

import json
from collections import Counter
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
    COUNTER_REPLAY_KEYS,
    IDENTITY_REPLAY_KEYS,
    PROP_REPLAY_KEYS,
    apply_counter_op,
    apply_identity_op,
    apply_prop_op,
    replay_skip,
)
from shenbi.facts.store import _write_facts_unlocked  # pyright: ignore[reportPrivateUsage] — R3-C1 锁边界
from shenbi.pipeline.truth_io import truth_file_flock


def _reject(reason: str) -> NoReturn:
    raise FactsOpRejectedError(reason)


def _load_sidecar_facts_ops(sidecar_path: Path) -> dict[str, Any]:
    """读单个 sidecar 的 ``facts_ops``；结构非法统一折算为拒收（audit-T8 I5）。"""
    try:
        doc: Any = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FactsOpRejectedError(f"sidecar 不可读/非法 JSON: {sidecar_path}: {exc}") from exc
    if not isinstance(doc, dict):
        # audit-T8 round3 I-3(a)：顶层非对象裸 AttributeError 炸穿 commit
        # 站点的 FactsOpRejectedError 单捕（G4.dec 常规先挡，纵深防御）
        _reject(f"sidecar 顶层必须是 JSON 对象，得到 {type(doc).__name__}: {sidecar_path}")
    facts_ops: Any = doc.get("facts_ops")
    if facts_ops is None:
        return {}
    if not isinstance(facts_ops, dict):
        _reject(f"facts_ops 必须是对象（props/counters/identity），得到 {type(facts_ops).__name__}")
    return facts_ops


def _apply_props(file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    seen: Counter[tuple[Any, ...]] = Counter()
    for raw in ops:
        try:
            ev = PropTransferEvent.model_validate(raw)
        except ValidationError as exc:
            _reject(f"props op 结构非法: {exc.error_count()} 处（{exc.errors()[0]['loc']}）")
        entry = ev.model_dump(by_alias=True)
        fp = tuple(entry.get(k) for k in PROP_REPLAY_KEYS)
        k = seen[fp]
        seen[fp] += 1
        if replay_skip(file.ops_log, entry, PROP_REPLAY_KEYS, k):
            continue  # 跨提交幂等重放——跳过（同章合法二跳指纹不同，不在此列）
        file = apply_prop_op(file, ev)
    return file


def _apply_counters(file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    seen: Counter[tuple[Any, ...]] = Counter()
    for raw in ops:
        try:
            ev = CounterEvent.model_validate(raw)
        except ValidationError as exc:
            _reject(f"counters op 结构非法: {exc.error_count()} 处（{exc.errors()[0]['loc']}）")
        entry = {"name": ev.name, "op": ev.op.value, "delta": ev.delta, "chapter": ev.chapter}
        fp = tuple(entry.get(k) for k in COUNTER_REPLAY_KEYS)
        k = seen[fp]
        seen[fp] += 1
        if replay_skip(file.ops_log, entry, COUNTER_REPLAY_KEYS, k):
            continue  # 跨提交幂等重放——跳过；同章同 delta 双计是两条合法 op
        file = apply_counter_op(file, ev.name, ev.op.value, delta=ev.delta, chapter=ev.chapter)
    return file


def _apply_identity(file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    seen: Counter[tuple[Any, ...]] = Counter()
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
        fp = tuple(entry.get(k) for k in IDENTITY_REPLAY_KEYS)
        k = seen[fp]
        seen[fp] += 1
        if replay_skip(file.ops_log, entry, IDENTITY_REPLAY_KEYS, k):
            continue  # 跨提交幂等重放——跳过（rename 重放不再回弹名字）
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
            if not ops:
                continue
            if not isinstance(ops, list):
                # audit-T8 round6 M-2：非列表 ops 值（如 props:5）裸
                # TypeError 绕 commit 路由——纵深防御（生产上游 G4.dec
                # schema 先挡，同轮 3 I-3(a) 类）
                _reject(f"facts_ops.{dim.value} 必须是数组，得到 {type(ops).__name__}: {sp}")
            per_dim_ops.setdefault(dim, []).extend(ops)
    if not per_dim_ops:
        return
    appliers = {
        FactsDim.PROPS: _apply_props,
        FactsDim.COUNTERS: _apply_counters,
        FactsDim.IDENTITY: _apply_identity,
    }
    # 阶段 1：逐维持锁读现态 + 内存 apply——拒收在任何写之前上抛
    # （audit-T8 round2 I-2 + round3 I-3(b)：损坏/不可读/非法 UTF-8 的既有
    # facts 文件统一折算拒收——ValidationError 与 UnicodeDecodeError 都是
    # ValueError 子类，裸上抛会炸穿三处 commit 点的既定路由协议）
    staged_writes: list[tuple[Path, FactsFile]] = []
    for dim, ops in per_dim_ops.items():
        path = project_dir / "truth" / "facts" / f"{dim.value}.json"
        with truth_file_flock(path):
            if path.is_file():
                try:
                    current = FactsFile.model_validate_json(path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise FactsOpRejectedError(
                        f"facts 文件损坏/不可读: {path}: {exc.__class__.__name__}"
                    ) from exc
                if current.dim is not dim:
                    # audit-T8 round5 I-1 写侧孪生：自洽错维文件过 schema 验、
                    # 在 appliers 的维度访问器裸抛 ValueError 绕过 commit 路由
                    # ——槽位断言折算拒收（阶段 1 零写入）
                    raise FactsOpRejectedError(
                        f"facts 文件维度错位: {path}: dim={current.dim.value}"
                        f"（槽位期望 {dim.value}）——先修复 facts 文件本体"
                    )
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
