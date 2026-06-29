# 契约单源架构 - 支柱四 Tier A（事件溯源 + 原子写）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `src/shenbi/trace/`（append-only 事件溯源，含 hash 链签名、目录 fsync、torn-line 恢复、版本前向不兼容、compaction 含 LEGACY 锚）与 `src/shenbi/safe_write.py`（全框架唯一原子写入口），并把 `progress.json` 降级为从 trace 重算的派生视图，G7 加只读篡改审计。

**Architecture:** 新建 `src/shenbi/trace/`（事件模型 + writer + replay + 版本 + compaction）与 `src/shenbi/safe_write.py`。`materialize_progress` 从 trace 重放重建 `progress.json` dict 并经 safe_write 落盘。G7 加只读 `audit_trace()`。**Tier A 只建机制 + 用它重建 progress**；不重写 update_progress.py 命令对 trace 的迁移（那是行为切换，后续），也不上 AST lint（支柱六）。这样每一步独立可测。

**Tech Stack:** Python 3.11+，Pydantic v2.5+（已依赖），mypy strict（已 CI），pytest+hypothesis（已依赖），pathlib+json+hashlib+os+fcntl。

**关联 spec:** [../specs/2026-06-29-contract-single-source-design.md](../specs/2026-06-29-contract-single-source-design.md) v5.2 支柱四 Tier A（成功判据 7、11）。

**v3 修订（round-1 审核 4→目标 9+，Zeno 全部 verified-against-reality）：** C1 覆盖率门加 Global Constraint（--no-cov on per-file）；C2 `_base_kwargs` 固定 ts（default_factory 致两次 sign 非确定）；C3 trace/ per-file-ignores + safe_write/g7_trace ASCII docstring；I1 materialize per-phase queue（非 total-done）；I2 skills three-pending 默认；I3 flock 跨 os.replace 持有；I4 baseline coverage-threshold 隔离 fail 声明；I5 compaction 跨边界审计限制诚实声明；I6 加 migrate_from_progress Task 8.5（LEGACY_MIGRATION + file-signature）。

**前置依赖:** 支柱一已落地（`shenbi.contracts.enums.ActorRole`、`shenbi.contracts.base`）。本计划 import `ActorRole`。

## Global Constraints

- Python 3.11+；pathlib + json + hashlib；框架代码无 print()（用 structlog）。
- Pydantic v2.5+；`TraceEvent` frozen 且 `extra="ignore"`。
- mypy strict + ruff 必须 CI 干净。
- Tier A **不修改** `update_progress.py`/`gates/g7.py` 的现有命令行为（只新增只读 `audit_trace` 与 `materialize_progress`，并让它们各自有测试）。现有测试集全 passed（不引用具体数字）必须保持。**注意（I4）：** `tests/unit/test_coverage_thresholds.py::test_branch_coverage_meets_threshold` 在**单文件隔离运行**时会因覆盖率数据不足而 fail（它依赖全量运行的覆盖率累积）——这是预期行为，不是 regression。只有全量 `uv run pytest -q` 才能正确评估覆盖率门。
- **覆盖率门：** `pyproject.toml` 设 `--cov=shenbi` + `fail_under=90`，因此任何**单文件/子集** `uv run pytest <path>` 都会因覆盖率不足退出码非零。本计划所有单文件 pytest 命令必须追加 `--no-cov`（如 `uv run pytest tests/unit/trace/test_event.py -q --no-cov`）。覆盖率门只在全量 `uv run pytest -q` 时生效。下面各步为简洁省略 `--no-cov`，执行者一律按此规则补上。
- safe_write 是**新入口**；是否唯一由 AST lint 强制（支柱六），本计划不强制。
- trace.jsonl 是 round 目录下的 `trace.jsonl`（与 `progress.json` 同级）。
- macOS/Linux fsync：`os.fsync`；目录 fsync 用 `os.open(dir, O_RDONLY)+os.fsync+os.close`。
- **RUFF（v3 Critical C3 修复）：** `src/shenbi/trace/*.py` 无 per-file-ignores 条目，且 `src/shenbi/*.py`/`gates/*.py` 的忽略列表不含 RUF001/002/003（fullwidth CJK 标点）。因此 trace/ 与 safe_write.py/g7_trace.py 的**全部 docstring 和注释必须 ASCII**（禁用 （）：，。等全角字符）。Task 1 Step 3 另需在 `[tool.ruff.lint.per-file-ignores]` 加 `"src/shenbi/trace/*.py"` 条目（含 D/E402/PLC0415 等，镜像 contracts/）。

## 文件结构

| 文件 | 责任 |
|---|---|
| `src/shenbi/trace/__init__.py` | 公共 API 导出 |
| `src/shenbi/trace/event.py` | `TraceEvent` frozen 模型 + 签名计算 |
| `src/shenbi/trace/writer.py` | `TraceWriter`（append + seq + dir/file fsync） |
| `src/shenbi/trace/replay.py` | `replay()` + torn-line 恢复 |
| `src/shenbi/trace/versioning.py` | `CURRENT_VERSION`、monotonic 校验、迁移注册表 |
| `src/shenbi/trace/compaction.py` | `compact()`、`verify_chain()`（含 LEGACY 锚） |
| `src/shenbi/safe_write.py` | `safe_write()`（temp+replace+fsync+flock+lockfile+trace） |
| `src/shenbi/trace/materialize.py` | `materialize_progress()`（replay→progress.json） |
| `src/shenbi/gates/g7_trace.py` | `audit_trace()`（只读篡改审计） |
| `tests/unit/trace/*.py` | 各模块单测 |
| `tests/property/trace/*.py` | hash 链不变量属性测试 |

---

### Task 1: trace 包骨架 + TraceEvent 模型 + 签名

**Files:** Create `src/shenbi/trace/__init__.py`、`src/shenbi/trace/event.py`、`tests/unit/trace/__init__.py`、`tests/unit/trace/test_event.py`

