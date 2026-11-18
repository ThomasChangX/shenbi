# Spec #93 阈值权威化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对账 lint 读执法器常量真执法（strict 进 just lint）、散文↔门裕度成文、pricing/executor 缓存/trend 列契约三处小型漂移清偿、疲劳词门-契约键形接线。

**Architecture:** 六个独立修复面共用「阈值权威单源」主题：常量提取→lint import→strict 翻转三段递进（门保护前序修复）；pricing 倒置（dispatch_helper 从 pricing import，方向已确立）；executor 派生集去冻结（委托 stat 键缓存的 bootstrap_registry）；TREND_COLUMNS 落 pipeline/_shared 叶（三消费者 import）；疲劳词门改读契约 camel 形状。全部离线可验，零 SKILL.md 散文改动。

**Tech Stack:** Python 3.11+ / pydantic contract models / pytest + hypothesis / just task runner / ruff+mypy 门禁。

## Global Constraints（spec 项目级约束逐字）

- 不改任何 SKILL.md 指令散文（T2 豁免：纯注释性 docs）；SKILL.md 改动属 prompt 变更，另立内容批
- T2 与 T6 同批合入或 T6 先行（禁 gates.md 先行描述未接线门语义）——本 plan 排序 Task 7 (T6) → Task 8 (T2)
- gate 检查器纯函数幂等（AGENTS.md）；`src/shenbi/` 无 `print()`（structlog，ruff T20 零豁免）
- 所有 commit 显式列文件路径，禁 `git add -A` / `git add .`
- 验收全部离线可复验（F947：零真实 LLM dispatch / 零手写 mock 冒充技能产物）
- G0.9：scenario 输入引用 `tests/fixtures/` 真实产物（genre-config-example.json 原样）；结构单测可 inline / tmp_path 构造
- deps.json 等生成物禁手改（改契约源头 + `just generate`）
- 常量命名对齐 gates/shared.py band 元组先例（`SCENE_INDEPENDENT_BAND` 式全大写下划线）

## Task ↔ Spec AC 覆盖表

| Spec AC | Task | 验证 |
|---|---|---|
| AC1 T1a 常量化行为零变化 | Task 1 | 现存 pacing 测试全绿+边界四测 |
| AC1 T1b 删 bounds 仍判越界+keyword 缺省 FAIL | Task 2 | tmp SKILL 注入 50% strict 红+keyword_missing strict 红 |
| AC1 T1c strict 进 just lint FAIL 态可触发 | Task 3 | 常量临时 (18,45) → just lint 红（回滚）+接线测试 |
| AC1 lint 测试重写 strict 语义全绿 | Task 2/3 | test_lint_threshold_reconciliation 重写 |
| AC2 gates.md 裕度节+g4 双向回指 | Task 8 | grep 双向锚 |
| AC3 T3 grep=0 | Task 4 | `grep -rn "dispatch_helper" src/shenbi/cost/` = 0 |
| AC3 T4 红测绿 | Task 5 | 同进程改 YAML 派生集刷新 |
| AC3 T5 三消费者 import+property | Task 6 | 往返 writer→bridge+SKILL 表头对账 |
| AC4 T6 红绿+无 snake 注入 | Task 7 | 眸光一凝×9 真 fixture 形状 |
| AC5 just check exit 0 | Task 8 末步+阶段 7 | 全量门禁 |

---

### Task 1: T1a · pacing 契约带宽常量提取（infra · characterization）

**Files:**
- Modify: `src/shenbi/contracts/skills/pacing_design.py:51-56`
- Test: `tests/unit/contracts/test_pacing_design_contract.py`（追加）

**Interfaces:**
- Consumes: 无（既有 `_constellation_range` validator）
- Produces: `CONSTELLATION_HARD_BAND: tuple[int, int] = (15, 40)`（模块级公共常量，Task 2 lint import 消费）

- [ ] **Step 1: 追加边界 characterization 测试**（当前无 [15,40] 边界测——现存测试只用带内 25）

```python
# tests/unit/contracts/test_pacing_design_contract.py 追加
from shenbi.contracts.skills.pacing_design import CONSTELLATION_HARD_BAND, PacingDesign


class TestConstellationHardBand:
    """Spec #93 T1a — 带宽常量提取后行为零变化（characterization）。"""

    def test_band_value(self) -> None:
        assert CONSTELLATION_HARD_BAND == (15, 40)

    def test_boundary_15_passes(self) -> None:
        PacingDesign(line_ratios={"QUEST": 45.0, "FIRE": 40.0, "CONSTELLATION": 15.0})

    def test_boundary_40_passes(self) -> None:
        PacingDesign(line_ratios={"QUEST": 25.0, "FIRE": 35.0, "CONSTELLATION": 40.0})

    def test_below_14_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match=r"outside \[15, 40\]"):
            PacingDesign(line_ratios={"QUEST": 46.0, "FIRE": 40.0, "CONSTELLATION": 14.0})

    def test_above_41_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match=r"outside \[15, 40\]"):
            PacingDesign(line_ratios={"QUEST": 25.0, "FIRE": 34.0, "CONSTELLATION": 41.0})
```

- [ ] **Step 2: 跑测试确认 import 红**

Run: `uv run pytest tests/unit/contracts/test_pacing_design_contract.py -k ConstellationHardBand -v`
Expected: FAIL with `ImportError: cannot import name 'CONSTELLATION_HARD_BAND'`

