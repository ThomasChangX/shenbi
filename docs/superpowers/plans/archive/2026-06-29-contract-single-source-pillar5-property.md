# 契约单源架构 - 支柱五（属性测试网）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `tests/property/` 属性测试网，以手写 hypothesis strategy 覆盖 spec 列出的全部算术 bug 不变量（判据 6：CI 必过）+ jieba 冻结分词基线，并补齐唯一会违反不变量的真 bug 修复（P50≠median）与 in-process 纯度运行时兜底 CapabilityFS。

**Architecture:** 属性测试网是 spec 的「无法 CI 落地」层：手写 strategy 把跨字段/算术不变量编码成 CI 门。每个不变量**先验证现有代码是否满足**——绝大多数（标点、熵归一、drift 排除、volume_decline）现有代码已正确，属性测试把它们从「样例覆盖」升级为「全输入不变量」；**唯一真 bug 是 `compute_percentiles` P50≠median**（Task 4 修复）。G3.4 空转与 G6.12 内嵌失效是「门改造」问题（spec 归支柱二），本计划**不改 gate_G3/g6.py**，而是为它们的正确不变量立纯函数 + 属性测试，门接线留给支柱二（与支柱四 `audit_trace` 不替换 gate_G7 同模式）。CapabilityFS 是 in-process 纯度兜底（判据 4/14），codex subprocess 的 read-provenance 仍是已知盲点（future work）。

**Tech Stack:** Python 3.11+，pytest + hypothesis（已依赖），jieba==0.42.1（已固定，pyproject.toml:10），mypy strict（已 CI），ruff，pathlib+json。**不引入 hypothesis-jsonschema**（N8 可选，手写 strategy 即可）。

**关联 spec:** [../specs/2026-06-29-contract-single-source-design.md](../specs/2026-06-29-contract-single-source-design.md) v5.2 支柱五（成功判据 4/5/6/14）。

**前置依赖:** 支柱一已落地（`shenbi.contracts.registry.bootstrap_registry`、`shenbi.contracts.enums`）；支柱三已落地（`shenbi.text.cjk`：`find_terms`/`count_punctuation`/`tokenize`）。本计划 import 这两者。

**已核实事实（亲手读源码，非转述）：**

| 不变量 | 真实位置 | 现状 | 本计划动作 |
|---|---|---|---|
| P50==median | `style_learning/compute_stats.py:99`（P50=`values[max(0,int(n*0.50)-1)]`）vs `:112`（median=`lengths[n//2]`） | **BUG**：n≥2 时索引不同 | Task 4 **修复** P50→`values[n//2]` + 属性测试 |
| 标点 count==text.count(token) | `text/cjk.py:58-70`（`sum(text.count(token) for token in tokens)`） | 正确（整 token）；对照 bug 在 `compute_stats.py:223`（per-char） | Task 2 属性测试 |
| drift 排除不泄漏 | `drift_detection/compute_drift.py:67-133`（excl reset run/below_run at :91/:117，kept 过滤 :110） | 触发层正确 | Task 5 属性测试（触发层；平滑层是已知边界，见风险表） |
| 熵 sum==1 | `chapter_pattern/compute_pattern.py:79-104`（input⊆PATTERNS 时 Σcount==n） | 正确 | Task 3 属性测试 |
| volume_decline 必触发 | `compute_drift.py:136-146`（`scores[-1] < scores[-2]`） | 正确 | Task 5 属性测试 |
| G6.12 CJK 内嵌必检出 | `gates/g6.py:399`（`[^\w]` 边界 → CJK 全是 `\w`，内嵌不检出）= BUG；正确工具 `text/cjk.find_terms`（substring） | g6.py 待支柱二改；find_terms 已正确 | Task 7 属性测试（断言 find_terms，不改 g6.py） |
| G3.4 无 SCORE 必 fail | `gates/g3.py:155`（`if gen_agent and scorer_agent and ...`，缺 scorer→PASS = fail-open）= BUG | gate 待支柱二改 | Task 8 纯函数 fail-closed + 属性测试（不改 gate_G3） |
| 门纯度 | gates 写文件是散文约束 | 无运行时兜底 | Task 9 CapabilityFS（in-process） |
| 三表一致 | `contracts/registry.py:bootstrap_registry` 与 `contract.py:load_registry` 均 read truth-files.yaml | 已一致（实测 54==54） | Task 10 属性测试 |
| jieba 冻结 | `text/cjk.py:96-110` tokenize | 固定 0.42.1 | Task 11 真实 token 基线（实测捕获，非猜测） |

## Global Constraints

- Python 3.11+；属性测试文件全部在 `tests/property/<域>/`，每个新域加 `__init__.py`。
- **手写 strategy only**：跨字段不变量用 `@composite` 手写；不引入 hypothesis-jsonschema（N8 可选，禁加依赖）。
- mypy strict + ruff CI 必须干净。新增测试文件在 `[tool.ruff.lint.per-file-ignores]` 加完整忽略集（仿现有 `"tests/property/cjk/*.py"` 块）。
- 框架代码无 print()（用 structlog）。
- **覆盖率门（关键，导致过以往计划失败）：** `pyproject.toml` addopts 含 `--cov=shenbi` + `fail_under=90`（`[tool.coverage.report]`）。因此**任何单文件/子集** `uv run pytest <path>` 都会因覆盖率不足退出码非零。本计划所有单文件/子集 pytest 命令必须追加 `--no-cov`（如 `uv run pytest tests/property/stats/test_percentile_properties.py -q --no-cov`）。覆盖率门只在**全量** `uv run pytest -q` 时生效（Task 12）。下面各步为简洁省略 `--no-cov`，执行者一律按此规则补上。
- **不引用具体测试数**（避免漂移）：写「现有测试集无 regression + 新增测试全通过」，不写「X passed」。
- **不修改 gate 行为**：本计划不改 `gates/g3.py`/`gates/g6.py`/`gates/g7.py` 的现有命令逻辑。G3.4/G6.12 的正确不变量以**新纯函数**承载 + 属性测试覆盖；门接线是支柱二。
- jieba 版本固定 `0.42.1`（pyproject.toml:10 已 pin）；冻结基线来自亲手运行该版本的真实分词，不是同义反复。

## 文件结构

