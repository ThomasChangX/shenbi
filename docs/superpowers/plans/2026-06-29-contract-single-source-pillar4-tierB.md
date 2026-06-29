# 契约单源架构 - 支柱四 Tier B（skill 产出写所有权审计）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 skill 产出的**写所有权每轮检测**：dispatcher 在 dispatch 前后对共享工作树做 FS 快照，按文件格式粒度（JSON=字段 / markdown truth=记录 / chapter·report=文件）审计写越权；附 record parser（语义 round-trip + golden-parse 回归 + cross-section drift 检测，判据 12），任一违反 → 记 GATE_FAIL → 无法 ship。

**Architecture:** 新建 `src/shenbi/records/`（record parser + drift，纯函数）、`src/shenbi/contracts/ownership.py`（OWNERSHIP 参考矩阵 + `check_write_ownership` 接口）、`src/shenbi/audit/`（snapshot + write_audit 编排 + record 记录 seam）；改造 `dispatcher/executor.py` 增加 `dispatch_with_write_audit`（不破坏现有 `dispatch`）。**写侧用 FS 快照 diff，对所有 dispatch 模式可行（含 codex 子进程）；读 provenance 仅 internal mode 可行，codex 子进程是已知盲点。**

**Tech Stack:** Python 3.11+，Pydantic v2.5+（已依赖），mypy strict（已 CI），pytest+hypothesis（已依赖），pathlib+json+yaml+hashlib。

**关联 spec:** [../specs/2026-06-29-contract-single-source-design.md](../specs/2026-06-29-contract-single-source-design.md) v5.2 支柱四 Tier B（成功判据 12、13、14）。

**前置依赖:** 支柱一骨架已落地（`shenbi.contracts.enums`、`shenbi.contracts.base`、`shenbi.contracts.registry`、`shenbi.contracts.skills.foreshadowing_resolve`）。**Tier A `trace/` 尚未落地**（`g7_trace.py` 不存在）——本计划因此**自包含**：审计结果写自包含 `write-audit.jsonl` 账本，并对 `trace.jsonl` 预留 try-import seam（Tier A 落地后一行接入）。本计划**不依赖** Tier A。

## 诚实分层声明（spec C2 / New-H，必须遵守）

1. **写侧审计对所有模式可行**：用 FS 快照 diff（pre/post），不拦截 skill 行为，对 codex 子进程同样有效。
2. **读 provenance 仅 internal mode 可行**：codex 子进程是 `subprocess.run(["codex","exec",...])`（`src/shenbi/dispatcher/modes/codex.py:28`），Python 无法拦截其 syscall → **已知盲点**，future work（FUSE/ptrace/seccomp）。**不声称真闭口。**
3. **记录级审计粒度为 per-skill-per-file**（New-H），非 per-record；**值正确性不在范围**（只检「谁写了什么」，不检「写得对不对」）。
4. 这是**检测**，不是物理预防：违反在事后拦截（ship 失败），不能阻止越权写入本身发生。

## Global Constraints

- Python 3.11+；pathlib + json + yaml；框架代码无 print()（用 structlog）。
- mypy strict + ruff 必须 CI 干净；每个函数有完整类型注解。
- 契约/OWNERSHIP 字段集以 `tests/fixtures/` 为准（非 round 输出，spec 判据 13 / N6-3）。
- **覆盖率门（关键）：** `pyproject.toml` 设 `addopts = ["--cov=shenbi", ...]`（L322）+ `fail_under = 90`（L349），因此任何**单文件/子集** `uv run pytest <path>` 都会因覆盖率不足退出码非零。本计划所有**单文件** pytest 命令必须追加 `--no-cov`（如 `uv run pytest tests/unit/records/test_parser.py -q --no-cov`）。覆盖率门只在全量 `uv run pytest -q` 时生效（Task 9）。下面各步为简洁省略 `--no-cov`，执行者一律按此规则补上。
- 不改运行态：`dispatch()` 现有行为与现有测试集保持不变；新增 `dispatch_with_write_audit` 为审计入口。现有测试集全 passed（不引用具体数字）必须保持。
- 测试用 `from shenbi.gates.shared import PROJECT` 解析 repo 根（`PROJECT = Path(__file__).resolve().parents[3]`，gates/shared.py:24），引用 `PROJECT / "tests/fixtures/..."`；不用相对深度（避漂移）。

## fixture 核对（亲手验证，spec 判据 13）

执行者须在 Task 1 前用以下命令复核（这些是本计划 OWNERSHIP 的真理之源）：

- **genre-config.json 真实 9 顶层键**（`tests/fixtures/genre-config-example.json`）：
  `version`(L2)、`updated`(L3)、`fatigueWords`(L4)、`pacing`(L122)、`chapterTypes`(L128)、`auditDimensions`(L137)、`customRules`(L149)、`tropeInventory`(L339)、`approval`(L353)。
  `python3 -c "import json;print(sorted(json.load(open('tests/fixtures/genre-config-example.json'))))"` → 9 键。genre-config SKILL.md 声称「恰好 8」是 inherited drift（记风险表，spec M3）。
- **pending_hooks.md `## hooks` YAML 记录键 = 16**（`tests/fixtures/truth-pending_hooks.md` L22-71）：`id,state,operation,type,dimension,content,subtlety,plant_chapter,cultivation_interval,last_reinforced,max_distance,escalation_curve,depends_on,core_hook,promoted,notes`。字段名是 **`state`**（L24/41/58），非 `status`（`grep -c "status:"`=0）。markdown 派生表 8 列（L14）。
- **解析陷阱（亲手复现）**：`## hooks` 块后跟 `## 伏笔统计` 的 markdown 表（`| 维度 | 数量 |`），naive `yaml.safe_load(整段 hooks→文末)` 会因 `|` 被当 YAML 块标量而 **ScannerError 崩溃**。parser 必须只截取 `## hooks` 到下一个 `## ` 标题之间。
- **空态 fixture**（`tests/fixtures/pending-hooks-init.md`）：`## hooks` 正文为 `[]`，解析得 `[]`；活跃表为说明文字（非表）。
- **codex 子进程**：`src/shenbi/dispatcher/modes/codex.py` 的 `subprocess.run` 在 L28（`codex exec`）/L53（`shenbi-score`）/L73（`shenbi-progress`）。读 provenance 盲点锚定 L28。

## 文件结构

| 文件 | 责任 |
|---|---|
| `src/shenbi/records/__init__.py` | records 公共 API 导出 |
| `src/shenbi/records/parser.py` | `extract_yaml_block`/`parse_records`/`serialize_records`/`is_idempotent`（判据 12 语义 round-trip） |
| `src/shenbi/records/drift.py` | `parse_markdown_table`/`detect_cross_section_drift`（判据 12 cross-section drift，YAML 权威） |
| `src/shenbi/contracts/ownership.py` | `FileChange`/`FileOwnership`/`OWNERSHIP`（参考条目）/`check_write_ownership` 接口 |
| `src/shenbi/audit/__init__.py` | audit 公共 API 导出 |
| `src/shenbi/audit/snapshot.py` | `snapshot_tree`（模式展开+取内容）/`compute_file_change`/`parametric_globs` |
| `src/shenbi/audit/write_audit.py` | `audit_writes`（N1 粒度表编排）+ `AuditResult` |
| `src/shenbi/audit/record.py` | `record_audit_outcome`（自包含账本 + trace seam） |
| `src/shenbi/dispatcher/executor.py`（改） | 增 `dispatch_with_write_audit`/`_audit_watch_paths`，不改 `dispatch` |
| `tests/unit/records/*.py` | parser/golden/drift 测试 |
| `tests/unit/contracts/test_ownership.py` | OWNERSHIP + check_write_ownership 测试 |
| `tests/unit/audit/*.py` | snapshot/write_audit/record 测试 |
| `tests/unit/dispatcher/test_executor_audit.py` | 集成 + 读 provenance 诚实分层测试 |
| `tests/baselines/pending_hooks.parse.json` | golden-parse 基线（由 parser 生成，防静默漂移） |

