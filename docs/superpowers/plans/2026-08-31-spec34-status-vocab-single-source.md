# spec #34 状态/词表单源收编 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每个状态概念恰一个主词表、生产越表被 lint 机械拦截（novel-output 全树 + repo 全量）、HARD_FAIL/severity/mode 越表实例清零（spec `docs/superpowers/specs/2026-08-16-audit-status-vocab-single-source-fix.md` v3）。

**Architecture:** T1 机器可解析登记表 `docs/framework/status-vocab.md` 为唯一裁决依据 → T2 enums/base/status 收编 + 死代码清理 → 状态域建域（spec T4）→ 生产越表修复 + G4 值域校验 + severity 复算脚本（spec T5）→ **lint 白名单反转 + 登记表对账 + 双面扫描最后落地**（spec T3，与修复同批保证 `just check` 终点绿）→ 文档对齐。执行顺序与 spec 编号不同仅因 lint 反转必须后置。

**Tech Stack:** Python 3.11+/StrEnum/Literal、ast 扫描（沿用 lint_status_strings 既有实现扩展）、pytest、just。

## Global Constraints

- 状态字面量唯一定义于登记表登记的主词表；新增裸状态字符串 = lint 红（Critical）。
- `src/shenbi/` 无 `print()`（structlog）；gate 检查器纯函数幂等。
- 验证一律 `uv run` / `just`（CI 同构）；fixtures 只用真实产物（G0.9）。
- commit 用 conventional commits，显式 pathspec。
- 全部 task 为 **infra**（contracts/gates/pipeline/tools）——协调者亲自实现，逐 task fresh-context 重审产出 `audit-T<N>.md`。

## 登记表裁决（T1 产出钉固，实施不得偏离）

对 T9 矩阵 40 行的逐域裁决（域→主词表→处置）：

| 域 | 主词表 | 裁决 |
|---|---|---|
| GateStatus | status.py | canonical；base.py:29 `GateOutcome.status` 改 `Literal`→`GateStatus` 类型注解（T904，值集含 UNIMPLEMENTED） |
| PhaseState/CommandStatus/ScoringStatus/ScoreClassification | status.py | 保留；CommandStatus 增 `DEGRADED = "degraded"`、`NOT_IMPLEMENTED = "not_implemented"`（T908，truth_embed.py:247 / cli.py 未实现面改用成员） |
| enums.Severity（BLOCKING/CRITICAL/MINOR） | enums.py | 保留 = 审计严重度域 |
| decisions.Severity → **SeverityLevel** | schemas/decisions.py | 改名消同名冲突（F211），值 low/medium/high 不变 = decisions 严重度域 |
| revision-decisions severity 生产域 | enums.py `RevisionSeverity = low/medium/high` | T903：SKILL 枚举化 + G4 值域校验；消费侧容错映射 blocking/critical/critical_per_audit→high、warning→medium、minor/info/none/observation→low（39 越表值全映射，AC2 21.1%→0%） |
| enums.Verdict（通过/有瑕疵/不通过） | enums.py | 保留 = review-* md 判定域 |
| resonance 判定 | enums.py `ResonanceVerdict = 通过/阻断/待人机复核` | T902：review_resonance.py `_VERDICTS` 裸 tuple 删除改 import |
| progress skill status | status.py `SkillProgressStatus = pending/done/skip` | T906：codex.py:44 / trace/materialize.py `_empty_skill` 改用；g_reconcile.py:40,70 `.upper()=="DONE"` 改 `== SkillProgressStatus.DONE.value`（大小写归一保留读旧 "DONE"） |
| ChapterState.status | pipeline/state.py `ChapterStatus = StrEnum{pending,in_progress,complete,settling_failed}` | T907：序列化值仍 `in-progress`（`IN_PROGRESS = "in-progress"`）；`PipelineState.from_dict`（state.py:~311）`completed→complete` 归一 + structlog WARN；写方 chapter_loop.py:1034/error_handler.py:115 改成员 |
| GenesisState/ClosureState | state.py | 保留独立域（值 pending/in-progress/checkpoint-pending/completed，genesis 语义登记） |
| RevisionMode | enums.py `RevisionMode = spot-fix/regenerate/constrained-regenerate/reconstruction/no-revision` | T910：route.py:28 与 revision_router.py:33 双域合一改 import；消费侧 alias `no_op→no-revision`；G4 校验 |
| ReviewDecision | state.py | 保留（命令域 approve/modify/reject） |
| genre approval.decision | enums.py `ApprovalDecision = approved/rejected` | T909：独立登记域；genre_config.py:41-44 validator 改 import 比对 |
| content_preservation status | enums.py `ContentPreservation = preserved/skipped/delegated/reconstructed_from_cross_source_evidence` | 立域（T9 行38） |
| 修订 verdict.status | enums.py `RevisionVerdictStatus` | 立域，值以生产实测定（实施时 grep novel-output revision-decisions verdict.status 值集后落表） |
| novel.json status | enums.py `NovelStatus = worldbuilding/worldbuilding_complete` | T911：生产两文件均持值 → 立域不删字段 |
| OutputKind/RegistryKind/Producer/ownership/HookState/Basis/Handling/Trim/PipelinePhase/CheckpointType 等 | 各原位 | 登记不动（已立案族注记移交编号） |
| F220 VALID_BASIS/VALID_SEVERITY | — | **已修**（g4/_decisions_schema.py 已删，仅 tests/coverage 陈旧 HTML 残留）——spec-deviations 记已修 |
| F221 ScoreReport 双定义 | skills/_scoring_base.py | schemas/scores.py:31 ScoreReport 零生产 import（F205 复核）→ 删除模块，_scoring_base 为唯一 |
| F336/F352 chapter=0 vs None | state.py `current_chapter: int | None = None` | genesis.py:260 `chapter=0` 与 state.py:145 统一 None 为"genesis 未进章"语义，读方判 `is None`；登记"genesis 语义"注记 |
| F441 check id 前缀 | scoring checker id | 值域 `"<skill>:<check-slug>"` 形态登记（id 命名词表），实施时对无前缀 checker 补技能前缀 |
| escalation severity regex 域 | 消费 enums.Severity | revision_router.py:75-86 / parallel_dispatch.py:218-220 / audit_layer.py:157 大小写归一后比对 enums.Severity（regex 域不另立） |

