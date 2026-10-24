# 默认文笔惊艳度（prose-excellence）设计

> **Date:** 2026-10-24 | **Status:** Active | **Severity:** 🔴 P0（用户点名「文笔不够惊艳」；排期用户定稿：本 spec 实现先落地，卷一 v2 全新首跑随后启动并即试点） | **方法:** 方案 B——指令层重锚 + WARN 级确定性闸 + 测量闭环升级 + 自锚定范文环 | **系列:** 文笔层 | **依赖:** 无 | **范围:** `style_seed.py` 模板重写 / `compute_stats.py` 两新指标 / G4.cd 三 WARN / 六份 SKILL 与两份框架文档 / `executor_config.toml` / truth 注册 / 单测

> 2026-10-24 brainstorming 定稿。决策路径：网络调研六位公认文笔派作者（「中原五青」共识 + 树下野狐/江南——起点六人名单与 NGA 纯文笔投票交叉）提炼共性带（长短落差大/意象密度高/煽情克制/对话承载辨识度）→ 本地实证三缺失（星火 ch1 全章最长句仅 31 字、≥25 字句占比 6%——「≥16 字收束长句」伪长句定义压死天花板；比喻只有 ≤2/千字单上限且喻体俗套失控——ch5 达 5.3/千字；金句只有卷纲排期、drafting 无工艺）→ 三问定稿：①**范围 P0-P3 全包**（含破折号框架红线与温度实验）②**风格定位重锚六人共性带**（基带 10-20→12-25，非「增强不换底」）③**排期 = spec 先落地、卷一 v2 即试点**（先 A/B 探针方案否决）→ 三方案对比（A 纯指令层[漂移无闸无对账] / B 指令+WARN 闸+自锚定环 / C 外部范文注入[版权风险 + StoryScope「改风格难掩底层叙事差异」边际收益否决]）用户选定 **方案 B**。
>
> **Revised 2026-10-24**（两轮：阶段 1 驳斥七项 + 阶段 3 设计审查 R1 十一项）：① golden_slot POST 谓词与 §3 模板行对齐且不耦合方括号字面；② 施工面补 `src/shenbi/pipeline/_shared.py`（load_volume_context 增金句母题行提取——extractor 白名单不含该行，只改 SKILL = dead-wire）+ `dispatch_helper.py`（OPTIONAL_READS 增 anchors.md）+ `gates/shared.py`（segment_sentences 迁入 + count_similes 单信源）；③ simile_band 分母改非对白域（分子分母同域）；④ §5.1 节号订正（§6 标点密度）；⑤ §6.1 契约面补 lint-contracts 家族 + just generate 派生物；⑥ §4.2 统计指标目录节同步面；⑦ G4.vo.quote_line 确认无需扩；⑧ surge 计数域补剥 META（strip_narrative_body——防 POST 自检清单喂饱闸）；⑨ anchors 铁律 2 例外条款 + 半操作化选取；⑩ §6.2 数据源改 gate 结果 JSON jq 归集（无现成 WARN 聚合面）；⑪ 温度回退基线钉死数值（$0.18 主判据 + vol1 首跑段实录辅判据）。

## 1. 定位与边界

- 问题定义：现行文风控制面防御完备（防 AI 味五道硬闸 + anti-ai 禁令），但正向文笔资产为零——目标函数只定义「不难看」未定义「好看」。本 spec 交付正向资产层：**句长落差、意象母题、金句工艺**三项进指令层与测量环，可测代理进 WARN 闸。
- 调研依据（存档于本 spec 头部决策路径与调研报告，例证见调研产物）：六位作者共性 = 长短句落差控节奏、画面靠具象名词、对话承载辨识度、煽情克制；反面教训 = 辞藻密度军备竞赛（「只学到辞藻，学不到自嘲」）与烽火式掉书袋在千万字尺度的疲劳风险。
- 本 spec 改**通用默认**（`style_seed.py` 播种模板）与管线工艺；项目级 `style_directives.md` 覆写权归用户（write-if-absent 语义不变）。
- 五道硬闸数值一律不动：转折词密度、AI 标记词、fatigueWords、字数契约、段落下限。唯一红线变更 = 破折号全禁转预算制（§5）。

## 2. P0 — 默认模板 v2（`DEFAULT_STYLE_DIRECTIVES` 重写）

新模板全文（`style_seed.py` 内嵌替换，`seed_style_directives` 的 write-if-absent 语义与幂等不覆写行为不变）：