- [ ] **Step 3: 提取常量（validator 改用，行为零变化）**

```python
# src/shenbi/contracts/skills/pacing_design.py — model 类之前、import 之后插入：
#: CONSTELLATION hard-fail band, in percent (spec #93 T1a). Single source —
#: the reconciliation lint (tools/lint_threshold_reconciliation.py) imports
#: this instead of carrying a hand-copied third copy in the allowlist JSON.
CONSTELLATION_HARD_BAND: tuple[int, int] = (15, 40)


# _constellation_range validator 改用常量（docstring 的 [15, 40] 报文保持逐字不变）：
    @model_validator(mode="after")
    def _constellation_range(self) -> PacingDesign:
        const = self.line_ratios.get("CONSTELLATION")
        lo, hi = CONSTELLATION_HARD_BAND
        if const is not None and not lo <= const <= hi:
            raise ValueError(f"CONSTELLATION ratio {const} outside [{lo}, {hi}]")
        return self
```

注意：报文 f-string 从字面量 `[15, 40]` 改为 `[{lo}, {hi}]`——输出逐字节相同（`f"[{lo}, {hi}]"` == `"[15, 40]"` 当 lo=15/hi=40）。

- [ ] **Step 4: 跑新测+现存 pacing 全绿（行为零变化）**

