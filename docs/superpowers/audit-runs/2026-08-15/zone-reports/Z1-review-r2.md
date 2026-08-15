# Z1 复核报告 r2（fresh-context 独立复核，第 2 轮）

- 轮次: 2026-08-15 全项目深度审查
- 分区: Z1（src/shenbi/ 顶层 14 清单文件）
- 复核 agent 编号段: F129–F149（初审 F101–F120，复核 r1 F121–F128）
- 本轮角度（与 r1 不复用）: (a) **producer/consumer 键空间与数据形状对账**——模块间传递的 dict/dataclass/JSON 键：写方键集 vs 读方键集逐一对账（scoring emit 结构 vs 消费方、phase_runner 状态键 vs gates/cli 读取、marker 写方命名 vs 读方命名）；(b) **数值边界与默认值链**——除零/空维度/负值/NaN/bool 混入、阈值边界与单源、异常数据下的静默默认
- 方法: 14/14 清单文件 fresh 全量重读 + 消费方模块独立核实（gates/cli.py、gates/shared.py、gates/g5.py、gates/g3.py、gates/g7.py、gates/gate_manifest.py、dispatcher/modes/codex.py、dispatcher/executor.py、contracts/thresholds.py、contracts/graph.py、contracts/schemas/scores.py、deps.json、acceptance.json、command-to-give.md、novel-output 实盘 marker）+ /tmp/z1r2/ 只读场景实测（uv run python -B，未触碰仓库文件、未运行 pytest/dispatch/pipeline、无 git 写操作）
- 只读声明: 除本报告外零仓库写入；全部脚本/场景文件位于 /tmp/z1r2/
- 结论速览: 初审+r1 共 28 条 **零误报**（全部经本轮独立重验或实跑复核成立）；**漏报 9 条**（F129–F137：P2×4、M×4、证据升级×1——F131 为 F121 的生产路径证据升级，提请 P1 复议）；覆盖空洞 5 项；严重度异议 4 项

---

## 一、漏报（新 findings）

### F129 | T3/G6 marker 读写协议错配：F121 的镜像面——写方恒写 generative，读方按 test_type 查 G6-{pipeline}-{bug-hunt|clean}.json 永不存在 | error | P2（=F121 同簇）
- 证据: src/shenbi/gates/cli.py:128（**全仓唯一** G6 marker 写方：`write_gate_marker("G6", pipeline_name or "", "generative", result, arg(1))`——test_type 字面量硬编码）; src/shenbi/scoring.py:216-222（t3-pipeline 分支读 `G6-{pipeline_name}-{test_type}.json`，test_type 为变量）
- 根因: 与 F121 完全同构（写侧硬编码 "generative"，读侧用变量 test_type），但 r1 的 F121 只覆盖 T1/G4 读写对，未覆盖 T3/G6 镜像对
- 验证（已运行，/tmp/z1r2）: 磁盘放置 `G6-long-form-generative.json`（写方唯一能产出的名字）后调 check_gate_markers：
  ```
  t3 long-form generative -> []
  t3 long-form bug-hunt   -> ['G6-long-form-bug-hunt']
  t3 long-form clean      -> ['G6-long-form-clean']
  ```
  另：novel-output 实盘 marker 全部为 `G4-*-generative.json`（find 实测），磁盘零 G6 marker、零 bug-hunt/clean 命名
- 影响面: T3 评分带 `--test-type bug-hunt|clean --round-dir` 时恒 exit 3（MARKER_MISSING）；command-to-give.md:53 的处置指引（"先运行 G4/G6 gate 并生成 marker"）对该组合不可满足
- 建议方向: 与 F121 合并修复——write_gate_marker 的 test_type 参数化或读侧统一认 generative；补 T3 命名回归测试
- 定级说明: 判 P2 与 F121 对齐；F121 的 P1 复议动议（见 F131/异议表）成立时本条同升