```markdown
# 文风目标（通用默认模板 v2）

> 本文件由 pipeline-init 播种，可自由修改；删除整文件 = 回退到纯测量画像
> （style_profile 描述「现在是什么」，本文件设定「要什么」）。
> 结构说明与硬闸边界见 `docs/framework/style-directives.md`：转折词密度、
> AI 标记词、fatigueWords、字数契约、段落下限五道硬闸不因本文件松动。

## 节奏与句法

- 叙述句基带：12-25 字/句；对白保持短促（4-12 字/句）
- 长短落差（惊艳主引擎）：每场景 ≥1 句 ≥35 字奔涌长句（铺陈蓄势），
  其后 3 句内落 1 句 ≤10 字收割短句；连续 4 句两两互差 ≤5 字 = 节奏平段，须打破
- 段落形态：段均 2-4 句；成段叙述与单行对白交替，避免连续 5 段以上同构断行

## 意象与修辞

- 感官细节密度：每千字 3-5 处（触觉/听觉优先于视觉）
- 比喻带（双向，叙述文字口径）：每千字 2-4 处，低于下限 = 干燥、高于上限 = 堆砌；
  喻体必须取材当章场景物象，通用喻体（月光如水／如释重负／隔层毛玻璃类）= 违规
- 意象母题：每卷 1-2 个核心物象（卷纲「金句、母题物象与梗位」行指定），
  每章 ≥1 次变奏复现，语境须不同

## 金句

- 每章 1 处候选金句位（对白内或叙述收束处）；写法三选一：
  对比（两个具象并置见张力，如「账上得有数。账上得有过磅这一下。」）／
  反差（语境错位：宏大词入琐事，或琐细词入宏大）／
  口诀化（短句可记诵，如「白天漏灰，夜里漏光。」）
- 禁对仗堆砌、禁「不是…而是…」变体；金句落位后 2 句内收，不解释不展开

## 对白/叙述配比

- 对白占比目标：35-55%（引号内文字 / 正文总字）
- 关键对白三层：信息／关系变化／潜台词至少推进其一
  （潜台词三法：答非所问／一语双关／反话克制）
- 连续裸对白（无归属无动作）≤4 轮；对白带归属或动作拍的比例 ≥70%

## 章型微调（自动，通常无需改动）

- 上述各带是全书基带；drafting 按备忘段 1 的 chapter_role/chapter_type 在带内
  自动调制重心——高潮 = 斩截与咏叹交替（短句连排后允许 1-2 句 ≥35 字咏叹长句）、
  过渡 = 长句与意象、battle = 动觉意象、dialogue = 对带上沿，见 drafting 创作原则 7
- 仅当某章型需要越出基带时才在此按章型覆写
```

对 v1 的变更点：基带 10-20→12-25；删除「≥16 字收束长句」伪长句定义，换奔涌/收割配额；感官密度 2-4→3-5；比喻单上限→双向带 + 喻体硬规则；新增金句节（含三写法与禁令）与母题行；对白新增三层要求；高潮调制改斩截与咏叹交替。金句示例取自星火 ch1 现成产出（自洽锚）。

## 3. P1 — drafting 正向工艺（`skills/shenbi-chapter-drafting/SKILL.md`）

- **创作原则 10「落差工艺」**（新增）：长句蓄势短句收割；三叠句刀刃使用（高潮/悲拍每章 ≤1 处）；点染收尾——章尾情绪落物象不落陈述。
- **创作原则 7 章型调制补反向档**：高潮拍在「句长压向带下沿」之外允许咏叹反向档——短句连排后 1-2 句 ≥35 字咏叹长句（斩截与咏叹交替）；五道硬闸照常。
- **创作原则 5 对话指纹升级**：在「匹配 voice_profile」之上增三层结构（信息/关系变化/潜台词至少推进其一，潜台词三法入文）。
- **PRE_WRITE_CHECK 增两行**：`- 本章意象母题: [卷纲物象 + 本章变奏]`（从备忘段 1 读）、`- 本章金句位: [对比/反差/口诀化｜落点场景]`（从备忘段 1 读）。
- **POST_WRITE_SELF_CHECK 增两项**：`- [ ] 奔涌句: 每场景 ≥1 句 ≥35 字 = [场景1: 原句摘录 / 场景2: …]`；`- [ ] 金句位: [原句摘录]（落位后 2 句内收）`——缺摘录 = 未达标，先补再输出（同章尾张力拍自检模式）。

## 4. P2 — 机制接线

### 4.1 金句/母题传导链（断链闭合）

