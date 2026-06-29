# 契约单源架构 - 支柱一（契约骨架）实施计划 v2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 立起 `src/shenbi/contracts/` Pydantic 契约层骨架（enums + REGISTRY 自动发现 + bootstrap + PureInput/GateOutcome + 迁移 foreshadowing_resolve 验证全管线），为后续支柱与 69 技能迁移打地基。

**Architecture:** 新建 `src/shenbi/contracts/`；保留 `contract.py`（TypedDict）过渡；foreshadowing_resolve 先导迁移。不触碰 gates/dispatcher/helpers。

**Tech Stack:** Python 3.11+，Pydantic v2.5+（已依赖），mypy strict（已 CI），pytest+hypothesis（已依赖），pathlib+json。

**关联 spec:** [../specs/2026-06-29-contract-single-source-design.md](../specs/2026-06-29-contract-single-source-design.md) v5.2（9/10）。

**v2 修订（round-1 审核 6→目标 9+）：** C1 truth-files.yaml 真实结构是 `concepts/globs/patterns`（非 `files`）；C2 Task 7 迭代层级错；C3 Task 3↔4 顺序（registry import skills 包，须先建包）；C4 `dict[str,type]` mypy strict 拒（Literal 非 type）；I1 GateResult 与 status.GateResult 碰撞→改名 GateOutcome；I2 测试数 1313 非 1231；I3 pre-commit 条件性 TODO→给精确 YAML + `uv run python`；I4 测试相对路径→用 repo 绝对路径。

## Global Constraints

- Python 3.11+；pathlib + json；框架代码无 print()（用 structlog）。
- Pydantic v2.5+；含 @computed_field 的模型用 `model_config={"extra":"ignore"}`（N7）。
- mypy strict + ruff 必须 CI 干净。
- 契约字段集以 `tests/fixtures/` 为准（非 round 输出）。
- 不改运行态（本计划只新增 contracts/）。
- contract.py 本计划结束**保留**；删除是后续「完全迁移」计划。

---

### Task 1: 契约包骨架 + enums.py

**Files:** Create `src/shenbi/contracts/__init__.py`（占位 Task 6 填）、`src/shenbi/contracts/enums.py`、`tests/unit/contracts/__init__.py`、`tests/unit/contracts/test_enums.py`

**Interfaces:** Produces `Severity/Verdict/CPZone/ActorRole` Literal + `ALL_ENUMS: dict[str, object]`（v2: object 非 type，避 mypy strict 拒）。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/__init__.py
"""契约层测试包。"""
```

```python
# tests/unit/contracts/test_enums.py
from __future__ import annotations
from typing import get_args
from shenbi.contracts.enums import ALL_ENUMS, ActorRole, CPZone, Severity, Verdict

def test_severity_members() -> None:
    assert set(get_args(Severity)) == {"BLOCKING","CRITICAL","MINOR"}
def test_verdict_members() -> None:
    assert set(get_args(Verdict)) == {"通过","有瑕疵","不通过"}
def test_cpzone_members() -> None:
    assert set(get_args(CPZone)) == {"GREEN","ORANGE","RED"}
def test_actor_role_members() -> None:
    assert set(get_args(ActorRole)) == {"GENERATOR","SCORER","GATE","SKILL","HUMAN"}
def test_all_enums_complete() -> None:
    assert set(ALL_ENUMS.keys()) == {"Severity","Verdict","CPZone","ActorRole"}
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/contracts/test_enums.py -v` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/contracts/__init__.py
"""契约单源层（spec 支柱一）。单一真理之源：技能输出 schema、算法不变量、
跨技能关系以 Pydantic 模型声明。门/helpers/文档从此派生。"""

# src/shenbi/contracts/enums.py
"""全框架单一词表（收严重性词汇分裂）。所有 Literal 必须从此处 import。"""
from __future__ import annotations
from typing import Any, Literal

Severity = Literal["BLOCKING","CRITICAL","MINOR"]
Verdict = Literal["通过","有瑕疵","不通过"]
CPZone = Literal["GREEN","ORANGE","RED"]
ActorRole = Literal["GENERATOR","SCORER","GATE","SKILL","HUMAN"]

# v2 C4: object 非 type——Literal 是 _LiteralGenericAlias 不是 type，mypy strict 拒 dict[str,type]
ALL_ENUMS: dict[str, Any] = {
    "Severity": Severity, "Verdict": Verdict, "CPZone": CPZone, "ActorRole": ActorRole,
}
```

