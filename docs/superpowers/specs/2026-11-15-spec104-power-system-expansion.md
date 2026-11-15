# Spec #104 · 力量体系卷界扩容（power-system-expansion）：power_system.md 双区化（演进台账 keyed append）、TRIGGER_STEPS 卷界插步、G4 expand 四检查（前层不可变/单调性/编年锚定/钩子可达）

**日期**：2026-11-15｜ **系列**：写作工艺批（authoring-craft）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**动机证据**：`skills/shenbi-power-system/SKILL.md:15-17`（updates `mode: create_or_overwrite`——**整文件覆写**：扩容=全量重写历史层=一次幻觉即 retcon 全书设定）；`src/shenbi/pipeline/triggers.py:277-309`（卷界扩容群五技能 character/faction/location/relationship/plot-thread + genre-config 更新——**无 power-system/worldbuilding**：力量天花板 genesis 写死后无合法升级通道，group-factual D2 只审计「不超天花板」却无正向步骤「升天花板」）；`skills/shenbi-review-group-factual/SKILL.md:12-17`（字段级读 4 节锚点：力量天花板/代价机制/跨级战斗参考/能力边界——**双区化必须保此 4 节结构不变**，消费面零扰动）；`skills/shenbi-power-system/SKILL.md:64`（铁律 6 编年锚定 volume_map 对照——P3 检查的程序化基础现成）；G1.4 `.bak` 快照（`derive_backup_skills`）+G2.11 truth-diff 对账先例——P1 检查机制复用；outline 账本 keyed 写同构（`dispatch_helper.py` `_KEYED_OUTLINE_TARGETS` + `check_new_volume_anchor` 落盘前拒收）；`docs/framework/invariants.md` 13 维普查表**无世界规则/力量行**——「改表即改 lint」：新 check id 族须同批登记（挂靠行或新行，plan 期定）。

**触及的不变量维度**：无现有维度行（世界规则/力量面现无普查行——T3 含 invariants.md 登记义务：新 check id 族 G4.ps.* 同批入表，形态 plan 期定）

---

## 0. 根因

**写模式锁死 + 触发面缺步**：`create_or_overwrite` 使任何扩容必然全量重写（retcon 风险），TRIGGER_STEPS 卷界扩容群不含力量体系——双缺共同导致：千万字多卷架构的**换挡机制缺席**（新层/新位面/换地图/揭更深真相无通道，硬写撞 group-factual 天花板审计，retcon 撞事实守恒）。附带发现：「主要人物阶位」表唯一写者是 genesis 跑一次的 power-system 技能——卷内阶位变化无刷新步（消费面分析：group-factual 4 字段读不含阶位表，滞后可容忍，但卷界必须有刷新）。

**用户裁定（2026-11-15）**：**不考虑在飞项目**——本 spec 不含 backfill/迁移工具，contract-upgrade 纪律走「显式声明」路径：既有运行工件的 power_system.md 为单区形态，新 expand 步对其运行时 G4 判非双区 FAIL 并附结构转换指引文案；新项目 genesis 起即双区。

**备选案已评估并否决**：「整档重发+审计 diff」——LLM 整档重写 49K 级文件已在 settle 增量契约史（spec #21/#99）中反复证伪（丢行/漂移），keyed 增量是既定架构方向；「把 power_system 并入 book_spine 卷界滚动审」——混载波频错误的层（书脊=叙事层，力量=世界规则层，写者/读者/审计面全不同）。

## 1. 任务分解

