# Z7-a 段审查报告（tests/unit/ 全部 236 文件）

- 审查轮次: 2026-08-15 全项目深度审查
- 分区: Z7-a（tests/unit/ 236 个文件，只读深读）
- 审查 agent: Z7-a
- findings 编号段: F701–F719
- 覆盖率交叉参照: docs/superpowers/audit-runs/2026-08-15/d1/d1-06-coverage-gaps.log
- 方法: 全部 236 文件逐一语义深读（无抽样遗漏）；src/ 关键签名与被断言的 src 行为逐一 grep 核对；`uv run pytest --collect-only -q` 验证三个代表性文件可收集（96 tests collected）；未执行任何测试运行态。

## 总览

| 指标 | 值 |
|---|---|
| 清单文件数 | 236 |
| 深读文件数 | 236（100%） |
| findings | 19（P1×4，P2×10，M×5） |
| skip/xfail 处置 | 10 处（keep×8，stale×2）；D1 静态清点"仅 2 处"不完整 |
| 未覆盖文件 | 无 |

严重度按决策表判定；多处命中取最高。

---

## findings 总表

| # | 标题 | 类别 | 严重度 | 证据 |
|---|---|---|---|---|
| F701 | lockfile 权限测试同义反复（不调用被测代码） | error | P1 | tests/unit/test_safe_write.py:62-100 |
| F702 | `or True` 恒真断言掩盖 weight_mismatch 警告验证缺失 | error | P1 | tests/unit/test_scoring.py:435-441 |
| F703 | `assert len(result) >= 0` 空断言 | error | P1 | tests/unit/pipeline/test_review_checklist.py:207-209 |
| F704 | 内联重实现被测逻辑的"自证"测试（modify 反馈 / step 回滚 / C1 守卫） | error | P1 | tests/unit/pipeline/test_cli.py:817-862; test_final_review_fixes.py:56-75 |
| F705 | 单测改写仓库真实文件 tests/tiers/deps.json（xdist 竞态 + 声称的 skip 不存在） | error | P2 | tests/unit/test_scoring.py:517-545 |
| F706 | g4/conftest.py 两个 fixture 全死代码且携带 D26 后已废弃的 `target_words` 字段 | optimization | P2 | tests/unit/gates/g4/conftest.py:10-27 |
| F707 | 覆盖率阈值 78% 与文档声明的 ≥80% floor 漂移 | error | P2 | tests/unit/test_coverage_thresholds.py:23-30 |
| F708 | src g5.py m.group(2) 必然 IndexError 被 except 吞掉 → G5.3 数值一致性检测整段死代码（测试 pin 而不修） | error | P2 | src/shenbi/gates/g5.py:153-171; tests/unit/gates/test_g5.py:139-163 |
| F709 | src g6_checks.py future_knowledge 守卫数学上不可达（intro_map[ent] > cn 恒假） | error | P2 | src/shenbi/gates/g6_checks.py:44-64; test_g6_checks.py:130-146 |
| F710 | GR.2 文件名解析不剥 `-scores` 后缀：生产命名报告误报 `status=?` FAIL（测试绕开而非覆盖） | error | P2 | tests/unit/gates/test_g_reconcile.py:1-16,33-46 |
| F711 | chapter_revision 门输出非词表状态 `HARD_FAIL`（违反 GateStatus 闭合集契约，测试 pin） | error | P2 | src/shenbi/gates/g4/chapter_revision.py:97; test_chapter_revision.py:112,142,179 |
| F712 | 2 处 `pytest.skip("...not yet created")` 守卫已过期（文件现存在）；D1 静态 skip 清点漏计 8 处运行时 skip | error | P2 | test_bridge_tracker.py:13-14,22-24; g4/test_state_settling.py:166-167 |
| F713 | D16 哨兵断言被 `if g610 is not None` 条件包裹 → 检查消失时哨兵空洞通过 | error | P2 | tests/unit/gates/test_g6.py:607-615 |
| F714 | test_logging.py docstring 引用不存在的 `tests/logging.py` | error | M | tests/unit/test_logging.py:5 |
| F715 | MASTER_PATH 手工保存/恢复非异常安全 + 测试名/docstring 名不副实 | error | M | tests/unit/test_plugins_generate.py:53-68 |
| F716 | 弱断言/条件断言集合（7 处） | error | M | 见 finding 正文 |
| F717 | 覆盖缺口：memory_distill 12%、score_* 检查器 not_found/SKIP 分支、sync_contracts 56%、audit_context_cache 54%、drift baseline 19%、safe_write 锁竞争 66% | error | P2 | d1-06-coverage-gaps.log 对应行 |
| F718 | `seed` 形参未使用（property 壳） | error | M | tests/unit/test_phase_runner_property.py:48-52 |
| F719 | test_field_filtering.py 声称测 dispatch_helper 集成但只测 contracts.fields 本体 | error | P2 | tests/unit/pipeline/test_field_filtering.py:1-17 |

---

## findings 详情

