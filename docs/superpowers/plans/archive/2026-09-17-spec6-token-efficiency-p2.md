# Spec #6 Token 效率 P2（终版范围）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec #6 阶段 3 终裁范围——T_A system prompt 字节稳定回归测试 + T_C 两个 skill（chapter-pattern / pacing-design）教学段外置瘦身；T_B（缓存）与 T_D（IDE 分离强形态）已裁决不实施（T_D：codex CLI 无 `--system-prompt` flag，openai/codex#11588 仍为 open feature request，本机无真 CLI 可实测）。

**Architecture:** 全部改动为「测试 + SKILL.md body 编辑 + 各 skill 目录内新增维护者参考文件」。零 `src/shenbi/` 生产代码改动（dispatcher 只注入 `SKILL.md`，同目录其他文件天然不注入——`anti-ai-reference.md`/`era-reference.md`/`truth-files-reference.md` 三先例）。外置文件以裸文件名在 body 引用（`lint_contract_prose.py:186` branch-b 的 `skills_root.glob(f"*/{base}")` 存在性检查构成 dead-link 机械防护）。验收全离线：测试内构建 `_build_skill_prompt` 量 system prompt 字符数 + `estimate_prompt_tokens` 估算 token。

**Tech Stack:** pytest（tests/pipeline/ 层，T1）、`shenbi.pipeline.dispatch_helper._build_skill_prompt`、`shenbi.cost.estimate.estimate_prompt_tokens`、`just check`。

## Global Constraints

- **环境**：本机 `/usr/bin/git` 被 Xcode license 拦截——git 一律用 `/Library/Developer/CommandLineTools/usr/bin/git`，命令前缀 `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH`；测试走 `uv run pytest`（与 CI `uv run --frozen` 同构）。
- **度量单位**：测试断言用**字符数**（`len()`，与 `_build_skill_prompt` 产出一致）与 `estimate_prompt_tokens`；字节换算记录进验收证据。spec §3.5 的原 741B/723B 净省估算按 146B 引用行预算（不含必需的 H2/H3 标题锚）——plan 审查实测锚块 198B/237B，spec 下限已随 plan 修订为字符/est 双口径（≥450/≥140 与 ≥280/≥130）。
- **Pre-slim 基线常量**（2026-09-17 于 branch f64d13c5 实测，已固化进测试）：chapter-pattern system prompt = 7,629 字符 / 2,681 估算 token；pacing-design = 6,829 字符 / 2,511 估算 token。
- **不可触碰不变量**（spec §3.7）：DOT flowchart、`## Anti-Rationalization` 表、frontmatter 契约、输出契约段（chapter-pattern 的 13×13 矩阵 / `### 熵评级阈值` / `### 熵计算公式输入文档化要求`；pacing 的 `## 输出格式` EXACT 模板与 `### 单调性检测阈值`）。
- **引用行**：裸文件名（禁斜杠路径）、诚实表述（禁"本章已提供"类伪陈述）。
- **提交**：conventional commits（`test:` / `perf:`，perf 有先例 PR #153）；pathspec 显式列文件，禁 `git add -A`。
- **每个 task commit 后**：全量 fresh-context 重审产出 `.superpowers/sdd/audit-T<N>.md`（SDD 阶段 6 规则，执行期由协调者调度）。

---

### Task 1: T_A — system prompt 字节稳定回归测试

**Files:**
- Create: `tests/pipeline/test_dispatch_helper_system_stability.py`

**Interfaces:**
- Consumes: `_build_skill_prompt(skill, project_dir, prompt, chapter, ...) -> tuple[str, str, list[str]]`（`src/shenbi/pipeline/dispatch_helper.py:601`）；`_strip_autogen_blocks(text) -> str`（:201）
- Produces: 无下游依赖（纯回归护栏，固化"同 skill 两次构建 system prompt 字节相等"隐式契约——API 路径 provider cache 命中的前提）

- [ ] **Step 1: 写测试**

