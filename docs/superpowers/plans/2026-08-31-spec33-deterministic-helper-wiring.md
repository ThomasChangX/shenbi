# Spec #33 确定性 helper 派发接线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 specs/2026-08-16-audit-deterministic-helper-wiring-fix.md（v9）完成 T1a（派发前 helper 预计算注入）/ T1b（calibration 派发后强制 + route_block 死模型删除 + 修订上限迁移）/ T2（plant/recall 死面清理）/ T3（group-craft anti-ai 收敛 + 阈值分母统一）/ T4（lint_helper_usage）。

**Architecture:** 全部 task 属 infra 面（pipeline/truth_io/contracts）——协调者亲自实现，不分派。注入走 dispatch_helper `_build_skill_prompt` 既有 seam（与 plan_skeleton/review_checklist 同层）；truth 写走 truth_io 既有锁与 keyed upsert 设施；per-skill 回退开关读 executor_config.toml。

**Tech Stack:** Python 3.11+ / structlog / pathlib / pytest（fixtures 驱动，G0.9 禁手写 fixture）/ just。

## Global Constraints

- `src/shenbi/` 无 `print()`，用 structlog；文件 I/O 用 pathlib。
- 改 SKILL.md 契约（reads/writes/updates）后必须 `just lint-contracts` + `shenbi-sync-contracts` 幂等 diff 为空（禁手改 tests/tiers/deps.json、docs/framework/skills 生成物）。
- 一切验证走 `just`/`uv run`（CI 同构）；LLM 产物验收一律 fixtures 驱动测试，禁真实 dispatch。
- 阈值字面量不进 thresholds.py（归 spec #35）；状态字面量唯一信源 enums.py。
- 每个 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 重审）。
- T4（lint 接入 just check）必须在 T1a/T1b/T3 的 SKILL.md 修订之后落。

---

### Task 1: T1a-1 · style-learning 派发前 compute_stats 注入 + per-skill 开关

**Files:**
- Create: `src/shenbi/pipeline/helper_injection.py`
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（`_build_skill_prompt` 注入 seam，~line 826 之后、review_checklist 注入之前）
- Modify: `skills/shenbi-style-learning/SKILL.md`（删 `python -m` 自执行指令，改引注入块）
- Test: `tests/unit/pipeline/test_helper_injection.py`

**Interfaces:**
- Produces: `inject_helper_precompute(skill: str, project_dir: Path, user_prompt: str) -> str`（helper_injection.py）；`_helper_injection_disabled() -> frozenset[str]`（读 executor_config.toml `helper_injection_disabled: list[str]`，缺省空）

- [ ] **Step 1: 失败测试**——`test_stats_block_injected_for_style_learning`（用 tests/fixtures 下真实章节产物构造 tmp project_dir，调 `_build_skill_prompt`，断言 user_prompt 含 `## Helper Precompute (style stats, deterministic)` 块且 JSON 含 compute_all_stats 真实键）；`test_switch_off_disables_injection`（executor_config 含 `helper_injection_disabled=["shenbi-style-learning"]` → 无注入块）；`test_other_skills_untouched`
- [ ] **Step 2: 跑测试确认失败** `uv run pytest tests/unit/pipeline/test_helper_injection.py -v` → FAIL (ModuleNotFoundError)
- [ ] **Step 3: 实现** helper_injection.py：
```python
def inject_helper_precompute(skill: str, project_dir: Path, user_prompt: str) -> str:
    if skill in _helper_injection_disabled():
        return user_prompt
    if skill == "shenbi-style-learning":
        texts = {p.name: p.read_text(encoding="utf-8") for p in sorted((project_dir / "chapters").glob("chapter-*.md"))}
        if not texts:
            log.info("helper_injection_no_chapters", skill=skill)
            return user_prompt
        stats = compute_all_stats(texts)
        block = "## Helper Precompute (style stats, deterministic)\n\n```json\n" + json.dumps(stats, ensure_ascii=False, indent=2) + "\n```\n\n以上统计已由框架预计算（compute_all_stats），直接引用，不要重算。\n\n"
        return block + user_prompt
    return user_prompt
```
（structlog logger；dispatch_helper seam 处 try/except 只 log.warning `helper_inject_failed` 后原样返回——不吞错静默，WARN 即披露。`_helper_injection_disabled()` 复用 dispatch_helper._load_executor_config 的缓存 loader，不自建第二读取。成本封顶：只读最近 10 章（sorted 取尾 10），JSON 块截断到既有 _INPUT_MAX_CHARS_TOTAL 单技能配额内，超限 log.warning `helper_block_truncated` 并截断注入——注入块在 `_INPUT_MAX_CHARS_TOTAL`（总量预算，输入组装点 :698 生效）**之后**拼入，现有预算不覆盖它，必须自设 guard（如 8KB 硬顶）；配置键落 `executor_config.toml` 顶层 `helper_injection_disabled`）
- [ ] **Step 4: 跑测试通过**；同步改 SKILL.md 第一步指令为「框架已在 prompt 注入 `Helper Precompute` 统计块，直接读取该块」；`just lint-contracts` + `uv run shenbi-sync-contracts` diff 空
- [ ] **Step 5: Commit** `feat: pre-dispatch compute_stats injection for style-learning (spec #33 T1a)` → audit-T1.md

