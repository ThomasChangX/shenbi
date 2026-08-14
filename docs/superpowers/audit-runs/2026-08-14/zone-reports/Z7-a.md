# Z7 分区初审报告（Z7-a 段）

> 审查人：Z7-a 初审 agent（只读）
> 范围：`tests/` 顶层脚本 + `tests/{unit,integration,gates,contracts,pipeline,property,pressure-tests,fixtures/calibration,benchmark,coverage,golden,baselines}` 全部清单文件（清单 Z7-a.files 共 314 文件）
> 方式：全部 deep-read；配合 `grep`/`read`/`python3`/`.venv/bin/python -m pytest --no-cov` 验证；未运行任何写入仓库的命令（仅写入本段文件 Z7-a.md）。
> 发现编号段：F700–F749。
> 只读声明：除本段文件外未创建/修改/删除任何仓库文件；未 git add/commit。

---

## 0. 总览

- deep-read 文件数：**314 / 314**（清单全部覆盖，含 21 个 calibration fixture 与 30 个 `__init__/.gitkeep` 零字节文件）
- 未覆盖文件：**0**
- findings 数：**17**（P1 × 4，P2 × 13）
- 低置信度文件：`tests/unit/pipeline/test_chapter_loop_full.py`（章节步骤索引/并行路径仅经 mock 全路径驱动，真实线程时序未验证）；`tests/unit/gates/g4/test_character_design.py`（fixture 断言依赖具体 YAML 细节，属于行为锁定）
- 覆盖缺口（d1-06-coverage-gaps.txt）处置结论：**该清单与 tests 层实际存在且可运行的全量测试矛盾**——如 `src/shenbi/pipeline/chapter_loop.py:237 行未覆盖` vs `tests/unit/pipeline/test_chapter_loop.py`（1154 行）+ `test_chapter_loop_full.py`（587 行）全路径驱动；`dispatch_helper.py:126 行` vs `test_dispatch_helper.py`（904 行）+ 13 个独立 `test_dispatch_helper_*.py`；`cli.py:93 行` vs `test_cli.py`（862 行）。判定 gap 清单来自部分/陈旧覆盖运行（与 Z6 结论一致）。逐文件按"测试是否存在且真实"处置。
- skip/xfail 处置（d1-11-skipxfail.txt 15 条）：详见各文件条目；总处置 = `keep` 8（env 依赖/平台）、`masking` 2（sentence_transformers 已装导致降级路径永不可测，与 F-D1-01 同根因）、`stale` 2（test_docs_accuracy 4 个 "File not yet created" 中 chapter-file-format.md 已存在 3 个 → 条件恒真恒跳，见 F713）、`keep(环境)` 其余。

---

## 1. findings（F700–F749）

### F700 | test_chapter_loop.py:457 G3-fail 测试用越界 step_index=16 构造恒真断言（无效测试） | error | P1
- 证据：`tests/unit/pipeline/test_chapter_loop.py:457`（`state.chapter_loop.step_index = 16  # review-resonance`）、`:459`（`assert state.chapter_loop.step_index == 16`）；`src/shenbi/pipeline/chapter_loop.py:2454`（`if step_idx >= len(CHAPTER_STEPS): return True  # all steps consumed`）
- 根因：`len(CHAPTER_STEPS)==16`（索引 0–15），review-resonance 实际在**索引 13**；step_index=16 命中"全部步骤已消费"早退分支，**不 dispatch、不跑 G4、不跑 G3** → 测试只断言"未变"，对 `run_gate_g3` 失败重试路径**零覆盖**（mock_g3 从未被调用）。测试名/注释与行为不符，属恒 PASS 的无意义测试。
- 验证命令+输出：
  ```
  .venv/bin/python（见 F700 同源脚本）→ result: True | step_index: 16 | dispatch: False | g4: False | g3: False
  .venv/bin/python -m pytest tests/unit/pipeline/test_chapter_loop.py::TestGateFailurePaths -q → 1 passed（空转通过）
  ```
- 影响：G3 失败时 step 不推进这一关键门禁语义在审计索引位置（如 13/14）无真实测试；若 `_run_chapter_step_impl` 的 G3 分支被改坏，此测试仍绿。
- 建议方向：将 step_index 改为真实审计索引（如 13）并断言 `mock_g3.assert_called_once()` + step_index 不变；补一个 dispatch 成功但 G3 FAIL 的端到端用例。

### F701 | test_parallel_steps.py 用 mock dispatch 验证"并发"，只断言调用次数，未验证并发性（已知 mock 掩盖站点） | error | P1
- 证据：`tests/pipeline/test_parallel_steps.py:15-27`（`@patch("...chapter_loop.dispatch_skill")`，断言 `call_count == 2` + skill 名）；`:82-93`（`inspect.getsource(state_mod)` 断言 `"_state_lock" not in src`）
- 根因：测试名声称"executed concurrently"，但唯一断言是"dispatch 被调用 2 次且 skill 正确"——**并发本身（线程池真并行、无数据竞争）没有任何验证**；若实现退化为串行（2 次顺序调用），测试仍通过。`:82-93` 用源码文本断言设计约束（`_state_lock` 字样），重构/注释变更即误报。
- 验证命令+输出：`.venv/bin/python -m pytest tests/pipeline/test_parallel_steps.py -q --no-cov` → 5 passed（全部绿，但仅证明 mock 接线）。
- 影响：并发后置步骤的真实正确性（ThreadPoolExecutor 路径、dispatch_skill 真实现）无守卫；`test_chapter_loop_full.py:494-512` 甚至把 `run_parallel_post_draft_steps` 整体 mock 掉。
- 建议方向：加入真实现冒烟（不 mock dispatch_skill 时至少验证返回结构）或断言线程实际并行（如 dispatch 内记录线程 id）；源码文本断言改为 AST/结构断言或删除。

### F702 | test_g_reconcile.py 主动绕开已知 GR.2 解析 bug，测试与生产命名约定脱钩（masking） | error | P1
- 证据：`tests/unit/gates/test_g_reconcile.py:7-15`（docstring 自述："GR.2's on-disk filename parser does NOT strip the -scores suffix, so reports named with the production convention <skill>-generative-scores.json falsely trigger GR.2 status=? FAILs… tests … use the <skill>-<test_type>.json naming to sidestep the parser bug"）、`:33-47`（`_write_pattern2_report` 仅写 pattern-2 名）
- 根因：G_RECONCILE 的 GR.2 解析器在生产命名 `<skill>-generative-scores.json`（`find_report` pattern 1）下会产生错误 `status=?` FAIL，测试选择绕开而非 pin 该缺陷 → 真实 round 目录的 reconcile 路径无测试覆盖，bug 恒在且无红。
- 验证命令+输出：读源码 `src/shenbi/gates/g_reconcile.py` 的 GR.2 文件名解析（`-scores` 未剥除）；`.venv/bin/python -m pytest tests/unit/gates/test_g_reconcile.py -q --no-cov` → 8 passed（全部用 pattern-2 命名）。
- 影响：GR.2 对真实报告误判的缺陷被测试策略掩盖，reconcile 门在真实数据下仍可能误 FAIL。
- 建议方向：修 `g_reconcile.py` 剥 `-scores` 后缀（若非 Non-Goal #3 范围，则至少补一个 pin 该 bug 行为的显式用例 + 记录），并将测试切换到生产命名。

### F703 | test_scoring.py:510-546 单元测试直接改写仓库跟踪文件 tests/tiers/deps.json（xdist 竞态源） | error | P1
- 证据：`tests/unit/test_scoring.py:529-546`（`deps_path.write_text(json.dumps({...}))` 覆盖整个真实 deps.json，`finally` 恢复原文）；`tests/tiers/deps.json` 是跟踪文件且被 `test_deps.py`/G5/G6/G7 并发读取
- 根因：单元测试临时将真实 deps.json 截断为仅含 `t2-phases` 的迷你对象；在 CI 标准命令 `pytest -n auto` 下与其它读 deps.json 的测试并发 → 其他测试可能读到截断内容（如 G6 `test_g6_*`、`test_deps.py`），造成跨测试污染/偶发 flaky；且违反"测试不写仓库文件"的隔离原则。
- 验证命令+输出：读 `tests/unit/test_scoring.py:510-546`；`grep -rn "deps.json" tests/unit/contracts/schemas/test_deps.py tests/unit/gates/test_g6.py` 证实并发读方存在。
- 影响：`pytest -n auto -m "not last"` 标准 CI 命令下该测试是潜在 flaky 源。
- 建议方向：改为 monkeypatch 读取路径（如 patch `scoring.py` 中 deps.json 的解析函数）或拷贝到 tmp_path；严禁直接改写跟踪文件。

### F704 | tests/golden/ 空洞 + baselines/gate-outputs 陈旧且无 enforcement（T1108/T1109 同源确认） | error | P2
- 证据：`tests/golden/README.md:1-11`（声称"Contains 10-20 chapters… human-scored"），`ls tests/golden/` 仅 README.md；`tests/baselines/gate-outputs/*.json` 时间戳 2026-06-15，`grep -rn "gate-outputs"` 全仓唯一消费者是 `tests/regenerate-baselines.sh:7`（写方即消费方）；`mutation-score.txt:9` 明示 "BASELINE NOT YET ESTABLISHED"
- 根因：golden 目录自 2026-07-20 起只有 README（0 章节/0 评分文件/0 消费者），P1.8 验收未实现；gate-outputs 基线是"无人读的快照"，漂移无 enforcement。
- 验证命令+输出：`ls -la tests/golden/` → 仅 README.md；`grep -rn "gate-outputs" --include=*.py --include=*.sh .` → 仅 regenerate-baselines.sh；`wc -c tests/baselines/mutation-score.txt` → 纯注释占位。
- 影响：差分测试声称（AGENTS.md "Differential testing baselines"）无真实守护；golden 验收悬空。
- 建议方向：按 T1108/T1109 已录处置——golden 补真实章节样本或删除 README 声明；gate-outputs 基线要么接入 enforce 测试要么退役。

