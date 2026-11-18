# Spec #93 · 阈值权威化（threshold-authority）：对账 lint 读执法器、散文↔门裕度入 docs、小型契约漂移点清偿

**日期**：2026-11-01（r2 修订 2026-11-02：带宽常量当前不存在须先提取；裕度声明改入 docs 不动 SKILL.md 散文——束4 验收后窗口的 prompt 行为红线；r2.2 全量对抗式审计修订——T1b 判定式改包含、T1c `--strict` 须新写、T5 parser 归属更正）｜ **r3 修订 2026-11-19**（价值门驳斥复核驱动：T2 疲劳词半边前提失真拆出 **T6 键形接线修复**（门-契约键形断裂实证）；T1b 吸收 keyword 必填硬化；验收补 lint 测试重写义务；全部行号刷新至 HEAD bdb1b3a3；④⑤ 预答栏补栏）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r3 · Revised 2026-11-19） ｜ **优先级**：🟠 P1
**动机证据**（行号=HEAD bdb1b3a3 亲验）：`pacing_design.py:51-56` 内联 `15 <= const <= 40`（无常量可读）；`threshold_allowlist.json` 4 条 entry 各带手拷 `bounds: [15,40]`；SKILL.md 转折词 1/3000 ×5 处（:92-94/:108/:185）vs 门执行 1/1000（`chapter_drafting.py:931/:943`）；**r3 新增**：疲劳词门读 `gc.get("fatigue_words")` snake 顶层列表（`chapter_drafting.py:970`）而技能契约写 camel 嵌套 `fatigueWords:{禁用,慎用,替换建议}`（`genre_config.py:50` alias；fixture `tests/fixtures/genre-config-example.json` 顶层仅 camel 键）且 `read_genre_config` 返回**原始 json**（`gates/shared.py:731-746`，无模型归一化）→ 门对真实技能产物**恒回退 FATIGUE_BASE**（`gates/shared.py:873` 27 词平面列表）；唯一「证明」门读配置的测试 `test_chapter_drafting_detect.py:13` 手工注入真实技能永不写的 snake 形状。

**触及的不变量维度**：情绪节奏（弱关联——pacing 域阈值声明单源化，不新增门检）；r3 增：疲劳词门输入权威（门行为修复面）

**价值门预答栏（r3 补栏，2026-11-19 五问实测）**：
- **④ 博弈路径**：已测 10 条（详见 progress.md 驳斥复核）。**通**=keyword 缺省→错列静默校验（本版吸收：T1b keyword 必填）；TREND_COLUMNS 后新消费者硬编码无守卫（本版登记：§3 方向登记）；疲劳词键形断裂（本版吸收：T6）。**断**=一行多 range（keyword 锚定挡住）/ tools→src import（lint_private_imports 只扫 tests/，check_severity_vocab.py:18 先例）/ strict 五 FAIL 面 / T3 后无第三处手拷（全仓 grep 双源+数据表键）/ T4 无额外 stale 层 / SKILL 表格改版 fail-closed / 改散文对齐（spec 明令禁止）
- **⑤ 候选机制**：`config/thresholds.py`（自述「quality thresholds 单源」）——**评估不采纳**于 T1a：[15,40] 带仅 pacing 契约 validator 执法+lint 读两消费者，非跨消费者质量阈（resonance floor 类）；contracts/skills/pacing_design.py 自含更内聚，contracts→config 无环但没必要。gates/shared.py band 元组命名先例（:64-65）供 T1a 命名参照。lint_chapter_num_single_source.py（#89 AST 单源守卫）=TREND 守卫可克隆体→§3 登记。trend 列名清单现状=review-resonance SKILL.md 表头散文+writer docstring（TREND_COLUMNS 将是第一份机器可读清单）

---

## 0. 根因

**对账器结构上抓不住它存在的目的**：lint_threshold_reconciliation 自认「parsing checker constants is out of scope」（:5-8 与 :36-38）且「always exits 0 (WARN-only)」（:81/:99）——比较 SKILL.md ↔ allowlist JSON，而 allowlist 的 bounds 是**第三份手拷**（4 条 entry × [15,40]）；真执法器只验文件存在（:44-48）。改 checker 为 [18,45]：无红无 WARN——进了 `just lint`（justfile:53，经 `just check` :22-24）却无条件放行。判定式 `d_hi < lo or d_lo > hi`（:67）是**相交**而非包含——SKILL 写 `10-20` 与硬带 [15,40] 相交即放行，带内漂移结构性漏检。

**r2 事实校正（r3 维持）**：执法器当前**没有可读常量**（内联字面量），故「lint import 读常量」需先提取（T1a）。SKILL「目标比值（按卷型）」四档（15-25/30-40/15-25/15-25，SKILL.md:174-177）落在硬失败带 [15,40] 内——allowlist 4 条 bounds 相同**是设计而非漂移**，本 spec 不指控其为复写错误，只去掉「bounds 作为第三源」。