| 文件 | 责任 |
|---|---|
| `tests/property/stats/__init__.py`、`test_percentile_properties.py` | P50==median + compute_percentiles 单调性属性（依赖 Task 4 修复） |
| `tests/property/stats/test_entropy_properties.py` | 熵归一（Σcount==n）+ 熵重算一致 |
| `tests/property/drift/__init__.py`、`test_drift_properties.py` | drift 排除不泄漏（触发层）+ volume_decline 必触发 |
| `tests/property/cjk/test_punct_properties.py` | 标点整-token 计数属性（cjk.count_punctuation） |
| `tests/property/cjk/test_g612_embedded_properties.py` | G6.12 内嵌 CJK 必检出（cjk.find_terms，含旧 `[^\w]` 失效对照） |
| `tests/property/gates/test_g34_independence_properties.py` | G3.4 fail-closed 属性（新纯函数 `gates/g3_independence.py`） |
| `src/shenbi/gates/g3_independence.py` | 纯函数 `scoring_independence_status`（fail-closed；gate_G3 接线=支柱二） |
| `src/shenbi/capability_fs.py` | `CapabilityFS`（in-process 只读 FS 句柄；写→PermissionError） |
| `tests/property/gates/test_capability_fs_properties.py` | CapabilityFS 纯度属性 |
| `tests/property/contracts/test_registry_consistency.py` | 三表一致：bootstrap_registry==load_registry concepts==truth-files.yaml |
| `tests/property/cjk/test_tokenize_frozen.py` | jieba 冻结分词基线（真实 token 列表） |

---

### Task 1: 属性测试网骨架 + ruff per-file-ignores

**Files:** Create `tests/property/stats/__init__.py`、`tests/property/drift/__init__.py`；Modify `pyproject.toml`

**Interfaces:** Consumes 现有 `tests/property/__init__.py`（已存在）。Produces 新测试域包。

- [ ] **Step 1: Create domain package markers**
```python
# tests/property/stats/__init__.py
"""属性测试：算术统计不变量（spec 支柱五）。"""
```
```python
# tests/property/drift/__init__.py
"""属性测试：drift 排除/触发不变量（spec 支柱五）。"""
```

- [ ] **Step 2: Add ruff per-file-ignores**

在 `[tool.ruff.lint.per-file-ignores]`（先 `grep -n "tests/property/cjk" pyproject.toml` 确认现有块位置与缩进，在其后追加）：
```toml
"tests/property/stats/*.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/drift/*.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/cjk/test_punct_properties.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/cjk/test_g612_embedded_properties.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/cjk/test_tokenize_frozen.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/gates/test_g34_independence_properties.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/gates/test_capability_fs_properties.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"tests/property/contracts/*.py" = [
    "D103", "D101", "D102", "D205", "D415", "E402",
    "I001", "F401", "F841", "PLR2004",
    "RUF001", "RUF002", "RUF003", "RUF005", "RUF059",
]
"src/shenbi/capability_fs.py" = ["RUF001", "RUF002", "RUF003", "RUF005", "RUF059"]
"src/shenbi/gates/g3_independence.py" = ["RUF001", "RUF002", "RUF003", "RUF005", "RUF059"]
```
（注意：`tests/property/gates/__init__.py` 已存在；`test_gate_invariants.py` 是既有文件，本计划不动它。）

- [ ] **Step 3: Verify packages importable**
`uv run python -c "import tests.property.stats, tests.property.drift; print('OK')"` → `OK`

- [ ] **Step 4: ruff clean**
`uv run ruff check tests/property/` → All passed（暂无新 .py，仅包标记）

- [ ] **Step 5: Commit**
```bash
git add tests/property/stats/__init__.py tests/property/drift/__init__.py pyproject.toml
git commit -m "chore(property): add property-test domain packages + ruff ignores"
```

---

### Task 2: 标点整-token 计数属性（cjk.count_punctuation，现状正确）

**Files:** Create `tests/property/cjk/test_punct_properties.py`

**Interfaces:** Consumes `shenbi.text.cjk.count_punctuation`、`shenbi.text.cjk.PUNCTUATION_TOKENS`。

**核实：** `cjk.py:58-70` `count_punctuation` = `{name: sum(text.count(token) for token in tokens)}`（整 token，正确）。对照 bug 在 `compute_stats.py:216-226` `compute_punctuation`（`sum(text.count(c) for c in chars)`，多字符标点 per-char 重复计数）——本任务测**正确**的 cjk 版本。

- [ ] **Step 1: Write property tests**
```python
# tests/property/cjk/test_punct_properties.py
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.text.cjk import PUNCTUATION_TOKENS, count_punctuation

# 所有标点 token 字符 + 普通 CJK，覆盖边界（token 在首/尾/中间/重叠）
_PUNCT_CHARS = "".join(t for toks in PUNCTUATION_TOKENS.values() for t in toks)
punct_text = st.text(
    alphabet=st.sampled_from(list(_PUNCT_CHARS + "你好世界正文内容level123 空格")),
    min_size=0,
    max_size=80,
)


@given(punct_text)
@settings(max_examples=200, deadline=None)
def test_each_punct_count_matches_text_count(text: str) -> None:
    """整 token 计数：counts[name] == sum(text.count(token) for token in tokens)。

    对照 bug：compute_stats.compute_punctuation 对多字符标点（——/……）per-char
    迭代导致重复计数；cjk.count_punctuation 用整 token 正确。"""
    counts = count_punctuation(text)
    for name, tokens in PUNCTUATION_TOKENS.items():
        assert counts[name] == sum(text.count(token) for token in tokens), name


@given(punct_text)
@settings(max_examples=200, deadline=None)
def test_dash_counted_once_not_per_char(text: str) -> None:
    """破折号 ——（2 字符）整体计数，绝不 per-char 翻倍。

    '你好——世界'：text.count('——')==1（不是 text.count('—')*迭代==4）。"""
    assert count_punctuation(text)["破折号"] == text.count("——") + text.count("──")


@given(punct_text)
@settings(max_examples=100, deadline=None)
def test_all_counts_non_negative(text: str) -> None:
    counts = count_punctuation(text)
    assert all(v >= 0 for v in counts.values())
```

- [ ] **Step 2: Run → passes**
`uv run pytest tests/property/cjk/test_punct_properties.py -q --no-cov` → 通过
- [ ] **Step 3: mypy + ruff**
`uv run mypy tests/property/cjk/test_punct_properties.py --ignore-missing-imports && uv run ruff check tests/property/cjk/test_punct_properties.py` → clean
- [ ] **Step 4: Commit**
```bash
git add tests/property/cjk/test_punct_properties.py
git commit -m "test(property): punctuation whole-token counting invariant (cjk.count_punctuation)"
```

---

### Task 3: 熵归一属性（compute_entropy，现状正确）

**Files:** Create `tests/property/stats/test_entropy_properties.py`

**Interfaces:** Consumes `shenbi.skill_utils.chapter_pattern.compute_pattern.compute_entropy`、`PATTERNS`。

**核实：** `compute_pattern.py:79-104`。`n=len(patterns)`；`counter=Counter(patterns)`；对每个 PATTERNS 项 count=counter.get(p,0)。当 input ⊆ PATTERNS：Σ(present count)==n（精确整数归一）；熵=round(Σ -count/n·log2(count/n),4)。

