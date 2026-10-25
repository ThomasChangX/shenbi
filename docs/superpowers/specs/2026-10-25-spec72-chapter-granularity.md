# Spec #72 · 平台章粒度改革（chapter-granularity）

> **Date:** 2026-10-25 | **Status:** Active (Revised 2026-10-25 · 价值门驳斥复核：施工面四处修正 + 保量数学自洽化 + 地板口径统一) | **Severity:** 🟥 P0（地基） | **方法:** 方案 C——平台章原生粒度 + 场景簇批量派发（一次派发 2 章）+ 声明式发布切分 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** 无 | **范围:** genre-config 常量与平台参数（含契约闭键集四站）/ novel.json 章数口径 / chapter-planning 与 chapter-drafting 双章 bundle 契约 + chapter_loop 派发循环 / 确定性拆分器 + scenes sidecar / G4 逐章校验扩展 / release_split v2 / volume-budget 重排接线

> 源自 2026-10-25 总设计 `2026-10-25-novel-market-overhaul-design.md` §2（诊断背景与决策路径见总设计 §0）。用户决策：双平台（起点粒度生成为主、番茄发布层适配）；方案 C（原生+批量派发）。

## 1. 定位与边界

- 问题：`chapter_word.default=7600` 锚定了 1316 章的生成粒度，每万字节拍数 ≈1（头部 ≈3）；release_split 启发式切分不带爽点/钩子意识，切分点打乱节拍布局。
- 本 spec 改生成与发布的**粒度合同**，不改内容规则（引擎/节奏归 #73/#74）。
- 卷界按字数锚定不变（12 卷历史锚不动）；旧九章全弃，无迁移包袱，旧启发式直接退役。
- **存量时序约束**（rev1）：本 spec 落地后、#79 删旧章前，不对 `novel-xinghuo-vol1` 现存 10 章（约 7600 字/章）执行 G2/G4（新字数带下必红）；pipeline-state 的 1316 章口径由 #74 重排 + volume-budget `--apply` 收敛。

## 2. 施工面

1. **常量与参数**（rev1 重写——真实闸口四站 + 项目面）：
   - `novel-xinghuo-vol1/genre-config.json`：`chapter_word` 7600/7200/12000 → **3200/2800/4000**；note 重写（双平台口径 + 保量数学见下）
   - 新增顶层键 `primary_platform: "qidian"`（枚举 `qidian|fanqie`）；番茄更带进 `chapter_word` 子块：`fanqie_update: {min: 1800, max: 2800}`（`chapter_word` 子键不受顶层闭键集约束）
   - **闭键集四站同步**（缺任一站新顶层键被 G4 拒）：`src/shenbi/contracts/ownership.py` GENRE_KEYS（:39-45 frozenset）+ `src/shenbi/contracts/skills/genre_config.py`（Pydantic 字段 + `_top_level_keyset` 校验 :51-64）+ `skills/shenbi-genre-config/SKILL.md`（模板 chapter_word 块 :122-126 现为 2200/2000/4500 → 3200/2800/4000 + note 重写 + 顶层闭键集规则行同步）
   - `novel-xinghuo-vol1/novel.json`：`target_total_chapters` 1400→**3300**（保量自洽：10M/3300≈3030 ≤ 3040 = 0.95×3200；预算章数语义=允许 ~5.6% 余量，同旧 1400 vs 1316 口径）；`total_chapters` 不手改——保持 volume-budget `--apply` 写回通道（实际重排归 #74）
   - **地板口径统一**（rev1）：G2/G4 每章硬地板从读 `default` 改读 `chapter_word.min`（=2800，与拆分器字数带下界同源）——消解「拆分器放行 2800-3199 但 G2/G4 地板 3200 拒」的自相矛盾；`default`(3200) 只用于章数数学（G0.3 ceil、volume_budget `_implied_total`、length_normalizing 目标带中心）。G6 的每章字数口径按现状语义在 plan 阶段取证后钉死（观察项可留 default，硬闸必须 min）
   - 总章数 ceil(1000万÷3200) = **3125 章**
