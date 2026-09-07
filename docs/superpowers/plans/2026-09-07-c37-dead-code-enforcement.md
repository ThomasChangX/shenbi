# C37 死代码清理与零接线执法 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按当前 main 现判收口 C37 簇 43 条 findings（7 已修关闭、~27 处存活面三桶裁决），清除假防线、批量删除死面，并落地 CI dead-code 执法门。

**Architecture:** R0 分桶表是硬闸（每编号一行，未经认领的删除禁止合入）；R1 假防线优先（error_guidance/recovery 整删 + 谎称接线注释清理）；R2 按 R0 表批量删（含 F427 三 checker 合一、T1506 legacy 改名、F325 fail-fast 接线）；R3 以 vulture（min-confidence 60 + 白名单文件——unused function 报 60% 置信度）接入 `just check` 与 CI。

**Tech Stack:** Python 3.11+/uv、pytest、vulture（新增 dev 依赖）、just、GitHub Actions。

## Global Constraints

- 每删除必先过 R0 表认领；表外删除禁止
- CLI 入口（shenbi-validate/score/dispatch/phase/sync-contracts、pipeline 子命令）不破调用方：删模块前核对 `__init__` re-export、pyproject console-scripts、justfile/CI 调用面
- 直测死函数的自证测试随删（C14 协同），`uv run pytest -n auto` 无 skip 增量
- 验证一律 `just`/`uv run`（与 CI 同构）；框架代码无 `print()`（structlog）；pathlib；conventional commits
- 全程禁真实 LLM dispatch（核心原则 8）；无 fixture 新造（G0.9）
- 每个 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`

---

### Task 1: R0 分桶裁决表（硬闸，先于一切动作）

**复杂度: infra（协调者亲自）** · **test_kind: n/a（文档产物）**

**Files:**
- Create: `docs/superpowers/audit-runs/2026-08-15/c37-triage.md`

**Interfaces:**
- Produces: 43 数据行表（列：Finding | 形态摘要 | file:line（当前 main） | 桶 wire/delete/defer/already-fixed | 执行者/认领方 | 备注）。后续 T2-T6 逐行执行，行号引用以本表为准。

预裁基准（执行时逐行复核后定稿）：already-fixed 7（F243/F346/F366/F512/F611/F903/F1027）；delete ~24（F108/F109/F110/F118/F226/F230 验证段/F314/F315+F793 drift/F316/F325 或 wire/F343+T1612/F345/F368 或 defer/F378/F427 合一/F471/F622 recall helper/F632 migrate/F631 组内 trace compact()/F641/F642 余量/F706/T301/T1506）；defer ≤5（F886 genesis 断流=产品缺陷、F319/F321 现判、F313 rebuild-即弃半面、F368 视 C33 语义）。

- [ ] **Step 1:** 逐 finding 打开当前 main 的 file:line 复核形态（阶段 1 驳斥表为底稿，F319/F321 按重构后代码现判：`src/shenbi/pipeline/review_checklist.py:426` split 段、`chapter_loop.py:2891+` 串行/并行审计路径）
- [ ] **Step 2:** 写表 43 数据行，每行一桶一执行者；行首锚定 `| F###`/`| T###`
- [ ] **Step 3:** 验证行数：`python3 -c "import re,pathlib; t=pathlib.Path('docs/superpowers/audit-runs/2026-08-15/c37-triage.md').read_text(); print(len(re.findall(r'^\| [FT]\d', t)))"` 输出 `43`
- [ ] **Step 4:** Commit `docs(c37): R0 triage table — 43 findings bucketed per current main`
- [ ] **Step 5:** 产出 audit-T1.md（fresh-context 重审）

### Task 2: R1 A 类假防线清除

**复杂度: infra** · **test_kind: regression_guard（删除后全量回归）**

**Files:**
- Delete: `src/shenbi/error_guidance.py`, `src/shenbi/recovery.py`
- Modify: `src/shenbi/exceptions.py`（删 7 个从未 raise 的类：ScoringError/ScoringRejectError/MigrationError/DefectApplicationError/RegistryCorruptError/ConfigurationError/SubAgentUnavailableError）
- Modify: `src/shenbi/pipeline/state.py:521`（删 `_validate_state_consistency` + 假注释）
- Modify: `src/shenbi/contracts/skills/pacing_design.py:67-72,82,131`（删不可达 3-window 校验与 `chapter_sequence` 透传；G4 no_beat_data 分支保留为空表 skip 路径）
- Delete tests: 引用被删符号的全部测试（grep 定位，如 `tests/unit/gates/test_g1_fields.py` 属 T301 归 T4）

