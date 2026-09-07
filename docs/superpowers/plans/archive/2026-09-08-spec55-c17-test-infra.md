# Spec #55 C17 测试基础设施配置失效 修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消灭六条"配置存在但永不运行"的质量防线中间态——每条防线要么真实激活（运行 + 结果被消费）要么诚实下线（配置与承诺删除）。

**Architecture:** 全部为测试基础设施（.gitignore/CI workflow/pytest 配置/gate checker），无生产运行时变更（唯一 src/ 改动是 g0.py G0.5 检查器实装）。防线激活优先；mutmut 限时尝试（时间盒见 T4）失败即走诚实下线；golden/未消费 gate-outputs 基线/压力 prompt 走诚实下线（再生成路径已死：tests/rounds 不存在、novel-output 真实树不在仓库）。

**Tech Stack:** pytest + hypothesis（examples 库）、GitHub Actions（ci.yml）、纯 Python markdown 内链解析（无 npm 依赖）、mutmut 3.x。

**Spec:** `docs/superpowers/specs/2026-08-16-audit-test-infra-fix.md`（Revised 2026-09-08，HEAD b21997f4）

## Global Constraints

- 一切验证走 `just` / `uv run`（与 CI `uv run --frozen` 同构）；系统 python 结果不算证据
- 禁止真实 LLM dispatch（核心原则 8）；验收全部离线可复验
- `src/shenbi/` 无 `print()`（ruff T20 零豁免）；pathlib 做文件 I/O；conventional commits；commit 显式列路径（禁 `git add -A`）
- G0.9：fixtures 只能是真实产物；本 plan 不新增手写 fixture
- 红灯验证法：每条激活防线须演示「注入已知缺陷 → 验证失败 → 还原 → 绿」
- 分支：`fix/spec55-c17-test-infra`

---

### Task 1 · T1 hypothesis 回归重放复活（F1159/F1158）

**Files:**
- Modify: `.gitignore:80`
- Modify: `.hypothesis/.gitignore`（如存在内部忽略需保留语义）
- Add（git add）: `.hypothesis/examples/`（现存 43 失败样本 + .gitkeep；stale 清理后存活面见 Step 2）
- Modify: `.github/workflows/ci.yml`（pytest 步骤加可见证据）
- Test: 现有 58 个 `@given` 测试（重放即验证）

**Interfaces:**
- Produces: 提交入库的 `.hypothesis/examples/` 样本库；CI 步骤输出 hypothesis statistics

- [ ] **Step 1: .gitignore 手术**

`.gitignore:80` 的 `.hypothesis/` 改为：

```
.hypothesis/*
!.hypothesis/.gitignore
!.hypothesis/examples/
```

（目录级忽略下 git 无法 re-include 子文件——F1318 失败模式根源，必须拆成 `/*` + 定向反排除。`.hypothesis/examples/` 内部自身的 `.gitignore`（hypothesis 自动生成的缓存忽略）继续生效，满足「保留内部缓存的忽略」。）

- [ ] **Step 2: 清 stale（F1158）——定义化出口**

digest 失配的样本目录（hypothesis 按 test key 命名目录、静默忽略失配）无法被加载，属死重。出口定义：
1. 本地跑挂一次任一 property 测试（如临时收紧一个断言）让 hypothesis 落下**当前 key 形态**的失败样本，观察目录命名形态作对照；
2. `.hypothesis/examples/` 下与当前 58 个 @given 测试 key 形态无法对应的旧目录（audit 期 10 个 digest 0/10 匹配的 key 族）`git rm -r` 删除；
3. **显式接受**：样本库是 go-forward 机制——绿色套件不重新生成失败样本，清理后库可能仅剩 `.gitkeep` + 少量仍匹配的样本；验收 1 的 `wc -l > 0` 由 `.gitkeep` + 存活样本满足（记 spec-deviations：库以「今后失败自动入库」为激活形态，不以历史 43 stale 样本续命）。
4. 提交存活面：`git add .hypothesis/.gitignore .hypothesis/examples/`；`git status --short .hypothesis/` 确认无缓存文件（database/ 被内部 .gitignore 忽略）；`uv run pytest -n auto -m "not last" tests/ -q` 全量绿。

- [ ] **Step 3: CI replay 可见证据**

ci.yml 加**独立一步**（不并入 -n auto 主步骤——58 个 statistics 块会淹日志）：对 property 测试子集运行 `uv run pytest tests/unit -m property -q --no-cov --hypothesis-show-statistics`（若无 property marker 则选 `tests/property/` 目录或 `-k "given"` 集合，执行时以实际组织为准），workflow 日志含 statistics 块。