### Task 2: T1a-2 · chapter-pattern 结构化累积 + 历史半注入

**Files:**
- Modify: `src/shenbi/pipeline/helper_injection.py`、`src/shenbi/pipeline/audit_layer.py`（BOUNDARY_TRIGGERS 每 6 章 dispatch chapter-pattern 的真实派发点 :85/:180——累积钩子挂这里，**不挂 chapter_loop step 循环**（该技能不是 CHAPTER_STEP，挂错位置=再造死分支））
- Modify: `docs/framework/truth-files.yaml`（新文件 `truth/chapter_patterns.md`、`context/chapter-pattern-input-{N}.json` 入 canonical 词表——`just check` 的 lint_key_reconciliation --strict 会拦未登记契约写）
- Modify: `skills/shenbi-chapter-pattern/SKILL.md`（writes 增 `context/chapter-pattern-input-{N}.json`（分类输入落盘）+ truth/chapter_patterns.md 由框架累积；正文流程改「分类结果写 JSON 落盘，框架自动累积并预计算注入」）
- Test: `tests/unit/pipeline/test_pattern_accumulation.py`

**Interfaces:**
- Produces: `accumulate_pattern_classification(project_dir: Path, chapter: int, payload: list[dict[str, Any]]) -> None`（读 `context/chapter-pattern-input-{chapter}.json`，keyed upsert 追加行到 `truth/chapter_patterns.md`，格式 `| {N} | {pattern} |`，走 `write_truth_file(mode="insert_markdown_row", key_field="chapter")`）；`inject_helper_precompute` 增 `shenbi-chapter-pattern` 分支：读 truth 行 → `patterns=[row["pattern"]]` → 注入 `compute_consecutive/compute_entropy/check_distribution(patterns, recent_n=6)` 结果块；空历史 → `log.info("pattern_history_empty")` 原样返回

- [ ] **Step 1: 失败测试**——G0.9 策略（记 spec-deviations）：全仓无真实 chapter-pattern 分类产物（tests/rounds 归档无、fixtures 无、采获需真实 dispatch 被 SDD 禁），沿用 `tests/unit/skill_utils/test_compute_pattern.py` 既有先例——pattern 字符串值是确定性 compute 函数的直接输入（非 LLM 产物 mock），内联构造；`context/chapter-pattern-input-{N}.json` 是框架定义的契约输入格式（框架接口非技能输出），按契约格式构造。断言：accumulate（纯函数，payload 参数化）后 truth 行存在且重跑同章 dedup；注入块含 `entropy`；首跑空历史无块
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 通过 + lint-contracts/sync-contracts 幂等**
- [ ] **Step 5: Commit** `feat: chapter-pattern structured accumulation + historical-half injection (spec #33 T1a)` → audit-T2.md