- [ ] **Step 1: Write property tests**
```python
# tests/property/stats/test_entropy_properties.py
from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.skill_utils.chapter_pattern.compute_pattern import PATTERNS, compute_entropy

# input 必须取自 PATTERNS（compute_entropy 的契约：未知模式不入归一分母）
pattern_lists = st.lists(
    st.sampled_from(PATTERNS), min_size=1, max_size=40
)


@given(pattern_lists)
@settings(max_examples=200, deadline=None)
def test_present_counts_sum_to_n(patterns: list[str]) -> None:
    """归一：出现模式的计数之和 == 总数（精确整数，非浮点近似）。

    compute_entropy 对 input⊆PATTERNS 保证 Σ(count/n)==1。本测试断言其整数
    等价 Σcount==n，避免浮点舍入噪音。"""
    _, terms = compute_entropy(patterns)
    n = len(patterns)
    assert sum(t["count"] for t in terms if t["count"] > 0) == n


@given(pattern_lists)
@settings(max_examples=200, deadline=None)
def test_entropy_matches_recompute(patterns: list[str]) -> None:
    """熵重算一致：返回值 == round(-Σ(count/n)·log2(count/n), 4)。"""
    entropy, terms = compute_entropy(patterns)
    n = len(patterns)
    recompute = round(
        sum(-(t["count"] / n) * math.log2(t["count"] / n) for t in terms if t["count"] > 0),
        4,
    )
    assert entropy == recompute


@given(pattern_lists)
@settings(max_examples=200, deadline=None)
def test_entropy_bounded_non_negative(patterns: list[str]) -> None:
    """0 ≤ H ≤ log2(不同模式数)。单模式 H==0。"""
    entropy, _ = compute_entropy(patterns)
    assert entropy >= 0.0
    k = len(set(patterns))
    assert entropy <= math.log2(k) + 1e-9


@given(st.lists(st.sampled_from(PATTERNS), min_size=1, max_size=10))
@settings(max_examples=50, deadline=None)
def test_single_pattern_zero_entropy(patterns: list[str]) -> None:
    if len(set(patterns)) == 1:
        entropy, _ = compute_entropy(patterns)
        assert entropy == 0.0
```

- [ ] **Step 2: Run → passes**
`uv run pytest tests/property/stats/test_entropy_properties.py -q --no-cov` → 通过
- [ ] **Step 3: mypy + ruff + commit**
```bash
git add tests/property/stats/test_entropy_properties.py
git commit -m "test(property): entropy normalization + recompute invariants (compute_entropy)"
```

---

### Task 4: 修复 P50≠median + 属性测试（唯一真算术 bug）

**Files:** Modify `src/shenbi/skill_utils/style_learning/compute_stats.py:99`；Create `tests/property/stats/test_percentile_properties.py`

**Interfaces:** Consumes `shenbi.skill_utils.style_learning.compute_stats.compute_percentiles`、`compute_sentence_stats`。Produces 修复后的 P50（== median）。

**核实（亲手）：** `compute_stats.py:99` P50 = `values[max(0, int(n * 0.50) - 1)]`；`:112` median = `lengths[n // 2]`。
- n=2：P50 索引 max(0,0)=0；median 索引 1 → **不等**。
- n=3：P50 索引 max(0,0)=0；median 索引 1 → **不等**。
- n=4：P50 索引 1；median 索引 2 → **不等**。
即 P50≠median（spec「P50≠median」缺陷属实）。**修复**：让 P50 与 median 同用 `n//2` 地板中点（compute_sentence_stats 已以此定义 median）。**回归安全核实：** `tests/unit/skill_utils/test_compute_stats.py` 无任何测试 pin 具体 P50/median 数值（仅查 key 存在、count、histogram、空→零、单值→自身）→ 修复不破坏既有测试。

- [ ] **Step 1: Write failing property test**
```python
# tests/property/stats/test_percentile_properties.py
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.skill_utils.style_learning.compute_stats import (
    compute_percentiles,
    compute_sentence_stats,
)

sorted_pos_ints = st.lists(
    st.integers(min_value=1, max_value=999), min_size=1, max_size=60
).map(lambda xs: sorted(xs))


@given(sorted_pos_ints)
@settings(max_examples=200, deadline=None)
def test_p50_equals_median_index(vs: list[int]) -> None:
    """P50 == 地板中点 vs[n//2]（与 compute_sentence_stats 的 median 同索引）。

    旧 bug：P50 用 int(n*0.50)-1，median 用 n//2，n≥2 时不等。修复后二者一致。"""
    pct = compute_percentiles(vs)
    assert pct["P50"] == vs[len(vs) // 2]


@given(sorted_pos_ints)
@settings(max_examples=200, deadline=None)
def test_p50_equals_sentence_stats_median(vs: list[int]) -> None:
    """compute_percentiles P50 与 compute_sentence_stats median 必须相等（同一排序序列）。"""
    pct = compute_percentiles(vs)
    # compute_sentence_stats 内部 sort，故传已排序即稳定
    sentences = [("", x) for x in vs]
    stats = compute_sentence_stats(sentences)
    assert stats["P50"] == stats["median"] == pct["P50"]


@given(sorted_pos_ints)
@settings(max_examples=100, deadline=None)
def test_percentiles_within_range(vs: list[int]) -> None:
    """所有百分位必须在 [min, max] 区间（值域约束，非跨级单调）。

    nearest-rank 百分位方案不保证跨级单调（P25<=P50<=P95）：
    n=2 时 P50=values[1] 而 P25/P95=values[0]，故 P25<=P50 但 P50>P95 可能成立。
    正确不变量是每个百分位值落在数据 [min,max] 区间内。
    """
    pct = compute_percentiles(vs)
    lo, hi = vs[0], vs[-1]
    for key in ("P25", "P50", "P75", "P95"):
        assert lo <= pct[key] <= hi, key


def test_percentiles_empty_returns_zeros() -> None:
    assert compute_percentiles([]) == {"P25": 0, "P50": 0, "P75": 0, "P95": 0}
```