- `volume-outlining`：「金句与梗位行（P2-6）」扩为「**金句、母题物象与梗位**」——每卷新增指定 1-2 个核心物象；G4.vo.quote_line **无需扩**（现谓词 `re.search(金句|梗位|彩蛋)` 对扩名行仍命中，volume_outlining.py:84）。
- `chapter-planning`：备忘段 1 增两行——金句位（对齐卷纲排期）与母题物象（卷纲物象 + 本章变奏）。planning 对 volume_map 的读取走 `extractor: volume_chapter` → `load_volume_context`（`src/shenbi/pipeline/_shared.py:363`）白名单提取（卷标题/Objective/张力曲线/当前 KR 块/章节点/跨卷桥），**现不含卷头部元数据区的「金句与梗位」行——须在 `load_volume_context` 增该行提取**（卷区段内「金句、母题物象与梗位」行，含卷区段头部 `**…**:` 加粗形态），否则断链闭合无效；drafting 对备忘段 1 的既有字段级 reads 已覆盖（新行在段 1 内）。

### 4.2 测量闭环升级（`src/shenbi/skill_utils/style_learning/compute_stats.py` + style-learning SKILL）

- `compute_sentence_stats` 增 **≥35 字句占比（奔涌率）**；新增 `count_similes`。**单信源落点 = `gates/shared.py`**：`segment_sentences` 自 compute_stats 迁入 + `count_similes`（闭集 + `find_quote_spans` 非对白剥离）新增；compute_stats 与 G4.cd 同向导入（既有依赖方向 skill_utils→gates 不变；compute_stats re-export `segment_sentences` 保 API 兼容——gates 层零 skill_utils 导入的仓规不被打破）。
- 比喻闭集（子串计数，非对白文本）：`像`、`仿佛`、`宛如`、`宛若`、`恰似`、`如同`、`似的`——密度 = 计数 / **非对白文本字数** × 1000。**非对白文本 = 剥离引号内文字后的正文**（引号对覆盖 `「」『』""“”`，复用 `cjk.find_quote_spans`）；**分母与分子同域**（非对白文本的非空白字符数，含 H1 行、剥 META 块）——若沿用 `total_chars_md_text`（含对白）作分母，对白占比 35-55% 下测值系统性下移约半，[2,4] 带界与 §2 模板「每千字 2-4 处」的写作者语义错位，故分母取非对白域。「像」子串匹配含「好像/就像」复合形式与名词内嵌（影像/画像/像样等）——两类误计均为接受的 WARN 级精度损失；`仿佛`/`如同`/`似乎` 计入 FATIGUE_BASE 疲劳预算（≤8/章）且 `仿佛` 另受 AI 标记词 ≤1 次/章硬闸——闭集七词中三词受限，实际可用喻词以 `像/宛如/宛若/恰似/似的` 为主，带内达标现实可行（试点观察项 6 人工抽检覆盖）。
- profile 模板：§1 句长分布表增「≥35 字句占比」行；§6 修辞模式表增「比喻密度（处/千字）」行；SKILL 统计指标目录节（「### 1. 句长分布」/「### 5. 修辞模式」）同步增两指标条目。反馈环语义从「强化均衡」变为「强化落差」。

### 4.3 自锚定范文环 `style/anchors.md`

- style-learning 每次重测（每 12 章/卷界）从**成书章节**自选 3-5 段最佳段落写 `style/anchors.md`（整文件重写），三类各 ≥1 段：落差奔涌段（含达标奔涌句）、母题变奏段、金句段；每段 ≤300 字，注明出处章号与一句示范点指认。**铁律 2 增 anchors 例外条款**（anchors 是该技能唯一下沉到产物的评判面）；选取半操作化：奔涌段以 §1 统计达标记章定位、金句段/母题段以 PRE/POST 摘录行为候选池，终选 LLM——候选池确定性保铁律 4 可重现叙事。few-shot 注入成本 ≈ 3-5 段 × ≤300 字 ≤1.5K tokens/章（相对 $0.18/章可忽略）。
- drafting reads 增 `- style/anchors.md`（few-shot 自锚定——用自己最好的文字拉自己，零版权风险）。文件缺席不阻塞：创世期前 12 章无 anchors，照 directives 写；首次重测后生成。
- truth 注册：`docs/framework/truth-files.yaml` 与 `truth-files.index.json` 增 `{name: style/anchors.md, kind: style}`（画像族文件；铁律 5 的 hands-off 只针对 `style_directives.md`，不冲突）。

### 4.4 G4.cd 三 WARN 谓词（确定性；WARN 不阻拦，进审计报告供裁决）

