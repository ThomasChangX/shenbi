# Spec #27 读方↔写方键空间对账 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消灭 gates/pipeline 读键无写方的死检查与读方-写方形状错配的假 FAIL，落地 `tools/lint_key_reconciliation.py` 对账 lint。

**Architecture:** 三层——(1) 单源常量化（marker 命名族、审计扫描名单从 `audit_suffix()` 派生）；(2) 读方对齐唯一写方（g_reconcile 状态词、G3.2 读键、G7.14/G0.10 glob、触发器正则）；(3) 静态对账 lint（READ_KEY_REGISTRY 常量表 + grep 可复核写方锚点断言）接入 `just check`（首周期 WARN）。

**Tech Stack:** Python 3.11+ / pytest / structlog / just。全部为 `src/shenbi/`（infra 面，协调者亲自实现）+ `tools/` + `tests/`。

**Spec:** `docs/superpowers/specs/2026-08-16-audit-reader-writer-key-reconciliation-fix.md`（含 2026-08-30 修订节——已核销项不得实施）

## Global Constraints

- gate 检查器纯函数、幂等、无副作用；`src/shenbi/` 禁 `print()`（structlog）
- fixtures 只能是真实产物或源文件副本（G0.9）；验证走 `just`/`uv run`
- 已核销（禁做）：F104/F757 解析面、F238/F373 主体、F342、F1103、F1107
- 状态字面量唯一定义于 `src/shenbi/contracts/enums.py`；`tools/lint_status_strings.py` 保持绿
- commit 用 Conventional Commits；逐 task 独立提交可 revert

## 现状锚点（真实签名，源码复制）

```python
# src/shenbi/scoring.py:236
def check_gate_markers(rubric_path: str, test_type: str | None, round_dir: str | None) -> list[str]
# src/shenbi/gates/shared.py:190
def write_gate_marker(gate: str, target: str, test_type: str, result_str: str,
                      round_dir: str | None, file_paths: list[str] | None = None) -> None
# src/shenbi/pipeline/audit_layer.py:135
def audit_suffix(skill: str) -> str
# src/shenbi/pipeline/audit_layer.py:150
def audit_relative_path(chapter: int, skill: str) -> str  # "audits/chapter-{N}-{suffix}.md"
# src/shenbi/cost/report.py:16
def _try_avg_g3_score(project_dir: Path) -> float | None
# src/shenbi/pipeline/triggers.py:325
_WARNING_RE = re.compile(r"(?:warning|drift|fatigue)\s*[:\uff1a]\s*(.+)", re.IGNORECASE)
```

---

### Task 1: marker 协议单源 + bug-hunt/clean 写方（spec T2 · F121/F129/F131/F463/F1111 空转面）

**Files:**
- Modify: `src/shenbi/scoring.py`（check_gate_markers 命名族）、`src/shenbi/gates/shared.py`（新增 marker 命名常量）、`src/shenbi/gates/cli.py:102-128`（G4 分支 `--test-type` 扩展 + bughunt/clean marker 写方）
- Test: `tests/unit/test_scoring.py`、`tests/unit/test_gates_cli.py`

**Interfaces:**
- Produces: `src/shenbi/gates/shared.py` 新常量 `def marker_filename(gate: str, target: str, test_type: str) -> str`（返回 `f"{gate}-{target}-{test_type}.json"`）；scoring 与 cli 统一调用。`G4_STATUS_VOCAB`（读方容忍集，见 Task 4 复用状态词单一信源 enums）。
- 复杂度: infra · test_kind: tdd_red_green · T1 层级（unit）

