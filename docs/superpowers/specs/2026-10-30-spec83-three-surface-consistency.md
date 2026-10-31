# Spec #83 · 三面一致性之网（three-surface-consistency）：正文/声明/truth/大纲的对账、联动与回灌

**日期**：2026-10-30 ｜ **系列**：卷一复盘→卷二防复发（与 #82 retention-engine-net / #84 vol1-repair-vol2-launch 配对）
**状态**：Active（r4 修订 2026-10-31） ｜ **优先级**：🟠 P1（正确性基建——P1×4 全部由此族产生；#80 管不变量本身，本 spec 管四面之间的搬运）
**动机证据**：G3.4 缺陷清单 P1×4 + 盲审「声明 vs 实际（货不对板清单）」+ vol1-ledger 运行史（identity 门/类别漂移/F6 族）+ longitudinal fail-closed 假阴性
**修订**：r2 2026-10-30 高精度审核修订——T2 stale 写入者定为框架回调（不动修订技能契约，免 contract-upgrade backfill 义务）；T4 打摆切换取数路径定为 DISPATCH `failure_class`＋RETRY/loop_id 聚合（不从反馈文本判读）；T6 计数锚并入 F17 `cd.counter` 提取器扩族（不建第二套 prose 计数器）；T5 与 #82 T0 声明快照层同点位同批；新增铁律 L-D（新门 shadow 纪律，与 #82 L-D 配对）。r3 2026-10-31 驳斥复核修订（fresh-context 五问+协调者六项亲验）——T1 增嵌套引号提取前置修复+门作用面收窄至 POST 声明类行（PRE 禁忌词表/跨段转述噪声白名单化）；T2 主修法改「PRE 物象/POST 引句并入既有 #72 R3-C1 复验面」、stale 状态化降次级（11 行漂移真源=驱动侧手工改文，非管线修订步）；T4 打摆切换取数源改 RETRY `reason.check_ids`（DISPATCH `failure_class` 在唯一长跑语料实弹空集 361/0）、SKILL 铁律子项撤销（与既有铁律 0 调和）、`incremental_only` 降格为反馈定向增强+diff 面积 WARN 量化、复发章号勘误；T5 同点位措辞改「接续」（#82 T0 已落地预留接口）；T6 ch28 判据重设计（「并集外」判据下实例不红）；T7 声明面 lint 并入 lint_outline_truth_drift 子命令；辅助实证清理（C16 证伪/C17 子串噪声前置/C18 实例过期）。r4 2026-10-31 熔断清偿修订（连续 2 次 REWRITE 熔断→用户 B 路径审单授权；两阻断项+两项设计抉择经用户裁定）——T4 取数源定稿 **RETRY 两源合流**（monitor_rewind `reason.issues` 前缀分族为主源〔35 条全 drafting、check_ids 全空、r3「47 条全带 check_ids」不实〕＋g4_hard check_ids 兜底；monitor_rewind **计入**；族名勘误 cd.word_*→G4.word_count/word_band/chapter_band；补引 `_length_family` 既有定向反馈先例）；T6 判据定稿（N+0 解析扩面＋**计划内部矛盾门**〔同 counter 多条异值声明→FAIL，ch28 :88 4+0 vs :100 4+1 稳红〕＋终值不一致 FAIL——r3 判据在该夹具下仍全绿经逐行重演证伪）；T1 执法面定稿**两行**（金句位＋章尾张力（G4.cd 口径）——标签实名勘误；**微粒钩移出机器执法面**〔用户裁定，跨段转述噪声 7/9 无谓词可分，交 G3.4 兜底〕；嵌套感知正则钉死、删最长匹配备选；PRE 噪声 4.7 条/章勘误）；T2 物象谓词取数面=**plan 结构化行**（`物象: X|Y`/`X@hold:`，用户裁定；PRE 散文行不判）；T5 resonance 数字勘误 20→14。r5 2026-10-31 全语料回放门修订（第 3 次 REWRITE 续裁 A 路径授权；**每条判据写入前对 36 章红绿两面回放，回放证据入 progress.md**——r3/r4/r5 同签名翻车〔判据未对全语料回放即写入〕的根治门）——T1 判定改**两臂制**（逐字臂缺席→子句臂标点归一子句等值：子句有缺=FAIL〔回放 5 例全「命中原句/金句」失真：ch1/ch6/ch2/ch31/ch33 逐例缺子句实锚〕、子句全在=WARN〔7 例标点/复合变体交评审〕；r4「排尾注」单臂经回放证实不收敛〔21→12，主因标点变体与复合引句〕，子句臂为可达收敛线）；T2 物象谓词改**相对口径**（entity_in_text(修订前)∧¬(修订后)→FAIL——绝对在场在全语料证伪：朴素 28 例/14 章零删改即红、三形匹配仍余 7 例合法缺席〔ch4/6 红纸包、ch27 半部《鉴录》、ch33/34 灰底采买旗〕）；T4 计数改**口径a**（同 key seq 序 RETRY 连击**不分族**——「长度/结构族才计入」门控在全语料证伪：ch25〔卷一最重打摆 14 连〕该口径下最长连击 3 永不触发；分族表〔7 族 147 条全表补 G4.cd×31/XC×4〕重定位为**反馈路由面**非门控面；loop_id 不作计数器；g4_hard check_id 剥 `G4.` 前缀归一）；T6 判据③改**「基值==facts」口径**（+0 六章全绿/ch28 双声明稳红回放实证）＋prose 面**同句锚定**（ch30 船单「七个名字」/修辞「一个名字」两误红排除实证）＋剥 META；T5 resonance 钉死 **per_chapter 面=8**（ch6-30 偶数 follower 恒缺；20/14 两旧口径均不复现）＋chapter_states 锚路径补 `chapter_loop.` 层级（顶层无该键）；T2/T6 新 FAIL 支路点名 shadow 位；「45/45 章」勘误为 36 章 68 行实际形态。r5.1 2026-10-31 轮 4 勘误（fresh-context 驳斥复核：五路判据数值与实锚全部经独立复算**存活、无一路被驳斥**；收 1C+6I 勘误）——「68 逐字绿」算术勘误为 **61**（73−12；68 系执法行数误植）；T4 断链锚定改钉**章循环状态机**（trace 词表实测无终态 action〔全集仅 AUDIT_PASS/DISPATCH/GATE_FAIL/RETRY〕——执行面计数器落 chapter_loop 既有 per-chapter retry 状态族，episode=章状态机对本章的生命周期，推进/升级清零、重开新 episode；trace seq 序仅为观测回放面）；T6④ 同句钉切分正则 `_SENTENCE_SPLIT_RE`（chapter_drafting.py:91）；T6③ ch9 绿测夹具注明构造 facts=3；T2 谓词作用面钉 strip_narrative_body 剥后正文＋修订前正文取 `chapter-N-pre-rev.md` 备份（`_create_pre_revision_backup` chapter_loop.py:2771 修订派发前写、:1437 复验已在读——可实施性实锚）；T5 注明 ch31-36 为行整体缺席（报告生成于 ch30 checkpoint）；T1 补 1 字引句已知逃逸面注记

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
2. 修订联动面半覆盖（r3 改写）：管线内修订步已有 #72 R3-C1 复验（`_revalidate_revised_chapter`，chapter_loop.py:1416、接线 :4487——scene 钩声明+场景标记 diff+字数带，修订后自动排队 settle 重派），但 **PRE 物象行/POST 引句不在复验面**；且 11 行 scene_hook 漂移的真源是**驱动侧手工批量改文**（R1/R2 清偿轮，不经管线修订步，零门复跑）——两条路径都缺「PRE 物象/POST 引句」的联动，手工改文路径更无任何对账；
3. 运行期 canon 演化（修复轮发明、settle 双写）单向流入 truth，大纲**无系统化回灌路径**（R1 曾手工把轮回触点◆×5 拍入节点——回灌靠手工且不一致地发生，恰证无工具路径）且节点是规划的唯一锚（「不得越过节点另起炉灶」）——emergent canon 不回灌 = 后续章以过时锚规划；
4. 束（bundle）的完成语义只对 leader 章写全——follower 章的 status/resonance/ledger 行半完成（F6 同族，卷一 18/36 章中招）；
5. POST 自检块是**模型自填的**，引用句可以是正文不存在的话——假声明会随 settle 摄取回流 truth（盲审 B 警告：「自检块声明失真比没有自检更危险，它会向上游 truth 文件回流假数据」）。

