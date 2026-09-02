# Spec #39 静默吞错与部分校验面修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 C13 簇 30 条 active findings 的静默吞错与部分校验（吞门禁/假值数值域/解析器部分校验/checker 只验表面/杂项静默），配 `c13_regression` 违规构造翻转回归集（任务面 31 项，F233 以残余形态计入）。

**Architecture:** 五条修复线（对应 spec T1-T5）：吞门禁清剿（gates/audit 链路 except 窄化+结构化披露）、scoring 数值域前置校验、路径/字段/协议解析完备（含 F116 逗号 fail-fast helper）、g4/g7 checker 语义化、杂项 fail-closed。T6 回归集以 pytest marker `c13_regression` 汇总。全部为 infra 级（gates/contracts/dispatcher/audit/orchestration）→ **协调者亲自实现，TDD 红-绿**。

**Tech Stack:** Python 3.11+, pytest, structlog, ruff (BLE001), uv/just。

## Global Constraints

- AGENTS.md：`src/shenbi/` 无 `print()`（structlog）；gate 检查器纯校验幂等无副作用；conventional commits；状态字面量唯一定义于 `src/shenbi/contracts/enums.py`（新增代码禁裸状态字符串，`tools/lint_status_strings.py` 必须保持绿）
- G0.9：对抗性违规样本**内联写在 test 代码内**，不入 `tests/fixtures/`；scenario 输入引用 `tests/fixtures/` 真实产物
- 验证走 `just`/`uv run`（与 CI `uv run --frozen` 同构）
- 每个测试标注 `@pytest.mark.c13_regression`（翻转用例）；**marker 注册（`pyproject.toml [tool.pytest.ini_options] markers`）在 Task 1 Step 0 先行落地**（`--strict-markers` 下未注册 marker 会让 T1-T12 全部红测在 collection 阶段假红）；存量既有测试不迁移 marker
- commit 一律 pathspec 显式列文件

---

### Task 1: G7 撕裂行检测（F535+F410 · spec T1+T4）

**Files:**
- Modify: `src/shenbi/gates/g7_trace.py:18-60`、`pyproject.toml`（pytest markers）
- Test: `tests/unit/gates/test_g7_trace.py`（追加）

**Interfaces:**
- Produces: `_read_only_events(path) -> tuple[list[TraceEvent], int, int]`（events, torn_at_line, total_nonblank_lines）；`audit_trace` 在 torn 时追加 `mf` 条目 `G7T.tamper: torn line at <n> (内容被改/链断裂)` 并在 checks 加 `{"id": "G7T.torn", "s": GateStatus.FAIL, "torn_line": n, "total_lines": m}`

- [ ] **Step 0: 注册 marker**：`pyproject.toml [tool.pytest.ini_options] markers` 追加 `"c13_regression: C13 cluster violation-construction flip tests (spec #39)"`
- [ ] **Step 1: 红测**（内联构造合法链 + 中段插入非法 JSON 行 → 期望检出 tamper，而非前缀 PASS）：

```python
@pytest.mark.c13_regression
def test_g7_torn_line_is_tamper_candidate(tmp_path):
    # build 3 valid events via TraceEvent + sign chain (reuse existing test helpers)
    ...
    bad = valid_lines[:1] + ["{not json"] + valid_lines[1:]
    (tmp_path / "trace.jsonl").write_text("\n".join(bad), encoding="utf-8")
    mf, checks = audit_trace(tmp_path)
    assert any("torn" in m for m in mf)  # F535: 插入非法行必须检出
```

另测尾部截断披露：文件末行撕裂 → checks 含 `G7T.torn` 且 `total_lines` 披露（F410）。注：既有 `tests/unit/gates/test_g7_trace.py` 仅 clean/tamper/absent 三用例、无 torn 前缀 PASS pin——若实跑发现有 pin 按新语义更新断言（解 pin 禁删测试）。
- [ ] **Step 2:** `uv run pytest tests/unit/gates/test_g7_trace.py -k torn -v` → FAIL（真实断言失败，非 marker 错误）
- [ ] **Step 3:** 实现：`_read_only_events` 改签名返回三元组；坏行不再 break——记录 `torn_line`（1-based 行号）后 `continue` 收集剩余可解析行；`audit_trace` 中 `torn_line is not None` → `mf.append(f"G7T.tamper: torn line at {torn_line} (内容被改/链断裂)")` + `checks.append({"id": "G7T.torn", "s": GateStatus.FAIL, "torn_line": ..., "total_lines": ...})`。既有 pin「坏行 break=PASS」测试按新语义改断言（解 pin，禁删除测试函数）。
- [ ] **Step 4:** 测试绿后 commit `fix: G7 torn-line tamper detection (F535/F410)`
- [ ] **Step 5:** 产出 `.superpowers/sdd/audit-T1.md`