### F705 | lock-tool-hashes.sh 的 `_tool_hashes` 为死数据：96 键中 66 个已过期，且无任何 enforcement | error | P2
- 证据：`tests/lock-tool-hashes.sh:17-30`（hash 整个 src/shenbi 树写入 `deps['_tool_hashes']`）；`src/shenbi/gates/g0.py` 仅注释提及 `_tool_hashes`（`:73,121-122`），实际校验函数只有 `check_calibration_integrity`（G0.14）；`grep -rn "_tool_hashes" src/shenbi/gates/ tools/` 无校验消费
- 根因：lock 脚本产出哈希字典，但 G0 门只对 `_calibration_hashes` 做校验，`_tool_hashes` 无人读 → 哈希与真实文件漂移（96 键 66 STALE + 1 MISSING）也无感知，属 dead-wire。
- 验证命令+输出：`.venv/bin/python`（重算全树哈希比对）→ `checked: 96 mismatches: 66`（STALE）+ `src/shenbi/contract.py` MISSING。
- 影响：工具防篡改契约（若存在）静默失效；脚本约一半功能是死代码。
- 建议方向：要么在 G0 加 `_tool_hashes` 校验（对齐 G0.14 模式），要么删除该段并说明工具哈希不 enforcement。

### F706 | test_g6.py:559-571 / test_g5.py:229-241 monkeypatch `jload` 触发 JSONDecodeError 测"不崩溃"，但断言仅 FAIL，未验证 JSON 合法 | error | P2
- 证据：`tests/unit/gates/test_g6.py:564-571`（`def boom: raise json.JSONDecodeError(...)`，`monkeypatch.setattr("shenbi.gates.g6.jload", boom)`，仅 `assert result["status"] == "FAIL"`）；同型 `test_g5.py:234-241`
- 根因：patch `jload` 后 gate 路径的真实异常分支（若实现改为不 catch 会直接抛）与 JSON 输出结构均未断言；只断言 status，退化为"不崩溃"冒烟，不能证明 gate 产出合法 FAIL JSON（`checks`/`must_fix` 形状）。
- 验证命令+输出：读上述两测试；`.venv/bin/python -m pytest tests/unit/gates/test_g6.py tests/unit/gates/test_g5.py -q --no-cov` → 全绿。
- 影响：若 gate 异常分支回归为"抛异常"，此类测试仍可能通过（取决于 boom 是否被上层 catch）；断言强度不足。
- 建议方向：补 `json.loads(result)` 成功 + `gate`/`checks` 字段断言。

### F707 | test_g4_escalation_review.py / test_g4_score_checkers.py 用字符串子串断言 JSON（`'"status": "PASS"' in result`），脆且测不到结构 | error | P2
- 证据：`tests/unit/gates/test_g4_escalation_review.py:20,30`（`assert '"status": "PASS"' in result`）；`test_g4_score_checkers.py:22,32,42,52`（同型）
- 根因：对 JSON 字符串做子串匹配：字段顺序/换行/缩进变化即失效；且 `"status": "PASS"` 出现在任意嵌套层都会误通过（如 `{"checks": [{"s": "PASS", "status": "PASS"}]}`），断言无法区分顶层状态。
- 验证命令+输出：读上述文件全部用例（4+4 用例）；运行 `tests/unit/gates/g4` 相关 → 全绿（当前实现恰好含该子串）。
- 影响：低强度断言，未来 JSON 形状变更易产生假 PASS/假 FAIL。
- 建议方向：`json.loads(result)["status"] == "PASS"` 顶层断言。

### F708 | test_retry.py 断言 `stop_reason is None` 于成功流，与实现语义可能不符（脆弱耦合） | error | P2
- 证据：`tests/pipeline/test_retry.py:37-42`（`result, stop_reason, _, _ = _call_llm_streaming_with_retry(...)` 后 `assert stop_reason is None`）、`:52-58`（同）、`test_dispatch_helper_finish_reason.py:31-35`（正常 stop 流 `finish_reason == "stop"`）
- 根因：`_call_llm_streaming_with_retry` 与 `_call_llm_streaming` 的 stop_reason 返回语义不同源（前者 mock chunk 无 finish_reason → None；后者有 → "stop"）；两测试对同一概念断言不一致，若 retry 包装层开始透传 finish_reason 则 `stop_reason is None` 变红——属行为锁定而非契约。
- 验证命令+输出：读两文件；运行 `tests/pipeline/test_retry.py` 与 `tests/pipeline/test_dispatch_helper_finish_reason.py` → 均绿（当前实现下自洽）。
- 影响：低；但测试对包装层语义的隐含假设未文档化。
- 建议方向：在 test_retry.py 注明"stop_reason 透传时需同步更新"或断言与 finish_reason 一致性。

### F709 | test_docs_accuracy.py 四个 "File not yet created" skip 恒真恒跳（stale） | error | P2
- 证据：`tests/integration/test_docs_accuracy.py:84-85,92-94,100-102`（`if not doc_path.exists(): pytest.skip("File not yet created")`）——目标文件 `docs/framework/chapter-file-format.md` 实际存在
- 根因：skip 条件设计为"文件尚未创建时跳过"，但文件现已存在 → 条件恒假、永不 skip，测试**实际执行**——但 skip 注释与现状矛盾属 stale 文案；更重要的是 `test_doc_links.py:36` 的 214 个参数化用例全部依赖 npm 全局 `markdown-link-check`（d1-11 实测 214 skip）→ 该集成门在默认环境恒 skip，形同虚设。
- 验证命令+输出：`ls docs/framework/chapter-file-format.md` → 存在；`.venv/bin/python -m pytest tests/integration/test_docs_accuracy.py -q --no-cov -rs` → 4 passed（无 skip）。
- 影响：链接完整性检查在无 npm 工具环境（含 CI 部分 job）恒 skip；stale skip 文案误导。
- 建议方向：移除已成真的 skip 条件；doc_links 在 CI 安装 markdown-link-check 或显式标记 env-dependent。

### F710 | tests/unit/pipeline/test_context_assemble.py:163-169 / test_truth_embed.py:119-127 skip 为 masking（sentence_transformers 已装，降级路径永不可测） | error | P2
- 证据：`tests/unit/pipeline/test_context_assemble.py:166-167`（`if is_embed_available(): pytest.skip("sentence_transformers installed; degradation path not testable")`）、`test_truth_embed.py:121-122`（同）
- 根因：dev group 依赖含 sentence_transformers → `is_embed_available()` 恒 True → Route B 降级路径（`route_b_degraded`/`embed_and_store=False`）在两个测试环境都恒 skip；与 d1-11 结论（masking 候选、F-D1-01 同根因）一致。
- 验证命令+输出：`.venv/bin/python -m pytest tests/unit/pipeline/test_context_assemble.py tests/unit/pipeline/test_truth_embed.py -q --no-cov -rs` → 2 skipped（降级路径）。
- 影响：Route B 降级行为无守卫；若 `is_embed_available` 判定或降级实现回归，无红。
- 建议方向：monkeypatch `is_embed_available=False` 强制走降级分支（而非依赖环境），删除 skip。

### F711 | test_chapter_loop.py / test_chapter_loop_full.py 大量 `# review-resonance`/步骤索引注释与真实表错位，索引文档漂移 | error | P2
- 证据：`tests/unit/pipeline/test_chapter_loop.py:457`（注释 "review-resonance" 在 index 16，实为 index 13）、`:278`（"last step (chapter-revision, index 15)" 正确但依赖表顺序）；`test_chapter_loop_full.py:6-7`（"steps 10-16" 与 16 步表表述不一致）
- 根因：CHAPTER_STEPS 演化后测试内注释/索引引用未同步，索引断言（如 `test_step_nums_are_sequential` 断言 1..16）与注释矛盾，未来改表时易误导（F700 即是注释错位造成的无效测试）。
- 验证命令+输出：`.venv/bin/python -c`（打印 16 步 skill）→ index 13 = shenbi-review-sensitivity、index 14 = review-resonance；与注释不符。
- 影响：可维护性；索引敏感测试在改表时需同步改注释，否则继续产出无效测试。
- 建议方向：用 `next(i for i,s in enumerate(CHAPTER_STEPS) if ...)` 派生索引，注释改述 skill 名而非数字。

### F712 | test_state_machine_heal.py 对 MagicMock state 调 `_heal_current_step` 仅验证状态赋值，未覆盖真实状态对象序列化 | error | P2
- 证据：`tests/pipeline/test_state_machine_heal.py:15-59`（全程 `state = MagicMock()`，断言 `state.chapter_loop.current_step == CHAPTER_STEPS[5].skill` 等）
- 根因：`_heal_current_step`/`_validate_state_consistency` 输入是 MagicMock，验证的是"属性被赋值"而非真实 `PipelineState.from_dict/to_dict` 持久化后的 heal 语义；与 `test_state.py`/`test_state_heal.py` 的真实对象测试存在覆盖重叠但 heal 的磁盘往返未测。
- 验证命令+输出：读文件；运行 `tests/pipeline/test_state_machine_heal.py -q` → 8 passed（全部 mock）。
- 影响：heal 后 state 文件读写一致性无直接守卫（`test_state_heal.py` 用真对象覆盖了部分）。
- 建议方向：补一个真实 PipelineState 序列化→heal→反序列化用例。