**铁律 L-C**：对账器只对**结构化可判定**的子集动手（引句逐字存在/数值锚/清单枚举），语义级留给评审——不造 NLP 假象（#82 同纪律）。

**铁律 L-D（r2 新增，新门 shadow 纪律）**：本 spec 与 #82 全部新增 FAIL 门带 `shadow` 配置位，卷二首束（ch37-38）WARN 试运行，零误伤后升 FAIL——#80 前向门五连校准（commit 8001ed3f）实录教训：实弹误报回修的成本高于一次 shadow 轮。

---

## 1. T1 · POST 声明引句 verbatim 门（声明↔正文）

- **前置子任务（r3）：嵌套引号提取修复**——#82 共基 `_QUOTE_RE`（quote_verbatim.py:21）字符类排除嵌套括号：ch1 钦定实证句「心里记下这笔「听不懂的账」——却不知道明天城就破了」（chapter-1.md:231，外层「」内嵌「」）当前提取零命中（协调者实跑复现：22 条提取、实证句族 0 条），内层片段 4 字 < min_len=6 又被丢弃——不先修提取器，红测不红、门形同虚设。修法**钉死嵌套感知式（r4）**：`「((?:[^「」]|「[^「」]*」)*)」`（一轮实测 ch1 实证句可提取可判红）——**不用最长匹配**（按行 greedy 会把 `场景1「…」／场景2「…」` 合并成跨 `/` 假引句，ch1:234/235、ch6:298 均双引句行），ch1 实证句入提取结果为验收；
- **门作用面（r5 回放定稿：两行执法）**：`G4.cd` 增 `quote_verbatim`（shadow 起，L-D）——执法面仅 **POST「金句位」＋「章尾张力（G4.cd 口径）」两行**。**行覆盖实测（r5 全语料清点，勘误 r4「45/45 章统一形态」系文件/章混淆）**：36 章共 **68 行＝两标签各 34**（`- [ ]`29＋`- [x]`5，复选两态均收）；ch25 变体行 `- [x] 章尾张力:`（无 G4.cd 口径标签）不入执法面；ch11 无 POST 自检行（其缺块归 T7 声明面漂移清单）。**微粒钩行移出机器执法面（r4 用户裁定）**维持——轮 2 实测三类声明行 miss 共 9 条中 7 条为微粒钩跨段转述噪声（对白被动作拍切分/跨段重组，如 ch28「王朝的命，」…「是拿附籍人的命续的。」），无机械谓词可分——微粒钩假声明交 G3.4 评审兜底；**PRE 面整体不入场**维持（12 章样本噪声实测 4.7 条/章，主形态=禁忌词表引号句＋标签自引；PRE 金句位行与 POST 逐字相同，排除无覆盖损失——ch15:15 vs :293 实证）；无引号裸句张力声明（ch6 形态，命中原句后无「」包裹）不入执法面（缩面已知取舍）；
- **提取管线（r5 定稿）**：嵌套感知正则 `「((?:[^「」]|「[^「」]*」)*)」`（r4 钉死，删最长匹配备选——按行 greedy 会把双引句行合并成跨 `/` 假引句，ch1:234/235、ch6:298 实证）＋**位置法排尾注**——引句起点落在全角括号区间 `（…）` 内即弃（尾注〔（含张力词「…」）（三点同型…）（另有「…」一拍）〕构造上不可能逐字命中；r5 实测排除 9 条括号内引句）；**用位置法而非文本剥除**（防主引句内含括号被误改写）；
- **判定两臂（r5 回放定稿，替代 r4 单臂逐字判定）**：**逐字臂**——`quote_in_chapter`（#82 共基：剥后正文子串＋扁平回退）缺席 → 进子句臂，不直接 FAIL；**子句臂**——标点归一（剥除 。！？；，、：·—–…「」『』“”（）等全标点族与空白）切子句（≥2 字），声明引句**每一子句**须以等值子句出现在本章剥后正文（strip_narrative_body）子句集：**任一子句缺席 → FAIL**（修复者 drafting：改 POST 声明一行即可，修复成本极低；盲审 B 警告「自检块声明失真比没有自检更危险，会回流 truth」——失真声明在本判据下不可豁免）；**子句全在 → WARN**（逐字缺席但内容有据——标点变体/复合归并形态，交 G3.4 评审，不 FAIL）。**回放实证（36 章 73 引句）**：**61 逐字绿**（73−12；r5.1 勘误：r5 曾误植 68——那是执法行数）；**5 FAIL 全为声明失真**（逐例正文亲验）——ch1（缺子句「却不知道明天城就破了」，正文无此句）/ch6（缺「册子认得」，正文 :262/:270 为「册子认得人」——截断漂移）/ch2（缺「想着账上还欠老驼一包盐」，正文 :256 为「想着还欠老驼一包盐」——声明侧添「账上」的归并缩写）/ch31（缺「他在私账」「栏底下写下第一行」，正文 :50 为「私放」两个字写在头一行——句式发明复合体）/ch33（缺「旗会换」「价会变」「经手人这一栏」，正文 :363 无此排比——发明尾）；**7 WARN=标点变体**（ch2 `——`vs`，`、ch19 `：`vs`，`）**与复合归并**（ch13/16/26 等——如 ch16 金句在正文为被叙述切分的对白）。**r4 修单「排尾注」单臂不收敛的回放证据**：尾注排除仅消 21→12（剩余主因=标点变体与复合引句），12→5 由子句臂消除——两臂制是本语料可达的收敛线（5 FAIL 均失真、7 WARN 均有据），且子句**等值**（非子串）恰保 ch6 截断红（`册子认得`≠`册子认得人`）不漏；**min_len 分档（r3 意图）由子句 ≥2 字下限承载**（「册子认得。」4 字金句形态合法——防「写短逃逸」博弈路径）；**已知逃逸面注记（r5.1）**：1 字引句（语料现存 ch6「查」/ch23「叁」形态）逐字臂平凡子串命中即绿、缺席时子句集为空落 WARN——伪造 1 字引句为已知对抗路径（与短引句逃逸同类，G3.4 评审兜底，不为此扩子句下限）；
- POST 声明-门实测交叉：POST 报「转折词 0」而 G4.cd 词法检查命中 ≥1 → FAIL——**前置子任务（r3）**：`count_transition_words` 子串语义修正（ch17:79「算**不过**来的账」被误计 1 次、ch17:186「忽然说」不计——现行命中即噪声；不修则交叉门反向误伤无过错正文，制造新打摆源）。r2 所引 C16 反思句实证**删除**（现行 META_NARRATIVE 词表下 POST 声明与门计数完全一致，证伪）；
- 字数行虚假精度复用 G2.7 助手复算——差 >2% → WARN（r2 所引 C18「报 3795 实 3700」实例已过期——R4 批后 ch18 声明 3800、实测 +1.1% 带内；判据保留、实例泛化不指定）；
- **共基声明（r2 维持）**：verbatim 判定器复用 #82 `quote_verbatim.py`（`quote_in_chapter`/`extract_meta_quotes` seam 已建，注释明示 #83 T1 extraction seam）；本任务只扩消费面+修提取器，不建第二套。
- **TDD**：红测五例（ch1 嵌套修后红/ch6 截断金句/ch2 归并缩写/ch31/ch33 复合发明——r5 回放钉死的 5 FAIL 全集）；WARN 测例（ch13/ch16/ch19/ch26——逐字缺席子句全在不 FAIL）；负例（ch28 微粒钩移出执法面/ch25 变体标签行不入面/ch30 尾注位置法弃/ch17 子串噪声交叉门前置红测）——全部 G0.9 真实输出拷贝 → tests/fixtures/。