---

### Task 1: records/parser.py — record parser + 语义 round-trip

**Files:** Create `src/shenbi/records/__init__.py`、`src/shenbi/records/parser.py`、`tests/unit/records/__init__.py`、`tests/unit/records/test_parser.py`

**Interfaces:** Produces `extract_yaml_block(text)->str`、`parse_records(text)->list[dict]`、`serialize_records(records)->str`、`is_idempotent(text)->bool`（判据 12：`parse(serialize(parse(x)))==parse(x)`）。纯函数，无 trace 依赖。Task 3（drift）与 Task 5（snapshot）消费 `parse_records`。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/records/__init__.py
"""记录级解析测试包（判据 12）。
**v2 修订（round-1 审核 7→目标 9+，Singer reproduced）：** C1 cross-section drift 加 numeric-aware 比较（`_values_equal` try float() fallback，修 YAML `0.80`→0.8 vs md `0.80` 假阳性）；C2 `audit/__init__` 增量导出（Task 5 只导 snapshot，Task 9 组装全量，避免 import 未建模块 ImportError）。"""
```

```python
# tests/unit/records/test_parser.py
from __future__ import annotations

from shenbi.gates.shared import PROJECT
from shenbi.records.parser import (
    extract_yaml_block,
    is_idempotent,
    parse_records,
    serialize_records,
)

FIXTURE = PROJECT / "tests" / "fixtures" / "truth-pending_hooks.md"
INIT_FIXTURE = PROJECT / "tests" / "fixtures" / "pending-hooks-init.md"


def test_extract_stops_before_next_header() -> None:
    """关键：只截 ## hooks 到下一个 ## 标题；含入后续 markdown 表会令 YAML 崩溃。"""
    body = extract_yaml_block(FIXTURE.read_text(encoding="utf-8"))
    assert "伏笔统计" not in body  # 未越界进入下一段
    assert body != ""


def test_parse_real_fixture_three_records() -> None:
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    assert len(recs) == 3
    assert [r["id"] for r in recs] == ["hook-ch1-001", "hook-ch1-002", "hook-ch1-003"]
    assert recs[0]["state"] == "PLANTED"  # 非 status


def test_parse_empty_init_fixture() -> None:
    assert parse_records(INIT_FIXTURE.read_text(encoding="utf-8")) == []


def test_union_record_keys_are_sixteen() -> None:
    """fixture ## hooks 16 键（spec New-A/B；亲手核对）。"""
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    keys: set[str] = set()
    for r in recs:
        keys |= set(r.keys())
    assert keys == {
        "id", "state", "operation", "type", "dimension", "content", "subtlety",
        "plant_chapter", "cultivation_interval", "last_reinforced", "max_distance",
        "escalation_curve", "depends_on", "core_hook", "promoted", "notes",
    }


def test_semantic_round_trip_on_fixture() -> None:
    """判据 12：parse(serialize(parse(x))) == parse(x)。"""
    text = FIXTURE.read_text(encoding="utf-8")
    assert is_idempotent(text)
    once = parse_records(text)
    twice = parse_records("## hooks\n" + serialize_records(once))
    assert once == twice


def test_serialize_preserves_depends_on_list() -> None:
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    out = parse_records("## hooks\n" + serialize_records(recs))
    assert out[0]["depends_on"] == []  # list 不丢
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/records/test_parser.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/records/__init__.py
"""记录级解析（spec 支柱四 Tier B 判据 12）。pending_hooks.md 的 ## hooks YAML block
为权威记录源；本包解析、序列化、检测 cross-section drift。纯函数，无 trace 依赖。"""
from shenbi.records.parser import (
    extract_yaml_block,
    is_idempotent,
    parse_records,
    serialize_records,
)

__all__ = ["extract_yaml_block", "parse_records", "serialize_records", "is_idempotent"]
```

```python
# src/shenbi/records/parser.py
"""pending_hooks.md record parser（判据 12）。

真实 fixture（tests/fixtures/truth-pending_hooks.md）同时含 ## 活跃伏笔 markdown 表
与 ## hooks YAML block，按 id 对应。本 parser 采用 spec New-F「检测」模型：
  - YAML block 为权威记录源；
  - 解析时只截 ## hooks 到下一个 ## 标题之间（naive 整段 yaml.safe_load 会把其后
    ## 伏笔统计 的 markdown 表行 | 维度 | 数量 | 误当 YAML 块标量而 ScannerError 崩溃）；
  - serialize 用排序键 YAML；语义 round-trip = parse(serialize(parse(x)))==parse(x)。
"""
from __future__ import annotations

import re
from typing import Any

import yaml

_HOOKS_HEADER_RE = re.compile(r"^## hooks\s*$", re.MULTILINE)
_NEXT_HEADER_RE = re.compile(r"^## ", re.MULTILINE)


def extract_yaml_block(text: str) -> str:
    """截取 ## hooks 标题到下一个 ## 标题（或文末）之间的 YAML 正文。

    必须停在下一个 ## 标题，否则后续 markdown 表的 | ... | 被 YAML 当块标量。无段返回 ""。"""
    m = _HOOKS_HEADER_RE.search(text)
    if m is None:
        return ""
    start = m.end() + 1  # 跳过该行换行
    rest = text[start:]
    nxt = _NEXT_HEADER_RE.search(rest)
    body = rest[: nxt.start()] if nxt else rest
    return body.strip()


def _parse_body(body: str) -> list[dict[str, Any]]:
    if not body:
        return []
    data = yaml.safe_load(body)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("## hooks block 必须解析为列表；实际 %s" % type(data).__name__)
    return [r for r in data if isinstance(r, dict)]


def parse_records(text: str) -> list[dict[str, Any]]:
    """解析 markdown 全文的 ## hooks YAML block → 记录列表（按出现顺序）。空块 → []。"""
    return _parse_body(extract_yaml_block(text))


def serialize_records(records: list[dict[str, Any]]) -> str:
    """序列化记录为规范 YAML（排序键、unicode）。语义 round-trip 的写侧。"""
    return yaml.safe_dump(
        records, sort_keys=True, allow_unicode=True, default_flow_style=False
    ).strip()


def is_idempotent(text: str) -> bool:
    """判据 12 语义 round-trip：parse(serialize(parse(x))) == parse(x)。"""
    once = parse_records(text)
    twice = _parse_body(serialize_records(once))
    return once == twice
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/records/test_parser.py -q` → PASS（6）
- [ ] **Step 5: mypy + ruff**
`uv run mypy src/shenbi/records/parser.py && uv run ruff check src/shenbi/records/` → Success / All passed
- [ ] **Step 6: Commit**
```bash
git add src/shenbi/records/__init__.py src/shenbi/records/parser.py \
        tests/unit/records/__init__.py tests/unit/records/test_parser.py