Run: `uv run pytest tests/unit/contracts/test_pacing_design_contract.py tests/unit/gates/g4/test_pacing_design.py -v`
Expected: 全 PASS（含既有全部）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/skills/pacing_design.py tests/unit/contracts/test_pacing_design_contract.py
git commit -m "feat: spec #93 T1a — 提取 CONSTELLATION_HARD_BAND 常量（validator 改用，行为零变化）"
```

---

### Task 2: T1b · lint 读常量+删 bounds+包含式+keyword 必填+测试重写（leaf · tdd_red_green）

**Files:**
- Modify: `tools/lint_threshold_reconciliation.py`（全文语义改写）
- Modify: `tools/threshold_allowlist.json`（删 4 条 `bounds` 字段）
- Test: `tests/unit/tools/test_lint_threshold_reconciliation.py`（全文重写）

**Interfaces:**
- Consumes: `CONSTELLATION_HARD_BAND`（Task 1 产出；`from shenbi.contracts.skills.pacing_design import CONSTELLATION_HARD_BAND`——tools import src 先例 check_severity_vocab.py:18）
- Produces: `main(argv: list[str] | None = None) -> int`（语义变更：bounds 不再读自 allowlist；keyword 缺省产出 `keyword_missing` 行；判定式包含；**本 task 保持 WARN-only exit 0**，strict 在 Task 3）

- [ ] **Step 1: 重写测试（红：新语义未实现）**

```python
# tests/unit/tools/test_lint_threshold_reconciliation.py 全文替换
"""Spec #93 T1b/T1c — threshold reconciliation lint: constant-reading,
containment test, mandatory keyword, --strict FAIL mode."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LINT = REPO_ROOT / "tools" / "lint_threshold_reconciliation.py"


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(LINT), *argv], capture_output=True, text=True)


def _allowlist(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "allowlist.json"
    p.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return p


def _skill_md(tmp_path: Path, constellation: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(
        f"| 卷 | QUEST% | FIRE% | CONSTELLATION% | 检查结果 |\n"
        f"| 标准卷: QUEST 40 FIRE 30 CONSTELLATION {constellation} |\n",
        encoding="utf-8",
    )
    return p


def _entry(skill_md: Path, **overrides: object) -> dict:
    entry: dict = {
        "skill": "shenbi-pacing-design",
        "pattern": "标准卷: QUEST",
        "keyword": "CONSTELLATION",
        "file": str(skill_md),  # 绝对路径：REPO_ROOT / abs 保持原值
        "checker": "src/shenbi/contracts/skills/pacing_design.py",
    }
    entry.update(overrides)
    return entry


def test_repo_allowlist_strict_clean() -> None:
    r = _run(["--strict"])
    assert r.returncode == 0
    assert r.stdout == ""


def test_containment_rejects_partial_overlap(tmp_path: Path) -> None:
    # SKILL 写 10-20 与硬带 [15,40] 相交但不包含 —— 旧相交式放行，包含式必拒
    skill = _skill_md(tmp_path, "10-20%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)])), "--strict"])
    assert r.returncode == 1
    assert "threshold_drift" in r.stdout and "10-20" in r.stdout


def test_out_of_band_50_rejected(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "50-60%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)]))])
    assert r.returncode == 0  # 非 strict 仍 WARN-only
    assert "threshold_drift" in r.stdout and "50-60" in r.stdout


def test_in_band_contained_passes(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "15-25%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)])), "--strict"])
    assert r.returncode == 0
    assert r.stdout == ""


def test_missing_keyword_strict_fails(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "15-25%")
    entry = _entry(skill)
    del entry["keyword"]
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry]))])
    assert r.returncode == 0
    assert "keyword_missing" in r.stdout


def test_bounds_field_ignored(tmp_path: Path) -> None:
    # bounds 已从 schema 删除 —— 即便残留旧字段也不得参与判定（deletion test）
    skill = _skill_md(tmp_path, "50-60%")
    entry = _entry(skill, bounds=[0, 100])
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry]))])
    assert "threshold_drift" in r.stdout and "50-60" in r.stdout  # 常量带赢，残留 bounds 失效
```

Run: `uv run pytest tests/unit/tools/test_lint_threshold_reconciliation.py -v`
Expected: FAIL（containment/keyword/bounds 用例红——现实现相交式+keyword 可选+读 bounds）

- [ ] **Step 2: 改写 lint 实现**

```python
# tools/lint_threshold_reconciliation.py 语义改写要点（保留 file_missing/checker_missing/no_range_found 面）：
# 1) 顶部加 import（sys.path 不需处理——tools 由 REPO_ROOT 下 uv run 执行，src 布局经 just/uv 环境 import shenbi 已确立）：
from shenbi.contracts.skills.pacing_design import CONSTELLATION_HARD_BAND

# 2) docstring 更新：不再 "parsing checker constants is out of scope"；改为
#    "reads the checker's own hard band constant (CONSTELLATION_HARD_BAND);
#     containment test (SKILL range must sit inside the hard band); keyword
#     is mandatory (an entry without keyword validates the wrong column)."

# 3) _scan_entry 签名不变，内部：
#    - lo, hi = entry["bounds"]  →  lo, hi = CONSTELLATION_HARD_BAND
#    - keyword 缺省处理前移：
#        keyword = entry.get("keyword", "")
#        if not keyword:
#            return (f"WARN threshold_entry keyword_missing skill={entry['skill']} "
#                    f"file={entry['file']}")   # 必填化：缺省即漂移行
#      （原「keyword 在行中缺失」分支保留——那是行内漂移，同一标签）
#    - 判定式：
#        if not (d_lo >= lo and d_hi <= hi):
#            return (f"WARN threshold_drift skill={entry['skill']} "
#                    f"file={entry['file']} found={d_lo}-{d_hi} expected=[{lo}, {hi}]")

# 4) main() 保持 return 0（WARN-only；strict 在 Task 3 加）
```

- [ ] **Step 3: 删 allowlist bounds 字段**

```python
# tools/threshold_allowlist.json — 4 条 entry 各删一行 "bounds": [15, 40]
# （用 python 脚本改写保持 2 空格缩进 + 末尾换行；改后 git diff 应只有 4 行删除）
```

- [ ] **Step 4: 跑重写测试全绿**

Run: `uv run pytest tests/unit/tools/test_lint_threshold_reconciliation.py -v`
Expected: 6 PASS

- [ ] **Step 5: 实跑 lint 现状（repo 数据面）**

Run: `uv run python tools/lint_threshold_reconciliation.py; echo exit=$?`
Expected: 无输出，exit=0（四档带内+4/4 keyword）

- [ ] **Step 6: Commit**

```bash
git add tools/lint_threshold_reconciliation.py tools/threshold_allowlist.json tests/unit/tools/test_lint_threshold_reconciliation.py
git commit -m "feat: spec #93 T1b — lint 读 CONSTELLATION_HARD_BAND+删 bounds 第三源+判定式改包含+keyword 必填"
```

---

### Task 3: T1c · --strict 模式+just lint 接线（leaf · tdd_red_green）

**Files:**
- Modify: `tools/lint_threshold_reconciliation.py:80-103`（argparse+main）
- Modify: `justfile:53`（`--strict` 接线；:33 NOTE 注释同步移除）
- Test: `tests/unit/tools/test_lint_threshold_reconciliation.py`（追加 strict 用例）

**Interfaces:**
- Consumes: Task 2 产出（keyword_missing/drift 行+`main(argv) -> int`）
- Produces: `--strict` CLI flag（无 WARN 行 → exit 0；任一 WARN 条件 → exit 1）；justfile lint 配方含 `--strict`

- [ ] **Step 1: 追加 strict 测试（红）**

```python
# 追加到 tests/unit/tools/test_lint_threshold_reconciliation.py
def test_strict_drift_fails(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "50-60%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)])), "--strict"])
    assert r.returncode == 1
    assert "threshold_drift" in r.stdout


def test_strict_keyword_missing_fails(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "15-25%")
    entry = _entry(skill)
    del entry["keyword"]
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry])), "--strict"])
    assert r.returncode == 1
    assert "keyword_missing" in r.stdout


def test_non_strict_drift_still_exits_zero(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "50-60%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)]))])
    assert r.returncode == 0
    assert "threshold_drift" in r.stdout
```

Run: `uv run pytest tests/unit/tools/test_lint_threshold_reconciliation.py -k strict -v`
Expected: FAIL with `returncode 0 != 1`（--strict 未实现，argparse 报 unrecognized exit 2 或直接 exit 0）

- [ ] **Step 2: 实现 --strict**

```python
# tools/lint_threshold_reconciliation.py main() 改写：
def main(argv: list[str] | None = None) -> int:
    """Entry point: WARN-only by default; --strict exits 1 on any warn line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allowlist",
        default=str(DEFAULT_ALLOWLIST),
        help="path to the allowlist JSON (default: tools/threshold_allowlist.json)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any entry drifted (spec #93 T1c; wired into `just lint`)",
    )
    args = parser.parse_args(argv)

    allow_path = Path(args.allowlist)
    if not allow_path.is_file():
        print(f"WARN allowlist_missing path={allow_path}")
        return 1 if args.strict else 0
    entries = json.loads(allow_path.read_text(encoding="utf-8")).get("entries", [])
    warned = False
    for entry in entries:
        warn = _scan_entry(entry)
        if warn:
            print(warn)
            warned = True
    return 1 if (args.strict and warned) else 0