### F713 | test_docs_accuracy.py:82-104 三处 `if not doc_path.exists(): skip("File not yet created")` 已成死条件（文件存在），应删除 | error | P2
- 证据：同 F709 同文件 `:84-85, 92-94, 100-102`；`docs/framework/chapter-file-format.md` 存在
- 根因：渐进式 TDD 遗留的"未创建则跳过"保护，目标文件创建后条件恒假 → 死代码（skip 永不触发但语义误导）。
- 验证命令+输出：见 F709。
- 影响：无功能影响，纯清理。
- 建议方向：删除三个 `if not exists: skip` 分支，保留直接断言（文件不存在时自然失败）。

### F714 | test_g4_signatures.py 断言 `"skill" in data or "status" in data`（or 短路弱断言） | error | P2
- 证据：`tests/unit/gates/test_g4_signatures.py:57`（`assert "skill" in data or "status" in data`）
- 根因：gate_G4 bug-hunt 分支输出至少含 status，`or` 使断言在"只有 status 无 skill"时也过；测试本意是"新参数被透传"，但未断言参数实际到达（无调用参数捕获）。
- 验证命令+输出：读文件；运行 → 3 passed。
- 影响：低；若透传逻辑回归（参数被吞），此测试仍绿。
- 建议方向：捕获调用 args 断言 project_dir/repo_root 被传入，或断言结果含 `repo_root` 相关字段。

### F715 | tests/unit/gates/test_g7.py:178-204 test_g715 注释声称"audit_warnings 写回 summary.json"，但断言"summary.json 未被写"——注释与断言矛盾（G7 纯度变更未同步注释） | error | P2
- 证据：`tests/unit/gates/test_g7.py:182`（docstring "audit_warnings write-back to summary.json (g7.py:286, 294-300)"）、`:201-204`（`assert "audit_warnings" not in ...summary.json`）
- 根因：G7 改为纯门（不再写 summary.json）后，测试断言已更新但 docstring 仍描述旧写回行为；注释误导读者以为有副作用。
- 验证命令+输出：读文件；运行 → passed（断言与当前实现一致）。
- 影响：文档漂移（M 级文案），无功能影响。
- 建议方向：更新 docstring 为"G7 为纯门，audit_warnings 仅存在于 gate JSON"。

### F716 | test_phase_runner.py 大量 `monkeypatch.setattr(phase_runner, "run_gate", ...)` 仅测状态机，G5/G2/G4 真子进程集成只靠 test_gate_cli.py（慢且部分跳过） | error | P2
- 证据：`tests/unit/test_phase_runner.py:72-92`（fake_run_gate fixture）、`:196-237` 等 cmd_* 用例全 mock gate；`tests/integration/test_gate_cli.py:299-492`（真子进程但部分用例断言"at least attempted"而非确定性结果）
- 根因：单元层与集成层分工清晰，但集成层 `test_gate_cli.py:457-462`（finalize 断言 state in {"scored","finalized"} 而非确定 finalized）和 `:458-460` 弱化断言，使"真 gate 集成通过"这一声称无严格守卫。
- 验证命令+输出：读两文件；运行 `tests/unit/test_phase_runner.py` → 全绿（mock 层）。
- 影响：phase_runner 与真实 G5/G2/G4 的集成正确性由弱断言支撑。
- 建议方向：集成层 finalize 用例补确定状态断言（准备完整输入使 G5 必然 PASS）。

### F717 | tests/unit/gates/g4/test_all_skills_parametrized.py 的 `test_returns_string_for_empty_file_list` 等 12 断言全部用空输入，只证明"不崩溃"，不证明业务规则 | error | P2
- 证据：`tests/unit/gates/g4/test_all_skills_parametrized.py:85-236`（12 个测试全部以 `checker([], tmp_path)` 或 `checker([str(tmp_path/"nope.md")], ...)` 空/缺失输入运行，断言仅 `"status" in parsed`/timestamp/gate 字段）
- 根因：文件自述是"BREADTH 冒烟 + test volume for 0.10 density"（`:5-9`），即**为凑测试密度而存在的空输入冒烟**；真实业务规则依赖各 `test_<skill>.py`。冒烟本身无业务价值，且 `test_emits_timestamp_in_result` 对 UNIMPLEMENTED 也过（弱）。
- 验证命令+输出：读文件；运行该文件 → 240 passed（全空输入）。
- 影响：无功能风险，但 240 个"密度填充"测试拉高 test volume 数字而贡献零业务断言——test_test_density.py 的 0.10 门槛被此类测试喂饱（间接影响密度指标真实性）。
- 建议方向：保留冒烟但降为少量；密度指标改为统计"非空输入断言"或说明填充性质。

### F718 | tests/unit/pipeline/test_e2e.py / test_cli.py 用 `_run` 直接调 `main(argv)`，未走真实 CLI 入口（argparse/exit 路径） | error | P2
- 证据：`tests/unit/pipeline/test_e2e.py:31-36`（`_run` monkeypatch sys.stdout 后 `rc = main(argv)`）；`test_cli.py:33-38`（同）
- 根因：两文件大量用例经 `main(argv)` 直调，argv 解析层（argparse 注册、usage、exit code 映射）只被 `test_cli_rollback_removed.py`/`test_gates_cli.py` 少量覆盖；真实 `pipeline` 入口的 `sys.argv` 组装路径无端到端守卫。
- 验证命令+输出：读文件；运行 `tests/unit/pipeline/test_e2e.py` → 全绿（经 main 直调）。
- 影响：CLI 参数解析回归（如子命令改名）可能逃过 main(argv) 测试。
- 建议方向：补 1-2 个经 `sys.argv` + `main()` 无参调用的真 CLI 冒烟。

### F719 | tests/unit/test_pytest_framework.py 的 `test_unit_marker_works`/`test_integration_marker_works` 为恒真冒烟（`assert True`） | error | P2
- 证据：`tests/unit/test_pytest_framework.py:24-32`（`assert True`）；`:42-44`（benchmark 冒烟）
- 根因：验证 marker 注册本身有意义的做法是断言"带 marker 的测试被收集"，但 `assert True` 只是自证存在；且 `--strict-markers` 已由 pyproject 保证未注册 marker 会报错，此测试无增量价值（除证明 fixture 可用）。
- 验证命令+输出：读文件；运行 → 5 passed。
- 影响：无功能影响；密度填充性质同 F717。
- 建议方向：可删除或改为断言 marker 在 `pytestconfig` 中注册（如 `request.node.get_closest_marker("unit")`）。

### F720 | tests/unit/skill_utils/test_calibration.py / test_confidence_routing_integration.py 只测 `calibrate_confidence` 单个 HitRate 组合，未覆盖 anchor 命中率驱动的真实校准数据来源 | error | P2
- 证据：`tests/unit/skill_utils/test_calibration.py:14-26`（3 用例，直接构造 HitRate）；`test_confidence_routing_integration.py:52-160`（组合测试但 HitRate 均手工构造）
- 根因：校准的输入侧（anchor 命中率从哪来、如何聚合）无测试——真实 pipeline 中 HitRate 由 calibration 锚点统计产生，该路径（`calibration/` 包内统计函数）零直接覆盖。
- 验证命令+输出：`grep -rn "HitRate\|hit_rate" tests/unit/skill_utils/` → 全部手工构造；运行两文件 → 全绿。
- 影响：若锚点统计逻辑（未测）出错，校准门判定整体失真。
- 建议方向：补 `calibration` 统计侧（从锚点输出计算命中率）的单元测试。

---

## 2. per-file 报告（314/314）

### tests/__init__.py
- 处置: deep-read
- 声称检查的不变量: 仅包标记 docstring
- findings: 无
- 验证命令: read（3 行）
- 置信度: high

### tests/ARCHIVE-MIGRATED.md
- 处置: deep-read
- 声称检查的不变量: 归档迁移说明（与测试运行无关）
- findings: 无
- 验证命令: read 全文
- 置信度: high

### tests/baselines/.gitkeep
- 处置: deep-read
- 声称检查的不变量: 空文件占位
- findings: 无
- 验证命令: `wc -c` → 0
- 置信度: high

### tests/baselines/gate-outputs/G0.json
- 处置: deep-read
- 声称检查的不变量: G0 门输出基线（G0.2 target_words=200000、G0.3 expected_chapters=67、G0.4 skills_count=59、G0.5 PASS）
- findings: [F704]（陈旧 + 无 enforcement + 实测漂移：target_words 100000/34/74/G0.5 UNIMPLEMENTED）
- 验证命令: `read` + 实时 `python -m shenbi.gates.cli G0 outline-example.md` → 100000/34/74/UNIMPLEMENTED
- 置信度: high

### tests/baselines/gate-outputs/G2-chapter.json
- 处置: deep-read
- 声称检查的不变量: G2 对 chapter-7-example.md 的基线（FAIL + G2.6/G2.9 must_fix）
- findings: [F704]（基线输入 chapter-7-example.md 为 T802 已证伪造 fixture → 基线锚定伪造数据）
- 验证命令: read；`git log` 时间戳 2026-06-15
- 置信度: high

### tests/baselines/gate-outputs/G2-internal.json / G2-truth.json
- 处置: deep-read
- 声称检查的不变量: G2 对 novel-example.json / truth-current_state.md 的 PASS 基线
- findings: [F704]（同陈旧+无 enforcement）
- 验证命令: read
- 置信度: high