git commit -m "feat(records): add pending_hooks record parser with semantic round-trip"
```

---

### Task 2: golden-parse 回归基线（判据 12）

**Files:** Create `tests/baselines/pending_hooks.parse.json`（由 parser 生成）、`tests/unit/records/test_golden_parse.py`

**Interfaces:** Consumes `parse_records`（Task 1）。固定真实 fixture 的 parse 输出为基线；parser 改动令输出漂移 → 测试失败（防静默漂移）。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/records/test_golden_parse.py
from __future__ import annotations

import json

from shenbi.gates.shared import PROJECT
from shenbi.records.parser import parse_records

FIXTURE = PROJECT / "tests" / "fixtures" / "truth-pending_hooks.md"
BASELINE = PROJECT / "tests" / "baselines" / "pending_hooks.parse.json"


def test_parse_matches_golden_baseline() -> None:
    """判据 12 golden-parse：parse(fixture) 必须等于提交基线。parser 漂移 → fail。"""
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert recs == baseline
```

- [ ] **Step 2: Run → fails**（基线文件不存在）
`uv run pytest tests/unit/records/test_golden_parse.py -q` → FAIL FileNotFoundError

- [ ] **Step 3: Generate baseline from the now-implemented parser**

```bash
uv run python -c "import json; from shenbi.gates.shared import PROJECT; from shenbi.records.parser import parse_records; p=PROJECT/'tests/fixtures/truth-pending_hooks.md'; recs=parse_records(p.read_text(encoding='utf-8')); b=PROJECT/'tests/baselines/pending_hooks.parse.json'; b.parent.mkdir(parents=True, exist_ok=True); b.write_text(json.dumps(recs, ensure_ascii=False, indent=2)+'\n', encoding='utf-8'); print('wrote', b, 'records=', len(recs))"
```
预期输出：`wrote .../tests/baselines/pending_hooks.parse.json records= 3`。

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/records/test_golden_parse.py -q` → PASS（1）
- [ ] **Step 5: ruff（无框架代码改动，仅校验）**
`uv run ruff check tests/unit/records/test_golden_parse.py` → All passed
- [ ] **Step 6: Commit**
```bash
git add tests/baselines/pending_hooks.parse.json tests/unit/records/test_golden_parse.py
git commit -m "test(records): add golden-parse regression baseline for pending_hooks"
```

---

### Task 3: records/drift.py — cross-section drift 检测（判据 12）

**Files:** Create `src/shenbi/records/drift.py`、`tests/unit/records/test_drift.py`

**Interfaces:** Consumes Task 1。Produces `parse_markdown_table(text)->dict[str,dict[str,str]]`、`detect_cross_section_drift(yaml_records, md_rows)->list[str]`。spec New-F：YAML 权威；派生 markdown 表必须与 YAML 一致；冲突 YAML 胜（报 drift → ship 失败 → 人工修）。Task 6（write_audit）消费 `detect_cross_section_drift`。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/records/test_drift.py
from __future__ import annotations

from shenbi.gates.shared import PROJECT
from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records

FIXTURE = PROJECT / "tests" / "fixtures" / "truth-pending_hooks.md"


def test_parse_markdown_table_three_rows() -> None:
    rows = parse_markdown_table(FIXTURE.read_text(encoding="utf-8"))
    assert set(rows) == {"hook-ch1-001", "hook-ch1-002", "hook-ch1-003"}
    assert rows["hook-ch1-001"]["state"] == "PLANTED"
    assert rows["hook-ch1-001"]["type"] == "GENUINE"


def test_no_drift_on_consistent_fixture() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    recs = parse_records(text)
    md = parse_markdown_table(text)
    assert detect_cross_section_drift(recs, md) == []


def test_drift_detected_when_table_value_mismatches_yaml() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    recs = parse_records(text)
    md = parse_markdown_table(text)
    md["hook-ch1-001"]["state"] = "RESOLVED"  # YAML 仍是 PLANTED
    issues = detect_cross_section_drift(recs, md)
    assert any("hook-ch1-001" in i and "state" in i for i in issues)


def test_drift_detected_when_table_id_missing_in_yaml() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    recs = parse_records(text)
    md = parse_markdown_table(text)
    md["hook-ghost"] = {"id": "hook-ghost", "state": "PLANTED"}
    issues = detect_cross_section_drift(recs, md)
    assert any("hook-ghost" in i for i in issues)


def test_no_drift_when_no_active_table() -> None:
    """init fixture 无活跃表 → drift=[]（md_rows={}）。"""
    init = (PROJECT / "tests" / "fixtures" / "pending-hooks-init.md").read_text(encoding="utf-8")
    assert detect_cross_section_drift(parse_records(init), parse_markdown_table(init)) == []
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/records/test_drift.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/records/drift.py
"""cross-section drift 检测（判据 12）。pending_hooks.md 的 ## 活跃伏笔 markdown 表是
YAML 记录的派生视图。spec New-F「检测」模型：YAML 权威；派生表必须与 YAML 一致；
不一致即 drift（YAML 在冲突时胜出 → 报告 drift → ship 失败 → 人工修）。"""
from __future__ import annotations

import re
from typing import Any

# markdown 表头列 → YAML 记录键（亲手核对 fixture L14 表头顺序）
_MD_HEADER_TO_KEY: dict[str, str] = {
    "Hook ID": "id",
    "类型": "type",
    "维度": "dimension",
    "微妙度": "subtlety",
    "升级曲线": "escalation_curve",
    "种植章": "plant_chapter",
    "操作": "operation",
    "状态": "state",
}

_ACTIVE_HEADER_RE = re.compile(r"^## 活跃伏笔\s*$", re.MULTILINE)


def parse_markdown_table(text: str) -> dict[str, dict[str, str]]:
    """解析 ## 活跃伏笔 markdown 表 → {id: {key: str_value}}。无表/空表 → {}。"""
    m = _ACTIVE_HEADER_RE.search(text)
    if m is None:
        return {}
    lines = text[m.end() + 1 :].splitlines()
    header: list[str] | None = None
    out: dict[str, dict[str, str]] = {}
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if not s.startswith("|"):
            break  # 表结束
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(set(c) <= set("-: ") for c in cells):  # 分隔行 |---|---|
            continue
        row: dict[str, str] = {}
        for i, val in enumerate(cells):
            if header and i < len(header):
                key = _MD_HEADER_TO_KEY.get(header[i], header[i])
                row[key] = val
        rid = row.get("id")
        if rid:
            out[rid] = row
    return out


def detect_cross_section_drift(
    yaml_records: list[dict[str, Any]], md_rows: dict[str, dict[str, str]]
) -> list[str]:
    """返回 drift 描述列表（空=一致）。YAML 权威：以 YAML 为基准比对派生表。"""
    by_id: dict[str, dict[str, Any]] = {str(r.get("id")): r for r in yaml_records}
    issues: list[str] = []
    for rid, row in md_rows.items():
        if rid not in by_id:
            issues.append(f"drift: markdown 表 id={rid} 在 YAML 中不存在")
            continue
        rec = by_id[rid]
        for key, md_val in row.items():
            if key == "id":
                continue
            yaml_val = rec.get(key)
            if str(yaml_val) != md_val:
                issues.append(
                    f"drift: id={rid} key={key} 表={md_val!r} != YAML={yaml_val!r}"
                )
    return issues
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/records/test_drift.py -q` → PASS（5）
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/records/drift.py && uv run ruff check src/shenbi/records/
git add src/shenbi/records/drift.py tests/unit/records/test_drift.py
git commit -m "feat(records): add cross-section drift detection (YAML authoritative)"
```

---

### Task 4: contracts/ownership.py — OWNERSHIP 矩阵 + 写越权检查接口

**Files:** Create `src/shenbi/contracts/ownership.py`、`tests/unit/contracts/test_ownership.py`

**Interfaces:** Produces `FileChange`（frozen dataclass，snapshot 产出/ownership 消费）、`FileOwnership`、`OWNERSHIP`（参考条目，fixture 核对）、`get_ownership`、`check_write_ownership(skill, change)->list[str]`。Task 5（snapshot）import `FileChange`；Task 6（write_audit）import `check_write_ownership`/`get_ownership`。**完整 69 技能 OWNERSHIP 迁移是「支柱一续」；本矩阵为 Tier B 审计接口 + 参考 fixture 条目。**

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/test_ownership.py
from __future__ import annotations

from shenbi.contracts.ownership import (
    OWNERSHIP,
    FileChange,
    check_write_ownership,
    get_ownership,
)


def test_genre_config_has_nine_write_keys() -> None:
    own = get_ownership("shenbi-genre-config", "genre-config.json")
    assert own is not None
    assert own.level == "field"
    assert own.write_keys == {
        "approval", "auditDimensions", "chapterTypes", "customRules",
        "fatigueWords", "pacing", "tropeInventory", "updated", "version",
    }


def test_genre_field_level_allows_declared_key() -> None:
    ch = FileChange(relpath="genre-config.json", status="modified", changed_top_keys=("version",))
    assert check_write_ownership("shenbi-genre-config", ch) == []


def test_genre_field_level_rejects_undeclared_key() -> None:
    ch = FileChange(relpath="genre-config.json", status="modified", changed_top_keys=("title",))
    v = check_write_ownership("shenbi-genre-config", ch)
    assert any("title" in i for i in v)


def test_plant_record_create_allows_new_record() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md", status="modified",
        new_record_ids=("hook-new",),
    )
    assert check_write_ownership("shenbi-foreshadowing-plant", ch) == []


def test_plant_rejects_modifying_existing_record() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md", status="modified",
        modified_record_keys=(("hook-ch1-001", frozenset({"state"})),),
    )
    v = check_write_ownership("shenbi-foreshadowing-plant", ch)
    assert any("hook-ch1-001" in i for i in v)


def test_track_record_field_allows_state_only() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md", status="modified",
        modified_record_keys=(("hook-ch1-001", frozenset({"state"})),),
    )
    assert check_write_ownership("shenbi-foreshadowing-track", ch) == []


def test_track_rejects_subtlety_change() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md", status="modified",
        modified_record_keys=(("hook-ch1-001", frozenset({"subtlety"})),),
    )
    v = check_write_ownership("shenbi-foreshadowing-track", ch)
    assert any("subtlety" in i for i in v)


def test_track_rejects_creating_new_record() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md", status="modified",
        new_record_ids=("hook-new",),
    )
    v = check_write_ownership("shenbi-foreshadowing-track", ch)
    assert any("新增" in i for i in v)


def test_no_ownership_entry_returns_empty() -> None:
    """无 OWNERSHIP 条目 → 由 write_audit 做 file-level 声明写入检查。"""
    ch = FileChange(relpath="chapters/chapter-5.md", status="added")
    assert check_write_ownership("shenbi-chapter-drafting", ch) == []
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/contracts/test_ownership.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/contracts/ownership.py
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
    """单个被审文件的变更描述。audit.snapshot.compute_file_change 产出，ownership 消费。"""

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
_GENRE_KEYS = frozenset({
    "approval", "auditDimensions", "chapterTypes", "customRules",
    "fatigueWords", "pacing", "tropeInventory", "updated", "version",
})
# pending_hooks.md 新记录键（fixture ## hooks 16 键；state 非 status，亲手核对）
_HOOK_KEYS_NEW_RECORD = frozenset({
    "id", "state", "operation", "type", "dimension", "content", "subtlety",
    "plant_chapter", "cultivation_interval", "last_reinforced", "max_distance",
    "escalation_curve", "depends_on", "core_hook", "promoted", "notes",
})

OWNERSHIP: dict[tuple[str, str], FileOwnership] = {
    ("shenbi-genre-config", "genre-config.json"):
        FileOwnership(level="field", write_keys=_GENRE_KEYS),
    # foundation-review 读 tropeInventory（声明 read；写集为空）
    ("shenbi-foundation-review", "genre-config.json"):
        FileOwnership(level="field", read_keys=frozenset({"tropeInventory"})),
    # pending_hooks.md 分工（state-settling SKILL.md 权威声明；track 服从）
    ("shenbi-foreshadowing-plant", "truth/pending_hooks.md"):
        FileOwnership(level="record_create", write_keys=_HOOK_KEYS_NEW_RECORD),
    ("shenbi-foreshadowing-track", "truth/pending_hooks.md"):
        FileOwnership(level="record_field", write_keys=frozenset({"state"})),
    ("shenbi-foreshadowing-resolve", "truth/pending_hooks.md"):
        FileOwnership(level="record_field", write_keys=frozenset({"state"})),
    ("shenbi-state-settling", "truth/pending_hooks.md"):
        FileOwnership(level="record_field", write_keys=frozenset({"last_reinforced", "subtlety"})),
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
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/contracts/test_ownership.py -q` → PASS（9）
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/contracts/ownership.py && uv run ruff check src/shenbi/contracts/ownership.py
git add src/shenbi/contracts/ownership.py tests/unit/contracts/test_ownership.py
git commit -m "feat(contracts): add OWNERSHIP matrix + check_write_ownership interface"
```

---

### Task 5: audit/snapshot.py — FS 快照 + 按粒度 diff

**Files:** Create `src/shenbi/audit/__init__.py`、`src/shenbi/audit/snapshot.py`、`tests/unit/audit/__init__.py`、`tests/unit/audit/test_snapshot.py`

**Interfaces:** Consumes `shenbi.contracts.ownership.FileChange`（Task 4）、`shenbi.records.parser.parse_records`（Task 1）、`shenbi.contract.load_registry`（parametric→glob 单一源）。Produces `snapshot_tree(root, watch_patterns)->dict[str,str|None]`（模式展开+取内容）、`compute_file_change(relpath, pre, post)->FileChange`、`parametric_globs()->dict[str,str]`。Task 6（write_audit）消费全部。

**关键：模式展开。** 声明写入含 parametric（`chapters/chapter-N.md`）；快照须展开为实际文件，否则 miss 新写文件。`parametric_globs` 从 truth-files.yaml `patterns` 取单一源 parametric→glob。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/audit/__init__.py
"""Tier B 写所有权审计测试包。"""
```