```

- [ ] **Step 3: justfile 接线**

```text
# justfile :53 行改：
-    uv run python tools/lint_threshold_reconciliation.py
+    uv run python tools/lint_threshold_reconciliation.py --strict
# 同时删除 :33 的 NOTE 注释行（"spec #93 will later add --strict ... batch-A re-anchor hook" —— 本 task 兑现该钩）
```

- [ ] **Step 4: 跑全部 lint 测试+实跑 strict**

Run: `uv run pytest tests/unit/tools/test_lint_threshold_reconciliation.py -v && uv run python tools/lint_threshold_reconciliation.py --strict; echo exit=$?`
Expected: 9 PASS；实跑无输出 exit=0

- [ ] **Step 5: 红测证据——临时改常量验 FAIL 态（回滚）**

```bash
# 临时将 pacing_design.py 的 CONSTELLATION_HARD_BAND 改为 (18, 45) →
uv run python tools/lint_threshold_reconciliation.py --strict; echo exit=$?   # Expected: threshold_drift 15-25 not in [18,45], exit=1
just lint >/dev/null 2>&1; echo exit=$?                                        # Expected: exit=1（just lint 面红）
# git checkout -- src/shenbi/contracts/skills/pacing_design.py 回滚 → 复跑 strict exit=0
```

输出全部粘贴进 progress.md 验收证据。

- [ ] **Step 6: Commit**

```bash
git add tools/lint_threshold_reconciliation.py justfile tests/unit/tools/test_lint_threshold_reconciliation.py
git commit -m "feat: spec #93 T1c — lint --strict FAIL 态+just lint 接线（兑现 batch-A 预留钩）"
```

---

### Task 4: T3 · pricing 模型契约单源倒置（infra · tdd_red_green）

**Files:**
- Modify: `src/shenbi/cost/pricing.py:3-7,14-15,31-32,41`
- Modify: `src/shenbi/pipeline/dispatch_helper.py:94-101,3741`
- Test: `tests/unit/cost/test_pricing.py`（追加）+ `tests/unit/pipeline/test_dispatch_helper_model_source.py`（新建）

**Interfaces:**
- Consumes: 无（pricing 现有 `DEFAULT_PRICING_MODEL: str`、`resolve_model(model: str | None) -> str`）
- Produces: `LLM_MODEL_ENV_VAR: str = "SHENBI_LLM_MODEL"`（pricing 公共常量，替换私有 `_ENV_LLM_MODEL`）；dispatch_helper `_DEFAULT_MODEL`/`_ENV_LLM_MODEL` 局部定义删除，改 import

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/pipeline/test_dispatch_helper_model_source.py 新建
"""Spec #93 T3 — dispatch model constants single-sourced in cost.pricing."""

from __future__ import annotations

import shenbi.pipeline.dispatch_helper as dh
from shenbi.cost import pricing


def test_dispatch_helper_has_no_local_model_constants() -> None:
    assert not hasattr(dh, "_DEFAULT_MODEL")
    assert not hasattr(dh, "_ENV_LLM_MODEL")


def test_dispatch_uses_pricing_single_source() -> None:
    assert dh.LLM_MODEL_ENV_VAR is pricing.LLM_MODEL_ENV_VAR
    assert dh.DEFAULT_PRICING_MODEL is pricing.DEFAULT_PRICING_MODEL
```

```python
# tests/unit/cost/test_pricing.py 追加
def test_env_var_public_constant() -> None:
    from shenbi.cost.pricing import LLM_MODEL_ENV_VAR

    assert LLM_MODEL_ENV_VAR == "SHENBI_LLM_MODEL"
```

Run: `uv run pytest tests/unit/pipeline/test_dispatch_helper_model_source.py tests/unit/cost/test_pricing.py -v`
Expected: FAIL（`hasattr(dh, "_DEFAULT_MODEL")` 为 True / `LLM_MODEL_ENV_VAR` ImportError）

- [ ] **Step 2: pricing 侧改写（单源方）**

```python
# src/shenbi/cost/pricing.py：
# 1) 模块 docstring（:3-7）改为（消除 dispatch_helper 引用）：
"""USD pricing per 1M tokens, keyed to the model that actually ran (spec §3.3).

This module is the single source for the dispatch-path model constants
(``LLM_MODEL_ENV_VAR`` / ``DEFAULT_PRICING_MODEL``) — dispatch_helper
imports them from here (spec #93 T3). Pricing uses that same default so
cost reflects what ran; do NOT hardcode other models here.
"""
# 2) :14-15 注释改：
# The dispatch-path default model — single source; dispatch_helper imports this (spec #93 T3).
# 3) :31-32 改（私有转公共）：
# Env var name — single source, dispatch_helper imports this (spec #93 T3).
LLM_MODEL_ENV_VAR: str = "SHENBI_LLM_MODEL"
# 4) resolve_model 内 :41：
    return os.environ.get(LLM_MODEL_ENV_VAR, DEFAULT_PRICING_MODEL)
```