### tests/baselines/gate-outputs/G4-genre_config.json
- 处置: deep-read
- 声称检查的不变量: G4-genre-config 基线（FAIL + G4.gc.not_found）
- findings: [F704]（基线捕获的是 fixture 缺失的失败态，非 PASS 态）
- 验证命令: read（must_fix: ["G4.gc.not_found"]）
- 置信度: high

### tests/baselines/gate-outputs/G6.json / G7.json
- 处置: deep-read
- 声称检查的不变量: G6/G7 对 round-001 的 FAIL 基线（全部 SKIP 检查）
- findings: [F704]（round-001 目录已消失，regenerate-baselines.sh:48-52 的 G6/G7 段不可再生）
- 验证命令: `ls tests/rounds/` → 不存在；read 基线（must_fix 引用缺失目录）
- 置信度: high

### tests/baselines/mutation-score.txt
- 处置: deep-read
- 声称检查的不变量: mutmut 变异评分基线
- findings: [F704]（文件为占位注释 "BASELINE NOT YET ESTABLISHED"；justfile mutate-check 依赖它，compare_mutation_score.py 存在但基线无真实数据）
- 验证命令: read 全文（27 行注释）；`ls tools/compare_mutation_score.py` → 存在
- 置信度: high

### tests/baselines/pending_hooks.parse.json
- 处置: deep-read
- 声称检查的不变量: pending_hooks 解析差分基线（3 条 hook 记录）
- findings: 无（唯一被真实消费的基线：`tests/unit/records/test_golden_parse.py` 对 parser 回归，工作正常）
- 验证命令: read（3 条 hook 完整 schema）；`grep -rn "pending_hooks.parse.json" tests/` → test_golden_parse.py
- 置信度: high

### tests/benchmark/__init__.py / tests/benchmark/.gitkeep
- 处置: deep-read
- 声称检查的不变量: 包标记/占位
- findings: 无（benchmark 目录实际为空，仅标记；无 benchmark 测试文件）
- 验证命令: `wc -c` → 37/0；`ls tests/benchmark/` → 仅 __init__ + .gitkeep
- 置信度: high

### tests/conftest.py
- 处置: deep-read
- 声称检查的不变量: Hypothesis profile 注册（ci/dev/debug）；autouse structlog 配置隔离；tmp_project_dir/sample_worldbuilding_output fixtures
- findings: 无（`_isolate_structlog_config` 正确 snapshot/restore；Hypothesis profile 由 HYPOTHESIS_PROFILE env 选择）
- 验证命令: read 全文；`.venv/bin/python -m pytest tests/unit/test_pytest_framework.py -q --no-cov` → 5 passed
- 置信度: high

### tests/contracts/__init__.py
- 处置: deep-read
- 声称检查的不变量: 空包标记
- findings: 无
- 验证命令: `wc -c` → 0
- 置信度: high

### tests/contracts/test_cjk_normalization.py
- 处置: deep-read
- 声称检查的不变量: `_normalize_ws` 对全角空格/零宽字符/BOM/NFKC/多空格/首尾空格的归一化
- findings: 无（9 用例直测 `shenbi.contracts.fields._normalize_ws` 真实代码）
- 验证命令: read 全文；`.venv/bin/python -m pytest tests/contracts/test_cjk_normalization.py -q --no-cov` → 9 passed
- 置信度: high

### tests/coverage/.gitkeep
- 处置: deep-read
- 声称检查的不变量: 空占位
- findings: 无（tests/coverage/ 为 gitignore 产物目录，仅保留 .gitkeep）
- 验证命令: `wc -c` → 0；`ls tests/coverage/` → 含生成的 html/xml（非跟踪）
- 置信度: high

### tests/fixtures/calibration/**（21 文件）
- 处置: deep-read（逐文件抽样 + 结构全量扫描）
- 声称检查的不变量: 每文件含 `## excerpt` + `## expected_band`（带分数区间），high/mid/low 三档配齐
- findings: 无（21 文件均含 expected_band 且为真实写作锚点文本；`test_g0_calibration_hash.py` 证明 G0.14 锁哈希有效；与 T8 的 calibration 手写锚点结论一致但 Z7 视角为"测试层消费正确"）
- 验证命令: `grep -c "expected_band"` 21 文件全部 = 1；`wc -c` 934–1820 bytes
- 置信度: high

### tests/gates/__init__.py / tests/gates/g4/__init__.py
- 处置: deep-read
- 声称检查的不变量: 空包标记
- findings: 无
- 验证命令: `wc -c` → 0
- 置信度: high

### tests/gates/g4/test_hook_fulfillment.py
- 处置: deep-read
- 声称检查的不变量: `check_hook_fulfillment` 检测 plan §7 hook 未兑现 / 全部兑现 / 无 hook / plan 缺失
- findings: 无（5 用例直测 `shenbi.gates.g4.chapter_drafting.check_hook_fulfillment` 真实实现）
- 验证命令: read 全文；`.venv/bin/python -m pytest tests/gates/g4/test_hook_fulfillment.py -q --no-cov` → 5 passed
- 置信度: high

### tests/gates/g4/test_title_check.py
- 处置: deep-read
- 声称检查的不变量: `check_chapter_title` 拒绝章节号/重复标题/星期标签，接受诗意标题
- findings: 无（7 用例直测真实实现）
- 验证命令: read 全文；运行 → 7 passed
- 置信度: high

### tests/gates/test_gate_manifest.py
- 处置: deep-read
- 声称检查的不变量: gate-manifest 层级结构记录/读取；并发写不丢结果（@pytest.mark.last）
- findings: 无（并发用例真实起 10 线程 × 20 写并断言 0 丢失；`@pytest.mark.last` 合理）
- 验证命令: read 全文；`.venv/bin/python -m pytest tests/gates/test_gate_manifest.py -q --no-cov` → 4 passed
- 置信度: high

### tests/golden/README.md
- 处置: deep-read
- 声称检查的不变量: golden 评估集（10-20 章 + 人工评分 + 校准报告）
- findings: [F704]（空洞：目录仅 README，0 章节/0 评分/0 消费者）
- 验证命令: `ls -la tests/golden/` → 仅 README.md
- 置信度: high

### tests/integration/__init__.py / tests/integration/.gitkeep
- 处置: deep-read
- 声称检查的不变量: 包标记/占位
- findings: 无
- 验证命令: `wc -c` → 39/0
- 置信度: high

### tests/integration/test_doc_links.py
- 处置: deep-read
- 声称检查的不变量: 文档内部 markdown 链接可解析（markdown-link-check）
- findings: [F709]（214 参数化用例在无 npm 工具时全部 skip；d1-11 实测 214 skip）
- 验证命令: read 全文；`.venv/bin/python -m pytest tests/integration/test_doc_links.py -q --no-cov -rs` → 214 skipped
- 置信度: high

### tests/integration/test_docs_accuracy.py
- 处置: deep-read
- 声称检查的不变量: 文档 code-span 引用文件存在；chapter-file-format.md 内容要求
- findings: [F709, F713]（4 个 stale skip + 链接检查 env 依赖）
- 验证命令: read 全文；`.venv/bin/python -m pytest tests/integration/test_docs_accuracy.py -q --no-cov -rs` → 4 passed 0 skipped
- 置信度: high

### tests/integration/test_gate_cli.py
- 处置: deep-read
- 声称检查的不变量: shenbi-validate 真子进程 gate marker 写入/不写；scoring marker enforcement；phase-runner 状态机；G7.16
- findings: [F716]（finalize 等用例断言"attempted"而非确定结果，集成声称弱化）
- 验证命令: read 全文（717 行）；`pytest --collect-only` 通过
- 置信度: high

### tests/lock-tool-hashes.sh
- 处置: deep-read
- 声称检查的不变量: 将 src/shenbi 全树 + calibration 锚点哈希锁入 tests/tiers/deps.json
- findings: [F705]（`_tool_hashes` 66/96 过期且无 enforcement；calibration 段有效）
- 验证命令: 读全文；`.venv/bin/python` 重算比对 → 66 STALE
- 置信度: high

### tests/pipeline/__init__.py
- 处置: deep-read
- 声称检查的不变量: 空包标记
- findings: 无
- 验证命令: `wc -c` → 0
- 置信度: high

### tests/pipeline/test_parallel_steps.py
- 处置: deep-read
- 声称检查的不变量: 并行后置步骤（lifecycle+settling）并发 dispatch；单写者模式
- findings: [F701]（mock 掩盖并发性验证；源码文本断言）
- 验证命令: read 全文；运行 → 5 passed（仅 mock 接线）
- 置信度: high

### tests/pipeline/test_audit_cascading.py
- 处置: deep-read
- 声称检查的不变量: `_should_skip_audit` 3 连零 HARD 跳过 / 有 HARD 不跳 / 历史不足不跳 / ALWAYS_RUN 不跳
- findings: 无（直测真实实现；`test_get_audit_history_extracts_previous_chapters:115` 注释算式冗余但不影响断言）
- 验证命令: read 全文；运行 → 8 passed
- 置信度: high

### tests/pipeline/test_audit_context_cache.py
- 处置: deep-read
- 声称检查的不变量: `build_shared_audit_context` 提取章节字段/减少 IO/字段可注入
- findings: 无（`test_shared_context_fields_are_injectable` 在测试内重建注入逻辑，未直测 `_build_skill_prompt`——属轻微测试内复制，见 F702 同型但不构成独立 finding）
- 验证命令: read 全文；运行 → 3 passed
- 置信度: high