### Task 3: T1b-1 · truth_io `patch_markdown_table_cell` 新原语

**Files:**
- Modify: `src/shenbi/pipeline/truth_io.py`（新函数，走既有 `_path_lock`）
- Test: `tests/unit/pipeline/test_truth_io_cell_patch.py`

**Interfaces:**
- Produces: `patch_markdown_table_cell(path: Path, key: str, key_field: str, cell_index: int, value: str) -> bool`（读文件→逐行 split_table_cells→cells[0] 归一化 == key 的行→cells 不足 `cell_index+1` 时补 "-" 占位→替换该 cell→整行回写；行不存在返回 False；全程持 `_path_lock(path)`；文件不存在返回 False）

- [ ] **Step 1: 失败测试**——表头行/分隔行跳过；9 列技能富行 patch cells[7]；框架占位行（无表头首文件）patch；短行补齐；行缺失 False；并发（两线程 patch 不同行不丢更新，沿既有锁测试范式）
- [ ] **Step 2-4: 红→实现→绿** · **Step 5: Commit** `feat: patch_markdown_table_cell primitive (spec #33 T1b)` → audit-T3.md

### Task 4: T1b-2 · calibration 派发后强制 + 锚点 truth 行 + 修订上限迁移

**Files:**
- Create: `src/shenbi/pipeline/confidence_calibration.py`
- Modify: `docs/framework/truth-files.yaml`（`truth/resonance_anchors.md` 入词表）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（trend 行落盘点 :1795-1812 后接校准；pattern 无涉）、`src/shenbi/pipeline/revision_router.py`（MAX_AUTO_REVISIONS=2 + 检查函数）、`src/shenbi/skill_utils/review_resonance/`（删 routing.py、`__main__.py` 整文件、`__init__.py` re-export 清除）、`skills/shenbi-review-resonance/SKILL.md`（铁律3 改写、铁律5、:81-82 流程图节点、:114 阻断规则、§5.4 整节删除/改写、:118 route_block 引用删除；trend 行声明注明 confidence 单元格由框架 patch；锚点判定结果按 truth 行格式追加）
- Test: `tests/unit/pipeline/test_confidence_calibration.py`、改写 `tests/unit/skill_utils/test_confidence_routing_integration.py`（保留 confidence 面、删 routing 面）、删 `tests/unit/skill_utils/test_routing.py`

**Interfaces:**
- Produces:
  - `compute_anchor_hit_rate(project_dir: Path) -> HitRate | None`（读 `truth/resonance_anchors.md` keyed 行 `| {N} | {high_conf_anchors} | {correct} |`；分母<3 → None）；判对标准：行内 correct 数由章节修订交叉核对写入（dispatch 后由框架比对 revision 记录是否改写锚点覆盖文本块；证据不足记 correct=0 且 flag `anchor_unverifiable`）
  - `calibrate_and_patch_trend(project_dir: Path, chapter: int, reported: str) -> None`（HitRate None → `log.info("calibration_insufficient_history")` 不降级；否则 `calibrate_confidence(reported, hr)` → `patch_markdown_table_cell(trend_path, str(chapter), "chapter", 7, calibrated)` → 行缺失先写 `_build_resonance_trend_row` 占位再 patch；降级时 `log.info("confidence_calibrated", before=…, after=…)`）
  - revision_router: `MAX_AUTO_REVISIONS = 2` + `def revision_cap_exceeded(revision_count: int) -> bool`；chapter_loop 在 `cs.revision_count += 1`（:1831）旁：超限走 `dispatch_escalation(...)`
- LLM 自报 confidence 来源：review-resonance 报告输出格式节增加机器可解析行 `calibration: reported=<high|mid|low>`（SKILL.md 输出格式节修订），框架解析正则 `reported=(high|mid|low)`；锚点行格式（框架写，技能只产出报告）：报告输出格式节增加机器可解析锚点块 `anchors: high=<n> | dim=<维度>:<行号>`，框架解析后写 `truth/resonance_anchors.md` 行（producer=framework，技能不写该 truth 文件）；`correct` 列仅框架回填（修订交叉核对后）