---

### Task 1: 登记表 + 双单源文案修正（spec T1 + T901 docstring）

**Files:**
- Create: `docs/framework/status-vocab.md`
- Modify: `src/shenbi/contracts/enums.py:1`（docstring）
- Modify: `src/shenbi/status.py:1-8`（docstring）
- Test: `tests/unit/tools/test_status_vocab_registry.py`

**Interfaces（Produces，Task 5 lint 对账消费）:**
- 登记表格式（每域一行，Task 5 的解析器按此读取）：

```markdown
# 状态词表登记表（唯一裁决依据）

| 域 | 主词表 | 合法值 | 生产写方 | 生产读方 |
|---|---|---|---|---|
| GateStatus | shenbi.status.GateStatus | PASS\|FAIL\|SKIP\|WARN\|UNIMPLEMENTED | gates/* | gates/cli, scoring |
```

- 合法值列以 `\|` 分隔；主词表列为 `module.Symbol` 全限定名。

**Steps:**
- [ ] 写登记表全 40+ 行（按上表裁决逐域落值；生产读写方列按 T9 矩阵 + 实施时 grep 核对）
- [ ] enums.py:1 docstring 改：`"""词表登记见 docs/framework/status-vocab.md（唯一裁决依据）。本模块承载其中 enums 域。"""`；status.py 头部 docstring 同步指向登记表并删 "THE single definition" 绝对化表述
- [ ] 测试：解析登记表 markdown（固定 5 列），断言 (a) 每行主词表符号可 import（`importlib`）(b) 合法值列 == 该符号实际 Literal 值/StrEnum 成员值集合（本 task 先覆盖已存在域，Task 5 扩为 lint 子检查）
- [ ] `uv run pytest tests/unit/tools/test_status_vocab_registry.py -v` PASS
- [ ] commit `feat: status-vocab registry (spec #34 T1) + dual-single-source docstring fix (T901)`

### Task 2: enums/status/base 收编 + 批量死代码（spec T2 + F221/F336/F352）

