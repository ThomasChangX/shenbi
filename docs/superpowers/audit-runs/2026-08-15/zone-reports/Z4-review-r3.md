# Z4 复核报告（r3，定向）— src/shenbi/gates/ ↔ 框架写入方 键空间/命名族双向对账

- 复核轮：2026-08-15 全项目深度审查，Z4 区独立复核第 3 轮（定向收尾）
- 定向范围：r2 立覆盖空洞 **F462**——checker 读的 JSON 键空间/值词表/文件命名族 vs 框架写入方实际写的键空间/命名族，**双向枚举对账**。不做全量重读。
- 编号段：F463–F471（初审 F401–F431，r1 F432–F448，r2 F449–F462）
- 只读约束：仓库零写入（唯一例外为本报告文件）；验证脚本与轮目录均在 /tmp/z4r3/，输出为实际运行结果；未执行 pytest / shenbi-dispatch / pipeline / git 写操作
- 对账方法：写方侧 grep `safe_write|write_text|json.dump|cat >|cat <<`（src/ + tests/*.sh + justfile）后逐文件读码确认键空间；读方侧穷举 gates/ 全部 `jload|json.loads|glob|rglob|\.get(` 提取键名、期望值词表、命名族

## 总体结论

F462 缝隙本轮已完成双向枚举：**17 个写方**（含 3 个"不写状态文件的 dispatch 路径"与 1 个 stdout-only）× **23 个读点**，约 61 个对账单元格。r2 的 6 个 drift 全部复核成立（F450/F455 实跑抽验通过，F449 追加 V6 复证）。缝隙内新发现 **9 条**：P1×2（F463 评分前置 marker 的 bug-hunt/clean 命名族无写方，阻断 2/3 测试类型的文档化评分流程；F464 summary.json `t1_scores` 全仓零填充写方，G7 每轮收尾结构性 FAIL）+ P2×7。另确认 3 条**结构性健康线**（phase-state 的 `"finalized"` 小写匹配、novel.json `target_word_count` D26、trace.jsonl 读写同模型单源）与 1 个**死修复雏形**（contracts/schemas/state.py 的 ProgressDoc/SummaryDoc 零使用，F471）。

**收敛判定：该缝隙已扫干净**（论证见文末）。

---

## 一、写方清单（全仓枚举，17 项）

枚举命令面：`grep -rn "safe_write|write_text|json\.dump" src/ --include="*.py"`、`grep -rn "cat >|cat <<|json.dump" tests/*.sh`、`grep -rn "t1-reports|t2-reports|t3-reports" src/`。逐项确认：

| # | 写方 | 产物 | 键空间/命名族 | 调用面 |
|---|---|---|---|---|
| W1 | trace/materialize.py:94-100 | progress.json | 12 键：round/tier/test_cycle_phase/subagent_completion_count/completed_skill_names/skills/remaining_generative/remaining_bug_hunt/remaining_clean/gate_blockers(恒[])/total_framework_skills/expected_chapters；skills[skill][tt] 子键 = {status: "done"\|"skip"\|"pending", score}，tt ∈ ("generative","bug-hunt","clean")（**子键连字符，队列键下划线——写方自身内部不一致**，materialize.py:15 vs :87-89） | chapter_loop.py:685/703 周期物化 + 崩溃自愈 |
| W2 | dispatcher/modes/codex.py:48 | progress.json | 增量合并：completed_skill_names 追加 + skills[skill][test_type] = {score, status:"done"} | executor.py:227（codex 模式，本机 detect_mode 实测返回 codex） |
| W3 | dispatcher/modes/codex.py:56+87 | t1-reports/{skill}-{test_type}-scores-subagent.json | codex 原始 JSON（数值维度键）；另 :58 产出同名 .raw | 同上。**src 内唯一 t1-reports 自动写方** |
| W4 | pipeline/dispatch_helper.py:1980-1989 | progress.json（仅缺失时引导） | {current_scorer_agent: "pipeline-g3-scorer-{uuid}", scoring_history: [{"agent": …, "g2_passed": true}]}（键名 `agent`） | run_gate_g3，管线主路径 |
| W5 | tests/round-exec.sh:92-101 | progress.json | 4 键：completed_skill_names=[]/skills={}/tier/expected_chapters（**无 remaining_* / gate_blockers / scoring_history**） | 轮创建 |
| W6 | tests/round-exec.sh:117-126 | meta.json | round/date/model/tier_target/skill_versions/notes | 轮创建（读方仅 round-exec.sh --validate 的 tier_target） |
| W7 | tests/round-exec.sh:128-141 | summary.json | 11 键：round/model/tier_target/**t1_scores:{}/t2_scores:{}/t3_scores:{}**/kill_switches/enhancement_signals/band_breakdown/next_actions | 轮创建。**t*_scores 全仓无任何填充写方**（见 F464） |
| W8 | tests/round-exec.sh:143 | enhancement-signals.json | {enhancement_signals: []} | 轮创建；gates 无读方 |
| W9 | tests/round-exec.sh:108-114 | .token-hashes.json | {tokens:[{hash,spent}]} | 轮创建；gates 无读方 |
| W10 | gates/cli.py:121 | gate-markers/G4-{skill}-generative.json | marker = gate 结果 + files_checked；**test_type 硬编码 "generative"** | `shenbi-validate G4 <skill> …`（generative 分支） |
| W11 | gates/cli.py:128 | gate-markers/G6-{pipeline}-generative.json | 同上 | `shenbi-validate G6 …` |
| W12 | phase_runner.py:43-47 | phase-state/{phase}.json | {phase, state, steps}；state ∈ PhaseState（"created"/"started"/"skills_done"/"scored"/"finalized"，全小写，status.py:30-37） | shenbi-phase 各子命令 |
| W13 | gates/gate_manifest.py:39-44 | 管线 gate manifest | 自带读方（:32），写读同文件闭合 | dispatch_helper / phase_runner / chapter_loop |
| W14 | pipeline/seed_parser.py:122-125 | novel.json.target_word_count | + pipeline/_shared.py:160-163 增量写 total_chapters | 管线 genesis |
| W15 | safe_write.py:129-140 | trace.jsonl（经 TraceWriter.append） | TraceEvent 同一 pydantic 模型（trace/writer.py:80 `TraceEvent.sign_and_new`） | 所有 safe_write 落盘 |
| W16 | dispatch_helper._dispatch_via_api(:1492)/_dispatch_via_ide | **只写 skill 产物文件，不写任何状态文件** | — | 管线 API/IDE 路径（写方覆盖面备注：这两条路径产出的 skill 完成状态不进 progress.json，但管线轮不运行 GD/GR，语义自洽） |
| W17 | scoring.py（shenbi-score） | **stdout only**（scoring.py:462 emit_json），不落盘任何报告 | 输出键 dimensions[]/final_score/classification | —（因此 `*-scores.json` 命名族**无自动写方**，仅 command-to-give.md:135 规定 T3 手工记录 `t3-reports/<pipeline>-generative-scores.json`） |

