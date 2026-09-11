# Spec #58 C20 技能契约声明面修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 SKILL.md「正文↔frontmatter 契约」双向闭合 lint（R1/R2），修复 C20 簇存活 findings（8 P1 + P2 族 + D104 裁决），并使能相对章号占位符。

**Architecture:** 新独立 lint 工具 `tools/lint_contract_prose.py`（R1 正文引用⊆声明 / R2 声明 writes⇒正文步骤，双面挂载 justfile+ci.yml，终态 FAIL 阻断）；`src/shenbi/contracts/paths.py` 扩展相对偏移占位符 `chapter-{N-3}`（F811 时序修复的使能前提）；~14 个 SKILL.md 的 frontmatter/正文修复。

**Tech Stack:** Python 3.11+ / pytest / just / uv（与 CI `uv run --frozen` 同构）。

**对应 spec:** `docs/superpowers/specs/2026-08-16-audit-skill-contract-declaration-fix.md`（Revised 2026-09-11 · 设计审查四轮收敛版）

## Global Constraints

- 一切验证命令走 `uv run` / `just`（环境同构；系统 python 不算证据）
- `src/shenbi/` 无 `print()`（structlog）；gate 检查器纯函数幂等；`pathlib.Path` 文件 I/O
- 所有 SKILL.md frontmatter 契约变更后：`just lint-contracts` 绿 + `just generate` 幂等 diff 空（生成物 `## 数据契约` AUTO-GENERATED 块由 sync-contracts 重生，禁手改生成物）
- F947：全验收离线（fixtures/tmp_path 驱动；禁真实 `shenbi-dispatch`/`pipeline` dispatch）
- G0.9：`tests/fixtures/` 只放真实产物；tmp_path 内测试组装内容不算 fixture
- 状态字面量唯一定义于 `src/shenbi/contracts/enums.py`（本 plan 无新增状态词）
- commit 走 conventional commits，显式 pathspec（禁 `git add -A`）
- 修复后 21 条簇成员 ledger 回写：3 条已修 elsewhere（F838→PR #120、F881→PR #120、F882→PR #117），余 18 条 closed (C-20 spec #58)

## 验收覆盖表（spec 验收 → task → 可执行验证）

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1. R1/R2 违规=0（基线↔修复同口径对照） | T3 基线 + T9 清零 | `uv run python tools/lint_contract_prose.py --fail` exit 0（对照 `.superpowers/sdd/r1r2-baseline.md`） |
| 2. 读侧五技能 dispatch 注入断言 | T9 | `uv run pytest tests/pipeline/test_dispatch_reads_injection.py -v` 全 PASS |
| 3. G4 PASS + market-radar decisions 回归 | T9 | T9 Step 4（gates 全量 pytest + T1 套件 + decisions lint）；`uv run pytest tests/tiers/t1-skill/shenbi-market-radar tests/test_lint_decisions_sources.py -q`（**deviation**：仓内无真实 market-radar decisions.json——G0.9 禁现造，以既有 T1 套件 + decisions 链测试承载回归） |
| 4. meta 豁免显式输出 | T8 | `uv run python tools/lint_contract_prose.py --list-exempt` 列 2 条 meta 豁免 |
| 5. just check 全绿 + FAIL 级 + CI 挂载 | T3 + T9 | `just check` exit 0；ci.yml 契约步含新工具与 lint_contract_graph |

## Task 复杂度/测试分级总表

| Task | 内容 | 复杂度 | test_kind | 层级 |
|---|---|---|---|---|
| 1 | paths.py 偏移占位符 | **infra**（contracts/ 模块） | tdd_red_green | T1 |
| 2 | lint_contract_prose.py | **infra**（CI 承载 + 消费 contracts loader） | tdd_red_green | T1 |
| 3 | 接线 + 基线 | **infra**（ci.yml/justfile） | regression_guard | T1 |
| 4 | P1 读侧 7 技能 | leaf | characterization | T1 |
| 5 | P1 写侧 3 面 | leaf | characterization | T1 |
| 6 | F870 越权写 + F884 glob | leaf | characterization | T1 |
| 7 | P2 批量 5 面 | leaf | characterization | T1 |
| 8 | D104 + F849 | leaf | characterization | T1 |
| 9 | 验收聚合 | **infra**（断言面广） | acceptance/regression | T1 |

---

### Task 1: 相对章号偏移占位符（paths.py）

**Files:**
- Modify: `src/shenbi/contracts/paths.py`（`_FAMILY_N` 定义行（:30）后新增偏移正则；`resolve_contract_path` ctx 路由 + `resolve_chapter_path` no-ctx/genesis 路由）
- Test: `tests/unit/contracts/test_paths_offset.py`（新建；paths 旧族测试在 `tests/unit/contracts/test_paths.py` + `test_paths_family.py`，新测试与家族同位）

**Interfaces:**
- Consumes: `PathContext`（既有 dataclass，`chapter/arc/stratum/volume/anchor/escalation`）
- Produces: 偏移形态 `chapter-{N-3}` / `volume-{N+1}` 的解析语义——ctx 路由按 ctx 家族值为基（家族值 None 或 str sentinel → `UnresolvedPathError`）；no-ctx 路由按 chapter 为基（`resolve_chapter_path`）；chapter=None 且路径含偏移 → `UnresolvedPathError`（genesis 由 `resolve_or_skip_ctx` 过滤为 skip）。Task 4 的 reads 声明 `chapters/chapter-{N-3}.md` 依赖此语义；Task 2 的 lint canonical 化消费同一形态。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/contracts/test_paths_offset.py
"""Relative-offset placeholder semantics (spec #58 C20 T2.5 enabler, F811)."""