## 2. T2 · revision→声明联动（升格既有复验面为主，r3 改写）

- **主修法（r3；r4 定取数面；r5 定谓词口径）**：`_revalidate_revised_chapter`（chapter_loop.py:1416，#72 R3-C1 已有 scene 钩声明+场景标记 diff+字数带复验）扩面——**物象/POST 声明引句**并入复验谓词：物象取数面=**plan 结构化行**（`物象: X|Y`／`X@hold: 持有者` 形态，chapter-28-plan.md:86/:99 实锚；r4 用户裁定；r5 全语料清点 44 行＝@hold 23＋物象行 21）——**谓词=相对口径（r5 回放定稿；r5.1 钉作用面与取数源）**：`entity_in_text(物象名, 修订前正文) ∧ ¬entity_in_text(物象名, 修订后正文) → FAIL`（修订把物象整段删尽；entity_in_text 为 F16 既有三形匹配器，chapter_drafting.py:66——升格既有）。**作用面（r5.1）=strip_narrative_body 剥后正文，两侧同口径**（raw 面下 PRE/POST 声明块自身含物象名会使 pre 侧恒真、谓词退化为单侧）；**修订前正文取 `chapters/chapter-N-pre-rev.md` 备份**（`_create_pre_revision_backup` chapter_loop.py:2771 修订派发前 safe_write 写、`_revalidate_revised_chapter` :1437 已在读——可实施性实锚，语料现存 18 个 pre-rev 文件）。**绝对在场口径在全语料证伪（r5 回放）**：朴素全串匹配 28 例/14 章零删改即红（与轮 3 审计逐数吻合）；三形匹配仍余 7 例**合法缺席**（持有物象当章正文零提及为合法叙事态——ch4/ch6 红纸包〔ch4 唯一命中在 PRE 声明行〕、ch27 半部《鉴录》、ch33/34 灰底采买旗）——故在场判定必须相对化，零修订现状全绿。**入场行**：`@hold` 与 `物象: X|Y`；`@lose`/`@mention`/`@none` 形态（现语料未出现）不入场——丢失/纯提及物象不在场是预期态；POST 引句走 T1 判定器（执法两行）；**PRE 散文物象行不判**（「本章母题物象：」行为散文变体——/（）/；切分近乎恒真，与 T1 PRE 排除同款纪律）——升格既有而非新建回调，扩面后任何经管线修订步的改文即被复验覆盖；**新 FAIL 支路（物象删尽）shadow 起（L-D）**；
- **次级（stale 状态化）**：`declaration_stale` 状态写 manifest（写入者=框架回调，修订完成处；修订技能契约面不扩——shenbi-chapter-revision/SKILL.md:6-19 writes/updates 不动，免 contract-upgrade backfill 义务），`state-settling` 摄取前检查 stale 未清 → FAIL（**新 FAIL 支路 shadow 起，L-D**）——覆盖「复验谓词漏网形态」（复验只查三类声明，stale 兜底任何修订后未同步面）；
- **手工改文路径（真源，r3 定位）**：11 行 scene_hook 漂移源于 R1/R2 驱动侧手工批量改文——不经管线修订步，两机制均不触发；该路径由 **T7 lint 子命令**事后对账兜底（工具只报不写，清偿随 #84 T0）；
- 联动面最小化：只挂「scene_hook / 物象 / POST 引句」三类（卷一漂移全部落此三类；timeline 行归 T5 工具顺带对账）。
- **TDD**：修订改末行 → 复验 FAIL（scene 钩既有语义）/物象新谓词红（修订删尽：pre 命中 post 不命中）/物象绿路径（零修订现状 44 行全绿——r5 回放；修订不动物象相关段仍绿；7 例合法缺席章〔ch4/27/33 等〕修订其他段仍绿）→ 重派反馈定向；stale 标记升起 → settle 拒收 → 重跑 hook_match → 清除。集成测试走 `tests/integration/` 束链路径。

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