死写方：dispatcher/modes/codex_api.py（占位 raise，模块自注释"never reachable"）；dispatcher/modes/internal.py（硬拒，无落盘）。
死 schema：contracts/schemas/state.py 的 ProgressDoc/SummaryDoc——全仓零使用（grep 证实，见 F471），且其模块 docstring 自认"written by shell heredocs and lack unified writers"。

## 二、读方清单（gates/ 全部读点，23 项）

**progress.json（10 读点）**：GD.1 `completed_skill_names`（g_dispatch.py:45）；GT.1 `remaining_{from_phase}`（g_transition.py:47-48）；GT.3 `gate_blockers`（g_transition.py:70）；GR.1 `skills[sn][tt].status == "DONE"`（g_reconcile.py:40）；GR.2 文件名 rsplit 族 + `skills[skill][tt].status != "DONE"`（g_reconcile.py:49-62）；G3.3 `skills[skill].output_files`（g3.py:151-153）；G3.4 `current_scorer_agent` + `agent_trace[skill]`（g3_independence.py:20-27）；G3.5 `scoring_history[].agent_id`|str + `current_scorer_agent`（g3.py:213-222）；G1.6 `scoring_history` 仅 isinstance（g1.py:262-273）。
**文件存在性（1）**：G1.5 `rd/.gate-lock`（g1.py:245-251）。
**summary.json（4）**：G5.1 `t1_scores[pr].generative`（g5.py:57-63）；G7.1 `t1_scores` 键 ⊆ ALL_SKILLS（g7.py:37）；G7.1b `t1_scores` 键 ⊇ ALL_SKILLS（g7.py:58-61）；G7.16 `t2_scores`→phase-state/`t3_scores`→G6 marker（g7.py:241-251）。
**t1/t2/t3-reports（5 命名族）**：find_report `<skill>-<tt>-scores.json`/`<skill>-<tt>.json`/`<skill>.json`（shared.py:149-167；GR.1 + G5.1 回退）；G0.10 `*-generative-scores.json`（g0.py:447）；G7.14 `*-scores.json` mtime（g7.py:179）；G7.15 `*-generative-scores.json` + dimensions[]/数值键（g7.py:204-216）；G3.2 `*.json` + total_score/score/数值维度键（g3.py:100-124，**唯一能看见 codex 文件的读方**）。
**gate-markers（3）**：scoring.check_gate_markers `G4-{skill}-{test_type}.json` / `G6-{pipe}-{test_type}.json`（scoring.py:200-222，test_type 取自 --test-type 实参）；phase_runner pre-score/finalize `G4-{skill}-generative.json`（phase_runner.py:250/321）；G7.13 `*.json` stem 族 G4-/G6- × -generative/-bug-hunt/-clean + status/files_checked（g7.py:119-141）。
**phase-state（1）**：G7.16 `phase-state/{phase}.json` 的 `state == "finalized"`（g7.py:246-248）。