### F701 | lockfile 权限测试同义反复 | error | P1
- 证据: tests/unit/test_safe_write.py:62-80（test_lockfile_has_correct_permissions）、:83-100（test_lockfile_permissions_are_set_via_os_chmod）
- 根因: 两个测试自行 `os.open(...O_EXCL...)` + `os.chmod(lockfile, 0o600)` 后断言权限等于刚设置的值——全程未 import/调用 `shenbi.safe_write._acquire_lock`。删除 src 中的 `os.chmod(lockfile, 0o600)`（safe_write.py:69,79,90）测试仍通过。这是安全相关属性（锁文件权限）的 mock 自证。
- 验证命令: `grep -n "_acquire_lock\|safe_write" tests/unit/test_safe_write.py` → 仅 `from shenbi.safe_write import safe_write`（line 10），无 `_acquire_lock` 调用；src/shenbi/safe_write.py:68-69 确认 chmod 在 `_acquire_lock` 内。
- 建议方向: 重写为强制走 O_EXCL 回退路径（参照同文件 test_safe_write_lockfile_fallback_cleanup_posix 的 monkeypatch fcntl.flock 法）后断言磁盘上 lockfile 的 st_mode。

### F702 | `or True` 恒真断言 | error | P1
- 证据: tests/unit/test_scoring.py:435-441
  `assert (any(... caplog.records ...) or True)`
- 根因: structlog 不经 std logging，caplog 捕不到 `weight_mismatch`（src/shenbi/scoring.py:172 用 `log.warning`），作者以 `or True` 让测试变绿。恒真断言 = 测试声称的检查（权重≠100 告警）从未被验证；scoring.py 覆盖率 97% 但该告警路径实际无断言保护。
- 验证命令: `grep -n "weight_mismatch" src/shenbi/scoring.py` → `172: log.warning("weight_mismatch", total_weight=total_weight, expected=100)`（structlog）。
- 建议方向: `patch("shenbi.scoring.log")` 或 capsys 捕 stderr JSON 行断言 `weight_mismatch` 事件；删除 `or True`。

### F703 | `assert len(result) >= 0` 空断言 | error | P1
- 证据: tests/unit/pipeline/test_review_checklist.py:207-209（TestExtractHookDeliverables.test_extracts_planted_hooks）
- 根因: docstring 说“Only returns H001 (PLANTED state, due chapter 5 >= current chapter 4)”但断言 `assert len(result) >= 0` 恒真。钩子交付提取（review checklist 的关键内容）正例零保护。
- 验证命令: 文件读取（见行号）；src review_checklist._extract_hook_deliverables 无其它测试覆盖其过滤逻辑。
- 建议方向: 改为 `assert [h["id"] for h in result] == ["H001"]`（负例 H002 RESOLVED 已在 fixture 中）。

### F704 | 内联重实现被测逻辑的自证测试 | error | P1
- 证据 1: tests/unit/pipeline/test_cli.py:848-862 test_modify_injects_feedback_into_dispatch_prompt——prompt 拼接与 feedback 消费逻辑在测试体内重实现（“same logic as run_chapter_step”），断言的是自己的模拟串。
- 证据 2: tests/unit/pipeline/test_cli.py:817-846 test_modify_chapter_memo_rolls_back_step_index——step_index 回滚 `if cp.type == CHAPTER_MEMO: step_index = 1` 在测试体内模拟，仅 clear_checkpoint 是真代码。
- 证据 3: tests/unit/pipeline/test_final_review_fixes.py:56-75 TestC1TriggerReFireGuard——`state.chapter_loop.step_index = 1` 手工设置后断言 `not (step_index == 0 and ...)`，纯同义反复。
- 根因: 回归测试写成“模拟期望行为”而非驱动真实编排器。若 run_chapter_step/cmd_review 丢掉 feedback 注入或回滚，这三个测试照样绿。
- 验证命令: 三个测试体内均无对 `run_chapter_step`/`_build_skill_prompt` 的调用（对照同文件 test_chapter_loop.py 真实驱动的写法）。
- 建议方向: 用 monkeypatch dispatch 捕获真实 prompt（同 test_chapter_loop.py 的 mock_disp.call_args 模式），断言 modify_feedback 出现且被消费；C1 用真实 `next` 驱动验证 resume 后不重入触发块。

### F705 | 单测改写仓库真实文件 deps.json | error | P2
- 证据: tests/unit/test_scoring.py:517-545 test_t2_phase_branch_uses_real_deps_json——`deps_path.write_text(...)` 直接覆盖 `tests/tiers/deps.json`，finally 恢复。
- 根因: (a) docstring 声称 “skipped if tests/tiers/deps.json is read-only (CI sandboxes)” 但代码没有实现该 skip，只读环境下会直接 FAIL；(b) `pytest -n auto`（justfile/CI 默认）下其它 worker 并发读真实 deps.json（test_g5.py 的 gate_G5、test_deps.py 断言 `"genesis" in d.t2_phases`）存在竞态窗口；(c) 测试进程在 write 与 finally 之间被杀会留下损坏的 tracked 文件。
- 验证命令: `git ls-files tests/tiers/deps.json` → 已跟踪；`grep -rn "t2-phases" tests/unit/gates/test_g5.py tests/unit/contracts/schemas/test_deps.py` → 两处运行期读取同一文件。
- 建议方向: monkeypatch `shenbi.scoring` 内 deps 路径常量指向 tmp 文件；或 monkeypatch jload。

### F706 | g4/conftest.py 死 fixture + 废弃字段 | optimization | P2
- 证据: tests/unit/gates/g4/conftest.py:10-27 定义 `sample_skill_output` / `empty_skill_output`；`grep -rn "sample_skill_output\|empty_skill_output" tests/ --include="*.py" | grep -v conftest` → 零使用。且 fixture 的 novel.json 使用 `target_words`（D26 后生产者权威字段为 `target_word_count`，NovelConfig extra=forbid 拒绝旧键——tests/unit/contracts/schemas/test_novel_scores_state.py:52-58 明确 pin）。
- 建议方向: 删除两个死 fixture（或接线使用并改用 `target_word_count`）。

