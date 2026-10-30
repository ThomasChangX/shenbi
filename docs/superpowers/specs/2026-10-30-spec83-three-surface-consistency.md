# Spec #83 · 三面一致性之网（three-surface-consistency）：正文/声明/truth/大纲的对账、联动与回灌

**日期**：2026-10-30 ｜ **系列**：卷一复盘→卷二防复发（与 #82 retention-engine-net / #84 vol1-repair-vol2-launch 配对）
**状态**：Active ｜ **优先级**：🟠 P1（正确性基建——P1×4 全部由此族产生；#80 管不变量本身，本 spec 管四面之间的搬运）
**动机证据**：G3.4 缺陷清单 P1×4 + 盲审「声明 vs 实际（货不对板清单）」+ vol1-ledger 运行史（identity 门/类别漂移/F6 族）+ longitudinal fail-closed 假阴性
**修订**：r2 2026-10-30 高精度审核修订——T2 stale 写入者定为框架回调（不动修订技能契约，免 contract-upgrade backfill 义务）；T4 打摆切换取数路径定为 DISPATCH `failure_class`＋RETRY/loop_id 聚合（不从反馈文本判读）；T6 计数锚并入 F17 `cd.counter` 提取器扩族（不建第二套 prose 计数器）；T5 与 #82 T0 声明快照层同点位同批；新增铁律 L-D（新门 shadow 纪律，与 #82 L-D 配对）

**触及的不变量维度**：恒等 identity（1）、时间（2）、持有与经手 props（4）、枚举计数 counters（5）、承诺与债务（7）、叙事纪律（10）

---

## 0. 背景与根因