非状态文件读点（对账为健康，不展开）：deps.json/acceptance.json（静态检入配置）；novel.json `target_word_count`（g6.py:51 ← seed_parser:125，D26 已统一）；genre-config.json `chapter_word.default`（g0.py:211 与 g6.py:56 读键一致；`auditDimensions` g0_config_coherence.py:89，写方为 skill 产物，不在框架写方域）；trace.jsonl（g7_trace.py:17-28 用与写方同一 TraceEvent/canonical_payload/sign 模块，**结构性免疫键漂移**）。

## 三、双向对账矩阵

图例：✓ = 写方满足读方期望；✗ = 错配（drift）；△ = 写方不写该键时读方空转/降级；dead = 读方期望全仓无写方；— = 不适用。

### 3.1 progress.json：10 读点 × 4 写方（W1 materialize / W2 codex / W4 dispatch_helper / W5 round-exec.sh）

| 读点（期望词表） | W1 | W2 | W4 | W5 | 判定 |
|---|---|---|---|---|---|
| GD.1 completed_skill_names（list） | ✓ | ✓ | —（不写） | ✓(空) | 健康 |
| GT.1 remaining_{from_phase}（空 list） | △ 仅 from_phase ∈ {generative, clean} 可命中；"bug-hunt"（标准拼写）→ 键 remaining_bug-hunt 不存在（W1 自身子键用连字符、队列键用下划线）；T2 相位名无键 | — | — | ✗ 不写该键 → 恒 vacuous PASS | **F455**（r2，复核成立） |
| GT.3 gate_blockers（空） | ✗ 恒写 `[]`（materialize.py:90）→ 检查永远 PASS | — | — | ✗ 不写 → 同 | **F466 新**：无任何写方能写非空 |
| GR.1 status == "DONE"（大写） | ✗ 写 "done"/"skip"/"pending" | ✗ 写 "done" | — | —(skills={}) | **F449**（r2，成立）：GR.1 死检查 |
| GR.2 同上 + 文件名 rsplit 族 | ✗ | ✗（叠加 -scores-subagent 后缀使 candidate_tt 错配） | — | — | **F449/F458**（r2，V6 复证） |
| G3.3 skills[skill].output_files | dead（无写方） | dead | — | — | **F452**（r2，成立） |
| G3.4 current_scorer_agent | —（不写） | — | ✓ | — | 健康（fail-closed 半边有效） |
| G3.4 agent_trace[skill] | dead（全仓无写方，grep 证实） | dead | dead | dead | **F451**（r2，成立） |
| G3.5 scoring_history[].agent_id | — | — | ✗ 写键名 `agent` → aid 恒 "" | — | **F450**（r2，V1 复证） |
| G1.6 scoring_history（isinstance list） | △ 不写 → 默认 [] 也 PASS"0 entries"（V7） | △ 同 | ✓ PASS"1 entries" | △ 同 | **F468 新**：空转 PASS，与 F450 合看整条 scoring_history 线无兼容读写对 |

### 3.2 summary.json：4 读点 × 1 写方（W7 round-exec.sh）+ 手工协议

| 读点 | W7 | 手工填充 | 判定 |
|---|---|---|---|
| G5.1 t1_scores[pr].generative | ✗ 恒 {} → 恒走 find_report 回退（回退再撞 F458） | 可满足 | F464 关联（G5.1 的 summary 快路径在框架数据上不存在） |
| G7.1 t1_scores ⊆ ALL_SKILLS | ✓(空集) vacuous PASS | ✓ | 语义弱化 |
| G7.1b t1_scores ⊇ ALL_SKILLS(74) | ✗ 恒 FAIL 74 missing（V3） | ✗ 结构性不可满足：含 2 个 meta skill（using-shenbi 等）无测试轮可产生其条目（初审 F424 读者侧 + 本轮写者侧合流） | **F464 新** |
| G7.16 t2_scores/t3_scores | ✗ 恒 {} → 循环零次 vacuous PASS；phase-state(✓"finalized" 小写匹配 W12)与 G6 marker(W11 ✓)两支线永远到不了 | 未文档化 | **F470 新** |