### F707 | 覆盖率阈值与文档漂移 | error | P2
- 证据: tests/unit/test_coverage_thresholds.py:23 `BRANCH_THRESHOLD_PCT = 78` vs :28-30 docstring “must meet the permanent >=80% floor”；pyproject.toml:447-448 注释也声明 “>=80% branch … permanent”。
- 根因: 阈值被悄悄放宽 2 个点，文档与 CI 注释未同步——分支覆盖率跌破 80% 仍过闸。
- 验证命令: `sed -n 23,30p tests/unit/test_coverage_thresholds.py`；`grep -n "80%" pyproject.toml`。
- 建议方向: 二选一——恢复 78→80，或把三处文档统一改为 78 并说明让位原因。

### F708 | G5.3 数值一致性检测死代码（src bug，被 pin） | error | P2
- 证据: src/shenbi/gates/g5.py:153 `num_pat = re.compile(r"(\d+)\s*(?:个|种|人|...)")`（单捕获组）；:159 `unit = m.group(2)` 必然 IndexError；:171 `except Exception: continue` 吞掉。tests/unit/gates/test_g5.py:139-163 与 test_g5_coverage.py:41-43 明确 pin “numeric conflict is NOT detected (source bug)”。
- 根因: regex 单组 vs group(2) 读法不一致；宽 except 把 IndexError 与“文件不可读”混为一谈。
- 验证命令: `sed -n 150,171p src/shenbi/gates/g5.py`；`grep -n "group(2)" src/shenbi/gates/g5.py` → 仅 :159。
- 建议方向: 捕获组改为 `r"(\d+)\s*(个|种|...)"`；except 收窄为 OSError。修复后翻转两个 pin 测试为正断言。

### F709 | G6.4 future_knowledge 守卫不可达 | error | P2
- 证据: src/shenbi/gates/g6_checks.py:44-52 intro_map 按章节升序首现填充（值恒 ≤ 当前章），:61 `if intro_map[re_ent] > cn` 数学上恒假；test_g6_checks.py:130-146 pin “future_knowledge is never flagged (dead guard)”。
- 验证命令: `sed -n 44,64p src/shenbi/gates/g6_checks.py`（见上文摘录）。
- 建议方向: 语义应为“当前章 know_pat 命中但该实体首现于更晚章节”——需要全书 intro_map 先建完再逐章检查（两遍扫描）；当前一遍扫描结构决定了守卫永不触发。

### F710 | GR.2 `-scores` 后缀解析缺陷（src bug，测试绕开） | error | P2
- 证据: tests/unit/gates/test_g_reconcile.py:7-16 模块 docstring 记录：生产命名 `<skill>-generative-scores.json` 会假阳性触发 GR.2 `status=?` FAIL；:33-46 `_write_pattern2_report` 辅助函数专门用 pattern-2 命名“sidestep the parser bug”。
- 根因: GR.2 的磁盘文件名→(skill, test_type) 解析不剥 `-scores` 后缀（shared.find_report 接受三种命名，GR.2 只按一种反解析）。
- 验证命令: 文件内容读取；src/shenbi/gates/g_reconcile.py 对应解析段。
- 建议方向: GR.2 解析时 strip `-scores` 后缀，并补一条生产命名直接命中的回归测试。

### F711 | HARD_FAIL 破坏状态词表契约 | error | P2
- 证据: src/shenbi/gates/g4/chapter_revision.py:97 `"status": GateStatus.PASS if not issues else "HARD_FAIL"`；tests/unit/gates/g4/test_chapter_revision.py:112,142,179 断言 `"HARD_FAIL"`。src/shenbi/status.py:17-25 GateStatus 闭合集 {PASS,FAIL,SKIP,WARN,UNIMPLEMENTED}，注释明言 “a gate result envelope never carries a non-gate status”。test_all_skills_parametrized.py:173 的闭合集断言不含 chapter_revision（不在 20 技能清单内），故未撞车。
- 根因: 三元表达式右支绕过了 lint（test_lint_status_strings 的 ternary 检测覆盖 `{"status": ...}` 字面量场景，此处的字面量在不同上下文）。
- 验证命令: `grep -rn "HARD_FAIL" src/shenbi/` → 仅 chapter_revision.py 两处。
- 建议方向: HARD_FAIL → GateStatus.FAIL（must_fix 已携带 hard 语义）；同步改三处测试断言。

### F712 | 过期 skip 守卫 + D1 skip 清点不完整 | error | P2
- 证据: tests/unit/pipeline/test_bridge_tracker.py:13-14,22-24 `pytest.skip("bridge_tracker.md template not yet created")`——`truth/bridge_tracker.md` 现已存在（ls 验证）；tests/unit/gates/g4/test_state_settling.py:166-167 同理（`truth/character_matrix.md` 已存在）。
- 附带: D1 机械清点称全仓静态标记仅 2 处；实际 tests/unit/ 内 grep 到 10 处 skip 站点（2 个 mark.skipif + 8 个运行体 pytest.skip()），任务书要求的“逐条处置”覆盖如下（见下表）。
- 验证命令: `grep -rn "pytest\.skip\|pytest\.mark\.skip\|skipif\|xfail" tests/unit/ --include="*.py"` → 10 行；`ls truth/bridge_tracker.md truth/character_matrix.md` → 两文件均存在。
- 建议方向: 删除两处 stale 守卫（改为直接断言文件存在，防未来误删）；D1 清点补运行时 skip。