### F130 | G3.2 读键与 scoring 输出形状错配：`total_score`/`score`/顶层数字键 vs 写方 `final_score`+嵌套 dimensions[]——按文档协议落盘的规范评分报告（95 分 PASS excellent）被判 G3 FAIL | error | P2
- 证据: src/shenbi/gates/g3.py:102（`score = data.get("total_score", data.get("score", 0))`——**不读 final_score**）; g3.py:107-124（回退链只认顶层数字键 `k.isdigit()` 与 `_compute_rubric_weighted_score(data)` 的顶层数字键——scoring.py 的维度分数嵌套在 `dimensions[]` 列表内，顶层零数字键）; src/shenbi/scoring.py:439-460（emit 键集：`_provenance`/`dimensions[{num,name,weight,score}]`/`kill_switch_triggered`/`kill_switches`/`final_score`/`classification`）; command-to-give.md:51+56（协议明文："Dispatcher 将 stdout 保存到 `t1-reports/<skill>-generative-scores.json`"）
- 根因: G3.2 的键期望从未与 scoring.py 的 emit 形状对账；其当前"能用"完全依赖 dispatcher 违反文档（F458：不落盘规范名文件）——即它只碰巧能读 `-scores-subagent.json` 原始分数文件（顶层数字键），而按协议应存在的规范输出文件它一个键都读不到
- 验证（已运行，/tmp/z1r2）: 用真实 rubric（using-shenbi，7 维全 95）跑 scoring 产出规范输出（`final_score: 95.0, classification: PASS (excellent)`），按文档协议命名落盘 `t1-reports/using-shenbi-generative-scores.json`，再跑 gate_G3：
  ```
  G3 status: FAIL
  G3.2 checks: []
  must_fix: ['G3.2:using-shenbi-generative-scores.json']
  ```
  即一份 95 分优秀的规范报告让 G3 假 FAIL（score 被算成 0 < 阈值 90，F411）
- 影响面: 任何按 command-to-give.md 协议保存 scoring stdout 的执行者/修复 F458 后的 dispatcher，其下一轮 G3 预检对高分报告必现假 FAIL；与 F458（文件名族）、F411（回退阈值 90）、F126（文档漂移）构成四重叠加
- 建议方向: G3.2 首选读 `final_score`（与 g5.py:68 对齐），dimensions 嵌套解析作回退；补"规范 scoring 输出文件"夹具回归（fixtures 规则：用真实 scoring 产出）

### F131 | F121 证据升级：dispatcher codex 模式对每次 dispatch 恒传 `--round-dir + --test-type`——marker 强制失效不是"文档化流程不触发"的边角，而是 bug-hunt/clean dispatch 评分步骤的必经死路 | 证据升级（F121）| 提请 P1 复议
- 证据: src/shenbi/dispatcher/modes/codex.py:94-107（`shenbi-score <rubric> <scores> --test-type <test_type> --round-dir <round_dir> --subagent`——test_type 为 dispatch 参数直通）; src/shenbi/dispatcher/cli.py:22-29（`<skill_name> <test_type> <round_dir>` 无 choices 限制，bug-hunt/clean 合法传入）; gates/cli.py:107-110（bughunt/clean 分支**不写任何 marker）+ :121（generative 分支恒写 generative 命名）
- 根因: r1 判 F121 为 P2 的依据是"文档化 T1 流程不传 --round-dir 故未踩中"——但 dispatcher 生产路径（codex 模式）对**每个** dispatch 都传 --round-dir + --test-type，前提不成立
- 验证（已运行，/tmp/z1r2）: 复刻 dispatcher 的精确调用形态（含 --subagent），磁盘放置写方唯一能产出的 `G4-shenbi-worldbuilding-generative.json`：
  ```
  $ uv run python -B -m shenbi.scoring tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md <scores> \
      --test-type bug-hunt --round-dir /tmp/z1r2/round --subagent
  {"status": "MARKER_MISSING", "missing_markers": ["G4-shenbi-worldbuilding-bug-hunt"], ...}
  rc=3
  ```
  且 command-to-give.md:53 的补救指引（"先运行 G4/G6 gate 并生成 marker 文件"）对该组合**不可满足**——G4 的 bughunt/clean 分支根本不写 marker（cli.py:107-110），按协议重试是死循环
- 影响面: `shenbi-dispatch <skill> bug-hunt|clean <round> "<prompt>"` 的评分步骤 100% exit 3；AGENTS.md "no gate can be skipped" 的执行面对 2/3 测试类型为不可满足强制
- 建议方向: 采信 r1 异议 1 + 本条证据：F121（连同 F129）升 P1；修复时写侧按实际 test_type 写 marker 并给 bughunt/clean 分支补写
- 定级说明: 本条为 F121 的证据升级登记（非独立缺陷），ledger 合并时挂到 F121 名下