- [ ] **Step 4: Run → passes** (5)
- [ ] **Step 5: mypy + ruff**
`uv run mypy src/shenbi/contracts/enums.py` → Success（v2 用 Any 通过）
`uv run ruff check src/shenbi/contracts/` → All passed
- [ ] **Step 6: Commit**
```bash
git add src/shenbi/contracts/__init__.py src/shenbi/contracts/enums.py \
        tests/unit/contracts/__init__.py tests/unit/contracts/test_enums.py
git commit -m "feat(contracts): add enums.py single-vocabulary"
```

---

### Task 2: base.py — PureInput + GateOutcome（v2 改名避 status.GateResult 碰撞）

**Files:** Create `src/shenbi/contracts/base.py`、`tests/unit/contracts/test_base.py`

**Interfaces:** Produces `PureInput`(frozen: skill/round_dir/raw_outputs:dict[str,str])、`GateOutcome`(frozen: skill/status/issues/checks + passed()/fail() 工厂)。

**v2 I1: 改名 GateResult→GateOutcome**。现有 `shenbi.status.GateResult` 是 TypedDict（gate/status/timestamp/checks/blocked_action/must_fix），被 gates/shared.py 消费。契约层用不同 shape，同名会制造「两个 GateResult」混淆。GateOutcome 是新名，后续门改造（支柱二）再统一迁移 status.GateResult→GateOutcome。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/test_base.py
from __future__ import annotations
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest
from shenbi.contracts.base import GateOutcome, PureInput

def test_pure_input_frozen() -> None:
    pi = PureInput(skill="x", round_dir=Path("/tmp"), raw_outputs={"a.md":"..."})
    with pytest.raises(FrozenInstanceError): pi.skill = "y"  # type: ignore[misc]
def test_gate_outcome_frozen() -> None:
    gr = GateOutcome(skill="x", status="PASS", issues=(), checks=())
    with pytest.raises(FrozenInstanceError): gr.status = "FAIL"  # type: ignore[misc]
def test_gate_outcome_factories() -> None:
    assert GateOutcome.passed("x").status == "PASS"
    f = GateOutcome.fail("x", ["e1","e2"])
    assert f.status == "FAIL" and f.issues == ("e1","e2")