### Task 2: G5.3 数值一致性解死代码（F708 · spec T1）

**Files:**
- Modify: `src/shenbi/gates/g5.py:151,157`
- Test: `tests/unit/gates/test_g5.py`（追加；F708 pin 在 :139-163）

**Interfaces:**
- Produces: `num_pat = re.compile(r"(\d+)\s*(个|种|人|章|次|处|条|名|位|倍|%|万|千|百)")`（单位组改捕获组，`m.group(2)` 合法）

- [ ] **Step 1: 红测**（内联构造两个 world md 文件，同一概念+单位不同数值 → 期望 `numeric:` conflict；当前因 IndexError 被吞永远无 conflict）：
- [ ] **Step 2:** `uv run pytest tests/unit/gates/test_g5.py -k numeric_conflict -v` → FAIL
- [ ] **Step 3:** 正则单位组去 `(?:` 改捕获；既有 pin 测试（若有断言"无 conflict"）按新语义更新
- [ ] **Step 4:** 绿后 commit `fix: G5.3 numeric consistency un-dead via capture group (F708)`
- [ ] **Step 5:** audit-T2.md

### Task 3: G6.4 future_knowledge 守卫可达化（F709 · spec T1）

**Files:**
- Modify: `src/shenbi/gates/g6_checks.py:51-71`
- Test: `tests/unit/gates/test_g6_checks.py`（追加；F709 pin 在 :130-146）

**Interfaces:** 保持 `check_continuity(chapters: list[Path])`（g6_checks.py:15）外部签名不变，内部改两遍扫描。

- [ ] **Step 1: 红测**（内联构造 chapter-001.md 引入"金手指"、chapter-003.md 写"知道金手指"→ 期望 `future_knowledge` violation；当前恒假检不出）
- [ ] **Step 2:** 红
- [ ] **Step 3:** 实现：第一遍按章号升序构建 `intro_map`（完整扫描全部章节后 intro_map 为全局最早引入章）；第二遍扫描 know_pat，命中时若 `intro_map[ent] > cn`（实体在本章之后才首次引入）→ violation。章号排序用 `sorted(chapters, key=chapter_num)`；既有 pin 测试解 pin 更新
- [ ] **Step 4:** 绿后 commit `fix: G6.4 future_knowledge guard reachable via two-pass scan (F709)`
- [ ] **Step 5:** audit-T3.md

### Task 4: write_audit/compute_stats 吞错披露（F507/F610 · spec T1）

**Files:**
- Modify: `src/shenbi/audit/write_audit.py:30-38`、`src/shenbi/skill_utils/style_learning/compute_stats.py:355-372`
- Test: `tests/unit/audit/test_write_audit.py`（追加 F507 用例）、`tests/unit/skill_utils/test_compute_stats.py`（追加 F610 用例）

- [ ] **Step 1: 红测**（write_audit：monkeypatch `derive_output_files` 抛 RuntimeError → 期望 WARN 日志事件 `derive_outputs_failed` + 返回 []；compute_stats：不可读文件（构造权限/不存在路径）→ WARN 事件 `chapter_read_failed` + 返回 dict 不含该文件）
- [ ] **Step 2:** 红
- [ ] **Step 3:** 实现：两处 `except Exception` 改 `except Exception as e: log.warning("derive_outputs_failed", skill=skill, error=repr(e)); return []`（compute_stats 同型 `log.warning("chapter_read_failed", path=str(p), error=repr(e))`）。窄化不加——derive_output_files 内部调用面广，WARN+上下文即满足 spec「窄化或结构化处理」二选一
- [ ] **Step 4:** 绿后 commit `fix: write_audit/read_chapters swallow → WARN disclosure (F507/F610)`
- [ ] **Step 5:** audit-T4.md