**散文↔门值分歧（1/3000 vs 1/1000）**：门侧注释自认「relaxed for automated gen」（:931），散文侧 5 处仍教 1/3000 为铁律。**若为「提示比门严」的故意设计则完全合理**（prompt 工程），问题仅是**决策未成文**。修法=r2 改入文档，**不改 SKILL.md 散文**（SKILL.md 指令改动会改变 LLM 行为——束4 验收后窗口 prompt 行为红线维持）。

**r3 新增根因 · 疲劳词门-契约键形断裂**：门的意图是读 genre-config 的疲劳词表（`_check_fatigue` docstring 自认「genre-config 阈」，:967），但 `gc.get("fatigue_words", FATIGUE_BASE)`（:970）读的是 snake_case 顶层**列表**形状，而 genre-config 技能契约定义的是 camelCase **嵌套对象** `fatigueWords:{禁用:[],慎用:[],替换建议:{}}`（genre_config.py:50 alias + SKILL.md:91-93 模板 + fixture 实证）——`read_genre_config` 返回原始 json 不经模型归一化（shared.py:741-744），真实技能产物下该键**永不存在**，门恒用内置 FATIGUE_BASE 计数。这不是裕度而是**断线**：r2.2 拟成文的「疲劳词 ≤3（原）vs ≤8（门）」对照在现状下无数据流支撑——两侧数的是不同的词表（慎用报警线 vs 内置基表）。

## 1. 任务分解

### T1 · 对账器读执法器（含前置常量提取）
- **T1a**：`contracts/skills/pacing_design.py` 提取 `CONSTELLATION_HARD_BAND: tuple[int,int] = (15, 40)`（命名对齐 gates/shared.py band 元组先例 :64-65），validator 改用它（行为零变化，红测：现值通过/越界失败照旧）。落点裁决已预答（预答栏 ⑤）：不落 config/thresholds.py；
- **T1b**：lint_threshold_reconciliation 改 `import` 该模块读常量（tools 可 import src——check_severity_vocab.py:18 / facts_backfill.py:27-30 先例；lint_private_imports 只扫 tests/ 不拦 tools）；**删 allowlist 的 `bounds` 字段**（deletion test：删之严格增收信息保真）；判定式从相交改包含 **`d_lo >= lo and d_hi <= hi`**（否则只是把第三源换成第二源，结构性漏检照旧）；**r3 硬化：`keyword` 升必填**——缺 keyword 的 entry 在 strict 下 FAIL、非 strict 下 WARN（博弈路径 ②实测：缺 keyword 时 scope=整行，RANGE_RE 抓第一个 range，行首 range 恰在带内则静默校验错列）；
- **T1c**：新写 `--strict` 模式（对照 lint_key_reconciliation --strict 先例 justfile:44；justfile:33 已有本 spec 预留钩注释）并接线进 `just lint`；strict 的 FAIL 面=五面全保留：file_missing / checker_missing / keyword_missing（r3 新增）/ no_range_found / drift-vs-constant（越出常量带）。**测试重写义务（r3）**：`tests/unit/tools/test_lint_threshold_reconciliation.py` 现锁 WARN-only exit 0 + bounds 形状（:23-:72）——同批重写为 strict 语义 + 无 bounds schema；
- 红测：临时改常量为 (18,45) → strict 红（回滚）；SKILL 表行注入 50-60 → strict 红（50>40）。

### T2 · 裕度决策成文（**docs only**；r3 内容重写）
- `docs/framework/gates.md` 增「散文↔门裕度」节，**两行决策+出处**：
  - 转折词：散文预算 1/3000（chapter-drafting SKILL ×5 处）/ 门限 1/1000（chapter_drafting.py:943 `max(5, wc//1000)`）——3× 自动化裕度，理由=自动化生成文本转折词天然偏多（门注释 :931 自认）；
  - 疲劳词（T6 接线后的真实语义）：散文面=禁用词出现即报错+慎用词每章 >3 报警（genre-config SKILL.md:168-186）/ 门面=禁用∪慎用命中 >8 FAIL（chapter_drafting.py:972）——门对禁用词同样给了自动化裕度（散文零容忍 vs 门 ≤8），与转折词同一裕度模式；
- g4 侧注释回指（`chapter_drafting.py:931` 转折词注释与 `:967` 疲劳词 docstring 各加「裕度裁定见 docs/framework/gates.md §散文↔门裕度」）；
- **不改任何 SKILL.md 指令散文**（豁免：纯注释性 docs）；若用户裁定应把散文也对齐，另立内容批（属 prompt 变更）。

### T3 · pricing 模型契约 import 化
`cost/pricing.py:16-32` 与 `dispatch_helper.py:94-101` 的 env 名 + 默认模型双源（pricing→dispatch_helper 单向指针注释 pricing.py:31 小写 `must match`）→ 常量单源（落 `shenbi/config/` 中性叶，cost 与 pipeline 双向 import 均可；或 dispatch_helper 从 pricing import 一次倒置——**r3 预答倾向后者**：dispatch_helper 已 import cost.ledger/estimate（:56/:3253/:3751），pipeline→cost 方向已确立且 pricing 仅 import stdlib 无环；plan 择一，判据=无环）。
**判据**：`grep -rn "must match shenbi.pipeline.dispatch_helper" src/shenbi/cost/` = 0（注释消除后）；宽式 `must match` 另有 dispatch_helper.py:963/:3137 两处无关文案，验收 grep 须锚定全串非宽式。