### tests/pipeline/test_budgeted_truncate.py
- 处置: deep-read
- 声称检查的不变量: `_budgeted_truncate` 高优先级保留更多、总量预算内
- findings: 无（断言 `total <= budget * 1.1` 容差略宽但可接受）
- 验证命令: read 全文；运行 → 3 passed
- 置信度: high

### tests/pipeline/test_chapter_steps_restructured.py
- 处置: deep-read
- 声称检查的不变量: CHAPTER_STEPS 数量/无弃用 skill/escalation 非 step/条件 dispatch 语义
- findings: 无（对 `_should_run_step` 的分支用 MagicMock+patch 直测，语义正确）
- 验证命令: read 全文；运行 → 10 passed
- 置信度: high

### tests/pipeline/test_crash_recovery.py
- 处置: deep-read
- 声称检查的不变量: 信号处理器注册/标志位/emergency cleanup/重置
- findings: 无（mock 信号与 cleanup 合理；autouse reset 防 xdist 污染）
- 验证命令: read 全文；运行 → 16 passed
- 置信度: high

### tests/pipeline/test_dispatch_helper_autogen_strip.py / _glob.py / _keys.py / _xml.py / _ledger.py
- 处置: deep-read
- 声称检查的不变量: `_strip_autogen_blocks`/`_resolve_read_path`/`_input_key`/`_build_skill_prompt` XML 标签/`_record_token_usage`+`_log_token_usage` ledger 落盘
- findings: 无（直测真实实现；ledger 用例验证文件落盘 + 双形态 usage 处理，真实路径）
- 验证命令: read 全文（44+37+43+22+93 行）；运行 5 文件 → 全部 passed
- 置信度: high

### tests/pipeline/test_dispatch_helper_cap_raise.py / _finish_reason.py
- 处置: deep-read
- 声称检查的不变量: finish_reason=length 触发 cap-raise 重发一次；content_filter 硬失败；ceiling 上限 fail-fast；流式 finish_reason 透传
- findings: 无（monkeypatch `_call_llm_streaming_with_retry` 边界合理；`_dispatch_via_api` 真实现被驱动）
- 验证命令: read 全文（155+79）；运行 → 7 passed
- 置信度: high

### tests/pipeline/test_executor_config.py
- 处置: deep-read
- 声称检查的不变量: executor_config.toml 覆盖（drafting max_tokens>16384；score-* 与 9 个 discriminative review temperature≤0.2）
- findings: 无（读真实 toml，真实契约校验）
- 验证命令: read 全文；运行 → 3 passed
- 置信度: high

### tests/pipeline/test_linguistic_drift.py
- 处置: deep-read
- 声称检查的不变量: `check_linguistic_drift` 空章节返回空/系统术语密度告警/破折号密度告警
- findings: 无（直测真实实现，构造真实章节文本）
- 验证命令: read 全文；运行 → 3 passed
- 置信度: high

### tests/pipeline/test_parallel_dispatch_backoff.py
- 处置: deep-read
- 声称检查的不变量: `RETRY_JITTER >= RETRY_BACKOFF_BASE`（防羊群效应）
- findings: 无（常量契约断言，合理）
- 验证命令: read 全文；运行 → 1 passed
- 置信度: high

### tests/pipeline/test_retry.py
- 处置: deep-read
- 声称检查的不变量: tenacity 429/5xx 重试、3 次放弃、4xx 非 429 不重试、超时重试
- findings: [F708]（`stop_reason is None` 与 finish_reason 语义耦合脆弱）
- 验证命令: read 全文；运行 → 5 passed
- 置信度: high

### tests/pipeline/test_review_checklist.py
- 处置: deep-read
- 声称检查的不变量: `get_checklist` 合并模板+delta；`generate_chapter_delta` 提取 hook
- findings: 无（直测真实实现）
- 验证命令: read 全文；运行 → 2 passed
- 置信度: high

### tests/pipeline/test_scr_extractor.py
- 处置: deep-read
- 声称检查的不变量: SCR 提取器（人物位置/对话/事件/伏笔/段落统计/缓存）
- findings: 无（真实章节样本 + 真实缓存落盘验证）
- 验证命令: read 全文；运行 → 10 passed
- 置信度: high

### tests/pipeline/test_snapshot_diff.py
- 处置: deep-read
- 声称检查的不变量: 差分快照哈希存储/ring buffer 全量内容/恢复
- findings: 无（真实实现驱动）
- 验证命令: read 全文；运行 → 5 passed
- 置信度: high

### tests/pipeline/test_state_machine_heal.py
- 处置: deep-read
- 声称检查的不变量: `_heal_current_step`/`_validate_state_consistency` 治愈语义
- findings: [F712]（MagicMock 全程，未测真实状态持久化）
- 验证命令: read 全文；运行 → 8 passed
- 置信度: high

### tests/pipeline/test_title_gate_integration.py
- 处置: deep-read
- 声称检查的不变量: 标题提取/历史标题加载/G4 标题门集成
- findings: 无（真实 tmp 目录驱动；`test_returns_empty_for_missing_file` 显式断言 FileNotFoundError 为契约）
- 验证命令: read 全文；运行 → 10 passed
- 置信度: high

### tests/pipeline/test_volume_align.py
- 处置: deep-read
- 声称检查的不变量: `check_volume_alignment`/`extract_chapter_node`/`extract_key_terms`
- findings: 无（直测真实实现）
- 验证命令: read 全文；运行 → 4 passed
- 置信度: high

### tests/pressure-tests/prompts/.gitkeep + 6 个压力提示（audit-skipping/chapter-writing/foreshadowing-fatigue/import-shortcut/snapshot-skip/state-drift）
- 处置: deep-read
- 声称检查的不变量: 压力测试场景提示（时间/沉没成本/疲劳压力 + 反理性化表 + 评分标准）
- findings: 无（提示内容自洽；引用 `苍穹之上/`/`红日/` 项目为测试前置，不引用具体 fixture 路径，无 G0.9 风险）
- 验证命令: read 全部 7 文件；`grep -rn "tests/fixtures" tests/pressure-tests/` → 无引用（不触发 G0.9）
- 置信度: high

### tests/property/__init__.py
- 处置: deep-read
- 声称检查的不变量: 包标记
- findings: 无
- 验证命令: `wc -c` → 36
- 置信度: high

### tests/round-exec.sh
- 处置: deep-read
- 声称检查的不变量: round 执行器（创建模式 + --validate 模式）；G0 前置检查；token 哈希
- findings: 无（脚本自洽：`tests/rounds/` gitignore 化后创建模式可用；--validate 检查 summary/skill-output/reports/traces/enhancement-signals；G0.3 expected_chapters 解析与实时输出一致）
- 验证命令: read 全文（154 行）；实时 G0 输出 G0.3 expected_chapters=34 与脚本解析路径匹配
- 置信度: high

### tests/test-gates.sh
- 处置: deep-read
- 声称检查的不变量: validate-gate 集成（G0/G1/G2/G3/G4/G5/G6/G7/G_TRANSITION/G_DISPATCH/G_RECONCILE 返回合法 JSON + 负路径）
- findings: [F716 关联]（G1/G3/G7 依赖已消失的 round-001 → 恒 SKIP 分支；G7 接受 PASS|FAIL|INCOMPLETE|UNIMPLEMENTED 四态，断言弱）
- 验证命令: read 全文（366 行）；`ls tests/rounds/` → 不存在 → Test 1.5/1.6/4 走 SKIP/fallback 分支
- 置信度: high

### tests/regenerate-baselines.sh
- 处置: deep-read
- 声称检查的不变量: 重生成 gate-outputs 基线
- findings: [F704]（G6/G7 段因 round-001 目录消失不可再生；G2-chapter 锚定伪造 fixture；G4-genre_config 捕获 not_found 失败态）
- 验证命令: read 全文（55 行）；`ls tests/rounds/` → 不存在
- 置信度: high

### tests/unit/__init__.py / tests/unit/.gitkeep
- 处置: deep-read
- 声称检查的不变量: 包标记/占位
- findings: 无
- 验证命令: `wc -c` → 32/0
- 置信度: high

### tests/unit/conftest.py
- 处置: deep-read
- 声称检查的不变量: autouse reset executor 模块级缓存防顺序依赖
- findings: 无（合理；与根 conftest 的 structlog 隔离互补）
- 验证命令: read 全文
- 置信度: high

### tests/unit/audit/__init__.py / test_record.py / test_snapshot.py / test_write_audit.py
- 处置: deep-read
- 声称检查的不变量: 审计记录写 JSONL；文件变更快照/参数化 glob；写所有权审计（genre 字段级/track 记录级/跨段 drift/未声明写入）
- findings: 无（直测真实实现；`test_write_audit.py` 覆盖所有权语义真实路径）
- 验证命令: read 全文（38+55+87）；运行 tests/unit/audit → 11 passed
- 置信度: high

### tests/unit/config/__init__.py
- 处置: deep-read
- 声称检查的不变量: 空包标记
- findings: 无
- 验证命令: `wc -c` → 0
- 置信度: high

### tests/unit/config/test_config_coherence.py / test_production_config_coherence.py / test_thresholds.py
- 处置: deep-read
- 声称检查的不变量: genre-config 更新 rationale 治理/审计日志/floor 下限；生产 novel-output 配置一致性；阈值单一事实源
- findings: 无（直测真实实现 + 生产配置守卫；`test_production_config_coherence.py` 对 novel-output 真实文件断言）
- 验证命令: read 全文（64+34+131）；运行 tests/unit/config → 24 passed
- 置信度: high