**Files:**
- Modify: `src/shenbi/contracts/enums.py`（新增 ResonanceVerdict/RevisionSeverity/RevisionMode/ApprovalDecision/ContentPreservation/RevisionVerdictStatus/NovelStatus，入 ALL_ENUMS）
- Modify: `src/shenbi/contracts/base.py:29`（`status: GateStatus`，import shenbi.status）
- Modify: `src/shenbi/contracts/schemas/decisions.py:16`（`Severity`→`SeverityLevel`，全仓 import 点同步改名）
- Modify: `src/shenbi/gates/g4/review_resonance.py:25`（`_VERDICTS` 改 import `enums.ResonanceVerdict` 元组派生）
- Delete: `src/shenbi/contracts/schemas/scores.py`（F221/F205 死模块；先 grep 确认零 src import、tests 引用改 _scoring_base 或删）
- Modify: `src/shenbi/pipeline/state.py:145` + `src/shenbi/pipeline/genesis.py:260`（chapter=None 统一，读方 `== 0` 判定改 `is None`）
- Test: 既有 `tests/unit/contracts/`、`tests/unit/gates/g4/` + 新增 `tests/unit/contracts/test_enums_consolidation.py`

**Steps（每域独立 commit）:**
- [ ] TDD：`test_enums_consolidation.py` 断言新 Literal 值集、`GateOutcome` 注解为 GateStatus、decisions.SeverityLevel 存在且旧名不存在
- [ ] 逐域实施 + `uv run pytest tests/unit/contracts tests/unit/gates -x -q` + `uv run basedpyright src/shenbi/contracts/` 干净
- [ ] F336/F352：改后跑 `uv run pytest tests/unit/pipeline -q` 全绿（genesis chapter=None 语义）
- [ ] commits：`fix: consolidate status vocabularies into enums.py (spec #34 T2: T902/T904/F211/F221/F336/F352)`（可拆多笔）

### Task 3: 无主域建域 + 兼容归一层（spec T4）

**Files:**
- Modify: `src/shenbi/status.py`（SkillProgressStatus；CommandStatus 增 DEGRADED/NOT_IMPLEMENTED）
- Modify: `src/shenbi/pipeline/state.py:98,~311`（ChapterStatus StrEnum；from_dict 归一 `completed→complete` + structlog WARN）
- Modify: `src/shenbi/pipeline/chapter_loop.py:1034`、`src/shenbi/pipeline/error_handler.py:115`（写方改成员）
- Modify: `src/shenbi/pipeline/truth_embed.py:247`（`CommandStatus.DEGRADED`）
- Modify: `src/shenbi/dispatcher/modes/codex.py:44`、`src/shenbi/trace/materialize.py`（SkillProgressStatus）
- Modify: `src/shenbi/gates/g_reconcile.py:40,70`（比对 SkillProgressStatus.DONE.value，兼容旧大写 "DONE"）
- Modify: `src/shenbi/revision_routing/route.py:28`、`src/shenbi/pipeline/revision_router.py:33`（import enums.RevisionMode；消费侧 `no_op` alias 归一 `no-revision`）
- Modify: `src/shenbi/contracts/skills/genre_config.py:41-44`（ApprovalDecision import 比对）
- Test: `tests/unit/pipeline/test_chapter_status_vocab.py`（新增）+ 既有 pipeline/gates 测试

**Steps:**
- [ ] TDD：新测试覆盖 (a) from_dict `completed` 归一 `complete` + WARN（caplog 断言）(b) 非法 status 值 → ValueError 结构化 (c) RevisionMode alias (d) g_reconcile 兼容 "DONE"/"done"
- [ ] 实施；`uv run pytest tests/unit/pipeline tests/unit/gates -x -q` 全绿
- [ ] `uv run python -c "from shenbi.pipeline.state import PipelineState; PipelineState.from_dict({'chapter_loop':{'chapter_states':{'1':{'status':'completed'}}}})"` 归一无异常
- [ ] commit `fix: establish ownerless status domains + compat normalizer (spec #34 T4: T906-T911)`

### Task 4: 生产越表修复 + G4 值域 + 复算脚本（spec T5 + F402/F711/T903/T204）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_revision.py:38,97`（HARD_FAIL→`GateStatus.FAIL` + `"severity": enums.Severity.BLOCKING` 标注；解 pin `tests/unit/gates/g4/test_chapter_revision.py:112,142,155,179`）
- Modify: `skills/shenbi-chapter-revision/SKILL.md`（severity 枚举化 low/medium/high 说明）
- Modify: `src/shenbi/gates/g4/chapter_revision.py`（G4 对 revision-decisions severity/mode 值域校验：severity∈RevisionSeverity（含容错映射表）、mode∈RevisionMode）+ `src/shenbi/gates/g0_skill_contract.py:133-137`（T204：mode 值合法性 ∈ 登记词表 `update_mode`/`write_mode` 值域）
- Create: `tools/check_severity_vocab.py`（AC2 复算：扫 novel-output/**/revision-decisions*.json 的 severity 值，越表=不在 RevisionSeverity 且不在容错映射；exit 0 输出越表率 0%）
- Modify: `justfile`（lint 块加 `uv run python tools/check_severity_vocab.py`）
- Test: `tests/unit/gates/g4/test_chapter_revision.py` 更新 + `tests/unit/tools/test_check_severity_vocab.py`（fixtures 驱动：用 `tests/fixtures/` 真实 revision-decisions 产物）