### F132 | validate_scores 类型/范围检查两个穿透口：NaN 通过 0-100 检查（比较恒 False）→ final_score=NaN 且 emit 含非 RFC 8259 的 `NaN` 字面量；JSON `true/false` 被 `isinstance(x, int)` 放行（bool 是 int 子类）→ 按分数 1/0 参与计算并原样回显 | error | P2（latent）
- 证据: src/shenbi/scoring.py:153-157（`isinstance(score, (int, float))` + `score < 0 or score > 100`——NaN 两比较均 False；True/False 过 isinstance）; :173（`float(scores.get(...))`——NaN 传播、True→1.0）; src/shenbi/cli_utils.py:20（`json.dumps` 默认 allow_nan=True → 输出 `NaN` 字面量）; Python `json.load` 默认接受 `NaN`/`Infinity` 字面量（parse_constant 默认放行），故 scores.json 里手写/LLM 写出 NaN 可原样进入
- 根因: 边界校验未覆盖 float 特殊值与 bool 子类语义
- 验证（已运行，/tmp/z1r2，chapter-drafting rubric 10 维全 90、dim3 特殊值）:
  ```
  scores 含 "3": NaN  → rc=0, "score": NaN, "final_score": NaN, "classification": "FAIL"
                     → jq 解析该行失败（非合法 JSON）；仓内 Python 消费方 json.loads 可静默读回
  scores 含 "3": true → rc=0, "score": true, 按权重参与计算（True→1.0）
  ```
  对照：`Infinity` 被 `> 100` 正确拒绝（REJECT）
- 影响面: dispatch 评分 subagent 产出的 scores 文件是 LLM 输出，`true/false/NaN` 形态可出现；NaN 使 stdout 协议输出对非 Python 消费方（jq/CI 工具链）不可解析；bool 静默算分
- 建议方向: validate 增加 `isinstance(score, bool)` 拒绝 + `math.isfinite(score)` 检查；emit_json 如需严格可设 allow_nan=False 兜底崩溃改结构化错误

### F133 | compute_score 数值边界三连：空/零权重维度集静默返回 0（早退于 weight_mismatch 告警之前，零诊断）；负权重被 load_rubric 接受 → 总权重非 100 时按小分母重归一 → **final_score 可越出 0-100 且 classify 判 PASS (excellent)** | error | P2（latent）
- 证据: src/shenbi/scoring.py:168-174（`total_weight = sum(...)`; `if total_weight == 0: return 0`——早于 :171 的 `!= 100` 告警，空维度集零告警）; :56-58（`int(cells[2].rstrip("%"))` 接受 "-60%" → 负权重，无下界校验）; :174（`weighted_sum / total_weight` 分母可为小/负数）
- 根因: "权重解析失败静默跳过"契约（初审已注）只覆盖 ValueError，未覆盖"成功解析出非法值"（负数）；total_weight==0 早退吞掉所有告警
- 验证（已运行，/tmp/z1r2）:
  ```
  rubric 主表解析出 0 维（格式漂移）+ scores={1:90,2:80} → rc=0, dimensions=[], final_score=0, FAIL（仅 stderr WARNING: unexpected keys，无任何"rubric 解析为空"诊断）
  rubric 权重 60/-10, scores={1:100,2:0}            → final_score=120.0, classification="PASS (excellent)"（越出 0-100 且判优）
  rubric 权重 60/-60（和恰为 0）                     → final_score=0（零告警早退）
  ```
- 影响面: rubric 权重笔误（"-" 打进权重列）静默产出 >100 的"优秀"；rubric 模板漂移静默 0 分 FAIL——均无 REJECT/无状态字段异常。空维度场景与 F104（18 份 applicability 不解析）同向：主表格式漂移时 scoring 不报错只给 0 分
- 建议方向: load_rubric 对 weight<0 报错或告警；compute_score 对 `not dimensions` 或 total_weight<=0 返回结构化 ERROR；validate 增加 final_score ∈ [0,100] 终检