### T1 · 数据面双区化（消费面零扰动）
- 输出格式改双区：**前部【现行生效区】**（等级表/进阶规则/能力边界/代价机制/力量天花板/跨级战斗参考——group-factual 4 字段锚点节名与层级**原样**）+ **后部【演进台账区】**（`## 演进台账` key=volume 的层记录表：卷号/生效区间/变更类型 + `### 卷N层` 详情节：新阶/新位面/新分支/重解释声明）；
- contract 写模式改造：genesis 首写保留整建语义；expand 走 keyed append/upsert（`_KEYED_OUTLINE_TARGETS` 机制同构——写模式细化 init/expand 两契约面，plan 期定形）；
- G4.ps 结构校验双区分支（genesis/expand 共用结构面）；「主要人物阶位」表刷新并入 expand 步（读 current_state 尾窗重算）。

**判据**：G4 红测（单区旧形态→FAIL+转换指引文案）；**消费面零扰动红测**：group-factual extractor 对双区文件的 4 字段切片输出与单区基线**逐字节一致**（fixture 快照测试）。

### T2 · 触发面插步 + expand 上下文构造
- TRIGGER_STEPS 卷界扩容群插步（五技能后、genre-config 更新前——先看本卷成色再决定扩什么，现有顺序天然合理）：
  `TriggerStep(skill="shenbi-power-system", mode="expand", output_path="world/power_system.md", category="volume_boundary")`；
- expand prompt 框架构造上下文：现有层全文／本卷实际力量高度（current_state 尾窗+主角 character_matrix 行）／下一卷 volume_map 节点（战力/换图节点）／pending_hooks 力量类母钩（hooks_overview 或 hooks_inventory_scoped extractor——plan 期定）。

**判据**：TRIGGER_STEPS 含 expand 步；演练（fixture 测试项目）：卷界触发→前部 diff=0、台账新增一层、阶位表刷新生效。

### T3 · 门禁面：G4.ps.expand 四检查 + 检查点摘要 + 普查表登记
- **P1 前层不可变**：现行生效区+既有层节 vs 派发前快照**逐字节一致**（G1.4 `.bak` 机制复用）；
- **P2 单调性**：新层要么纯增量（不改旧阶定义），要么带**重解释声明**（旧规则=新规则的下位特例+兼容论证段——只许重解释不许改史）；
- **P3 编年锚定**：新层章号里程碑对 volume_map 下一卷节点逐条对表（铁律 6 程序化）；
- **P4 钩子可达**：声明依赖力量升级的 TRIGGERED 钩兑现窗口在新层下仍可达（pending_hooks 数据面）；
- VOLUME_BOUNDARY 检查点 context 带本卷力量层 diff 摘要（triggers.py:763-775 set_checkpoint context 面）——**人审是重解释的最终闸**；
- invariants.md 登记义务：G4.ps.* check id 族同批入普查表（「改表即改 lint」规约）。

**判据**：四检查各自红绿测试（改前层一字节→P1 FAIL／锚不上 volume_map→P3 FAIL／重解释缺声明→P2 FAIL／TRIGGERED 钩不可达→P4 FAIL）。

**明确不建**：重解释的**全史回放检验**——价值门预答：一次性校验不建全章回放；兜底=次卷首章 group-factual 审计天然携新层上下文（报矛盾走既有 revision/escalation 回路）+卷界人审终闸。

## 2. 验收
1. T1-T3 判据全绿；
2. 端到端演练：fixture 测试项目 genesis→手工卷界→expand 全绿（前部 diff=0/台账一层/四检查过/阶位表刷新）；
3. 消费面切片逐字节一致（T1 红测）；
4. T1 生成测试 ≥94（新技能 expand 产物质量：台账层完整性/锚定对表）。

## 3. 风险
- expand 派发写坏前部 → P1 字节对账硬拦（红测即守门）；
- **重解释自由度滥用** → 声明协议+卷界人审终闸+次卷审计兜底三层；
- 在飞项目不兼容面 → 用户裁定显式声明（:0 节），FAIL 文案附转换指引非静默破坏；
- 新 check id 未登记普查表 → 「改表即改 lint」同批义务（T3 内置）；
- 与批次 A 共享文件面：triggers.py 不在批次 A 共享表内，冲突面低；`gates/g4/` 触及新文件为主。
