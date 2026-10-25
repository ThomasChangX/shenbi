# Spec #76 · 声口与梗位执行层（voice-meme-wiring）

> **Date:** 2026-10-25（rev4 2026-10-26 阶段 3 三轮审查清偿） | **Status:** Active | **Severity:** 🟠 P1 | **方法:** 声口/梗位/金句三 lint + memo 通道注入 + 离线盲认判据 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** #73（市场参数）、#72（备忘格式通道）、#74（卷纲梗位行重锚） | **范围:** plan_format v2 版本化 / planning+drafting SKILL 声口接线 / voice_lexicon 共享词表 / lint_voice_meme 工具 / G4.cd 金句位双型 / G4.vo 梗位行结构 / genre_config 数值域定档 / 对白差异化离线盲认 / #77 校准条款同步

> 源自总设计 §3。问题依据：protagonist.md 定「贫嘴吐槽役、越惨越贫」，九章正文贫嘴声口出现 ≤4 次；volume_map 梗位「班味的内核全球统一」规划 0 落地；十余角色对白全员同腔（格言腔问答体），遮署名无法盲认；金句全是收敛型静句。

## 0. 机制裁定（阶段 3 审查落定）

- **注入通道 = memo（备忘），本批 protagonist-only**：planning 契约 reads **新增** `characters/protagonist.md`（全卡读——voice_profile 是 frontmatter，字段级切片不可用，token 成本入 dispatch 读面）；备忘模板**新增**「声口要求」行（protagonist 口癖/句式要点，planning 从卡生成）——此为新模板字段，G4.cp 校验其存在（v2 起）；drafting SKILL 正文增强制段（消费备忘声口要求行 + 金句位类型声明）——drafting 契约 reads 不动。**在场多角色声口注入显式 deferred**（阻塞项 = 备忘角色行 + 逐卡 reads 面扩展成本，归后续批；deviations 记录）
- **计数口径（确定性）**：贫嘴密度 = 全章正文域（剥 SCENE 标记行/META 块）内**去重信号数** ≥ `voice_density_min.min_per_chapter`；信号 = protagonist catchphrases（卡面原串）∪ 账房动词族命中（共享词表），不依赖对白归属解析器（M3 裁定：归属解析不入本 spec 范围，catchphrase 本身即主角专属串）
- **共享词表**：`src/shenbi/text/voice_lexicon.py` 单一定义（账房动词族 + 自嘲反问句式正则），lint 与 G4.cd 同源引用，版本化注释
- **#77 调和条款（口径区隔）**：本 spec 密度口径计**字面记账动词/口癖串**用法；#77 喻体域集中度计**比喻句喻体**（「像账册一样」类）——同一账房词汇的字面用法与喻体用法分属两口径，#77 落地时以实测分布校准阈值（校准条款入 #77 spec）；声口测量基建归属本 spec，#77 引用
- **G6.8 分工**：G6.8 保持卡面卫生（voice_profile 存在性）；本 spec 拥有章级密度、章级金句类型、**卷级登场条件化 catchphrase 出现窗**（G6.8 语料级卡级出现 WARN 与卷级窗并存——卷级窗为本 spec 消费口径，G6.8 保持卡面完整性口径）；解析器沿用 G6.8 有界段提取先例

## 1. 施工面