### Task 5: BLE001 blind-except lint 接入（spec T1 防复发 · 验收 1）

**Files:**
- Modify: `pyproject.toml` `[tool.ruff]` lint select 加 `"BLE"`；per-file ignores 逐文件豁免存量点
- Test: `uv run ruff check src/shenbi/` 自身即验证

**Interfaces:** 豁免白名单 = T1-T4 修复后仍存的 `except Exception` 点（每处须有结构化处理注释）；新增违规 = CI 红。

- [ ] **Step 1:** `grep -n "except Exception" src/shenbi/ -r` 盘点存量；`pyproject.toml` `[tool.ruff.lint] select` 追加 `"BLE"`，`[tool.ruff.lint.per-file-ignores]` 对存量非本 spec 范围文件豁免 `BLE001`（范围文件不豁免）
- [ ] **Step 2:** `uv run ruff check src/shenbi/` 绿
- [ ] **Step 3:** commit `chore: ruff BLE001 blind-except lint with explicit per-file allowlist`
- [ ] **Step 4:** audit-T5.md

### Task 6: scoring 数值域与 fail-closed（F133/F132/F137 · spec T2+T5）

**Files:**
- Modify: `src/shenbi/scoring.py:55-70（权重解析）,204-208（validate_scores）,216-225（compute_score）,115-131（applicability）`
- Test: `tests/unit/test_scoring.py`（追加数值域用例）

**Interfaces:**
- Produces: `validate_scores(dimensions, scores)` 新增拒绝：`isinstance(score, bool)` → REJECT；`not math.isfinite(score)` → REJECT。`compute_score`：任何 `d["weight"] <= 0` → 返回前 `log.error("invalid_weight", ...)` 并 raise `ValueError`（负/零权重不再参与）。`parse_applicability` 缺格（cells 越界）→ 显式记 `missing_cell` 计数并按 NOT-APPLICABLE（fail-closed）处理，附 WARN。

- [ ] **Step 1: 红测**（全部 c13_regression，内联构造）：
  - 负权重 rubric（-20/+120）+ 分数 → 期望异常/FAIL 而非 final_score>100
  - `{"1": float("nan")}` → REJECT；`{"1": True}` → REJECT
  - applicability 表缺格 → 该维不计入（fail-closed）+ WARN
- [ ] **Step 2:** 红
- [ ] **Step 3:** 实现（isfinite/isinstance(bool) 前置；weight<=0 raise；缺格 fail-closed + WARN）。存量产物影响：grep tests/fixtures 中 rubric 缺格形态，如触发 FAIL 先在 spec-deviations 记盘点结果再切换
- [ ] **Step 4:** `uv run pytest tests/unit/test_scoring.py tests/unit/test_scoring_applicability.py -v` 全绿后 commit `fix: scoring weight/NaN/bool domain + applicability fail-closed (F133/F132/F137)`
- [ ] **Step 5:** audit-T6.md

### Task 7: paths family/anchor 解析完备（F207/F208/F209/F228 · spec T3）

**Files:**
- Modify: `src/shenbi/contracts/paths.py:92-147`
- Test: `tests/unit/contracts/test_paths_family.py`（新建；`tests/unit/contracts/` 已存在）

**Interfaces:**
- `resolve_contract_path(path, chapter, ctx)`：family 键 `val is None` → raise `UnresolvedPathError(path)`（不再回退 chapter 语义）；替换后若仍含 `_FAMILY_N`（第二个同键或异键 family 占位符）→ raise；family 替换与 AC-NNN 替换不再互斥提前 return——先做 family（全部出现），再 anchor，再 `resolve_chapter_path`
- NNN 无界 `path.replace(_NNN, ...)`（:143）改为 `_NNN_RE.sub(lambda _: f"{chapter:03d}", path)`（有界语义：NNN 是完整 token，正则锚定）

- [ ] **Step 1: 红测**（内联）：ctx.family 缺值含 family 占位符 → UnresolvedPathError；`f-{arc-N}/vol-{arc-N}` 双占位符全替换；`AC-NNN` + `vol-N` 共存路径两者都解析；NNN 不误伤 `ANNN` 类 token
- [ ] **Step 2-4:** 红→实现→绿，commit `fix: contract path family/anchor explicit resolution (F207/F208/F209/F228)`
- [ ] **Step 5:** audit-T7.md；`just generate` 幂等 diff 核验（无契约源头变更应为空）