- [ ] **Step 4: 红灯验证（本地，两段）**

段 1 · 机制：向 `.hypothesis/examples/<当前 key>/` 注入 1 个已知失败样本（本地跑挂一次同测试让 hypothesis 自己落样本后保留），`uv run pytest <该测试> -q` 期望 FAIL，删除注入样本后复跑绿。
段 2 · 新克隆机制证明（验收 1 CI 半的离线同构证据 + spec「statistics 输出不构成重放证明」的满足——**置于 Step 5 commit 之后执行**，使克隆树带上已提交样本；两重断言：a) 提交样本存在时新克隆运行加载样本库；b) 注入失败样本到克隆树同 key 后运行 FAIL、删除后绿）：`git clone --depth 1 <branch 的远端或本地路径> /tmp/sdd55-clone && cd /tmp/sdd55-clone && uv sync --group dev && uv run pytest <同一测试> -q`，然后注入失败样本复跑期望 FAIL，删除后绿。输出粘 progress.md。

- [ ] **Step 5: commit**

```bash
git add .gitignore .hypothesis/.gitignore .hypothesis/examples/ .github/workflows/ci.yml
git commit -m "fix: C17 T1 hypothesis examples committed + CI replay visibility (F1159/F1158)"
```

### Task 2 · T2 internal-links 纯 Python 化 + per-PR CI（F001/F732 · 承载 C23）

**Files:**
- Modify: `tests/integration/test_doc_links.py`（整体重写 internal 分支）
- Modify: `.github/workflows/nightly.yml`（删除冗余 doc-links job；per-PR 覆盖由 ci.yml 既有全量 pytest 步骤自然承载——重写后无 skip、无 npm，ci.yml 本身无需改动）

**Interfaces:**
- Produces: `check_internal_links(doc: Path) -> list[str]`（返回断链描述，空=通过）

- [ ] **Step 1: 重写测试为纯 Python 批量解析**

替换 `tests/integration/test_doc_links.py`：删除 `_require_mlc` fixture 与 subprocess spawn；实现 `check_internal_links(doc: Path) -> list[str]`——**先剥离围栏代码块（``` ... ```）与行内代码 span（`...`）再**正则收集 `[text](target)`（docs/specs/plans 里满是反引号内的链接示例，不剥离会大规模假阳性），排除 `http(s)://`、`mailto:`、纯锚点（`#...`）目标；相对路径以 doc 所在目录解析，`Path.exists()` 判定（`#section` 后缀剥离后再判文件）；保留现有 scope（docs/ rglob + 根 *.md；tests/fixtures、tests/rounds/archived 排除不变）。为解析器边界（锚点后缀、mailto、代码 span 剥离）写单元用例（tmp_path 合成 md 输入——单测输入非 fixtures-dir 条目，G0.9 不适用）。参数化保留 per-doc。

- [ ] **Step 2: 运行验证（371 项不再 skip）**

```bash
uv run pytest tests/integration/test_doc_links.py -q --no-cov
```

期望：0 skip。存量断链（若有）分级：阻断级（真实 rot）立即修链接；登记非阻断进 spec-deviations。已知预期：spec 归档后 INDEX 相对链接由 docs workflow mkdocs --strict 把关，本测试是第二防线。

- [ ] **Step 3: 红灯验证**

临时把 README.md 一条相对链接改坏（指向不存在的文件）→ 该参数化用例 FAIL → 还原 → 绿。输出粘 progress.md（对应验收 2 的本地半；CI 半 = PR 自身 CI 运行本测试即红绿对照）。

- [ ] **Step 4: nightly doc-links job 删除（避免虚假声称）**

事实核查：nightly doc-links job 用的 mlc-config `ignorePatterns: ^https?://` 使其**本就只查内链**——与重写后的 per-PR 测试完全同域，保留即重复防线 + 「nightly 管 external」的虚假声称（本 spec 要消灭的形态）。动作：删除 nightly.yml 的 doc-links job 及头部块对应条目；头部块注明 internal links 已由 per-PR CI 的 tests/integration/test_doc_links.py 覆盖（spec #55）。

- [ ] **Step 5: commit**

```bash
git add tests/integration/test_doc_links.py .github/workflows/nightly.yml
git commit -m "fix: C17 T2 internal-links pure-Python per-PR CI (F001/F732)"
```

### Task 3 · T5 G0.5 权重和校验实装（T1109）

**Files:**
- Modify: `src/shenbi/gates/g0.py:349-350`
- Test: `tests/unit/gates/test_g0_weight_sum.py`（新建）