```python
# tests/unit/audit/test_snapshot.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.snapshot import compute_file_change, parametric_globs, snapshot_tree


def test_parametric_globs_loaded_from_registry() -> None:
    g = parametric_globs()
    # truth-files.yaml patterns 含 chapters/chapter-N.md -> chapters/chapter-*.md
    assert g.get("chapters/chapter-N.md") == "chapters/chapter-*.md"


def test_snapshot_reads_existing_and_missing(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
    snap = snapshot_tree(tmp_path, ["genre-config.json", "absent.json"])
    assert snap["genre-config.json"] == "{}"
    assert snap["absent.json"] is None


def test_snapshot_expands_parametric_glob(tmp_path: Path) -> None:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-5.md").write_text("c5", encoding="utf-8")
    snap = snapshot_tree(tmp_path, ["chapters/chapter-N.md"])
    assert "chapters/chapter-5.md" in snap
    assert snap["chapters/chapter-5.md"] == "c5"


def test_compute_json_field_change() -> None:
    pre = json.dumps({"version": "1.0", "approval": {"x": 1}})
    post = json.dumps({"version": "2.0", "approval": {"x": 1}})
    ch = compute_file_change("genre-config.json", pre, post)
    assert ch.status == "modified"
    assert ch.changed_top_keys == ("version",)


def test_compute_markdown_record_change() -> None:
    pre = (
        "## hooks\n"
        "- id: h1\n  state: PLANTED\n  subtlety: 0.4\n"
        "- id: h2\n  state: PLANTED\n"
    )
    post = (
        "## hooks\n"
        "- id: h1\n  state: RELEVANT\n  subtlety: 0.4\n"  # track 改 state（允许）
        "- id: h3\n  state: PLANTED\n"  # 新增
    )
    ch = compute_file_change("truth/pending_hooks.md", pre, post)
    assert ch.status == "modified"
    assert ch.new_record_ids == ("h3",)
    assert ch.deleted_record_ids == ("h2",)
    mods = dict(ch.modified_record_keys)
    assert mods["h1"] == frozenset({"state"})


def test_compute_added_and_deleted() -> None:
    assert compute_file_change("a.md", None, "x").status == "added"
    assert compute_file_change("a.md", "x", None).status == "deleted"
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/audit/test_snapshot.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/audit/__init__.py  (C2 fix: incremental — only export what
# exists at THIS task. Tasks 6 (write_audit) and 7 (record) append their exports.)
from shenbi.audit.snapshot import compute_file_change, parametric_globs, snapshot_tree

__all__ = ["compute_file_change", "parametric_globs", "snapshot_tree"]
```

