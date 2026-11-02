# Spec #93 · 阈值权威化（threshold-authority）：对账 lint 读执法器、散文↔门分歧入 docs、小型契约漂移点清偿

**日期**：2026-11-01（r2 修订 2026-11-02：**带宽常量当前不存在**须先提取；裕度声明改入 docs 不动 SKILL.md 散文——卷二开卷前 prompt 行为红线）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2） ｜ **优先级**：🟠 P1
**动机证据**：architecture-review-20261101 #9/#26 卡；亲验：`pacing_design.py:52-56` 的 `15 <= const <= 40` 是 **pydantic validator 内联字面量**（无常量可读）；`threshold_allowlist.json` 4 条 entry 各带手拷 `bounds: [15,40]`；SKILL.md 转折词 1/3000 ×5 处 vs 门执行 1/1000（chapter_drafting.py:732/:754）

**触及的不变量维度**：情绪节奏（弱关联——pacing 域阈值声明单源化，不新增门检）

---

## 0. 根因

**对账器结构上抓不住它存在的目的**：lint_threshold_reconciliation 自认「parsing checker constants is out of scope」（:26-28）且「always exits 0 (WARN-only)」（:99）——比较 SKILL.md ↔ allowlist JSON，而 allowlist 的 bounds 是**第三份手拷**（4 条 entry × [15,40]）；真执法器只验文件存在。改 checker 为 [18,45]：无红无 WARN——进了 `just check` 却无条件放行。

**r2 事实校正**：执法器当前**没有可读常量**（内联字面量），故「lint import 读常量」的前提需先补一步（T1a 提取常量）。另：SKILL 的「目标比值（按卷型）」四档（15-25/30-40/15-25/15-25）落在硬失败带 [15,40] 内——allowlist 4 条 bounds 相同**是设计而非漂移**，本 spec 不指控其为复写错误，只去掉「bounds 作为第三源」。

**散文↔门值分歧（1/3000 vs 1/1000）**：门侧注释自认「relaxed for automated gen」，散文侧 5 处仍教 1/3000 为铁律。**若为「提示比门严」的故意设计则完全合理**（prompt 工程），问题仅是**决策未成文**。修法=r2 改入文档，**不改 SKILL.md 散文**：任何 SKILL.md 指令改动都会改变 LLM 行为，而卷二开卷在即（#84 冻结窗红线）。

## 1. 任务分解

### T1 · 对账器读执法器（含前置常量提取）
- **T1a**：`contracts/skills/pacing_design.py` 提取 `CONSTELLATION_HARD_BAND: tuple[int,int] = (15, 40)`，validator 改用它（行为零变化，红测：现值通过/越界失败照旧）；
- **T1b**：lint_threshold_reconciliation 改 `import` 该模块读常量（tools 可 import src——facts_backfill.py:27-30 先例）；**删 allowlist 的 `bounds` 字段**（deletion test：删之严格增收信息保真）；
- **T1c**：`--strict` 翻转进 `just check`（WARN-only 历史 → FAIL）；
- 红测：临时改常量为 (18,45) → lint 红（回滚）。

### T2 · 裕度决策成文（**docs only**）
- `docs/framework/gates.md` 增「散文↔门裕度」节：记录 转折词 预算 1/3000 / 门限 1/1000（3× 自动化裕度，理由=自动化生成文本转折词天然偏多）、疲劳词 门限 ≤8（原 ≤3）——两行决策 + 出处；
- g4 侧放宽注释补回指（`chapter_drafting.py:732`/`:767` 注释加「裕度裁定见 docs/framework/gates.md §散文↔门裕度」）；
- **不改任何 SKILL.md 指令散文**（豁免：纯注释性 docs）；若用户裁定应把散文也对齐，另立内容批（属 prompt 变更，走 #84 窗口）。

### T3 · pricing 模型契约 import 化
`cost/pricing.py:8-29` 与 `dispatch_helper.py:97-103` 的 env 名 + 默认模型双源（注释互指「MUST match」）→ 常量单源（落 `shenbi/config/` 中性叶，cost 与 pipeline 双向 import 均可；或 dispatch_helper 从 pricing import 一次倒置——plan 择一，判据=无环）。
**判据**：`grep -rn "MUST match\|must match shenbi.pipeline" src/shenbi/cost/ src/shenbi/pipeline/dispatch_helper.py` 零（注释互指消除）。

### T4 · executor 派生集缓存失效
`executor.py:32-59` `_truth_files_cache`/`_decisions_files_cache` 进程期冻结，与 loader.load_registry 的 mtime 键缓存契约（loader.py:166-197）相悖——长生命周期进程中途编辑 truth-files.yaml 时契约验新值而 file_type 派生用旧值。改：派生集按同一 stat 键失效（或每 dispatch 调 bootstrap_registry——C28 后已缓存）。
**红测**：改 truth-files.yaml 后同进程再派发，file_type 集已刷新。

### T5 · trend 表列契约单源
`chapter_loop.py:2690-2721`（writer，docstring 自认 "requires >=7 cells and reads cells[6]"）与 `skill_utils/drift_detection/compute_drift.py:164`（parser）异包 wire 靠 docstring 同步 → 共享 `TREND_COLUMNS` 常量（落 compute_drift，chapter_loop import）+ 往返 property 测试（writer→parser 列位不变；红测：重排列序断言 parser 读出对应字段）。

## 2. 验收

1. T1a 常量化后现存 pacing 测试全绿（行为零变化）；T1b 删 bounds 后 lint 仍能判 SKILL 数字越界（红测注入 50%）；T1c strict 后 just check 中该 lint FAIL 态；
2. gates.md 裕度节落盘 + g4 两处注释回指（grep 双向锚）；
3. T3/T4/T5 三判据各绿；
4. `just check` exit 0。

## 3. 方向登记（不施工）

frontmatter `gate_thresholds` 块（g4 读之、SKILL 散文引用之——genre-config 字数带经 gates/shared.py:274 已证此模式）：作为「值域进契约」的长期方向登记，待第三个散文↔门值分歧出现时再立项（两个先例不值得抽象——YAGNI 线）。
