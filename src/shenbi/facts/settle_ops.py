"""settle 双写写侧——facts_ops 应用（spec #80 §1.1/§6 P1，T8）。

RMW 事务：全程持 ``truth_file_flock``，写走 T2 的**无锁内层**
``_write_facts_unlocked``（R3-C1：同进程 flock 跨 fd 无重入）。
拒收 ⇒ ``FactsOpRejectedError`` 上抛且**不写任何文件**（fail-fast，
spec：在 Markdown upsert 之前——调用方（settle commit 站点）在写循环
之前调本函数，异常中止即无半写态）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.exceptions import TruthFileParseError
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
)
from shenbi.facts.store import _write_facts_unlocked  # pyright: ignore[reportPrivateUsage] — R3-C1 锁边界
from shenbi.pipeline.truth_io import truth_file_flock


def _load_sidecar_facts_ops(sidecar_path: Path) -> dict[str, Any] | None:
    try:
        doc: dict[str, Any] = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TruthFileParseError(f"{sidecar_path}: {exc}") from exc
    return doc.get("facts_ops")


def _apply_props(project_dir: Path, file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    for raw in ops:
        file = apply_prop_op(file, PropTransferEvent.model_validate(raw))
    return file


def _apply_counters(project_dir: Path, file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    for raw in ops:
        ev = CounterEvent.model_validate(raw)
        file = apply_counter_op(file, ev.name, ev.op.value, delta=ev.delta, chapter=ev.chapter)
    return file


def _apply_identity(project_dir: Path, file: FactsFile, ops: list[dict[str, Any]]) -> FactsFile:
    for raw in ops:
        ev = IdentityEvent.model_validate(raw)
        file = apply_identity_op(
            file,
            ev.op.value,
            new_name=ev.new_name,
            alias=ev.alias,
            from_ch=ev.from_ch,
        )
    return file


def apply_sidecar_ops(project_dir: Path, sidecar_path: Path) -> None:
    """读 sidecar ``facts_ops`` → 逐维 apply → 落盘。

    无 ``facts_ops`` 键（旧 settle 兼容期）⇒ no-op。任一 op 拒收 ⇒
    异常上抛、零写入。
    """
    facts_ops = _load_sidecar_facts_ops(sidecar_path)
    if not facts_ops:
        return
    appliers = {
        FactsDim.PROPS: _apply_props,
        FactsDim.COUNTERS: _apply_counters,
        FactsDim.IDENTITY: _apply_identity,
    }
    for dim in FactsDim:
        ops = facts_ops.get(dim.value) or []
        if not ops:
            continue
        path = project_dir / "truth" / "facts" / f"{dim.value}.json"
        if path.is_file():
            with truth_file_flock(path):
                current = FactsFile.model_validate_json(path.read_text(encoding="utf-8"))
                updated = appliers[dim](project_dir, current, ops)
                _write_facts_unlocked(path, updated)
        else:
            with truth_file_flock(path):
                fresh = FactsFile.model_validate({"$schema": FACTS_SCHEMA, "dim": dim, "facts": {}})
                updated = appliers[dim](project_dir, fresh, ops)
                _write_facts_unlocked(path, updated)
