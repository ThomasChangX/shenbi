"""facts op 状态机——纯内存应用与合法性校验（spec #80 §1.1 T1）。

纯函数：不碰文件系统；拒收 raise ``FactsOpRejectedError``（fail-fast，
spec：无来源的二次获得=拒收）。实体副本语义（spec rev1）：同母题新实体=
独立键（``·`` 消歧后缀）初见，老键不动。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn

from pydantic import ValidationError

from shenbi.exceptions import FactsOpRejectedError, TruthFileParseError
from shenbi.facts.enums import FactsDim
from shenbi.facts.schemas import (
    FACTS_SCHEMA,
    CounterFact,
    FactsFile,
    PropFact,
    PropTransferEvent,
)
from shenbi.pipeline.truth_io import truth_file_flock
from shenbi.safe_write import safe_write


def _reject(reason: str) -> NoReturn:
    raise FactsOpRejectedError(reason)


def apply_prop_op(file: FactsFile, ev: PropTransferEvent) -> FactsFile:
    """应用一条物象 op；非法即抛 FactsOpRejectedError。

    - transfer：实体在场须 from_ 非空且 == 当前 owner（空 from_ 的在场
      实体 = 无来源获得，与 acquire 同罪拒收）；实体缺席 = 初见登记
    - acquire：实体在场 = 无来源二次获得（拒收）；缺席 = 合法初见
    - hold：实体在场须 owner == to（to 空仅记录持有不变）；缺席 = 初见
    - lose：声明者 from_ 须为当前 owner，owner 置空保留事件链
    """
    out = file.model_copy(deep=True)
    prop = ev.prop
    existing: PropFact | None = out.props().get(prop)
    if ev.op.value == "transfer":
        owner = ev.to or ev.from_
        if not owner:
            _reject(f"prop.transfer {prop}: to/from both empty (ch{ev.chapter})")
        if existing is None:
            out.facts[prop] = PropFact(
                entity=prop,
                owner=owner,
                events=[f"{prop}: {ev.from_}->{owner} (ch{ev.chapter}, {ev.evidence})"],
            )
        else:
            if not ev.from_ or ev.from_ != existing.owner:
                _reject(
                    f"prop.transfer {prop}: from={ev.from_!r} does not match"
                    f" current owner {existing.owner!r} (ch{ev.chapter});"
                    " empty from on an owned entity is a sourceless"
                    " acquisition — use a disambiguated copy key"
                    f" ({prop}.<branch>) for a new same-motif entity"
                )
            existing.owner = owner
            existing.events.append(f"{prop}: {ev.from_}->{owner} (ch{ev.chapter}, {ev.evidence})")
    elif ev.op.value == "acquire":
        if existing is not None:
            _reject(
                f"prop.acquire {prop}: entity exists (owner={existing.owner!r})"
                f" — sourceless re-acquisition rejected; a new same-motif"
                f" entity must use a disambiguated key ({prop}.<branch>)"
                f" (ch{ev.chapter})"
            )
        if not ev.to:
            _reject(f"prop.acquire {prop}: to empty (ch{ev.chapter})")
        out.facts[prop] = PropFact(
            entity=prop,
            owner=ev.to,
            events=[f"{prop}: first sighting ->{ev.to} (ch{ev.chapter}, {ev.evidence})"],
        )
    elif ev.op.value == "hold":
        if existing is None:
            if not ev.to:
                _reject(f"prop.hold {prop}: first-sighting declaration needs to (ch{ev.chapter})")
            out.facts[prop] = PropFact(
                entity=prop,
                owner=ev.to,
                events=[f"{prop}: first sighting held by {ev.to} (ch{ev.chapter})"],
            )
        elif ev.to and ev.to != existing.owner:
            _reject(
                f"prop.hold {prop}: declared holder {ev.to!r} != current"
                f" owner {existing.owner!r} (ch{ev.chapter})"
            )
        else:
            holder = ev.to or existing.owner
            existing.events.append(f"{prop}: still held by {holder} (ch{ev.chapter})")
    elif ev.op.value == "lose":
        if existing is None:
            _reject(f"prop.lose {prop}: entity not found (ch{ev.chapter})")
        if not ev.from_ or ev.from_ != existing.owner:
            _reject(
                f"prop.lose {prop}: declarer {ev.from_!r} != current owner"
                f" {existing.owner!r} (ch{ev.chapter})"
            )
        existing.owner = ""
        existing.events.append(f"{prop}: {ev.from_} lost (ch{ev.chapter}, {ev.evidence})")
    else:  # pragma: no cover - PropOp exhausts
        _reject(f"unknown prop op: {ev.op!r}")
    out.ops_log.append(ev.model_dump(by_alias=True))
    return out


def apply_counter_op(file: FactsFile, name: str, op: str, *, delta: int, chapter: int) -> FactsFile:
    """计数器 op：单调律（increment 仅正向；set 仅种子期 chapter=0）。"""
    out = file.model_copy(deep=True)
    if op == "set":
        if chapter != 0:
            _reject(f"counter.set {name}: seed-only (chapter=0), got ch{chapter}")
        out.facts[name] = CounterFact(name=name, value=delta, history=[f"seed set={delta}"])
    elif op == "increment":
        if delta <= 0:
            _reject(f"counter.increment {name}: delta={delta} violates monotonicity (need >=1)")
        counters = out.counters()
        existing = counters.get(name)
        if existing is None:
            _reject(f"counter.increment {name}: counter not seeded yet")
        existing.value += delta
        existing.history.append(f"ch{chapter} +{delta} -> {existing.value}")
    else:  # pragma: no cover
        _reject(f"unknown counter op: {op!r}")
    out.ops_log.append(
        {"dim": "counters", "name": name, "op": op, "delta": delta, "chapter": chapter}
    )
    return out


def apply_identity_op(
    file: FactsFile,
    op: str,
    *,
    new_name: str | None,
    alias: str | None,
    from_ch: int,
) -> FactsFile:
    """身份 op：rename 更新 narration_name（携带 from_ch 生效界，旧名入别名集）。"""
    out = file.model_copy(deep=True)
    fact = out.identity()
    if fact is None:
        _reject("identity.apply: identity dim is empty (seed first)")
    if op == "rename":
        if not new_name:
            _reject("identity.rename: new_name required")
        if from_ch <= 0:
            _reject("identity.rename: from_ch bound required (>=1)")
        old = fact.narration_name
        if old not in fact.aliases:
            fact.aliases.append(old)
        fact.narration_name = new_name
        fact.from_ch = from_ch
    elif op == "set_alias":
        if not alias:
            _reject("identity.set_alias: alias required")
        if alias not in fact.aliases:
            fact.aliases.append(alias)
    else:  # pragma: no cover
        _reject(f"unknown identity op: {op!r}")
    out.ops_log.append(
        {"dim": "identity", "op": op, "new_name": new_name, "alias": alias, "from_ch": from_ch}
    )
    return out


# ── IO（T2）：flock + safe_write 原子写；内层无锁供 RMW 外层复用 ──────────


def _facts_path(project_dir: Path, dim: FactsDim) -> Path:
    return project_dir / "truth" / "facts" / f"{dim.value}.json"


def load_facts(project_dir: Path, dim: FactsDim) -> FactsFile | None:
    """读 facts 文件；缺席 None（门检 WARN 降级依据），损坏 raise。"""
    path = _facts_path(project_dir, dim)
    if not path.is_file():
        return None
    try:
        return FactsFile.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise TruthFileParseError(f"{path}: {exc}") from exc


def _write_facts_unlocked(path: Path, file: FactsFile) -> None:
    """无锁内层写（R3-C1）：外层 RMW 持锁时直调本函数。

    公开 ``save_facts`` 自带 flock 供独立调用方；同进程 flock 跨 fd
    无重入语义——外层持锁再进公开 save_facts 的自锁=死锁。
    """
    payload = json.dumps(file.model_dump(by_alias=True), ensure_ascii=False, indent=2)
    safe_write(path, payload)


def save_facts(project_dir: Path, file: FactsFile) -> None:
    """线程/进程安全落盘（flock + safe_write 原子写）。"""
    path = _facts_path(project_dir, file.dim)
    with truth_file_flock(path):
        _write_facts_unlocked(path, file)


def seed_empty(project_dir: Path) -> None:
    """pipeline-init 空种子（spec §4 F15 bootstrap）：三维 write-if-absent，幂等。"""
    for dim in FactsDim:
        path = _facts_path(project_dir, dim)
        if path.is_file():
            continue
        save_facts(
            project_dir,
            FactsFile.model_validate({"$schema": FACTS_SCHEMA, "dim": dim, "facts": {}}),
        )