系统里有四个「事实面」：**正文**（chapters/*.md）、**声明**（PRE/POST/META 块 + plans 备忘）、**truth**（facts/registry/hooks/timeline）、**大纲**（volume_map 节点）。卷一实证的每一个 P1 与大半 P2，都是这四面之一与其余面脱钩的实例：

| 脱钩 | 卷一实证 |
|------|---------|
| 正文 ↔ 声明 | ch28 正文「名数四改五」vs 备忘声明 4+0（P1-1）；ch1 POST 引句「却不知道明天城就破了」正文不存在；ch6 POST 金句「册子认得。」vs 正文「册子认得人」；C16 反思句/C17 转折词 POST 声明 0 而词法命中；scene_hook 声明漂移 11 行（R1/R2 改文未同步） |
| 正文 ↔ truth | ch26:L26 章首余额 103（付前应 113）；ch30 三十文脚钱蒸发；ch35/36 骨哨来历「渡口那夜」vs ch2 城破门洞 canon（P1-3）且**错误已扩散进 prop_registry**（「按老驼渡口那夜教的结法」） |
| truth ↔ 大纲 | 双哨 canon（ch20 运行期 emergent）从未回灌——卷纲 L88「四件东西第一次同匣」清单只一把哨，ch35 plan 忠实执行过时清单（P1-2 的真正根因链）；卷纲 L105「老驼临终塞给他」vs 实际 ch2 授哨；卷纲 L21「第36章后附渡鸦局档案卡」被 ch36 PRE 禁忌「不碰渡鸦局档案卡」静默弃约；五条欠账（ch36 运行期立账）不在种子还账进度表首批六行内 |
| truth ↔ 生成指标 | pipeline-state chapter_states 18 个 follower 章恒 `pending` + resonance 行缺失 → longitudinal fail-closed 假阴性（ch2/4/6…全部误报） |

**根因裁定**：四面之间**没有对账器、没有联动器、没有回灌路径**——

1. 门只校验「声明面内部一致」（memo 声明行 ↔ facts；plan 钩声明 ↔ 场景末行），从不把声明与**正文本体**做语义比对（正文本体只有词法级：裸名/token/字数）；
2. 修订步（constrained-regenerate）改正文后**没有联动刷新声明面**的机制——钩行/物象行/POST 引句全部手工同步，漏同步即漂移（scene_hook 11 行全属此类）；
3. 运行期 canon 演化（修复轮发明、settle 双写）单向流入 truth，**大纲节点文本运行中只读**且是规划的唯一锚（「不得越过节点另起炉灶」）——emergent canon 不回灌 = 后续章以过时锚规划；
4. 束（bundle）的完成语义只对 leader 章写全——follower 章的 status/resonance/ledger 行半完成（F6 同族，卷一 18/36 章中招）；
5. POST 自检块是**模型自填的**，引用句可以是正文不存在的话——假声明会随 settle 摄取回流 truth（盲审 B 警告：「自检块声明失真比没有自检更危险，它会向上游 truth 文件回流假数据」）。

**铁律 L-C**：对账器只对**结构化可判定**的子集动手（引句逐字存在/数值锚/清单枚举），语义级留给评审——不造 NLP 假象（#82 同纪律）。

**铁律 L-D（r2 新增，新门 shadow 纪律）**：本 spec 与 #82 全部新增 FAIL 门带 `shadow` 配置位，卷二首束（ch37-38）WARN 试运行，零误伤后升 FAIL——#80 前向门五连校准（commit 8001ed3f）实录教训：实弹误报回修的成本高于一次 shadow 轮。

---

## 1. T1 · POST/PRE 引句 verbatim 门（声明↔正文）

- `G4.cd` 增 `quote_verbatim`：META 块（PRE_WRITE_CHECK/POST_WRITE_SELF_CHECK）内所有「」/"" 引号句（≥6 字，过滤通用短语白名单如切口/口诀类已在正文的），必须在同章正文中逐字出现（含场景分隔与 META 剥离后）——不存在 → FAIL（修复者：drafting——要么改正文要么改声明）；
- POST 声明-门实测交叉：POST 报「转折词 0」「无反思句: 是」而 G4.cd 词法检查命中 ≥1 → FAIL（假自检直接红）；
- 字数行虚假精度（报 3795 实 3700）复用 G2.7 助手复算——差 >2% → WARN（卷一 C18 实证）。
- **共基声明（r2）**：本任务的 verbatim 判定器是 #82 T1「引句锚定」的共用零件（章尾张力拍声明的引句回查走同一判定器）——两 spec 在此拼接，勿各造一份。
- **TDD**：ch1/ch6 实证句作红测夹具（G0.9 真实输出拷贝 → tests/fixtures/）。

## 2. T2 · revision→声明联动（步骤契约）

- `chapter_revision` 完成后自动把同章 staging 的 plan 钩声明行/PRE 物象行/POST 引句标记 stale（`declaration_stale` 状态写入 manifest），`state-settling` 摄取前检查 stale 未清 → FAIL——逼「修订后重跑 hook_match 或手工同步」成为路径而非美德；
- **stale 写入者=框架回调（r2 定案）**：`chapter_loop` 修订完成处写 manifest——修订技能的 writes/updates 契约面不扩（现契约 writes 仅 state_snapshot-pre-rev/revision-decisions.json、updates 仅 chapters/chapter-N.md，shenbi-chapter-revision/SKILL.md:6-19），免 contract-upgrade backfill 义务（AGENTS.md 纪律）；
- 联动面最小化：只挂「scene_hook / 物象 / POST 引句」三类（卷一漂移全部落此三类；timeline 行归 T5 工具顺带对账）。
- **TDD**：修订改末行 → stale 标记升起 → settle 拒收 → 重跑 hook_match → 清除。集成测试走 `tests/integration/` 束链路径。

## 3. T3 · canon 回灌对账（truth↔大纲）

- **Create** `tools/lint_outline_truth_drift.py`（`python tools/lint_outline_truth_drift.py <dir> [--volume N]`）：
  - 物象清单对账：卷纲节点行枚举的道具集合（如「四件：红纸包、骨哨、《鉴录》、私账」）vs `truth/facts/props.json` 当前持有集——**持有物缺席节点清单** → finding（P1-2 类：第二把哨在 truth 持有、不在节点清单）；
  - 来历短语对账：prop_registry 事件行的授物地点/场景短语 vs 卷纲对应描述（「临终」vs 实际存活）——词级重叠 <阈值 → finding（P1-3 种子面）；
  - 承诺件对账：卷纲「金句出场点/卷末彩蛋/梗位」逐项 grep 全卷正文——缺件 → finding（渡鸦局档案卡实证）；
  - 欠账对账：正文书立的欠条/誓言行（「欠」「还之日」句式）vs 种子还账进度表行——运行期新账不在排期 → finding。
- **运行点**：每 6 章束 settle 后 + 卷界前驱动侧必跑；finding → 人工裁定「改大纲 or 标 canon 附件」（volume_map 节点行就地更新或行内 `※canon-vN` 引注，双择一，不许悬空）。
- **回填补丁**（随 #84 T0 执行）：卷一四件清单/来历/档案卡/五条欠账四处一次性回灌。
- **TDD**：卷一四实证作夹具单测（真项目片段拷贝）。

## 4. T4 · 增量生成模式硬化（settle + drafting 全量重写病理）

settle 全量重写是声明漂移与 content_dropped 三连败的共同根因（probe29 老病，卷一 ch16/23/25/29-30 五次复发；r2 核实：G4.ss 现无任何 diff 面积类检查，最接近的 G2.11 只记删除行）：

- `G4.ss` 增 `incremental_only`：staged 既有行文件 diff 面积 >50%（既有行删除/重写占比）→ FAIL，反馈定点单行编辑指令（类别词表/粗体式格式枚举随反馈附上——「册上正字」「YAML 式」两次手工修的教训）；
- `shenbi-state-settling` SKILL 增铁律行（#80 铁律 0 同型）：「既有表行只许单行编辑/追加，禁止整表重排」；
- drafting 打摆切换（**r2 明确取数路径**）：同 (skill, chapter) 连续 ≥4 次全档重写型失败（长度/结构族）→ 反馈模板自动切「定点扩写」模式（明确段落锚 + 目标字数差 + 逐字 token 白名单），不再发整档约束重述。计数取数：**DISPATCH 事件既有 `failure_class` 字段**（dispatch_helper.py:3174-3202）＋ RETRY/loop_id 聚合（observe_report.py:58 已有 per-(skill,chapter) max loop_id 表）——**不从反馈文本判读**「重写型 vs 定点型」；若 failure_class 粒度未区分长度/结构族，先扩该枚举再计数（前置小任务）。卷一战术沉淀（「打摆>5 轮切手工」）的代码化，阈值 4 给自动路径留裕量。
- **TDD**：diff 面积门红测；反馈路由切换单测（4 次计数器 + 模板选择，计数来源=failure_class 聚合）。

## 5. T5 · follower 完成语义 + 指标面补全（＋声明快照同点位）

- `_complete_chapter`（chapter_loop）束感知完成时**批量写全 bundle 成员**：`chapter_states[str(ch)].status="complete"` 全员 + per-chapter 检查点已升（既有）——修 18/18 假 pending（r2 核实：status 写点仅 leader 一处 chapter_loop.py:2055，游标直接跳过 follower :2081）；
- **同点位同批（r2）**：与 #82 T0 在同一改动面加 `chapter_states[n].declared` 快照写入（一个 PR 两件事，避免两次触碰同函数）；
- resonance 行：follower 章由束级评分拆行或显式 `bundle-merged` 标记（longitudinal fail-closed 读到标记跳过单章断言、束级断言替代）——不再静默缺行；
- 纵向采集表自动回填：`tools/report_longitudinal.py` 增 `--emit-ledger-rows N M` 从 trace/cost 生成台账缺行草稿（ch5-10/19-24 挂账清偿工具化）。
- **TDD**：双章束完成后两章 status 均 complete；resonance 标记路径单测；快照写入断言（详见 #82 T0）。

## 6. T6 · 正文本体数字锚（正文↔truth 的最小可判定集）

结构化可判定的三个数值不变量（L-C 铁律内的）：

- **余额锚 `balance_value_drift`**（G4.cd，WARN→束级 FAIL）：`truth/particle_ledger.md` 现值（一百零三文）数字化后，本章正文出现**同句式异值余额**（「一百一十三文」且本章无对应支出 ops 声明）→ WARN；章首首现余额 ≠ 前章末值 → FAIL（ch26:L26 类）。金额噪声用强锚限定：只认「(一共|还剩|只剩|袋底|余额)[^。]{0,6}N文」句式；
- **计数锚（r2 并轨 F17）**：不另起提取器——「名数[^。]{0,12}」pattern 并入 F17 `cd.counter`（chapter_drafting.py:182-260）的 prose 总数族提取器，作为其扩展面（门 ID 沿用 F17 域；两套 prose 计数提取器并存=维护面翻倍；ch28「五个」漏网实证现行 pattern 族有洞——扩族而非重建）。判定：正文提取值 vs `facts/counters.json` 现值与 memo 声明 N+1 **二者并集外** → FAIL（ch28「四改五」类——#80 F17 三方对账的正文本体补臂）；
- **来历锚（WARN）**：prop_registry 结构化新增 `provenance` 字段（地点+章号，settle 写侧扩一列；r2 核实现状：prop_registry.md 表仅 实体名/当前owner/经手事件 三列，地点与章号只散在散文里）；正文来历句（「(得|授|给|塞)」+道具名+「那夜/那天」）命中地点词 ≠ provenance → WARN（渡口/门洞类）。WARN 起步：词法地点匹配有假阳性，供检查点人工裁决，不自动 FAIL。
- **TDD**：ch28/ch26 实证句红测；金额强锚句式负例（价格句不命中）；扩族后「名数」句式命中正例。

## 7. T7 · 验收口径清偿（挂账项归位）

- **判据 5 声口口径**：`voice_lexicon` 标记字典换声口 token 族（复用 #76 ACCOUNTING_VERBS/自嘲句尾正则思路按角色分桶），五角色 4/5 阈值下可达——tools/regen_accept.py 判据 5 实现面替换 + 挂账节关闭（r2 核实：现实现 check_blind_recognition 4/5 阈值，vol1-ledger.md:75 挂账「签名句命中率 4-33% 不可达」，工具无豁免分支）；
- **#80 前向门回放口径裁定**：manifest 门行对已生成章不回放（文档化入 docs/framework/gates.md #80 节 + regen_accept 判据 2b 读法注释——卷一 10-29 记录已剥离，卷二按新口径执行；r2 核实：gates.md 现无 #80 节，口径只在 regen-vol1-continue-prompt.md:83 挂账）；
- **声明面漂移清单**：scene_hook 11 行 + ch10 voice_density + ch11 无 META 块——`tools/lint_declaration_drift.py`（或并 lint_outline_truth_drift 子命令）一次性对账输出修复清单，随 #84 T0 清偿。
- **TDD**：token 族归属单测；回放口径文档 + 判据读法回归。

## 8. 非目标（防过度工程）

- 不做正文语义级不变量机器判定（矛盾检测交 G3.4/评审——T6 只做数字/清单枚举）；
- 不建大纲双向同步机制（人工裁定改节点 vs canon 附件，工具只报不写）；
- 不追溯回填 ch1-24 的 follower 指标面（历史证据面不动原则；只保证卷二起写全）；
- timeline 陈旧行（ch23 备注类）随 #84 T0 手工清，不造通用 timeline linter。

## 9. 验收（=卷二防复发判据）

1. 全部新门/工具红测→绿 + `just check` exit 0；新 FAIL 门 shadow 位默认 true，首束零误伤后转正；
2. 卷二首束实弹：settle 增量门零误伤、双章 status 全 complete、POST 引句门零 FAIL（首月≥20 章窗口）；
3. 束前 lint_outline_truth_drift 零悬空 finding（或全部裁定归档）；
4. 正文本体数字锚：卷二余额/计数零漂移（WARN 面人工裁决记录在台账）；
5. regen-accept 判据 5 从「口径失配挂账」转绿。