### F713 | D16 哨兵断言条件化 | error | P2
- 证据: tests/unit/gates/test_g6.py:607-613 `if g610 is not None: assert g610["s"] != "SKIP"`——若 G6.10 检查整体消失（比 dead-path 更彻底的回归），哨兵（canary #5，sentinel index 成员）静默通过。
- 建议方向: 前置 `assert g610 is not None, "G6.10 not emitted"`。

### F714 | docstring 路径笔误 | error | M
- 证据: tests/unit/test_logging.py:5 “These tests verify the REAL production code path in tests/logging.py” —— 应为 src/shenbi/logging.py。
- 建议方向: 修正 docstring。

### F715 | MASTER_PATH 手工恢复非异常安全 | error | M
- 证据: tests/unit/test_plugins_generate.py:63-68：手工 `original = gen_mod.MASTER_PATH` / 恢复；若 `pytest.raises` 断言失败（FileNotFoundError 未抛出），恢复行不执行，泄漏全局状态到后续测试。测试名 `test_load_master_with_valid_master_fails_on_bad_data` 与 docstring（“ValueError on invalid data”）名不副实——只测了 FileNotFoundError 分支；函数内重复 `import pytest`。
- 建议方向: 改 monkeypatch.setattr；测试名改为 `test_load_master_missing_file_raises`。

### F716 | 弱断言/条件断言集合 | error | M
- 证据与逐条:
  - tests/unit/gates/test_g2.py:40 `assert result["status"] in {"FAIL", "PASS"}  # behavior depends on impl`——双收 smoke。
  - tests/unit/gates/test_g5.py:225 `assert result["status"] in ("PASS", "FAIL")`——corrupt summary 分支双收。
  - tests/unit/cost/test_report.py:34 三连 or 的空台账断言。
  - tests/unit/pipeline/test_parallel_dispatch.py:82 `assert A not in B if "##" in result else True`——条件表达式断言，无 "##" 时恒过。
  - tests/unit/pipeline/test_context_curation.py:30 `assert "chapter-1.md" not in result.lower() or "1" in result`——右侧恒真。
  - tests/unit/test_scoring_anti_collapse.py:98-99 `assert isinstance(missing, list)`——类型断言近似恒真。
  - tests/unit/test_phase_runner.py:862-864 `if captured_outputs: assert ...`——cmd_post_skill 在 output_files 为空时不调 G2（src phase_runner.py:214 `if output_files:` gate），断言体不执行；且注释 “G2 should receive empty string” 与实际行为（不调用）不符。
  - tests/unit/gates/test_g0.py:215-216 `if g07 is not None:` 包裹 WARN 断言。
- 建议方向: 各改为精确断言或补 not-None 前置断言。

### F717 | 覆盖缺口（测试存在/缺失但行未覆盖） | error | P2
- 证据（d1-06-coverage-gaps.log 交叉）:
  - `src/shenbi/gates/g4/memory_distill.py 12%（18-36 全缺）`——本清单内**无任何** memory-distill 测试文件，且不在 test_all_skills_parametrized 的 20 技能清单；该 checker 在 closure/trigger 生产路径被 run_gate_g4 调用（test_closure.py 仅断言技能在 CLOSURE_STEPS 里，从不调用 checker 本体）。
  - `score_arc 80% / score_stratum 74% / score_volume 69%（各缺 23-24,27-35）`——not_found 与 SKIP 分支未测：test_g4_score_checkers.py 无 nonexistent-file/空列表用例，三个 score 检查器也不在参数化清单（ escalation_review 有、score_* 无）。
  - `src/shenbi/sync_contracts.py 56%（128-134,144-155,159-203）`——test_sync_contracts.py 只测纯函数，main()/CLI 半个模块未覆盖。
  - `src/shenbi/pipeline/audit_context_cache.py 54%（55-103 大块）`——tests/unit/pipeline/ 无对应测试文件（test_audit_layer.py 测的是 audit_layer）。
  - `src/shenbi/skill_utils/drift_detection/baseline.py 19%（44-85）`——无 baseline 测试。
  - `src/shenbi/safe_write.py 66%（71-91）`——O_EXCL 重试回退与 stale-takeover（10×0.1s backoff + unlink 重建）未测：多写者竞争路径零覆盖（F701 的两个假测试本应覆盖此处）。
  - `dispatcher/cli.py 0%` 与各 `__main__.py 0%`——清单内无 CLI 入口测试（低优先，注明）。
- 验证命令: `grep -rln "memory_distill\|audit_context_cache" tests/unit/` → 仅 test_closure.py（列表断言）；coverage log 行号见 d1-06。
- 建议方向: 补 memory_distill 专属测试文件；把 3 个 score checker 与 memory-distill、book_spine_init、escalation_review 一并纳入参数化清单；补 audit_context_cache / drift baseline 测试。

### F718 | 未使用形参 | error | M
- 证据: tests/unit/test_phase_runner_property.py:48-52 `@given(seed=st.integers(...))` + `test_now_iso_always_ends_with_utc_offset(seed: int)`——seed 从未使用（仅作重复调用器）。
- 建议方向: 保留 given 但在 docstring 说明意图，或改用 `@settings(max_examples=...)`。