import pytest

from shenbi.contracts.paths import (
    PathContext,
    UnresolvedPathError,
    resolve_chapter_path,
    resolve_contract_path,
    resolve_or_skip_ctx,
)


def test_offset_no_ctx_chapter_base():
    assert resolve_chapter_path("chapters/chapter-{N-3}.md", 5) == "chapters/chapter-2.md"
    assert resolve_chapter_path("chapters/chapter-{N-1}.md", 1) == "chapters/chapter-0.md"


def test_offset_ctx_family_base():
    ctx = PathContext(chapter=99, volume=3)
    assert resolve_contract_path("chapters/chapter-{N-3}.md", 99, ctx) == "chapters/chapter-96.md"


def test_offset_ctx_family_value_missing_raises():  # 路径须家族前有 / 或 -（_FAMILY_N_OFFSET lookbehind），字符串起始形态不匹配
    with pytest.raises(UnresolvedPathError):
        resolve_contract_path("truth/volume-{N-1}/x.md", 5, PathContext(chapter=5))


def test_offset_genesis_skipped_via_resolve_or_skip():
    assert resolve_or_skip_ctx("chapters/chapter-{N-3}.md", None, None) is None
    with pytest.raises(UnresolvedPathError):
        resolve_chapter_path("chapters/chapter-{N-3}.md", None)


def test_offset_no_interference_with_legacy_forms():
    assert resolve_chapter_path("chapters/chapter-N.md", 5) == "chapters/chapter-5.md"
    assert resolve_chapter_path("import/canon/01_SECTION.md", 5) == "import/canon/01_SECTION.md"
    assert resolve_chapter_path("audits/AC-NNN.md".replace("NNN", "007"), 5) == "audits/AC-007.md"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/contracts/test_paths_offset.py -v`
Expected: FAIL（`chapter-{N-3}` 原样返回/不抛 UnresolvedPathError——偏移形态未实现）

- [ ] **Step 3: 最小实现**

```python
# src/shenbi/contracts/paths.py —— _FAMILY_N 定义行后新增：
# Spec #58 C20 (F811): relative-offset placeholders `chapter-{N-3}` — brace
# form only (prose's paren form `(N-3)` is lint-side canonicalized, never a
# declared read). Base value: ctx family value (ctx route, F207 semantics —
# None/str-sentinel raises) or chapter (no-ctx route).
_FAMILY_N_OFFSET = re.compile(
    r"(?<=[-/])(arc|stratum|volume|chapter|escalation)-\{N([+-]\d+)\}"
)


def _offset_sub(path: str, base: int) -> str:
    return _FAMILY_N_OFFSET.sub(lambda m: f"{m.group(1)}-{base + int(m.group(2))}", path)
```

`resolve_contract_path` 的 `if ctx is not None:` 块内、`_FAMILY_N.search` 之前插入：

```python
        if _FAMILY_N_OFFSET.search(path):
            for fm in _FAMILY_N_OFFSET.finditer(path):
                base = getattr(ctx, fm.group(1))
                if not isinstance(base, int):
                    # F207 语义沿用：家族值缺失/str sentinel 无算术基 → 显式错
                    raise UnresolvedPathError(path)
                path = path.replace(
                    fm.group(0), f"{fm.group(1)}-{base + int(fm.group(2))}"
                )
```

（单一循环：per-family base 校验 + 逐处替换。）

`resolve_chapter_path` 改为：

```python
def resolve_chapter_path(path: str, chapter: int | None) -> str:
    if chapter is None:
        if _NNN in path or _BOUND_N.search(path) or _FAMILY_N_OFFSET.search(path):
            raise UnresolvedPathError(path)
        return path
    result = _NNN_BOUNDED.sub(f"{chapter:03d}", path)
    result = _offset_sub(result, chapter)
    return _bounded_replace_n(result, chapter)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/contracts/test_paths_offset.py -v`
Expected: 5 passed

- [ ] **Step 5: 回归既有路径测试 + 类型门**

Run: `uv run pytest tests/unit/contracts -q && uv run ruff check src/shenbi/contracts/paths.py && uv run mypy src/shenbi/contracts/paths.py`
Expected: tests/unit/contracts 全 PASS（含 test_paths.py/test_paths_family.py 旧族 + 新 test_paths_offset.py）、ruff/mypy 0 errors

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/contracts/paths.py tests/unit/contracts/test_paths_offset.py
git commit -m "feat: relative-offset placeholder chapter-{N-k} in contract paths (spec58 C20 enabler)"
```

---

### Task 2: R1/R2 契约闭合 lint 工具

**Files:**
- Create: `tools/lint_contract_prose.py`
- Test: `tests/test_lint_contract_prose.py`