### 3.3 t1/t2/t3-reports：5 命名族 × 2 写方族（W3 codex 自动 / 协议手工 *-scores.json）

| 读方族 | W3 `-scores-subagent.json` | 手工/协议 `*-scores.json` 族 | 判定 |
|---|---|---|---|
| find_report（GR.1、G5.1 回退） | ✗ 三试全不中 | ✓ | **F458**（r2，成立） |
| G0.10 `*-generative-scores.json` | ✗ | ✓ | F458（r2） |
| G7.15 `*-generative-scores.json` | ✗ | ✓ | F458（r2） |
| **G7.14 `*-scores.json`（mtime 时间线）** | ✗（V5：旧 codex 分数文件对新 marker 的时间线违规不可见） | ✓（V5 对照组 WARN 命中） | **F465 新**：r2 F458 未列此读方 |
| G3.2 `*.json` + total_score/score/数值键 | ✓（唯一命中 codex 文件的读方） | ✓ | 健康（副作用：G3.2 成为唯一消费 codex 报告的门，低分会 FAIL 而其余读方全盲） |
| t2/t3-reports 全部族 | —（W3 不写 t2/t3） | 仅 command-to-give.md:135 手工 T3 记录 | 无自动写方（协议依赖） |

### 3.4 gate-markers：3 读点 × 2 写方（W10 G4 / W11 G6）

| 读点 | W10（G4，恒 -generative） | W11（G6，恒 -generative） | 判定 |
|---|---|---|---|
| scoring.check_gate_markers `G4-{skill}-{test_type}`（test_type=--test-type 实参） | ✓ generative；**✗ bug-hunt/clean 族无写方**（V4：missing=['G4-shenbi-worldbuilding-bug-hunt'] / ['…-clean']） | — | **F463 新（P1）** |
| scoring.check_gate_markers `G6-{pipe}-{test_type}` | — | ✓ generative；bug-hunt/clean 同族缺写方（G6 评分协议仅 generative，影响面小） | F463 附注 |
| phase_runner pre-score/finalize `G4-{skill}-generative` | ✓ | — | 健康 |
| G7.13 stem 族（G4-/G6- × generative/bug-hunt/clean） | ✓（实际只会见 generative，与 G7.13 解析兼容） | ✓ | 一致（bug-hunt/clean stem 永不出现——F463 的另一面） |

### 3.5 phase-state：1 读点 × 1 写方（W12）

G7.16 `state == "finalized"` ↔ PhaseState.FINALIZED = "finalized"（status.py:37，StrEnum 序列化为小写值）→ **✓ 键与词表双匹配**（本轮专项验证，r2 未查）。该线本身健康，只是被 3.2 的 t2_scores 死读闸住（F470）。

### 3.6 写而不读（dead data，写方产物 × 读方消费）

| 写方产物 | 读方 | 判定 |
|---|---|---|
| progress.json：round / tier / test_cycle_phase / subagent_completion_count / total_framework_skills / expected_chapters / skills[·][·].score | gates/ 内零读方（grep 证实：`subagent_completion_count\|test_cycle_phase\|total_framework_skills` 在 gates/ 无命中；`.get("round")/.get("tier")/.get("expected_chapters")` 无命中） | **F469 新**：materialize 12 键仅 4 键被消费 |
| summary.json：round/model/tier_target/kill_switches/enhancement_signals/band_breakdown/next_actions | src 内零读方（grep 证实；round-exec.sh --validate 只读 t1_scores 与 meta.tier_target） | F469 一并 |
| meta.json（全文件） | gates 零读方 | F469 一并 |
| enhancement-signals.json / .token-hashes.json | gates 零读方（.token-hashes 属 kill-switch 工具域） | 矩阵备注 |
| gate manifest（W13） | 自带读方闭合 | 健康 |
| trace.jsonl（W15） | g7_trace 同模型 | 结构性健康 |

矩阵规模合计：3.1（10×4=40 格）+ 3.2（4×2=8 格）+ 3.3（6×2=12 格）+ 3.4（4×2=8 格，按读点展开）+ 3.5（1 格）+ 3.6（6 行产物侧）≈ **61 个判定格 + 6 行 dead-data 清单**。

---

## 四、新 findings（F463–F471）