| id | 口径（全部操作化） | 触发 |
|---|---|---|
| `G4.cd.surge` | 计数域 = `strip_narrative_body(content)`（剥 PRE/POST META 块后的叙述正文，与 G4.transition 同域——防 POST 自检清单喂饱闸，probe escalation #4 同型）；句切分与 `compute_sentence_stats` 同源（`segment_sentences`）；句长 = 非空白字符数（含标点）；叙述句 = 引号内字符占比 <50% 的句；计数章内句长 ≥35 的叙述句 | 计数 < max(1, gate 口径章字数 // 3000)（切分与 §4.2 同源；配额分母取全章口径，对白占比高的 dialogue 章配额相对叙述域偏宽——温和方向，接受；7145 字章即 <2 处；1700 字探针章即 <1 处） |
| `G4.cd.simile_band` | §4.2 闭集子串计数于非对白文本，密度 = 计数 / 非对白文本字数 × 1000 | 密度 ∉ [2, 4]/千字（低 = 干燥，高 = 堆砌） |
| `G4.cd.golden_slot` | PRE_META 块含行首 `- 本章金句位: ` 且值为非空；POST_META 块含金句摘录项（行含「金句位」且冒号后至行尾非空——不耦合方括号字面，摘录带引号写法同样命中） | 任一缺失 |

- 俗套喻体与金句**质量**判定不进 G4（确定性闸管不了审美）——`simile_band` WARN 的 reason 文本附「俗套喻体抽检」提示，归审计裁决复核；试点期人工抽检（§6）。
- 母题行（PRE）**不设独立 WARN**：变奏复现的判定开放性强，机器只能查行存在、价值低，且避免 WARN 泛滥；母题质量归审计面抽检。

## 5. P3 — 框架红线（两项）

### 5.1 破折号预算制（`anti-ai-reference.md` 全禁 → 预算；本 spec 即框架变更流程载体）

- **每章 ≤2 处**，仅限两种用法：咏叹收束（长句末尾情绪延宕）、对话打断（话被截断）。**解释补充用法（「他深吸一口气——这不可能」类）仍然全禁**。
- 执行面：`anti-ai-reference.md` 句式禁令表该行改写；`review-anti-ai` SKILL 检查 3 改口径——每章 >2 处 = ERROR；≤2 处但属解释补充用法 = ERROR；合法用法 ≤2 = pass。计数口径用 `cjk.py` 破折号类（`——`/`──`），style-learning 测量节「§6 标点密度」（每千字破折号数）本就测量，作观察项。
- 依据：维基百科《AI 生成文的特征》自标破折号在中文语境为弱信号；咏叹破折号是烽火/猫腻文体核心标点。`docs/framework/style-directives.md` §4 中「解除破折号禁令须走框架变更」条款同步改写为预算制表述。

### 5.2 drafting 温度 0.85 → 0.90（`executor_config.toml`，单臂变更）

- 理由：对抗 RLHF 均值回归（「意料之外的妥帖比喻」被淘汰的直接补偿旋钮）；双跑 A/B 成本一整卷不成立，卷一 v2 首跑即单臂观察，对比 vol1 首跑段历史基线（~$0.18/章、escalation 率）。
- 回退条件：主判据 = 章均成本 >1.5× $0.18；辅判据 = 重派/escalation 率 >1.5× vol1 首跑段实录口径（空正文族修复前 9 次/4 章、decisions-stub 2/5 章——docs/probe-vol1-driver-prompt.md 已钉数字）→ 任一触发回 0.85 并记档（观察项，不动代码结构）。

## 6. 验证与试点

### 6.1 单测面（每处改动配套，TDD）

- `compute_stats`：奔涌率/比喻密度构造输入断言（结构性用例，测试内构造——G0.9 约束的是冒充真实产物的 fixture，不约束结构性用例）。
- G4.cd 三 WARN 三态：触发/不触发/边界（7145 字章恰 2 处 surge 达标、1 处触发；密度 2.0 与 4.0 恰在带界；PRE 行存在但值为空触发）。
- `style_seed`：新模板内容快照断言（改既有测试）+ write-if-absent 幂等不覆写仍守。
- 契约面：六份技能面（五 SKILL 契约 + anti-ai-reference 参考文件）的 reads/writes 变更后 `lint_registry_reconcile` 跑通 + `just lint-contracts` 家族绿（ORPHAN_READ 闭环：drafting reads `style/anchors.md` 的生产者 = style-learning writes）+ `just generate` 派生物（deps.json/docs/skills）再生成幂等；truth-files 注册一致；PRE/POST 新行的 G4 机械检查（META 块提取复用 `gates/shared.py` 既有函数）。

### 6.2 试点 = 卷一 v2 全新首跑（本 spec 落地后启动）