settle 全量重写是声明漂移与 content_dropped 复发的共同根因（probe29 老病；卷一复发勘误（r3）：ch11 重派/ch16/ch23 content_dropped＋ch29-30 类别词表漂移三连败——r2 所列 ch25 实为 identity 反向检查非此类；G4.ss 现有 id 清单〔position/characters/facts_ops/summaries/arcs/particle_ledger/pending_hooks/matrix_structure 等〕无任何 diff 面积类，G2.11 只记删除行）：

- **`incremental_only` 降格（r3；r4 补先例）**：diff 面积 >50% → **WARN（shadow 量化面）**，主修法=**反馈定向增强**——全量重写型 FAIL 的反馈自动附「定点单行编辑指令＋类别词表＋粗体式格式枚举」（复用 `_enrich_g4_feedback` 静态模板增强先例，chapter_loop.py:1121——「册上正字」「YAML 式」两次手工修的教训；**长度族已有一半先例（r4 补引）**：`_length_family` 判定（chapter_loop.py:1198-1214）已对 G4.word_count/word_band/chapter_band/scene_domain 附「持久化草稿＋扩写不重写」指令（escalation #024/#026）——扩面挂此既有机制，勿建平行通道）。检测职责已由 matrix_structure content_dropped 覆盖 ≥60%（卷一五次复发全部被它抓到，缺的是反馈定向性与事前量化）——不再新建 FAIL 门；
- **SKILL 铁律子项撤销（r3）**：`shenbi-state-settling` SKILL 铁律 0（SKILL.md:94-103）已存在且更严（「ABSOLUTELY NEVER modify 现有行」append-only）——r2 拟增「只许单行编辑」与其直接冲突（松动既有约束），撤销；仅在铁律 0 段附一行指路「定点编辑反馈见 incremental 通道」；
- **drafting 打摆切换（r5 计数口径定稿：口径a 不分族连击）**：同 (skill=`shenbi-chapter-drafting`, chapter) **seq 序连续 RETRY 记录 ≥4 次 → 反馈模板自动切「定点扩写」模式**（明确段落锚 + 目标字数差 + 逐字 token 白名单），不再发整档约束重述。**计数口径（r5 回放定稿——「长度/结构族才计入」门控在全语料证伪；r5.1 钉断链锚定）**：**每条 RETRY 记录（reason.kind 不分族：monitor_rewind 与 g4_hard 同计）连击 +1**；**断链锚定=章循环状态机（r5.1——trace 词表实测无终态 action〔全集仅 AUDIT_PASS/DISPATCH/GATE_FAIL/RETRY〕，不断链的 trace 派生不可实施）**：执行面计数器落 `chapter_loop` 既有 per-chapter retry 状态族（retry_counts/soft_fail_trackers 同域），**episode=章状态机对本章 drafting 循环的生命周期**——章推进/升级/人工熔断即随章状态重置，已完章重开=新 episode 从零计；**交织的 DISPATCH 不断链**（RETRY→DISPATCH→RETRY 是重派循环本体，ch25 实测 seq 505-546 流形）；**loop_id 不作计数器**（ch25 实测 [1,2,3,4,1,2,3,4,2,3,2,3,1,2] 熔断重置、ch29 [1,2,3,1]——loop_id max 会漏触发）；trace `seq` 序聚合仅为观测/测试回放面（observe_report；卷一各 key 单 episode，回放数值与执行面等价）。**回放实证**：被咬六章 ch25×14/ch31×5/ch27/29/33/35×4 在口径a 下**全部 ≥4 触发、零假触发**（其余章最长 3）；若按「长度/结构族才计入」（r4 口径）ch25 最长连击仅 **3 永不触发**（卷一最重打摆章漏网）、六章中仅 ch29 触发——打摆的实弹签名是**混合族连续全档重写**（ch25 族并集=scene_domain+word_band+chapter_band+G4.cd+XC+CH 全混），非单族纯化。
- **分族表（r5 重定位：反馈路由面，非连击门控面）**：RETRY 载荷分族用于**切换后的反馈定向路由**与 observe_report 观测面。`monitor_rewind.reason.issues` 前缀 7 族 147 条全表（r5 回放补全 r4 漏记的 G4.cd/XC 两族）：`scene_domain`×61/`word_band`×19/`chapter_band`×19/`G4.cd`×31（**前缀内含章号 token**，形如 `G4.cd ch25:…`）/`composition`×9/`CH`×4/`XC`×4——路由：长度族（word_band/chapter_band/G4.word_count）→ `_length_family` 既有「持久化草稿＋扩写不重写」定向（chapter_loop.py:1198-1214）；结构族（scene_domain/composition/CH）→ 场景结构修复定向；G4.cd/XC 族 → 内容门定向（交叉 T1 引句/T6 数字锚修复面）。35 条 monitor_rewind 全部为 chapter-drafting 且 `check_ids` 全空、信号在 `reason.issues`（r4 勘误维持：r3「47 条全带 check_ids」不实）。`g4_hard.reason.check_ids` 兜底合流（12 条全 planning 族 G4.cp.*，drafting 真实 g4_hard=0；**check_id 剥可选 `G4.` 前缀归一**——r5 实测 1 条 `cp.prop_decl:…` 无前缀）。DISPATCH `failure_class` 实弹 361/0 全空（r2 钦定路径废弃）维持；**不从反馈文本判读、不扩 FailureClass 枚举**（r2 前置小任务作废）；loop_id 聚合仅存 observe_report 观测面（observe_report.py:57 per-(skill,chapter) max loop_id 表），不参与触发判定。卷一战术沉淀（「打摆>5 轮切手工」）的代码化，阈值 4 给自动路径留裕量。
- **TDD**：反馈定向增强单测（重写型 FAIL → 反馈含定点指令）；打摆切换单测（口径a：ch25 型连击 4 次且 loop_id 中途重置 [1,2,3,4,1,…] → 仍切换；DISPATCH 交织不断链；**章状态机推进 → episode 计数器重置；已完章重开=新 episode 从零计**；planning key 不触发）；路由单测（长度族 issue → 反馈附 _length_family 扩写定向；G4.cd/XC → 内容门定向）；g4_hard check_id 无 `G4.` 前缀仍归族（cp.prop_decl 实例）。