### F134 | classify 的 75/60 边界硬编码在 scoring.py，违背 thresholds 模块"所有数值阈值集中此处"的单源声明 | error | M
- 证据: src/shenbi/scoring.py:178-184（`if score >= TEST_PASS`（导入）… `if score >= 75` … `if score >= 60`——后两者裸数字）; src/shenbi/contracts/thresholds.py:1-10（docstring："门阈值单一源（spec 支柱二）。**所有数值阈值集中此处**；门 import 具名常量，ruff 禁裸魔法数"——文件只定义 94/90/100，无 75/60）
- 根因: PASS_ACCEPTABLE/CONDITIONAL 边界从未进单源；今日与全部 rubric 的 "Scoring Rules" 行一致（如 using-shenbi/rubric.md:44），属漂移风险而非现行错误
- 验证: 已运行（两文件直读比对；thresholds.py 无 75/60 定义）
- 建议方向: thresholds 增 PASS_ACCEPTABLE=75/CONDITIONAL=60 并 import；或 docstring 收窄声明范围

### F135 | `--chapter` 值非整数时 main() 裸抛 ValueError traceback（无结构化报错）——F123 家族第 3 成员 | error | M（=F123 同簇）
- 证据: src/shenbi/phase_runner.py:362（`chapter = int(chapter_str) if chapter_str else None` 无守卫）
- 验证（已运行，/tmp/z1r2）: `python -m shenbi.phase_runner post-skill genesis some-skill --round-dir R --project-dir P --chapter abc` →
  ```
  File ".../phase_runner.py", line 362, in main
      chapter = int(chapter_str) if chapter_str else None
  ValueError: invalid literal for int() with base 10: 'abc'
  ```
  （整机 traceback，无 JSON 输出；对照 find_flag 缺参有结构化 log.error+exit(1)）
- 建议方向: try/except ValueError → log.error("invalid_chapter", value=...) + exit(1)；与 F123/F105 修复同批

### F136 | _provenance.gate_markers_verified 在"标记检查空转"时仍记 true——provenance 失真（F113 家族） | error | M
- 证据: src/shenbi/scoring.py:443（`"gate_markers_verified": bool(round_dir and test_type)`——只看旗标是否给齐，不看 check_gate_markers 是否真的检查了任何 marker）; :187-224（rubric 路径不含 t1-skill/t2-phase/t3-pipeline 部件时 check_gate_markers 无条件返回 []）
- 验证（已运行）: `check_gate_markers('/tmp/z1r2/empty_rubric.md', 'bug-hunt', '/tmp/z1r2/round')` → `[]`（零检查），而 `bool(round_dir and test_type)` → `True` → provenance 声称已验证
- 影响面: 自定义路径 rubric（RUBRIC env 覆盖时，见 codex.py:91-93）评分记录声称"gate markers verified"但实际零 marker 被检查——G3.4 独立审计口径污染，与 F113（scored_by 失真）同面
- 建议方向: 由 check_gate_markers 返回实际检查数/是否适用，provenance 记真值（如 "verified" / "not_applicable" / false 三态）

### F137 | load_applicability 行单元格数少于表头时缺省 "Yes"——豁免信息静默丢失的默认方向错配 | error | M（latent）
- 证据: src/shenbi/scoring.py:95（`cell_val = cells[i + 1] if i + 1 < len(cells) else "Yes"`——短行按"适用"处理）
- 根因: 缺省方向选了"保留维度"（不豁免）；表格列被截断/漏填时 N/A 豁免静默失效，被误豁免不可能、该豁免未豁免必然——与 F122（区间端点漏 4/5/6）同向的"漏豁免"族
- 验证: 已运行（直读 + 现网 44 份可解析 rubric 均为满列，当前未触发）
- 建议方向: 缺格时记 warning 或按 "No" 保守处理；与 F122 的区间展开同批修

---

## 二、误报 / 事实修正（F101–F128 全 28 条复读）

**整条误报：无。** 28 条全部成立。本轮为 fresh-context 独立重验（非沿用 r1 结论），关键复核记录：