**Interfaces:**
- Consumes: R0 表对应行（F108/F109/F110/F118 部分/F230/F378/F886 注记）
- Produces: 无新公共面；`shenbi.exceptions` 导出面收窄（调用方 grep 零引用后删）

- [ ] **Step 1:** `grep -rn "error_guidance\|from shenbi import recovery\|ScoringRejectError\|RegistryCorruptError\|_validate_state_consistency" src/ tests/` 收集全部引用点，逐一对 R0 表核对后删除（含 tests）
- [ ] **Step 2:** 删 F886 谎称面：`src/shenbi/pipeline/cli.py:497-500` genesis 写点上注释如实标注"write-only，零消费者（F886 defer——种子断流为产品缺陷，移交后续 spec）"
- [ ] **Step 3:** `uv run pytest -n auto -m "not last" -q` 全绿 + skip 数不增（记录前后数）
- [ ] **Step 4:** 抽查验收：`git grep -n "error_guidance\|Consumed by CLI" -- src/ docs/` 与 R0 表裁决一致；另枚举 5 处声称接线注释/文档（R0 表 F108/F109/F378/F343/F345 行）逐条核对与真实调用图一致，结果记入验收证据
- [ ] **Step 5:** Commit `chore(c37): remove A-class false-frontline — error_guidance/recovery, 7 dead exceptions, F378 dead validator, F230 unreachable validation`
- [ ] **Step 6:** audit-T2.md

### Task 3: R2 批量删除 · 死模块/死表/死缓存组

**复杂度: infra** · **test_kind: regression_guard**