观察项六条（数据源：G4 gate 结果 JSON 的 checks 数组——gate-markers/ 逐章 marker 文件 jq 归集，无现成聚合面、不新增工具 + style_profile 重测 + 审计面 + 成本台账）：

1. 奔涌率：0 → ≥ max(1, 字数//3000)/章（style_profile §1 新行）
2. 比喻密度入带率（2-4/千字）
3. 金句位命中率（PRE 行 100% 落位 + POST 摘录 100%）
4. 三 WARN 触发率随章数收敛（前高后低 = 反馈环生效）
5. 温度 0.90 的 escalation/重派率 vs 历史基线（>1.5× 触发回退）
6. 人工抽检：金句不出现对仗堆砌模板化；奔涌句真奔涌（非注水长句）；母题变奏非复读

**GO/NO-GO 判据（前 10 章评估）**：奔涌率达标 + 金句位 100% + WARN 率收敛 + 成本 ≤1.5× 基线 + 人工抽检无模板化 → 文笔面 GO；任一不达 → 定位归因（指令层遵从率 vs 闸口径 vs 温度）后调参再验。

## 7. 非目标

- 不做外部范文注入（方案 C 否决记录在案：版权风险 + StoryScope「改风格难掩底层叙事差异」边际收益存疑）。
- 五道硬闸数值不动（转折词/AI 标记词/fatigueWords/字数/段落下限）；唯一红线变更 = 破折号全禁转预算。
- 金句质量/俗套喻体不进确定性闸；不动商业节奏批（G4.cp 三硬闸）；不做温度 A/B 机器。
- 项目级 `style_directives.md` 覆写权归用户；`anchors.md` 不进硬闸。
- 转折词预算在长句文风下的消耗抬升为试点观察项（若成瓶颈另立 spec，本批不动）。

## 8. 施工面清单

| 层 | 文件 | 改动 |
|---|---|---|
| 代码 | `src/shenbi/pipeline/style_seed.py` | `DEFAULT_STYLE_DIRECTIVES` 重写（§2 全文）+ docstring 叙事更新 |
| 代码 | `src/shenbi/gates/shared.py` | `segment_sentences` 迁入（compute_stats re-export 保 API）+ `count_similes` 新增（§4.2 单信源落点） |
| 代码 | `src/shenbi/skill_utils/style_learning/compute_stats.py` | 奔涌率 + `count_similes` 消费（单信源在 gates/shared.py，§4.2） |
| 代码 | `src/shenbi/pipeline/dispatch_helper.py` | `OPTIONAL_READS["shenbi-chapter-drafting"]` 增 `style/anchors.md`（前 12 章缺席常态；probe9 先例同 style_directives.md） |
| 代码 | `src/shenbi/gates/g4/chapter_drafting.py` | 三 WARN 谓词（§4.4，`GateStatus.WARN` 先例：`chapter_planning.py:98`） |
| 代码 | `executor_config.toml` | drafting `temperature = 0.90` + 注释 |
| 代码 | `src/shenbi/pipeline/_shared.py` | `load_volume_context` 增「金句、母题物象与梗位」行提取（§4.1 断链闭合的机器侧落点） |
| SKILL | `shenbi-chapter-drafting/SKILL.md` | 原则 5/7/10 + PRE 两行 + POST 两项（§3） |
| SKILL | `shenbi-chapter-drafting/anti-ai-reference.md` | 破折号预算行（§5.1） |
| SKILL | `shenbi-chapter-planning/SKILL.md` | 备忘段 1 增两行 + volume_map 字段级 reads 对齐（§4.1） |
| SKILL | `shenbi-volume-outlining/SKILL.md` | 「金句与梗位」行扩母题物象（§4.1） |
| SKILL | `shenbi-style-learning/SKILL.md` | profile §1/§6 新行 + `anchors.md` 产出（§4.3，writes 增该文件） |
| SKILL | `shenbi-review-anti-ai/SKILL.md` | 检查 3 破折号预算口径（§5.1） |
| 框架文档 | `docs/framework/style-directives.md` | §3 模板同步 v2 结构；§4 破折号条款改预算制 |
| 框架文档 | `docs/framework/truth-files.yaml` + `truth-files.index.json` | `style/anchors.md` 注册 |
| 测试 | `tests/unit/`（pipeline / skill_utils / gates） | §6.1 各面 |

**契约升级纪律声明**：drafting reads 新增 `style/anchors.md`、PRE/POST 与备忘段 1 新行——全部 WARN 级、非硬闸必填；历史项目目录已全删（2026-10-24），**无在途 artifacts 受影响**，无 backfill 义务。`plan_format` 版本化不触发（新行皆可选级，不构成「第二个硬闸必填字段」）。