- [ ] **Step 1: 失败测试**——fixtures 驱动：校准历史（锚点 truth 行）由**新框架累积代码跑在真实章节 fixtures 上**生成（G0.9 upstream-generated：框架是上游生成器）；tests/fixtures/calibration/resonance 的锚点 prose 作为锚点文本输入复用。锚点判对机制（spec v8 交叉信号）：以 `_create_pre_revision_backup` 快照与修订后章文本做块级 diff——锚点行号引用在修订后行号漂移时按相邻文本窗口（±5 行）重定位，仍无法定位 → `anchor_unverifiable` flag 且 correct 记 0 + WARN（不静默降级），防系统性误降级：高报+低锚命中 → patch 后 trend cells[7]=="mid" + structlog 事件；锚点 <3 → 不降级 + insufficient_history 事件；行缺失 → 占位行先写后 patch；cap：revision_count 3 → escalate 断言；对账测试：retries(3) 与 cap(2) 正交（构造 retries 未满但 cap 超限场景）
- [ ] **Step 2-4: 红→实现→绿**；route_block 删除面核验 `git grep -w route_block src/ tests/ skills/ -- ':!tests/coverage'` 零残留；`just lint-contracts` + sync-contracts 幂等
- [ ] **Step 5: Commit** `feat: post-dispatch confidence calibration + anchor truth row; remove route_block dead model; migrate revision cap (spec #33 T1b)` → audit-T4.md

### Task 5: T2 · plant/recall 死面清理（裁决：选 (b) 删死面保留 LLM 面）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（删 :2818-2826 plant 死分支、:3109-3110 recall 死分支）、删 `src/shenbi/pipeline/hook_planting.py`、`src/shenbi/pipeline/dispatch_helper.py`（删 :385 OPTIONAL_READS 条目）、删 `tests/unit/pipeline/test_hook_planting.py`
- 保留：genesis.py:97 `_INDEX_UPDATE_SKILLS`（活代码）
- 核查处置：`skills/shenbi-foreshadowing-plant/SKILL.md` 手动路由面保留（LLM 面保留）、using-shenbi.md:73 路由表保留；弃用 `skills/shenbi-review-anti-ai/checklist.md` 死资产删除（review-anti-ai SKILL.md 已 DEPRECATED，checklist 无人读）
- Test: 既有回归套件（删除后 `just test` 全绿即证）

- [ ] **Step 1:** 删除 + `uv run pytest tests/unit/pipeline/ -n auto -q` 全绿
- [ ] **Step 2:** `git grep plant_hooks_from_plan src/ tests/ skills/` 零残留；`git grep -w foreshadowing-recall src/shenbi/pipeline/chapter_loop.py` 仅剩注释/无死分支
- [ ] **Step 3: Commit** `chore: remove unreachable plant/recall dead branches and hook_planting dead impl (spec #33 T2)` → audit-T5.md

### Task 6: T3 · group-craft anti-ai 收敛 + 阈值分母统一

**Files:**
- Modify: `src/shenbi/pipeline/review_checklist.py`（ReviewChecklist 增 `transition_count: int = 0`、`paragraph_cv: float | None = None`、`ai_marker_hits: int = 0`、`version: int = 1`；`_build_checklist` 预计算：`count_transition_words`（gates/shared.py:429）、段落 CV（segment_paragraphs）、AI 标记词计数（ai_blacklist 逐词计数）；`transition_budget` 分母改 `word_count_md(chapter_path)`（gates/shared.py:107）；缓存读侧 version 不匹配→视为 stale 重生成；写侧 data dict 增全字段+version）
- Modify: `skills/shenbi-review-group-craft/SKILL.md:198-226`（「检查执行」10 项中程序化项 1/4/5 改「读 prompt 注入的审查参考数据预计算块（transition_count/paragraph_cv/ai_marker_hits），不再自行计数」，保留非确定性项；转折词阈值引用 `max(5, word_count//1000)`）、`skills/shenbi-chapter-drafting/anti-ai-reference.md:20-22`（改引同口径）
- Test: `tests/unit/pipeline/test_review_checklist_precompute.py`