## 5. T5 · follower 完成语义 + 指标面补全（＋声明快照同点位）

- `_complete_chapter`（chapter_loop.py:2139）束感知完成时**批量写全 bundle 成员**：`chapter_states[str(ch)].status="complete"` 全员 + per-chapter 检查点已升（既有）——修 18/18 假 pending（r5 复核：`pipeline-state.json` **`chapter_loop.chapter_states`**〔顶层无 chapter_states 键，r3/r4 锚路径漏 chapter_loop 层级〕实测 pending=18 恰为全部偶数章〔follower〕、complete=18〔leader〕；**resonance 缺失钉死=8**〔r5 口径：metrics/longitudinal-report.json `per_chapter` 面，覆盖 ch1-30（n_done=30，**ch31-36 为行整体缺席——报告生成于 ch30 checkpoint，非 present=false**，r5.1 注）；缺失章 ch6/8/10/20/22/26/28/30 **全偶数=follower**——与束语义根因严丝合缝；r3 记 20/r4 记 14 两口径均不复现，以 per_chapter 缺失口径为准〕；status 写点仅 leader 一处 :2160，游标 `chapter + len(bundle_chapters)` 直接跳过 follower :2195）；
- **同点位接续（r3 改写）**：#82 T0 已落地并在同函数 bundle 循环（:2162-2169）为**全员**写 `declared` 快照——注释明示「#83 T5 routes its batch status write through the same per-chapter function」；r2 的「一个 PR 两件事」前提因 #82 先行合并失效，T5 在既有循环内补 `mcs.status=COMPLETE` 一行即可（纯升格既有）；
- resonance 行：follower 章由束级评分拆行或显式 `bundle-merged` 标记（longitudinal fail-closed 读到标记跳过单章断言、束级断言替代）——不再静默缺行；
- 纵向采集表自动回填：`tools/report_longitudinal.py` 增 `--emit-ledger-rows N M` 从 trace/cost 生成台账缺行草稿（ch5-10/19-24 挂账清偿工具化）。
- **TDD**：双章束完成后两章 status 均 complete；resonance 标记路径单测；快照写入断言（详见 #82 T0）。