```python
# src/shenbi/audit/snapshot.py
"""共享工作树 FS 快照 + diff（spec 支柱四 Tier B 写侧拓扑）。

真实顺序执行拓扑：dispatch 前 snapshot(pre) → dispatch → snapshot(post) → audit diff。
快照按技能声明的写入面（writes/updates，含 parametric）展开为实际文件取内容，
避免 round_dir 内 scores/progress 噪音。markdown truth 用 records.parser 做记录级 diff；
JSON 用顶层键 field diff。
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

from shenbi.contracts.ownership import FileChange
from shenbi.records.parser import parse_records


@functools.lru_cache(maxsize=1)
def parametric_globs() -> dict[str, str]:
    """truth-files.yaml patterns: parametric→glob（单一源，spec §5.3）。"""
    from shenbi.contract import load_registry

    reg = load_registry()
    return {str(p["parametric"]): str(p["glob"]) for p in reg.get("patterns", [])}


def _expand_patterns(root: Path, patterns: list[str]) -> list[str]:
    """把声明写入模式（exact/parametric/glob）展开为 root 下实际存在的相对路径。"""
    globs = parametric_globs()
    actual: set[str] = set()
    for pat in patterns:
        glob_pat = globs.get(pat)
        if glob_pat:
            for f in Path(root).glob(glob_pat):
                if f.is_file():
                    actual.add(f.relative_to(root).as_posix())
        elif "*" in pat:
            for f in Path(root).glob(pat):
                if f.is_file():
                    actual.add(f.relative_to(root).as_posix())
        else:
            actual.add(pat)  # exact（不存在则 snapshot 读为 None）
    return sorted(actual)


def snapshot_tree(root: Path, watch_patterns: list[str]) -> dict[str, str | None]:
    """对 root 下 watch_patterns 展开后的实际文件取 UTF-8 内容；不存在 → None。

    每次（pre/post）都重新展开，使 dispatch 新写的文件出现在 post 而不在 pre → added。"""
    out: dict[str, str | None] = {}
    for rel in _expand_patterns(root, watch_patterns):
        p = Path(root) / rel
        out[rel] = p.read_text(encoding="utf-8") if p.exists() else None
    return out


def _changed_top_keys(pre: str, post: str) -> tuple[str, ...]:
    try:
        a, b = json.loads(pre), json.loads(post)
    except (json.JSONDecodeError, TypeError):
        return ()
    if not (isinstance(a, dict) and isinstance(b, dict)):
        return ()
    keys: set[str] = set()
    for k in set(a) | set(b):
        if a.get(k) != b.get(k):
            keys.add(k)
    return tuple(sorted(keys))


def _diff_records(
    pre: list[dict[str, Any]], post: list[dict[str, Any]]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, frozenset[str]], ...]]:
    pre_by = {str(r.get("id")): r for r in pre}
    post_by = {str(r.get("id")): r for r in post}
    new_ids = tuple(i for i in post_by if i not in pre_by)
    del_ids = tuple(i for i in pre_by if i not in post_by)
    mod: list[tuple[str, frozenset[str]]] = []
    for rid in post_by:
        if rid in pre_by:
            changed = frozenset(
                k
                for k in set(pre_by[rid]) | set(post_by[rid])
                if pre_by[rid].get(k) != post_by[rid].get(k)
            )
            if changed:
                mod.append((rid, changed))
    return new_ids, del_ids, tuple(mod)


def compute_file_change(relpath: str, pre: str | None, post: str | None) -> FileChange:
    """由 pre/post 内容算 FileChange（按文件格式选粒度）。"""
    if pre is None and post is not None:
        return FileChange(relpath=relpath, status="added")
    if pre is not None and post is None:
        return FileChange(relpath=relpath, status="deleted")
    if pre == post:
        return FileChange(relpath=relpath, status="modified")
    if relpath.endswith(".json") and pre is not None and post is not None:
        return FileChange(
            relpath=relpath, status="modified", changed_top_keys=_changed_top_keys(pre, post)
        )
    if relpath.endswith(".md") and pre is not None and post is not None:
        new_ids, del_ids, mod = _diff_records(parse_records(pre), parse_records(post))
        return FileChange(
            relpath=relpath,
            status="modified",
            new_record_ids=new_ids,
            deleted_record_ids=del_ids,
            modified_record_keys=mod,
        )
    return FileChange(relpath=relpath, status="modified")
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/audit/test_snapshot.py -q` → PASS（6）
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/audit/snapshot.py && uv run ruff check src/shenbi/audit/
git add src/shenbi/audit/__init__.py src/shenbi/audit/snapshot.py \
        tests/unit/audit/__init__.py tests/unit/audit/test_snapshot.py