**Steps:**
- [ ] **1.1 失败测试**（tests/unit/test_gates_cli.py 追加）：
```python
def test_g4_bughunt_writes_marker(tmp_path, monkeypatch):
    # bug-hunt 分支必须写 G4-<skill>-bug-hunt.json marker（F463）
    out = run_cli(["G4", "bug-hunt", "<fixture files>", str(tmp_path)])
    marker = tmp_path / "gate-markers" / "G4-bug-hunt-bug-hunt.json"
    # 断言：PASS 时 marker 存在；命名从 marker_filename() 取
```
（具体断言按 `gate_G4_bughunt` 现有返回形状落实；fixture 引 `tests/fixtures/` 真实 bug-hunt 产物路径，grep `tests/fixtures -r "bug-hunt"` 取现存样本）
- [ ] **1.2 跑测确认失败**：`uv run pytest tests/unit/test_gates_cli.py -k bughunt_writes_marker -v` → FAIL（marker 不存在）
- [ ] **1.3 实现**：shared.py 增加 `marker_filename()`；cli.py G4 分支 bughunt/clean 路径调用 `write_gate_marker("G4", target, "bug-hunt"|"clean", result, rd, file_list)`；scoring.py `check_gate_markers` 内三处 f-string 换 `marker_filename(...)`。读方兼容历史 `G4-*-generative.json`（t2-phase 分支已是 generative 字面量，保持）
- [ ] **1.4 验收命令**（spec 验收 1 前半）：
```bash
uv run shenbi-validate G4 bughunt <fixture-files> <round-dir>   # 真实产出 marker（G0.9：非手写）
uv run shenbi-score tests/tiers/t1-skill/<skill>/<rubric>.md <scores.json> --test-type bug-hunt --round-dir <round-dir>
# 期望 exit 0（无 MARKER_MISSING exit 3）
```
- [ ] **1.5 兼容断言**：`tests/baselines/gate-outputs/G4-genre_config.json` 经读方逻辑解析不破坏（unit test 直接调 `check_gate_markers` 对构造 round-dir）
- [ ] **1.6 commit**: `fix: marker protocol single source + bug-hunt/clean marker writers (spec #27 T2)`

### Task 2: g_reconcile/评分读键对齐（spec T4 · F449/F710/F130/F435/F462）

**Files:**
- Modify: `src/shenbi/gates/g_reconcile.py:35-70`、`src/shenbi/gates/g3.py:100-110`
- Test: `tests/unit/gates/test_g_reconcile.py`、`tests/unit/gates/`（g3 相关既有文件）

**Interfaces:**
- Consumes: codex 写方形状 `{"score": …, "status": "done"}`（dispatcher/modes/codex.py:53）+ `*-scores-subagent.json`（codex.py:75）
- 复杂度: infra · test_kind: regression_guard + tdd_red_green · T1

**Steps:**
- [ ] **2.1 失败测试**：`test_g_reconcile.py` 追加——构造 progress.json 含 `"status": "done"`（真实写方小写形态）→ GR.1/GR.2 零假 FAIL；`"status": "DONE"` 旧形态仍通过（读方容忍双形态过渡）
- [ ] **2.2 跑测确认失败**：现 `== "DONE"` 对 `done` 报 status=? 假 FAIL
- [ ] **2.3 实现**：g_reconcile.py:40/:65 比较改 `.upper() == "DONE"`（或经 enums 状态词表 helper）；不改写方
- [ ] **2.4 F130 核对**：unit test 喂 canonical `{"final_score": x, "dimensions": {...}}` 形状 → g3.py `_compute_rubric_weighted_score` 路径产出正确分数；不匹配则补 final_score 分支
- [ ] **2.5 F435 核对**：`cmd_post_skill`（phase_runner.py:247-261）新形状下 Route C 侧车索要行为——unit test 驱动 `derive_output_files` 输出含 sidecar 时 G2 面不误报；若已无索要面则记 spec-deviations 核销
- [ ] **2.6 验收命令**（spec 验收 2）：`uv run shenbi-validate G_RECONCILE <dir-with-codex-progress>` → 零 `status=?`
- [ ] **2.7 commit**: `fix: g_reconcile status vocab alignment + G3.2 canonical shape (spec #27 T4)`

### Task 3: 死检查清剿（spec T1 · F340 子面 F349/F406/F419、F450-F455、F458 残存 glob、F464/F465/F466、F467/F468/F470、F639）