- [ ] **Step 3: dispatch_helper 侧改写（消费方）**

```python
# src/shenbi/pipeline/dispatch_helper.py：
# 1) 顶部 shenbi.cost import 区（:56 一带）加：
from shenbi.cost.pricing import DEFAULT_PRICING_MODEL, LLM_MODEL_ENV_VAR
# 2) 删 :97 `_ENV_LLM_MODEL = "SHENBI_LLM_MODEL"` 与 :101 `_DEFAULT_MODEL = "deepseek-v4-flash"  # fallback...`
#    （_ENV_LLM_API_KEY/_ENV_LLM_BASE_URL 保持原地——它们本就单源于此模块）
# 3) :3741 改：
    model = os.environ.get(LLM_MODEL_ENV_VAR, DEFAULT_PRICING_MODEL)
```

- [ ] **Step 4: 跑测试+全仓引用面核验**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_helper_model_source.py tests/unit/cost/ -v && grep -rn "dispatch_helper" src/shenbi/cost/; echo grep_exit=$?`
Expected: 测试全 PASS；grep 无输出 exit=1（AC3 判据）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/cost/pricing.py src/shenbi/pipeline/dispatch_helper.py tests/unit/cost/test_pricing.py tests/unit/pipeline/test_dispatch_helper_model_source.py
git commit -m "refactor: spec #93 T3 — dispatch 模型常量单源倒置（dispatch_helper 从 cost.pricing import）"
```

---

### Task 5: T4 · executor 派生集缓存 stat 键失效（leaf · tdd_red_green）

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py:30-59`
- Test: `tests/unit/dispatcher/test_executor_derived_set_freshness.py`（新建）

**Interfaces:**
- Consumes: `bootstrap_registry() -> dict[str, str]`（contracts/registry.py:17-37，内部经 load_registry 的 `(path, mtime_ns, size)` stat 键缓存，自动失效）
- Produces: `_truth_file_set() -> set[str]` / `_decisions_file_set() -> set[str]`（签名不变；语义变更：不再进程期冻结——每次调用重derive，成本=stat 键命中的 dict 查找+set 推导）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/dispatcher/test_executor_derived_set_freshness.py 新建
"""Spec #93 T4 — derived truth/decisions sets follow the registry stat key.

Editing truth-files.yaml mid-process must refresh the derived sets on the
next call (loader contract: (mtime_ns, size) keyed cache), not stay frozen
for the process lifetime.
"""

from __future__ import annotations

from pathlib import Path

import shenbi.contracts.loader as loader_mod
from shenbi.contracts.enums import OutputKind
import shenbi.dispatcher.executor as ex


def _write_registry(path: Path, truth_kind: str) -> None:
    # 真实 schema：concepts 为 {name, kind} 列表（docs/framework/truth-files.yaml）
    path.write_text(
        f"concepts:\n  - {{name: truth/current_state.md, kind: {truth_kind}}}\n",
        encoding="utf-8",
    )


def test_derived_set_refreshes_on_registry_edit(tmp_path: Path, monkeypatch) -> None:
    reg = tmp_path / "truth-files.yaml"
    _write_registry(reg, "truth")
    monkeypatch.setattr(loader_mod, "REGISTRY_PATH", reg)
    monkeypatch.setattr(
        ex,
        "load_contract",
        lambda skill: {
            "kind": OutputKind.ARTIFACT,
            "writes": {"truth/current_state.md"},
            "updates": set(),
        },
    )
    assert ex.derive_file_type("test-skill-writes") == "truth"
    # 同进程改 registry：kind truth → decisions（size 变 → stat 键变）
    _write_registry(reg, "decisions")
    assert ex.derive_file_type("test-skill-writes") == "decisions"
```

Run: `uv run pytest tests/unit/dispatcher/test_executor_derived_set_freshness.py -v`
Expected: FAIL — 第二次断言得 `"truth"`（进程期冻结的 `_truth_files_cache`）

- [ ] **Step 2: 去冻结——删两个模块级缓存，改经 bootstrap_registry 每次 derive**

```python
# src/shenbi/dispatcher/executor.py :30-59 替换为：
def _truth_file_set() -> set[str]:
    """Files listed as kind='truth' in truth-files.yaml concepts.

    Both truth and chapter edits have OutputKind.ARTIFACT, so OutputKind cannot
    distinguish them; the distinction lives in truth-files.yaml (spec New-I).
    Spec #93 T4: derived per call via bootstrap_registry() — the loader's
    (mtime_ns, size) stat-key cache makes this cheap and keeps the derived
    sets fresh when truth-files.yaml is edited mid-process (frozen module
    globals violated the loader's cache contract).
    """
    return {name for name, kind in bootstrap_registry().items() if kind == "truth"}


def _decisions_file_set() -> set[str]:
    """Files listed as kind='decisions' in truth-files.yaml concepts."""
    return {name for name, kind in bootstrap_registry().items() if kind == "decisions"}