```

- [ ] **Step 2: Run → fails**
- [ ] **Step 3: Implement**

```python
# src/shenbi/contracts/base.py
"""契约层不可变基类型。PureInput 只含已读入内存数据，无 Path 写能力。
GateOutcome 是纯数据，门返回它而非修改文件系统。

v2: 命名为 GateOutcome 而非 GateResult，避与 shenbi.status.GateResult(TypedDict) 碰撞。
后续支柱二门改造时统一迁移 status.GateResult→GateOutcome。"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

@dataclass(frozen=True)
class PureInput:
    skill: str
    round_dir: Path
    raw_outputs: dict[str,str]

@dataclass(frozen=True)
class GateOutcome:
    skill: str
    status: Literal["PASS","FAIL","SKIP","WARN"]
    issues: tuple[str,...] = ()
    checks: tuple[dict[str,object],...] = ()
    @classmethod
    def passed(cls, skill: str) -> "GateOutcome":
        return cls(skill=skill, status="PASS")
    @classmethod
    def fail(cls, skill: str, issues: list[str]) -> "GateOutcome":
        return cls(skill=skill, status="FAIL", issues=tuple(issues))
```

- [ ] **Step 4: Run → passes** (3)
- [ ] **Step 5: mypy+ruff+commit**
```bash
git add src/shenbi/contracts/base.py tests/unit/contracts/test_base.py
git commit -m "feat(contracts): add PureInput + GateOutcome frozen base types"
```

---

### Task 3: contracts/skills/ 子包占位（v2 从 Task 4 提前，解 C3 顺序）

**v2 C3: 原 Task 4 提前为 Task 3。** registry.py 的 `_discover_skill_models` 在 import 时 `from shenbi.contracts import skills`——若 skills/ 包不存在，import 崩溃。必须先建包。

**Files:** Create `src/shenbi/contracts/skills/__init__.py`

- [ ] **Step 1: Create**
```python
# src/shenbi/contracts/skills/__init__.py
"""已迁移技能的 Pydantic 模型。每个 <name>.py 导出 Report(BaseModel)。
自动被 contracts.registry._discover_skill_models 收集进 REGISTRY。"""
```
- [ ] **Step 2: Verify package importable**
`uv run python -c "from shenbi.contracts import skills; print(skills.__path__)"` → prints path
- [ ] **Step 3: Commit**
```bash
git add src/shenbi/contracts/skills/__init__.py
git commit -m "feat(contracts): add skills/ subpackage (required before registry discovery)"
```

---

### Task 4: registry.py — 自动发现 + bootstrap（v2 C1: 读 concepts 非 files）

**Files:** Create `src/shenbi/contracts/registry.py`、`tests/unit/contracts/test_registry.py`

**Interfaces:** Consumes `shenbi.gates.shared.PROJECT`、`docs/framework/truth-files.yaml`（真实结构：`concepts:[{name,kind}]`/`globs`/`patterns`）。Produces `REGISTRY: dict[str,type[BaseModel]]`、`bootstrap_registry() -> dict[str,str]`、`load_skill_contract(skill) -> type[BaseModel]|None`。

**v2 C1 关键修正：** truth-files.yaml 真实顶层键是 `concepts`（非 `files`），每条是 `{name, kind}`（非 `{path, kind}`）。亲手核对：`python3 -c "import yaml; print(yaml.safe_load(open('docs/framework/truth-files.yaml'))['concepts'][:2])"` → `[{'name':'novel.json','kind':'config'}, ...]`。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/test_registry.py
from __future__ import annotations
from shenbi.contracts.registry import REGISTRY, bootstrap_registry, load_skill_contract

def test_registry_empty_before_migration() -> None:
    assert REGISTRY == {}  # Task 6 后改
def test_bootstrap_returns_vocab() -> None:
    reg = bootstrap_registry()
    assert isinstance(reg, dict) and len(reg) > 0
    # 真实 concepts 含 truth/pending_hooks.md
    assert any("pending_hooks" in k for k in reg)
def test_load_unmigrated_returns_none() -> None:
    assert load_skill_contract("shenbi-worldbuilding") is None
def test_load_unknown_returns_none() -> None:
    assert load_skill_contract("shenbi-does-not-exist") is None
```

- [ ] **Step 2: Run → fails**

- [ ] **Step 3: Implement**

```python
# src/shenbi/contracts/registry.py
"""REGISTRY 自动发现 + 过渡期 truth-files.yaml bootstrap。C1 修复：单一注册表。