### F719 | 名不副实的“集成”测试 | error | P2
- 证据: tests/unit/pipeline/test_field_filtering.py:1-17 模块 docstring “Integration tests for Layer B field-level filtering **through dispatch_helper** … assert that the dispatch_helper read loop correctly delegates”——但 import 全部来自 `shenbi.contracts.fields`，从不触 dispatch_helper；dispatch 循环接线点 src/shenbi/pipeline/dispatch_helper.py:605 无本文件覆盖（其它文件 test_dispatch_helper.py 的 TestOptionalReads/TestMultiFileOutputFormat 覆盖 prompt 侧，不覆盖 read-filter 侧）。
- 建议方向: 补一条走 `_build_skill_prompt`（read_fields 声明 + tmp 内容）断言 read 内容被过滤的真集成测试，或改 docstring 为 contracts.fields 单测。

---

## skip/xfail 逐条处置（rubric 第 8 项，全 10 处）

| 位置 | 类型 | 处置 | 理由 |
|---|---|---|---|
| tests/unit/test_safe_write.py:103 | mark.skipif(win32) | keep | fcntl POSIX-only，平台合法差异 |
| tests/unit/test_phase_runner_property.py:59 | mark.skipif(win32) | keep | xdist Windows worker crash（spec OQ-1） |
| tests/unit/test_scoring.py:520 | pytest.skip（tiers 缺失） | keep | checkout 完整性守卫 |
| tests/unit/test_coverage_thresholds.py:33 | pytest.skip（非 --no-cov 相位） | keep | 两段式覆盖率设计（文档明确）；但见 F707 阈值漂移 |
| tests/unit/pipeline/test_truth_embed.py:122 | pytest.skip（模型已装） | keep | 降级路径仅模型缺席可测；环境条件合法 |
| tests/unit/pipeline/test_context_assemble.py:167 | pytest.skip（模型已装） | keep | 同上 |
| tests/unit/pipeline/test_bridge_tracker.py:14 | pytest.skip（模板未建） | **stale** | truth/bridge_tracker.md 已存在——守卫永不触发，属死代码（F712） |
| tests/unit/pipeline/test_bridge_tracker.py:24 | pytest.skip（同上） | **stale** | 同上 |
| tests/unit/gates/g4/test_state_settling.py:167 | pytest.skip（模板未建） | **stale** | truth/character_matrix.md 已存在（F712） |
| tests/unit/pipeline/test_audit_layer.py:308 | pytest.skip（fixture 缺失） | keep | fixture（tests/fixtures/genre-config-example.json）实际存在，守卫作为真实文件依赖的兜底合理 |

无 masking 判定：未发现 skip 掩盖真实失败的案例（两个 stale 守卫因文件存在而等效于无 skip）。

---

## per-file / per-directory 报告

### tests/ARCHIVE-MIGRATED.md
- 处置: deep-read
- 声称检查的不变量: 迁移映射表完整性（skill-behavior/triggering/pressure → tiers/t1-skill 路径）
- findings: 无（映射目标目录抽查存在；文档性质，与 AGENTS.md 的 T1 结构一致）
- 验证命令: `ls tests/ | grep -E "skill-behavior|skill-triggering|pressure-tests"` → 三目录均在
- 置信度: high

### tests/__init__.py / tests/unit/.gitkeep / tests/unit/__init__.py 及全部子目录 __init__.py（15 个）
- 处置: deep-read（全部为空或单行 docstring）
- 声称检查的不变量: 包结构
- findings: 无
- 验证命令: `head -5 tests/unit/*/__init__.py`（见审查记录）
- 置信度: high

### tests/conftest.py
- 处置: deep-read
- 声称检查的不变量: structlog 全局配置每测试快照恢复（防跨测试 closed-file 崩溃）；tmp_project_dir / sample_worldbuilding_output fixture
- findings: 无
- 验证命令: 文件读取
- 置信度: high

### tests/lock-tool-hashes.sh / tests/regenerate-baselines.sh / tests/round-exec.sh / tests/test-gates.sh
- 处置: deep-read
- 声称检查的不变量: 工具哈希锁定；基线再生（G0/G2/G4/G6/G7）；round 脚手架与 --validate；gate CLI 集成 shell 测试（bash 3.2 兼容）
- findings: 无新（regenerate-baselines.sh:48 引用 round-001-2026-06-11 与 test-gates.sh 同——路径存在性未逐一验证，标注 未验证；round-exec.sh 的 validate 模式 diff 输出仅 WARN 不计错误，设计如此）
- 验证命令: 文件读取
- 置信度: high

### tests/unit/conftest.py
- 处置: deep-read
- 声称检查的不变量: executor 模块级缓存（_truth_files_cache/_decisions_files_cache）每测试前后重置（防顺序依赖）
- findings: 无
- 验证命令: 文件读取；`grep -n "_truth_files_cache" src/shenbi/dispatcher/executor.py` 确认属性存在
- 置信度: high

### tests/unit/test_safe_write.py
- 处置: deep-read
- 声称检查的不变量: 原子写持久化/无残留 tmp/接受 bytes/trace 追加/无 lockfile 泄漏/flock 失败回退清理
- findings: [F701]；另 safe_write.py 71-91（锁竞争重试+stale takeover）零覆盖（计入 F717）
- 验证命令: `grep -n "_acquire_lock" tests/unit/test_safe_write.py` → 无；coverage log safe_write.py 66%
- 置信度: high

### tests/unit/test_phase_runner_property.py
- 处置: deep-read
- 声称检查的不变量: load_state 默认态、save/load round-trip、now_iso 单调性、任意 steps 保序
- findings: [F718]；skipif 处置 keep
- 验证命令: `grep -n "def load_state\|def save_state\|def now_iso" src/shenbi/phase_runner.py` → 签名一致
- 置信度: high