### Task 8: F116 逗号路径 fail-fast（spec T3）

**Files:**
- Create: `src/shenbi/contracts/file_list.py`（或置于 `audit/_shared.py`，按 import 方向选 contracts——被 dispatcher/scoring/phase_runner/pipeline 共用）
- Modify: `src/shenbi/dispatcher/executor.py:131`、`src/shenbi/scoring.py:390`、`src/shenbi/pipeline/dispatch_helper.py:2699`、`src/shenbi/phase_runner.py:257,260`
- Test: `tests/unit/contracts/test_file_list.py`（新建）

**Interfaces:**
- Produces: `def join_gate_file_list(files: list[str]) -> str`：任一 `","` in f → raise `ValueError(f"gate file list cannot contain commas (C34 protocol migration pending): {f}")`；否则 `",".join(files)`。四个生产点全部改用（空列表返回 `""`）

- [ ] **Step 1: 红测**（c13_regression，内联）：`join_gate_file_list(["a,b.md", "c.md"])` → ValueError；正常列表 → 逗号串；**四个生产点各 ≥1 含逗号拒斥断言**（executor.run_g2/run_g4 monkeypatch run_subprocess_json、scoring gate-only 路径、dispatch_helper G4 cmd 构造、phase_runner post-skill——经各调用面既有测试文件追加）；空列表 → ""
- [ ] **Step 2-4:** 红→实现+四点接线→`uv run pytest tests/unit/contracts/test_file_list.py tests/unit/dispatcher tests/unit/test_phase_runner.py -x -q`→绿，commit `fix: comma-path fail-fast across gate file-list producers (F116)`
- [ ] **Step 5:** audit-T8.md