### F463 | 评分前置 marker 的 bug-hunt/clean 命名族无写方：`shenbi-score --test-type bug-hunt|clean` 结构性 MARKER_MISSING 退出 | 漏报（写方枚举新证据，推翻初审"非缺陷"判断） | P1
- 证据: 读方 src/shenbi/scoring.py:200-202 `marker_file = marker_dir / f"G4-{skill_name}-{test_type}.json"`（test_type 取 `--test-type` 实参，scoring.py:368 强制检查，缺失即 emit MARKER_MISSING 并 `sys.exit(3)`，scoring.py:368-377）。写方仅两处：gates/cli.py:121 `write_gate_marker("G4", full_name, "generative", …)`（test_type 硬编码 "generative"）；cli.py:107-110 的 bughunt/clean 分支路由到 `gate_G4_bughunt/gate_G4_clean`（generic.py:354-361，不写任何 marker）。grep `write_gate_marker` 全仓调用面仅 cli.py:121/128。初审 Z4.md:68 曾判"bug-hunt/clean 不写 marker 与 phase_runner.py:252 只查 generative 一致，非缺陷"——**该判断只对账了 phase_runner，漏掉 scoring.py 这一用实参 test_type 的读方**。
- 验证（实跑 /tmp/z4r3/repro.py V4，round_dir 内预置 G4-shenbi-worldbuilding-generative.json）:
  ```
  V4 check_gate_markers test_type='generative': missing=[]
  V4 check_gate_markers test_type='bug-hunt': missing=['G4-shenbi-worldbuilding-bug-hunt']
  V4 check_gate_markers test_type='clean': missing=['G4-shenbi-worldbuilding-clean']
  ```
- 根因: F462 键空间/命名族缝隙——marker 写方命名族 {G4-skill-generative} ⊂ 读方期望族 {G4-skill-{generative,bug-hunt,clean}}。
- 影响面: AGENTS.md 定义 T1 三测试类型（generative/bug-hunt/clean）全部经 shenbi-score 评分；bug-hunt 与 clean（2/3 类型）的评分在框架数据上必然 exit 3，除非手工伪造未文档化的 marker 文件。正常路径功能错误 → P1。
- 建议方向: cli.py G4 bughunt/clean 分支补 marker 写入（需把 skill 名传入该分支），或 check_gate_markers 对 bug-hunt/clean 降级为 WARN；补一个三类型评分回归测试。

### F464 | summary.json `t1_scores` 全仓零填充写方：G7.1b 反向覆盖在框架产出的轮上恒 FAIL（74 missing） | 漏报（F424 的写方侧合流） | P1
- 证据: 读方 g7.py:58-61 `missing_in_summary = set(ALL_SKILLS) - summary_skills` → mf。写方: 全仓 grep `t1_scores` 仅 tests/round-exec.sh:133 写 `"t1_scores": {}`（空）与同文件 :19 的 --validate 读；**src/ 内零写方**（dispatcher 记 progress.json，scoring.py 只 emit stdout——W17）。叠加初审 F424：ALL_SKILLS=74 含 meta skill（using-shenbi 等），它们没有测试轮可产生条目 → 即使手工填满 72 个功能 skill 仍差 2 个，**G7.1b 结构性不可 PASS**。
- 验证（实跑 V3，round-exec.sh 脚手架形态 summary.json）:
  ```
  V3 G7 on scaffold round-exec.sh summary.json: status=FAIL
  V3 G7.1 missing_coverage entries: 1; ALL_SKILLS=74; sample=G7.1:missing_coverage:['shenbi-anchor-curate', 'shenbi-anti-detect', 'shenbi-book-spine-init', …
  ```
  调用面真实存在：command-to-give.md「每轮结束」`uv run shenbi-validate G7 <round_dir>`。
- 根因: F462——读方期望的 summary 键空间无写方（框架把分数记到 progress.json/t1-reports，G7 却查 summary.json）。
- 影响面: 文档化的每轮收尾 gate 在框架自动产出的轮目录上必 FAIL（假 FAIL），操作者只能学会忽略之——门禁信号失真。P1。
- 建议方向: 要么 dispatcher 评分后同步填 summary.t1_scores（并从 ALL_SKILLS 排除 meta skill，呼应 F424），要么 G7.1b 改读 progress.json/t1-reports（与 G0.10 同源）。