```python
"""Spec #6 T_A: system prompt byte-stability regression (offline).

Fixes the implicit contract that the system prompt for a given skill is
byte-identical across consecutive _build_skill_prompt calls. The API
path relies on a stable system prefix for provider prompt-cache hits;
_strip_autogen_blocks must stay deterministic (pure regex, no
timestamps/random) for that to hold.
"""

from pathlib import Path

import pytest

from shenbi.pipeline.dispatch_helper import _build_skill_prompt

STABILITY_SKILLS = (
    "shenbi-chapter-pattern",
    "shenbi-review-resonance",
    "shenbi-state-settling",
)


@pytest.mark.parametrize("skill", STABILITY_SKILLS)
def test_system_prompt_byte_stable_across_calls(tmp_path: Path, skill: str) -> None:
    sys1, _, _ = _build_skill_prompt(skill, tmp_path, "prompt A", 1)
    sys2, _, _ = _build_skill_prompt(skill, tmp_path, "prompt B", 2)
    assert sys1 == sys2
```
（strip 确定性由参数化字节稳定测试传递性覆盖，不设同义反复的单测——plan 审查 M3）

- [ ] **Step 2: 跑测试确认通过**

Run: `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH uv run pytest tests/pipeline/test_dispatch_helper_system_stability.py -v`
Expected: 3 passed（当前实现已字节稳定——本测试是固化护栏，非修 bug，故直接绿）

- [ ] **Step 3: just check 全量**

Run: `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH just check`
Expected: EXIT=0

- [ ] **Step 4: Commit**

```bash
G=/Library/Developer/CommandLineTools/usr/bin/git
$G add tests/pipeline/test_dispatch_helper_system_stability.py
$G commit -m "test: spec6 T_A — system prompt byte-stability regression

Fixes the implicit contract that consecutive _build_skill_prompt calls
yield byte-identical system prompts (provider prompt-cache prefix
stability on the API path). Covers three heavy skills."
```

---

### Task 2: T_C-1 — chapter-pattern 熵教学段外置

**Files:**
- Modify: `skills/shenbi-chapter-pattern/SKILL.md:296-332`（删 `## 熵计算公式` 的公式+算例子段，换锚点节；`:334` 起的 `### 熵评级阈值` 与 `:344+` 文档化要求**逐字不动**——:333 为空行，保留锚点块与 `### 熵评级阈值` 之间恰好一个空行）
- Create: `skills/shenbi-chapter-pattern/chapter-pattern-reference.md`（被移内容的 verbatim 归档 + 维护者注记头）
- Create: `tests/pipeline/test_spec6_prompt_slimming.py`

**Interfaces:**
- Consumes: Task 1 无依赖；`_build_skill_prompt`、`estimate_prompt_tokens`
- Produces: `chapter-pattern-reference.md`（维护者参考，无代码消费者）；测试常量与断言形态（Task 3 复用文件扩展 pacing 用例）

- [ ] **Step 1: 写失败测试**

```python
"""Spec #6 T_C: externalized-teaching-block slimming assertions (offline).

Pre-slim baselines measured 2026-09-17 on branch f64d13c5 via
_build_skill_prompt (chars via len(); tokens via estimate_prompt_tokens).
Spec §3.5's 887B/869B figures are UTF-8 BYTES — different unit, both
recorded in acceptance evidence.
"""

from pathlib import Path

from shenbi.cost.estimate import estimate_prompt_tokens
from shenbi.pipeline.dispatch_helper import _build_skill_prompt

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"

# Pre-slim constants (captured before externalization, branch f64d13c5)
PRE_LEN_CHAPTER_PATTERN = 7629
PRE_EST_CHAPTER_PATTERN = 2681


def _system_prompt(skill: str, tmp_path: Path) -> str:
    system, _, _ = _build_skill_prompt(skill, tmp_path, "measure", 1)
    return system


def test_chapter_pattern_slimmed(tmp_path: Path) -> None:
    system = _system_prompt("shenbi-chapter-pattern", tmp_path)

    # net char drop: removed 627 chars, anchor block 104 chars (plan-review simulated)
    assert PRE_LEN_CHAPTER_PATTERN - len(system) >= 450
    # estimated-token drop (simulated 159, threshold with margin)
    assert estimate_prompt_tokens(system) <= PRE_EST_CHAPTER_PATTERN - 140

    # externalized file exists + bare-filename reference line in body
    ref = SKILLS_DIR / "shenbi-chapter-pattern" / "chapter-pattern-reference.md"
    assert ref.is_file()
    body = (SKILLS_DIR / "shenbi-chapter-pattern" / "SKILL.md").read_text(encoding="utf-8")
    assert "`chapter-pattern-reference.md`" in body

    # runtime sections kept inline (invariants)
    assert "### 熵评级阈值" in body
    assert "### 熵计算公式输入文档化要求" in body

    # moved teaching markers no longer in the system prompt
    assert "H = -Σ(p_i × log₂(p_i))" not in system
    assert "假设模式分布为" not in system
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH uv run pytest tests/pipeline/test_spec6_prompt_slimming.py -v`
Expected: FAIL（`PRE_LEN - len(system) >= 450` 断言失败——尚未瘦身，drop = 0）