### tests/unit/test_exceptions.py / test_recovery.py / test_error_guidance.py / test_status.py
- 处置: deep-read
- 声称检查的不变量: 异常层级/序列化/目录键与真实类一致；恢复策略映射；guidance 目录完备；状态枚举 wire 值
- findings: 无（目录一致性测试设计良好，防字符串键漂移）
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_logging.py
- 处置: deep-read
- 声称检查的不变量: JSON/console 渲染器、stderr 路由、幂等配置；3 个 CLI 子进程测试验证真实 uv run 行为
- findings: [F714]（docstring 笔误）；资源维度注：3 个子进程测试每次 spawn `uv run`（秒级），属可接受的真实验证成本
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_capability_fs.py / test_round_paths.py / test_contract.py
- 处置: deep-read
- 声称检查的不变量: CapabilityFS 只读沙箱（读允许/写拒绝/越界拒绝）；RoundPaths 三根解析与 .bak 同根；load_contract 单一加载器 + 真实 registry 的 decisions 路径解析
- findings: 无（test_contract 用 tmp registry 隔离 + 真实 registry 集成双轨，mock 纪律正确）
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_coverage_thresholds.py
- 处置: deep-read
- 声称检查的不变量: Cobertura 分支覆盖率 ≥ 阈值（两段式 --no-cov 相位）
- findings: [F707]
- 验证命令: `ls tests/coverage/coverage.xml` → 存在；`sed -n 420,445p pyproject.toml` 确认 xml 输出路径匹配
- 置信度: high

### tests/unit/test_dispatcher_executor.py
- 处置: deep-read
- 声称检查的不变量: derive_file_type/derive_input/output_files 委托契约（含真实契约端到端用例）、SECTION N 腐败哨兵、detect_mode 回退、subprocess mock
- findings: 无（mock 在使用位置 monkeypatch `shenbi.dispatcher.executor.load_contract`，纪律正确；subprocess 全局 patch 经模块共享对象生效）
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_dispatcher_modes.py
- 处置: deep-read
- 声称检查的不变量: internal/codex_api 模式硬拒绝（DispatcherError）
- findings: 无
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_gates_cli.py
- 处置: deep-read
- 声称检查的不变量: shenbi-validate CLI 全 gate 分支 + usage/unknown 路径
- findings: 无
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_generate_autocheck_docs.py / test_migrate_contract.py / test_lint_contracts.py / test_lint_no_forbid_with_computed_field.py / test_lint_no_fs_mutation.py / test_lint_repo_consistency.py / test_lint_status_strings.py
- 处置: deep-read
- 声称检查的不变量: autocheck 块注入幂等与防篡改；迁移幂等（防内容腐蚀回归）；report-consumed 完备性 lint；computed_field×forbid lint（正/负例）；FS-mutation lint（9 正例 + 8 反例 + 真实 src 树 + allowlist 诚实性）；repo 一致性 lint（含 decisions sidecar 死线正负对照）；裸状态串 lint（含 ternary 回归）
- findings: 无（工具测试普遍带正/负双对照，质量高）
- 验证命令: 文件读取；`ls tools/lint_*.py tools/migrate_contract_to_frontmatter.py tools/generate_autocheck_docs.py` 均存在
- 置信度: high

### tests/unit/test_plugins_generate.py
- 处置: deep-read
- 声称检查的不变量: load_master 校验、generate_all 平台清单写出、未知格式退出码
- findings: [F715]
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_pricing_fail_loud.py / tests/unit/cost/（4 文件）
- 处置: deep-read
- 声称检查的不变量: 未知模型 fail-loud；token 估算比率；ledger JSONL 追加/容错行；定价表完备；report CLI 退出码
- findings: [F716]（test_report.py:34 弱断言计入）
- 验证命令: 文件读取；cost/report.py coverage 70%（25-32,35 缺）与弱断言相关
- 置信度: high

### tests/unit/test_pytest_framework.py
- 处置: deep-read
- 声称检查的不变量: fixture 与 marker 基建可用
- findings: 无（自检性质，`assert True` 属于其目的本身）
- 验证命令: 文件读取
- 置信度: high

### tests/unit/test_phase_runner.py
- 处置: deep-read
- 声称检查的不变量: 状态机转换矩阵、G5 门控、marker 强制、CLI 路由、M5/M8（契约输出+派生 file_type）、run_gate 子进程契约（含 OSError→FAIL）
- findings: [F716]（:862-864 条件断言 + 注释与 src 行为不符——src phase_runner.py:214 `if output_files:` 才调 G2）
- 验证命令: `sed -n 193,240p src/shenbi/phase_runner.py`
- 置信度: high

### tests/unit/test_scoring.py
- 处置: deep-read
- 声称检查的不变量: rubric 解析、REJECT 语义、加权计算、kill switch、分类阈值、marker 强制、CLI 全模式（gate-only/--tier/interactive）
- findings: [F702], [F705]
- 验证命令: `grep -n "weight_mismatch" src/shenbi/scoring.py`；`git ls-files tests/tiers/deps.json`
- 置信度: high

### tests/unit/test_scoring_anti_collapse.py / test_scoring_property.py / test_sync_contracts.py / test_test_density.py
- 处置: deep-read
- 声称检查的不变量: 双评一致性/坍塌标记；classify/compute 全域性质；DAG/glob 归一化/双射自检；测试密度 ≥0.10
- findings: [F716]（anti_collapse:98-99 isinstance 弱断言）；[F717]（sync_contracts main 159-203 未覆盖）
- 验证命令: 文件读取；coverage log sync_contracts 56%
- 置信度: high