## 6. T6 · 正文本体数字锚（正文↔truth 的最小可判定集）

结构化可判定的三个数值不变量（L-C 铁律内的）：

- **余额锚 `balance_value_drift`**（G4.cd，WARN→束级 FAIL）：`truth/particle_ledger.md` 现值（一百零三文）数字化后，本章正文出现**同句式异值余额**（「一百一十三文」且本章无对应支出 ops 声明）→ WARN；章首首现余额 ≠ 前章末值 → FAIL（ch26:L26 类）。金额噪声用强锚限定：只认「(一共|还剩|只剩|袋底|余额)[^。]{0,6}N文」句式；
- **计数锚（r2 并轨 F17；r5 判据回放定稿）**：不另起提取器——「名数[^。]{0,12}」pattern 并入 F17 `cd.counter`（chapter_drafting.py:182-260）的 prose 总数族提取器，作为其扩展面（门 ID 沿用 F17 域；两套 prose 计数提取器并存=维护面翻倍；ch28「五个」漏网实证现行 pattern 族只认「N个名字」形态——扩族而非重建）。**判定（r5 全语料回放定稿——r4 判据 ③「声明终值」口径对 +0 单声明全误红）**：① **N+M 解析扩面**——`_COUNTER_DECL_RE`（chapter_drafting.py:166）现只匹配 `+1` 形（r5 回放：全语料 9 条声明仅捕 2 条、+0 六章全盲），扩兼容 `+N` 全形态（读出基值/增量，含 `4 +1` 空格变体）；② **计划内部矛盾门**——同 counter 多条声明**终值（基值+增量）互斥** → FAIL（ch28 双声明实证：:88 `计数: 鉴录名数 4+0`〔final 4〕vs :100 `4 +1`〔final 5〕→ finals {4,5} 稳红——r5 回放维持）；③ **基值==facts 门（r5 新口径）**——每条声明**基值 == facts 现值（check 时点——`load_facts(FactsDim.COUNTERS)` 在 G4.cd 运行时读现值，chapter_drafting.py:536-538/:627 接线实锚）**，不等 → FAIL（r5 回放：+0 六章 ch25/26/27/29/30/36 base4==facts4 **全绿**——r4 判据 `declared_final != facts+1` 对六章推演 4≠5 全误红；ch9 `3+1` 为 check 时点 facts=3 的时序绿，现终态 4 即其 +1 落地——**绿测夹具须构造 facts=3**（r5.1：照抄终态 4 会得红测））；④ **prose 面（r5 收窄：同句锚定＋剥 META）**——F17 词族面扩**锚词注册**（counter → 同句锚词集：鉴录名数 → 「《鉴录》」/「鉴录」；注册落点=`_WORD_FAMILY` 既有 dict，chapter_drafting.py:218-220——升格既有），总数/序数判定要求**锚词与计数同句共现**（**「同句」= `_SENTENCE_SPLIT_RE` 切分（chapter_drafting.py:91，[。！？；]，r5.1 钉——语料判定对该切分稳健）**）且正文取 strip_narrative_body 剥后（排自身 POST 行）；总数允许集={facts, 声明终值}。**r5 回放实证（ch30 假红全消）**：`:58 「经手」这栏，有七个名字`（船单语境，无锚词）排除、`:176 一个名字`（修辞性反问）排除、`:154 《鉴录》上四个名字` 真命中 ✓、`:186 POST 一个名字` 剥 META 排除——无锚定口径下 ch30 双误红。**②③④ 三 FAIL 支路 shadow 起（L-D）**；
- **来历锚（WARN）**：prop_registry 结构化新增 `provenance` 字段（地点+章号，settle 写侧扩一列；r2 核实现状：prop_registry.md 表仅 实体名/当前owner/经手事件 三列，地点与章号只散在散文里）；正文来历句（「(得|授|给|塞)」+道具名+「那夜/那天」）命中地点词 ≠ provenance → WARN（渡口/门洞类）。WARN 起步：词法地点匹配有假阳性，供检查点人工裁决，不自动 FAIL。
- **TDD**：红测（ch28 双声明内部矛盾/ch26 章首余额 103）；绿测（+0 六章单声明——r5 回放夹具；ch9 时序 3+1）；锚定负例（ch30 船单「七个名字」/修辞「一个名字」/POST 行计数）；金额强锚句式负例（价格句不命中）；扩族后「名数」句式命中正例。