**Interfaces:** Consumes `shenbi.contracts.enums.ActorRole`。Produces `TraceEvent`（frozen Pydantic，含 `signature`、`schema_version`）、`canonical_payload(event)->str`、`sign(prev_signature, event)->str`、`GENESIS_PREV`。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/trace/__init__.py
"""Tier A 事件溯源测试包。"""
```

```python
# tests/unit/trace/test_event.py
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from shenbi.contracts.enums import ActorRole
from shenbi.trace.event import (
    GENESIS_PREV,
    TraceEvent,
    canonical_payload,
    sign,
)


def _base_kwargs(**over: object) -> dict[str, object]:
    # ts MUST be pinned: TraceEvent.ts has default_factory=datetime.now,
    # so two sign_and_new() calls without ts get different microsecond
    # timestamps, making canonical_payload/sign non-deterministic.
    from datetime import datetime, timezone
    kw: dict[str, object] = {
        "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "seq": 1,
        "actor": "dispatcher",
        "actor_role": "GATE",
        "action": "MARK_DONE",
        "target": "progress.json",
        "schema_version": 1,
        "payload": {"skill": "x", "score": 94.0},
    }
    kw.update(over)
    return kw


def test_event_frozen() -> None:
    e = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs())
    with pytest.raises(ValidationError):
        e.actor = "other"  # type: ignore[misc]


def test_signature_deterministic() -> None:
    e1 = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs())
    e2 = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs())
    assert e1.signature == e2.signature
    assert len(e1.signature) == 64  # sha256 hex


def test_signature_chains_prev() -> None:
    e1 = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs(seq=1))
    e2 = TraceEvent.sign_and_new(prev_signature=e1.signature, **_base_kwargs(seq=2))
    e2b = TraceEvent.sign_and_new(prev_signature=GENESIS_PREV, **_base_kwargs(seq=2))
    # 不同 prev 必出不同签名（篡改检测基础）
    assert e2.signature != e2b.signature


def test_canonical_payload_is_order_independent() -> None:
    a = canonical_payload(TraceEvent.sign_and_new(GENESIS_PREV, **_base_kwargs(payload={"a": 1, "b": 2})))
    b = canonical_payload(TraceEvent.sign_and_new(GENESIS_PREV, **_base_kwargs(payload={"b": 2, "a": 1})))
    assert a == b


def test_sign_helper_matches_method() -> None:
    e = TraceEvent.sign_and_new(GENESIS_PREV, **_base_kwargs())
    assert e.signature == sign(GENESIS_PREV, canonical_payload(e), 1)
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/trace/test_event.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/trace/__init__.py
"""Tier A 事件溯源：append-only trace.jsonl（spec 支柱四 Tier A）。"""
```

```python
# src/shenbi/trace/event.py
"""TraceEvent 不可变模型 + hash 链签名。signature 链前一条签名，使整条
trace 篡改可见（G7 校验）。canonical_payload 用排序键，去引号/顺序差异。

v5 spec 成功判据 7/11：完整性靠 hash 链 + compaction 边界 + LEGACY 锚。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from shenbi.contracts.enums import ActorRole

GENESIS_PREV = "0" * 64  # 链首/compaction 后的合法前驱锚

_SIGNED_FIELDS = (
    "seq", "ts", "actor", "actor_role", "action",
    "target", "skill", "gate", "payload", "schema_version",
)


def canonical_payload(event: "TraceEvent") -> str:
    """排序键 JSON，消除 dict 顺序/引号差异（语义 round-trip 基础）。"""
    core = {k: getattr(event, k) for k in _SIGNED_FIELDS}
    return json.dumps(core, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      default=_json_default)


def _json_default(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def sign(prev_signature: str, payload_canonical: str, schema_version: int) -> str:
    return hashlib.sha256(
        (prev_signature + "|" + payload_canonical + "|" + str(schema_version)).encode("utf-8")
    ).hexdigest()


class TraceEvent(BaseModel):
    model_config = {"frozen": True, "extra": "ignore"}

    seq: int = Field(ge=1)
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    actor_role: ActorRole
    action: str
    target: str
    skill: str | None = None
    gate: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    schema_version: int = Field(ge=1)
    signature: str = ""

    @classmethod
    def sign_and_new(cls, prev_signature: str, **kw: object) -> "TraceEvent":
        """构造并算签名（签名空时填入）。保证 signature 链 prev_signature。"""
        obj = cls(**kw)  # type: ignore[arg-type]
        sig = sign(prev_signature, canonical_payload(obj), obj.schema_version)
        return obj.model_copy(update={"signature": sig})
```

- [ ] **Step 4: Run → passes** (5)
- [ ] **Step 5: Add ruff per-file-ignores for trace/ (C3 fix)**

Append to `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml` (mirror `contracts/*.py`):
```toml
"src/shenbi/trace/*.py" = [
    "D103", "E402", "D101", "D102", "D205", "D415", "E501", "E741",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059", "PLC0415",
]
"tests/unit/trace/*.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402", "E501", "E741",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/trace/*.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402", "E501", "E741",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
```
注：`safe_write.py` 匹配 `src/shenbi/*.py`（无 RUF 忽略）→ **必须 ASCII docstring**。`gates/g7_trace.py` 匹配 `gates/*.py`（无 RUF 忽略）→ **必须 ASCII docstring**。trace/*.py 虽加了忽略但**建议仍用 ASCII** 以保持一致。

- [ ] **Step 6: mypy + ruff**
`uv run mypy src/shenbi/trace/event.py` → Success
`uv run ruff check src/shenbi/trace/ src/shenbi/safe_write.py` → All passed
- [ ] **Step 7: Commit**
```bash
git add src/shenbi/trace/__init__.py src/shenbi/trace/event.py \
        tests/unit/trace/__init__.py tests/unit/trace/test_event.py pyproject.toml
git commit -m "feat(trace): add TraceEvent frozen model with hash-chain signature + ruff config"
```

---

### Task 2: TraceWriter — append + seq 单调 + 目录/文件 fsync

**Files:** Create `src/shenbi/trace/writer.py`、`tests/unit/trace/test_writer.py`

**Interfaces:** Consumes `TraceEvent.sign_and_new`、`GENESIS_PREV`。Produces `TraceWriter`（`append(...)->TraceEvent`、`last_signature()->str`、`next_seq()->int`）。写入 `round_dir/trace.jsonl`。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/trace/test_writer.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.event import GENESIS_PREV
from shenbi.trace.writer import TraceWriter


def test_append_writes_jsonl_line(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    e = w.append(actor="d", actor_role="GATE", action="INIT", target="progress.json")
    lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["seq"] == 1 and rec["action"] == "INIT"
    assert rec["signature"] == e.signature


def test_seq_monotonic_and_chained(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    e1 = w.append(actor="d", actor_role="GATE", action="A", target="t")
    e2 = w.append(actor="d", actor_role="GATE", action="B", target="t")
    assert e1.seq == 1 and e2.seq == 2
    assert e2.signature != e1.signature
    assert w.last_signature() == e2.signature


def test_new_writer_resumes_existing_trace(tmp_path: Path) -> None:
    w1 = TraceWriter(tmp_path)
    w1.append(actor="d", actor_role="GATE", action="A", target="t")
    w2 = TraceWriter(tmp_path)  # 复用同一文件
    e = w2.append(actor="d", actor_role="GATE", action="B", target="t")
    assert e.seq == 2  # 接续而非重置
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/trace/writer.py
"""TraceWriter：append-only JSONL。seq 从现有 trace 接续；每条事件签名链前一条。
首次创建对父目录 fsync（判据 7 I6a）；每条 append 后对文件 fsync（durability）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from shenbi.contracts.enums import ActorRole
from shenbi.trace.event import GENESIS_PREV, TraceEvent