- [ ] **Step 3: 建参考文件** `skills/shenbi-chapter-pattern/chapter-pattern-reference.md`

内容 = 维护者注记头 + 被移段 verbatim：

````markdown
# chapter-pattern 维护者参考：香农熵公式与算例

> 本文件面向 skill 作者/维护者，运行时**不注入** dispatch prompt（T_C 外置，spec #6）。
> 熵计算结果由框架 Helper Precompute 代算（`src/shenbi/skill_utils/chapter_pattern/compute_pattern.py`
> 逐行输出 frequency/p_log2p）；运行时所需的评级阈值与输入文档化要求保留在 SKILL.md。

## 熵计算公式

### 香农熵计算

对最近 N 章的模式分布计算香农熵：

```
H = -Σ(p_i × log₂(p_i))

其中:
- p_i = 模式 i 在最近 N 章中出现的频率（出现次数 / N）
- 求和范围: 13 种模式中实际出现的所有模式
- log₂ 以 2 为底
```

### 计算示例

```markdown
## 熵计算示例（最近 10 章）

假设模式分布为:
- 升级: 3次 (p=0.3)
- 日常: 2次 (p=0.2)
- 转折: 2次 (p=0.2)
- 引入: 1次 (p=0.1)
- 揭示: 1次 (p=0.1)
- 沉淀: 1次 (p=0.1)
- 其他 7 种: 0次

H = -(0.3×log₂(0.3) + 0.2×log₂(0.2) + 0.2×log₂(0.2) + 0.1×log₂(0.1) + 0.1×log₂(0.1) + 0.1×log₂(0.1))
  = -(0.3×(-1.737) + 0.2×(-2.322) + 0.2×(-2.322) + 0.1×(-3.322) + 0.1×(-3.322) + 0.1×(-3.322))
  = -(-0.521 + -0.464 + -0.464 + -0.332 + -0.332 + -0.332)
  = -(-2.446)
  = 2.446

评级: 健康（2.0 < H ≤ 2.5）
```
````

- [ ] **Step 4: 编辑 SKILL.md** —— 将 `:296-332`（从 `## 熵计算公式` 行到 `### 计算示例` 代码块收尾的 ```` ``` ```` 行，即 `### 熵评级阈值` 之前的全部内容）替换为：

````markdown
## 熵计算

香农熵公式与算例见维护者参考 `chapter-pattern-reference.md`（运行时不注入；计算由 Helper Precompute 代算，评级阈值与文档化要求见下）。
````

`### 熵评级阈值` 起的全部后续内容**逐字不动**（`## 模式转移矩阵` 等更早内容也不动）。

- [ ] **Step 5: 跑测试确认通过**

Run: `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH uv run pytest tests/pipeline/test_spec6_prompt_slimming.py tests/pipeline/test_dispatch_helper_system_stability.py -v`
Expected: all passed

- [ ] **Step 6: 暂存后 just check 全量（contract-prose R1/R2 + registry R1 是实际防护面）**

justfile 的幂等 diff 门（`git diff --exit-code -- ... skills/ ...`）比较工作树与索引——**必须先暂存**三个文件再跑 check，否则未暂存的 SKILL.md 编辑会让该门误红（plan 审查 I2）：