**Steps:**
- [ ] TDD：先改 test_chapter_revision 断言 FAIL+severity（红）→ 实施（绿）
- [ ] `git grep -rn "HARD_FAIL" src/` 零命中（或仅 enums/登记表注释）
- [ ] `uv run python tools/check_severity_vocab.py` → 输出 `out-of-vocab: 0/185 (0.0%)` exit 0
- [ ] commit `fix: production vocab violations — HARD_FAIL, severity/mode G4 value-domain checks (spec #34 T5)`

### Task 5: lint 白名单反转 + 登记表对账 + 双面扫描（spec T3，最后落地）

**Files:**
- Modify: `tools/lint_status_strings.py`（重写检测面）
- Test: `tests/unit/tools/test_lint_status_strings.py`（新增/扩展）

**Interfaces（Consumes Task 1 登记表格式）:**
- 新 CLI：`uv run python tools/lint_status_strings.py [--scan-tree DIR]`
- 子检查三面：
  1. **裸字面量面**（反转）：`Path(__file__).resolve().parents[1]` 锚定 repo 根，扫 `src/shenbi/**/*.py` + `tests/**/*.py`（status.py/enums.py 豁免），dict 键 `status/state/classification/s` 的值表达式里**任何**不在登记表全集的裸 str 字面量 = 违规（原"仅拦已知值"改为"拦一切裸值"，成员经枚举表达式不受影响）
  2. **登记表对账面**：解析 status-vocab.md 全表 ↔ AST 提取 src/shenbi 全部 Literal/StrEnum 域，双向比对（代码域未登记/登记域不存在/值集不等 = 违规）
  3. **生产值面**（`--scan-tree`）：对给定树（AC1 用 `novel-output`）全部 .json 递归收集 status/severity/mode/decision 键值，越登记表全集（含 Task 3/4 容错映射）= 违规
- exit 非 0 = 有违规；`just check` 既有接线（justfile:15,48）不变

**Steps:**
- [ ] TDD：对每面写红样本（裸 `{"s": "PASSED"}`、登记表漏域、`--scan-tree` 对 fixture 树越表值）
- [ ] 实施；`uv run python tools/lint_status_strings.py --scan-tree novel-output` exit 0
- [ ] `just check` 全绿（本 task 与 Task 1-4 同批已在分支上，无中间红窗口残留）
- [ ] commit `feat: lint_status_strings inversion + registry reconciliation + tree scan (spec #34 T3)`

### Task 6: 文档对齐 + 验收终跑（spec T6）

**Files:**
- Modify: `AGENTS.md`（如有内嵌词表值→指向登记表）、`docs/framework/decisions-schema.md` 等 grep 命中处
- Modify: `docs/superpowers/specs/INDEX.md`（不动，归档期处理）

**Steps:**
- [ ] `git grep -l "PASS.*FAIL.*SKIP.*WARN" docs/ AGENTS.md` 逐处改为指向 `docs/framework/status-vocab.md`
- [ ] AC 终跑五条（AC1 lint 双面 exit 0 / AC2 复算 0% / AC3 HARD_FAIL grep / AC4 对账子检查 / AC5 `just check`），输出粘贴 progress.md
- [ ] commit `docs: align status vocab references to registry (spec #34 T6)`

## 验收覆盖表

| spec AC | task | 验证命令 |
|---|---|---|
| AC1 lint 修复前假阴性/修复后 exit 0 | Task 5 | `uv run python tools/lint_status_strings.py --scan-tree novel-output` |
| AC2 severity 越表 21.1%→0% | Task 4 | `uv run python tools/check_severity_vocab.py` |
| AC3 HARD_FAIL 零残留 | Task 4 | `git grep -rn "HARD_FAIL" src/` |
| AC4 登记表对账 | Task 5 | lint 对账子检查（just check 内含） |
| AC5 just check 全绿 | Task 6 | `just check` |

G3.4 说明：本 spec 无生成型输出评分场景，全部验收为机械命令/测试，无需评分子 agent。