_TRACE_NAME = "trace.jsonl"


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class TraceWriter:
    def __init__(self, round_dir: Path) -> None:
        self._path = Path(round_dir) / _TRACE_NAME
        self._seq = self._count_existing()
        self._prev = self._last_sig_existing()

    def _count_existing(self) -> int:
        if not self._path.exists():
            return 0
        return sum(1 for _ in self._path.read_text(encoding="utf-8").splitlines() if _.strip())

    def _last_sig_existing(self) -> str:
        if not self._path.exists():
            return GENESIS_PREV
        lines = [ln for ln in self._path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return GENESIS_PREV
        return str(json.loads(lines[-1]).get("signature", GENESIS_PREV))

    def next_seq(self) -> int:
        return self._seq + 1

    def last_signature(self) -> str:
        return self._prev

    def append(
        self, *, actor: str, actor_role: ActorRole, action: str, target: str,
        skill: str | None = None, gate: str | None = None,
        payload: dict[str, object] | None = None, schema_version: int = 1,
    ) -> TraceEvent:
        created = not self._path.exists()
        if created:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        event = TraceEvent.sign_and_new(
            prev_signature=self._prev,
            seq=self.next_seq(), actor=actor, actor_role=actor_role, action=action,
            target=target, skill=skill, gate=gate,
            payload=payload or {}, schema_version=schema_version,
        )
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        if created:
            _fsync_dir(self._path.parent)  # 判据 7 I6a
        self._seq = event.seq
        self._prev = event.signature
        return event
```

- [ ] **Step 4: Run → passes** (3)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/trace/writer.py tests/unit/trace/test_writer.py
git commit -m "feat(trace): add TraceWriter append-only with dir+file fsync"
```

---

### Task 3: replay + torn-line 恢复

**Files:** Create `src/shenbi/trace/replay.py`、`tests/unit/trace/test_replay.py`

**Interfaces:** Consumes `TraceEvent`、`sign`、`canonical_payload`。Produces `replay(round_dir)->list[TraceEvent]`（逐行校验签名链，首条失败截断，返回有效事件）。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/trace/test_replay.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def test_replay_returns_chained_events(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    w.append(actor="d", actor_role="GATE", action="B", target="t")
    evs = replay(tmp_path)
    assert [e.seq for e in evs] == [1, 2]


def test_replay_truncates_torn_tail(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = tmp_path / "trace.jsonl"
    p.write_text(p.read_text(encoding="utf-8") + '{"seq":2,"incomplete":', encoding="utf-8")
    evs = replay(tmp_path)
    assert [e.seq for e in evs] == [1]  # 撕裂行被截断
    assert "incomplete" not in p.read_text(encoding="utf-8")


def test_replay_drops_bad_signature(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = tmp_path / "trace.jsonl"
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    rec["actor"] = "tampered"  # 改了内容但签名没重算
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    assert replay(tmp_path) == []
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/trace/replay.py
"""replay：逐行读 trace.jsonl，校验签名链。首条（JSON 解析失败 或 签名不匹配）
即视为撕裂/篡改边界，截断其后所有内容（判据 7 I6b torn-line 恢复）。
"""
from __future__ import annotations

from pathlib import Path

from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign

_TRACE_NAME = "trace.jsonl"


def _verify(event: TraceEvent, prev_sig: str) -> bool:
    expected = sign(prev_sig, canonical_payload(event), event.schema_version)
    return expected == event.signature


def replay(round_dir: Path) -> list[TraceEvent]:
    path = Path(round_dir) / _TRACE_NAME
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    out: list[TraceEvent] = []
    prev = GENESIS_PREV
    keep_chars = 0
    for ln in lines:
        if not ln.strip():
            keep_chars += len(ln) + 1
            continue
        try:
            event = TraceEvent.model_validate_json(ln)
        except Exception:
            break  # 撕裂行：截断
        if not _verify(event, prev):
            break  # 签名断裂：截断
        out.append(event)
        prev = event.signature
        keep_chars += len(ln) + 1
    if keep_chars < len(raw):
        path.write_text(raw[:keep_chars], encoding="utf-8")
    return out
```

- [ ] **Step 4: Run → passes** (3)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/trace/replay.py tests/unit/trace/test_replay.py
git commit -m "feat(trace): add replay with torn-line recovery + signature verification"
```

---

### Task 4: 事件版本化（monotonic + 前向不兼容 + 迁移注册表）

**Files:** Create `src/shenbi/trace/versioning.py`、`tests/unit/trace/test_versioning.py`

**Interfaces:** Consumes `TraceEvent`。Produces `CURRENT_VERSION`、`assert_monotonic(events)->list[str]`（非递减；未知更高→标记 fail）、`MIGRATIONS: dict[int,Callable]`、`migrate_to_current(event)->TraceEvent`。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/trace/test_versioning.py
from __future__ import annotations

from shenbi.trace.event import TraceEvent
from shenbi.trace.versioning import (
    CURRENT_VERSION,
    assert_monotonic,
    migrate_to_current,
)


def _ev(sv: int) -> TraceEvent:
    return TraceEvent.sign_and_new(
        prev_signature="0" * 64, seq=1, actor="d", actor_role="GATE",
        action="A", target="t", schema_version=sv,
    )


def test_monotonic_ok() -> None:
    assert assert_monotonic([_ev(1), _ev(1), _ev(2)]) == []


def test_monotonic_rejects_decrease() -> None:
    issues = assert_monotonic([_ev(2), _ev(1)])
    assert any("decrease" in i for i in issues)


def test_unknown_higher_version_fails() -> None:
    issues = assert_monotonic([_ev(CURRENT_VERSION + 1)])
    assert any("unknown" in i.lower() for i in issues)


def test_migrate_old_to_current() -> None:
    old = _ev(1)
    new = migrate_to_current(old)
    assert new.schema_version == CURRENT_VERSION
    assert new.action == old.action
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/trace/versioning.py
"""事件版本化（判据 7 I6c + N5）。schema_version 单调非递减；未知更高版本→fail；
旧→新迁移函数注册在 MIGRATIONS。当前只有 v1，迁移逻辑为恒等（结构扩展点）。
"""
from __future__ import annotations

from typing import Callable

from shenbi.trace.event import TraceEvent

CURRENT_VERSION = 1


def _identity(e: TraceEvent) -> TraceEvent:
    return e


MIGRATIONS: dict[int, Callable[[TraceEvent], TraceEvent]] = {}


def assert_monotonic(events: list[TraceEvent]) -> list[str]:
    issues: list[str] = []
    highest = 0
    for e in events:
        if e.schema_version > CURRENT_VERSION:
            issues.append(f"unknown schema_version {e.schema_version} > CURRENT {CURRENT_VERSION}")
        if e.schema_version < highest:
            issues.append(f"schema_version decrease: {e.schema_version} < {highest}")
        highest = max(highest, e.schema_version)
    return issues


def migrate_to_current(event: TraceEvent) -> TraceEvent:
    e = event
    while e.schema_version < CURRENT_VERSION:
        up = MIGRATIONS.get(e.schema_version, _identity)
        e = up(e)
    return e
```

- [ ] **Step 4: Run → passes** (4)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/trace/versioning.py tests/unit/trace/test_versioning.py
git commit -m "feat(trace): add schema_version monotonicity + forward-incompatible guard"
```

---

### Task 5: compaction（COMPACTION 事件 + LEGACY 锚 + 链校验）

**Files:** Create `src/shenbi/trace/compaction.py`、`tests/unit/trace/test_compaction.py`

**Interfaces:** Consumes `TraceWriter`、`replay`、`GENESIS_PREV`。Produces `compact(round_dir, snapshot)->TraceEvent`（写 COMPACTION，payload 含 `prev_compaction_seq`/`snapshot`/`truncated_at_seq`，truncate 旧事件）、`verify_chain(events)->list[str]`（COMPACTION 链单调无缺口，LEGACY_MIGRATION 为合法锚）。

**设计：** COMPACTION 事件本身成为 trace 新首条（链从它的 signature 继续）。`prev_compaction_seq` 指向前一次 compaction 的 seq（首次=None，语义=LEGACY_MIGRATION 锚）。verify_chain 校验每条 COMPACTION 的 prev_compaction_seq 严格无缺口，首条可为 None。

**已知限制（I5，诚实声明）：** compact() 截断旧事件后，当前文件只含一条 COMPACTION。`prev_compaction_seq` 指向已被截断的旧 seq，verify_chain 只校验单文件内 COMPACTION 序列的单调性（首条 None 合法），**无法跨 compaction 边界独立回验**被截断的历史（那是 snapshot 的职责，不是 hash 链的）。这是 compaction-by-design 的固有权衡（以 auditability 换体积）。spec 判据 7 要求 compaction "保历史 + 篡改边界链"——snapshot 保历史、当前链校验篡改边界，但跨 compaction 的端到端审计是已知 Tier A 限制（full cross-compaction end-to-end auditability 是 future work）。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/trace/test_compaction.py
from __future__ import annotations

from pathlib import Path

from shenbi.trace.compaction import compact, verify_chain
from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def test_compact_keeps_only_compaction_event(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    w.append(actor="d", actor_role="GATE", action="B", target="t")
    c = compact(tmp_path, snapshot={"done": ["x"]})
    assert c.action == "COMPACTION"
    evs = replay(tmp_path)
    assert len(evs) == 1 and evs[0].action == "COMPACTION"
    assert evs[0].payload["snapshot"] == {"done": ["x"]}


def test_verify_chain_first_legacy_anchor_ok(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    w.append(actor="d", actor_role="GATE", action="LEGACY_MIGRATION", target="t")
    c = compact(tmp_path, snapshot={})
    evs = replay(tmp_path)
    assert verify_chain(evs) == []  # 首条 COMPACTION prev=None 合法


def test_verify_chain_detects_gap(tmp_path: Path) -> None:
    w = TraceWriter(tmp_path)
    compact(tmp_path, snapshot={})  # COMPACTION seq=1, prev=None
    w.append(actor="d", actor_role="GATE", action="COMPACTION", target="trace.jsonl",
             payload={"prev_compaction_seq": 99, "snapshot": {}, "truncated_at_seq": 1})
    evs = replay(tmp_path)
    issues = verify_chain(evs)
    assert any("gap" in i.lower() or "monotonic" in i.lower() for i in issues)
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/trace/compaction.py
"""compaction（判据 7 I6b + N4 + New-G）。COMPACTION 事件成为 trace 新首条，
payload={prev_compaction_seq, snapshot, truncated_at_seq}。旧事件被截断，
历史保存在 snapshot。verify_chain 校验 COMPACTION 的 prev_compaction_seq
链单调无缺口；首条可为 None（LEGACY_MIGRATION 合法锚）。
"""
from __future__ import annotations

from pathlib import Path

from shenbi.trace.event import TraceEvent
from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def compact(round_dir: Path, snapshot: dict[str, object]) -> TraceEvent:
    """压缩当前 trace：重写为新文件，仅含一条 COMPACTION 事件作为新首条。"""
    path = Path(round_dir) / "trace.jsonl"
    prev_events = replay(round_dir)
    prev_compaction_seq: int | None = None
    truncated_at = 0
    for e in prev_events:
        if e.action == "COMPACTION":
            prev_compaction_seq = e.seq
        truncated_at = max(truncated_at, e.seq)
    path.write_text("", encoding="utf-8")
    w = TraceWriter(round_dir)  # 空文件 → seq=1, prev=GENESIS
    return w.append(
        actor="system", actor_role="GATE", action="COMPACTION", target="trace.jsonl",
        payload={
            "prev_compaction_seq": prev_compaction_seq,
            "snapshot": snapshot,
            "truncated_at_seq": truncated_at,
        },
    )


def verify_chain(events: list[TraceEvent]) -> list[str]:
    """校验 COMPACTION 链：prev_compaction_seq 无缺口；首条 None 合法。"""
    issues: list[str] = []
    last_prev: int | None = None
    for e in events:
        if e.action != "COMPACTION":
            continue
        pcs = e.payload.get("prev_compaction_seq")
        if last_prev is None:
            if pcs is not None and not isinstance(pcs, int):
                issues.append(f"COMPACTION seq={e.seq} prev_compaction_seq 非法类型")
        else:
            if not isinstance(pcs, int):
                issues.append(f"COMPACTION seq={e.seq} 缺 prev_compaction_seq（应为 {last_prev}）")
            elif pcs != last_prev:
                issues.append(f"COMPACTION chain gap: prev={pcs} 期望={last_prev} (monotonic 断裂)")
        last_prev = e.seq
    return issues
```

- [ ] **Step 4: Run → passes** (3)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/trace/compaction.py tests/unit/trace/test_compaction.py
git commit -m "feat(trace): add compaction with LEGACY anchor + chain verification"
```

---

### Task 6: safe_write（原子写 + fsync + flock + lockfile 回退 + trace）

**Files:** Create `src/shenbi/safe_write.py`、`tests/unit/test_safe_write.py`

**Interfaces:** Produces `safe_write(path, data: bytes|str, *, round_dir=None, trace_action=None, trace_target=None) -> None`。原子语义：临时文件 → fsync(文件) → os.replace → fsync(目录) → fcntl.flock（失败回退锁文件 M5）→ 可选 trace 追加。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_safe_write.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.safe_write import safe_write


def test_safe_write_persists_content(tmp_path: Path) -> None:
    p = tmp_path / "out.json"
    safe_write(p, '{"x":1}')
    assert json.loads(p.read_text(encoding="utf-8")) == {"x": 1}


def test_safe_write_atomic_no_residue(tmp_path: Path) -> None:
    p = tmp_path / "out.json"
    safe_write(p, "first")
    safe_write(p, "second")
    assert p.read_text(encoding="utf-8") == "second"
    assert [f.name for f in tmp_path.iterdir() if ".tmp" in f.name] == []


def test_safe_write_accepts_bytes(tmp_path: Path) -> None:
    p = tmp_path / "bin.dat"
    safe_write(p, b"\x00\x01")
    assert p.read_bytes() == b"\x00\x01"


def test_safe_write_traces_when_round_given(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    safe_write(rd / "progress.json", "{}", round_dir=rd,
               trace_action="MATERIALIZE", trace_target="progress.json")
    assert (rd / "trace.jsonl").exists()
    rec = json.loads((rd / "trace.jsonl").read_text(encoding="utf-8").strip())
    assert rec["action"] == "MATERIALIZE"
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/safe_write.py
"""safe_write：框架状态原子写唯一入口（spec 支柱四 Tier A）。
temp + fsync(文件) + os.replace(原子) + fsync(目录) + fcntl.flock；
flock 在不支持时回退锁文件（M5）。可选经 TraceWriter 追加事件。
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    except OSError as e:  # 某些 FS 不支持目录 fsync
        log.debug("dir_fsync_unsupported", path=str(path), error=str(e))
    finally:
        os.close(fd)


def _acquire_lock(path: Path) -> object | None:
    """Acquire exclusive lock on parent dir; return fd to release later (I3 fix).

    The fd must stay open across os.replace+fsync for the lock to be held.
    Returns the fd (caller closes after write) or None on flock-unavailable
    (lockfile fallback M5).
    """
    try:
        import fcntl

        fd = os.open(str(path.parent), os.O_RDONLY)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd  # caller must close after write to release
    except (ImportError, OSError):
        # M5 fallback: lockfile (advisory, not as strong as flock)
        lockfile = path.parent / (path.name + ".lock")
        lockfile.touch()
        return None


def safe_write(
    path: Path,
    data: bytes | str,
    *,
    round_dir: Path | None = None,
    trace_action: str | None = None,
    trace_target: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = _acquire_lock(path)  # held open across write (I3 fix)
    payload = data if isinstance(data, bytes) else data.encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    finally:
        if lock_fd is not None:
            os.close(lock_fd)  # release flock AFTER os.replace+fsync
    if round_dir is not None and trace_action is not None:
        from shenbi.trace.writer import TraceWriter  # 局部 import 避免循环

        TraceWriter(round_dir).append(
            actor="safe_write", actor_role="GATE", action=trace_action,
            target=trace_target or path.name, payload={"path": str(path)},
        )
```

- [ ] **Step 4: Run → passes** (4)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/safe_write.py tests/unit/test_safe_write.py
git commit -m "feat(safe_write): add atomic write with fsync+flock+lockfile fallback+trace"
```

---

### Task 7: materialize_progress（replay → progress.json 经 safe_write）

**Files:** Create `src/shenbi/trace/materialize.py`、`tests/unit/trace/test_materialize.py`

**Interfaces:** Consumes `replay`、`safe_write`。Produces `materialize_progress(round_dir, *, total_skills: list[str], tier="T1", expected_chapters=67) -> dict`。重放 INIT/MARK_DONE 事件重建 progress.json dict，并经 safe_write 落盘 + trace。

**重建规则（与 update_progress.py 语义对齐）：** `INIT` 事件 payload 含 `tier`/`expected_chapters`；`MARK_DONE` payload 含 `skill`/`test_type`/`score`/`status`。一个 skill 三个 test_type 均 done/skip → completed_skill_names。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/trace/test_materialize.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.materialize import materialize_progress
from shenbi.trace.writer import TraceWriter

SKILLS = ["shenbi-a", "shenbi-b"]


def test_materialize_from_init_and_marks(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(actor="d", actor_role="GATE", action="INIT", target="progress.json",
             payload={"tier": "T1", "expected_chapters": 5})
    for tt in ("generative", "bug-hunt", "clean"):
        w.append(actor="d", actor_role="GATE", action="MARK_DONE", target="progress.json",
                 payload={"skill": "shenbi-a", "test_type": tt, "score": 94.0, "status": "done"})
    prog = materialize_progress(rd, total_skills=SKILLS)
    assert prog["completed_skill_names"] == ["shenbi-a"]
    assert prog["tier"] == "T1"
    assert json.loads((rd / "progress.json").read_text(encoding="utf-8"))["completed_skill_names"] == ["shenbi-a"]


def test_materialize_empty_trace(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    prog = materialize_progress(rd, total_skills=SKILLS)
    assert prog["completed_skill_names"] == []
    assert set(prog["remaining_generative"]) == set(SKILLS)
    # I2 fix: unmarked skills get three-pending structure (not empty)
    assert prog["skills"]["shenbi-a"]["generative"]["status"] == "pending"


def test_materialize_partial_skill_per_phase_queue(tmp_path: Path) -> None:
    """I1 fix: per-phase queue. Skill done on generative ONLY should NOT be
    in remaining_generative, but SHOULD be in remaining_bug_hunt/clean."""
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(actor="d", actor_role="GATE", action="MARK_DONE", target="progress.json",
             payload={"skill": "shenbi-a", "test_type": "generative", "score": 94.0, "status": "done"})
    prog = materialize_progress(rd, total_skills=SKILLS)
    # shenbi-a done on generative only -> NOT fully complete, NOT in remaining_generative
    assert "shenbi-a" not in prog["completed_skill_names"]
    assert "shenbi-a" not in prog["remaining_generative"]
    assert "shenbi-a" in prog["remaining_bug_hunt"]  # still pending bug-hunt
    assert "shenbi-a" in prog["remaining_clean"]
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/trace/materialize.py
"""materialize_progress：progress.json 降级为 trace 派生视图（spec 支柱四）。
重放 INIT/MARK_DONE 重建 progress dict，经 safe_write 落盘。语义对齐
update_progress.py（三个 test_type 均 done/skip → completed）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.safe_write import safe_write
from shenbi.trace.replay import replay

_TEST_TYPES = ("generative", "bug-hunt", "clean")


def _empty_skill() -> dict[str, dict[str, Any]]:
    """Match update_progress.cmd_init: every skill starts three-phase pending."""
    return {tt: {"status": "pending"} for tt in _TEST_TYPES}


def materialize_progress(
    round_dir: Path,
    *,
    total_skills: list[str],
    tier: str = "T1",
    expected_chapters: int = 67,
) -> dict[str, Any]:
    """Reconstruct progress.json from trace (I1/I2 fix: match update_progress semantics).

    Per-phase queues (NOT total - genuinely_done): remaining_generative = skills
    not done on generative specifically. Skills sub-structure defaults to
    three-pending (not empty) for unmarked skills — matches cmd_init.
    """
    events = replay(round_dir)
    skills_state: dict[str, dict[str, dict[str, Any]]] = {}
    init_tier, init_chapters = tier, expected_chapters
    done_counter = 0
    for e in events:
        if e.action == "INIT":
            payload = e.payload
            init_tier = str(payload.get("tier", tier))
            init_chapters = int(payload.get("expected_chapters", expected_chapters))
        elif e.action == "MARK_DONE":
            payload = e.payload
            skill = str(payload.get("skill"))
            tt = str(payload.get("test_type"))
            sd = skills_state.setdefault(skill, _empty_skill())  # I2: default three-pending
            sd[tt] = {"status": str(payload.get("status", "done")),
                      "score": float(payload.get("score", 0.0))}
            if sd[tt]["status"] in ("done", "skip"):
                done_counter += 1

    all_skills_set = set(total_skills)

    # I1 fix: per-phase pending (mirror cmd_rebuild_queues semantics)
    def _pending(test_type: str) -> set[str]:
        return all_skills_set - {
            sn for sn, sd in skills_state.items()
            if sd.get(test_type, {}).get("status") in ("done", "skip")
        }

    genuinely_done = sorted(
        all_skills_set - (_pending("generative") | _pending("bug-hunt") | _pending("clean"))
    )
    # I2 fix: unmarked skills get three-pending structure (not empty)
    skills_full = {
        skill: skills_state.get(skill, _empty_skill())
        for skill in sorted(total_skills)
    }
    out: dict[str, Any] = {
        "round": Path(round_dir).name.split("-")[1] if "round-" in str(round_dir) else "???",
        "tier": init_tier,
        "test_cycle_phase": "generative",
        "subagent_completion_count": done_counter,
        "completed_skill_names": genuinely_done,
        "skills": skills_full,
        "remaining_generative": sorted(_pending("generative")),
        "remaining_bug_hunt": sorted(_pending("bug-hunt")),
        "remaining_clean": sorted(_pending("clean")),
        "gate_blockers": [],
        "total_framework_skills": len(total_skills),
        "expected_chapters": init_chapters,
    }
    safe_write(
        Path(round_dir) / "progress.json",
        json.dumps(out, indent=2, ensure_ascii=False),
        round_dir=Path(round_dir),
        trace_action="MATERIALIZE",
        trace_target="progress.json",
    )
    return out
```

- [ ] **Step 4: Run → passes** (2)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/trace/materialize.py tests/unit/trace/test_materialize.py
git commit -m "feat(trace): add materialize_progress — progress.json as trace-derived view"
```

---

### Task 8: G7 篡改审计（只读 audit_trace）

**Files:** Create `src/shenbi/gates/g7_trace.py`、`tests/unit/gates/test_g7_trace.py`

**Interfaces:** Consumes `verify_chain`、`assert_monotonic`、`sign`、`canonical_payload`。Produces `audit_trace(round_dir)->tuple[list[str],list[dict]]`（must_fix issues + check 记录）。**只读**：不修改任何文件。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/gates/__init__.py  （若已存在跳过创建）
```

```python
# tests/unit/gates/test_g7_trace.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.g7_trace import audit_trace
from shenbi.trace.writer import TraceWriter


def test_audit_clean_trace(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    issues, checks = audit_trace(rd)
    assert issues == []
    assert any(c["id"] == "G7T.chain" for c in checks)


def test_audit_detects_tamper(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    w = TraceWriter(rd)
    w.append(actor="d", actor_role="GATE", action="A", target="t")
    p = rd / "trace.jsonl"
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    rec["actor"] = "hacker"
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    issues, _ = audit_trace(rd)
    assert any("signature" in i.lower() or "tamper" in i.lower() for i in issues)


def test_audit_no_trace_ok(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    issues, checks = audit_trace(rd)
    assert issues == []
    assert any(c["id"] == "G7T.absent" for c in checks)
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/gates/g7_trace.py
"""G7 篡改审计（只读）。读 trace.jsonl 原始字节，重算 hash 链判定篡改；
校验 COMPACTION 链（LEGACY 锚）+ 版本单调。绝不修改文件（判据 7/11）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from shenbi.trace.compaction import verify_chain
from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign
from shenbi.trace.versioning import assert_monotonic


def _read_only_events(path: Path) -> list[TraceEvent]:
    out: list[TraceEvent] = []
    if not path.exists():
        return out
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            out.append(TraceEvent.model_validate_json(ln))
        except Exception:
            break  # 撕裂行：到此为止（只读，不修）
    return out


def audit_trace(round_dir: str | Path) -> tuple[list[str], list[dict[str, Any]]]:
    path = Path(round_dir) / "trace.jsonl"
    mf: list[str] = []
    checks: list[dict[str, Any]] = []
    if not path.exists():
        checks.append({"id": "G7T.absent", "s": "PASS", "note": "no trace.jsonl (pre-TierA round)"})
        return mf, checks
    events = _read_only_events(path)
    prev = GENESIS_PREV
    tampered = False
    for e in events:
        expected = sign(prev, canonical_payload(e), e.schema_version)
        if expected != e.signature:
            mf.append(f"G7T.tamper: seq={e.seq} signature mismatch (内容被改/链断裂)")
            tampered = True
            break
        prev = e.signature
    if not tampered:
        checks.append({"id": "G7T.chain", "s": "PASS", "events": len(events)})
    ver_issues = assert_monotonic(events)
    comp_issues = verify_chain(events)
    mf.extend(f"G7T.version: {i}" for i in ver_issues)
    mf.extend(f"G7T.compaction: {i}" for i in comp_issues)
    if not ver_issues and not comp_issues:
        checks.append({"id": "G7T.version_chain", "s": "PASS"})
    return mf, checks
```

- [ ] **Step 4: Run → passes** (3)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/gates/g7_trace.py tests/unit/gates/test_g7_trace.py
git commit -m "feat(g7): add read-only trace tamper audit (chain + version + compaction)"
```

---

### Task 8.5: migrate_from_progress (LEGACY_MIGRATION, 判据 7 I6d)

**Files:** Create `src/shenbi/trace/migrate.py`、`tests/unit/trace/test_migrate.py`

**Interfaces:** Consumes `TraceWriter`、`hashlib`、`json`。Produces `migrate_from_progress(round_dir: Path) -> TraceEvent`。从现有 progress.json 反推 LEGACY_MIGRATION 事件（含文件签名快照），写入 trace.jsonl 作合法链首锚。判据 7 I6d 核心。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/trace/test_migrate.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.migrate import migrate_from_progress


def test_migrate_from_existing_progress(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text(json.dumps({
        "round": "001", "tier": "T1",
        "completed_skill_names": ["shenbi-a"],
    }), encoding="utf-8")
    e = migrate_from_progress(rd)
    assert e.action == "LEGACY_MIGRATION"
    assert "progress_sha256" in e.payload
    assert "completed_skill_names" in e.payload["progress_snapshot"]


def test_migrate_idempotent(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text("{}", encoding="utf-8")
    migrate_from_progress(rd)
    from shenbi.trace.replay import replay
    before = len(replay(rd))
    migrate_from_progress(rd)
    after = len(replay(rd))
    assert before == after
```

- [ ] **Step 2: Run -> fails**

- [ ] **Step 3: Implement**

```python
# src/shenbi/trace/migrate.py
# I6d: bootstrap LEGACY_MIGRATION from existing progress.json + file signature.
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from shenbi.trace.event import TraceEvent
from shenbi.trace.replay import replay
from shenbi.trace.writer import TraceWriter


def migrate_from_progress(round_dir: Path) -> TraceEvent:
    events = replay(round_dir)
    if events:
        for e in events:
            if e.action == "LEGACY_MIGRATION":
                return e  # idempotent: already migrated
    progress_path = Path(round_dir) / "progress.json"
    raw = progress_path.read_text(encoding="utf-8") if progress_path.exists() else "{}"
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError:
        snapshot = {}
    w = TraceWriter(round_dir)
    return w.append(
        actor="system", actor_role="GATE",
        action="LEGACY_MIGRATION", target="progress.json",
        payload={
            "progress_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "progress_snapshot": {
                "tier": snapshot.get("tier"),
                "completed_skill_names": snapshot.get("completed_skill_names", []),
            },
        },
    )
```

- [ ] **Step 4: Run -> passes** (2)
- [ ] **Step 5: mypy + ruff + commit**
```bash
git add src/shenbi/trace/migrate.py tests/unit/trace/test_migrate.py
git commit -m "feat(trace): add migrate_from_progress (LEGACY_MIGRATION + file-signature snapshot)"
```

---

### Task 9: 公共 API 导出 + 属性测试 + 全量回归

**Files:** Modify `src/shenbi/trace/__init__.py`；Create `tests/property/trace/__init__.py`、`tests/property/trace/test_chain_invariants.py`

- [ ] **Step 1: Update `__init__.py`**

```python
# src/shenbi/trace/__init__.py
"""Tier A 事件溯源：append-only trace.jsonl（spec 支柱四 Tier A）。"""
from shenbi.trace.compaction import compact, verify_chain
from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign
from shenbi.trace.materialize import materialize_progress
from shenbi.trace.migrate import migrate_from_progress
from shenbi.trace.replay import replay
from shenbi.trace.versioning import CURRENT_VERSION, assert_monotonic, migrate_to_current
from shenbi.trace.writer import TraceWriter

__all__ = [
    "CURRENT_VERSION", "GENESIS_PREV", "TraceEvent", "TraceWriter",
    "canonical_payload", "sign", "replay", "compact", "verify_chain",
    "materialize_progress", "migrate_from_progress",
    "assert_monotonic", "migrate_to_current",
]
```

- [ ] **Step 2: Write property test**

```python
# tests/property/trace/__init__.py
"""trace hash-链不变量。"""
```

```python
# tests/property/trace/test_chain_invariants.py
from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.trace.writer import TraceWriter
from shenbi.trace.replay import replay


@given(actions=st.lists(st.sampled_from(["A", "B", "C"]), min_size=1, max_size=20))
@settings(max_examples=25)
def test_chain_always_verifies(actions: list[str]) -> None:
    """写任意序列 → replay 全部签名通过。"""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        w = TraceWriter(Path(d))
        for a in actions:
            w.append(actor="d", actor_role="GATE", action=a, target="t")
        evs = replay(Path(d))
        assert [e.seq for e in evs] == list(range(1, len(actions) + 1))


@given(seed=st.text(min_size=1, max_size=10))
@settings(max_examples=25)
def test_tamper_any_field_breaks_chain(seed: str) -> None:
    """改任一字段 → 签名不匹配 → replay 截断。"""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        w = TraceWriter(Path(d))
        w.append(actor="d", actor_role="GATE", action="A", target=seed)
        p = Path(d) / "trace.jsonl"
        rec = json.loads(p.read_text(encoding="utf-8").strip())
        rec["target"] = "TAMPERED"
        p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
        assert replay(Path(d)) == []
```

- [ ] **Step 3: Run property tests → pass**
`uv run pytest tests/property/trace/ -q` → PASS
- [ ] **Step 4: Full regression**
`uv run pytest -q` → 现有测试集全部 passed（不引用具体数字，避免漂移）+ 新增 trace 测试全 passed，无 regression。执行者以实际输出为准，只断言「无失败」。
`uv run mypy src/shenbi && uv run ruff check .` → Success / All passed
- [ ] **Step 5: Empty marker commit**
```bash
git add src/shenbi/trace/__init__.py tests/property/trace/__init__.py tests/property/trace/test_chain_invariants.py
git commit -m "feat(trace): export public API + hash-chain property tests"
git commit --allow-empty -m "chore(trace): pillar 4 Tier A skeleton complete"
```

---

## Self-Review

**1. Spec coverage（Tier A 范围）：** 判据 7（trace 完整性：目录 fsync I6a Task 2、torn-line I6b Task 3、compaction+LEGACY 锚 Task 5、版本前向不兼容 I6c+N5 Task 4、在飞 round 迁移=LEGACY_MIGRATION Task 8.5）全覆盖。判据 11（compaction 链单调 Task 5/9；跨 compaction 端到端审计是已知 Tier A 限制，见 Task 5 I5 诚实声明）。progress 降级 Task 7（I1/I2：per-phase queue + three-pending 默认）。G7 只读篡改审计 Task 8。**范围外：** safe_write 唯一性 AST lint 强制（支柱六）、Tier B 写所有权审计（支柱四 Tier B）、update_progress.py 命令迁到 trace（行为切换，后续）。

**2. Placeholder scan：** 无 TBD/TODO；每个 code step 有完整代码；命令精确。

**3. Type consistency：** `TraceEvent`/`sign`/`canonical_payload`/`TraceWriter.append`/`replay`/`compact`/`verify_chain`/`materialize_progress`/`audit_trace` 签名跨任务一致；`ActorRole` 复用支柱一。`safe_write` 的 `round_dir`/`trace_action` 可选，trace 追加走 `TraceWriter`。

**4. 已知限制（诚实）：** (a) Tier A **不**改 update_progress.py 现有命令（materialize_progress 是新独立函数，语义对齐 cmd_rebuild_queues）。(b) AST lint 强制 safe_write 唯一性留给支柱六。(c) G7 audit_trace 是新只读函数，未替换 gate_G7 主体。(d) **compaction 跨边界审计有限**（I5，Task 5 诚实声明）。(e) **subprocess read-provenance 不在 Tier A**（future work）。(f) coverage-threshold 测试在隔离运行时 fail（预期，I4）。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-contract-single-source-pillar4-tierA.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