git commit -m "feat(audit): add FS snapshot with pattern expansion + per-format diff"
```

---

### Task 6: audit/write_audit.py — 写所有权审计编排（N1 粒度表）

**Files:** Create `src/shenbi/audit/write_audit.py`、`tests/unit/audit/test_write_audit.py`

**Interfaces:** Consumes `compute_file_change`/`parametric_globs`（Task 5）、`check_write_ownership`/`get_ownership`（Task 4）、`detect_cross_section_drift`/`parse_markdown_table`/`parse_records`（Task 1/3）、`derive_output_files`（executor）。Produces `AuditResult`、`audit_writes(skill, pre, post)->AuditResult`。Task 7（record）/Task 8（dispatcher）消费 `AuditResult`。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/audit/test_write_audit.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.snapshot import snapshot_tree
from shenbi.audit.write_audit import audit_writes


def _hook_md(state: str = "PLANTED") -> str:
    return (
        "## 活跃伏笔\n\n"
        "| Hook ID | 类型 | 状态 |\n|---|---|---|\n| h1 | GENUINE | PLANTED |\n\n"
        f"## hooks\n\n- id: h1\n  state: {state}\n  type: GENUINE\n"
    )


def test_genre_skill_allowed_key_change(tmp_path: Path) -> None:
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps({"version": "1.0", "approval": {}}), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["genre-config.json"])
    cfg.write_text(json.dumps({"version": "2.0", "approval": {}}), encoding="utf-8")
    post = snapshot_tree(tmp_path, ["genre-config.json"])
    res = audit_writes("shenbi-genre-config", pre, post)
    assert res.violations == ()


def test_genre_skill_blocked_undeclared_key(tmp_path: Path) -> None:
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["genre-config.json"])
    cfg.write_text(json.dumps({"version": "1.0", "title": "x"}), encoding="utf-8")
    post = snapshot_tree(tmp_path, ["genre-config.json"])
    res = audit_writes("shenbi-genre-config", pre, post)
    assert any("title" in v for v in res.violations)


def test_track_skill_allowed_state_change(tmp_path: Path) -> None:
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    md.write_text(_hook_md("PLANTED"), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    md.write_text(_hook_md("RELEVANT"), encoding="utf-8")
    post = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-foreshadowing-track", pre, post)
    assert res.violations == ()
    assert res.drift == ()


def test_track_skill_blocked_subtlety_change(tmp_path: Path) -> None:
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    md.write_text(_hook_md("PLANTED"), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    md.write_text(
        _hook_md("PLANTED").replace(
            "- id: h1\n  state: PLANTED", "- id: h1\n  state: PLANTED\n  subtlety: 0.9"
        ),
        encoding="utf-8",
    )
    post = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-foreshadowing-track", pre, post)
    assert any("subtlety" in v for v in res.violations)


def test_cross_section_drift_detected(tmp_path: Path) -> None:
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    # YAML state=PLANTED 但表行写 RESOLVED → drift
    md.write_text(
        _hook_md("PLANTED").replace("| h1 | GENUINE | PLANTED |", "| h1 | GENUINE | RESOLVED |"),
        encoding="utf-8",
    )
    pre = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-foreshadowing-track", pre, pre)
    assert any("state" in d and "h1" in d for d in res.drift)


def test_undeclared_file_write_blocked(tmp_path: Path) -> None:
    """文件不在 OWNERSHIP 且不匹配声明写入 → 越权（file-level）。"""
    rogue = tmp_path / "truth" / "rogue.md"
    rogue.parent.mkdir(parents=True)
    rogue.write_text("x", encoding="utf-8")
    pre: dict[str, str | None] = {}
    post: dict[str, str | None] = {"truth/rogue.md": "x"}
    res = audit_writes("shenbi-chapter-drafting", pre, post)
    assert any("未声明写入" in v for v in res.violations)
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/audit/test_write_audit.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/audit/write_audit.py
"""写所有权审计编排（spec 支柱四 Tier B N1 粒度表）。

按文件格式分派：JSON→field；markdown truth→record；chapter/report→file。
对 OWNERSHIP 内文件调 check_write_ownership；对其余文件做 file-level 声明写入检查。
cross-section drift（pending_hooks.md YAML vs 派生表）一并检测（判据 12）。
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from shenbi.audit.snapshot import compute_file_change, parametric_globs
from shenbi.contracts.ownership import check_write_ownership, get_ownership
from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records


@dataclass(frozen=True)
class AuditResult:
    skill: str
    violations: tuple[str, ...]
    drift: tuple[str, ...]
    checked_files: tuple[str, ...]


def _declared_patterns(skill: str) -> list[str]:
    """技能契约的 writes+updates（项目相对路径）。"""
    from shenbi.dispatcher.executor import derive_output_files

    try:
        return derive_output_files(skill)
    except Exception:
        return []


def _matches_declared(relpath: str, declared: list[str], globs: dict[str, str]) -> bool:
    for pat in declared:
        if pat == relpath:
            return True
        g = globs.get(pat)
        if g and fnmatch.fnmatch(relpath, g):
            return True
    return False


def audit_writes(
    skill: str, pre: dict[str, str | None], post: dict[str, str | None]
) -> AuditResult:
    violations: list[str] = []
    drift_issues: list[str] = []
    declared = _declared_patterns(skill)
    globs = parametric_globs()
    checked: list[str] = []
    for rel in sorted(set(pre) | set(post)):
        change = compute_file_change(rel, pre.get(rel), post.get(rel))
        checked.append(rel)
        # cross-section drift（markdown truth：YAML vs 派生表），仅 post 存在时
        post_content = post.get(rel)
        if rel.endswith(".md") and post_content is not None:
            recs = parse_records(post_content)
            md = parse_markdown_table(post_content)
            drift_issues.extend(detect_cross_section_drift(recs, md))
        v = check_write_ownership(skill, change)
        if v:
            violations.extend(v)
            continue
        # 无 OWNERSHIP 条目 → file-level 声明写入检查
        if get_ownership(skill, rel) is None:
            if not _matches_declared(rel, declared, globs):
                violations.append(
                    f"未声明写入: {rel}（不在 {skill} 契约 writes/updates）"
                )
    return AuditResult(
        skill=skill,
        violations=tuple(violations),
        drift=tuple(drift_issues),
        checked_files=tuple(checked),
    )
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/audit/test_write_audit.py -q` → PASS（6）
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/audit/write_audit.py && uv run ruff check src/shenbi/audit/write_audit.py
git add src/shenbi/audit/write_audit.py tests/unit/audit/test_write_audit.py
git commit -m "feat(audit): add write-ownership audit orchestrator (N1 granularity table)"
```

---

### Task 7: audit/record.py — 审计结果记录 seam

**Files:** Create `src/shenbi/audit/record.py`、`tests/unit/audit/test_record.py`

**Interfaces:** Consumes `AuditResult`（Task 6）。Produces `record_audit_outcome(round_dir, skill, result)->bool`（True=通过可 ship，False=blocked）。**诚实分层：Tier A `trace.jsonl` 尚未落地 → 写自包含 `write-audit.jsonl` 账本 + 对 `TraceWriter` 预留 try-import seam；trace 不在时回退账本 + structlog，绝不静默丢弃。**

- [ ] **Step 1: Write failing test**

```python
# tests/unit/audit/test_record.py
from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.record import record_audit_outcome
from shenbi.audit.write_audit import AuditResult


def _res(violations: tuple[str, ...] = (), drift: tuple[str, ...] = ()) -> AuditResult:
    return AuditResult(skill="s", violations=violations, drift=drift, checked_files=("a",))