**Interfaces:**
- Consumes: rubric 文件集 `tests/tiers/**/rubric.md`（表格式，Weight 列为 `10%` 形态；G0.5b 已遍历 `tests/tiers/t1-skill/`，复用其发现逻辑）
- Produces: G0.5 check dict `{"id": "G0.5", "s": GateStatus.PASS|FAIL, ...}`；辅助函数 `_rubric_weight_sum(rubric_path: Path) -> int | None`（None = 无权重行，跳过该 rubric）

- [ ] **Step 1: 写失败测试**

```python
"""G0.5 — rubric weight-sum checker (T1109)."""
import re
from pathlib import Path
import pytest
from shenbi.status import GateStatus


def _make_rubric(tmp_path: Path, weights: list[str]) -> Path:
    rows = "\n".join(f"| {i} | dim{i} | {w} | |" for i, w in enumerate(weights, 1))
    p = tmp_path / "rubric.md"
    p.write_text(f"# R\n## D\n| # | Dimension | Weight | Standard |\n|---|---|---|---|\n{rows}\n", encoding="utf-8")
    return p


@pytest.mark.parametrize("weights,expected", [(["10%", "5%", "50%", "20%", "15%"], 100), (["50%", "40%"], 90)])
def test_weight_sum(tmp_path, weights, expected):
    from shenbi.gates.g0 import _rubric_weight_sum
    assert _rubric_weight_sum(_make_rubric(tmp_path, weights)) == expected


def test_real_rubrics_all_sum_100():
    from shenbi.gates.g0 import _rubric_weight_sum
    rubrics = list(Path("tests/tiers").rglob("rubric.md"))
    assert rubrics, "no rubrics found"
    for r in rubrics:
        total = _rubric_weight_sum(r)
        if total is not None:  # rubrics without weight tables are skipped
            assert total == 100, f"{r}: weights sum to {total}%"


def test_g0_gate_report_contains_real_g05(monkeypatch, tmp_path):
    # G0.5 must no longer be UNIMPLEMENTED: run the real gate entry and assert
    # the G0.5 row is PASS or FAIL — never UNIMPLEMENTED.
    ...
```