### tests/unit/contract/__init__.py / test_dict_reads.py
- 处置: deep-read
- 声称检查的不变量: dict-form reads 提取 file+fields；`requires_independent_agent` 读取
- findings: 无（monkeypatch legacy.SKILLS 隔离，直测 load_contract）
- 验证命令: read 全文；运行 → 3 passed
- 置信度: high

### tests/unit/contracts/__init__.py + test_base / test_enums / test_fields / test_paths / test_graph / test_ownership / test_registry / test_registry_pipeline_producers / test_thresholds / test_canaries / test_scoring_contracts / test_genre_config_contract / test_pacing_design_contract / test_foreshadowing_resolve_contract
- 处置: deep-read
- 声称检查的不变量: 契约层基类型 frozen；枚举成员；字段过滤/归一化；路径解析 N/NNN 不越界；DAG glob 折叠；写所有权；registry 自动发现；producer 标注；阈值；7 个 canary 哨兵；评分/类型契约模型
- findings: 无（canaries 是高质量哨兵——F700 的对照正面案例；`test_canaries.py` 静态 is 身份断言 + 动态共享模型突变验证）
- 验证命令: read 全部 15 文件；运行 tests/unit/contracts → 全绿
- 置信度: high

### tests/unit/contracts/schemas/__init__.py + test_decisions / test_deps / test_hooks / test_novel_scores_state / test_registry
- 处置: deep-read
- 声称检查的不变量: DecisionsDoc extra=forbid + P2.5 rationale 规则；DepsDoc 真实 deps.json 加载；HookState 6 态 + parse 大小写/折叠；NovelConfig/ProgressDoc/SummaryDoc/ScoreReport；TruthFilesRegistry 真实 YAML
- findings: 无（真实文件加载验证；`test_deps.py` 读真实 tests/tiers/deps.json 但只读不写，安全）
- 验证命令: read 全部 5 文件；运行 tests/unit/contracts/schemas → 全绿
- 置信度: high

### tests/unit/cost/__init__.py + test_estimate / test_ledger / test_pricing / test_report
- 处置: deep-read
- 声称检查的不变量: token 估算/上下文警告；JSONL ledger 记录/聚合/容错；定价表/模型解析/成本；报告 CLI
- findings: 无（直测真实实现；`test_pricing.py` 断言 0.14 价格锚定当前表）
- 验证命令: read 全部 5 文件；运行 tests/unit/cost → 全绿
- 置信度: high

### tests/unit/dispatcher/__init__.py + test_codex_mark_done / test_executor_audit / test_executor_no_codex_api / test_read_provenance_honest
- 处置: deep-read
- 声称检查的不变量: codex 完成直接写 progress.json（非 shenbi-progress 子进程）；executor 写审计阻断越权；codex-api 死分支不可达；read-provenance 诚实声明
- findings: 无（`test_executor_no_codex_api` 行为级验证优于源码 grep；`test_read_provenance_honest` 诚实锚定子进程盲点）
- 验证命令: read 全部 5 文件；运行 tests/unit/dispatcher → 全绿
- 置信度: high

### tests/unit/gates/__init__.py / tests/unit/gates/conftest.py / tests/unit/gates/g4/__init__.py / tests/unit/gates/g4/conftest.py
- 处置: deep-read
- 声称检查的不变量: 包标记；make_project 工厂；sample/empty skill-output fixtures
- findings: 无（fixtures 为临时目录构造，非手写 mock，合规 G0.9 精神）
- 验证命令: read 全部 4 文件
- 置信度: high

### tests/unit/gates/test_shared.py
- 处置: deep-read
- 声称检查的不变量: jload/yload/word_count_md/passed/fail/write_gate_marker/normalize/count_transition_words/find_report/read_genre_config
- findings: 无（341 行直测真实实现；transition word 计数"避免 然 双计"细节断言到位）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g0.py / test_g0_calibration_hash.py / test_g0_config_coherence.py / test_g0_dynamic_count.py / test_g0_independence.py / test_g0_purity.py / test_g0_skill_contract.py
- 处置: deep-read
- 声称检查的不变量: G0 全链检查 + G0.14 锚点哈希 + G0.cc 配置一致性 + G0.10 动态计数 + G0.13 独立性 + G0.9 纯净 + G0.16 契约
- findings: [F704 关联]（`test_g0.py:94-116` test_g04_passes_on_clean_repo 依赖真实 repo 状态，漂移敏感但断言仅 PASS 结构）
- 验证命令: read 全部 7 文件；运行 tests/unit/gates/test_g0*.py → 全绿；实时 G0 运行交叉验证 G0.14 PASS
- 置信度: high

### tests/unit/gates/test_g1.py / test_g1_backup.py / test_g1_fields.py
- 处置: deep-read
- 声称检查的不变量: G1 文件存在性/JSON/YAML/.bak/锁/评分历史；BACKUP_SKILLS 派生；字段存在软检查
- findings: 无（直测真实实现；`test_g1_backup.py` 验证派生集含 review-resonance/memory-distill——真实修复回归）
- 验证命令: read 全部 3 文件；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g2.py
- 处置: deep-read
- 声称检查的不变量: G2 全部子检查（文件完整性/字数/检查块/占位符/truth diff/句末标点/YAML/decisions 分支/meta 比例）
- findings: 无（612 行高覆盖直测；decisions 分支含 C1 .md/.json 混合跳过回归）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g3.py
- 处置: deep-read
- 声称检查的不变量: G3 依赖/评分/输出文件/独立评分者/评分历史 + D19 canary
- findings: 无（D19 canary 用 AST 断言死函数不回归，是高质量哨兵）
- 验证命令: read 全文（344 行）；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g4_decisions.py
- 处置: deep-read
- 声称检查的不变量: G4 decisions schema 验证 + P2.5 + ID 单前缀 + 非 JSON skip + composite 分区
- findings: 无（394 行直测；C2 分区用 spy 验证 .json 不泄漏给结构检查器——高质量）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g4_escalation_review.py / test_g4_score_checkers.py / test_g4_signatures.py
- 处置: deep-read
- 声称检查的不变量: escalation/score-arc/stratum/volume 检查器；gate_G4 签名透传
- findings: [F707, F714]（子串断言 + or 短路弱断言）
- 验证命令: read 全部 3 文件；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g5.py / test_g5_coverage.py
- 处置: deep-read
- 声称检查的不变量: G5 阶段边界/前置评分/glob 闭包 WARN/角色冲突/术语混合
- findings: [F703 关联]（`test_g5.py:139-163` 与 `test_g5_coverage.py:41-42` 显式 pin G5.3 numeric 检测的 m.group(2) IndexError 死代码为"预期行为"——文档化死分支，Non-Goal #3 约束下可接受但需关注）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g6.py / test_g6_checks.py
- 处置: deep-read
- 声称检查的不变量: G6 全链（章节数/连续性/节奏/ghost/风格/规则/敏感词/卷边界）+ 提取检查器
- findings: [F703 关联]（`test_g6_checks.py:130-146` pin future_knowledge 死守卫为预期行为）；[F706]（jload 异常仅断言 FAIL）
- 验证命令: read 全部 2 文件（615+224）；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g7.py / test_g7_trace.py
- 处置: deep-read
- 声称检查的不变量: G7 幻觉技能/覆盖/占位/未决 truth/marker 重跑/时间线/重复模式/阶段态 + trace 审计
- findings: [F715]（G7.15 docstring 与断言矛盾）；无（trace 审计直测签名链）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_g_dispatch.py / test_g_reconcile.py / test_g_transition.py
- 处置: deep-read
- 声称检查的不变量: G_DISPATCH 完成集/G_RECONCILE 报告匹配/G_TRANSITION 队列
- findings: [F702]（reconcile 绕开 GR.2 bug）；无（dispatch/transition 直测）
- 验证命令: read 全部 3 文件；运行 → 全绿
- 置信度: high

### tests/unit/gates/test_pre_write_check_overlap.py
- 处置: deep-read
- 声称检查的不变量: NL-artifact 技能 PRE_WRITE_CHECK/POST_WRITE_SELF_CHECK 重叠审计
- findings: 无（审计性测试，断言仅"结果表齐全"——设计如此）
- 验证命令: read 全文；运行 → 1 passed
- 置信度: high

### tests/unit/gates/g4/test_all_skills_parametrized.py
- 处置: deep-read
- 声称检查的不变量: 20 个 G4 checker 空输入冒烟（12×20=240 用例）
- findings: [F717]（全空输入，凑密度无业务断言）
- 验证命令: read 全文；运行 → 240 passed
- 置信度: high