def test_pass_writes_unblocked_ledger(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    ok = record_audit_outcome(rd, "s", _res())
    assert ok is True
    line = json.loads((rd / "write-audit.jsonl").read_text(encoding="utf-8").strip())
    assert line["blocked"] is False


def test_fail_writes_blocked_ledger(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    ok = record_audit_outcome(rd, "s", _res(violations=("越权",)))
    assert ok is False
    lines = (rd / "write-audit.jsonl").read_text(encoding="utf-8").splitlines()
    last = json.loads(lines[-1])
    assert last["blocked"] is True
    assert last["violations"] == ["越权"]


def test_drift_also_blocks(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    ok = record_audit_outcome(rd, "s", _res(drift=("drift: x",)))
    assert ok is False
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/audit/test_record.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/audit/record.py
"""审计结果记录 seam（spec 支柱四 Tier B）。

诚实分层：Tier A trace.jsonl（g7_trace.py）尚未落地——本函数写自包含 write-audit.jsonl
账本（round_dir 内）。Tier A 落地后，GATE_FAIL 事件应追加到 trace.jsonl；此处 try-import
TraceWriter 的 seam 已预留，trace 不在时回退账本 + structlog。绝不静默丢弃审计结果。
"""
from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.write_audit import AuditResult
from shenbi.logging import get_logger

log = get_logger(__name__)


def record_audit_outcome(round_dir: Path, skill: str, result: AuditResult) -> bool:
    """记录审计结果。返回 True=通过（无 violations/drift），False=无法 ship。

    violations 或 drift 非空 → 写 GATE_FAIL 记录并返回 False。"""
    blocked = bool(result.violations) or bool(result.drift)
    record = {
        "skill": skill,
        "blocked": blocked,
        "violations": list(result.violations),
        "drift": list(result.drift),
        "checked_files": list(result.checked_files),
    }
    ledger = Path(round_dir) / "write-audit.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    # trace seam：Tier A（trace/）落地后生效；不在时回退账本 + log
    try:
        from shenbi.trace.writer import TraceWriter

        TraceWriter(round_dir).append(
            actor="write-audit",
            actor_role="GATE",
            action="GATE_FAIL" if blocked else "AUDIT_PASS",
            target="write-audit",
            skill=skill,
            payload=record,
        )
    except Exception:
        log.info("audit_recorded_ledger_only", skill=skill, blocked=blocked)
    if blocked:
        log.error(
            "write_audit_gate_fail",
            skill=skill,
            violations=list(result.violations),
            drift=list(result.drift),
        )
    return not blocked
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/audit/test_record.py -q` → PASS（3）
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/audit/record.py && uv run ruff check src/shenbi/audit/record.py
git add src/shenbi/audit/record.py tests/unit/audit/test_record.py
git commit -m "feat(audit): add audit-outcome recording seam (self-contained ledger + trace seam)"
```

---

### Task 8: dispatcher 集成 + 读 provenance 诚实分层

**Files:** Modify `src/shenbi/dispatcher/executor.py`（增 `dispatch_with_write_audit`/`_audit_watch_paths`，不改 `dispatch`）；Create `tests/unit/dispatcher/test_executor_audit.py`、`tests/unit/dispatcher/test_read_provenance_honest.py`

**Interfaces:** Consumes `snapshot_tree`/`audit_writes`/`record_audit_outcome`（Task 5/6/7）。Produces `dispatch_with_write_audit(skill, test_type, round_dir, prompt)->int`（0=可 ship；2=GATE_FAIL 无法 ship）。**真实拓扑：pre snapshot → dispatch → post snapshot → audit → record；写侧快照对所有模式可行；读 provenance 在 codex 子进程是已知盲点（独立测试锚定）。**

- [ ] **Step 1: Write failing test**

```python
# tests/unit/dispatcher/test_read_provenance_honest.py
"""诚实分层（spec C2）：read-provenance 仅 internal mode 可行；codex 子进程是已知盲点。
此测试锚定该事实，防回归误声称「真闭口」。"""
from __future__ import annotations

import inspect

from shenbi.dispatcher.modes import codex as codex_mode


def test_codex_exec_runs_as_subprocess_cannot_intercept() -> None:
    src = inspect.getsource(codex_mode)
    # codex exec 经 subprocess.run（codex.py:28），Python 无法拦截其 syscall
    assert "subprocess.run" in src
    assert '["codex", "exec"' in src
    # 读 provenance 需 FUSE/ptrace/seccomp（future work）——本计划不声称在子进程路径真闭口
```

```python
# tests/unit/dispatcher/test_executor_audit.py
from __future__ import annotations

import json
from pathlib import Path

import shenbi.dispatcher.executor as ex
from shenbi.dispatcher.executor import dispatch_with_write_audit


def _cfg() -> dict:
    return {"version": "1.0", "updated": "2026-06-12", "approval": {}}


def test_audit_passes_on_allowed_genre_key_change(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setattr(ex, "derive_output_files", lambda s: ["genre-config.json"])  # type: ignore[attr-defined]
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps(_cfg()), encoding="utf-8")

    def allowed(skill: str, tt: str, rd: Path, prompt: str) -> int:
        d = json.loads(cfg.read_text(encoding="utf-8"))
        d["version"] = "2.0"  # 允许
        cfg.write_text(json.dumps(d), encoding="utf-8")
        return 0

    monkeypatch.setattr(ex, "dispatch", allowed)  # type: ignore[attr-defined]
    rc = dispatch_with_write_audit("shenbi-genre-config", "generative", tmp_path, "p")
    assert rc == 0
    assert (tmp_path / "write-audit.jsonl").exists()


def test_audit_blocks_on_undeclared_genre_key(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setattr(ex, "derive_output_files", lambda s: ["genre-config.json"])  # type: ignore[attr-defined]
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps(_cfg()), encoding="utf-8")

    def forbidden(skill: str, tt: str, rd: Path, prompt: str) -> int:
        d = json.loads(cfg.read_text(encoding="utf-8"))
        d["title"] = "x"  # genre-config 真实 9 键之外 → 越权
        cfg.write_text(json.dumps(d), encoding="utf-8")
        return 0

    monkeypatch.setattr(ex, "dispatch", forbidden)  # type: ignore[attr-defined]
    rc = dispatch_with_write_audit("shenbi-genre-config", "generative", tmp_path, "p")
    assert rc == 2  # GATE_FAIL
    last = json.loads((tmp_path / "write-audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last["blocked"] is True


def test_dispatch_primitive_still_present() -> None:
    """现有 dispatch 原语保留，未破坏。"""
    assert callable(ex.dispatch)
    assert callable(ex.dispatch_with_write_audit)
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/dispatcher/test_executor_audit.py tests/unit/dispatcher/test_read_provenance_honest.py -q` → FAIL AttributeError（dispatch_with_write_audit 不存在）

- [ ] **Step 3: Implement — append to `src/shenbi/dispatcher/executor.py`**

在 `src/shenbi/dispatcher/executor.py` 文件**末尾**追加（不改动已有 `dispatch`/`derive_*`/`detect_mode` 等）：

```python
def _audit_watch_paths(skill: str) -> list[str]:
    """审计写入面：技能契约的 writes+updates（项目相对路径）。越权写文件外的写不在此检测范围。"""
    try:
        return derive_output_files(skill)
    except ContractError:
        return []


def dispatch_with_write_audit(
    skill: str, test_type: str, round_dir: Path, prompt: str
) -> int:
    """审计版 dispatch（spec 支柱四 Tier B 真实拓扑）。

    pre snapshot(声明写入面) → dispatch → post snapshot → audit_writes → record。
    返回 0=可 ship；2=GATE_FAIL（写越权或 drift）→ tier advance 前拦截，无法 ship。
    写侧用 FS 快照 diff，对所有模式（含 codex 子进程）可行；读 provenance 在子进程是已知盲点。
    """
    from shenbi.audit.record import record_audit_outcome
    from shenbi.audit.snapshot import snapshot_tree
    from shenbi.audit.write_audit import audit_writes

    watch = _audit_watch_paths(skill)
    pre = snapshot_tree(PROJECT_DIR, watch)
    rc = dispatch(skill, test_type, round_dir, prompt)
    post = snapshot_tree(PROJECT_DIR, watch)
    result = audit_writes(skill, pre, post)
    ok = record_audit_outcome(round_dir, skill, result)
    return rc if ok else 2
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/unit/dispatcher/test_executor_audit.py tests/unit/dispatcher/test_read_provenance_honest.py -q` → PASS（4）
- [ ] **Step 5: mypy + ruff**
`uv run mypy src/shenbi/dispatcher/executor.py && uv run ruff check src/shenbi/dispatcher/executor.py` → Success / All passed
- [ ] **Step 6: Commit**
```bash
git add src/shenbi/dispatcher/executor.py \
        tests/unit/dispatcher/test_executor_audit.py \
        tests/unit/dispatcher/test_read_provenance_honest.py
git commit -m "feat(dispatcher): add dispatch_with_write_audit + read-provenance honest layering"
```

---

### Task 9:
**C2 follow-up (audit/__init__ final assembly):** By Task 9, `record.py` (Task 7) and `write_audit.py` (Task 6) now exist. Update `src/shenbi/audit/__init__.py` to export all:

```python
# src/shenbi/audit/__init__.py (final, after Tasks 6-7 land)
from shenbi.audit.record import record_audit_outcome
from shenbi.audit.snapshot import compute_file_change, parametric_globs, snapshot_tree
from shenbi.audit.write_audit import AuditResult, audit_writes

__all__ = [
    "AuditResult", "audit_writes", "compute_file_change",
    "parametric_globs", "record_audit_outcome", "snapshot_tree",
]
```

(original Task 9 content below)
 公共 API 导出 + 全量回归 + spec 判据对齐确认

**Files:** Modify `src/shenbi/contracts/__init__.py`（导出 ownership）

- [ ] **Step 1: 导出 ownership 公共 API**

在 `src/shenbi/contracts/__init__.py` 末尾追加（不动现有导出）：

```python
from shenbi.contracts.ownership import (
    OWNERSHIP,
    FileChange,
    FileOwnership,
    check_write_ownership,
    get_ownership,
)
```
执行者先 `sed -n '1,40p' src/shenbi/contracts/__init__.py` 确认 `__all__` 是否存在；若存在，把上述 6 个名字加入 `__all__`（按现有风格）；若无 `__all__`，则仅追加 import（导出靠 import 即可）。

- [ ] **Step 2: 验证导入**
`uv run python -c "from shenbi.contracts import OWNERSHIP, check_write_ownership, FileChange; from shenbi.audit import audit_writes, AuditResult, record_audit_outcome; from shenbi.records import parse_records, is_idempotent; print(len(OWNERSHIP))"` → 打印 `6`
- [ ] **Step 3: 全量回归（覆盖率门在此生效）**
`uv run pytest -q` → 现有测试集全部 passed（不引用具体数字，避免漂移）+ 新增 records/ownership/audit/dispatcher 测试全 passed，无 regression。执行者以实际输出为准，只断言「无失败」。
`uv run mypy src/shenbi && uv run ruff check .` → Success / All passed
- [ ] **Step 4: spec 判据对齐（本支柱范围）**
  - 判据 12（record parser 正确性）：语义 round-trip（Task 1）+ golden-parse 回归（Task 2）+ cross-section drift 检测（Task 3）✓
  - 判据 13（OWNERSHIP 字段 fixture 核对）：genre-config 9 键 + pending_hooks 16 记录键（Task 4，附「fixture 核对」节）✓；markdown truth 键集经 record parser 解析（Task 1）✓
  - 判据 14（读 provenance 诚实分层）：internal 可行 / codex 子进程已知盲点（诚实分层声明 + Task 8 测试锚定）✓
  - N1 粒度表：JSON=field / markdown truth=record / chapter·report=file（Task 5/6）✓
  - **范围外**：完整 69 技能 OWNERSHIP 迁移（支柱一续）、Tier A trace 落地后的 GATE_FAIL→trace.jsonl 接线（seam 已预留）、subprocess read-provenance（FUSE/ptrace，future work）、AST lint（支柱六）。
- [ ] **Step 5: Empty marker commit**
```bash
git add src/shenbi/contracts/__init__.py
git commit -m "feat(contracts): re-export ownership public API"
git commit --allow-empty -m "chore(audit): pillar 4 Tier B (skill write-ownership audit) complete"
```

---

## Self-Review

**1. Spec coverage（Tier B 范围）：** 判据 12 三件套（语义 round-trip Task 1、golden-parse Task 2、cross-section drift Task 3）全覆盖；判据 13（OWNERSHIP 字段 fixture 核对，JSON + markdown truth）Task 4 + 「fixture 核对」节覆盖；判据 14（读 provenance 诚实分层）诚实分层声明 + Task 8 锚定；N1 粒度表 Task 5/6 覆盖；写侧真实拓扑（pre/post 快照 diff）Task 5/8。**范围外（明确声明）：** 完整 69 技能 OWNERSHIP 迁移（支柱一续）、Tier A trace 落地后接线（seam 预留）、subprocess read-provenance（future work）、AST lint（支柱六）、值正确性（New-H）、per-record 粒度（New-H）。

**2. Placeholder scan：** 无 TBD/TODO；每个 code step 含完整可运行代码；命令精确；golden 基线由 parser 实际生成（非手写）。

**3. Type consistency：** `FileChange`（Task 4 定义）在 Task 5（snapshot 产出）/Task 4（ownership 消费）签名一致；`AuditResult`（Task 6 定义）在 Task 7/8 一致；`check_write_ownership(skill, FileChange)` 跨 Task 4/6 一致；`parse_records`/`parse_markdown_table`/`detect_cross_section_drift` 跨 Task 1/3/5/6 一致；`snapshot_tree(root, watch_patterns)` 跨 Task 5/6/8 一致。

**4. 诚实边界（不 overclaim）：** (a) 这是检测非预防；(b) 记录级为 per-skill-per-file，值正确性不在范围；(c) 读 provenance 仅 internal，codex 子进程是已知盲点（Task 8 测试锚定）；(d) 审计写入面=技能声明 writes/updates，越权写文件外的写不在检测范围；(e) Tier A 未落地 → 账本自包含 + trace seam（不假装已接入 trace.jsonl）。

**5. 已知风险（诚实登记）：** detect 模型要求 skills 双写 YAML+表保持一致——迁移期 drift 检测可能噪音失败，由判据 8 全迁移门吸收（spec 风险表）；genre-config「恰好 8」与 plant 漏 notes 为 inherited drift，OWNERSHIP 以 fixture 为准（spec M3/M4）。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-contract-single-source-pillar4-tierB.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
