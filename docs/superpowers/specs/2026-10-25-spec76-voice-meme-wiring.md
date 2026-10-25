# Spec #76 · 声口与梗位执行层（voice-meme-wiring）

> **Date:** 2026-10-25（rev2 2026-10-26 阶段 3 审查清偿） | **Status:** Active | **Severity:** 🟠 P1 | **方法:** 声口/梗位/金句三 lint + memo 通道注入 + 离线盲认判据 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** #73（市场参数）、#72（备忘格式通道）、#74（卷纲梗位行重锚） | **范围:** planning/drafting SKILL 声口接线 / voice_lexicon 共享词表 / lint_voice_meme 工具 / G4.cd 金句位双型 / G4.vo 梗位行结构 / genre_config 数值域定档

> 源自总设计 §3。问题依据：protagonist.md 定「贫嘴吐槽役、越惨越贫」，九章正文贫嘴声口出现 ≤4 次；volume_map 梗位「班味的内核全球统一」规划 0 落地；十余角色对白全员同腔（格言腔问答体），遮署名无法盲认；金句全是收敛型静句。

## 0. 机制裁定（阶段 3 审查落定）

- **注入通道 = memo（备忘）**：planning 读 protagonist.md（voice_profile 全读）+ 在场角色（memo 角色行的既有数据源），在备忘模板增「声口要求」段（在场角色各一行：口癖/句式要点）；drafting SKILL 正文增强制段（消费备忘声口要求行 + 金句位类型声明）——drafting 契约 reads 不动（备忘是其既有通道），无字段级读取改造
- **计数口径（确定性）**：贫嘴密度 = 全章正文域（剥 SCENE 标记行/META 块）内**去重信号数** ≥ `voice_density_min.min_per_chapter`；信号 = protagonist catchphrases（卡面原串）∪ 账房动词族命中（共享词表），不依赖对白归属解析器（M3 裁定：归属解析不入本 spec 范围，catchphrase 本身即主角专属串）
- **共享词表**：`src/shenbi/text/voice_lexicon.py` 单一定义（账房动词族 + 自嘲反问句式正则），lint 与 G4.cd 同源引用，版本化注释
- **#77 调和条款**：#77 喻体域集中度在**叙述域**（排除对白）计算——账房腔属对白域，两指标不冲突；声口测量基建归属本 spec，#77 引用
- **G6.8 分工**：G6.8 保持卡面卫生（voice_profile 存在性/卡级 catchphrase 出现）；本 spec 拥有章级密度与章级金句类型；解析器沿用 G6.8 有界段提取先例

## 1. 施工面

1. **贫嘴声口接线**：planning 备忘声口段（§0 通道）；`tools/lint_voice_meme.py --mode chapter`：贫嘴密度计数（§0 口径）——低于下限 = **G4.cd 硬 FAIL**（强制段使达标可达）；执行层：lint 函数并入 G4.cd（`shenbi-text/voice_lexicon` 同源），实数据离线跑、单测构造用例入 CI
2. **梗位落地 lint**：**梗位清单语法契约**——卷纲「金句、母题物象与梗位」行内 `梗位复用：` 后「」引号短语、顿号分隔、可选 `（类：梗）` 标注；G4.vo 增结构校验（引号短语 ≥1 否则 FAIL）；计数 = 引号短语在卷内正文**精确串出现**次数；`--mode volume`：每梗位 ≥ `meme_quota.per_volume`，缺额 WARN 行入 truth/audit_drift（`[梗位] <名> 卷内 n/m——下章 PRE_WRITE_CHECK 补触`），卷末仍未达 = lint FAIL（卷末执行点 = 卷收束工具链调用，#79 重生成循环强制）
3. **对白差异化抽检（离线判据，F947 重述）**：(a) **确定性盲认测试**——构造五角色标注对白语料（G0.9 结构性构造：每角色口癖/句长带/语气词按已知率植入）+ 确定性标记分类器（逐行卡面标记 argmax 归属），五角色归属正确 ≥4/5 且分离边际（次高标记数 < 最高×0.6）；(b) 真遮署名盲测为 T1 生成验收（shenbi-dispatch + 独立 G3.4 评分，明示 CI 外）；(c) 章级抽检 = 在场角色卡 catchphrase 在本章出现性检查（G6.8 卡级先例延伸，WARN 级）
4. **金句双型配额**：金句位格式扩为 `静/燃｜<写法三选一>｜<落点场景>`（类型轴正交于写法轴，PRE_WRITE_CHECK 行与章尾钩行双落点同步）；G4.cd 金句位正则更新；**每卷燃句下限** = market_params 新键 `quote_type_quota {burning_per_volume: N}`（可选键，缺席取默认 2，三态校验：缺块 PASS/越域 FAIL）；drafting 金句位备忘声明类型；`--mode volume` 计数 lint

## 2. genre_config 数值域定档（#73 遗留债务清偿）

- `voice_density_min.min_per_chapter`: int ∈ [0,5]（当前 2）
- `meme_quota.per_volume`: int ∈ [1,20]（当前 3）
- `quote_type_quota.burning_per_volume`: int ∈ [0,10]（新键，缺省 2）
- 三态校验 + 越域 FAIL 用例（G4 genre_config 既有测试面扩展）

## 3. 验收

- 贫嘴密度：旧九章真阳性回归（≤4/9 章 ≥2 信号 → lint 报缺）+ 构造达标章零误报；**下限唯一真源 = voice_density_min.min_per_chapter**（不硬编码 2）
- 梗位：G4.vo 结构校验对无引号短语卷纲 FAIL；lint 对卷纲梗位表全覆盖，班味类（引号串「班味的内核全球统一」）卷内 ≥3 精确串；缺额 WARN 行格式可被 drafting 下章消费
- 盲认：确定性测试五角色 ≥4/5 + 分离边际（CI 内）；T1 盲测声明为 CI 外生成验收
- 金句双型：G4.cd 对缺类型 token 的金句位 FAIL；双格式（PRE/钩行）一致校验；卷级燃句计数 lint；**契约升级声明**：金句位新格式自下批 memo 生效，ch1-10 旧章随 #79 重生成（无在途 artifacts 受影响）