（第三用例按 `gate_G0(seed_file, round_dir) -> str`（g0.py:266）补全——它会跑完整 G0 环境布局，需 monkeypatch 模块级根常量 `SKILLS`/`TESTS` 指向 tmp_path 合成树，避免真实环境副作用；从返回的 JSON 报告断言 G0.5 行 `s in {PASS, FAIL}`。）

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/unit/gates/test_g0_weight_sum.py -q
```

期望：FAIL（`_rubric_weight_sum` 不存在）。

- [ ] **Step 3: 实现**

g0.py 中替换 UNIMPLEMENTED 块：`_rubric_weight_sum` 用正则 `\|\s*\d+(\.\d+)?%\s*\|` 从表格行提取权重求和；遍历 `tests/tiers` 全部 rubric.md（t1/t2/t3），全量跑一次实测耗时（70+ 文件、纯文本解析——预期毫秒级；若实测确贵再降采样并注释理由，预期不需要）；sum≠100 的任一 rubric → `GateStatus.FAIL` + `r` 列出文件与和值；无权重表的 rubric 跳过不计失败。

- [ ] **Step 4: 跑测试绿 + 红灯验证（验收 5）**

```bash
uv run pytest tests/unit/gates/test_g0_weight_sum.py -q
```

红灯：临时对某真实 rubric.md 注入一行 `| 99 | x | 3% | |`（破坏和=100）→ `test_real_rubrics_all_sum_100` FAIL → 还原 → 绿。输出粘 progress.md。

- [ ] **Step 5: 全量回归 + commit**

```bash
just test
git add src/shenbi/gates/g0.py tests/unit/gates/test_g0_weight_sum.py
git commit -m "fix: C17 T5 G0.5 rubric weight-sum real implementation (T1109)"
```

### Task 4 · T3 mutation 基线：限时尝试或诚实下线（T1104/F783/F1010/T1102/T1105）

**Files（激活分支）:** `tests/baselines/mutation-score.txt`、`.github/workflows/`（weekly job）、`justfile`
**Files（下线分支）:** Delete `tools/compare_mutation_score.py`、`tests/baselines/mutation-score.txt`；Modify `pyproject.toml`（删 mutmut 依赖 + `[tool.mutmut]`）、`justfile`（删 mutate/mutate-check）、`README*`（若有声称）

- [ ] **Step 1: 限时尝试（时间盒 30 分钟实机 · 偏差已登记）**

**偏差登记（spec-deviations + progress）**：spec 任务 6 定「下线时钟自开工两周」——SDD 单 session 无法跨两周，压缩为 30 分钟实机时间盒；且 mutation 防线已死两个月、根因（editable .pth 沙盒穿透）无既有修复证据，下线为默认预期分支。此压缩构成对 spec 的执行偏差，按纪律显式记录而非静默。

沙盒复制树方案：`git worktree add`（或 cp -r）出干净树 → 树内 `uv run mutmut run`（paths_to_mutate 三文件面）→ 观察是否仍测回原仓库（editable .pth）。若 30 分钟内基线无法建立（空转复现 / 大面积超时不可控）→ 走 Step 2 下线；若建立成功 → mutation-score.txt 写真实值、compare_mutation_score.py 接 weekly workflow（`schedule: cron weekly` + workflow_dispatch，非 per-PR）、T1105 低分模块在 findings-ledger 开新登记行（归属本 spec 后续补测）→ commit 激活分支并跳到 Step 3。

- [ ] **Step 2: 诚实下线（默认预期路径）**

```bash
git rm tools/compare_mutation_score.py tests/baselines/mutation-score.txt
```

pyproject 删 `"mutmut>=3.0.0"` 依赖与 `[tool.mutmut]` 段；justfile 删 `mutate:`/`mutate-check:`；`git grep -ni "mutmut\|mutation-score\|mutate-check"` 全仓对账，残留声称（README/CHANGELOG 除外——CHANGELOG 是历史记录不改写）一并删除；uv.lock 同步（`uv lock`）。T1105/T1102 处置：findings-ledger 回写行注明「mutation 防线经 spec #55 裁决下线（2026-09-08）；T1105 低分模块补测输入随下线失效，escalation 模块覆盖缺口转由 C15 已建 per-module 覆盖底线表承担（tools/check_module_coverage.py 已含 escalation 面）」。

- [ ] **Step 3: 验收 3 核验**

```bash
git grep -n "mutmut" -- ':!docs/superpowers/' ':!CHANGELOG.md'
```

期望：激活分支 = 配置+weekly workflow+真实基线一致；下线分支 = 零命中。输出粘 progress.md。

- [ ] **Step 4: commit（按分支）**

```bash
git add pyproject.toml uv.lock justfile tools/ tests/baselines/ .github/workflows/
git commit -m "chore: C17 T3 mutation defense activated-or-retired (T1104/F783/F1010/T1102)"
```

### Task 5 · T3-9 gate-outputs 基线对账（F782/T1103）

**Files:**
- Delete: `tests/baselines/gate-outputs/{G0,G2-chapter,G2-internal,G2-truth,G6,G7}.json`（6 份无消费者）
- Keep: `tests/baselines/gate-outputs/G4-genre_config.json`（唯一消费者 tests/unit/test_scoring.py:1267）
- Delete: `tests/regenerate-baselines.sh`（再生成路径已死：tests/rounds 不存在）
- Modify: findings-ledger F782/T1103 回写（归档阶段统一做，此处记 spec-deviations）

- [ ] **Step 1: 确认零消费者后删除**

```bash
grep -rn "gate-outputs" tests/ src/ tools/ justfile .github/ --include="*.py" --include="*.sh" --include="*.yml" --include="justfile" | grep -v test_scoring
```

期望：除 regenerate-baselines.sh 自身外零命中 → 删 6 份 + 脚本。若发现意外消费者：该基线转 Keep 并在 spec-deviations 记录。

- [ ] **Step 2: 回归 + commit**

```bash
uv run pytest tests/unit/test_scoring.py -q --no-cov
git rm tests/baselines/gate-outputs/G0.json tests/baselines/gate-outputs/G2-chapter.json tests/baselines/gate-outputs/G2-internal.json tests/baselines/gate-outputs/G2-truth.json tests/baselines/gate-outputs/G6.json tests/baselines/gate-outputs/G7.json tests/regenerate-baselines.sh
git commit -m "chore: C17 retire unconsumed gate-outputs baselines, keep G4-genre_config (F782/T1103)"
```

### Task 6 · T4 golden/benchmark/压力 prompt 诚实化（F741/F742/F1160/T1101）

**Files:**
- Delete: `tests/golden/README.md`（承诺的评测集无真实数据源可建——novel-output 真实树不在仓库；golden 评测属 T3 真实 dispatch 域，SDD 禁现场 dispatch 取证 → 唯一合法分支是删承诺）
- Move: `tests/pressure-tests/prompts/*.md` → `docs/superpowers/design/pressure-scenarios/`（降级为设计材料；接 harness 需真实 dispatch 同样被核心原则 8 排除）
- Modify: `pyproject.toml:439-440`（删死条目 `"tests/benchmarks"`；删 `"tests/pressure-tests"` 排除——目录移空后不再存在）
- Delete: 本地 `.benchmarks/Darwin-CPython-3.11-64bit/0001_*.json`（未跟踪的冒烟 autosave；`.gitignore:32` 已忽略 `.benchmarks/`，保持）

- [ ] **Step 1: golden 承诺删除**

```bash
git rm tests/golden/README.md && rmdir tests/golden 2>/dev/null; grep -rn "golden" tests/ README* --include="*.md" | grep -vi "golden-3\|goldens"
```

期望：对账零残留声称（tests/golden 引用全部消失）。

- [ ] **Step 2: 压力 prompt 移档**

```bash
mkdir -p docs/superpowers/design/pressure-scenarios
git mv tests/pressure-tests/prompts/*.md docs/superpowers/design/pressure-scenarios/
git rm tests/pressure-tests/prompts/.gitkeep 2>/dev/null; rm -rf tests/pressure-tests
```

docs/superpowers/design/ 若无 README 则加一行说明这 6 份是 2026-08-15 审计期压力场景设计材料（非可执行 harness）。

- [ ] **Step 3: pyproject 死配置清理 + benchmark 保持收集**

删除 norecursedirs 中 `"tests/benchmarks"`（指向不存在目录）与 `"tests/pressure-tests"`（目录已移除）。`tests/benchmark` 保持被收集：

```bash
uv run pytest tests/benchmark --collect-only -q --no-cov | tail -3   # 期望 3 collected（#153 用例不受影响；--no-cov 避免 collect-only 触发 85% 覆盖门）
```

- [ ] **Step 4: 验收 4 对账 + commit**

```bash
grep -rn "golden" tests/ README* | grep -vi "golden-3\|goldens" ; ls tests/golden 2>&1   # 期望：零声称残留（golden-3/goldens 为 G4 测试名合法语义）、目录消失
git add pyproject.toml docs/superpowers/design/pressure-scenarios/
git commit -m "chore: C17 T4 golden/benchmark/pressure honesty cleanup (F741/F742/F1160/T1101)"
```

### Task 7 · 门禁 + findings-ledger 回写收尾

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（C17 成员行状态回写）

- [ ] **Step 1: just check 全量**

```bash
just check
```

期望 exit 0（注意：uv.lock 若在 T4 改动则 `uv lock --check` 须过；新增 doc-links 用例计入全局覆盖率）。无新增 skip（验收 6）：`uv run pytest tests/integration/test_doc_links.py -q` 0 skipped。

- [ ] **Step 2: ledger 回写**

18 成员（F001, F732, F741, F742, F782, F783, F1010, F1158, F1159, F1160, T1101-T1107, T1109）状态 open → closed，注明 `(C-17 spec #55, PR #<N>)` + 一句话处置（激活面/下线面）。T1106（压力场景计数）随移档消解。

- [ ] **Step 3: commit**

```bash
git add docs/superpowers/audit-runs/2026-08-15/findings-ledger.md
git commit -m "docs: C17 findings-ledger writeback — 18 members closed (spec #55)"
```

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 样本入库+重放+红灯 | T1 | `git ls-files .hypothesis/examples \| wc -l` > 0（.gitkeep + 存活样本；stale 43 删除为显式出口，见 T1 Step 2）；本地机制红灯 + 新克隆注入红灯（CI 半的离线同构证据）；CI statistics 步骤随 PR 运行 |
| 2 internal-links per-PR 红灯 | T2 | 改坏 README 链接 → `uv run pytest tests/integration/test_doc_links.py -q` FAIL → 还原绿 |
| 3 mutation 激活或下线一致 | T4 | `git grep -n "mutmut" -- ':!docs/superpowers/' ':!CHANGELOG.md'` 与所选分支一致 |
| 4 golden/benchmark 声称=磁盘 | T6 | `grep -rn "golden" tests/ README* \| grep -vi "golden-3\|goldens"` 零残留；`pytest tests/benchmark --collect-only --no-cov` 3 collected |
| 5 G0.5 负样本红灯 | T3 | 注入权重≠100 rubric → test FAIL → 还原绿 |
| 6 just check/test 绿 + 无新增 skip | T7 | `just check` exit 0；doc-links 0 skipped |

## 涉及评分场景

无（本 spec 不含 LLM 评分验收）——G3.4 不适用。