## 7. T7 · 验收口径清偿（挂账项归位）

- **判据 5 声口口径**：`voice_lexicon` 标记字典换声口 token 族（复用 #76 ACCOUNTING_VERBS/自嘲句尾正则思路按角色分桶），五角色 4/5 阈值下可达——tools/regen_accept.py 判据 5 实现面替换 + 挂账节关闭（r2 核实：现实现 check_blind_recognition 4/5 阈值，vol1-ledger.md:75 挂账「签名句命中率 4-33% 不可达」，工具无豁免分支）；
- **#80 前向门回放口径裁定**：manifest 门行对已生成章不回放（文档化入 docs/framework/gates.md #80 节 + regen_accept 判据 2b 读法注释——卷一 10-29 记录已剥离，卷二按新口径执行；r2 核实：gates.md 现无 #80 节，口径只在 regen-vol1-continue-prompt.md:83 挂账）；
- **声明面漂移清单（r3 定案：并入 T3 工具）**：scene_hook 11 行 + ch10 voice_density + ch11 无 META 块——作 `lint_outline_truth_drift` 的 `--declarations` 子命令（同一对账工具族，数据源=plans/chapters 声明面 vs 正文；不另建独立 linter）一次性输出修复清单，随 #84 T0 清偿；同时兜底 T2 手工改文路径的事后对账。
- **TDD**：token 族归属单测；回放口径文档 + 判据读法回归。

## 8. 非目标（防过度工程）

- 不做正文语义级不变量机器判定（矛盾检测交 G3.4/评审——T6 只做数字/清单枚举）；
- 不建大纲双向同步机制（人工裁定改节点 vs canon 附件，工具只报不写）；
- 不追溯回填 ch1-24 的 follower 指标面（历史证据面不动原则；只保证卷二起写全）；
- timeline 陈旧行（ch23 备注类）随 #84 T0 手工清，不造通用 timeline linter。

## 9. 验收（=卷二防复发判据）

1. 全部新门/工具红测→绿 + `just check` exit 0；新 FAIL 门 shadow 位默认 true，首束零误伤后转正；
2. 卷二首束实弹：settle 反馈定向增强生效（重写型 FAIL 反馈附定点指令）、双章 status 全 complete、POST 引句门零 FAIL（首月≥20 章窗口）；
3. 束前 lint_outline_truth_drift 零悬空 finding（或全部裁定归档）；
4. 正文本体数字锚：卷二余额/计数零漂移（WARN 面人工裁决记录在台账）；
5. regen-accept 判据 5 从「口径失配挂账」转绿。