### T4 · executor 派生集缓存失效
`dispatcher/executor.py:30-59` `_truth_files_cache`（:33）/`_decisions_files_cache`（:49）进程期冻结，与 loader.load_registry 的 (mtime_ns, size) stat 键缓存契约（loader.py:156-183）相悖——长生命周期进程中途编辑 truth-files.yaml 时契约验新值而 file_type 派生用旧值。改：派生集按同一 stat 键失效（或每 dispatch 调 bootstrap_registry——其无自有缓存，registry.py:17-37 直接委托 load_registry）。实际暴露面=phase_runner 长进程（:240 import derive_file_type）+运行中改 repo YAML，窄但真实（驳斥复核低危标注维持）。
**红测**：改 truth-files.yaml 后同进程再派发，file_type 集已刷新。

### T5 · trend 表列契约单源（三个位置消费者）
- **writer**：`chapter_loop.py:2877-2906` `build_resonance_trend_row`（9 列硬编码；docstring 自认 ">=7 cells and reads cells[6]"）；
- **位置解析者**：`orchestration/escalation_bridge.py:15-22`（`len(cells)>=7`、`float(cells[6])`）；
- **第三处**：`pipeline/confidence_calibration.py:116/:128` `patch_markdown_table_cell(..., "chapter", 7, calibrated)` 硬编码 confidence=第 7 列。
（r3 复核注：compute_drift.py:164-208 与 resonance_policy.py:252-285 均表头名驱动，不受列序影响——spec 三消费者点名准确。）
**处置**：共享 `TREND_COLUMNS`（含 `confidence`）常量——**落 `pipeline/_shared` 或 `orchestration/`，不落 compute_drift**（语义不需要+将来 gate 用它会造成 gates→skill_utils 环）；writer/escalation_bridge/confidence_calibration 三处 import + writer docstring 改函数名引用；**往返 property 测试必须打 escalation_bridge**（writer→bridge 列位不变）；红测：重排列序断言 bridge 读出对应字段。

### T6 · 疲劳词门-契约键形接线（**r3 新增，代码修复**）
`chapter_drafting.py:970` `gc.get("fatigue_words", FATIGUE_BASE)` 改读契约真实形状：camelCase 顶层 `fatigueWords` 嵌套对象，计数词表=**禁用∪慎用并集**（保持门的「疲劳词总量」语义与 >8 FAIL 阈不变——最小行为变更：现状对真实配置产物=仅 FATIGUE_BASE 计数，修复后=配置词表接管、FATIGUE_BASE 仅作缺配置回退）；非列表成员防御（形状异常→回退基表+WARN 日志，不炸门）。
**测试重写义务**：`test_chapter_drafting_detect.py:13` 现以手工注入 `gc["fatigue_words"]=["咣当"]` snake 形状证「门读配置」——重写为真实 fixture 形状（genre-config-example.json 原样 + 写章节命中其 禁用 词 >8 次）。**红测**：fixture 禁用词「心中暗道」×9 → 现状 PASS（词不在 FATIGUE_BASE，回退计数 0 命中）→ 修复后 FAIL。
gates.md 裕度节疲劳词条目以 T6 后语义为准（T2 已预写）。

## 2. 验收

1. T1a 常量化后现存 pacing 测试全绿（行为零变化）；T1b 删 bounds 后 lint 仍能判 SKILL 数字越界（红测注入 50%）；keyword 缺省 entry 在 strict 下 FAIL；T1c strict 后 `just lint` 中该 lint FAIL 态可触发（红测注入越界值/临时改常量）；`test_lint_threshold_reconciliation.py` 重写为 strict 语义全绿；
2. gates.md 裕度节落盘（转折词+疲劳词两行）+ g4 两处注释回指（grep 双向锚）；
3. T3 判据 grep=0；T4 红测绿（同进程改 YAML 后派生集刷新）；T5 三消费者 import 共享常量+property 往返打 escalation_bridge 绿；
4. **T6 红绿**：真实 fixture 形状禁用词 >8 次命中 → FAIL（修复前 PASS）；`test_chapter_drafting_detect.py` 无手工 snake 注入；
5. `just check` exit 0。

## 3. 方向登记（不施工）

- frontmatter `gate_thresholds` 块（g4 读之、SKILL 散文引用之——「契约常量供门与散文共同引用」模式已由 gates/shared.py:64-65 场景字数带元组先例证实；r2.2 原引 :274 已随 #87/#89 拆分漂移）：作为「值域进契约」的长期方向登记，待第三个散文↔门值分歧出现时再立项（两个先例不值得抽象——YAGNI 线）；
- **TREND_COLUMNS AST 单源守卫**（r3 登记）：克隆 lint_chapter_num_single_source.py（#89 先例）判 `cells[6]`/列字面量 7 唯一合法点=TREND_COLUMNS——待第二个硬编码复现事件再立项（博弈路径 ⑦实测通，接受残留）。