### Task 9: 解析器静默覆盖/回退清剿（F217/F367/F606/F607/F623/F233残余/F218/F219 · spec T3+T4）

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py:78-82,114-118`、`src/shenbi/pipeline/genesis.py:375`、`src/shenbi/records/drift.py:82,113-124`、`src/shenbi/records/parser.py:48`、`src/shenbi/contracts/fields.py:61-68`、`src/shenbi/dispatcher/modes/codex.py:129` 附近、`src/shenbi/dispatcher/modes/internal.py:15-27`
- Test: `tests/unit/dispatcher/`（executor/codex/internal 对应文件）、`tests/unit/pipeline/test_genesis.py`、`tests/unit/records/test_drift.py`、`tests/unit/records/test_parser.py`、`tests/unit/contracts/test_fields.py:112-121`（F233 残余追加点）各追加

**Interfaces / 修复形态：**
- F217：`derive_file_type`/`derive_input_files` 的 `except ContractError: return "chapter"/[]` → `log.error("contract_error_fallback", skill=skill)` 后返回原值（保留回退但披露；上层 run_g1/g2 已有 FAIL 透传路径）——显式降级注记而非静默
- F367：`state.genesis.skills_done` 用前 `if step.skill not in state.genesis.skills_done:` 防重复 append（genesis 状态 schema 不变，list 语义保留、幂等写入；与 spec「set 语义」字面偏离已记 spec-deviations——语义等效无重复，避免 schema 迁移）
- F607：drift.py:82 重复 id → `log.warning("duplicate_id_first_wins", id=rid)`（语义不变只披露，F658 兼容）
- F606：`detect_cross_section_drift` 尾部追加反向遍历：`for rid in by_id: if rid not in md_rows: issues.append(f"drift: YAML id={rid} not in markdown table")`
- F623：parser.py:48 改显式循环：非 dict 元素 `log.warning("record_row_not_dict_discarded", index=i)` + 计数
- F233 残余：fields.py extract_h2_sections 重复 H2 → `log.warning("duplicate_h2_first_wins", heading=h)`
- F218：codex.py `_extract_json_object` 成功后 `finally`/显式 `raw_out.unlink(missing_ok=True)`（在解析完成后、返回前清理 .raw）
- F219：internal.py 报错文案与 docstring 删除 `SHENBI_LLM_API_KEY` 指引，改为实际语义：`"internal mode has no LLM backend, cannot score. Use codex CLI dispatch or the pipeline API entrypoint (pipeline/dispatch_helper)."`

- [ ] **Step 1: 红测**（c13_regression，内联逐条）：契约损坏 skill → 有 error 日志事件 + 回退值；重复 record_step 同 skill → skills_done 无重复；重复 id → WARN 事件；YAML-only id → drift 报；非 dict 行 → WARN；重复 H2 → WARN；dispatch 后 .raw 不存在；internal 报错文案不含 SHENBI_LLM_API_KEY
- [ ] **Step 2-4:** 红→实现→绿，commit `fix: parser silent-override/fallback disclosure batch (F217/F367/F606/F607/F623/F233/F218/F219)`
- [ ] **Step 5:** audit-T9.md

### Task 10: checker 语义化 batch 1（F420/F422/F421/F430/F405 · spec T4）

**Files:**
- Modify: `src/shenbi/gates/g4/review_arc_payoff.py:34,102`、`src/shenbi/gates/g4/review_resonance.py:121`、`src/shenbi/gates/g4/character_design.py:60-75`、`src/shenbi/gates/g4/genre_config.py:29-44`、`src/shenbi/gates/g4/generic.py:178-192`
- Test: `tests/unit/gates/g4/test_review_arc_payoff.py`、`tests/unit/gates/g4/test_character_design.py`、`tests/unit/gates/g4/test_genre_config.py`、`tests/unit/gates/g4/test_generic.py` 各追加

**修复形态：**
- F420：`_FORESHADOW_FLOOR_RE` 改语义解析：`re.compile(r"伏笔兑现质量[^\d]{0,10}(\d+(?:\.\d+)?)")` 提取报告分值 v，`v >= 15` PASS，否则 mf `G4.ap.foreshadow_subfloor:{v}<15`；无匹配 → mf `G4.ap.foreshadow_floor_missing`
- F422：证据正则改**上下文锚定方案（唯一方案，禁止裸 `:\d+` 变体）**：匹配 `(?:line|行|L)\s*(\d+)` 或同行含 `file|文件` 字段的 `:(\d+)`——实现上要求匹配处同行存在文件引用字样才算 file:line 证据；红测双向断言：纯时间戳 "发生于 12:30" 不再满足（收紧），`行 42`/`line 42` 仍算证据（防误收紧的正向断言）
- F421：character_design `_validate_protagonist` 逐字段：字段在 mf（missing_*）时**不**追加对应 PASS check；同字段互斥
- F430：genre_config 遍历 `for gc in fps:`（全部文件逐个 validate），不再只 `fps[0]`
- F405：generic.py 否定过滤对**每个**匹配位置检查（`for m in re.finditer(re.escape(sug), content, re.IGNORECASE)` 任一位置无否定即算 real_suggestion），替换 `.index()` 首位置

- [ ] **Step 1: 红测**（c13_regression，内联违规样本）："伏笔兑现质量 12 < 子地板 15 ✗" → FAIL；"发生于 12:30" 证据行不算 file:line；同字段 PASS+must_fix 不共存；两文件第二份 invalid → 报；否定词在第二出现处 → 正确判定
- [ ] **Step 2-4:** 红→实现→绿，commit `fix: g4 checkers semantic validation batch 1 (F420/F422/F421/F430/F405)`
- [ ] **Step 5:** audit-T10.md

### Task 11: checker 语义化 batch 2（F749/F513 · spec T4）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:42-50`、`src/shenbi/orchestration/escalation_bridge.py:20`
- Test: `tests/unit/gates/g4/test_chapter_drafting.py`（F749 追加锚）、`tests/unit/orchestration/test_bridges.py`（F513 追加）

**修复形态：**
- F749：先切出 Section 7（`re.split(r"^## ", plan_text, flags=re.MULTILINE)` 取标题匹配 `Section 7|Hook Ledger` 的块；无该节 → 返回 [] 或按 plan 无 hooks 语义）再 findall；docstring 同步为真实行为
- F513：`if val > 0:` → `if val >= 0:`（0 分保留；负值仍跳过——非分数噪声）
- **F522 已剔除**（plan 审查 R1 复核：truth_index 的 `extra=` 是 IndexEntry dataclass 字段、estimate.py 是 stdlib logging 合法用法，structlog 调用零 `extra=` kwarg——指控形态在 main 不存在；spec 修订记录已同步）