| 条目 | 本轮复核方式 | 结果 |
|---|---|---|
| F101 | phase_runner.py:216（G4 第 3 参 str(round_dir)）+ gates/cli.py:113-121（`project_dir=rd`）直读 | 成立 |
| F102 | phase_runner.py:117,307 `str(project_dir)` + g5.py:115 `if project_dir:`（本轮定位到精确行号；"None" 真值）直读 | 成立 |
| F103 | scoring.py:356-362 直读（吞点 :361-362） | 成立 |
| F104 | **实跑重扫**：82 份 rubric → with_section=62 / parseable=44 / unparseable=18（与初审/r1 计数一致） | 成立 |
| F105 | phase_runner.py:37,46 直读 | 成立 |
| F106 | phase_runner.py:94 异常元组直读（TimeoutExpired ∉ 元组且非 OSError） | 成立 |
| F107 | scoring.py:302-309 直读（:303 IndexError 面、:309 裸 json.loads） | 成立 |
| F108 | **实跑** `ls docs/{registry,gates,schemas,dispatcher,integrity}.md tests/build_registry.py` → 全部 No such file；SHENBI_SUBAGENT_TIMEOUT grep 仅 error_guidance.py:44（余为 coverage HTML） | 成立 |
| F109 | **实跑** grep（src+tools 滤自身）→ 零运行时消费者 | 成立 |
| F110 | **实跑** 7 类逐类 grep（src+tools 非 def 命中）→ 全部 0 | 成立 |
| F111 | safe_write.py:63-91 直读 + tests/unit/test_safe_write.py:62-100 **重读**：两个 chmod 测试手工 os.open+chmod，从未调用 `_acquire_lock`（注释 "Use _acquire_lock directly" 与实现不符） | 成立 |
| F112 | justfile:22 **重读**（`shenbi-sync-contracts && git diff --exit-code` 幂等门存在——r1 轻微异议 1 的"零 pytest 覆盖"表述采纳） | 成立（表述修正沿 r1） |
| F113 | **实跑**：文件模式 probes 输出 `"scored_by": "interactive"`（F132/F133 探针顺带复核） | 成立 |
| F114 | **实跑** grep scoring_bridge（src+tools 滤自身）→ 零命中 | 成立 |
| F115/F116 | phase_runner.py:208-216 + gates/cli.py:91-104 直读 | 成立 |
| F117/F127 | __init__.py:3-10 直读（forwarder 注记 + 6 项清单） | 成立 |
| F118 | 五散点逐一复核：error_guidance.py:9 / recovery.py:8 未用 log；sync_contracts.py:124-134 skill 形参未用；scoring.py:321,331 `_phase`；phase_runner.py:188 裸 assert | 成立 |
| F119 | capability_fs.py:22-29 直读 | 成立 |
| F120 | scoring.py:266-274 直读（all_identical 无最小样本数；majority 分支有 len>=3 但 all_identical 分支没有） | 成立 |
| F121 | **实跑复刻 dispatcher 调用形态**（--test-type bug-hunt --round-dir --subagent + 唯一可产出 marker）→ exit 3 MARKER_MISSING | 成立（证据升级见 F131） |
| F122 | **实跑** `re.findall(r"#?(\d+)", "Shared audit (3-7)")` → `['3','7']` | 成立 |
| F123 | **实跑** `start --round-dir R`（漏 phase）→ `phase-state/--round-dir.json` 落盘 + `{"phase": "--round-dir", ...}` | 成立（家族扩展见 F135） |
| F124 | **实跑** skills_done + `not-json{` → `json.decoder.JSONDecodeError` 整机 traceback | 成立 |
| F125 | scoring.py:304-308/:343-355 直读——两处 subprocess.run 均无 timeout kwarg | 成立 |
| F126 | usage（:289-291）vs 实现（:337 仅 T1；--gate-only :300-313 仅 G2 argv 序）+ command-to-give.md:48-58 直读 | 成立（扩展注记见下） |
| F128 | scoring.py:51-69 直读（in_table 状态机与所在 ## 节无关） | 成立 |

事实修正/扩展注记（不改判级）：

1. **F126 再扩一例**: usage 文本（scoring.py:285-291）不列 `--subagent`，而 dispatcher 生产调用（codex.py:104）恒带该旗标且 `_provenance.scored_by` 依赖它——文档↔实现漂移清单第 4 项（前 3 项为 T1|T2|T3/gate-only/exit 3）。
2. **F121/F129 与 command-to-give.md:53 的死循环**: 协议对 exit 3 的处置是"先运行 G4/G6 gate 并生成 marker 再评分"，但 G4 的 bughunt/clean 分支（cli.py:107-110）不写任何 marker——按文档补救永远无法凑齐 marker。该事实同时强化 F131 的 P1 动议。
3. **F104 计数独立复核一致**（62/44/18），并补充：44 份可解析 rubric 的表头键 100% 统一为 `| Dimension scope | Bug-hunt | Clean | Generative |`（44/44 uniq 计数），`capitalize()` 归一化当前全部命中（见覆盖空洞 2 的隐性契约）。