**Interfaces:**
- Consumes: `shenbi.sync_contracts.load_all_contracts()`（dict[skill → contract dict]，monkeypatch 点同 `tests/unit/tools/test_lint_contract_graph.py:50` 先例：`monkeypatch.setattr("shenbi.sync_contracts.load_all_contracts", ...)`）、`shenbi.contracts.graph.dag_key`、`shenbi.pipeline.dispatch_helper._strip_autogen_blocks`（R2/R1 共用：AUTO-GENERATED 数据契约块不算正文证据）、`tools.lint_contracts.META_SKILLS`
- Produces: CLI `python tools/lint_contract_prose.py [--fail] [--list-exempt]`——默认 WARN（打印违规 exit 0）；`--fail` 违规 exit 1；`--list-exempt` 显式输出 meta 豁免与 allowlist（验收 4/5）。Task 3 挂载、Task 9 清零验证消费。

**规则设计（spec T1.1 三段裁决全文落地）：**
- R1 正文→声明：剥 AUTO-GENERATED 块后，提取正文路径引用（相对路径/裸 `.md` 名/glob 形态），归一化 `[({]N±k[)}]` → `N`，依次匹配：①声明精确（双方归一后相等）②声明转 glob（`N`→`*`，fnmatch）③裸名=任一声明基名 ④skill-bundle（`skills/<skill>/<basename>` 物理存在）⑤registry 词表 globs/patterns ⑥显式 allowlist（具名类别+理由）。六级全不中 → 违规。
- R2 声明→正文：剥 AUTO-GENERATED 块后，声明 writes/updates 每个文件须在正文（步骤/标题/输出格式节）出现其 basename 或归一路径；仅出现在 AUTO-GENERATED 摘要块不算（F812/F871/F872 靶点）。

**Allowlist 数据结构（具名类别，验收 5 的记录载体）：**

```python
ALLOWLIST: tuple[tuple[str, str, str], ...] = (
    # (category, "skill:pattern"(fnmatch，* 通配), reason)
    ("skill-bundle", "*:anti-ai-reference.md", "捆绑参考文件，dispatcher 不注入（T1.1 裁决 b）"),
    ("anti-example", "shenbi-context-composing:chapters/chapter-*.md", "anti-rationalization 反例行，非真实读依赖"),
    # 基线期按实况增补，每条附一行理由；known-limitation 注记见 docstring
)
```

- [ ] **Step 1: 写失败测试**（tmp_path 组装合成 SKILL 文本——先例 `tests/pipeline/test_g4_directory.py:24-32` 的 tmp_path 豁免（G0.9 边界裁决在其 docstring），非 tests/fixtures 产物；monkeypatch `load_all_contracts` 与 skills 根路径）

测试覆盖矩阵（每条一个 test 函数，全部写全）：
1. R1 命中：正文引用 `outline/three_act.md` 未声明 → 违规列表含 `(skill, "outline/three_act.md")`
2. R1 裸名过：正文 `protagonist.md`，声明含 `characters/protagonist.md` → 过（基名规范化）
3. R1 glob 过：正文 `characters/**/*.md`，声明 `characters/*.md` → 过
4. R1 偏移归一过：正文 `chapter-(N-3).md`，声明 `chapters/chapter-{N-3}.md` → 过（双形态归一）
5. R1 skill-bundle 过：正文 `anti-ai-reference.md` 且 `skills/<skill>/anti-ai-reference.md` 存在 → 过
6. R1 AUTO-GEN 块不算：违规引用只出现在 AUTO-GENERATED 块内 → 不报
7. R2 命中：声明写 `truth/drift_guidance.md`，正文（剥块后）零出现 → 违规
8. R2 块内出现不算：basename 仅在 AUTO-GENERATED 块 → 仍违规（F812 靶点）
9. meta 豁免：`using-shenbi`/`shenbi-writing-skills` 不参与两规则
10. `--fail` exit 语义：有违规 exit 1 / 无违规 exit 0 / WARN 模式恒 exit 0

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_lint_contract_prose.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 tools/lint_contract_prose.py**

结构（骨架 + 关键函数签名；docstring 载明 spec 出处、三类白名单裁决、known-limitation 注记——reads/writes/updates 并池基名匹配对 F836 回退形态不可见，由 Task 9 行为级断言兜底）：

```python
#!/usr/bin/env python3
"""Prose↔declaration closure lint (spec #58 C20 T1).

R1 body→decl: every file path referenced in a SKILL.md body (outside the
AUTO-GENERATED contract block) must be covered by the frontmatter contract
(six-level match: exact / glob / basename / skill-bundle / registry vocab /
allowlist).  R2 decl→body: every declared write/update must appear in real
prose (steps/headers/output sections), not only the AUTO-GENERATED summary.

Known limitation (deliberate, spec T1.1 note): basename matching pools
reads+writes+updates, so a READ reference that only matches a WRITE
declaration passes — the F836 regression shape is covered instead by the
behavioral dispatch assertions (tests/pipeline/test_dispatch_reads_injection.py).
"""
from __future__ import annotations
import fnmatch, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shenbi import sync_contracts
from shenbi.contracts.graph import dag_key
from shenbi.pipeline.dispatch_helper import _strip_autogen_blocks
from tools.lint_contracts import META_SKILLS

_OFFSET_N = re.compile(r"[({]N[+-]\d+[)}]")

def _canonical(path: str) -> str: ...
def _body_refs(body: str) -> set[str]: ...          # 路径/glob/裸 .md 提取
def _covered(ref: str, declared: list[str], skill_dir: Path, registry) -> bool: ...  # 六级匹配
def find_violations(contracts, skills_root: Path, registry) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    """Returns (r1_violations [(skill, ref, rule)], r2_violations [(skill, target)])."""
def main(argv: list[str] | None = None) -> int: ...  # --fail / --list-exempt
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_lint_contract_prose.py -v`
Expected: 全 PASS