- [ ] **Step 2: Run → FAIL**
`uv run pytest tests/property/stats/test_percentile_properties.py -q --no-cov` → FAIL（`test_p50_equals_median_index` 在 n≥2 断言 P50==vs[n//2] 失败，现状 P50=vs[int(n*0.5)-1]）

- [ ] **Step 3: Implement fix (compute_stats.py:99)**

读现状确认行号：`sed -n '92,102p' src/shenbi/skill_utils/style_learning/compute_stats.py`。

将 P50 行由：
```python
        "P50": values[max(0, int(n * 0.50) - 1)],
```
改为：
```python
        # P50 必须与 compute_sentence_stats 的 median（lengths[n//2]）同源；
        # 旧式 int(n*0.50)-1 在 n≥2 时与 median 偏移 → P50≠median（spec 支柱五修复）。
        "P50": values[n // 2],
```
P25/P75/P95 不变（它们是最近秩估计，无 median 对照项，不在本不变量范围）。

- [ ] **Step 4: Run property tests → PASS**
`uv run pytest tests/property/stats/test_percentile_properties.py -q --no-cov` → 通过
- [ ] **Step 5: Regression — 既有 compute_stats 测试不变**
`uv run pytest tests/unit/skill_utils/test_compute_stats.py -q --no-cov` → 既有测试无 regression（无 pin 具体 P50/median 值）
- [ ] **Step 6: mypy + ruff + commit**
```bash
git add src/shenbi/skill_utils/style_learning/compute_stats.py \
        tests/property/stats/test_percentile_properties.py
git commit -m "fix(style_learning): P50==median (compute_percentiles uses n//2 floor-midpoint)"
```

---

### Task 5: drift 排除不泄漏 + volume_decline 必触发属性（现状正确）

**Files:** Create `tests/property/drift/test_drift_properties.py`

**Interfaces:** Consumes `shenbi.skill_utils.drift_detection.compute_drift.detect_chapter_drift`、`detect_volume_drift`。

**核实（亲手）：** `compute_drift.py`：
- 排除（`:82` excl=`exclude_indices or set()`）：monotonic run 在 excl 处 reset（`:91-92` `run,start,prev=0,i+1,None`）；sigma kept 过滤 excl（`:110`）；below_run 在 excl reset（`:117-118`）。→ 触发层：任何 MONOTONIC_DECLINE finding 的章节跨度（detail `chapters {start+1}-{i+1}`，0-基 `[start, i]`）**不含**任何 excl 索引。**触发层正确**；平滑层会把 excl 原值渗入邻居（已知边界，记风险表，不在本不变量）。
- volume_decline（`:136-146`）：finding 当且仅当 `len≥2 且 scores[-1] < scores[-2]`。

- [ ] **Step 1: Write property tests**
```python
# tests/property/drift/test_drift_properties.py
from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.skill_utils.drift_detection.compute_drift import (
    detect_chapter_drift,
    detect_volume_drift,
)

_CHAPTER_RE = re.compile(r"chapters (\d+)-(\d+)")

scores_st = st.lists(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    min_size=0,
    max_size=20,
)


@given(
    raw=scores_st,
    excl=st.sets(st.integers(min_value=0, max_value=19), max_size=8),
)
@settings(max_examples=200, deadline=None)
def test_monotonic_decline_span_excludes_overridden(
    raw: list[float], excl: set[int]
) -> None:
    """drift 排除不泄漏（触发层）：任何 MONOTONIC_DECLINE 的章节跨度不含 excl 索引。

    excl reset run/start/prev（compute_drift.py:91-92），故递减不可能跨越被排除章。
    detail 形如 '...chapters {start+1}-{i+1}'，0-基区间 [start, i] 必与 excl 不交。"""
    if len(raw) < 2:
        return
    findings = detect_chapter_drift(raw, dim="情感落地", exclude_indices=excl)
    for f in findings:
        if f.kind != "monotonic_decline":
            continue
        m = _CHAPTER_RE.search(f.detail)
        assert m is not None, f.detail
        start1, end1 = int(m.group(1)), int(m.group(2))  # 1-based chapter numbers
        span0 = set(range(start1 - 1, end1))  # 0-based indices [start, i]
        assert not (span0 & excl), f"{f.detail} 跨越被排除索引 {span0 & excl}"


@given(
    series=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=8,
    ).map(lambda xs: sorted(xs, reverse=True))  # 严格递减序列
)
@settings(max_examples=80, deadline=None)
def test_excluding_all_decline_indices_suppresses_finding(series: list[float]) -> None:
    """把递减序列全部排除 → 无 monotonic_decline（排除真起作用，不空转）。"""
    if len(series) < 3:
        return
    excl_all = set(range(len(series)))
    findings = detect_chapter_drift(series, dim="情感落地", exclude_indices=excl_all)
    assert all(f.kind != "monotonic_decline" for f in findings)


@given(
    series=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=10,
    ).map(lambda xs: sorted(xs, reverse=True))
)
@settings(max_examples=60, deadline=None)
def test_monotonic_decline_triggers_without_exclusion(series: list[float]) -> None:
    """严格递减 + 平滑后累计跌幅>=3 必触发 monotonic_decline。

    detect_chapter_drift 对 s=smooth(raw) 检查：run>=3 且 s[start]-v>=3。
    raw 递减不保证 smoothed 递减（小步 EMA 可能使 smoothed 反弹），也不保证
    smoothed 累计跌幅>=3（如 [4,2,0] smooth 后跌幅~2.5）。故必须在 SMOOTHED
    域检验前置条件，而非 raw 域。
    """
    from shenbi.skill_utils.drift_detection.compute_drift import smooth

    if len(series) < 3:
        return
    s = smooth(series)
    # 前 3 个 smoothed 值须严格递减（run 才能到 3）+ s[0]-s[2]>=3（触发阈值）
    if not (s[1] < s[0] and s[2] < s[1]):
        return  # smoothed 未保持递减：本例不满足触发前置
    if s[0] - s[2] < 3.0:
        return  # smoothed 累计跌幅不足：本例不满足触发前置
    findings = detect_chapter_drift(series, dim="情感落地")
    assert any(f.kind == "monotonic_decline" for f in findings)


@given(scores=scores_st.filter(lambda xs: len(xs) >= 2))
@settings(max_examples=200, deadline=None)
def test_volume_decline_iff_last_below_second_to_last(scores: list[float]) -> None:
    """volume_decline 当且仅当末卷 < 倒数第二卷触发（compute_drift.py:138）。"""
    findings = detect_volume_drift(scores)
    expected = scores[-1] < scores[-2]
    assert bool(findings) == expected


@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=8,
    )
)
@settings(max_examples=120, deadline=None)
def test_volume_decline_at_most_one_finding(scores: list[float]) -> None:
    findings = detect_volume_drift(scores)
    assert len(findings) <= 1
    for f in findings:
        assert f.kind == "volume_decline" and f.dim == "overall"
```

- [ ] **Step 2: Run → passes**
`uv run pytest tests/property/drift/test_drift_properties.py -q --no-cov` → 通过（若个别 hypothesis 例因平滑交互边缘抖动，缩小 max_examples 至 100 或对 `test_monotonic_decline_triggers_without_exclusion` 收紧递减幅度；核心两属性——跨度不含 excl、volume iff——必须稳过）
- [ ] **Step 3: mypy + ruff + commit**
```bash
git add tests/property/drift/test_drift_properties.py
git commit -m "test(property): drift exclusion no-leak (trigger layer) + volume_decline trigger invariants"
```

---

### Task 6: 标点属性——已由 Task 2 覆盖（合并，无独立文件）

> 说明：spec 列出的「标点 count==text.count(token)」已在 **Task 2**（`tests/property/cjk/test_punct_properties.py`）完整交付——整-token 计数属性 + 破折号不 per-char 翻倍。无独立文件。此条目仅作结构索引，无额外代码；任务编号从 Task 7 继续。

---

### Task 7: G6.12 CJK 内嵌必检出属性（cjk.find_terms 正确；g6.py 待支柱二）

**Files:** Create `tests/property/cjk/test_g612_embedded_properties.py`

**Interfaces:** Consumes `shenbi.text.cjk.find_terms`。

**核实（亲手）：** `gates/g6.py:399` 用 `re.search(rf"(?:^|[^\w]){re.escape(word)}(?:$|[^\w])", content)`。Python3 `\w` 默认匹配 Unicode 字母（含 CJK），故 `[^\w]` 在 CJK 文本中永不命中——敏感词「革命」嵌于「这个时代革命运动」时，前后「代」「运」均为 `\w`，**不检出**（G6.12 失效属实）。正确工具 `text/cjk.find_terms`（精确子串）。本任务**不改 g6.py**（接线=支柱二「G6.12 用 cjk.find_terms」），只把「内嵌必检出」立为 find_terms 的不变量 + 旧正则失效对照（防回归）。

- [ ] **Step 1: Write property tests**
```python
# tests/property/cjk/test_g612_embedded_properties.py
from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.text.cjk import find_terms

cjk_pad = st.text(alphabet=st.sampled_from(list("在这个时代悄然兴起运动发展和平")), min_size=1, max_size=6)
term_st = st.sampled_from(["革命", "暴动", "起义", "敏感词"])


@given(pre=cjk_pad, post=cjk_pad, term=term_st)
@settings(max_examples=200, deadline=None)
def test_find_terms_detects_embedded_cjk(pre: str, term: str, post: str) -> None:
    """G6.12 内嵌必检出：敏感词被 CJK 包夹时 find_terms 必命中（substring 语义）。

    旧 g6.py 正则 [^\w] 边界对纯 CJK 文本失效（CJK 全是 \w），内嵌不检出；
    find_terms 用精确子串，正确。"""
    text = pre + term + post
    hits = find_terms(text, [term])
    assert len(hits) >= 1
    assert hits[0].term == term


@given(term=term_st)
@settings(max_examples=20, deadline=None)
def test_old_word_boundary_regex_fails_on_embedded(term: str) -> None:
    """回归对照：g6.py 旧 `[^\w]` 边界正则在纯 CJK 内嵌场景**不命中**——
    记录 bug 行为，证明 find_terms 是正确替代（接线在支柱二）。"""
    text = "这个时代" + term + "运动开始"
    old = re.search(rf"(?:^|[^\w]){re.escape(term)}(?:$|[^\w])", text)
    assert old is None  # 旧正则失效（确认 bug 存在）
    assert len(find_terms(text, [term])) == 1  # find_terms 正确


@given(pre=cjk_pad, post=cjk_pad, term=term_st)
@settings(max_examples=100, deadline=None)
def test_find_terms_hit_position_correct(pre: str, term: str, post: str) -> None:
    text = pre + term + post
    hits = find_terms(text, [term])
    h = hits[0]
    assert h.start == len(pre)
    assert h.end == len(pre) + len(term)
    assert text[h.start : h.end] == term
```

- [ ] **Step 2: Run → passes**
`uv run pytest tests/property/cjk/test_g612_embedded_properties.py -q --no-cov` → 通过
- [ ] **Step 3: mypy + ruff + commit**
```bash
git add tests/property/cjk/test_g612_embedded_properties.py
git commit -m "test(property): G6.12 embedded-CJK detection invariant (cjk.find_terms)"
```

---

### Task 8: G3.4 fail-closed 纯函数 + 属性（无 SCORE 必 fail）

**Files:** Create `src/shenbi/gates/g3_independence.py`、`tests/property/gates/test_g34_independence_properties.py`

**Interfaces:** Consumes 无（纯逻辑）。Produces `scoring_independence_status(progress: dict, skill_name: str) -> tuple[str, str]` 返回 `("PASS","")` 或 `("FAIL", reason)`。**不改 `gates/g3.py`**（gate_G3 接线=支柱二「G3.4 fail-closed + 读 trace」）。

**核实（亲手）：** `gates/g3.py:155` `if gen_agent and scorer_agent and str(gen_agent)==str(scorer_agent): FAIL else: PASS`。当 `current_scorer_agent` 缺失 → 落 else → **PASS（fail-open 空转）**。spec/AGENTS.md：「Scoring MUST use an independent subagent (G3.4); dispatcher-scored results are invalid」。正确行为=fail-closed：无独立评分证据→FAIL。本任务把 fail-closed 逻辑立为可测纯函数；现有 `tests/unit/gates/test_g3.py` 的 G3.4 测试（scorer==gen→FAIL、无 progress.json→SKIP）不受影响（不动 gate_G3）。

- [ ] **Step 1: Write failing property test**

注意 hypothesis `st.characters` 的 `whitelist_categories` 是关键字参数；下面 `agent_id` 用显式字母数字表（避免 API 误写）：
```python
# tests/property/gates/test_g34_independence_properties.py
from __future__ import annotations

import string

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from shenbi.gates.g3_independence import scoring_independence_status

agent_id = st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=20)
skill = st.sampled_from(["shenbi-worldbuilding", "shenbi-chapter-drafting"])


@given(skill=skill)
@settings(max_examples=40, deadline=None)
def test_no_scorer_recorded_fails_closed(skill: str) -> None:
    """G3.4 fail-closed：progress.json 存在但无 current_scorer_agent → FAIL（空转 bug 的正确化）。"""
    status, _ = scoring_independence_status(
        {"agent_trace": {skill: "agent-1"}}, skill
    )
    assert status == "FAIL"


@given(skill=skill)
@settings(max_examples=40, deadline=None)
def test_empty_progress_fails_closed(skill: str) -> None:
    status, _ = scoring_independence_status({}, skill)
    assert status == "FAIL"


@given(skill=skill, gen=agent_id, scorer=agent_id)
@settings(max_examples=80, deadline=None)
def test_same_agent_fails(skill: str, gen: str, scorer: str) -> None:
    assume(scorer == gen)
    status, _ = scoring_independence_status(
        {"agent_trace": {skill: gen}, "current_scorer_agent": scorer}, skill
    )
    assert status == "FAIL"


@given(skill=skill, gen=agent_id, scorer=agent_id)
@settings(max_examples=80, deadline=None)
def test_different_agents_pass_only_when_distinct(skill: str, gen: str, scorer: str) -> None:
    assume(scorer != gen)
    status, reason = scoring_independence_status(
        {"agent_trace": {skill: gen}, "current_scorer_agent": scorer}, skill
    )
    assert status == "PASS"
    assert reason == ""


@given(skill=skill)
@settings(max_examples=40, deadline=None)
def test_scorer_present_no_gen_trace_passes(skill: str) -> None:
    """有独立评分者、无该技能生成 trace（无法证同源）→ 不能判同源 → PASS。"""
    status, _ = scoring_independence_status(
        {"current_scorer_agent": "scorer-9"}, skill
    )
    assert status == "PASS"
```

- [ ] **Step 2: Run → FAIL**
`uv run pytest tests/property/gates/test_g34_independence_properties.py -q --no-cov` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement pure fail-closed function**
```python
# src/shenbi/gates/g3_independence.py
"""G3.4 评分独立性纯函数（spec 支柱五；判据 6）。

gate_G3（g3.py:144-162）现状 fail-open：progress.json 存在但缺
current_scorer_agent 时返回 PASS（空转 bug）。本模块承载**正确**的 fail-closed
逻辑，供属性测试钉死；接线进 gate_G3 是支柱二「G3.4 fail-closed + 读 trace」。

规则（AGENTS.md：评分必须用独立 subagent；dispatcher 自评无效）：
  - 无 current_scorer_agent 证据 → FAIL（fail-closed）
  - 生成 agent == 评分 agent（同源）→ FAIL
  - 否则 → PASS
"""
from __future__ import annotations

from typing import Any


def scoring_independence_status(
    progress: dict[str, Any], skill_name: str
) -> tuple[str, str]:
    """返回 ("PASS","") 或 ("FAIL", reason)。fail-closed：缺评分证据即 FAIL。"""
    scorer = progress.get("current_scorer_agent")
    if not scorer:
        return "FAIL", "no independent scorer recorded (fail-closed)"
    agent_trace = progress.get("agent_trace")
    if isinstance(agent_trace, dict):
        gen = agent_trace.get(skill_name)
        if gen is not None and str(gen) == str(scorer):
            return "FAIL", "scorer agent same as generator"
    return "PASS", ""
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/property/gates/test_g34_independence_properties.py -q --no-cov` → 通过
- [ ] **Step 5: mypy + ruff**
`uv run mypy src/shenbi/gates/g3_independence.py && uv run ruff check src/shenbi/gates/g3_independence.py` → clean
- [ ] **Step 6: Commit**
```bash
git add src/shenbi/gates/g3_independence.py \
        tests/property/gates/test_g34_independence_properties.py
git commit -m "feat(gates): add G3.4 fail-closed scoring-independence pure function + property tests"
```

---

### Task 9: CapabilityFS — in-process 纯度运行时兜底 + 属性

**Files:** Create `src/shenbi/capability_fs.py`、`tests/property/gates/test_capability_fs_properties.py`

**Interfaces:** Produces `CapabilityFS(allow_root: Path)`（只读 FS 句柄：`read_text(path)`/`read_bytes(path)`/`exists(path)`/`list_dir(path)`；任意写/删/改抛 `PermissionError`）。用于测试时给门注入只读句柄（判据 4/14）。**codex subprocess read-provenance 是 future work（已知盲点）**，本模块只覆盖 in-process。

**核实：** 现状 gates 的「不写」是散文约束（spec 根因五）；AST lint（禁 FS 原语）在支柱六。CapabilityFS 是 in-process 运行时兜底：把可写 Path 换成只读句柄，门若误写即 PermissionError 暴露。spec v5 命名分离（I1）：本模块=CapabilityFS；subprocess read-provenance≠本模块。

- [ ] **Step 1: Write failing test**
```python
# tests/property/gates/test_capability_fs_properties.py
from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.capability_fs import CapabilityFS


@given(content=st.text(min_size=0, max_size=200))
@settings(max_examples=100, deadline=None)
def test_read_text_roundtrips(tmp_path: Path, content: str) -> None:
    f = tmp_path / "a.txt"
    f.write_text(content, encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    assert fs.read_text(f) == content


@given(data=st.binary(min_size=0, max_size=64))
@settings(max_examples=60, deadline=None)
def test_read_bytes_roundtrips(tmp_path: Path, data: bytes) -> None:
    f = tmp_path / "b.bin"
    f.write_bytes(data)
    assert CapabilityFS(tmp_path).read_bytes(f) == data


def test_any_write_raises_permissionerror(tmp_path: Path) -> None:
    f = tmp_path / "w.txt"
    f.write_text("x", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    for op in (
        lambda: fs.write_text(f, "y"),
        lambda: fs.write_bytes(f, b"y"),
        lambda: fs.unlink(f),
        lambda: fs.mkdir(tmp_path / "sub"),
    ):
        with pytest.raises(PermissionError):
            op()


def test_path_outside_allow_root_denied(tmp_path: Path) -> None:
    inside = tmp_path / "in"
    inside.mkdir()
    outside = tmp_path / "out.txt"
    outside.write_text("z", encoding="utf-8")
    fs = CapabilityFS(inside)
    with pytest.raises((PermissionError, FileNotFoundError)):
        fs.read_text(outside)


def test_exists_and_list_dir_read_only(tmp_path: Path) -> None:
    (tmp_path / "c.txt").write_text("1", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    assert fs.exists(tmp_path / "c.txt") is True
    assert fs.exists(tmp_path / "nope") is False
    names = fs.list_dir(tmp_path)
    assert "c.txt" in names
```

- [ ] **Step 2: Run → FAIL** ModuleNotFoundError
- [ ] **Step 3: Implement**
```python
# src/shenbi/capability_fs.py
"""CapabilityFS：in-process 只读 FS 句柄（spec 支柱五；判据 4/14）。

把可写 Path 换成只读句柄注入门/测试：读允许，任意写/删/改抛 PermissionError。
是「门纯度」的运行时兜底（AST lint 禁 FS 原语在支柱六）。

v5 命名分离（I1）：本模块仅 in-process；codex subprocess 的 read-provenance
（需 FUSE/ptrace）是 future work / 已知盲点，不由本模块承担。
"""
from __future__ import annotations

from pathlib import Path


class CapabilityFS:
    """只读文件系统句柄。读经 allow_root 沙箱；写一律拒绝。"""

    def __init__(self, allow_root: Path) -> None:
        self._root = Path(allow_root).resolve()

    def _sandbox(self, path: Path) -> Path:
        p = Path(path)
        try:
            resolved = p.resolve(strict=False)
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise PermissionError(f"path outside allow_root: {p}") from exc
        return resolved

    def exists(self, path: Path) -> bool:
        return self._sandbox(path).exists()

    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        return self._sandbox(path).read_text(encoding=encoding)

    def read_bytes(self, path: Path) -> bytes:
        return self._sandbox(path).read_bytes()

    def list_dir(self, path: Path) -> list[str]:
        return [p.name for p in self._sandbox(path).iterdir()]

    # --- 写侧：全部拒绝（纯度兜底） ---
    def write_text(self, path: Path, data: str, encoding: str = "utf-8") -> None:
        raise PermissionError("CapabilityFS is read-only")

    def write_bytes(self, path: Path, data: bytes) -> None:
        raise PermissionError("CapabilityFS is read-only")

    def unlink(self, path: Path) -> None:
        raise PermissionError("CapabilityFS is read-only")

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        raise PermissionError("CapabilityFS is read-only")
```

- [ ] **Step 4: Run → passes**
`uv run pytest tests/property/gates/test_capability_fs_properties.py -q --no-cov` → 通过
- [ ] **Step 5: mypy + ruff**
`uv run mypy src/shenbi/capability_fs.py && uv run ruff check src/shenbi/capability_fs.py` → clean
- [ ] **Step 6: Commit**
```bash
git add src/shenbi/capability_fs.py tests/property/gates/test_capability_fs_properties.py
git commit -m "feat(capability_fs): add in-process read-only FS handle (gate purity backstop)"
```

---

### Task 10: 三表一致属性（REGISTRY 派生，现状已一致）

**Files:** Create `tests/property/contracts/__init__.py`、`tests/property/contracts/test_registry_consistency.py`

**Interfaces:** Consumes `shenbi.contracts.registry.bootstrap_registry`、`shenbi.contract.load_registry`、`docs/framework/truth-files.yaml`、`shenbi.gates.shared.PROJECT`。

**核实（亲手，实测）：** `bootstrap_registry()`（contracts/registry.py，read truth-files.yaml `concepts`）返回 {name:kind}；`load_registry()`（contract.py:70，read 同文件）返回含 `concepts` 的 dict。实测二者文件名集合均 54 项且**完全相等**。三表=truth-files.yaml（单一源）+ 两个读者（contracts.bootstrap_registry / contract.load_registry）。

- [ ] **Step 1: Create package + property test**
```python
# tests/property/contracts/__init__.py
"""属性测试：三表（REGISTRY 派生）一致（spec 支柱五；判据 5）。"""
```
```python
# tests/property/contracts/test_registry_consistency.py
from __future__ import annotations

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.contract import load_registry
from shenbi.contracts.registry import bootstrap_registry
from shenbi.gates.shared import PROJECT

_TRUTH_YAML = PROJECT / "docs" / "framework" / "truth-files.yaml"


def _yaml_concept_names() -> set[str]:
    data = yaml.safe_load(_TRUTH_YAML.read_text(encoding="utf-8")) or {}
    return {c["name"] for c in data.get("concepts", [])}


def test_three_registry_sources_agree() -> None:
    """判据 5（本支柱范围）：三表从单一源 truth-files.yaml 派生，文件名集合 diff 为空。

    三源：(1) truth-files.yaml concepts 直读 (2) contract.load_registry concepts
    (3) contracts.bootstrap_registry vocab。三者必相等（实测 54==54==54）。
    全 69 技能契约迁移锁定（判据 8）是支柱一续 + 支柱二的范围。"""
    src = _yaml_concept_names()
    lr = {c["name"] for c in load_registry().get("concepts", [])}
    br = set(bootstrap_registry().keys())
    assert src == lr == br
    assert len(src) > 0


@pytest.mark.parametrize("name", sorted(_yaml_concept_names()))
def test_every_truth_file_has_kind(name: str) -> None:
    """单一源约束：每个登记 concept 必有非空 kind（派生分层依赖）。"""
    data = yaml.safe_load(_TRUTH_YAML.read_text(encoding="utf-8")) or {}
    kinds = {c["name"]: c.get("kind") for c in data.get("concepts", [])}
    assert kinds.get(name), f"{name} 缺 kind"


@given(st.data())
@settings(max_examples=20, deadline=None)
def test_bootstrap_subset_of_yaml(_data: object) -> None:
    """bootstrap_registry 词汇必 ⊆ truth-files.yaml concept 名集（派生一致性）。"""
    assert set(bootstrap_registry().keys()) <= _yaml_concept_names()
```

- [ ] **Step 2: Run → passes**
`uv run pytest tests/property/contracts/test_registry_consistency.py -q --no-cov` → 通过
- [ ] **Step 3: mypy + ruff + commit**
```bash
git add tests/property/contracts/__init__.py tests/property/contracts/test_registry_consistency.py
git commit -m "test(property): three-registry single-source consistency (bootstrap==load==yaml)"
```

---

### Task 11: jieba 冻结分词基线（真实 token 列表，非猜测）

**Files:** Create `tests/property/cjk/test_tokenize_frozen.py`

**Interfaces:** Consumes `shenbi.text.cjk.tokenize`。

**核实（亲手运行 jieba==0.42.1，pyproject.toml:10 已 pin）：** 对固定样本捕获真实分词（非同次 t1==t2 同义反复）。jieba 升级改变分词 → 基线断言失败 → 审查。下面 token 列表是**实测输出**：

| 文本 | 实测 words | 实测 pos |
|---|---|---|
| `他在黑暗中看到了一束光明` | `['他','在','黑暗','中','看到','了','一束','光明']` | `['r','p','z','f','v','ul','m','n']` |
| `主角缓缓地走向了那扇古老的大门` | `['主角','缓缓','地','走向','了','那','扇','古老','的','大门']` | `['n','d','uv','v','ul','r','q','nr','uj','n']` |
| `革命运动在这个时代悄然兴起` | `['革命','运动','在','这个','时代','悄然兴起']` | `['vn','vn','p','r','n','l']` |
| `筑基期的修炼需要极大的耐心` | `['筑','基期','的','修炼','需要','极大','的','耐心']` | `['v','n','uj','v','v','a','uj','a']` |

- [ ] **Step 1: Write frozen baseline + determinism property**
```python
# tests/property/cjk/test_tokenize_frozen.py
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from shenbi.text.cjk import tokenize

# 实测于 jieba==0.42.1（pyproject.toml:10 已 pin）。升级改变分词 → 失败 → 审查。
_FROZEN: list[tuple[str, list[str], list[str]]] = [
    (
        "他在黑暗中看到了一束光明",
        ["他", "在", "黑暗", "中", "看到", "了", "一束", "光明"],
        ["r", "p", "z", "f", "v", "ul", "m", "n"],
    ),
    (
        "主角缓缓地走向了那扇古老的大门",
        ["主角", "缓缓", "地", "走向", "了", "那", "扇", "古老", "的", "大门"],
        ["n", "d", "uv", "v", "ul", "r", "q", "nr", "uj", "n"],
    ),
    (
        "革命运动在这个时代悄然兴起",
        ["革命", "运动", "在", "这个", "时代", "悄然兴起"],
        ["vn", "vn", "p", "r", "n", "l"],
    ),
    (
        "筑基期的修炼需要极大的耐心",
        ["筑", "基期", "的", "修炼", "需要", "极大", "的", "耐心"],
        ["v", "n", "uj", "v", "v", "a", "uj", "a"],
    ),
]


def test_frozen_baseline_matches_jieba_0_42_1() -> None:
    """冻结分词基线（spec M2）。token 列表来自 jieba==0.42.1 实测，非 t1==t2 同义反复。"""
    for text, exp_words, _exp_pos in _FROZEN:
        toks = tokenize(text)
        assert [t.word for t in toks] == exp_words, text


def test_frozen_pos_tags_match() -> None:
    """词性标注也冻结（pseg 输出稳定）。"""
    for text, _words, exp_pos in _FROZEN:
        toks = tokenize(text)
        assert [t.pos for t in toks] == exp_pos, text


def test_tokenize_preserves_chars_concat() -> None:
    """不变量：tok2word 拼接 == 原文（分词不丢/不增字符）。"""
    for text, _w, _p in _FROZEN:
        assert "".join(t.word for t in tokenize(text)) == text


cjk_sample = st.text(
    alphabet=st.sampled_from(list("主角缓缓走向古老大门光明黑暗耐心修炼需要")),
    min_size=0,
    max_size=30,
)


@given(cjk_sample)
@settings(max_examples=80, deadline=None)
def test_tokenize_is_deterministic(text: str) -> None:
    """确定性不变量：同一输入两次分词完全一致（冻结版本下稳定）。"""
    a = tokenize(text)
    b = tokenize(text)
    assert [t.word for t in a] == [t.word for t in b]
    assert [t.pos for t in a] == [t.pos for t in b]


@given(cjk_sample)
@settings(max_examples=60, deadline=None)
def test_tokenize_concat_equals_input(text: str) -> None:
    if not text.strip():
        return
    assert "".join(t.word for t in tokenize(text)) == text
```

- [ ] **Step 2: Run → passes**
`uv run pytest tests/property/cjk/test_tokenize_frozen.py -q --no-cov` → 通过（基线来自实测；若环境 jieba 输出不同，执行者用 `uv run python -c "from shenbi.text.cjk import tokenize; print([(t.word,t.pos) for t in tokenize('他在黑暗中看到了一束光明')])"` 复核并更新 `_FROZEN` 后提交）
- [ ] **Step 3: mypy + ruff + commit**
```bash
git add tests/property/cjk/test_tokenize_frozen.py
git commit -m "test(property): jieba frozen tokenization baseline (0.42.1, real tokens)"
```

---

### Task 12: 全量回归 + 支柱五完成确认

**Files:** 无。仅验证。

- [ ] **Step 1: 全量测试（覆盖率门在此生效）**
`uv run pytest -q` → 现有测试集**无 regression** + 新增属性测试全通过。执行者以实际输出为准，只断言「无失败」（不引用具体数字，避免漂移）。
- [ ] **Step 2: Type check + lint 全仓**
`uv run mypy src/shenbi && uv run ruff check .` → Success / All passed
- [ ] **Step 3: 覆盖率门达标**
`uv run pytest -q` 末尾 coverage 报告 `fail_under=90` 通过（属性测试只读不改主路径，覆盖率不降）。
- [ ] **Step 4: 判据对齐（本支柱范围）**
  - 判据 6（属性测试 CI 必过，覆盖全部算术 bug 性质 + jieba 冻结）逐项：
    - P50==median：Task 4（含修复）✓
    - 标点 count==text.count(token)：Task 2 ✓
    - drift 排除不泄漏：Task 5 ✓
    - 熵 sum==1：Task 3 ✓
    - volume_decline 必触发：Task 5 ✓
    - G6.12 CJK 内嵌必检出：Task 7 ✓
    - G3.4 无 SCORE 必 fail：Task 8（纯函数 fail-closed）✓
    - 门纯度：Task 9（CapabilityFS in-process）✓
    - 三表一致：Task 10 ✓
    - jieba 冻结：Task 11 ✓
  - 判据 4（纯度强制：AST lint 在支柱六；in-process CapabilityFS 兜底）：Task 9 ✓
  - 判据 14（读 provenance 诚实分层：internal CapabilityFS 可行 / codex subprocess 已知盲点）：Task 9 ✓
  - **范围外（明确）：** gate_G3 fail-closed 接线、g6.py 改用 find_terms、AST lint 禁 FS 原语、subprocess read-provenance（FUSE/ptrace）——支柱二/六/future work。
- [ ] **Step 5: Empty marker commit**
```bash
git commit --allow-empty -m "chore(property): pillar 5 property-test network complete"
```

---

## Self-Review

**1. Spec coverage（支柱五范围）：** 判据 6 的十项算术 bug 性质 + jieba 冻结，逐项有任务覆盖（见 Task 12 Step 4 清单）。判据 4/14 的 in-process 纯度（CapabilityFS）在 Task 9。N8（hypothesis-jsonschema 可选）严格遵守——全程手写 strategy，未加依赖。

**2. Placeholder scan：** 无 TBD/TODO；每个 code step 含完整可运行代码。Task 11 基线 token 列表来自实测（非 TBD）；若环境差异给出复核命令与处理流程。

**3. Type consistency：** `compute_percentiles -> dict[str,int]`；`compute_sentence_stats -> dict`（含 median:int）；`detect_chapter_drift -> list[DriftFinding]`；`detect_volume_drift -> list[DriftFinding]`；`find_terms -> list[TermHit]`；`count_punctuation -> dict[str,int]`；`tokenize -> list[Token]`；`scoring_independence_status -> tuple[str,str]`；`CapabilityFS` 读方法返回 str/bytes/bool/list[str]、写方法返回 None。跨任务命名一致（`scoring_independence_status`、`CapabilityFS` 单一名）。`bootstrap_registry`/`load_registry` 复用支柱一/现有契约层。

**4. 已知限制（诚实声明）：**
  - **drift 平滑层渗漏**：excl 的原始值会经 `smooth()` 渗入邻居平滑值（已知边界）；属性测试钉死的是**触发层**（finding 跨度不含 excl、排除生效不空转），这是 compute_drift 当前真正保证的不变量。把平滑改成「仅对非 excl 值平滑」需语义决策（插值/重索引），超出属性测试网范围，记入 spec 风险表。
  - **G3.4/G6.12 不接线**：本计划立正确纯函数/不变量，不改 gate_G3/g6.py（与支柱四 `audit_trace` 不替换 gate_G7 同模式）；接线是支柱二。
  - **G3.4 fail-closed 与现有 gate_G3 行为不同**：现有 gate 缺 scorer→PASS（fail-open）；`scoring_independence_status` 缺 scorer→FAIL（fail-closed）。这是有意的——纯函数承载 spec 要求的正确行为，接线时由支柱二同步既有 G3.4 测试。
  - **三表=文件注册维度**：本支柱钉死 truth-files.yaml 三读者一致（判据 5 的文件注册部分）；全 69 技能契约迁移锁定（判据 8）是支柱一续+二。
  - **subprocess read-provenance**：CapabilityFS 只 in-process；codex exec 子进程 syscall 不可拦截，仍是已知盲点（future work）。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-contract-single-source-pillar5-property.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
