# Spec #96 · 反 AI 检测体系方法论对齐（anti-ai-tell-alignment）：机制解释、证据分级、结构 tell、人味保留

**日期**：2026-11-04 ｜ **系列**：文笔面强化批（humanizer 对标） ｜ **状态**：Active（r1） ｜ **优先级**：🟡 P2
**依赖**：**#95 T1（gate 词表⇄prompt 契约同步器——显式枚举常量单源）落地后施工**（T1/T2 若先动词表面=双源复发，#95 R1 同型事故）；**批次时序：批次 A（#85→#95→束4 验收→#86-#94）清偿后启动**——本 spec 主战场=SKILL.md×3＋`pipeline/review_checklist.py` 预计算，不抢 `chapter_loop.py` 最热文件（r2.2 共享文件表无需增行）；验收搭卷二实弹后续章，不开新探针。
**动机证据**：blader/humanizer v3.1.0（64.3k stars，MIT，源流 Wikipedia "Signs of AI writing"）全量调研落盘 `docs/research/2026-11-04-humanizer-skill-analysis.md`（26 tell 逐条英文原文+来源 URL）；对标基面=现行三面实现：D3 检查清单（`skills/shenbi-review-group-craft/SKILL.md` L213-265，10 项中 3 项机器预计算注入）＋anti-detect 9 手法（`skills/shenbi-anti-detect/SKILL.md`）＋确定性预计算（`pipeline/review_checklist.py` paragraph_cv/transition_count+budget/ai_marker_hits 每词 ≤1）。

**触及的不变量维度**：叙事纪律（POV/声口）（弱关联——T3 人味/声口保留面防改写磨平，不新增判定判据）；其余为审计检查项与改写工艺层，不动 13 维门检判据与 truth 结构。

---

## 0. 对标矩阵（humanizer 六类 26 tell × shenbi 现行三面）

### 0.1 已覆盖（不重做）