```

（删 `_truth_files_cache`/`_decisions_files_cache` 两个全局与 `global` 语句；`bootstrap_registry` 已在 :25 import。）

- [ ] **Step 3: 跑新测+executor 存量测试**

Run: `uv run pytest tests/unit/dispatcher/ -v`
Expected: 全 PASS

- [ ] **Step 4: Commit**

```bash
git add src/shenbi/dispatcher/executor.py tests/unit/dispatcher/test_executor_derived_set_freshness.py
git commit -m "fix: spec #93 T4 — executor 派生集缓存改经 bootstrap_registry stat 键失效（契约对齐）"
```

---

### Task 6: T5 · TREND_COLUMNS 列契约单源（infra · tdd_red_green）

**Files:**
- Modify: `src/shenbi/pipeline/_shared.py`（常量+charter 扩域+__all__）
- Modify: `src/shenbi/pipeline/chapter_loop.py:2877-2906`
- Modify: `src/shenbi/orchestration/escalation_bridge.py:10-25`
- Modify: `src/shenbi/pipeline/confidence_calibration.py:116,128`
- Test: `tests/unit/orchestration/test_bridges.py`（追加）+ `tests/unit/pipeline/test_trend_columns.py`（新建）

**Interfaces:**
- Consumes: 无
- Produces:
  - `TREND_COLUMNS: tuple[str, ...]`（9 列名，序=`("chapter", "chapter_role", "情感落地", "场景临场感", "文笔质感", "读者回报", "overall", "confidence", "human_overridden")`——逐字对齐 skills/shenbi-review-resonance/SKILL.md:181 表头）
  - `TREND_OVERALL_IDX: int`（=TREND_COLUMNS.index("overall")=6）/ `TREND_CONFIDENCE_IDX: int`（=TREND_COLUMNS.index("confidence")=7）
  - `build_resonance_trend_row(chapter: int, overall: int) -> str`（签名不变，输出逐字节不变）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/pipeline/test_trend_columns.py 新建
"""Spec #93 T5 — resonance_trend.md column contract single source."""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings, strategies as st

from shenbi.orchestration.escalation_bridge import parse_resonance_scores
from shenbi.pipeline._shared import (
    TREND_COLUMNS,
    TREND_CONFIDENCE_IDX,
    TREND_OVERALL_IDX,
)
from shenbi.pipeline.chapter_loop import build_resonance_trend_row

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_HEADER = REPO_ROOT / "skills" / "shenbi-review-resonance" / "SKILL.md"


def test_columns_match_skill_contract_header() -> None:
    # 三源对账：常量 ↔ 技能契约表头（SKILL.md:181 prose 契约是列名的权威散文面）
    text = SKILL_HEADER.read_text(encoding="utf-8")
    header_line = next(ln for ln in text.splitlines() if ln.startswith("| chapter | chapter_role"))
    names = [c.strip() for c in header_line.strip("|").split("|")]
    assert TREND_COLUMNS == tuple(names)


def test_indices_pin_positions() -> None:
    assert TREND_OVERALL_IDX == 6
    assert TREND_CONFIDENCE_IDX == 7


def test_writer_row_exact_string() -> None:
    assert build_resonance_trend_row(55, 83) == "| 55 | - | - | - | - | - | 83 | - |  |"


@settings(max_examples=50, deadline=None)
@given(chapter=st.integers(1, 9999), overall=st.integers(0, 100))
def test_roundtrip_writer_to_bridge(tmp_path, chapter: int, overall: int) -> None:
    # 往返 property：writer 产出行 → bridge 解析出 overall（列位漂移即红）
    trend = tmp_path / "resonance_trend.md"
    trend.write_text(
        "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        + build_resonance_trend_row(chapter, overall)
        + "\n",
        encoding="utf-8",
    )
    assert parse_resonance_scores(trend) == [float(overall)]
```

Run: `uv run pytest tests/unit/pipeline/test_trend_columns.py -v`
Expected: FAIL with `ImportError: cannot import name 'TREND_COLUMNS'`

- [ ] **Step 2: _shared 加常量（charter 扩域）**

```python
# src/shenbi/pipeline/_shared.py — docstring 首段后追加一句：
# "Spec #93 T5 extends this leaf with the resonance_trend.md column contract
#  (TREND_COLUMNS) — still stdlib-only, no cycle member."
# 模块体追加（__all__ 同步加 TREND_COLUMNS/TREND_OVERALL_IDX/TREND_CONFIDENCE_IDX）：

#: resonance_trend.md column contract (spec #93 T5) — single source for the
#: 9-column layout. Prose authority: skills/shenbi-review-resonance/SKILL.md
#: table header. Consumers: chapter_loop.build_resonance_trend_row (writer),
#: orchestration/escalation_bridge.parse_resonance_scores (overall reader),
#: pipeline/confidence_calibration (confidence patcher).
TREND_COLUMNS: tuple[str, ...] = (
    "chapter",
    "chapter_role",
    "情感落地",
    "场景临场感",
    "文笔质感",
    "读者回报",
    "overall",
    "confidence",
    "human_overridden",
)
#: cell index of the overall score — what parse_resonance_scores reads.
TREND_OVERALL_IDX: int = TREND_COLUMNS.index("overall")
#: cell index of confidence — what confidence_calibration patches.
TREND_CONFIDENCE_IDX: int = TREND_COLUMNS.index("confidence")
```

- [ ] **Step 3: 三消费者换装**