### F465 | G7.14 时间线检查的 glob `*-scores.json` 漏掉唯一自动写方的 `-scores-subagent.json` 族 | 漏报（F458 清单外的第 4 个读方） | P2
- 证据: 读方 g7.py:179 `reports_dir.glob("*-scores.json")`（t1/t2/t3-reports 三目录）；W3 codex.py:56 命名为 `…-scores-subagent.json`——glob 不匹配（文件名尾是 `-subagent.json`）。r2 F458 只列了 find_report/G0.10/G7.15 三个读方，漏了 g7.py:179。
- 验证（实跑 V5：两个同 mtime 的旧分数文件 + 一个新 marker，差分对照）:
  ```
  V5 G7.14 WARN entries (both files are older than marker; only manual family should appear): 1
      detail: G7.14:shenbi-story-architecture-generative-scores.json:older_than_G4-shenbi-worldbuilding-generative.json
  ```
  （codex 命名的 `shenbi-worldbuilding-generative-scores-subagent.json` 同样早于 marker 5000s，但未产生任何 WARN——检测面盲区实证。）
- 根因: 同 F458（命名族未对账），本条为独立读方点。
- 影响面: 对 codex 自动产出的分数报告，"marker 晚于分数"的时序异常检测失效（该检查本为发现事后补写 marker 的作弊模式）。死检查于 codex 轮 → P2。
- 建议方向: glob 增补 `*-scores-subagent.json` 或统一命名（与 F458 一并修）。

### F466 | GT.3 读 `gate_blockers`，唯一写方 materialize 恒写 `[]`——检查在框架数据上恒 PASS | 漏报 | P2
- 证据: 读方 g_transition.py:70-85（非空即 FAIL）；写方 materialize.py:90 `"gate_blockers": []`（字面量，无任何条件分支）；W2/W4/W5 均不写该键。全仓无其他写方（grep `"gate_blockers"` src/ 仅 materialize 写 + g_transition/g7 读）。
- 根因: F462——"gate 失败应回写 blockers"的语义没有任何写方实现（G7.8 也仍是 UNIMPLEMENTED，g7.py:113）。
- 影响面: 相位转换门的质量闸第三条为死检查；fail 信号只能来自 GT.1（而 GT.1 自身受 F455 键错配）。P2。
- 验证: 读码 + grep（行号如上）；V2 场景中 gate_blockers=[] 与 GT.3 PASS 共现。
- 建议方向: gate FAIL 路径回写 gate_blockers（经 trace 事件），或暂将 GT.3 标 UNIMPLEMENTED 与 G7.8 对齐。

### F467 | G1.5 读轮级 `.gate-lock`——全仓无写方，锁检查恒 PASS（死检查） | 漏报 | P2
- 证据: 读方 g1.py:243-253（存在且 ≤300s 即 FAIL）；grep `gate-lock` 全仓（--include='*.py/sh/md'）仅命中 g1.py、tests/unit/gates/test_g1.py、两份 2026-06-11 归档设计文档（docs/superpowers/{plans,specs}/archive/…gate-system…）——设计有、实现无。
- 根因: 并发锁的写方（dispatcher 或 round-exec 层）从未落地；checker 读的是规划中而非实存的文件族。
- 影响面: 文件锁防并发 dispatch 的门禁空转；由于是"不存在即 PASS"的 fail-open 形态，无假 FAIL，仅防护缺失。P2（罕见路径死检查）。
- 验证: `grep -rn "gate-lock" <repo> --include=… -l` 输出如上 4 文件。
- 建议方向: dispatcher 执行期创建/清除 .gate-lock，或删除 G1.5。

### F468 | G1.6 对缺 `scoring_history` 键的写方形态记 PASS"0 entries"——与 F450 合并看，scoring_history 读写线无任何兼容写方 | 漏报 | P2
- 证据: 读方 g1.py:262-273 仅 `isinstance(scoring_history, list)` 判断，键缺失时 `progress.get("scoring_history", [])` 默认 [] 亦为 list → PASS。写方：materialize/W2/W5 不写该键；唯一写该键的 W4 用 `{"agent": …}` 条目——G3.5 读不出（F450），G1.6 却计数"1 entries"PASS。
- 验证（实跑 V7，materialize 形态 progress 无该键）:
  ```
  V7 G1.6 on materialize-shape progress (no scoring_history key): [{'id': 'G1.6', 's': 'PASS', 'note': 'scoring_history: 0 entries'}]
  ```
- 根因: F462；G1.6 的检查强度只有 isinstance，无法暴露键空间断层。
- 影响面: "评分历史就绪"检查在所有框架写方形态下空转 PASS，给 G3 链提供虚假的前置信心。P2（主危害已由 F450 P1 承载）。
- 建议方向: G1.6 改为"scoring_history 存在且非空且条目含可识别 agent 键（agent|agent_id）"，与 F450 修复联动。