- [ ] **Step 1: 失败测试**——同章 fixture 下 `transition_budget == max(5, word_count_md(ch)//1000)`（与 G4 同值断言，构造 1000 边界章文本）；注入 JSON 含新字段+version；旧缓存（无 version 字段）被重生成；grep fixtures 中编码旧 `_estimate_chapter_char_count` 预算的快照并同步
- [ ] **Step 2-4: 红→实现→绿**；`_estimate_chapter_char_count` 删除时同步清 `__all__`（review_checklist.py:576）；lint-contracts/sync 幂等
- [ ] **Step 5: Commit** `feat: anti-ai deterministic precompute into review checklist + threshold denominator unification (spec #33 T3)` → audit-T6.md

### Task 7: T4 · tools/lint_helper_usage.py + just check 接入

**Files:**
- Create: `tools/lint_helper_usage.py`
- Modify: `justfile` check recipe（`uv run python tools/lint_decisions_sources.py` 行后加 `uv run python tools/lint_helper_usage.py`）
- Test: `tests/unit/tools/test_lint_helper_usage.py`

**Interfaces:**
- Produces: exit 0（无 WARN）/ exit 1（有 WARN 且无豁免）。能力清单 = 五件套面：`compute_stats|compute_pattern|calibration|review_resonance|count_transition|CV|变异系数`；疲劳词计数（group-craft 第 6 项，词表已由 fatigue_warnings 注入）列入 ALLOWED 豁免（本轮不改，记 T5 候选）——扫描 `skills/*/SKILL.md` 正文「计算/统计/计数」类指令若要求 LLM 自算命中清单 → WARN（skill 名 + 行号），豁免表 `ALLOWED: dict[str, list[int]]` 内置已裁决项。drift-guidance 的 `python -m drift_detection` 不在清单（spec 注记，T5 候选）。

- [ ] **Step 1: 失败测试**——构造违规 SKILL 文本片段（tmp）→ WARN；当前 main skills/ 扫描 → exit 0
- [ ] **Step 2-4: 红→实现→绿**；`just check` 实际执行到该行（跑一次全量确认）
- [ ] **Step 5: Commit** `feat: lint_helper_usage anti-recurrence lint wired into just check (spec #33 T4)` → audit-T7.md

### Task 8: 全量门禁

- [ ] `just check` 全绿（两段 pytest + cov ≥85）；`uv lock --check`（未改依赖则略）
- [ ] spec 验收 1a/1b/2/3/4/5 逐条跑验证命令，输出粘贴 progress.md `## 验收证据`

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1a 注入块+无 python -m+开关 | T1/T2 | pytest test_helper_injection.py test_pattern_accumulation.py；`git grep 'python -m shenbi.skill_utils' skills/shenbi-{style-learning,chapter-pattern,review-resonance}/SKILL.md` 为零；style-learning DOT 流程图节点 "Run compute_stats.py on chapter files"（SKILL.md:45）同步改为 "Read Helper Precompute block" |
| 1b 校准覆盖+route_block 零残留 | T3/T4 | pytest test_confidence_calibration.py；`git grep -w route_block src/ tests/ skills/ -- ':!tests/coverage'` |
| 2 死面清理 | T5 | `git grep plant_hooks_from_plan src/ tests/ skills/` 空 |
| 3 预计算块+同值断言 | T6 | pytest test_review_checklist_precompute.py |
| 4 lint exit 0 + just check 接入 | T7 | `uv run python tools/lint_helper_usage.py; echo $?` |
| 5 just check 全绿 | T8 | `just check` |
