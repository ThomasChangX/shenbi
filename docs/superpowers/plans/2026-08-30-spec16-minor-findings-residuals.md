# Spec #16 Minor-Findings Residuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 41 unclaimed M-level findings (copy/comment/naming/dead-code/guard micro-fixes) from spec #16's narrowed scope.

**Architecture:** 8 tasks grouped by module cluster; all are infra-class (scoring/phase_runner/sync_contracts/gates/pipeline/contracts) → coordinator implements personally, TDD where behavioral, grep verification where textual. Gates/g4 fixes stay pure & idempotent (no side effects).

**Tech Stack:** Python 3.11+ (pathlib, structlog, pydantic), pytest, just.

## Global Constraints

- structlog (no print in src/shenbi except cost/report.py print-face already owned by spec #50 — do not add new print)
- gate checkers pure & idempotent — fixes must not add file writes/logging-to-file inside checkers (structlog log calls OK)
- conventional commits, pathspec-only `git add` (never `git add -A`)
- every deletion requires a recorded caller grep in the commit body
- behavioral fixes ship with T1 unit tests; textual fixes verified by grep
- 验收（spec）: grep 无残留目标模式；`just check` 全绿

---

### Task 1: scoring.py 微修（F151/F152/F157/F146/F142）

**Files:**
- Modify: `src/shenbi/scoring.py` (:444-448 非数字键, :43-48 kill-switch 解析, :417/:426 input() 提示, :234-236 deps.json 守卫, :136-139 docstring)
- Test: `tests/unit/test_scoring*.py`（现有文件，追加用例；fixture 输入用现有 rubric fixtures）

**Fixes:**
- F151: `scores = {int(k): v for k, v in raw.items() if k.lstrip("-").isdigit()}` → collect dropped keys, `log.warning("non_numeric_score_keys_dropped", keys=sorted(dropped))` before building dict
- F152: kill-switch 匹配条件追加 `or "detection dimension = 0" in stripped.lower()`
- F157: `input()` 交互提示（kill-switch y/n 与逐维打分）写 stderr：`print(..., file=sys.stderr)` 或先 `sys.stderr.write`——stdout 仅承载 emit_json
- F146: `if deps_path.exists(): deps = json.loads(...)` → 包 `try/except json.JSONDecodeError` → log.error + deps = {}
- F142: `filter_dimensions_by_test_type` docstring 删 "and renormalize weights"（函数体重归一不存在则删词；若存在重归一则删 finding 记载相反——执行时以函数体为准修正 docstring 或驳回该条记 deviation）

**Steps:** write failing tests for F151/F152 (non-numeric key dropped + warning; "→ detection dimension = 0" line parsed as kill switch) → run fail → implement → run pass → `git add src/shenbi/scoring.py tests/unit/test_scoring*.py && git commit -m "fix: spec #16 Z1 scoring micro-fixes (F151/F152/F157/F146/F142)"`

### Task 2: sync_contracts + cli_utils + exceptions + pyproject（F159/F147/F130/F160/F110/F0-08）

**Files:**
- Modify: `src/shenbi/sync_contracts.py`（main 缺 configure_logging；:195 deps.json 裸读；:141-153 render_body_into 静默跳过）
- Modify: `src/shenbi/cli_utils.py:13-22`（emit_json）
- Modify: `src/shenbi/exceptions.py:61`（语法）
- Modify: `pyproject.toml:447-452`（注释漂移）

**Fixes:**
- F159: sync_contracts main() 入口加 `configure_logging()`（与 phase_runner 同款 import）
- F147: `deps = json.loads(DEPS_PATH.read_text(...))` → try/except json.JSONDecodeError → log.error + 保留组织字段空骨架 `deps = {}`
- F130: render_body_into `if not m: return` → `log.warning("skill_md_frontmatter_missing", path=str(skill_md))` 后 return；`count=1` 保留（banner 单例不变量）+ 行内注释说明
- F160: emit_json 外层 `try: ... except BrokenPipeError: return`（下游 head/pipe 关闭不栈轨）
- F110: `f"{len(mismatches)} source files changed"` → `f"{len(mismatches)} source file{'s' if len(mismatches) != 1 else ''} changed"`；同步 tests/unit/test_exceptions.py:64 断言
- F0-08: pyproject 注释改为与 `fail_under = 85` 一致（删 ≥90%/89 陈旧叙述，写明 85 与缘由）

**Steps:** implement → run `uv run pytest tests/unit/test_exceptions.py -q` → grep 验证 → commit `fix: spec #16 Z1/Z5 textual+guard fixes (F159/F147/F130/F160/F110/F0-08)`

### Task 3: phase_runner.py（F162/F165/F143/F145）

**Files:**
- Modify: `src/shenbi/phase_runner.py`（:212/:364 冗余 configure_logging、:2 docstring、:233-236 陈旧注释、:33-34 load_deps）

**Fixes:**
- F162: `configure_logging()` 在 :212（cmd_post_skill）与 :364（main）重复——main 已覆盖 CLI 路径；grep cmd_post_skill 是否被 main 之外的入口直接调用，无则删 :212 冗余调用（commit body 记 grep）；有则记 deviation 保留

- F165: docstring "State machine for T2/T3 phase execution" 若与实际支持范围不符（执行时 grep `phase` 字面量核对），订正为实际口径
- F143: `# G2's decisions branch would json.loads() markdown → crash` 注释——打开 gates/g2.py decisions 分支核实现行行为（continue 跳过而非 crash）→ 订正注释
- F145: `load_deps()` 裸 `json.loads` → try/except json.JSONDecodeError → log.error + raise PhaseError（或返回 {} 视调用方容错需求，执行时按调用方定）

**Steps:** implement → `uv run pytest tests/unit/test_phase_runner*.py -q` → commit `fix: spec #16 phase_runner docstring+guard fixes (F165/F143/F145)`

### Task 4: contracts + dispatcher（F263/F264/F271/F258/F261/F267/F257）

**Files:**
- Modify: `src/shenbi/contracts/legacy.py:147,235`、`src/shenbi/gates/g0_skill_contract.py:67`（frontmatter 锚定）
- Modify: `src/shenbi/contracts/fields.py:38-52`（H2 折叠 + 围栏）
- Modify: `src/shenbi/contracts/paths.py:155-157`（chapter 0）
- Modify: `src/shenbi/contracts/schemas/decisions.py:11-12`（死常量）
- Modify: `src/shenbi/dispatcher/cli.py:28`（argv 截断）
- Modify: `src/shenbi/dispatcher/executor.py`（F257 chapter kwarg）
- Test: `tests/unit/contracts/`、`tests/unit/test_dispatcher*.py`（追加）

**Fixes:**
- F263: `text.split("---", 2)` → 行首/EOF 容忍锚定：`m = re.match(r"^---\n(.*?)\n---(?=\n|$)", text, re.DOTALL)`（frontmatter 内非行首 `---` 不再误劈；闭合 `---` 在 EOF 无尾换行仍合法——须补该测试用例）——三处统一该模式
- F264: extract_h2_sections 重复 H2 → 保留首个（`if current_heading in sections: current_heading = None; continue` 语义——重复节跳过并入前节尾部不丢首段），docstring 说明 first-wins
- F271: extract_h2_sections 跳过 ``` 围栏内的 `## ` 行（fence toggle 状态机）
- F258: extract_chapter `re.search(r"\bchapter\s+(\d+)\b")` → 取第一个 **非零** 匹配：`next((int(m.group(1)) for m in re.finditer(...) if int(m.group(1)) > 0), None)`
- F261: 删 VALID_BASIS/VALID_SEVERITY（grep 全仓零消费已 VERIFY；commit body 记 grep 输出）
- F267: `prompt = sys.argv[4] if ...` → `prompt = " ".join(sys.argv[4:])`（join 为增量兼容，原单参带引号调用不变）
- F257: `dispatch(..., chapter=None)` kwarg——grep 调用方；若零外部调用方传 chapter=，删 kwarg 与优先级块（commit body 记 grep）；有调用方则记 deviation 驳回

**Steps:** failing tests（frontmatter 内容含 `---` 行；H2 重复 + fenced `## `；"chapter 0 ... chapter 3" 取 3）→ fail → implement → pass → commit `fix: spec #16 Z2 contracts/dispatcher fixes (F263/F264/F271/F258/F261/F267/F257)`

### Task 5: pipeline（F343/F390/F394/F395/F398/F3A2/F3A7）

**Files:**
- Modify: `src/shenbi/pipeline/cli.py`（:299-302、:617-618、:748-754、:838-841）
- Modify: `src/shenbi/pipeline/crash_recovery.py:28-34`
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1842-1845`
- Modify: `src/shenbi/pipeline/plan_skeleton.py:84`

**Fixes:**
- F343: `dispatch_escalation(project_dir, 0, ...)` → `None`（与 revision_router/genesis 现行 None 语义对齐；先 grep dispatch_escalation 签名确认 0|int|None 接受度）
- F390: `Path(args.feedback).read_text()` → 先 `if not Path(args.feedback).is_file():` 输出明确错误 "feedback file not found"（区分 project not found 误报）
- F394: reset_emergency_state docstring/注释与实现（无 atexit.unregister）对齐——订正注释
- F395: `except Exception as exc: _handle_timeout_gracefully(...)` → 仅 timeout 族异常（`openai.APITimeoutError`/`asyncio.TimeoutError`/`socket.timeout` 按现行 import 面）走 graceful，其余仅 log.error + return；执行时核对该 except 块的实际异常面
- F398: `_verify_truth_integrity` 对当前章 plan 的缺失误报 → 现行 `if ch > 1` 守卫保留但排除**当前章**（当章 plan 在 step-2 生成）：改为检查 `chapter < ch` 的 plan 缺失
- F3A2: `next_chapter = min(chapter + 1, ch_end)` → 卷末不再自指：`next_chapter = chapter + 1 if chapter < ch_end else None`；`_extract_chapter_node(volume_map_text, None)` 需返回 None（核对签名，加 None 短路）
- F3A7: `dispatch_skill("shenbi-snapshot-manage", ...)` 返回值 → `snap_rc = ...; if snap_rc not in (0, None): log.error("volume_boundary_snapshot_failed", rc=snap_rc)`

**Steps:** implement → `uv run pytest tests/unit/pipeline/ -q`（相关模块）→ commit `fix: spec #16 Z3 pipeline fixes (F343/F390/F394/F395/F398/F3A2/F3A7)`

### Task 6: gates g2/g6（F481/F4A2/F4A4）

**Files:**
- Modify: `src/shenbi/gates/g2.py:330-334,394-407`
- Modify: `src/shenbi/gates/g6.py`（:191 口头禅切片、最终 PASS 汇总——执行时定位）
- Test: `tests/unit/gates/test_g2*.py`、`test_g6*.py`（追加）

**Fixes:**
- F481: `_check_meta_ratio` 已在 checks 里发 WARN（ratio>0.5 时）；调用方 :332-334 又把 failures 逐条 append 成第二份 WARN → 调用方删重复循环；_check 的 WARN 条目补 `"r": failure` 与 `"file": str(file_path)` 字段（_check 已收 file_path 参数，保文件归属不丢）
- F4A2: G6 子检查 must_fix 非空时汇总仍输出 PASS —— 执行时定位 g6 汇总输出点，must_fix 非空时汇总不得为 PASS
- F4A4: `cp_section = ct[ct.index("voice_profile:"):]`（切到 EOF）→ 切到下一角色块边界（下一个非缩进行或下一 `##`/角色头；执行时看 ct 结构定界）

**Steps:** failing tests（meta_ratio 单条 WARN；G6 must_fix 时汇总非 PASS）→ implement → pass → commit `fix: spec #16 Z4 g2/g6 gate output fixes (F481/F4A2/F4A4)`

### Task 7: gates g4（F479/F480/F482/F486/F490/F4A1）

**Files:**
- Modify: `src/shenbi/gates/g4/worldbuilding.py`（:68 注释、:152-158 truth PASS）
- Modify: `src/shenbi/gates/g4/generic.py:122,172`（死条件）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:65`（docstring 承诺）
- Modify: `src/shenbi/gates/g4/plot_thread_weaver.py:40-44`（子串 OR）
- Modify: `src/shenbi/gates/g4/chapter_revision.py:96-100`（checks 槽类型）
- Test: `tests/unit/gates/test_g4*.py`（追加）

**Fixes:**
- F479: 注释 `prose density < 5%` 与代码 `bullet_density>5% FAIL` 方向相反 → 订正注释为实际检查方向
- F480: `if not mf or all(not x.startswith("G4.bh.") for x in mf):` → `if not mf:`（bh/cl 两处；all 分支使 mf 含非本前缀项时误发 PASS）
- F482: docstring 删 `- Thematic naming encouraged (1-4 Chinese characters)`（无对应检查的空头承诺）
- F486: `for label in ["A 长线",..., "## A","## B","## C"]: if label in content` 子串 OR → `## A/B/C` 改为行级匹配 `re.search(r"^##\s+A\b", content, re.M)`（防正文子串误命中）
- F490: `"checks": issues`（list[str]）→ checks 槽类型统一为 check dict 列表：`"checks": []`，issues 保留在 must_fix
- F4A1: truth 模板循环中 `c.append(PASS)` 无条件执行（missing field 已 mf.append 后仍 PASS）→ 该模板无 mf 项才 append PASS（收集本模板 mf 前缀判断）

**Steps:** characterization tests 先钉现状（F490 checks 结构变更则 tdd_red_green）→ implement → pass → commit `fix: spec #16 Z4 g4 checker fixes (F479/F480/F482/F486/F490/F4A1)`

### Task 8: 残余散点 + spec/INDEX 注记（F510/F657/F658 + docs）

**Files:**
- Modify: `src/shenbi/cost/report.py:96`（不可达 return 2）
- Modify: `src/shenbi/skill_utils/drift_detection/compute_drift.py:278-280`（卷级排除丢弃）
- Modify: `src/shenbi/records/drift.py:57`（重复 id last-wins）
- Modify: `docs/superpowers/specs/2026-08-14-minor-findings-batch-design.md`（头注记收窄）
- Modify: `docs/superpowers/specs/INDEX.md`（#16 内容注记）
- Test: `tests/unit/test_records_drift*.py` 等（追加）

**Fixes:**
- F510: `ap.parse_args` 后 `if args.cmd == "report": ... return 0` + 尾部 `return 2` —— subparsers required=True 且仅一子命令 → 重构为直接 dispatch（保 return 2 为 argparse 失败路径的显式防御并注释），删除不可达形态（print 归 #50 不动）
- F657: `volume_scores = [score for score, _ in overall_series]`（human_overridden 标志被丢）→ 过滤被排除项：`[score for score, overridden in overall_series if not overridden]`（核对 tuple 第二元语义后实施；若该元并非 override 标志，记 deviation 驳回）
- F658: `out[rid] = row` 重复 id 覆盖 → 首个保留：`if rid not in out: out[rid] = row` + 注释 first-wins
- spec 注记：头 `Status: Design` → `Status: Revised (2026-08-30 · 收窄为 41 条无主残留执行，82 条移交活跃簇，6 条已修核销——见归档注记)`；INDEX #16 内容字段补「2026-08-30 收窄：41 条残余执行中，移交清单见归档」

**Steps:** implement + tests → commit `fix: spec #16 Z5/Z6 residual fixes (F510/F657/F658) + docs annotation`

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| grep 无残留目标模式 | T1-T8 | 每 finding 的指控模式 grep = 0（progress.md 验收证据逐条记） |
| `just check` 全绿 | 阶段 7 | `just check` 完整输出 |

复杂度：全部 infra（协调者亲做）。test_kind：F151/F152/F263/F264/F271/F258/F480/F490/F4A1/F658 = tdd_red_green；其余 = characterization / grep 验证。