### F469 | materialize 写 12 键仅 4 键被 gates 消费；summary.json 7 键、meta.json 全文件、progress 子键 score 均为 dead data | 漏报（dead data 清单） | P2
- 证据: gates/ 内 grep `subagent_completion_count|test_cycle_phase|total_framework_skills` → 0 命中；`.get("round")|.get("tier")|.get("expected_chapters")`（progress）→ 0 命中；`\.get("score")|\["score"\]` gates/*.py → 0 命中（gates 只从 t1-reports 读分数）。summary 的 kill_switches/band_breakdown/enhancement_signals/next_actions/round/model/tier_target 在 src 零读方（grep 证实，唯一 summary 读者 g5/g7 只读 t*_scores）。
- 根因: W1 物化时按旧 update_progress 语义全量重建，读方从未跟上；W7 是兼容性脚手架。
- 影响面: 无错误判定（读不到 ≠ 判错），但状态文件承载大量无消费数据，掩盖"哪些键是真契约"——正是 F462 得以滋生的土壤。P2。
- 验证: 上述 grep 实跑输出（空）。
- 建议方向: 以 contracts/schemas/state.py 为单源裁剪键集（见 F471），dead 键删除或在 schema 注明 informational。

### F470 | command-to-give.md:118 要求"从 summary.json 读取"T2 finalized+分数——该键空间无写方；G7.16 同键读恒 vacuous PASS | 漏报 | P2
- 证据: 协议文档 command-to-give.md:118 `# 1. 确认 T2 全部 finalized + ≥ 94（从 summary.json 读取）`；W7 写的 summary.json 键空间（11 键）无任何 finalized/分数语义键；t2_scores 全仓无填充写方（见 F464 grep）。读方 g7.py:241-251 遍历 `t2_scores`/`t3_scores` → 恒零次循环 → PASS（phase-state 与 G6 marker 两支线——本身键词表健康（3.5 节）——永远不可达）。
- 根因: F462 的文档面投影：协议步骤引用了不存在于任何写方的数据源。实际 finalized 状态存于 phase-state/{phase}.json（W12），协议指错了文件。
- 影响面: T3 启动前置确认步骤无数据可依（操作者只能自行改读 phase-state）；G7.16 门禁空转。P2。
- 验证: 读码 + F464 同批 grep（t2_scores/t3_scores 零写方）。
- 建议方向: 协议改指 `phase-state/*.json` + `shenbi-phase` 查询；或实现 summary 回填。G7.16 与 F464 一并修。

### F471 | contracts/schemas/state.py 的 ProgressDoc/SummaryDoc（F462 的修复雏形）全仓零使用——schema 存在但未接线 | 漏报 | P2
- 证据: `grep -rn "ProgressDoc\|SummaryDoc" src/ --include="*.py" | grep -v schemas/state.py` → 空输出。模块 docstring 自述"written by shell heredocs and lack unified writers…routinely carry keys the contract layer does not own. Once the writers are unified, these upgrade to extra: forbid"。
- 根因: 修复停在建模层：没有任何写方/读方 import 这两个模型，`extra: ignore` 也无运行时效果。
- 影响面: r2 F462 建议的"单一 schema"看起来已存在，实则死代码——后续修复者可能误以为契约已建立。P2（dead-wire 修复雏形）。
- 验证: 上述 grep 实跑（空）。
- 建议方向: 将 materialize/codex/round-exec.sh 的写路径与 gates 的读路径统一 import 该 schema（键名常量化），或在其 docstring 标注"未接线"。

---

## 五、r2 六 drift 复核结论（逐条）

| r2 编号 | 结论 | 本轮证据 |
|---|---|---|
| F449（status DONE/done + -scores 后缀） | **成立** | 写方行号复读一致（materialize.py:59 "done"、codex.py:44 "done"）；新增 V6 实跑：`V6 G_RECONCILE codex naming (progress says done; SHOULD PASS): status=FAIL must_fix=['GR.2:shenbi-worldbuilding-bug-hunt-scores-subagent:status=?']`——后缀错配与大小写错配同现，GR.1 对 "done" 未触发（死检查面复证） |
| F450（agent_id/agent） | **成立** | V1 实跑：`G3.5 (writer-shape, scorer-A in history as 'agent'; SHOULD FAIL): [{'id': 'G3.5', 's': 'PASS', 'note': '0 prior scorers'}] | gate=PASS`——r2 repro V3 结论逐字复现 |
| F451（agent_trace 无写方） | **成立** | 本轮 grep 复跑：`agent_trace` 在 src/ 仅 g3_independence.py:23-25 读方，无写方 |
| F452（output_files 无写方） | **成立** | 本轮 grep 复跑：`"output_files"` src/ 命中仅 g3.py:153 读方 + phase_runner/executor 局部变量（不落盘 progress.json） |
| F455（remaining_ 键错配） | **成立** | V2/V2b 实跑：`GT from_phase='bug-hunt' (queue NON-empty; SHOULD FAIL): PASS` / `from_phase='bug_hunt': FAIL must_fix=['GT.1']`；补充根因：materialize 自身内部不一致（子键 "bug-hunt" 连字符 vs 队列键 remaining_bug_hunt 下划线，materialize.py:15 vs :88） |
| F458（-scores/-scores-subagent 命名族） | **成立** | find_report/G0.10/G7.15 读码复读一致；V5/V6 差分实证漏读；**范围修正：同族还有第 4 个读方 g7.py:179（G7.14）r2 未列** → 已立 F465 |

r2 复核无单方降级异议；F449/F450 维持 P1。

## 六、收敛判定：F462 缝隙是否已扫干净

**判定：已扫干净（双向枚举完备），可宣布该缝隙收敛。** 论证：

1. **写方枚举完备性**：以 `safe_write|write_text|json.dump`（src/ 全部 .py）+ `cat >|cat <<|json.dump`（tests/*.sh、justfile）+ `t1-reports|t2-reports|t3-reports|progress.json|summary.json|gate-markers|phase-state`（全仓）三组 grep 交叉，命中面逐文件读码归类为 W1–W17；三条否定验证封边：(a) dispatcher 另两 mode（internal.py 硬拒 / codex_api.py 死占位）不写状态文件；(b) 管线 API/IDE 路径只写 skill 产物（W16）；(c) shenbi-score stdout-only（W17）。唯一"写方"残留在协议文档规定的人工动作（command-to-give.md:135 T3 手工记录），已作为独立写方族入矩阵。
2. **读方枚举完备性**：穷举 gates/ 全部 `jload|json.loads` 调用点（21 处，含 cli.py 2 处透传）与全部 `glob|rglob` 命名族（g0:447、g3:100、g7:119/179/183/204/251、find_report 内 3 试），逐点提取键名/期望词表，共 23 个状态读点——无第 24 个（g2 的 decisions.json 属产物文件非状态文件，其读写对账在 r1 已覆盖；deps/acceptance/genre-config/novel 属静态配置或 skill 产物域，均注明）。
3. **对账完备性**：61 判定格 + 6 行 dead-data 行全部落到 ✓/✗/△/dead 四值之一；每个 ✗/dead 均归到 F449–F471 之一，无未归类错配格残留。健康线（GD.1、G3.4 fail-closed 半边、phase-state 词表、novel.json D26、trace 同模型、gate manifest 闭合）明确标出，避免下轮重查。
4. **本轮新发现 9 条全部落自矩阵格**（非随机重读命中），且 P1 两条（F463/F464）分别是"读方期望族 ⊃ 写方族"与"读方键无写方"两个方向的极端案例——恰证明双向枚举已把该缝隙的两个方向都走到头。

残余风险声明：本判定限于"缝隙已扫干净"（发现面收敛），**不等于缺陷已修复**——F449/F450/F463/F464 四条 P1 仍在架上。若协调者组织修复轮，建议顺序：F462 治本（接线 state.py schema + 键名常量单源，F471）→ F463/F464（评分与收尾主路径）→ F449/F450（词表兼容）→ 其余 P2 打包。

## 七、验证命令与产物索引（均在 /tmp/z4r3/，仓库零写入）

- `/tmp/z4r3/repro.py`（`uv run python /tmp/z4r3/repro.py` 实跑，输出已嵌入上文）：V1=F450 复证 / V2+V2b=F455 复证 / V3=F464 / V4=F463 / V5=F465 差分 / V6=F449+F458 复证 / V7=F468
- grep 组（输出见各 finding）：agent_trace 无写方（F451）、output_files 无写方（F452）、t1-reports 唯一自动写方 codex（F458）、t1/t2/t3_scores 零填充写方（F464/F470）、gate-lock 全仓 4 文件（F467）、gate_blockers 唯一写方恒 []（F466）、progress 死键 gates 零读方（F469）、ProgressDoc/SummaryDoc 零使用（F471）、write_gate_marker 仅 cli.py 两调用（F463）
- 未验证项（逐条声明）：F463 的端到端 `shenbi-score --test-type bug-hunt` exit 3（需构造完整 rubric+scores 输入；静态链完整：scoring.py:368-377 对 check_gate_markers 非空即 exit 3，V4 已证 missing 非空）；F466/F467 为"无写方"型死检查，无可正向触发的运行时路径，证据以 grep+读码为准。