**Files:**
- Modify: `src/shenbi/gates/g0.py:230-240,367-372,450,529-537`、`gates/g_transition.py:69-85`、`gates/g1.py:243-273`、`gates/g3.py:224-240`、`gates/g3_independence.py:20`、`gates/g5.py:57`、`gates/g7.py:40,61,182,207`、`gates/shared.py`（若 find_report 吸收 glob）
- Test: 对应 `tests/unit/gates/*`

**Interfaces:**
- 复杂度: infra · test_kind: characterization（先固现状再删）+ regression_guard · T1

**Steps:**
- [ ] **3.1 逐条裁决表**（progress.md 落盘）：每 finding 二选一「删检查」或「补写方」。默认删（spec 修复形状建议）；.gate-lock（F467）删除读方 g1.py:243-245 并记 deviation 与 C11 联动注记
- [ ] **3.2 characterization 测试**：删除前对每个目标 checker 跑既有测试确认绿（现状锚定），然后删除死分支（G0.7 exists-check、GT.3 gate_blockers、G1.6 scoring_history、G3.5 agent_id、F419 missing_dirs 死分支、t1_scores 读方 g5/g7、F406 豁免计数、F639）+ 同步删除/收编对应 pin 测试（F708-F709 面）——**每删一处跑其测试文件**
- [ ] **3.3 F458 残存**：g7.py:182/:207、g0.py:450 的 `*-scores.json`/`*-generative-scores.json` glob 改走 `find_report()`（gates/shared.py:156-175 已支持 `-scores-subagent` 多后缀）
- [ ] **3.4 死数据面**：`trace/materialize.py:90` 的 `"gate_blockers": []` 恒空键删除（写方即唯一读方已删）；F469 例外（归 Task 5/T6 处置）
- [ ] **3.5 验收命令**（spec 验收 4）：`git grep -n "G0\.7\|GT\.3\|\.gate-lock"` → 零残留（或仅剩注释性联动注记）
- [ ] **3.6 commit**: `fix: dead-check purge — zero-writer read keys removed/rewired (spec #27 T1)`

### Task 4: 审计门控/触发器格式对账（spec T5 · F340/F369/F370、F303/F341、F372、F374、F375/F643、F511、F891/F309/F312/F322/F364、F524 对账面、F238 残面）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:1601-1626`（扫描名单）、`:307-321`（级联词表）、`:325-363`（_should_skip_audit）、`:1311`（局部 regex）、`src/shenbi/pipeline/triggers.py:94-122,325-327,420-421`、`src/shenbi/skill_utils/drift_detection/compute_drift.py:229-232`（写方形状对齐面）、`src/shenbi/cost/report.py:16-36`
- Test: `tests/unit/pipeline/`、`tests/skill-triggering/`（resonance/drift 既有面）

**Interfaces:**
- Consumes: `audit_relative_path(chapter, skill)`（Task 0 已存在，audit_layer.py:150）
- 复杂度: infra · test_kind: tdd_red_green · T1/T2