- [ ] **Step 5: ruff/mypy 门（tools 面按仓库现状跑 ruff 即可，mypy 仅 src/）**

Run: `uv run ruff check tools/lint_contract_prose.py tests/test_lint_contract_prose.py && uv run ruff format --check tools/lint_contract_prose.py`
Expected: 0 errors（format 不符则 `ruff format` 该两文件后复跑）

- [ ] **Step 6: Commit**

```bash
git add tools/lint_contract_prose.py tests/test_lint_contract_prose.py
git commit -m "feat: R1/R2 prose-contract closure lint tool (spec58 C20 T1)"
```

---

### Task 3: 双面接线 + WARN 基线

**Files:**
- Modify: `justfile:74-77`（lint-contracts target）、`.github/workflows/ci.yml:53-57`（契约 lint 步）
- 产出（gitignored 工作态）: `.superpowers/sdd/r1r2-baseline.md`

**Interfaces:**
- Consumes: Task 2 的 `--fail` 语义
- Produces: CI/本地双面 FAIL 阻断 + 基线底单（Task 4-8 修复的机械验收参照；Task 9 对照清零）。**预期时序**：本 task 落地后本地 `just check` 在 Task 4-8 完成前会红（R1/R2 存量违规）——这是设计内状态，阶段 7 才要求全绿。

- [ ] **Step 1: justfile lint-contracts 增行**

```just
lint-contracts:
	uv run python tools/lint_contract_graph.py
	uv run python scripts/lint_contract_fields.py
	uv run python tools/lint_contracts.py
	uv run python tools/lint_contract_prose.py --fail
```

- [ ] **Step 2: ci.yml 契约 lint 步补两行**（同时修复该步漏跑 lint_contract_graph 的存量缺口——spec T1.1 记载）

```yaml
      - name: Contract + repo-consistency lints (spec §5.5)
        run: |
          uv run python tools/lint_contracts.py
          uv run python tools/lint_contract_graph.py
          uv run python tools/lint_contract_prose.py --fail
          uv run python scripts/lint_contract_fields.py
          uv run python tools/lint_repo_consistency.py
```

- [ ] **Step 3: WARN 基线全量跑批落盘**

Run: `uv run python tools/lint_contract_prose.py > /tmp/r1r2-baseline.txt 2>&1; echo "exit=$?"; wc -l /tmp/r1r2-baseline.txt`
Expected: exit=0（WARN 模式），输出违规清单——复制到 `.superpowers/sdd/r1r2-baseline.md`（附日期与 HEAD SHA；此即验收 1 的「基线报告」半侧）

- [ ] **Step 4: 行动验证 yaml/justfile 语法**

Run: `uv run python tools/lint_contract_prose.py --fail; echo "fail-exit=$?"`（预期非 0——存量违规存在，FAIL 语义生效）+ `just --fmt --check`（或 `just -l` 列 target 不报错）
Expected: fail-exit=1；justfile 语法有效

- [ ] **Step 5: Commit**

```bash
git add justfile .github/workflows/ci.yml
git commit -m "chore: wire prose-closure lint into justfile+CI, backfill lint_contract_graph in CI (spec58 C20)"
```

---

### Task 4: P1 读侧修复（F803/F809/F811 读侧/F821/F836/F889/F892 + volume_summaries 三方对齐）

**Files:**
- Modify: `skills/shenbi-book-spine-init/SKILL.md`、`skills/shenbi-character-design/SKILL.md`、`skills/shenbi-context-composing/SKILL.md`、`skills/shenbi-foundation-review/SKILL.md`、`skills/shenbi-memory-distill/SKILL.md`、`skills/shenbi-sequel-writing/SKILL.md`、`skills/shenbi-escalation-review/SKILL.md`、`skills/shenbi-volume-consolidation/SKILL.md`（仅模板节）
- 验证：无新测试文件——机械验证 = lint 收敛 + `just generate` 幂等（characterization：修复行为由 Task 2 lint 与 Task 9 行为断言刻画）

**Interfaces:**
- Consumes: Task 1 偏移占位符（F811 近章声明）、Task 2/3 lint
- Produces: 六技能 reads 集合变更（Task 9 断言的输入）。

**编辑清单（每处 = frontmatter `reads:` 列表增行；YAML 缩进对齐既有条目）：**