| humanizer | shenbi 现行对应 | 备注 |
|---|---|---|
| §1 not-X-but-Y（最强 tell） | D3 检查 2「不是…而是…」 | 等价 |
| §8 破折号万能连接 | D3 检查 3 预算制 ≤2/章＋合法用法白名单（咏叹收束/对话打断，spec #71） | **比 humanizer 精细**（其立场=全禁除非样本匹配） |
| §12 高频词表 | `ai_blacklist`＋fatigueWords 禁用/慎用（实弹词表全为中文网文表情/动作套话：「眼中闪过一丝」「瞳孔猛地一缩」族） | **genre 特化，厚于 humanizer** |
| §25 写文档本身 | D3 检查 7 元叙事/编剧旁白 | 等价 |
| §2 章尾复述（半边） | #82 T4① 章尾复述行 ≥60% 语义重述 finding（D2 检查 9） | 只覆盖章尾；**中段缺口→T2** |
| §22-25 聊天/草稿残留 | `strip_narrative_body` 剥 META/PRE_WRITE_CHECK 块（review_checklist.py:313，fixcheck ch2 教训） | **机器等价物更强** |
| §9 堆叠限定词（部分） | D3 检查 4 转折词密度（预算=max(5, wc//1000)） | 部分对应 |

### 0.2 shenbi 反超面（humanizer 反该学 shenbi，本 spec 不动）

机器面零 LLM 成本预计算；审计累积→genre-config 词表的学习闭环（humanizer 靠 issue 模板人工迭代）；章型调制（高潮章碎段=章型恰当，SKILL L45——humanizer 无此文体分支粒度）；声口正向硬预算（`voice_density_min.min_per_chapter`，drafting SKILL L144）；替换建议「自然得不像替换」约束（genre-config SKILL L185）。

### 0.3 五缺口（本 spec 施工面）

| # | 缺口 | humanizer 证据 | shenbi 后果 |
|---|---|---|---|
| G1 | **机制层解释缺失**——规则是平铺清单非原理 | 单一机制统领 26 条：「LM 为最广读者做默认选择，人类为一个读者做特定选择——每条 tell 都是默认选择的一种表现」 | 换代模型的新口癖不在清单上时零泛化能力；每代靠审计累积追认 |
| G2 | **证据分级与聚集规则缺失**——全部检查项平级二元判定 | 「§1-5 单次 sighting 即改；标 weak-alone 的需同段其他 tell 聚集才行动」（概率化判断）；防误报例外内嵌每条＋全局 When-not-to-act | over-enforcement 实案：spec #84 审计「口癖帽×voice 门互斥」——两门一个要求口癖达标、一个限制超帽；anti-rationalization 表全防「不改」不防「误改」 |
| G3 | **结构 tell 覆盖缺口** | 「词随模型版本漂移，结构习惯持久，故结构 tell 排最前」——A 类五条全是结构级 | shenbi 词级厚、结构级仅「不是…而是…」一条；三连排比（§6）、中段单句收束段（§2 非章尾半边）、重复句首（§7）无对应 |
| G4 | **anti-detect 改写工艺薄弱**——9 手法各仅一句话描述；无人味保留清单；reads 不含 #71 正向资产 | 每条 tell 带 Watch for/Problem/Before/After 四件套＋因果解释；人味细节保留清单（反常具体细节/矛盾情绪/自嘲旁白除非伤害语义否则保留） | 改写质量靠 LLM 自由发挥；「保留不改的好句」节纯自报，无资产对照；刚挣来的金句位可能被改写磨平 |
| G5 | **事实守恒无显式复核** | 「添加/丢失 fact、number、quote、citation、ranking、同时性声明均算错误」与 tell 幸存同级；点名形状类改写（§6/9/19）最易丢 claim | 铁律 1「不改叙事内容」靠自报复核；改写后仅复跑 anti-ai+sensitivity 两审计；「打破段落等长/句式规律」两手法同为形状类改写、同风险无提示 |

**根本差异裁定**：humanizer 明确「不以骗过检测器为目标，检测器仍标记其大部分输出」；shenbi 的 anti-detect 存在理由=平台 AIGC 检测关联推荐权重与收入（SKILL 铁律面）。**两目标并存不互换**：检测器导向硬闸（paragraph_cv/转折词预算/破折号预算/标记词每词 ≤1）全部保留硬判定；humanizer 经验是在其上**加**「读起来像人写」的结构层与改写工艺，不是替代。

## 1. 任务分解

### T1 · D3 检查协议升级：机制段＋证据分级与聚集规则（修 G1/G2）

- **机制段**：D3 开头加一段中文机制解释（默认选择 vs 特定选择——措辞转译 humanizer 原文，注明源流），后接现有 10 项清单；作用=给 LLM 判定面一个可泛化的原理锚，清单外新 tell 可按机制归入最近检查项报告（报告须引机制句＋最近检查项名，不得自造新检查 id）；
- **分级协议**：检查项二分——**强 tell**（结构级：不是…而是…、元叙事/编剧旁白、破折号违例）单次即 ERROR（维持现状）；**弱 tell**（疲劳词、段长规律性、分析报告术语、集体反应套话）引入聚集规则：同段 ≥2 类弱 tell 聚集才升 ERROR，单发保持 WARNING；**机器面硬判定一律不动**（ai_marker_hits 每词 ≤1、转折词超预算、破折号 >2、paragraph_cv 阈值——这些有明确预算且是检测器导向，不属「弱 tell」软化范围）；
- **防误报例外内嵌**：三条强/中 tell 检查项各补一行保留例外（对照式：负面半句纠正读者实际持有的信念→保留；引文/角色台词内→豁免；节奏目的重复→保留）——对应 humanizer「引文/专名/讨论该短语本身的段落豁免」；
- **红测**：聚集规则断言（单发弱 tell 不升 ERROR/同段聚集升）；用口癖帽×voice 互斥型实例（voice 预算要求的口癖串 vs 疲劳词检查）构造结构输入（G0.9 允许内联构造）断言不再互斥双报。

### T2 · 结构 tell 三条转译进 D3（修 G3）

- D3 检查清单续编 11-13，各带保留例外（防 G2 同型误报）：
  - **11 三连排比**：单句三项并列（「他不怕，不让，不退」型）或三个平行短段＋归纳句；保留=真三项语义（意义确需三部分）——中文三项并列是真修辞高频（ unlike 英文 forced triad），**判定必须走语义而非计数**；
  - **12 中段单句收束段**：非章尾（章尾归 #82 T4①，不重复报）的单句段重述前段且不加新信息（「这就是成长。」「那一刻他懂了。」型）；保留=加事实或后果的收束；
  - **13 重复句首**：连续 ≥3 段同字/同词开头且非节奏目的；保留=故意排比节奏（声口要求行的排比预算优先）；
- **机器面只做参考计数**：三连候选（顿号/逗号三项并列出现次数）进 `review_checklist.py` 预计算注入作参考值，**不设硬阈值**（误报风险裁定：中文真修辞密度高，硬阈值=G2 同型 over-enforcement）；重复句首可同法预统计；两者均为「参考注入＋LLM 语义判定」模式（先例：paragraph_cv 注入）；
- 新条目随 D3 default-activated，**不新增 genre-config auditDimensions 键**（防键膨胀）；
- 词表若需扩结构类慎用词（如「那一刻」「这就是」候选短语）——**只进 genre-config fatigueWords 慎用（运营面，不占本 spec 施工）**，本 spec 不动词表本体。

### T3 · anti-detect 改写工艺升级（修 G4/G5）

- **四件套**：9 手法每条补 Before/After 中文网文对照例（每条 ≤2 行例句，防 SKILL 膨胀）＋一句因果解释（该手法为何降检测性——机制段同源）；**新增第 10 手法「整段自然重述」**：靶向替换 2 轮仍有幸存 tell 时，对密集段允许整段围绕主旨重述（humanizer 终步「state each point naturally instead of patching flagged phrases one at a time」转译）——仍受铁律 1/4 与 3 次回退约束；
- **人味保留清单**（改写护栏，SKILL 铁律区）：具体反常细节（数字/专名/奇怪联想）、矛盾情绪、自嘲与旁白、声口指纹串——除非直接构成检测标记否则不改；anti-rationalization 表补两行防「误改」向（现有表全防「不改」向）：「为通过检查把好句改平庸」/「人味细节看起来像口癖」；
- **reads 接线正向资产**：anti-detect contract reads 增两投影——本章出场角色声口指纹（characters 面 voice_fingerprint 行，先例 `_extract_voice_constraints` 确定性名匹配）＋备忘金句位/声口要求行（plans 面）；「保留不改的好句」节从自报升级为**对照资产核验**（逐条注「金句位/声口预算/人味细节」来源标签）；
- **事实守恒复核**（修 G5）：改写报告复核清单增「事实守恒」项——改写前后 fact/数字/专名/同时性声明不增不减；**「打破段落等长」「打破句式规律」两手法点名最易丢 claim**（humanizer §6/9/19 形状类经验转译）；改写后审计复跑维持 anti-ai+sensitivity（不扩面——事实漂移由复核项＋既有 continuity 审计兜底，不新增第三审计）。

### T4 · 验证面

- T1 per-skill 测试：anti-detect（generative/bug-hunt）＋review-group-craft（D3 维度）——fixture 用实弹章与实弹 genre-config（tests/fixtures 现有 xinghuo 实弹族）；
- 实弹回归（搭车卷二束4 后续章，不开新探针）：≥3 章 audits 新旧检查项误报率不升（聚集规则上线后 WARNING 噪音下降=正向信号，记录对比数）；anti-detect 若触发，金句位/声口零丢失（对照核验新节逐条可查）；
- 单测面：聚集规则红测、三连参考计数注入、reads 投影过滤（声口指纹/金句位行命中）、改写报告新节结构断言（G4.ad 检查器同步扩：改写报告须含事实守恒复核项与资产核验节——`gates/g4/anti_detect.py` 检查面同步）。

## 2. 验收

1. `just check` 全绿（含 lint_invariant_coverage 对新登记块的节存在性校验）；
2. D3 SKILL：机制段＋分级协议在盘；检查 11-13 各带 Before/After 例与保留例外；聚集规则红测绿（单发弱 tell 不升 ERROR/聚集升/口癖帽×voice 互斥实例不再双报）；
3. anti-detect SKILL：10 手法四件套齐；reads 含声口指纹＋金句位投影；改写报告模板含「事实守恒对照」「保留好句对照资产核验」两节且 G4.ad 结构检查同步；
4. 实弹回归 ≥3 章：audits 误报不升（对比数落盘）；anti-detect 触发章金句位/声口零丢失；
5. 调研文档 `docs/research/2026-11-04-humanizer-skill-analysis.md` 在仓（对标证据锚，含 26 tell 原文）。

## 3. 不做面（防过度施工）

- 不搬 humanizer E 类（聊天残留/知识截止声明）与 F 类（wrong reader）——中文小说正文无此面，机器等价物已有（`strip_narrative_body` 剥 META、#82 T4① 章尾复述）；
- 不动检测器导向硬闸（paragraph_cv/转折词预算/破折号预算/ai_marker_hits 每词 ≤1 维持硬判定）——商业约束优先，分级只作用于无预算 LLM 判定项；
- 不整搬 26 条清单——按 humanizer 防膨胀原则（新 tell 默认并入既有 pattern）只并入既有检查体系；清单外新 tell 走「机制归入最近检查项」路径（T1）；
- 不动 fatigueWords 词表本体与审计累积闭环（词表漂移已由闭环治理）；结构类慎用词候选属 genre-config 运营面；
- 不加 SKILL.md 词数硬预算 lint（humanizer 的 5,500 词上限机制属其单文件形态；shenbi SKILL 有 auto-check/契约结构，词预算治理另议不占本 spec）；
- 不给 anti-detect 加第三审计复跑（事实守恒走复核项，不增审计成本）。

## 4. 与在档 spec 的关系

- 上游证据：`docs/research/2026-11-04-humanizer-skill-analysis.md`（26 tell 英文原文逐条+方法论+工程面全记录）；
- **#95 T1**：枚举常量单源基座——本 spec 施工时序硬前置（先 #95 后 #96，防词表/枚举双源）；
- **#71 惊艳度层**（PR #246/#247）：T3 reads 接线其正向资产（金句位/声口/文笔资产）——anti-detect 与 #71 层首次互认，改写不再可能磨平刚挣来的资产；
- **#82 T4①**：章尾复述 finding 已覆盖 §2 章尾半边——T2 条目 12 明确只管中段、不重复报；
- **#84 口癖帽×voice 互斥**：T1 聚集规则＋保留例外是该发现的方法论级回应（over-enforcement 防线）；
- 批次 A 无共享文件冲突（主战场 SKILL.md×3＋review_checklist.py 预计算——后者不在 r2.2 共享文件表内；若执行时 review_checklist 预计算与批次 A 任一 spec 撞面，按 r2.2 表规约 plan 首步 re-anchor 裁）。