```python
# chapter_loop.py — build_resonance_trend_row 顶部 import（pipeline 同包）：
from shenbi.pipeline._shared import TREND_COLUMNS


# 函数体改为由常量驱动（输出逐字节不变，test_writer_row_exact_string 锁死）：
def build_resonance_trend_row(chapter: int, overall: int) -> str:
    """Build a 9-column markdown table row for resonance_trend.md.

    Column layout is the TREND_COLUMNS contract (pipeline/_shared.py, spec
    #93 T5) — parse_resonance_scores reads cells[TREND_OVERALL_IDX]. The
    skill contract keeps a bare ``{N}`` key so framework and skill writers
    dedup onto the same row (SDD #21 R1).
    """
    cells: list[str] = []
    for name in TREND_COLUMNS:
        if name == "chapter":
            cells.append(str(chapter))
        elif name == "overall":
            cells.append(str(overall))
        elif name == "human_overridden":
            cells.append("")  # blank like the skill's convention
        else:
            cells.append("-")  # placeholder: role + 4 dimensions + confidence
    return "| " + " | ".join(cells) + " |"


# docstring 其余段落（parse_trend/caller persist 说明）保留。

# escalation_bridge.py — import 加：
from shenbi.pipeline._shared import TREND_OVERALL_IDX
# parse_resonance_scores 内：
#   `if len(cells) >= 7:`        → `if len(cells) > TREND_OVERALL_IDX:`
#   `val = float(cells[6])`      → `val = float(cells[TREND_OVERALL_IDX])`

# confidence_calibration.py — import 加：
from shenbi.pipeline._shared import TREND_CONFIDENCE_IDX
# 两处 patch_markdown_table_cell(trend_path, str(chapter), "chapter", 7, calibrated)
#   的字面量 7 → TREND_CONFIDENCE_IDX
```

- [ ] **Step 4: 跑新测+三消费者存量测试**

Run: `uv run pytest tests/unit/pipeline/test_trend_columns.py tests/unit/orchestration/test_bridges.py tests/unit/pipeline/ -k "trend or resonance or calibration or bridge" -v`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/_shared.py src/shenbi/pipeline/chapter_loop.py src/shenbi/orchestration/escalation_bridge.py src/shenbi/pipeline/confidence_calibration.py tests/unit/pipeline/test_trend_columns.py
git commit -m "feat: spec #93 T5 — TREND_COLUMNS 列契约单源（三消费者 import+往返 property+SKILL 表头对账）"
```

---

### Task 7: T6 · 疲劳词门-契约键形接线（infra · tdd_red_green）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:967-977`
- Test: `tests/unit/gates/g4/test_chapter_drafting_detect.py`（重写 snake 注入测试为真实 fixture 形状）

**Interfaces:**
- Consumes: `read_genre_config(project_dir: str | Path) -> dict[str, Any]`（gates/shared.py:731，原始 json dict）；`FATIGUE_BASE: list[str]`（gates/shared.py:873）；`log = get_logger(__name__)`（chapter_drafting.py:46 既有）
- Produces: `_fatigue_word_list(gc: dict[str, Any]) -> list[str]`（新私有助手：camel `fatigueWords` 禁用∪慎用并集；缺/畸形 → `list(FATIGUE_BASE)` 回退+structlog WARN）

- [ ] **Step 1: 重写测试为真实 fixture 形状（红）**

```python
# tests/unit/gates/g4/test_chapter_drafting_detect.py —
# test_fatigue_words_use_project_genre_config 全函数替换为：
def test_fatigue_words_use_project_genre_config(tmp_path, monkeypatch):
    # spec #93 T6 — 门读契约真实形状（camelCase fatigueWords 嵌套对象）。
    # 眸光一凝 ∈ fixture 禁用表且与 FATIGUE_BASE 零子串碰撞（碰撞词现状即
    # base 计数 FAIL，红测不红——词选约束见 spec）；真实技能产物顶层无
    # snake `fatigue_words` 键（旧测试手工注入的形状技能永不写）。
    pd = tmp_path / "pd"
    rd = tmp_path / "rd"
    pd.mkdir()
    rd.mkdir()
    shutil.copy(FIXTURES / "genre-config-example.json", pd / "genre-config.json")
    body = "第3章\n\n" + "眸光一凝" * 9
    chapter = rd / "chapter-3-x.md"
    chapter.write_text(body, encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # CWD independent
    result = json.loads(g4_chapter_drafting([str(chapter)], str(rd), str(pd), str(tmp_path)))
    must_fix = " ".join(str(x) for x in result.get("must_fix", []))
    assert "G4.fatigue" in must_fix and ">8" in must_fix


def test_fatigue_malformed_config_falls_back_to_base(tmp_path, monkeypatch):
    # 形状异常（禁用非列表）→ 回退 FATIGUE_BASE + 不炸门（防御面）
    pd = tmp_path / "pd"
    rd = tmp_path / "rd"
    pd.mkdir()
    rd.mkdir()
    (pd / "genre-config.json").write_text(
        json.dumps({"fatigueWords": {"禁用": "not-a-list", "慎用": []}}), encoding="utf-8"
    )
    body = "第3章\n\n" + "突然" * 9  # 突然 ∈ FATIGUE_BASE
    chapter = rd / "chapter-3-x.md"
    chapter.write_text(body, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = json.loads(g4_chapter_drafting([str(chapter)], str(rd), str(pd), str(tmp_path)))
    must_fix = " ".join(str(x) for x in result.get("must_fix", []))
    assert "G4.fatigue" in must_fix and ">8" in must_fix
```