1. book-spine-init（F803）: reads += `characters/protagonist.md`、`world/rules.md`
2. character-design（F809）: reads += `outline/chapter_outline.md`、`outline/three_act.md`、`characters/**/*.md`（**glob 语义边界（2026-09-11 轮 3 亲证）**：dispatcher `_resolve_read_path` 用 stdlib glob **无 recursive=True**——`**` 退化为单层，匹配 `characters/<dir>/*.md` 嵌套位、不匹配顶层 `characters/*.md`；registry 也无 `characters/*.md` glob，故角色文件按既有 registry 布局放嵌套位（`characters/major/` 等），声明保持 `characters/**/*.md` 与 SKILL.md:224 散文一致）
3. context-composing（F811 读侧+时序）: reads -= `chapters/chapter-N.md`；reads += `chapters/chapter-{N-3}.md`、`chapters/chapter-{N-2}.md`、`chapters/chapter-{N-1}.md`
4. foundation-review（F821）: reads += `genre-config.json`、`truth/book_spine.md`；正文删重复的第二个 `## 输出格式` 节（`:95` 与 `:125` 并存——保留信息更全的一节，另一节删除）
5. memory-distill（F836）: reads += `truth/author_intent.md`、`truth/book_spine.md`、`world/rules.md`
6. sequel-writing（F889）: reads += `style/style_profile.md`
7. escalation-review（F892）: reads += `truth/volume_score_trend.md`、`truth/arc_payoff_trend.md`、`audits/stratum-N-score.md`（六类触发：score_decline/sensitivity 已覆盖，volume_objective_missed/arc_score_below_threshold/stratum_axis_drift 三源补入；regeneration_loop_exhausted 为 pipeline 计数器非文件，无 reads 面）
8. volume-consolidation（F811c 三方对齐）: 锚定**精确输出模板**（`:166 ## 输出格式` 下的模板块，`:177 ### 叙事弧线` 起——注意勿改 `:80` 的填充示例区）增三节 `### 卷目标达成`、`### 核心事件`、`### 跨卷钩子`；既有六节保留（`### 关键事件` 与新增 `### 核心事件` 并存为有意超集：前者服务其他读者，后者为 context-composing fields/fixture 的三方闭合节，勿删改前者）。消费方 fields（卷目标达成/核心事件/跨卷钩子）与 fixture（tests/fixtures/volume-summary-example.md 三 H2）由此闭合

- [ ] **Step 1: 逐技能编辑**（上表 1-8；每技能一个独立 commit 可选，按仓库惯例合并为本 task 单 commit 亦可——本 plan 取单 commit）
- [ ] **Step 2: 契约同步与 lint 收敛验证**

Run: `just generate && just lint-contracts || true` → 重点看 `lint_contract_prose` 段：上述七技能的 R1 违规消失（其余技能存量违规仍在，Task 5-8 处置）；`uv run python tools/lint_contract_graph.py` 无新 ORPHAN_READ（新增 reads 均有 producer：protagonist/world rules/outline 三件/near-chapter/style_profile/trend 三件——若 ORPHAN 出现即声明了无生产者文件，回查 truth-files.yaml registry）
Expected: 生成物 diff 空（`git status --short` 无 deps.json/docs/skills 意外变更——预期变更仅 AUTO-GENERATED 块重生）；无新 ORPHAN_READ
- [ ] **Step 3: 偏移声明生效单测**

Run: `uv run pytest tests/unit/contracts/test_paths_offset.py -q`
Expected: PASS（Task 1 语义仍绿）
- [ ] **Step 4: Commit**

```bash
git add skills/shenbi-book-spine-init/SKILL.md skills/shenbi-character-design/SKILL.md skills/shenbi-context-composing/SKILL.md skills/shenbi-foundation-review/SKILL.md skills/shenbi-memory-distill/SKILL.md skills/shenbi-sequel-writing/SKILL.md skills/shenbi-escalation-review/SKILL.md skills/shenbi-volume-consolidation/SKILL.md
just generate
git add docs/skills deps.json 2>/dev/null
git commit -m "fix: P1 read-side contract closures — F803/F809/F811/F821/F836/F889/F892 + volume_summaries 3-way alignment (spec58 C20)"
```

---

### Task 5: P1 写侧修复（F812/F871/F811 后半）

**Files:**
- Modify: `skills/shenbi-drift-guidance/SKILL.md`、`skills/shenbi-score-volume/SKILL.md`、`skills/shenbi-context-composing/SKILL.md`

**Interfaces:**
- Consumes: Task 3 lint（R2 验证）
- Produces: 三处正文产出节 + 两处 frontmatter 变更。

**编辑清单：**

1. **F812 drift-guidance**：正文步骤区（`## 数据契约` AUTO-GEN 块之外）新增产出节。**消费面实况（2026-09-11 亲证）**：`truth/drift_guidance.md` 仅被 triggers.py:268-273 声明为 volume 边界 TriggerStep 的 `output_path`——pipeline 消费的是「产物存在性」（dispatch 后 gate 检查输出落盘），**无任何代码解析其字段**（全 src/ grep `drift_guidance` 仅 3 处：声明 + chapter_loop:1743/1814 的触发器读的是 `truth/audit_drift.md` 而非本文件）。因此产出节**不得虚构消费者行为**，字段语义由本 skill 自身定义：

```markdown
## drift_guidance 产出（truth/drift_guidance.md，create_or_overwrite）

每次执行末尾整体写出该文件（pipeline volume 边界触发器期待其存在——triggers.py volume_boundary 链）。最小模板：
- `## 漂移状态`：无漂移 | 轻度漂移 | 重度漂移（汇总自本次读取的 audit_drift 证据）
- `## 拦截建议`：一句话处置建议（供下一卷开卷决策的人类伙伴参考）
```

核对命令：`grep -rn "drift_guidance" src/shenbi/`（预期仅 3 处，如上——若执行时出现新消费代码以其为准）。

2. **F871 score-volume**：frontmatter `updates` 条目 `key: chapter` → `key: volume`（`:19`）；正文新增步骤与格式节：

```markdown
## volume_score_trend 追加（append_dedup，key=卷号）