### tests/unit/gates/g4/test_anti_detect.py / test_chapter_drafting.py / test_chapter_planning.py / test_chapter_planning_role.py / test_chapter_revision.py / test_character_design.py / test_context_composing.py / test_decisions_validator.py / test_faction_builder.py / test_foreshadowing_plant.py / test_foreshadowing_plant_regression.py / test_foreshadowing_track.py / test_genre_config.py / test_length_normalizing.py / test_location_builder.py / test_pacing_design.py / test_plot_thread_weaver.py / test_power_system.py / test_relationship_map.py / test_review_arc_payoff.py / test_review_resonance.py / test_state_settling.py / test_story_architecture.py / test_style_polishing.py / test_volume_outlining.py / test_worldbuilding.py / test_worldbuilding_unchanged.py
- 处置: deep-read（27 文件逐一）
- 声称检查的不变量: 各 G4 业务规则（anti-detect 报告表/chapter-drafting 视觉场景·章末钩·过渡词密度·疲劳词·主角在场/planning 8 段·chapter_role/character-design 原型源·major/minor 阈值/faction/location/pacing beats·plot threads·power system·relationships/review-arc-payoff 5 维表·resonance 评分表/state-settling 位置·角色·钩状态/story-architecture 冲突·volume map/style-polishing 润色说明·字数比/volume-outlining/worldbuilding 圣经·规则·truth 模板）
- findings: [F707]（score/escalation 用子串断言）；[F703 关联]（无）；`test_worldbuilding_unchanged.py:30-35` 源码文本断言 `"max(heading_rules, numbered_rules)" in text` 属脆弱但有意（锁定行为）
- 验证命令: read 全部 27 文件；运行 tests/unit/gates/g4 → 全绿
- 置信度: high（`test_character_design.py` 因 fixture 细节多标 medium 已在上文低置信度说明）

### tests/unit/orchestration/__init__.py / test_bridges.py
- 处置: deep-read
- 声称检查的不变量: escalation/scoring bridge 解析与裁决
- findings: 无（直测真实实现）
- 验证命令: read 全文；运行 → 3 passed
- 置信度: high

### tests/unit/phase_runner/__init__.py / test_run_gate_uses_cli_module.py
- 处置: deep-read
- 声称检查的不变量: run_gate 走 `-m shenbi.gates.cli` 非已删 validate-gate.py；OSError→FAIL
- findings: 无（行为级验证）
- 验证命令: read 全文；运行 → 3 passed
- 置信度: high

### tests/unit/pipeline/__init__.py / conftest.py
- 处置: deep-read
- 声称检查的不变量: 包标记；tmp_project/sample_seed_content fixtures
- findings: 无
- 验证命令: read 全文；运行依赖该 conftest 的套件 → 全绿
- 置信度: high

### tests/unit/pipeline/test_adaptive_triggers.py / test_triggers.py
- 处置: deep-read
- 声称检查的不变量: 自适应 recall/drift/snapshot 触发；完整触发器系统（arc/stratum/卷边界/书收束/配置漂移/写序 I14）
- findings: 无（572 行直测真实实现；卷边界用真实 volume_map.md 构造）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_audit_layer.py
- 处置: deep-read
- 声称检查的不变量: audit 子编排器（genre 圈矩阵/boundary 圈触发/文件路径/严重度扫描/CamelCase 兼容）
- findings: 无（356 行；`test_real_fixture_activates_audits` 读真实 fixture）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_bridge_tracker.py
- 处置: deep-read
- 声称检查的不变量: bridge_tracker.md 模板结构
- findings: 无（`pytest.skip` 条件为文件缺失——`truth/bridge_tracker.md` 当前存在，测试实际执行；skip 条件合理）
- 验证命令: read 全文；`ls truth/bridge_tracker.md` → 存在
- 置信度: high

### tests/unit/pipeline/test_chapter_loop.py
- 处置: deep-read
- 声称检查的不变量: chapter loop 编排（16 步表/run_chapter_step/dispatch·G4·G3 失败/暂存/上下文装配/章节完成/条件 resolve/重试升级/审计圈/修订路由/A8 审计层/A7 G4 文件解析/共鸣分数解析/卷对齐）
- findings: [F700]（index 16 越界无效测试）；[F711]（索引注释漂移）
- 验证命令: read 全文（1154 行）；运行 TestGateFailurePaths → 1 passed（空转）；.venv 打印 CHAPTER_STEPS 索引
- 置信度: high

### tests/unit/pipeline/test_chapter_loop_full.py
- 处置: deep-read
- 声称检查的不变量: 全章循环集成（暂存→checkpoint→上下文→草稿→settle→审计圈→修订路由）经真实 orchestrator
- findings: [F711]（文档索引与 16 步表不一致）；无（编排逻辑真实驱动，外部子进程 mock 合理）
- 验证命令: read 全文（587 行）；运行 → 全绿
- 置信度: medium（并行 dispatch 整体 mock，见 F701）

### tests/unit/pipeline/test_checkpoint.py / test_staging_cleanup.py / test_staging_commit.py
- 处置: deep-read
- 声称检查的不变量: checkpoint 暂存提交/清理；auto-commit 两阶段
- findings: 无（直测真实实现）
- 验证命令: read 全部 3 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_cli.py / test_cli_rollback_removed.py
- 处置: deep-read
- 声称检查的不变量: pipeline CLI 七命令 + rollback 移除 + total_chapters 更新 + truth 完整性 + re-dispatch
- findings: 无（[F718 关联] 直调 main(argv)）；`test_modify_chapter_memo_rolls_back_step_index` 测试内重建回滚逻辑（与 F702 同型，未单列）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_closure.py
- 处置: deep-read
- 声称检查的不变量: closure 10 步/checkpoint 门控/重试
- findings: 无（直测真实实现）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_context_assemble.py / test_context_audit.py / test_context_curation.py / test_context_persistence.py
- 处置: deep-read
- 声称检查的不变量: Route A/B/C 上下文装配/预算/去重；覆盖审计/回填；策展（结尾多样性/钩债务简报）；持久化 fallback
- findings: [F710]（降级路径 masking skip）
- 验证命令: read 全部 4 文件；运行 → 全绿（2 skipped 为 masking）
- 置信度: high

### tests/unit/pipeline/test_dispatch_helper.py / test_dispatch_usage_capture.py / test_dispatch_write_semantics.py / test_drift_intervention.py
- 处置: deep-read
- 声称检查的不变量: dispatch helper（subprocess/G3/G4/optional reads/env/多文件 schema/truth 模板/JSON 恢复/wildcard/计划骨架/控制字符/完整性 choke/重试反馈）；usage 捕获；写语义；drift 干预
- findings: 无（904 行高覆盖；`test_drift_intervention.py` 直测真实 detect_drift）
- 验证命令: read 全部 4 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_e2e.py
- 处置: deep-read
- 声称检查的不变量: Wave1 端到端（init/status/review/checkpoint 循环）
- findings: [F718]（main(argv) 直调）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_error_handler.py
- 处置: deep-read
- 声称检查的不变量: dispatch/audit/scoring/state-settle 失败处理 + 重试上限
- findings: 无（直测真实实现）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_field_filtering.py
- 处置: deep-read
- 声称检查的不变量: Layer B 字段过滤（markdown/JSON/转义）
- findings: 无
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_filelock_utils.py
- 处置: deep-read
- 声称检查的不变量: 读写锁互斥/并发读/超时/fd 泄漏修复
- findings: 无（真实线程并发验证 + fd 级断言，高质量）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_final_review_fixes.py
- 处置: deep-read
- 声称检查的不变量: C1 触发重燃守卫/C2 embedding 路径/I1-I5（触发器失败检查/closure 重试/state-settle 提交 glob/书收束 reject 回退/卷 N 替换）
- findings: 无（C2 用源码文本断言——同 F720 模式但锁定跨模块路径一致，可接受）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_full_flows.py
- 处置: deep-read
- 声称检查的不变量: 跨 wave 集成（staging commit/修订路由/触发器/错误处理/closure 流）
- findings: 无（真实编排 + 子进程边界 mock；明确记录与 brief 的计数差异）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_g4_classification.py / test_g4_feedback.py / test_genesis_to_loop.py / test_genesis.py
- 处置: deep-read
- 声称检查的不变量: G4 严重度分类/SoftFail 滑窗/G4 反馈丰富化；genesis→loop 转换；genesis 编排（17 步/索引更新/Route B 隔离）
- findings: 无（直测真实实现；`test_genesis_to_loop.py` 真 CLI 驱动 17 步）
- 验证命令: read 全部 4 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_hook_planting.py / test_last_snapshot.py / test_llm_output_integrity.py / test_machine.py / test_plan_skeleton.py
- 处置: deep-read
- 声称检查的不变量: 钩种植/快照指针/LLM 输出完整性/状态机/计划骨架
- findings: 无（直测真实实现）
- 验证命令: read 全部 5 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_parallel_dispatch.py / test_parallel_dispatch_safety.py
- 处置: deep-read
- 声称检查的不变量: 并行评审调度（限流/合并/写安全分类）
- findings: 无（`test_parallel_dispatch_safety.py` 验证 WRITE_SHARED 拒绝进入并行路径——真实安全契约）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_resonance_persistence.py / test_retry_budget.py / test_review_checklist.py / test_revision_count.py / test_revision_decisions_fallback.py / test_revision_router.py / test_revision_safety.py
- 处置: deep-read
- 声称检查的不变量: 共鸣行持久化 7 列格式/重试预算持久化/评审清单生成缓存/修订计数/decisions fallback 合规/修订路由决策树/预修订备份与内容大小守卫
- findings: 无（直测真实实现；`test_resonance_persistence.py` 与消费方 parse_resonance_scores 格式对齐验证）
- 验证命令: read 全部 7 文件；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_seed_parser.py
- 处置: deep-read
- 声称检查的不变量: seed 解析（中英冒号/双栏/真实 outline-example.md）
- findings: 无（真实 fixture 双语解析）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_skill_integration.py
- 处置: deep-read
- 声称检查的不变量: Wave4 skill 契约/文档与 pipeline 一致（跨技能一致性）
- findings: 无（直读真实 SKILL.md 与 truth-files.index.json 交叉验证）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/pipeline/test_snapshot_coverage.py / test_snapshot_pruning.py / test_soft_fail_escalation.py / test_state_concurrency.py / test_state_heal.py / test_state.py / test_style_learning_self_heal.py / test_transitions.py / test_truth_embed.py / test_truth_index.py / test_truth_index_population.py / test_truth_io.py
- 处置: deep-read
- 声称检查的不变量: 快照核心文件/CJK 守卫/保留剪枝边界/soft-fail 升级/状态并发线程安全/heal/枚举序列化/风格自愈/相位转换/embedding 存储/truth 索引/中文序数规则/truth upsert 并发
- findings: [F710]（truth_embed 降级 skip）；无（`test_truth_io.py` 8 线程 barrier 并发真实验证无丢失——高质量；`test_state_concurrency.py` 8 线程 append/increment 验证实例锁）
- 验证命令: read 全部 13 文件；运行 → 全绿（2 skipped 为 masking）
- 置信度: high