v2 C1: truth-files.yaml 真实结构是 concepts/globs/patterns（非 files），
每条 concept 是 {name, kind}。bootstrap 读 concepts。"""
from __future__ import annotations
import importlib
import pkgutil

import yaml
from pydantic import BaseModel

from shenbi.gates.shared import PROJECT

_TRUTH_FILES_YAML = PROJECT / "docs" / "framework" / "truth-files.yaml"

def bootstrap_registry() -> dict[str,str]:
    """从 truth-files.yaml 的 concepts 读全部文件词汇（未迁移技能用）。

    v2 C1: 真实结构 concepts:[{name,kind}]，非 files:[{path,kind}]。
    返回 {name: kind}。"""
    if not _TRUTH_FILES_YAML.exists():
        return {}
    data = yaml.safe_load(_TRUTH_FILES_YAML.read_text(encoding="utf-8")) or {}
    out: dict[str,str] = {}
    for entry in data.get("concepts", []):  # v2: concepts 非 files
        name = entry.get("name")  # v2: name 非 path
        if name:
            out[name] = entry.get("kind", "truth")
    return out

def _discover_skill_models() -> dict[str,type[BaseModel]]:
    """自动发现 contracts/skills/*.py 导出的 Report 类。约定：每模块有 Report(BaseModel)。"""
    from shenbi.contracts import skills as skills_pkg  # Task 3 已建包
    out: dict[str,type[BaseModel]] = {}
    for mod_info in pkgutil.iter_modules(skills_pkg.__path__):
        if mod_info.ispkg or mod_info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"shenbi.contracts.skills.{mod_info.name}")
        report_cls = getattr(mod, "Report", None)
        if isinstance(report_cls, type) and issubclass(report_cls, BaseModel):
            out[f"shenbi-{mod_info.name.replace('_','-')}"] = report_cls
    return out

REGISTRY: dict[str,type[BaseModel]] = _discover_skill_models()

def load_skill_contract(skill: str) -> type[BaseModel] | None:
    return REGISTRY.get(skill)
```

- [ ] **Step 4: Run → passes** (4)
- [ ] **Step 5: mypy+ruff+commit**
```bash
git add src/shenbi/contracts/registry.py tests/unit/contracts/test_registry.py
git commit -m "feat(contracts): add REGISTRY auto-discovery + truth-files.yaml bootstrap"
```

---

---

### Task 5: foreshadowing_resolve 契约模型（先导迁移，根治 CP 算术 bug）

**Files:** Create `src/shenbi/contracts/skills/foreshadowing_resolve.py`、`tests/unit/contracts/test_foreshadowing_resolve_contract.py`；Modify `tests/unit/contracts/test_registry.py`（REGISTRY 不再空）

**Interfaces:** Consumes `shenbi.contracts.enums.CPZone`、pydantic。Produces `CP_THRESHOLDS`、`HookCP`(含 `@computed_field zone`、`@computed_field must_resolve_next_chapter`)、`Report`(两 `@model_validator`)。REGISTRY 自动收录。

spec 展示案例：CP 算术三 bug（CP=80 标 RED、同 hook 三 CP、>200 vs ≥100）在此根治。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/test_foreshadowing_resolve_contract.py
from __future__ import annotations
import pytest
from pydantic import ValidationError
from shenbi.contracts.skills.foreshadowing_resolve import CP_THRESHOLDS, HookCP, Report
from shenbi.contracts.registry import REGISTRY

def test_cp_thresholds_constants() -> None:
    assert CP_THRESHOLDS == {"GREEN_MAX":50, "RED_NOW":100, "FORCE_NEXT_CHAPTER":200}
def test_zone_computed_from_cp() -> None:
    assert HookCP(hook_id="h", cp=80, last_reinforced=1, current_chapter=10).zone == "ORANGE"
    assert HookCP(hook_id="h", cp=100, last_reinforced=1, current_chapter=10).zone == "RED"
    assert HookCP(hook_id="h", cp=49, last_reinforced=1, current_chapter=10).zone == "GREEN"
def test_zone_ignores_hand_filled() -> None:
    """N7 + Bug 1：手填 zone=RED 被 extra=ignore 忽略，重算。"""
    h = HookCP.model_validate({"hook_id":"h","cp":80,"zone":"RED","last_reinforced":1,"current_chapter":1})
    assert h.zone == "ORANGE"
def test_report_rejects_inconsistent_debt() -> None:
    with pytest.raises(ValidationError):
        Report(current_chapter=10, hooks=[HookCP(hook_id="h",cp=100,last_reinforced=1,current_chapter=10)], debt_level="GREEN")
def test_report_rejects_dup_hook_three_cp() -> None:
    """v2 M3: 用三个 cp 值（80/45/180）忠于 spec「三 CP」。"""
    with pytest.raises(ValidationError):
        Report(current_chapter=10, hooks=[
            HookCP(hook_id="h1",cp=80,last_reinforced=1,current_chapter=10),
            HookCP(hook_id="h1",cp=45,last_reinforced=1,current_chapter=10),
            HookCP(hook_id="h1",cp=180,last_reinforced=1,current_chapter=10),
        ], debt_level="RED")
def test_report_accepts_valid() -> None:
    r = Report(current_chapter=10, hooks=[HookCP(hook_id="h1",cp=80,last_reinforced=1,current_chapter=10)], debt_level="ORANGE")
    assert r.debt_level == "ORANGE"
def test_must_resolve_threshold() -> None:
    assert HookCP(hook_id="h",cp=201,last_reinforced=1,current_chapter=10).must_resolve_next_chapter is True
    assert HookCP(hook_id="h",cp=200,last_reinforced=1,current_chapter=10).must_resolve_next_chapter is False
def test_must_resolve_serialized() -> None:
    """v2 M1: must_resolve 用 computed_field 才进 model_dump（支柱六文档派生需要）。"""
    h = HookCP(hook_id="h",cp=201,last_reinforced=1,current_chapter=10)
    assert h.model_dump()["must_resolve_next_chapter"] is True
def test_registry_includes_resolve() -> None:
    assert REGISTRY["shenbi-foreshadowing-resolve"] is Report
```

- [ ] **Step 2: Run → fails** (ModuleNotFoundError)

- [ ] **Step 3: Implement**

```python
# src/shenbi/contracts/skills/foreshadowing_resolve.py
"""foreshadowing_resolve 契约模型。spec 展示案例：根治 CP 算术三 bug。
zone/must_resolve 是 computed_field 只读派生；debt 一致性 + hook 单 cp 是
model_validator 运行时校验。字段以 fixture 为准（state 非 status）。

v2 M1: must_resolve_next_chapter 用 computed_field（非 @property）以进 model_dump。"""
from __future__ import annotations
from pydantic import BaseModel, Field, computed_field, model_validator
from shenbi.contracts.enums import CPZone

CP_THRESHOLDS: dict[str,int] = {"GREEN_MAX":50, "RED_NOW":100, "FORCE_NEXT_CHAPTER":200}

class HookCP(BaseModel):
    model_config = {"extra": "ignore"}  # N7
    hook_id: str
    cp: int = Field(ge=0)
    last_reinforced: int = Field(ge=1)
    current_chapter: int = Field(ge=1)

    @computed_field
    @property
    def zone(self) -> CPZone:
        if self.cp >= CP_THRESHOLDS["RED_NOW"]: return "RED"
        if self.cp >= CP_THRESHOLDS["GREEN_MAX"]: return "ORANGE"
        return "GREEN"

    @computed_field  # v2 M1: computed_field 非 property，进 model_dump
    @property
    def must_resolve_next_chapter(self) -> bool:
        return self.cp > CP_THRESHOLDS["FORCE_NEXT_CHAPTER"]

class Report(BaseModel):
    model_config = {"extra": "ignore"}
    current_chapter: int = Field(ge=1)
    hooks: list[HookCP]
    debt_level: CPZone

    @model_validator(mode="after")
    def _debt_consistent_with_hooks(self) -> "Report":
        max_cp = max((h.cp for h in self.hooks), default=0)
        expected: CPZone = (
            "RED" if max_cp >= CP_THRESHOLDS["RED_NOW"]
            else "ORANGE" if max_cp >= CP_THRESHOLDS["GREEN_MAX"] else "GREEN"
        )
        if self.debt_level != expected:
            raise ValueError(f"debt_level={self.debt_level} 与 max cp={max_cp} zone={expected} 矛盾")
        return self

    @model_validator(mode="after")
    def _hook_cp_single_value(self) -> "Report":
        seen: dict[str,int] = {}
        for h in self.hooks:
            if h.hook_id in seen and seen[h.hook_id] != h.cp:
                raise ValueError(f"hook {h.hook_id} 多个 cp: {seen[h.hook_id]} vs {h.cp}")
            seen[h.hook_id] = h.cp
        return self
```

- [ ] **Step 4: Update registry test (REGISTRY no longer empty)**
Replace `test_registry_empty_before_migration` with:
```python
def test_registry_includes_migrated() -> None:
    from shenbi.contracts.skills.foreshadowing_resolve import Report
    assert REGISTRY["shenbi-foreshadowing-resolve"] is Report
def test_registry_excludes_unmigrated() -> None:
    assert "shenbi-worldbuilding" not in REGISTRY
```

- [ ] **Step 5: Run all contract tests** → PASS
- [ ] **Step 6: mypy+ruff+commit**
```bash
git add src/shenbi/contracts/skills/foreshadowing_resolve.py \
        tests/unit/contracts/test_foreshadowing_resolve_contract.py \
        tests/unit/contracts/test_registry.py
git commit -m "feat(contracts): migrate foreshadowing_resolve, eradicating CP arithmetic bugs"
```

---

### Task 6: contracts/__init__.py 导出

**Files:** Modify `src/shenbi/contracts/__init__.py`

- [ ] **Step 1: Update**
```python
# src/shenbi/contracts/__init__.py
"""契约单源层（spec 支柱一）。过渡期 contract.py 从本包派生 REGISTRY。"""
from __future__ import annotations
from shenbi.contracts.base import GateOutcome, PureInput
from shenbi.contracts.enums import ALL_ENUMS, ActorRole, CPZone, Severity, Verdict
from shenbi.contracts.registry import REGISTRY, bootstrap_registry, load_skill_contract

__all__ = [
    "REGISTRY", "bootstrap_registry", "load_skill_contract",
    "PureInput", "GateOutcome",
    "Severity", "Verdict", "CPZone", "ActorRole", "ALL_ENUMS",
]
```
- [ ] **Step 2: Verify imports**
`uv run python -c "from shenbi.contracts import REGISTRY, load_skill_contract, PureInput, GateOutcome, Severity; print(len(REGISTRY))"` → prints `1`
- [ ] **Step 3: Full contract suite + lint** → PASS/All passed
- [ ] **Step 4: Commit**
```bash
git add src/shenbi/contracts/__init__.py
git commit -m "feat(contracts): re-export public API from __init__"
```

---

### Task 7: contract.py 过渡回归测试（v2 C2: 迭代 concepts 非 top-level keys）

**Files:** Modify `tests/unit/test_contract.py`（加回归测试，不改 contract.py）

**v2 C2 关键修正：** `load_registry()` 返回 `{"concepts":[...], "patterns":[...], "globs":[...]}`（顶层三键）。原计划 `for k in reg` 迭代顶层键名（"concepts"等），不含 "pending_hooks"。修正为迭代 `reg["concepts"]` 的 name 字段。

- [ ] **Step 1: Read current load_registry**
`sed -n '70,82p' src/shenbi/contract.py` — 确认返回原始 dict（含 concepts/patterns/globs）。

- [ ] **Step 2: Write regression test**
```python
# 追加到 tests/unit/test_contract.py
def test_load_registry_still_returns_truth_files_vocab() -> None:
    """过渡期：load_registry 仍含 truth-files.yaml 全部 concepts。
    v2 C2: 迭代 reg['concepts'] 的 name，非顶层键。"""
    from shenbi.contract import load_registry
    reg = load_registry()
    assert isinstance(reg, dict)
    concepts = reg.get("concepts", [])
    assert any("pending_hooks" in c.get("name", "") for c in concepts)

def test_contracts_registry_coexists_with_contract_py() -> None:
    """两源并行：contract.py（未迁移）+ contracts.REGISTRY（已迁移 foreshadowing-resolve）。"""
    from shenbi.contracts import REGISTRY
    assert "shenbi-foreshadowing-resolve" in REGISTRY
    from shenbi.contract import load_contract
    c = load_contract("shenbi-worldbuilding")  # 未迁移，走 TypedDict
    assert c is not None
```
- [ ] **Step 3: Run → PASS (contract.py unchanged)**
- [ ] **Step 4: Commit**
```bash
git add tests/unit/test_contract.py
git commit -m "test(contract): regression tests for transition-period two-source coexistence"
```

---

### Task 8: N7 lint — 禁 extra=forbid 于 computed_field 模型（v2 I3/I4 修正）

**Files:** Create `tools/lint_no_forbid_with_computed_field.py`、`tests/unit/test_lint_no_forbid_with_computed_field.py`

**v2 I3:** 给精确 pre-commit YAML + CI 用 `uv run python`（非 bare `python`）。
**v2 I4:** 测试用 `repo` 绝对路径（非相对 `tools/...`）。

- [ ] **Step 1: Write failing test**
```python
# tests/unit/test_lint_no_forbid_with_computed_field.py
from __future__ import annotations
import subprocess, sys
from pathlib import Path

def test_lint_passes_on_current_contracts() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = str(repo / "tools" / "lint_no_forbid_with_computed_field.py")  # v2 I4: 绝对路径
    target = str(repo / "src" / "shenbi" / "contracts")
    r = subprocess.run([sys.executable, script, target], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_lint_catches_forbid_violation(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    script = str(repo / "tools" / "lint_no_forbid_with_computed_field.py")  # v2 I4
    bad = tmp_path / "bad.py"
    bad.write_text(
        "from pydantic import BaseModel, computed_field\n"
        "class M(BaseModel):\n"
        "    model_config = {'extra': 'forbid'}\n"
        "    x: int\n"
        "    @computed_field\n"
        "    @property\n"
        "    def y(self) -> int: return self.x\n",
        encoding="utf-8")
    r = subprocess.run([sys.executable, script, str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 1 and "forbid" in r.stderr.lower()
```

- [ ] **Step 2: Run → fails** (script missing)

- [ ] **Step 3: Write lint script**
```python
# tools/lint_no_forbid_with_computed_field.py
#!/usr/bin/env python3
"""N7 守护：含 @computed_field 的 Pydantic 模型不能 extra=forbid。
用法: python tools/lint_no_forbid_with_computed_field.py <path>
exit 0=通过；exit 1=违规。"""
from __future__ import annotations
import ast, sys
from pathlib import Path

def _has_computed_field(class_body: list) -> bool:
    for item in class_body:
        if isinstance(item, ast.FunctionDef):
            for dec in item.decorator_list:
                if "computed_field" in ast.unparse(dec): return True
    return False

def _has_forbid_config(class_body: list) -> bool:
    for item in class_body:
        if isinstance(item, ast.Assign):
            for t in item.targets:
                if isinstance(t, ast.Name) and t.id == "model_config":
                    if "forbid" in ast.unparse(item.value): return True
        if isinstance(item, ast.AnnAssign):
            if isinstance(item.target, ast.Name) and item.target.id == "model_config" and item.value:
                if "forbid" in ast.unparse(item.value): return True
    return False

def lint_dir(root: Path) -> list[str]:
    violations: list[str] = []
    for py in root.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if _has_computed_field(node.body) and _has_forbid_config(node.body):
                    violations.append(f"{py}:{node.lineno}: {node.name} 含 computed_field 却设 extra=forbid (N7)")
    return violations

def main() -> int:
    if len(sys.argv) != 2:
        print("usage: lint_no_forbid_with_computed_field.py <path>", file=sys.stderr); return 2
    vs = lint_dir(Path(sys.argv[1]))
    for v in vs: print(v, file=sys.stderr)
    return 1 if vs else 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests → PASS (2)**

- [ ] **Step 5: Hook into CI + pre-commit（v2 I3: 精确 YAML + uv run python）**

先读现有格式：`grep -A5 "lint.contracts\|id: lint" .pre-commit-config.yaml | head -30` 与 `grep -B2 -A4 "lint_contracts" .github/workflows/ci.yml`。

CI（`.github/workflows/ci.yml`，参考现有 lint_contracts 步骤，用 `uv run python`）：
```yaml
      - name: N7 lint (no forbid on computed_field)
        run: uv run python tools/lint_no_forbid_with_computed_field.py src/shenbi/contracts
```

pre-commit（`.pre-commit-config.yaml`，参考现有 local hook 格式）：
```yaml
  - id: lint-no-forbid-with-computed-field
    name: N7 forbid-on-computed_field guard
    entry: uv run python tools/lint_no_forbid_with_computed_field.py src/shenbi/contracts
    language: system
    pass_filenames: false
    files: ^src/shenbi/contracts/.*\.py$
```
（实现者：按 `.pre-commit-config.yaml` 实际 repo/rev 与 local hook 段落格式调整缩进与位置；若现有 hook 全是 remote repo，加 `- repo: local` 段。）

- [ ] **Step 6: mypy+ruff+commit**
```bash
git add tools/lint_no_forbid_with_computed_field.py \
        tests/unit/test_lint_no_forbid_with_computed_field.py \
        .github/workflows/ci.yml .pre-commit-config.yaml
git commit -m "feat(lint): add N7 guard — no extra=forbid on @computed_field models"
```

---

### Task 9: 全量回归 + 支柱一骨架完成确认（v2 I2: 测试数 1313）

**Files:** 无。仅验证。

- [ ] **Step 1: Full test suite**
`uv run pytest -q` → v2 I2: 现有 1313 passed（非 1231）+ 新增 ~17 contract tests，无 regression
- [ ] **Step 2: Type check + lint whole repo**
`uv run mypy src/shenbi && uv run ruff check .` → Success/All passed
- [ ] **Step 3: Verify spec 判据对齐（本支柱范围）**
  - 判据 9（computed_field round-trip extra=ignore + lint 禁 forbid）：Task 5 + 8 ✓
  - 单一阈值真理（CP_THRESHOLDS）：Task 5 ✓
  - C1 过渡（两源并存不破坏）：Task 7 ✓
  - **范围外**：OWNERSHIP 矩阵、lifecycle 状态机、69 技能迁移、门改造、CJK、trace、属性测试网、文档派生。
- [ ] **Step 4: Empty marker commit**
```bash
git commit --allow-empty -m "chore(contracts): pillar 1 skeleton complete"
```

---

## 后续计划（本计划之外，各自独立可执行）

- **支柱一续**：OWNERSHIP 矩阵 + lifecycle 状态机 + 69 技能迁移。依赖本计划 REGISTRY。
- **支柱二**：门改造（阈值派生 + parser + G3.4/G5/G6/G7 + derive_file_type）。依赖支柱一续。
- **支柱三**：CJK 工具包（cjk.py + jieba + 属性测试）。独立可并行。
- **支柱四**：事件溯源 + Tier A/B。依赖支柱一续 + 二。
- **支柱五**：属性测试网。
- **支柱六**：文档派生。

## Self-Review（v2）

**1. Spec coverage（本骨架范围）**：enums/REGISTRY/base/先导迁移/N7/C1 过渡全覆盖。OWNERSHIP/lifecycle/69 技能/门/CJK/trace/属性测试/文档派生明确留给后续。

**2. Placeholder scan**：v2 已消除 Task 8 的条件性 TODO（给精确 YAML）；无 TBD。

**3. Type consistency**：v2 C4 `ALL_ENUMS: dict[str, Any]`；`Report`=spec ResolveReport；`HookCP.zone/must_resolve -> CPZone/bool`；`GateOutcome`（v2 I1 改名）；`REGISTRY: dict[str,type[BaseModel]]`。一致。

**4. 已知限制**：Task 4（registry）import 时执行 `_discover_skill_models`，依赖 Task 3 已建 skills/ 包（v2 C3 修正顺序）；Task 7 不改 contract.py（bootstrap 等价，有意不改运行态）；Task 8 pre-commit 接入按现有 `.pre-commit-config.yaml` 格式调整（实现者先读现有格式）。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-contract-single-source-pillar1.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