评分完成后向 `truth/volume_score_trend.md` 追加**本卷一行**（首列=第X卷，勿输出他卷行/表头）：
`| 第X卷 | <总评> | <三维分项> | <相较上卷 Δ> |`
```

3. **F812 子项 2（audit_drift_archive 写未声明）**：drift-guidance frontmatter writes += `- file: truth/audit_drift_archive.md
    mode: create_or_overwrite`（正文铁律 6 :69 的滚动归档语义 = 整文件重写归档；改后 `just lint-contracts` 须绿）。
4. **F811 后半 context-composing**：frontmatter `writes` += `- file: context/chapter-N-context.md\n    mode: create_or_overwrite`；正文非 pipeline 模式补产出步骤（pipeline 模式 `:111-116` 已有）——直接 dispatch 时同样把组装结果写出至 `context/chapter-N-context.md`（spec 轮 3 裁决：双模式均写）。

- [ ] **Step 1: 三处编辑**
- [ ] **Step 2: R2 收敛验证**

Run: `just generate && uv run python tools/lint_contract_prose.py 2>&1 | grep -E "drift-guidance|score-volume|context-composing" || echo "(三技能 R2 违规清零)"`
Expected: 三技能零 R2 违规（R1 若因新增正文路径引用出现新违规，本 task 内补声明或 allowlist——增补 allowlist 须附理由）
- [ ] **Step 3: G4 结构验证（score-volume key 变更）**

Run: `uv run pytest tests/gates -q && just lint-contracts`
Expected: gates 全 PASS（score-volume key 变更由 G4/键对账测试承载——仓内无独立 score-volume 真实产物 fixture）；lint-contracts 四件绿
- [ ] **Step 4: Commit**

```bash
git add skills/shenbi-drift-guidance/SKILL.md skills/shenbi-score-volume/SKILL.md skills/shenbi-context-composing/SKILL.md
just generate
git add -u docs/skills deps.json 2>/dev/null
git commit -m "fix: P1 write-side closures — F812 drift_guidance output section, F871 volume key+steps, F811 main-artifact writes (spec58 C20)"
```

---

### Task 6: 越权写拆除（F870）+ 占位模式 glob 化（F884）

**Files:**
- Modify: `skills/shenbi-state-settling/SKILL.md`（`:277-287` arc_log 指令）、`skills/shenbi-truth-sync/SKILL.md`（reads）

**编辑清单：**
1. F870：删除「For the protagonist specifically, append an `arc_log` entry to `characters/protagonist.md` frontmatter」整个代码块与指令（字段所有权归 character 域技能）；其上「Set "Last Updated Ch"」与其下「3. Write updated character_matrix.md」步骤序号顺延重排。
2. F884：reads `chapters/chapter-N.md` → `chapters/chapter-*.md`（多章 N..M 语义；token 由预算截断+披露兜底——spec 轮 3 裁决倾向 glob 化）。

- [ ] **Step 1: 两处编辑**
- [ ] **Step 2: 验证**

Run: `just generate && uv run python tools/lint_contract_prose.py 2>&1 | grep -E "state-settling|truth-sync" || echo "(清零)"; uv run pytest tests/gates -q`
Expected: 两技能零新违规；G4 state-settling 相关测试绿
- [ ] **Step 3: Commit**

```bash
git add skills/shenbi-state-settling/SKILL.md skills/shenbi-truth-sync/SKILL.md
git commit -m "fix: remove protagonist.md out-of-contract write (F870) + truth-sync multi-chapter glob read (F884) (spec58 C20)"
```

---

### Task 7: P2 批量（F802/F805/F807/F825/F872）

**Files:**
- Modify: `skills/shenbi-anti-detect/SKILL.md`、`skills/shenbi-style-learning/SKILL.md`、`skills/shenbi-chapter-planning/SKILL.md`、`skills/shenbi-foreshadowing-lifecycle/SKILL.md`、`skills/shenbi-score-stratum/SKILL.md`

**编辑清单：**
1. **F802 anti-detect**：DOT 流程图 `:44-48` 循环边补 sensitivity 复审节点——`"Re-run anti-AI audit" -> "Re-run sensitivity audit"` → `-> "Pass"`（与铁律 3「anti-ai + sensitivity 两个审计必须重新通过」对齐，DOT 为权威）。
2. **F805 style-learning**：输出模板节名/编号对齐 fixture 11 节实名（`tests/fixtures/style-profile-example.md`：`## 1. 句长分布`/`## 2. 段长分布`/`## 3. TTR（Type-Token Ratio）`/`## 4. 高频 character 二元组（bigrams，出现 ≥ 30 次）`/`## 5. 高频 character 三元组（trigrams，出现 ≥ 15 次）`/`## 6. 修辞模式`/`## 7. 标点密度（每千字）`/`## 8. 连接词密度（每千字）`/`## 9. 对白占比`/`## 10. 各章统计`/`## 11. 综合画像`）——模板重排为该 11 节（消费方 chapter-drafting fields 声明 `11. 综合画像/6. 修辞模式/9. 对白占比` 由此为真）。
3. **F807 chapter-planning**：reads += `novel.json`。
4. **F825 foreshadowing-lifecycle**：reads += `outline/story_frame.md`、`truth/bridge_tracker.md`（spec 明文「**读写**声明补全」——Cross-Volume Bridge 节先读 tracker 查 pending 桥再写）；writes += `- file: truth/bridge_tracker.md\n    mode: append_dedup\n    key: bridge_id`；正文 Cross-Volume Bridge Tracking 节（`:120-126`）补一句产出说明（每桥一行、首列 Bridge ID、勿输出他行——append_dedup 纪律，镜像 state-settling mode-rules 行文）。
5. **F872 score-stratum**：正文补 book_spine 更新说明节（「评分后更新 `truth/book_spine.md` 的**数据字段**（当前位置/进度/themes 探索深度），不改声明字段——与 memory-distill L5 同语义」）。