### tests/unit/audit/（3 文件）
- 处置: deep-read
- 声称检查的不变量: write-audit 台账 PASS/FAIL/drift 阻断；快照树（含参数化 glob 展开）；genre/track 写审计（含跨节 drift、越权写）
- findings: 无（用真实 ownership 语义，断言中文违规串精确）
- 验证命令: 文件读取
- 置信度: high

### tests/unit/config/（3 文件）
- 处置: deep-read
- 声称检查的不变量: 关键维度禁停（rationale ≥50 字符）、审计轨迹、floor 下限；生产 novel-output 配置不回归（texture 常开、floor 对齐、coherence 通过）；阈值单源
- findings: 无新（test_production_config_coherence.py:11 用相对路径 `Path("novel-output/...")` 依赖 CWD=repo root——脆弱点记 M 级观察，不入独立 finding）
- 验证命令: `ls novel-output/xinghuo-ranqiong` → 存在且 git 跟踪（1260 文件）
- 置信度: high

### tests/unit/contract/test_dict_reads.py
- 处置: deep-read
- 声称检查的不变量: dict 形 reads 抽 file+fields；requires_independent_agent 顶层标记
- findings: 无
- 验证命令: 文件读取
- 置信度: high

### tests/unit/contracts/（17 文件 + schemas/ 5 文件）
- 处置: deep-read（抽查名：test_canaries.py, test_paths.py, test_ownership.py, test_registry_pipeline_producers.py, schemas/test_deps.py, schemas/test_novel_scores_state.py——全部逐文件读完）
- 声称检查的不变量: 冻结基类型；7 哨兵索引完整性（含 sentinel-7 跨层 seam 的静态 is + 动态 schema 变异双证明）；N 替换边界；字段过滤（含全角折叠/零宽）；glob-aware DAG；9 键写所有权；registry producer 分型（D20 真实平文件）；truth-files.yaml 真实加载（61 concepts）；deps.json 真实形状；D26 生产者字段契约；decisions P2.5 规则；pydantic 错误→gate 微失败适配
- findings: 无（该目录为全区质量标杆：真实仓库工件 + 正负对照 + 哨兵机制）
- 验证命令: 文件读取；`ls docs/framework/truth-files.yaml tests/tiers/deps.json tests/fixtures/novel-example.json` → 均存在
- 置信度: high

### tests/unit/dispatcher/（4 文件）+ tests/unit/orchestration/test_bridges.py + tests/unit/phase_runner/test_run_gate_uses_cli_module.py
- 处置: deep-read
- 声称检查的不变量: codex 直接写 progress.json（非子进程）；写审计 pass/block；codex-api 不可达行为证明；read-provenance 诚实分层（源码锚定）；escalation/scoring bridge；run_gate 指向 shenbi.gates.cli（防 deleted-path 回归，含 FileNotFoundError→FAIL）
- findings: 无
- 验证命令: 文件读取
- 置信度: high

### tests/unit/gates/ 非 g4（29 文件）
- 处置: deep-read（抽查名：test_g0.py, test_g2.py, test_g3.py, test_g5.py, test_g6.py, test_g7.py, test_shared.py, test_g_reconcile.py——全部逐文件读完）
- 声称检查的不变量: G0.1–G0.15 各子检查（含 G0.14 校准哈希锁的正/反/恢复三态）；G1 备份派生与锁过期；G2.1–G2.12 + decisions 分支（.md 跳过回归）；G3.0–G3.5 + D19 死函数哨兵（运行时+AST 双证明）；G4 decisions/composite/文件分区；G5.1–G5.4 + 未知相/损坏 deps FAIL；G6.1–G6.12 + D16 哨兵；G7.1/7.13–7.16 + 纯性（无写副作用）；G_DISPATCH/RECONCILE/TRANSITION 错误路径；shared 工具全集
- findings: [F708], [F710], [F713], [F716]（test_g2.py:40, test_g5.py:225, test_g0.py:215 弱断言）；G3 覆盖 77%（106-125,138-143 缺）与 G2 覆盖 87%（116-157 段缺）为测试未达点（计入观察，不另立 finding）
- 验证命令: `grep -n "num_pat\|group(2)" src/shenbi/gates/g5.py`；`sed -n 44,64p src/shenbi/gates/g6_checks.py`
- 置信度: high

### tests/unit/gates/conftest.py + tests/unit/gates/g4/（31 文件）
- 处置: deep-read（抽查名：test_all_skills_parametrized.py, test_chapter_drafting.py, test_character_design.py, test_generic.py, test_worldbuilding.py, test_decisions_validator.py——全部逐文件读完）
- 声称检查的不变量: 20 技能 × 12 契约断言（时间戳/gate/闭合状态集/幂等）；各 checker 业务规则（overlap/视觉场景/hook/黄金三章/角色档案 15 字段/archetype 3+阈值/P1-P7 分层/势力 2+/伏笔 24 op 上限/SMOKESCREEN 出口/genre 9 键/地点完整性/rhythm 30 节/thread A-B-C/矩阵保护）；composite 分区（.json 永不进结构 checker，spy 证明）；chapter_role 全角冒号与模板令牌回归；worldbuilding 中文序数规则计数锁定
- findings: [F706], [F711], [F712]（state_settling:167 stale skip）, [F717]（memory_distill 无测试、score_* 分支缺）
- 验证命令: `grep -rn "sample_skill_output" tests/unit/gates/`；`grep -n "HARD_FAIL" src/shenbi/gates/g4/chapter_revision.py`；`ls truth/character_matrix.md`
- 置信度: high