---

## 三、覆盖空洞（本轮角度排除后仍敞开的面）

1. **logging 事件键的消费者对账未做**: 本轮角度 (a) 覆盖了 emit JSON/状态文件/marker 命名，但 structlog 事件键（weight_mismatch、gate_manifest_record_failed 等）的潜在工具消费者未系统对账——grep 显示仅 tests 断言，无生产解析方，风险低，留给后续轮或判定为无需覆盖。
2. **applicability 表头键 ↔ test_type 归一化的"隐性契约"未成文**: `filter_dimensions_by_test_type` 的三级归一（原样→capitalize→lower）只在前两级命中当前表头（"Bug-hunt"）；第三级 `lower()` 是死分支（任何 lower 形式都不匹配 Title-Case 表头）。该匹配纯靠 44 份 rubric 表头 100% 统一维持，无测试钉死表头拼写——rubric 模板改一个大小写即全量静默失配（filter 返回原维度集，无告警）。建议补一条表头拼写契约测试。
3. **scoring `--interactive` 模式未实测**（无 tty 环境）：EOF 填零/kill-switch 交互路径仅静态复核（r1 已注 d1-06:391-393 acceptable）。
4. **safe_write 并发正确性仍未做并发实测**（F111 的 (a) 部分两轮均为代码推演——只读约束下无法安全构造双写者竞态，维持 r1 处置）。
5. **phase-state 手写/损坏文件的键缺失面**: load_state 对损坏 JSON 裸抛（r1 已在 F124 备注登记）；对合法 JSON 但缺 `phase`/`state`/`steps` 键的文件，require_state `state["state"]` 抛 KeyError、save_state `state['phase']` 抛 KeyError——同属无守卫家族，修 F124 时应一并处理（不另立条目）。

---

## 四、严重度异议（无权改级，仅提请复议）

| 条目 | 现级 | 本轮意见 | 依据 |
|---|---|---|---|
| F121（+F129 同簇） | P2 | **P1** | r1 异议 1 的前提被本轮推翻：dispatcher codex 模式对每次 dispatch 恒传 --round-dir+--test-type（codex.py:94-107），bug-hunt/clean 的评分步骤必经 exit 3（F131 实跑复证）；且协议补救路径（command-to-give.md:53）因 cli.py:107-110 不写 marker 而不可满足——符合 P1"正常路径可复现功能错误" |
| F130（本轮新，自判 P2） | P2 | 维持 P2，附升级条件 | 当前触发需"按文档落盘规范报告"（文档说 dispatcher 做、实际 dispatcher 不做=F458）；**修复 F458 让写方回归文档后本条立即变 P1**（高分报告假 FAIL）——与 F126→F121 的耦合关系同构，建议与 F458/F411 合并裁决 |
| F133（本轮新，自判 P2） | P2 | 维持 P2 | final_score=120 "PASS (excellent)" 形似 P0"静默错误结果"，但触发需 rubric 权重列出现负数（作者笔误面，非正常路径）；若 maintainer 认为 rubric 是可信输入则可降 M，若认为 rubric 也是 LLM/人写易错输入则 P2 站得住 |
| F104 vs F757（跨区，沿 r1） | P1/P2 | 维持 r1 动议：合并为 P1 | bug-hunt/clean T1 评分失真或 REJECT 误拒，正常路径可复现 |

---

## 五、本轮角度发现摘要

**(a) producer/consumer 键空间与数据形状对账**——共对账 12 组读写对：