- [ ] **Step 1: 五处编辑**
- [ ] **Step 2: 验证**

Run: `just generate && uv run python tools/lint_contract_prose.py 2>&1 | grep -E "anti-detect|style-learning|chapter-planning|foreshadowing|score-stratum" || echo "(清零)"; uv run python scripts/lint_contract_fields.py`
Expected: 五技能零新违规；fields lint 绿（F805 后消费方声明与 fixture 仍一致）
- [ ] **Step 3: Commit**

```bash
git add skills/shenbi-anti-detect/SKILL.md skills/shenbi-style-learning/SKILL.md skills/shenbi-chapter-planning/SKILL.md skills/shenbi-foreshadowing-lifecycle/SKILL.md skills/shenbi-score-stratum/SKILL.md
git commit -m "fix: P2 contract closures — F802 DOT/F805 style template 11-section/F807/F825 bridge_tracker/F872 (spec58 C20)"
```

---

### Task 8: D104 meta 豁免单一信源 + F849 fanfic 子模式拆除

**Files:**
- Modify: `tools/lint_contract_prose.py`（豁免输出）、`skills/shenbi-review-fanfic/SKILL.md`

**编辑清单：**
1. **D104**：lint 的 meta 处理已 import `META_SKILLS`（Task 2 单一信源）；本 task 在 `--list-exempt` 输出中显式列出两条豁免（`meta-exempt: using-shenbi`、`meta-exempt: shenbi-writing-skills`——验收 4 的可观察面）；豁免即裁决落文：meta skill 免契约（既有 lint_contracts 同裁定的沿用，不对称从静默变声明）。
2. **F849**：review-fanfic 正文删除 `:37`「模式由 shenbi-canon-import 导入并声明」句 + `:75` 区 `novel.json.fanfic.mode` 读取指令改为「模式由 human partner 在指令中直接给出（au/ooc/cp）」+ 删除依赖 fanfic.mode 配置的子模式选择分支描述（YAGNI——NovelConfig `extra: forbid` 无该字段，spec 推荐）。

- [ ] **Step 1: 编辑 + 豁免输出**

Run（编辑后）: `uv run python tools/lint_contract_prose.py --list-exempt | grep -c "meta-exempt"`
Expected: `2`

- [ ] **Step 2: 验证**

Run: `uv run pytest tests/test_lint_contract_prose.py -q && uv run python tools/lint_contract_prose.py 2>&1 | grep -E "review-fanfic" || echo "(清零)"`
Expected: 全绿/清零
- [ ] **Step 3: Commit**

```bash
git add tools/lint_contract_prose.py skills/shenbi-review-fanfic/SKILL.md
git commit -m "feat: D104 meta exemption made explicit + F849 fanfic.mode unconfigurable description removal (spec58 C20)"
```

---

### Task 9: 验收聚合——dispatch 五腿断言 + G4/G2 回归 + R1/R2 清零 FAIL

**Files:**
- Test: `tests/pipeline/test_dispatch_reads_injection.py`（新建）

**Interfaces:**
- Consumes: Task 4 的 reads 集合、Task 1 偏移解析、`_build_skill_prompt(skill, project_dir, prompt, chapter, uses_staging=False, shared_context=None, json_mode=False, path_context=None) -> tuple[str, str, list[str]]`（dispatch_helper.py:603 实签名）、`tests/fixtures/genre-config-example.json`（真实产物）
- Produces: 验收 1/2/3/4/5 的最终可执行证据（阶段 6 验收证据节直接引用）。

- [ ] **Step 1: 写五腿参数化测试**