**Steps:**
- [ ] **4.1 失败测试（F340 P0）**：构造 audits 目录含 `chapter-3-group-factual.md`（内含 "## BLOCKING"）→ `_any_audit_has_findings` 必须返回 True（现名单缺席 → False → revision 静默跳过）。fixture 用 xinghuo-ranqiong 真实审计产物或其精确副本
- [ ] **4.2 实现**：`_any_audit_has_findings` 13 型硬编码名单替换为 `audit_layer` 单源派生——遍历激活矩阵（audit_layer.py:40-48）+ group 技能集（chapter_loop.py:210-231），用 `audit_relative_path` 构造；`"FAIL" in text` 改 `re.search(r"^#{0,3}\s*(BLOCKING|FAIL)", text, re.M)` 精确标记（F370）；F349 `drift_alerts` 幽灵字段读删除
- [ ] **4.3 级联词表（F303/F341）**：CORE/CASCADABLE 补 `group-factual/character/craft/plan`、`era/fanfic/highpoint`；`_should_skip_audit` 读键对齐写方键（`blocking_found/issues/audit_reports`，chapter_loop.py:2870-2872）——无 per-skill `passed` 键则 streak 逻辑按写方真实形状重写
- [ ] **4.4 触发器正则（F375/F643）**：triggers.py `_WARNING_RE` 改匹配写方真实格式 `- [{kind}] {dim}: {detail}`：`re.compile(r"^\s*-\s*\[(warning|drift|fatigue)\]\s*(.+)$", re.M | re.I)`；unit test 喂 compute_drift 真实输出样本断言非空命中
- [ ] **4.5 F372 resonance**：`_parse_resonance_score`（chapter_loop.py:1339-1374）按技能自产格式实样对齐——以 `tests/fixtures/` 真实 resonance 产物断言解析非空；解析不了时 WARN 日志
- [ ] **4.6 F511**：`_try_avg_g3_score` 改只取明确契约键（`final_score`/`total_score` 顶层键），不再抓任意 0-100 数值；unit test 喂含噪声 JSON
- [ ] **4.7 F374/F524/F1311/F322/T105**：style_profile 陈旧判定排除 `chapter-*.md.bak`/备份命名族（写方 chapter_loop.py:1673-1694）；parse_trend 三方消费者表头契约对账断言（unit，三方构造同表头）；chapter_loop.py:1311 局部 regex 改走 truth_readers 单源；skills/shenbi-chapter-drafting SKILL.md reads 中 `context/chapter-N-context-decisions.json` 死读键处置（删除声明或补写方——改 SKILL.md 须跑 `just lint-contracts && just generate`）
- [ ] **4.8 验收命令**（spec 验收 6 前半）：`uv run pytest tests/unit/pipeline -k "resonance or drift or style_profile" -v` 全绿（解析非空断言）
- [ ] **4.9 commit**: `fix: audit gate single-source scan list + trigger format reconciliation (spec #27 T5)`

### Task 5: 写而不读数据裁决（spec T6 · F225/F229/F469/F527/F640、F240/F241/F629）

**Files:**
- Modify: `src/shenbi/trace/materialize.py:49-90`、`src/shenbi/contracts/ownership.py:33`、`src/shenbi/contracts/schemas/novel.py:18`、相关消费面
- Test: `tests/unit/`（trace/contracts 既有）

**Interfaces:**
- 复杂度: infra · test_kind: regression_guard · T1

**Steps:**
- [ ] **5.1 逐字段裁决表**（progress.md）：F469 `test_cycle_phase`/`subagent_completion_count`（materialize.py:83-84）、F629 trace INIT/MARK_DONE 读而不写（materialize.py:49,53）、F229 `read_keys`（ownership.py:33）、F527 write_semantics、F640 materialize 12 键仅 4 键被消费、F240 NovelConfig `genre: str` vs novel.json list、F241 ProgressDoc 键空间——每项「补消费者」或「删除」二选一，倾向删除（与 C37 死代码簇方向一致，本 spec 只处理读键无写方/写键无读方面）
- [ ] **5.2 实施**：删除面跑对应测试；F240 改 `genre: str | list[str]` 契约面须过 `just lint-contracts` + `just generate` 幂等 diff
- [ ] **5.3 验收命令**（spec 验收 5）：每字段 `git grep <field>` 有消费者锚点或零命中（删除完成）
- [ ] **5.4 commit**: `fix: write-not-read field adjudication — consumers or removal (spec #27 T6)`

### Task 6: 对账 lint 落地（spec T7 · 含 F104/F757 lint 面）

**Files:**
- Create: `tools/lint_key_reconciliation.py`
- Modify: `justfile`（lint 面）、`.github/workflows/ci.yml`（lint 面，与 C25 联动处核对既有 lint 接入惯例）
- Test: `tests/unit/test_lint_key_reconciliation.py`