命中的错配（5 组）：
- G4 marker 写名（恒 generative）↔ scoring t1 读名（按 test_type）＝F121（本轮补生产路径证据 F131）
- G6 marker 写名 ↔ scoring t3 读名＝**F129（新）**
- G3.2 读键（total_score/score/顶层数字键）↔ scoring emit（final_score/嵌套 dimensions[]）＝**F130（新，实跑假 FAIL）**
- G5.1/G0.10/G7.15 文件名族 ↔ codex 唯一写方（-scores-subagent.json）＝F458（Z4 已登记，本轮独立复现其 g5.py:65 后果，不重复立条）
- dispatcher 落盘承诺（command-to-give.md:51 规范名）↔ 实际落盘（不落/异名）＝F458/F126 域

对账通过（7 组，负面结果记录）：
1. scoring emit ↔ contracts/schemas/scores.py ScoreReport（extra=forbid）：键集逐字段精确匹配（_provenance 5 键、dimensions 4 键、6 顶层键零多余）——schema 侧本身的 dead-wire 已由 Z2 F210/F221 登记
2. applicability 表头键（Bug-hunt/Clean/Generative）↔ --test-type 归一链：44/44 当前命中（隐性契约，见空洞 2）
3. phase-state 键（phase/state/steps）↔ G7.16 读取（`state == "finalized"`）：匹配（StrEnum 序列化为小写 wire 值）
4. run_gate FAIL 回退 dict（status/raw_stdout/raw_stderr）↔ cmd_start 等 `.get("status")/.get("must_fix", [])`：缺键有默认，无崩溃
5. derive_file_type 值域 {report,chapter,truth,decisions} ↔ gates/cli G2 分支：全覆盖
6. deps.json t2-phases 键集（prerequisites/expected_outputs/g4_checker）↔ phase_runner/scoring/check_gate_markers 读取：匹配（实测 shape dump）
7. fail()/passed() 信封键（gate/status/timestamp/checks/blocked_action/must_fix）↔ phase_runner run_gate 消费：匹配；write_gate_marker 仅 PASS 落盘 ↔ 读方存在性检查：语义一致

**(b) 数值边界与默认值链**——除零/空集/越界/类型混入/单源：
- 除零：compute_score total_weight==0 静默早退（**F133**）；check_scorer_agreement/flag_score_collapse 无除零面
- 空维度：dims=[] → final 0 无诊断（**F133**，与 F104 同向）
- 越界输入：NaN/bool 穿透 validate（**F132**）；Infinity 正确拒绝
- 输出越界：负权重 → final 120（**F133**）；classify 对 >100 输入无终检
- 阈值单源：75/60 裸数字（**F134**）；G3.2 回退 90（Z4 F411 已登记）
- 默认链：load_applicability 缺格默认 Yes（**F137**）；gate_markers_verified 旗标即真值（**F136**）；G5.1 `rdata.get("final_score", rdata.get("score", 0))` 双层默认 0——对 F458 场景静默按 0 分处理（无告警），属 F458 影响面
- chapter 边界：int() 无守卫崩溃（**F135**）；`chapter or 0` 将 0/None 同义（初审已注，维持不改级）

**覆盖完整性**: 14/14 清单文件 fresh 重读（含 py.typed 空文件确认）；r1"14/14 覆盖声明"复核属实。

## 附：验证命令与产物索引（均在 /tmp/z1r2/，仓库零写入）

- marker 错配（F129/F131）: check_gate_markers 三 test_type × t3-rubric；`python -m shenbi.scoring <worldbuilding-rubric> <scores> --test-type bug-hunt --round-dir /tmp/z1r2/round --subagent` → exit 3
- G3.2 假 FAIL（F130）: 真实 scoring 输出（final_score 95.0）落盘规范名 → `gate_G3('using-shenbi','generative',round)` → FAIL `G3.2:using-shenbi-generative-scores.json`
- 数值边界（F132/F133）: NaN/bool/负权重/零维度四类 scores.json × `python -m shenbi.scoring`（输出原文摘录见各 finding）
- argv 面（F123 复跑/F135）: `phase_runner start --round-dir R` → `--round-dir.json` 落盘；`--chapter abc` → ValueError traceback
- F124 复跑: skills_done state + malformed scores → JSONDecodeError traceback
- 全量扫描: 82 rubric applicability 计数（62/44/18）；44 表头 uniq；dead-symbol greps（7 异常类、scoring_bridge、error_guidance/recovery、SHENBI_SUBAGENT_TIMEOUT）
- /tmp/z1r2/ 保留全部 probe 产物供三方可复核