Run: `uv run pytest tests/unit/gates/g4/test_chapter_drafting_detect.py -v`
Expected: 第一个测试 FAIL（现状回退 FATIGUE_BASE，眸光一凝 0 命中 → 无 G4.fatigue）；第二个 PASS（现状即回退）

- [ ] **Step 2: 实现键形接线**

```python
# src/shenbi/gates/g4/chapter_drafting.py — _check_fatigue 前加私有助手：
def _fatigue_word_list(gc: dict[str, Any]) -> list[str]:
    """Fatigue word list from genre-config's contract shape (spec #93 T6).

    The skill contract writes a camelCase nested object
    ``fatigueWords: {禁用: [...], 慎用: [...], 替换建议: {...}}``
    (contracts/skills/genre_config.py alias; read_genre_config returns the
    raw JSON). The gate counts the 禁用∪慎用 union — the config replaces
    FATIGUE_BASE entirely when present; missing/malformed shapes fall back
    to FATIGUE_BASE (never crash the gate).
    """
    fw = gc.get("fatigueWords")
    if isinstance(fw, dict):
        words: list[str] = []
        for key in ("禁用", "慎用"):
            group = fw.get(key)
            if isinstance(group, list):
                words.extend(w for w in group if isinstance(w, str))
        if words:
            return words
        log.warning("fatigue_words_config_empty_or_malformed", keys=sorted(fw.keys()))
    return list(FATIGUE_BASE)

    # _check_fatigue 内 :970 改：
    fatigue_list = _fatigue_word_list(gc)


# （>8 阈与 FAIL/PASS 结构不变；docstring :968 的「genre-config 阈」保持——接线后为真）
```

- [ ] **Step 3: 跑重写测试+chapter_drafting 全量**

Run: `uv run pytest tests/unit/gates/g4/test_chapter_drafting_detect.py tests/unit/gates/g4/ -v`
Expected: 全 PASS

- [ ] **Step 4: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py tests/unit/gates/g4/test_chapter_drafting_detect.py
git commit -m "fix: spec #93 T6 — 疲劳词门改读契约 camel 形状（禁用∪慎用并集，畸形回退 base+WARN）"
```

---

### Task 8: T2 · gates.md 裕度节+g4 双向回指（leaf · characterization · 依赖 Task 7）

**Files:**
- Modify: `docs/framework/gates.md`（文末追加节）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:931,967-968`（两处注释回指）

**Interfaces:**
- Consumes: Task 7 产出（T6 接线后的真实门语义）
- Produces: gates.md `## 散文↔门裕度（spec #93 T2）` 节（转折词+疲劳词两行决策+出处）

- [ ] **Step 1: gates.md 追加裕度节**

```markdown
## 散文↔门裕度（spec #93 T2）

散文（SKILL.md 教学面）与门（G4 执行面）的阈值**有意不同**——提示比门严是 prompt 工程设计：
自动化生成文本在对应指标上天然偏多，门给裕度防重派风暴，散文保持高压引导模型自律。
改任一侧前先读本节；把散文「对齐」到门值=改变 LLM 行为，属 prompt 变更须走内容批。

- **转折词**：散文预算 1/3000（chapter-drafting SKILL 字面 ×5 :92-94/:108/:185＋公式形态 [字数/3000] :174）
  / 门限 1/1000（chapter_drafting.py `max(5, wc//1000)`，:931 注释自认 relaxed for automated gen）——3× 裕度。
- **疲劳词**：散文面=禁用词出现即报错＋慎用词每章 >3 报警（genre-config SKILL.md 疲劳词管理节）
  / 门面=禁用∪慎用命中 >8 FAIL（chapter_drafting.py `_check_fatigue`，spec #93 T6 接线后门实读
  genre-config 词表）——门对禁用词同样给自动化裕度（散文零容忍 vs 门 ≤8），与转折词同一裕度模式。
```

- [ ] **Step 2: g4 两处注释回指**

```python
# chapter_drafting.py :931 注释行追加一句（保持原注释行不动，同注释块加行）：
    # ...relaxed from 1/3000 for automated gen) — 裕度裁定见 docs/framework/gates.md §散文↔门裕度
# _check_fatigue docstring（:967-968）追加：
    """Fatigue words <= 8 (genre-config 阈). 裕度裁定见 docs/framework/gates.md §散文↔门裕度."""
```

- [ ] **Step 3: 双向锚验收 grep**

Run: `grep -n "散文↔门裕度" docs/framework/gates.md src/shenbi/gates/g4/chapter_drafting.py`
Expected: gates.md ≥2 命中（节标题+正文回指）+ chapter_drafting.py 2 命中（双向锚成立）

Run: `uv run pytest tests/unit/gates/g4/ -q`
Expected: 全 PASS（注释改动零行为影响）

- [ ] **Step 4: Commit**

```bash
git add docs/framework/gates.md src/shenbi/gates/g4/chapter_drafting.py
git commit -m "docs: spec #93 T2 — gates.md 散文↔门裕度节（转折词 3×＋疲劳词并集模式）+g4 双向回指"
```

---

## 收尾（阶段 7 用，非独立 task）

- `just check` 全量（阶段 7 门禁，输出+首行指纹进 progress.md）
- AC 汇总证据进 progress.md `## 验收证据`（各 task Step 中的命令输出汇总）