```bash
G=/Library/Developer/CommandLineTools/usr/bin/git
$G add skills/shenbi-chapter-pattern/SKILL.md skills/shenbi-chapter-pattern/chapter-pattern-reference.md tests/pipeline/test_spec6_prompt_slimming.py
PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH just check
```
Expected: EXIT=0

- [ ] **Step 7: Commit**

```bash
G=/Library/Developer/CommandLineTools/usr/bin/git
$G commit -m "perf: spec6 T_C — externalize chapter-pattern entropy teaching block

Move Shannon-entropy formula + worked example (627 chars) to maintainer
reference chapter-pattern-reference.md (never injected at runtime,
anti-ai-reference.md precedent); keep entropy rating thresholds and
input-documentation requirements inline (runtime invariants). Net
system-prompt drop asserted >=450 chars / >=140 est-tokens offline."
```

---

### Task 3: T_C-2 — pacing-design 教学节外置

**Files:**
- Modify: `skills/shenbi-pacing-design/SKILL.md:84-110`（删 `### 2. 三线比例` 与 `### 3. 场景类型` 两教学节（含 :110 空行），换指针节，指针节与 `### 4.` 之间保留恰好一个空行；`### 4. 单调性检测阈值` 改号为 `### 3.`，内容逐字不动；`## 输出格式` 起全部不动）
- Create: `skills/shenbi-pacing-design/pacing-design-reference.md`
- Modify: `tests/pipeline/test_spec6_prompt_slimming.py`（追加 pacing 用例）

**Interfaces:**
- Consumes: Task 2 的测试文件结构（`_system_prompt` helper、常量段）
- Produces: `pacing-design-reference.md`（维护者参考，无代码消费者）

- [ ] **Step 1: 追加失败测试**（在 `tests/pipeline/test_spec6_prompt_slimming.py` 常量段与用例后追加）

```python
PRE_LEN_PACING = 6829
PRE_EST_PACING = 2511


def test_pacing_design_slimmed(tmp_path: Path) -> None:
    system = _system_prompt("shenbi-pacing-design", tmp_path)

    # net char drop: removed 481 chars, pointer block 111 chars (plan-review simulated)
    assert PRE_LEN_PACING - len(system) >= 280
    # estimated-token drop (simulated 146, threshold with margin)
    assert estimate_prompt_tokens(system) <= PRE_EST_PACING - 130

    ref = SKILLS_DIR / "shenbi-pacing-design" / "pacing-design-reference.md"
    assert ref.is_file()
    body = (SKILLS_DIR / "shenbi-pacing-design" / "SKILL.md").read_text(encoding="utf-8")
    assert "`pacing-design-reference.md`" in body

    # runtime invariants kept inline
    assert "单调性检测阈值" in body
    assert "## 输出格式" in body
    assert "EXACT 节标题" in body

    # moved teaching markers no longer in the system prompt
    assert "太多=流水账" not in system
    assert "每卷使用全部类型" not in system
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH uv run pytest tests/pipeline/test_spec6_prompt_slimming.py -v`
Expected: `test_pacing_design_slimmed` FAIL（drop = 0），`test_chapter_pattern_slimmed` PASS

- [ ] **Step 3: 建参考文件** `skills/shenbi-pacing-design/pacing-design-reference.md`

内容 = 维护者注记头 + 被移两节 verbatim：

````markdown
# pacing-design 维护者参考：三线比例与场景类型

> 本文件面向 skill 作者/维护者，运行时**不注入** dispatch prompt（T_C 外置，spec #6）。
> 运行时所需的输出骨架（三线目标比值表、场景类型表）已完整内含于 SKILL.md 的 `## 输出格式` EXACT 模板。

### 2. 三线比例

| 线 | 含义 | 典型比例 | 失衡后果 |
|----|------|---------|---------|
| QUEST | 任务/冒险/主线推进 | 50-60% | 太多=流水账；太少=停滞 |
| FIRE | 关系/情感/羁绊 | 25-35% | 太多=恋爱脑；太少=冷血 |
| CONSTELLATION | 世界观/设定/智斗 | 见下方「目标比值（按卷型）」表 | 太多=说教；太少=扁平 |