**Interfaces:**
- Produces: `READ_KEY_REGISTRY: list[ReadKey]`；`@dataclass class ReadKey {check_id: str; anchor: str; read_pattern: str; writer_sources: list[str]}`；`main(argv) -> int`（`--strict` flag：默认 WARN exit 0，strict 违规 exit 1）。断言 = (a) 每个 writer_source 锚点文件中模式 grep 存在；(b) read_pattern 与写方命名族样本交集非空（样本 = fixtures 真实产物路径 + 写方代码字面量，登记于 registry）
- 复杂度: infra · test_kind: tdd_red_green · T1

**Steps:**
- [ ] **6.1 失败测试**：构造临时 registry 含一条孤儿读键 → strict 模式 exit 1 且输出含 check_id；一条健全读键 → exit 0
- [ ] **6.2 实现**：首批登记 T1-T5 涉及的 40+ 读键（marker 命名族、g_reconcile 状态键、审计扫描族、触发器正则锚点、resonance 解析、score 键）；每条 writer_source 带 file:line 锚点
- [ ] **6.3 接线**：justfile 追加 `lint-key-reconciliation` recipe → 接入 `just check`（首周期无 `--strict`，WARN 模式）；ci.yml lint 面同构接入（核对既有 lint 工具的接入行复制形态）
- [ ] **6.4 验收命令**（spec 验收 3）：`uv run python tools/lint_key_reconciliation.py` exit 0 且零 WARN 输出
- [ ] **6.5 commit**: `feat: lint_key_reconciliation — read↔writer key reconciliation lint (spec #27 T7)`

### Task 7: 批量清理残项 + 全量门禁（spec 批量清理 F136/F353/F444 + T8 复验 + 验收收口）

**Files:**
- Modify: `src/shenbi/scoring.py:504`（F136 gate_markers_verified 空转）、triggers G3 失败面（F353 last_trigger_failure + stage 值族补 "g3"——状态字面量须入 enums.py）、`skills/shenbi-memory-distill` 校验面（F444 book_spine 文件族）
- Test: 对应既有测试文件

**Interfaces:**
- 复杂度: infra · test_kind: regression_guard · T1

**Steps:**
- [ ] **7.1 F136**：`gate_markers_verified = bool(round_dir and test_type)` 改真实核验结果（`not missing`）；unit 断言 missing 时 False
- [ ] **7.2 F353**：triggers G3 失败写 `last_trigger_failure`；stage 值族 "g3" 入 enums.py 唯一信源
- [ ] **7.3 F444**：memory-distill L5 校验的 book_spine 归属改对（蒸馏产物 vs 项目真相文件）；改 SKILL.md 相关面跑 `just lint-contracts && just generate`
- [ ] **7.4 T8 复验**：F1103/F1107 已核销——grep 复核接线仍在（revision_count/resonance_score、blocking_found）；xinghuo-ranqiong 树驱动触发器单测已在 Task 4.8 覆盖，此处补 F1111 marker 空转面复验（Task 1 已修，跑验收 1 完整命令）
- [ ] **7.5 全量门禁**：`just check` 全绿（完整输出粘 progress.md）
- [ ] **7.6 commit**: `fix: batch residuals F136/F353/F444 + acceptance closeout (spec #27)`

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 bug-hunt exit 0 + 双命名族兼容 | T1 步 1.4/1.5 | `uv run shenbi-score … --test-type bug-hunt --round-dir <round>` |
| 2 G_RECONCILE 零假 FAIL | T2 步 2.6 | `uv run shenbi-validate G_RECONCILE <dir>` |
| 3 lint exit 0 | T6 步 6.4 | `uv run python tools/lint_key_reconciliation.py` |
| 4 死检查零残留 | T3 步 3.5 | `git grep -n "G0.7\|GT.3\|\.gate-lock"` |
| 5 字段终态 | T5 步 5.3 | 逐字段 git grep |
| 6 just check + 触发器单测 | T4 步 4.8 / T7 步 7.5 | pytest + just check |

评分场景说明：本 spec 不涉及 LLM 产物评分验收（全部 fixtures 驱动/只读 CLI），无需 G3.4 独立评分子 agent。