2. **chapter-planning 双章 bundle**（`skills/shenbi-chapter-planning/SKILL.md`）：一次派发输出两份独立备忘（writes 增 `chapter-(N+1)-plan.md` + 对应 decisions sidecar）——各自章尾张力拍、场景字数预算（2-3 场景/章）、每场景收束钩声明；共享一次上下文读取。
3. **chapter-drafting 场景簇契约**（`skills/shenbi-chapter-drafting/SKILL.md`）：一次派发 = 连续 2 章（约 6400 字）；输出带标记的簇产物（`===CH:n===` 章界 + `<!--SCENE-->` 场景界）+ 两份章级 decisions sidecar（decisions 属 LLM 产物，拆分器不得代造）；每章末尾必须落在备忘声明的章尾钩上。SKILL 契约 writes 从 `chapters/chapter-N.md` 改为簇产物路径（具体形态 plan 钉死）。
3b. **chapter_loop 派发循环改造**（`src/shenbi/pipeline/chapter_loop.py`，rev1 补——原文施工面 2/3 只写 SKILL.md，实际单章步进机在此）：CHAPTER_STEPS（:143-264）单章步进 → 双章 bundle 步进：planning 一次产两备忘、context 组装覆盖两章、drafting 一次产簇、游标/checkpoint/ghost-chain 守卫按双章语义、审计 savepoint `_wave_savepoint` 按簇记账。
4. **确定性拆分器**（`src/shenbi/pipeline/` 新增，如 `scene_splitter.py`）：按 CH 标记拆 chapter-n.md；校验每章字数带 2800-4000、场景标记数 ≥2、标记缺失=硬失败（exit 1，熔断重派）；标记剥离正文，场景边界 + 各场景末行写 sidecar `scenes.jsonl`（章号/字符位/收束钩原文）。**必须被 chapter_loop 接线调用**（drafting 簇产物 → 拆分 → 章文件 ×2 + scenes.jsonl 追加 + manifest 记账）——独立存在零调用 = dead-wire 禁止。`scenes.jsonl` 在 `docs/framework/truth-files.yaml` 登记（`producer: pipeline` 形态，含 `site/framework/` 副本同步）。
5. **G4 逐章校验扩展**（`src/shenbi/gates/g4/chapter_drafting.py`）：现状 `chapter_end_hook`（:435-484）已按文件（=逐章）执行启发式（疑问句/张力词/账目行）——rev1 订正原文「章尾张力拍逐章生效」措辞；**新增**：每章场景数 ≥2 校验（读 scenes.jsonl）、收束钩「声明 vs 实际」匹配校验（plan 备忘每场景收束钩声明 ↔ scenes.jsonl 各场景末行）。
6. **release_split v2**（`tools/release_split.py`）：起点档 1 章=1 更（重题直发）；番茄档以场景为原子打包（打包域=已收束窗口场景序列，允许跨章组更），硬规则四条——每更 1800-2800 字、更边界只落 SCENE 边界、每更必须以声明的场景收束钩收尾、禁切场景中部，违反即切分失败。旧启发式分类器退役（SCENE_TRANSITION_WORDS/TIERS 常量）。**已收束窗口数据源**（rev1 补）：pipeline-manifest.json 逐章闸记录（已收束=该章全部 per-chapter 闸 PASS）+ scenes.jsonl。**同批重写债披露**（rev1 补）：`tests/unit/tools/test_release_split.py` 38 用例随 v2 重写为声明式切分用例。冻结机制保留——当前项目零已发布更 = 零冲突退役窗口，v2 须在任何真实发布前落地。
7. **volume-budget 重排接线**（`src/shenbi/pipeline/volume_budget.py`，rev1 订正路径——原文误写 `tools/`）：章数数学随 default=3200 自动生效（`_implied_total` :190-205）；`word_floor` 口径随地板统一改 min；`--apply`（:329-340）保持只写 novel.json `total_chapters` + 骨架同步。卷内章数按 3200 重排（卷一 45.6 万字 → 约 143 章）——重排执行归 #74，本 spec 只接数学与工具。
8. **审计批量**：LLM 审计同维度按簇批量派发（×1.19 而非 ×2.4）——落点 `chapter_loop.py:3010-3121` 审计两波 prompt（`Execute {skill} for chapter {n}` → 簇形态）+ `_wave_savepoint`/`_get_audit_history` 记账粒度；G2/G4 逐章执行（本地代码无 LLM 成本）。

## 3. 风险与对策

| 风险 | 对策 |
|---|---|
| 章间弧线渗漏（2 章写成一条长弧，第二无独立钩） | 双备忘各自独立章尾拍 + 拆分器逐章字数带校验 + G4 逐章验钩；违例章级重派 |
| 批量上下文变大 | 6400 字低于已验证的 8000-10000 字单章负载，实际减负 |
| 场景标记漏写 | 拆分器硬失败熔断（沿用现协议） |
| 存量 10 章（7600 字）与新字数带共存（rev1） | §1 时序约束：#72-#79 间不对旧章跑 G2/G4；删除归 #79 |
| 字数带下界与 G2/G4 地板两套口径（rev1） | 地板口径统一读 min（施工面 1） |

## 4. 验收

- 拆分器对批量产物确定性拆分，逐章字数带/场景数/钩匹配校验全绿
- G4 逐章（非逐簇）通过；标记缺失路径熔断可用（负例测试）
- 番茄切分：每更 100% 落在声明的场景收束钩上、零场景中部切割（含跨章组更用例）
- `just check` 全绿；章数预算重排幂等复跑一致
- （rev1）G2/G4 硬地板=2800 与拆分器字数带下界一致性：同章 2800 字两闸皆过、2799 皆拒（测试表达）
- （rev1）novel.json target_total_chapters=3300 口径：G0.3 ceil=3125、保量不等式 0.95×3200 ≥ 10M/3300 成立、volume_budget `_implied_total` 复算一致（测试表达）