比例可随卷调整：开卷 CONSTELLATION 偏高铺垫，情感卷 FIRE 偏高。

### 3. 场景类型

定义 6-12 种场景类型：

| 类型 | 标志 |
|------|------|
| 战斗 | 高强度冲突 |
| 对话 | 信息/情感交流 |
| 日常 | 角色互动/生活 |
| 探索 | 新地点/新信息 |
| 修炼 | 能力提升/突破 |
| 阴谋 | 算计/政治 |
| 逃亡 | 危机/追击 |
| 揭示 | 真相/揭露 |

每卷使用全部类型，单卷内不连续 3 章同类型。
````

- [ ] **Step 4: 编辑 SKILL.md** —— 将 `:84-110`（从 `### 2. 三线比例` 行到 `### 3. 场景类型` 节末的 `每卷使用全部类型，单卷内不连续 3 章同类型。` 行）替换为：

````markdown
### 2. 三线比例与场景类型

完整定义、典型比例与场景类型标志见维护者参考 `pacing-design-reference.md`（运行时不注入；三线/场景规则见本文件硬规则，输出骨架以内含 EXACT 模板为准）。
````

并将紧随其后的 `### 4. 单调性检测阈值` 行改为 `### 3. 单调性检测阈值`（仅改号，正文逐字不动）。其余内容（`### 1. 四拍循环`、`## 输出格式` 起）**全部不动**。

- [ ] **Step 5: 跑测试确认通过**

Run: `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH uv run pytest tests/pipeline/test_spec6_prompt_slimming.py tests/pipeline/test_dispatch_helper_system_stability.py -v`
Expected: all passed

- [ ] **Step 6: 暂存后 just check 全量**

（同 Task 2 Step 6 理由——先暂存再 check，避免幂等 diff 门误红）

```bash
G=/Library/Developer/CommandLineTools/usr/bin/git
$G add skills/shenbi-pacing-design/SKILL.md skills/shenbi-pacing-design/pacing-design-reference.md tests/pipeline/test_spec6_prompt_slimming.py
PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH just check
```
Expected: EXIT=0

- [ ] **Step 7: Commit**

```bash
G=/Library/Developer/CommandLineTools/usr/bin/git
$G commit -m "perf: spec6 T_C — externalize pacing-design teaching sections

Move three-line-ratio and scene-type teaching tables (481 chars) to
maintainer reference pacing-design-reference.md (never injected; output
template self-contained with EXACT skeleton + target ratio tables);
renumber monotonicity threshold section. Net system-prompt drop
asserted >=280 chars / >=130 est-tokens offline."
```

---

## 度量与验收证据（执行期动作，非 task）

- 每个 T_C task 完成时运行并粘贴到 progress.md `## 验收证据`：

```bash
PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH uv run python -c "
import tempfile
from pathlib import Path
from shenbi.pipeline.dispatch_helper import _build_skill_prompt
from shenbi.cost.estimate import estimate_prompt_tokens
with tempfile.TemporaryDirectory() as td:
    pd = Path(td)
    for s in ('shenbi-chapter-pattern', 'shenbi-pacing-design'):
        sys_p, _, _ = _build_skill_prompt(s, pd, 'x', 1)
        print(s, 'len=', len(sys_p), 'est=', estimate_prompt_tokens(sys_p))"
```

记录 post 值与 pre 常量差值（字符 + token 双口径；spec §3.5 的字节口径差值同时换算记录）。

## Self-Review 记录

- **Spec 覆盖**：T_A→Task 1；T_C 实施集（chapter-pattern/pacing）→Task 2/3；T_B/T_D 不实施已在 spec/deviations 记录，无 task（正确）。spec §3.8 四行验收：字节净降/估算 token 差→两 task 测试；just check→每 task Step 6；引用存在性→断言 + contract-prose 机械防护；audit-run 面→不做（记录）。
- **占位符扫描**：无 TBD/「适当处理」；所有代码块完整可粘贴。
- **类型一致**：`_build_skill_prompt(skill, project_dir, prompt, chapter)` 参数序与源码 :601 一致；常量名前后一致（PRE_LEN_CHAPTER_PATTERN 等）。