1. **贫嘴声口接线**：planning 备忘声口段（§0 通道）；`tools/lint_voice_meme.py --mode chapter`：贫嘴密度计数（§0 口径）——低于下限 = **G4.cd 硬 FAIL——适用域 = dispatch 轮闸流（v2 章）**；对 v1 旧章的独立复跑（`shenbi-validate G4` 实数据离线）密度报告为 WARN/跳过（v1 通道保证覆盖密度与金句位两项）；执行层：lint 函数并入 G4.cd（`shenbi-text/voice_lexicon` 同源），实数据离线跑、单测构造用例入 CI
2. **梗位落地 lint**：**梗位清单语法契约**——卷纲「金句、母题物象与梗位」行内 `梗位复用：` 段（至下一 `｜` 或行尾）内**全部「」跨度**为梗位项（覆盖 `第N章「X」` 带章号形态；顿号/章号前缀仅作分隔不计入串）；G4.vo 增结构校验（段内引号短语 ≥1 否则 FAIL）；计数 = 引号内串在卷内正文**精确串出现**次数；卷一行未引号的「记账式吐槽」类**形态型**梗位**不入精确串 lint**——由账房动词族密度 lint 承担（口径声明）；`--mode volume`：每梗位 ≥ `meme_quota.per_volume`，缺额 WARN 行入 truth/audit_drift（`[梗位] <名> 卷内 n/m——下章 PRE_WRITE_CHECK 补触`），卷末仍未达 = lint FAIL——**执行域声明**：#79 重生成循环内强制（#79 spec 判据 4 已接线）；卷二+ 常驻执行点归各卷 outlining 收束批（与 #74 过渡态政策同款，非静默遗漏）
3. **对白差异化抽检（离线判据，F947 重述）**：(a) **确定性盲认测试**——构造五角色标注对白语料（G0.9 结构性构造：每角色口癖/句长带/语气词按已知率植入，**含混淆行（双角色标记并存）与零标记行**）+ 确定性标记分类器（逐行卡面标记 argmax 归属；**平票/零标记 = 无归属行，计为该角色漏认**），五角色归属正确 ≥4/5 且分离边际（次高标记数 < 最高×0.6）；(b) 真遮署名盲测为 T1 生成验收（shenbi-dispatch + 独立 G3.4 评分，明示 CI 外）；(c) 配角声口抽检 = **卷级出现窗，登场条件化**（`--mode volume`：**卷内登场**的配角卡（登场集 = volume_map 节点表/章摘要可得名集）catchphrase 卷内 ≥1 次，WARN——未登场卡不检；章级逐章出现性会淹没 audit_drift，不做章级）
4. **金句双型配额（plan_format v2 版本化落地）**：**引入 `plan_format: v2` 版本令牌**（AGENTS 契约升级纪律：第二个硬闸必备 memo 字段批次 → 版本化取代第三件 bespoke 迁移工具；无令牌 = v1 默认；**令牌位置 = 段1 首行** `plan_format: v2`——备忘 H1 标题行前置规则不破坏，非 YAML frontmatter）。金句位格式 v2 扩为 `静/燃｜<写法三选一>｜<落点场景>`，**三点同步**：memo 段1 金句位行 → drafting PRE_WRITE_CHECK 照抄行 → 章尾钩行，三处一致（v2 校验）；G4.cd 金句位正则**版本条件化**（v1 旧格式仍过——真实产物 fixtures 与旧九章回归集均为 v1，不破坏 CI/回归；v2 缺类型 token = FAIL）；G4.cp 两查分立：v2 备忘 ⇒ 声口要求行存在；令牌值合法（v1/v2 之外 FAIL）；**每卷燃句下限** = market_params 新键 `quote_type_quota {burning_per_volume: N}`（可选键，**缺省代入属 lint 消费端**——validator 保持无副作用；三态校验：缺块 PASS/越域 FAIL）；drafting 金句位备忘声明类型；`--mode volume` 计数 lint（v2 章为分母）

## 2. genre_config 数值域定档（#73 遗留债务清偿）

- `voice_density_min.min_per_chapter`: int ∈ [0,5]（当前 2）
- `meme_quota.per_volume`: int ∈ [1,20]（当前 3）
- `quote_type_quota.burning_per_volume`: int ∈ [0,10]（新键，缺省 2）
- 三态校验 + 越域 FAIL 用例（G4 genre_config 既有测试面扩展）

## 3. 验收

- 贫嘴密度：旧九章真阳性回归（≤4/9 章 ≥2 信号 → lint 报缺）+ 构造达标章零误报；**下限唯一真源 = voice_density_min.min_per_chapter**（不硬编码 2）
- 梗位：G4.vo 结构校验对无引号短语卷纲 FAIL；lint 对卷纲梗位表全覆盖；**落地面真阳性 = 旧九章 0/3 缺额如实报告 + 构造语料计数正确性**（「班味类卷内 ≥3 达标」移 #79 判据 4 复核项——#76 收口时旧章尚未重生成，达标不可判）；缺额 WARN 行格式可被 drafting 下章消费
- 盲认：确定性测试五角色 ≥4/5 + 分离边际（CI 内）；T1 盲测声明为 CI 外生成验收
- 金句双型：plan_format v2 机制落地（令牌/三点同步/版本条件化检查）；v2 缺类型 token 的金句位 FAIL 而 **v1 旧格式 fixtures 与旧九章回归集不破坏**；卷级燃句计数 lint（v2 章分母）
- **契约升级声明（修正）**：plan_format v2 为 opt-in 令牌——新批 memo 起用 v2，旧 memo/ch1-10 旧章保持 v1 直到 #79 隔离重生成（#75 回归集与 CI fixtures 依赖旧章在场，v1 路径必须持续可跑）