**Files（均按 R0 表 delete 行执行）:**
- Delete: `src/shenbi/pipeline/volume_align.py` + `tests/pipeline/test_volume_align.py` + `tests/pipeline/test_step3_assembly_gate.py` 中 volume_align 引用面（F314）
- Modify: `src/shenbi/pipeline/chapter_loop.py:439`（删 CONDITIONAL_STEPS 死表）, `:1774`（删 `_should_run_drift` + `pyright: ignore`）, `:1174`（删 build_index 即弃调用，按 R0 F313 行裁决）
- Modify: `src/shenbi/pipeline/state.py:435,459`（删 `_archive_chapter_state`/`compact_pipeline_state`）
- Modify: `src/shenbi/trace/`（删 `compact()`；删 `migrate_from_progress` 及 `trace/__init__.py:6` 导出）
- Modify: `src/shenbi/records/__init__.py:7-12`（删 serialize_records/is_idempotent 导出）、`src/shenbi/text`（删 count_words/tokenize，保 count_punctuation 与其数据依赖 PUNCTUATION_TOKENS——cjk.py:106 消费 .items()，F642 的 PUNCTUATION_TOKENS 零消费主张对该常量不成立，R0 表 F642 行照此收窄）
- Modify: `src/shenbi/contracts/schemas/state.py:19,25`（删 ProgressDoc/SummaryDoc）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:220-260`（删 `_genre_config_cache` + `_load_genre_config_cached`——F343+T1612 同点，死缓存与错误路径一并消）
- Modify: dispatch_helper `skip_paths` 假象面（F226：删未被喂养的 skip_paths 参数与 docstring 声称，skills frontmatter 的 `no_op_behavior: skip_write` 声明如仍零消费则一并删并跑 `just generate` 同步）
- 同步删除上述全部直测/引用测试。

- [ ] **Step 1:** 逐符号 grep **全 src/**（不排除定义文件，仅排除定义行本身；同文件命中逐条人工复核——同模块存活函数是常见隐藏消费方，cjk.py PUNCTUATION_TOKENS 即实例）确认为零后删；有调用方的（与 R0 表冲突）→ 停，记 deviation 回 R0 改行
- [ ] **Step 2:** `just check` 全绿（契约面若动 SKILL frontmatter：`just generate` diff 为空）
- [ ] **Step 3:** `uv run pytest -n auto -q` skip 无增量
- [ ] **Step 4:** Commit `chore(c37): R2 batch deletion — volume_align/CONDITIONAL_STEPS/compact-pair/trace dead lines/records+text exports/ProgressDoc+SummaryDoc/genre cache`
- [ ] **Step 5:** audit-T3.md

### Task 4: R2 续 · 死参数/直测死函数/F427 合一/T1506 改名/F325 接线

**复杂度: infra** · **test_kind: tdd_red_green（F325）+ characterization（F427）+ regression_guard**

**Files:**
- Modify: `src/shenbi/scoring.py:433,443`（删 `_phase` 死参，F118）；`src/shenbi/pipeline/dispatch_helper.py:2707,2807`（F345：删 timeout 形参，体内本用 `_compute_dispatch_timeout`；调用方同步）
- Delete: `src/shenbi/gates/g1.py:106` `check_fields_exist` + `tests/unit/gates/test_g1_fields.py`（T301）
- Delete: `tests/unit/gates/g4/conftest.py:13,27` 两死 fixture（F706，先 grep 确认零引用）
- Modify: `src/shenbi/gates/g4/score_arc.py` + `score_stratum.py` + `score_volume.py` → 合一 `src/shenbi/gates/g4/scoring_sections.py`（F427）：参数化 checker，`generic.py:315-349` 改 import/注册
- Modify: `src/shenbi/contracts/legacy.py` → 改名（按内容定真名，如 `contracts_registry.py`），删 `contracts/__init__.py:49` re-export shim，全仓引用点全改（T1506，实测 `grep -rn "contracts\.legacy"` src/ 7 + tests/ 23 + tools/ 2 = 32 处，其中 tests 含 patch 字符串；另 grep `from shenbi.contracts import legacy` 变体一并改）
- Modify: `src/shenbi/pipeline/cli.py:755,856`（F325：`_verify_truth_integrity` 返回 list[str] 接线 fail-fast——非空则 `err` 输出并以非零退出中止 resume）

**F427 合一签名（Produces，T4 内自洽）：**
```python
def g4_scoring_sections(
    fps: list[str],
    skill_id: str,            # "shenbi-score-arc" 等，用于 gate 名与消息前缀
    required_sections: list[tuple[str, str]],  # [(normalized_marker, missing_msg), ...]
    alt_anchor: str | None = None,             # "锚点" 类替代命中
    rd: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str
```

- [ ] **Step 1 (F325, TDD 红灯):** 在 `tests/` 既有 cli resume 测试文件加用例：构造缺 truth 文件的 state → resume 路径返回非零且 stderr 含缺失清单。跑之，确认 FAIL
- [ ] **Step 2 (F325 绿灯):** 实现接线；单测 PASS
- [ ] **Step 3 (F427, characterization):** 为三个现有 checker 各留一条真实产物断言（fixtures 引用现有 G4 测试 fixture 路径），合一后断言不变
- [ ] **Step 4:** 其余删除（F118/F345/T301/F706）逐符号 grep 后执行
- [ ] **Step 5:** `just check` 全绿；`uv run pytest -n auto -q` skip 无增量
- [ ] **Step 6:** Commit `chore(c37): F427 checker unification, T1506 legacy rename, F325 fail-fast wiring, dead params + directly-tested dead functions removal`
- [ ] **Step 7:** audit-T4.md

### Task 5: R3 CI dead-code 执法门（vulture）

**复杂度: infra** · **test_kind: tdd_red_green（负例：新增零调用函数必须 FAIL）**

**Files:**
- Modify: `pyproject.toml` dev 组加 `"vulture>=2.11"`（R3 选型裁定：vulture；spec ≥80 修正为 60，记录 spec-deviations）
- Create: `tools/vulture_allowlist.py`（白名单：R0 defer 项 + 公共 API 面 + 文件头注明"季度复核 deferred 项"）
- Modify: `justfile` `check` target 追加一行 `uv run vulture src/shenbi --min-confidence 60`
- Modify: `.github/workflows/ci.yml` 在 lint 段同位置追加同一命令（保持与 just check 同构）

**Interfaces:**
- Produces: CI 门禁；验收负例 = 临时在 `src/shenbi/` 加零调用函数 → 命令非零退出（验收后撤销）；白名单内项 → PASS

- [ ] **Step 1:** `uv add --group dev "vulture>=2.11"` + `uv lock`；`uv lock --check` 通过
- [ ] **Step 2:** 跑 `uv run vulture src/shenbi --min-confidence 60` 收集全量报告 → 逐项处置：该删的漏网（对照 R0 表）回 T2-T4 补删；真公共 API/deferred 入白名单（每行注 F 编号或 API 理由）
- [ ] **Step 3:** 基线清零：该命令 exit 0
- [ ] **Step 4 (红灯验收):** `echo $'\ndef _c37_negative_probe():\n    return 1\n' >> src/shenbi/status.py` → 重跑命令，确认非零（unused function 于 60% 置信度命中）→ `git checkout -- src/shenbi/status.py` 撤销，重跑确认 0。两段输出都记入验收证据
- [ ] **Step 5:** `just check` 全绿（含新门）
- [ ] **Step 6:** Commit `feat(c37): vulture dead-code gate in just check + CI, allowlist with quarterly-review header`
- [ ] **Step 7:** audit-T5.md

### Task 6: R4 移交 + 回写 + 收口

**复杂度: infra** · **test_kind: n/a（文档/账务）**

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-audit-weak-assertions-fix.md`（#52 C14 spec）验收追加一条："直测对象全部为生产可达路径（C37 R4 移交）"
- Modify: 本 spec（C37）R3 段 vulture 置信度表述与验证命令一致（60，已同步则核验）
- Modify: `docs/superpowers/audit-runs/2026-08-14/findings-ledger.md`：C37 全部成员按 R0 表回写 merged-into F108 / already-fixed 注明修复 spec
- Modify: `docs/superpowers/audit-runs/2026-08-15/c37-triage.md` 若执行中出现改行，同步定稿
- F886 defer 若裁定需后续 spec：INDEX.md append-only 登记新条目（P2），否则 defer 行注记即可

- [ ] **Step 1:** 回写 findings-ledger（grep 每个 F/T 编号定位行，按 R0 表改状态）
- [ ] **Step 2:** C14 spec 验收追加；核对不与其他活跃 spec 冲突（INDEX 交叉）
- [ ] **Step 3:** 验证：`git grep -n "c37-triage" docs/ | wc -l` ≥2；R0 表 43 行复核；`just check` 全绿
- [ ] **Step 4:** Commit `docs(c37): R4 handoff to C14, findings-ledger writeback, triage finalization`
- [ ] **Step 5:** audit-T6.md

---

## 验收覆盖表（spec 验收 → task → 命令）

| spec 验收 | task | 验证 |
|---|---|---|
| R0 表 43/43、一编号一行 | T1 | `python3 -c "...findall(r'^\| [FT]\d', t)..."` = 43 |
| `git grep -l "error_guidance" -- src/ docs/` 与裁决一致；抽查 5 处声称接线注释 | T2 | grep 输出对照 R0 表 |
| `just check` 全绿；vulture 基线清零；删除清单↔R0 表一一对应 | T2-T5 | `just check` exit 0 + `uv run vulture src/shenbi --min-confidence 60` exit 0 |
| 新增零调用函数 → CI FAIL；白名单项 PASS | T5 | Step 4 红灯/撤销两段输出 |
| pytest 无 skip 增量 | T2-T4 | 前后 skip 计数对照 |
| C14 spec 验收含"直测对象全部为生产可达路径" | T6 | grep 该句在 #52 spec |
| C37 成员 merged-into F108 回写 | T6 | findings-ledger grep 抽查 |

## Self-Review

- 覆盖：R0→T1、R1→T2、R2→T3+T4、R3→T5、R4→T6，簇级验收全覆盖 ✓
- 无占位符：删除步骤均给出确切符号/路径/行号锚点；F427/F325 有完整签名与测试步骤 ✓
- 类型一致：F427 合一签名仅 T4 内部消费 ✓
- 风险注记：T3 任何"预期零调用实有调用"立即停并回 R0 改行（spec 风险节机制化）