### tests/unit/pipeline/（conftest + 56 文件）
- 处置: deep-read（抽查名：test_chapter_loop.py, test_cli.py, test_dispatch_helper.py, test_genesis.py, test_truth_io.py, test_chapter_loop_full.py——全部逐文件读完）
- 声称检查的不变量: 16 步表结构与顺序；staging 两段提交（G4 验证 staging 副本/checkpoint 提升/审批落盘）；上下文组装 Route A/B/C + 预算 + 降级；审计三圈激活矩阵（真实 genre-config fixture）；并发 8 线程 upsert 无丢行（barrier 竞态窗口）；retry 预算持久化与 RetryExhaustedError；快照保留边界（E40：50/52/56 章三态）；truth-index 双源 hook 与中文序数规则；触发日历（12/36/卷界/书末）与 I14 写序；genesis 17 步全流程 + G3 独立性 + Route B 错误隔离；CLI init/status/review/next/resume/chapters 全命令 + 波次间回归（book-closure 恢复跑 step 10）
- findings: [F703], [F704], [F712]（bridge_tracker stale skip）, [F716]（parallel_dispatch:82, context_curation:30）, [F719]
- 资源维度注: test_logging 型子进程调用无；conftest sample_seed_content 为合成种子而非 tests/fixtures 产物——但它是 CLI init 的输入而非“技能输出 fixture”，不构成 G0.9 手写 mock 冒充产物；真实产物侧由 test_seed_parser.py:83-108 使用 tests/fixtures/outline-example.md 覆盖（合规）
- 验证命令: `grep -n "filter_to_fields" src/shenbi/pipeline/dispatch_helper.py`；`uv run pytest --collect-only -q tests/unit/pipeline/test_review_checklist.py`（并入 96 collected）
- 置信度: high

### tests/unit/records/（3 文件）
- 处置: deep-read
- 声称检查的不变量: 真实 fixture（truth-pending_hooks.md / pending-hooks-init.md）三记录解析；golden 基线（pending_hooks.parse.json）防解析器漂移；跨节 drift 正/负例（含浮点格式假阳性回归 0.8 vs "0.80"）；16 键并集；parse∘serialize 幂等
- findings: 无（fixture 真实性合规：全部 tests/fixtures/ 真实产物）
- 验证命令: `ls tests/fixtures/truth-pending_hooks.md tests/baselines/pending_hooks.parse.json` → 存在
- 置信度: high

### tests/unit/skill_utils/（13 文件 + drift_detection/test_linguistic_drift.py）
- 处置: deep-read（抽查名：test_compute_stats.py, test_drift_detection.py, test_drift_triggers_integration.py, test_routing.py, test_trope_detection.py——全部逐文件读完）
- 声称检查的不变量: 置信度校准只降不升 + 校准→分流组合不变量（AUTO_REVISE→HUMAN_REVIEW 翻转证明）；熵/转移矩阵/连续 run 语义与边界（阈值排他性逐档验证）；语言漂移指标（系统词密度/开口相似度/窗口冗余，中文长文本）；drift 触发全链（fixture→parse→detect→audit 写出，含 human_overridden 排除）；升级信号 6 触发器；伏笔回召 overdue 语义；三路径分流全部边界（floor 等值/±5 边/cap=2）；套路检测用真实 genre-config-example.json tropeInventory（阈值严格大于语义）；卷级宏观触发（平台后不触发等）
- findings: 无独立 finding；[F717] 计入 drift baseline.py 19% 未覆盖
- 验证命令: `ls tests/fixtures/genre-config-example.json` → 存在且含 tropeInventory 键
- 置信度: high

### tests/unit/text/test_cjk.py
- 处置: deep-read
- 声称检查的不变量: CJK 子串匹配语义（无词边界）、破折号/省略号单计、cjk_only/mixed 计数、领域词典防拆分、jieba 0.42.1 冻结基线（防升级漂移）
- findings: 无
- 验证命令: 文件读取
- 置信度: high

### tests/unit/tools/（2 文件）
- 处置: deep-read
- 声称检查的不变量: 描述审计工具正/负例退出码；closure lint 真实仓库 0 孤儿读 + canary#1 注入孤儿（monkeypatch 在 sync_contracts 模块属性=使用位置，纪律正确）
- findings: 无
- 验证命令: `ls tools/audit-skill-descriptions.py tools/lint_contract_graph.py`
- 置信度: high

### tests/unit/trace/（7 文件）
- 处置: deep-read
- 声称检查的不变量: 事件冻结/签名确定性/链式 prev/规范载荷序无关；writer seq 接续；replay 撕裂尾截断+坏签名丢弃；compaction 快照替换+间隙检测（N1 fresh-writer 回归）；materialize 三相队列（I1）与空相三 pending（I2）；迁移幂等；版本单调
- findings: 无
- 验证命令: 文件读取
- 置信度: high

---

## 覆盖统计与汇总

- 清单 236 文件全部深读，报告条目覆盖 236/236（含目录聚合条目内逐文件列出）。
- findings：P1×4（F701–F704，全部为“测试不测真代码/恒真断言”类），P2×10（F705–F713, F717, F719），M×5（F714–F716, F718 + 弱断言并入 F716）。
- skip/xfail：10 处全部处置（keep 8 / stale 2 / masking 0 / enable 0）。
- 低置信度文件：无（所有 finding 均有 file:line 证据 + 实际运行的验证命令；唯一标注“未验证”的是 regenerate-baselines.sh 中 round-001 路径的运行期存在性，非 finding）。
- 未覆盖文件列表：空。