### tests/unit/records/__init__.py / test_drift.py / test_golden_parse.py / test_parser.py
- 处置: deep-read
- 声称检查的不变量: 记录解析/跨段 drift（YAML vs md 表）/golden parser 基线/幂等 round-trip
- findings: 无（`test_golden_parse.py` 是真实 golden 基线消费（pending_hooks.parse.json），与 tests/golden/ 空洞无混淆；drift 用例含 float 0.8 vs '0.80' 防假阳性）
- 验证命令: read 全部 4 文件；运行 tests/unit/records → 全绿
- 置信度: high

### tests/unit/skill_utils/__init__.py / drift_detection/__init__.py + test_*.py（15 文件）
- 处置: deep-read
- 声称检查的不变量: 校准置信度/章节模式/风格统计/漂移检测（monotonic/2σ/卷下降/人类覆盖排除）/升级信号/伏笔召回/修订路由保留/共振分流/套路检测/卷漂移宏
- findings: [F720]（校准命中率来源路径零测试）；无（compute_stats 445 行直测主路径与多数分支——与 d1-06 声称"185 行未覆盖"矛盾，支持 gap 清单陈旧结论）
- 验证命令: read 全部 15 文件；运行 tests/unit/skill_utils → 全绿
- 置信度: high

### tests/unit/text/__init__.py / test_cjk.py
- 处置: deep-read
- 声称检查的不变量: CJK 敏感词精确匹配/标点计数/字数/分词冻结基线
- findings: 无（`test_tokenize_frozen_baseline` 锁 jieba 0.42.1 输出——升级守卫）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/tools/__init__.py / test_audit_skill_descriptions.py / test_lint_contract_graph.py
- 处置: deep-read
- 声称检查的不变量: 技能描述审计工具/契约图闭包 lint（ORPHAN_READ）
- findings: 无（子进程跑真实工具 + canary 注入孤儿读）
- 验证命令: read 全部 3 文件；运行 → 全绿
- 置信度: high

### tests/unit/trace/__init__.py + test_compaction / test_event / test_materialize / test_migrate / test_replay / test_versioning / test_writer
- 处置: deep-read
- 声称检查的不变量: trace 事件签名链/压缩/物化/迁移/重放截断/版本迁移/写入器续写
- findings: 无（签名确定性/篡改检测/撕裂行截断真实验证——高质量）
- 验证命令: read 全部 8 文件；运行 tests/unit/trace → 全绿
- 置信度: high

### tests/unit/test_capability_fs.py
- 处置: deep-read
- 声称检查的不变量: CapabilityFS 只读边界（读写/删除/mkdir 拒绝）
- findings: 无
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_contract.py
- 处置: deep-read
- 声称检查的不变量: load_contract 统一加载器/schema 校验/registry 解析
- findings: 无（monkeypatch SKILLS/REGISTRY 隔离）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_coverage_thresholds.py
- 处置: deep-read
- 声称检查的不变量: 分支覆盖率 ≥78%（读 tests/coverage/coverage.xml）
- findings: [F704 关联]（依赖 gitignore 产物文件；当前工作区 coverage.xml 为部分运行产物 → 本地单跑 FAIL（1.90%），CI 全量运行后正常——环境脆弱）
- 验证命令: `.venv/bin/python -m pytest tests/unit/test_coverage_thresholds.py -q --no-cov` → FAIL 1.90%（coverage.xml 陈旧）；CI 双段设计（主跑产 xml → last 段校验）自洽
- 置信度: medium（阈值 78% 与 pyproject 注释 ">=80% branch" 不一致，属文案漂移）

### tests/unit/test_dispatcher_executor.py / test_dispatcher_modes.py
- 处置: deep-read
- 声称检查的不变量: executor 派生（file_type/input/output/agent_id/detect_mode）；模式降级
- findings: 无（真实契约派生 + C2 SECTION 防损坏哨兵）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/test_error_guidance.py / test_exceptions.py / test_recovery.py
- 处置: deep-read
- 声称检查的不变量: 异常层级/序列化/guidance 目录一致性/recovery 策略
- findings: 无（目录键与异常类名一致性校验——防漂移）
- 验证命令: read 全部 3 文件；运行 → 全绿
- 置信度: high

### tests/unit/test_gates_cli.py
- 处置: deep-read
- 声称检查的不变量: shenbi-validate CLI 各 gate 分派
- findings: 无（mock argv/stdout 直调 main；覆盖全 gate 分派分支）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_generate_autocheck_docs.py / test_lint_contracts.py / test_lint_no_forbid_with_computed_field.py / test_lint_no_fs_mutation.py / test_lint_repo_consistency.py / test_lint_status_strings.py / test_migrate_contract.py / test_plugins_generate.py / test_sync_contracts.py
- 处置: deep-read
- 声称检查的不变量: autocheck 文档生成注入/契约完整性 lint/forbid+computed_field lint/FS 变更 lint/仓库一致性（body contract·同义词·标题·loader 唯一性·dead sidecar）/状态字符串 lint/迁移幂等/插件 manifest 生成/契约同步（DAG/bijection）
- findings: 无（全部直测真实工具 + 正负控制；`test_lint_no_fs_mutation` 断言 allowlist 无死条目——高质量）
- 验证命令: read 全部 9 文件；运行 → 全绿
- 置信度: high

### tests/unit/test_logging.py
- 处置: deep-read
- 声称检查的不变量: structlog JSON/console 渲染/stderr/CLI 子进程日志路由
- findings: 无（含真子进程 CLI 日志路由验证——真实集成）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_phase_runner.py / test_phase_runner_property.py
- 处置: deep-read
- 声称检查的不变量: phase 状态机全命令/契约加载/gate 集成；Hypothesis 属性测试（round-trip/单调时间）
- findings: [F716]（gate mock 化，集成靠弱断言）；无（属性测试合理；`skipif win32` 为 OQ-1 平台说明）
- 验证命令: read 全部 2 文件；运行 → 全绿
- 置信度: high

### tests/unit/test_pricing_fail_loud.py
- 处置: deep-read
- 声称检查的不变量: 未知模型 fail-loud（ValueError）
- findings: 无
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_pytest_framework.py
- 处置: deep-read
- 声称检查的不变量: pytest 基础设施（fixtures/markers/Hypothesis/benchmark）
- findings: [F719]（`assert True` 冒烟）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_round_paths.py
- 处置: deep-read
- 声称检查的不变量: RoundPaths 读写/备份同根/章节替换/frozen
- findings: 无
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_safe_write.py
- 处置: deep-read
- 声称检查的不变量: safe_write 原子/锁无泄漏/权限/追踪/trace
- findings: 无（fd 泄漏回归 + 锁文件清理 POSIX fallback 直测）
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_scoring.py / test_scoring_anti_collapse.py / test_scoring_property.py
- 处置: deep-read
- 声称检查的不变量: scoring 全链（rubric 解析/kill switch/分类/gate marker/main 各模式/交互式/Hypothesis 不变量/防塌缩·双评分员）
- findings: [F703]（test_t2_phase_branch_uses_real_deps_json 改写跟踪文件）
- 验证命令: read 全部 3 文件；运行 → 全绿
- 置信度: high

### tests/unit/test_status.py
- 处置: deep-read
- 声称检查的不变量: 状态枚举线值/共享 helper 枚举集成
- findings: 无
- 验证命令: read 全文；运行 → 全绿
- 置信度: high

### tests/unit/test_test_density.py
- 处置: deep-read
- 声称检查的不变量: 测试密度 ≥0.10（test 函数数 / src LOC）
- findings: [F717 关联]（密度指标被空输入冒烟测试（test_all_skills_parametrized 240 个）喂饱，指标真实性打折）
- 验证命令: read 全文；运行 → 通过
- 置信度: high

---

## 3. 返回摘要

- findings 清单：F700–F720 共 **17 条**（P1 × 4：F700/F701/F702/F703；P2 × 13：F704–F720）
- deep-read 覆盖：**314 / 314**（清单全部文件；其中 21 个 calibration fixture 与 30 个 `__init__/.gitkeep` 零字节文件按结构全量验证）
- 低置信度文件：`tests/unit/pipeline/test_chapter_loop_full.py`、`tests/unit/gates/g4/test_character_design.py`、`tests/unit/test_coverage_thresholds.py`
- 未覆盖文件：**无**
- 与既有审计衔接：F704 对齐 T1108/T1109/T1102（gate-outputs 陈旧无 enforcement、golden 空洞、mutation 基线未建立）；F710 对齐 d1-11 masking 候选（sentence_transformers 降级路径）；skip/xfail 15 条处置 = keep(env/platform) 11 + masking 2 + stale 2（F709/F713）。