- [ ] **Step 1: 红测**（c13_regression，内联）：plan Section 3 出现 MH-999、Section 7 无 → 不报 hook_unfulfilled；trend 表 0 分行被 parse 进 scores
- [ ] **Step 2-4:** 红→实现→绿，commit `fix: hook scan Section-7 scoping + zero-score retention (F749/F513)`
- [ ] **Step 5:** audit-T11.md

### Task 12: 杂项 fail-closed/SKIP 标注（F381/T305 · spec T5）

**Files:**
- Modify: `src/shenbi/orchestration/escalation_bridge.py:31-38`、`src/shenbi/skill_utils/escalation/check.py:56,88,129,144`、`src/shenbi/contracts/fields.py:107-117`
- Test: `tests/unit/orchestration/test_bridges.py`（F381 追加）、`tests/unit/contracts/test_fields.py`（T305 追加）

**修复形态：**
- F381：`run_escalation_check` 的 `volume_objective_met: bool = True` → `bool | None = None`；**同步 `check_escalation` 签名**（check.py:56 `volume_objective_met: bool` → `bool | None`，mypy/basedpyright strict 下必改）；判定处 `volume_objective_met is None` → `log.warning("volume_objective_unknown_skip")` 且不触发 signal（显式 SKIP，不再默认满足）；`False` → signal 照旧。**既有调用点两处**（chapter_loop.py:1103 传 `_check_volume_completion` 计算值、check.py:144 CLI 入口）传 bool 子类型签名兼容；CLI flag `--volume-objective-met` 默认值同步改 `none`（choices true/false/none）保持 fail-closed 语义一致
- T305：`filter_to_fields` 末尾 `return text, True` → `log.warning("field_filter_unknown_extension_passthrough", path=path)` 后原样返回

- [ ] **Step 1: 红测**（c13_regression）：unknown volume objective 不产生 volume_objective_missed 误报、不默认满足；未知扩展名 → WARN 事件
- [ ] **Step 2-4:** 红→实现→绿，commit `fix: volume objective explicit SKIP + unknown extension WARN (F381/T305)`
- [ ] **Step 5:** audit-T12.md

### Task 13: c13_regression 回归集汇总与验收运行（spec T6 + 验收 1-5）

**Files:**
- Verify: `pyproject.toml` marker 注册（Task 1 Step 0 已落地，此处仅核验存在）
- Test: 核验既有 T1-T12 测试 marker 覆盖

**Interfaces:** `uv run pytest -m c13_regression -q` 全绿 = spec 验收 2。

- [ ] **Step 1:** 对账 T6 锚点清单 27 项（F133/F132/F207/F208/F209/F228/F116/F217/F367/F420/F421/F422/F430/F405/F410/F535/F708/F709/F606/F607/F623/F513/F749/F381/F137/T305/F233残余）逐一 grep 对应测试存在；缺则补
- [ ] **Step 2:** 运行并粘贴验收命令输出到 progress.md：
  - `git grep -n "except Exception" src/shenbi/gates/ src/shenbi/scoring.py src/shenbi/audit/`（人工清单核销）
  - `uv run pytest -m c13_regression -q`
  - `uv run shenbi-validate G4 <skill> <files>`：正常面用真实 fixture（如 `tests/fixtures/chapter-2-draft.md`，按 G4 checker 实际消费的 fixture 目录执行时以 `ls tests/fixtures/` 现核为准）；含逗号路径为对抗性内联输入 → 显式 ValueError
  - `just check`
- [ ] **Step 3:** commit `test: c13_regression marker registration + coverage reconciliation (spec #39 T6)`
- [ ] **Step 4:** audit-T13.md

---

## 验收覆盖表（spec 验收 → task → 命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1. except Exception 人工清单 + BLE001 CI | T4/T5 | git grep 输出 + `uv run ruff check src/shenbi/` |
| 2. 回归套件全绿（7 代表翻转用例） | T13 | `uv run pytest -m c13_regression -q` |
| 3. G4 含逗号路径显式报错 | T8/T13 | `uv run shenbi-validate G4 ...` + 内联 ValueError 测试 |
| 4. F218 .raw 不残留 / F219 文案 | T9 | 红测断言 |
| 5. just check 全绿 | T13 | `just check` |

## 评分场景声明
本 spec 无评分流程变更（G3.4 不适用）；全部验证为确定性测试与只读 CLI。