```python
# tests/pipeline/test_dispatch_reads_injection.py
"""Spec #58 C20 acceptance 2: declared reads must be injected for the five
read-side P1 skills (offline; F947 — no real dispatch). Precedent:
tests/pipeline/test_dispatch_helper_keys.py tmp_path assembly."""

from pathlib import Path

import pytest

from shenbi.pipeline.dispatch_helper import _build_skill_prompt

MARK = "# spec58 acceptance\n"

CASES = [
    # (skill, files to place, expected injected keys, keys that must be ABSENT)
    (
        "shenbi-book-spine-init",  # F803
        ["characters/protagonist.md", "world/rules.md", "outline/story_frame.md",
         "outline/volume_map.md", "novel.json"],
        ["characters/protagonist.md", "world/rules.md"],
        [],
    ),
    (
        "shenbi-character-design",  # F809
        ["world/story_bible.md", "world/rules.md", "outline/chapter_outline.md",
         "outline/three_act.md", "characters/major/alice.md"],
        ["outline/chapter_outline.md", "outline/three_act.md", "characters/major/alice.md"],
        [],
    ),
    (
        "shenbi-context-composing",  # F811: near-chapter in, current-chapter out
        ["truth/pending_hooks.md", "truth/chapter_summaries.md",
         "truth/volume_summaries.md", "chapters/chapter-2.md", "chapters/chapter-3.md",
         "chapters/chapter-4.md", "chapters/chapter-5.md"],
        ["chapters/chapter-2.md", "chapters/chapter-3.md", "chapters/chapter-4.md"],
        ["chapters/chapter-5.md"],  # N=5: 组装时不存在，不得注入
    ),
    (
        "shenbi-foundation-review",  # F821 (genre-config uses the real fixture)
        ["outline/story_frame.md", "world/rules.md"],
        ["genre-config.json", "truth/book_spine.md"],
        [],
    ),
    (
        "shenbi-memory-distill",  # F836: L5 inputs no longer filtered out
        ["truth/chapter_summaries.md", "truth/pending_hooks.md", "truth/character_matrix.md",
         "truth/volume_summaries.md", "truth/author_intent.md", "truth/book_spine.md",
         "world/rules.md"],
        ["truth/author_intent.md", "truth/book_spine.md", "world/rules.md"],
        [],
    ),
]


@pytest.mark.parametrize("skill,files,expected,absent", CASES)
def test_required_inputs_injected(tmp_path, skill, files, expected, absent):
    for rel in files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(MARK, encoding="utf-8")
    # F821 leg: real fixture for genre-config.json (G0.9 real product)
    if skill == "shenbi-foundation-review":
        gc = tmp_path / "genre-config.json"
        gc.write_text(
            Path("tests/fixtures/genre-config-example.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        tb = tmp_path / "truth" / "book_spine.md"
        tb.parent.mkdir(parents=True, exist_ok=True)
        tb.write_text(MARK, encoding="utf-8")
    _, user_prompt, _ = _build_skill_prompt(
        skill=skill, project_dir=tmp_path, prompt="chapter 5", chapter=5,
    )
    for key in expected:
        assert key in user_prompt, f"{skill}: expected input not injected: {key}"
    for key in absent:
        assert key not in user_prompt, f"{skill}: must NOT be injected: {key}"
```

（执行时按各 skill 契约的完整 reads 集补齐 files 列表使注入不因缺文件静默跳过——每腿以「expected 全命中」为准；context-composing 腿 chapter=5。）

- [ ] **Step 2: 跑测试**

Run: `uv run pytest tests/pipeline/test_dispatch_reads_injection.py -v`
Expected: 5 passed

- [ ] **Step 3: R1/R2 全量清零（FAIL 级）+ 基线对照**

Run: `uv run python tools/lint_contract_prose.py --fail; echo "exit=$?"; uv run python tools/lint_contract_prose.py --list-exempt`
Expected: exit=0（零违规——对照 `.superpowers/sdd/r1r2-baseline.md` 存量清单全数消解：修复/allowlist 具理由）；`--list-exempt` 输出含 2 条 meta-exempt + 全部 allowlist 条目

- [ ] **Step 4: G4/G2 回归（验收 3）**

Run: `uv run pytest tests/tiers/t1-skill/shenbi-market-radar -q && uv run pytest tests/test_lint_decisions_sources.py -q && uv run pytest tests/gates -q`
Expected: 全 PASS（market-radar decisions 链 = T1 套件 + decisions 三源 lint + gates 全量；**spec 验收 3 的 market-radar decisions.json 直跑形态因仓内无真实产物按 G0.9 改由本组测试承载——spec deviation 已记**）

- [ ] **Step 5: just check 终验（验收 5 + 全门禁闭环）**

Run: `just check`
Expected: exit 0（含 ruff/format 触达文件、`lint_key_reconciliation --strict`——score-volume key 改 volume 后由此验证、两段 pytest + 覆盖率门；本步是 T3 设计内红态的解除点）

- [ ] **Step 6: Commit**

```bash
git add tests/pipeline/test_dispatch_reads_injection.py
git commit -m "test: spec58 acceptance — five-leg dispatch injection assertions + R1/R2 zero-violation at FAIL level"
```

---

## Self-Review 记录

1. **Spec coverage**：spec 任务 1-3（lint+基线+升级）→ T2/T3/T9；任务 4-8（P1/P2/D104）→ T4-T8；任务 9（F849）→ T8；任务 10（F849 批量清理节）→ 同 T8；验收 1-5 → 覆盖表全映射。F838/F881/F882 无 task（已修退出）✓。volume_summaries（F811c）→ T4.8 ✓。bridge_tracker（F825）→ T7.4 ✓。
2. **Placeholder scan**：T1 Step 3 的 ctx 路由代码块含「终版收敛为单一循环」注记——实现指引非占位（意图与替换式均已给出）；T5 F812 产出节以 triggers.py 实际解析面为对齐锚（步骤含核对命令）。其余无 TBD/TODO。
3. **Type consistency**：`_build_skill_prompt` 签名/返回 tuple 与 Task 9 测试一致（源码 :603 实抄）；`_offset_sub`/`_FAMILY_N_OFFSET` 在 T1 定义、T2 `_canonical` 消费同形态；`META_SKILLS` 单一信源（tools/lint_contracts.py:22）T2/T8 一致引用。
