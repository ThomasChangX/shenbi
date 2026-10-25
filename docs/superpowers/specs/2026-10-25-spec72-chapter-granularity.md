# Spec #72 · 平台章粒度改革（chapter-granularity）

> **Date:** 2026-10-25 | **Status:** Active (Revised 2026-10-25 R1 驳斥复核施工面修正 + R2 设计审查修复（修订×标记一致性/天花板统一/卷界奇偶/钩谓词）+ R3 设计重审修复（修订后重验新接线/scenes.jsonl 退役/章解剖/G2.6 口径/场景预算两型）) | **Severity:** 🟥 P0（地基） | **方法:** 方案 C——平台章原生粒度 + 场景簇批量派发（一次派发 2 章）+ 声明式发布切分 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** 无 | **范围:** genre-config 常量与平台参数（含契约闭键集四站）/ novel.json 章数口径 / chapter-planning 与 chapter-drafting 双章 bundle 契约 + chapter_loop 派发循环 / 确定性拆分器 / G4 逐章校验扩展 / 章节修订×场景标记一致性 / release_split v2 / volume-budget 重排接线

> 源自 2026-10-25 总设计 `2026-10-25-novel-market-overhaul-design.md` §2。用户决策：双平台（起点粒度生成为主、番茄发布层适配）；方案 C（原生+批量派发）。总设计 §2.3「修订路径：批量产物先拆分再按章修订」由施工面 9 承载；**本 spec 覆写总设计 §2.2 的 scenes.jsonl 边车条款**——场景边界真源改为章文件内标记，sidecar 索引整体退役（R3-I1：无消费方的索引 = dead-wire；章内标记可随时确定性重导任何所需信息）。

## 1. 定位与边界

- 问题：`chapter_word.default=7600` 锚定了 1316 章的生成粒度，每万字节拍数 ≈1（头部 ≈3）；release_split 启发式切分不带爽点/钩子意识，切分点打乱节拍布局。
- 本 spec 改生成与发布的**粒度合同**，不改内容规则（引擎/节奏归 #73/#74）。
- 卷界按字数锚定不变（12 卷历史锚不动）；旧九章全弃，无迁移包袱，旧启发式直接退役。
- **存量时序约束**：本 spec 落地后、#79 删旧章前，不对 `novel-xinghuo-vol1` 现存 10 章（约 7600 字/章）执行 G2/G4/G6（新字数带下 G2/G4 必红；G6.1 最少章数阈值 ceil(3125×0.5)=1563 vs 存量 10 亦红）。pipeline-state 的 1316 章口径由 #74 重排 + volume-budget `--apply` 收敛；并存期间唯一预期红面 = volume-budget 的 `re_budget_pending`（设计内报告；G0.3 只报告 ceil 从不对比 novel.json，无其他消费方炸）。
- **场景标记的耐久性合同**：`<!--SCENE-->` 场景标记**保留在终稿章文件内**（独占一行 HTML 注释，渲染不可见）；`===CH:n===` 章界标记只存在于 staging 簇产物。发布层生成更文本时剥离标记。场景边界唯一真源 = 章文件内标记；**无 sidecar**。

## 2. 施工面

1. **常量与参数**：
   - `novel-xinghuo-vol1/genre-config.json`：`chapter_word` 7600/7200/12000 → **3200/2800/4000**；note 重写（双平台口径 + 保量数学 + 番茄更带 1800 下限的用户决策依据——旧模板 note「平台红线 2000」为 2200 单档检索口径，#72 双平台决策取代）
   - 新增顶层键 `primary_platform: "qidian"`（枚举 `qidian|fanqie`，**optional**——存量 fixture 无此键不断负载，缺省时消费方回退 v1 默认）；番茄更带进 `chapter_word` 子块：`fanqie_update: {min: 1800, max: 2800}`
   - **闭键集四站同步**：`src/shenbi/contracts/ownership.py` GENRE_KEYS（:39-52）+ `src/shenbi/contracts/skills/genre_config.py`（Pydantic 字段 + `_top_level_keyset` :51-64 + `_OPTIONAL_TOP_KEYS` :21-22）+ `skills/shenbi-genre-config/SKILL.md`（模板 :122-126 2200/2000/4500 → 3200/2800/4000 + note 重写 + 闭键集规则行 **:317/:323/:416** 同步——顺带修既有漂移「9 必填（含 tropeInventory）」实为 8 必填）
   - `novel-xinghuo-vol1/novel.json`：`target_total_chapters` 1400→**3300**（保量自洽：10M/3300≈3030 ≤ 3040 = 0.95×3200；预算章数语义 = 5.6% 余量，同旧 1400 vs 1316 口径）；`total_chapters` 不手改——volume-budget `--apply` 写回通道（重排归 #74）
   - **地板与天花板口径统一**：`chapter_word_floor()`（shared.py:130-152）改读 `chapter_word.min`，回退链 **min → default → CHAPTER_WORD_FLOOR 常量**（min 缺席不落回硬编码地板）；三调用方 G2.6 / G4.cd / G4.ln.below_floor 一并生效。G2.7 弃硬编码双档（`CHAPTER_WORD_CEILING`/`_is_important_chapter` 的 10000/4500，g2.py:209-212）改读 `chapter_word.max`（4000）；G4.ln.above_ceiling 同源。**计数口径统一 `total_chars_md_text`**（G4.cd/拆分器同口径；genre-config note 本就声明 total_chars 口径，现状 G2.6/G2.7/G4.ln/loop 边界检查用 CJK-only `word_count_md` 是口径错位——2800 total ≈ 2400 CJK 会假红）。**消费方总表（带口径列，R4-I1 补全）**：
     | 消费方 | 字数源 | 读键 |
     |---|---|---|
     | G2.6 地板 / G2.7 天花板（g2.py:189/195/209-212） | total_chars_md_text | min / max |
     | G4.cd 字数带（chapter_drafting.py:332） | total_chars_md_text（现状已同） | min / max |
     | G4.ln 地板/天花板（length_normalizing.py:44,70-75） | **word_count_md → total_chars_md_text** | min / max |
     | chapter_loop `_check_word_count_bounds`（:1379-1406，WARN 观测） | **CJK 裸数 → total_chars_md_text** | min / max |
     | 拆分器字数带 / release_split v2 番茄带 | total_chars_md_text | min / max / fanqie_update |
     | G0.3 ceil / volume_budget `_implied_total` / G6.1 最少章数 / length_normalizing 提示层 | ——（数学，非逐章计数） | default |
     一律读配置单源，禁工具硬编码。**大章概念退役**：4000 为全书统一天花板，大节拍由发布层场景组更承接
   - **口径变更冲击面披露**（R3-I5）：floor→min 与 G2.6 口径统一使既有断言测试同批更新（fixtures `genre-config-xinghuo-probe17.json` 1700/1500、`snapshots/chapter-118/genre-config.json` 1700/1300 的地板断言、G2.6 CJK 口径用例）——fixture 文件本身不动（真实产物），测试期望值与口径随本批更新
   - 总章数 ceil(1000万÷3200) = **3125 章**；volume_budget `word_floor` 口径随地板统一改 min（权衡明示：2800-3199 章不再触发 budget 保量预警，聚层安全网改由 ±3 漂移守卫 + G0.3 保量不等式承担——接受）
2. **chapter-planning 双章 bundle**（`skills/shenbi-chapter-planning/SKILL.md`）：一次派发输出两份独立备忘（writes 增 `plans/chapter-{N+1}-plan.md` brace 形态 + 对应 decisions sidecar）——各自章尾张力拍、**场景字数预算两型规则（R3-I7 + R4-I3 组合约束修正）**：场景分两型——独立型 [1800,2000]（单场景成更）、配对型 [900,1400]（相邻场景配对成更）；**章组合约束**（保证章带 [2800,4000] 与更带 [1800,2800] 双可满足）：2 场景章 = 两独立型（和 [3600,4000]）；3 场景章 = 三配对型（和 [2800,4200] 取带内）或一独两配（和 [3600,4800] 取带内）；禁混出带外组合（拆分器按场景域硬校验，见施工面 4）。灰域 [1400,1800) 非绝对不可打包（如 1500+1300=2800 合法更）但属规划脆弱域——planning 禁用，拆分器对单场景字数落灰域即熔断回 planning；**每场景收束钩声明（钩原文一行）**；共享一次上下文读取。
3. **chapter-drafting 场景簇契约**（`skills/shenbi-chapter-drafting/SKILL.md`）：一次派发 = 连续 2 章（约 6400 字）；**全部产物走 staging**（bundle + 两份章级 decisions sidecar——`uses_staging` 既有约定，且 G4 文件解析对 staging 步有 staging/ 前缀语义，R3-M8）；bundle = `staging/chapter-{N}-bundle.md`，内含每章完整现行章结构：`===CH:n===` 行起章、双 H1（其二为章题）、`## PRE_WRITE_CHECK` 块、正文（含 `<!--SCENE-->` 标记行）、`## POST_WRITE_SELF_CHECK` 块（R3-I4：拆分章文件与现行单章产物**完全同构**，G4.pre/post、G2.8/2.9、release_split 双 H1 题机制零改动）；**每场景末行 = 备忘声明的收束钩原文**（逐字，谓词：声明文本剥空白后为场景末非空行子串）；每章末尾落在备忘声明的章尾钩上。
3b. **chapter_loop 派发循环改造**（`src/shenbi/pipeline/chapter_loop.py`）：CHAPTER_STEPS（:143-264）单章步进 → 双章 bundle 步进。**约束**：① bundle 不跨卷界——卷末奇数章 = 单章簇（step1 卷界 checkpoint 后重新对齐配对）；② step 完成度 bundle 原子（两章同进退）；③ ghost-chain 守卫要求两份拆分产物齐备；④ **新确定性步「拆分+晋升」**（drafting 步后）：拆分器消费 staging 簇 → 拆出 `chapters/chapter-N.md`(+N+1)（剥 CH 标记留 SCENE 标记）+ decisions sidecar 直通晋升 → 逐章 G4.cd 终验（drafting 步自身的 G4 面只验 staging decisions 的 G4.dec——bundle 非章形态不进 G4.cd；drafting 步 **output_path 不设 md 路径**，防 `_resolve_g4_files` 后缀路由把 bundle 误喂 G4.cd，R4-I8）；crash 恢复 = 从 staging 簇重放（拆分确定性幂等），staging 清扫机制不变（拆分步即时消费）；⑤ 审计按簇派发但**报告工件保持逐章**（`chapter-{n}-review-summary.md` 等下游 `_get_audit_history`/G3 形态零改动——簇 prompt 一次产出两章报告）；⑥ `_wave_savepoint` 按簇记账但两章 `audit_results` 皆落（缺 N+1 = 级联盲区）；⑦ **post-draft 内联块重挂**（R4-I2：现状 `:3731-3744` 的 `_check_volume_map_alignment`/`_run_post_draft_extract`/`_run_g4_checks`/`_check_word_count_bounds` 以 `"chapter-drafting" in step.skill` 触发且读 `chapters/chapter-N.md`——拆分步插入后该文件彼时不存在，四检查静默停摆）——整块改挂拆分+晋升步（章文件已存在的首个时机），两章各跑一遍。
4. **确定性拆分器**（`src/shenbi/pipeline/scene_splitter.py` 新增，由 3b-④ 新步调用——独立存在零调用 = dead-wire 禁止）：读 staging 簇，按 CH 标记拆章；校验每章字数带 2800-4000（读配置）、场景标记数 ≥2、**每场景字数落两型域 [1800,2000]∪[900,1400]（灰域即熔断，施工面 2 组合约束的执法点）**、CH/SCENE 标记完整（缺失=硬失败 exit 1 熔断重派，失败归类既有 `FailureClass.DETERMINISTIC_GATE`，不新增状态域）；剥离 CH 标记、保留 SCENE 标记；decisions sidecar 直通晋升。G2/G4 作用于拆分后章文件；staging 簇不进 G2 章检查（拆分器硬校验即其门）。**计数口径**：字数统计剥标记行——`strip_narrative_body` 与 G4.cd 自建段面（chapter_drafting.py:388-392）**两处**都须剥标记行（R3-M6）；G4.cd content_uniqueness 指纹（:354）哈希前同剥（R4-I10）。
5. **G4 逐章校验扩展**（`src/shenbi/gates/g4/chapter_drafting.py`）：现状 `chapter_end_hook`（:435-484）已按文件逐章启发式；**新增**：每章场景数 ≥2（读章文件内 SCENE 标记）；收束钩「声明 vs 实际」匹配（plan 备忘钩声明 ↔ 章文件各场景末行，谓词见施工面 3）；标记行不参与既有检查计数（施工面 4 两站点）。
6. **release_split v2**（`tools/release_split.py`）：起点档 1 章=1 更（重题直发——双 H1 题机制现状不动）；番茄档以场景为原子打包（允许跨章组更），硬规则四条——每更 1800-2800 字（读 `chapter_word.fanqie_update`）、更边界只落 SCENE 边界（读章文件标记）、每更必须以声明的场景收束钩收尾、禁切场景中部；打包算法 = 贪心组相邻场景命中 [1800,2800]；不可打包 = 切分失败（exit 1，报 offending 场景字数清单，回 planning 场景预算重派——熔断协议）；**更文本剥离标记（两档皆剥，R4-I9）**。旧启发式退役（SCENE_TRANSITION_WORDS/TIERS 常量/段落窗口算法 plan_releases 族）。**已收束窗口**（R4-I4 谓词钉死）：打包域 = 已收束章集合——数据源 pipeline-manifest.json 逐章闸记录，**已收束 := 该章每个 (skill,gate) 键的最近一条记录为 PASS 且拆分步 G4 键存在**（latest-per-key 语义——历史 FAIL 已修复不永久排除；drafting/拆分键缺席 = 章未走完全链，空洞不纳入）；`--through <N>` 显式覆盖。**CLI 合同不破**：位置参数 dir + `--platform`（缺省改读 `genre-config.primary_platform`，无键回退 v1 默认 fanqie）保留；`--title-pattern`/`--renumber-published` 保留。**同批重写债披露**：`tests/unit/tools/test_release_split.py` 38 用例随 v2 重写。冻结机制保留——当前零已发布更 = 零冲突退役窗口，v2 须在任何真实发布前落地。
7. **volume-budget 重排接线**（`src/shenbi/pipeline/volume_budget.py`）：章数数学随 default=3200 自动生效（`_implied_total` :190-205）；`word_floor` 口径随地板统一改 min；`--apply`（:329-340）保持只写 novel.json `total_chapters` + 骨架同步。卷内章数按 3200 重排（卷一 45.6 万字 → 约 143 章）——重排执行归 #74。
8. **审计批量**：LLM 审计同维度按簇批量派发（×1.19 而非 ×2.4）——落点 `chapter_loop.py:3010-3121` 审计两波 prompt（:3060/:3094 → 簇形态）+ `_wave_savepoint` :3079/:3117 按簇记账（3b-⑥）；G2/G4 逐章执行（本地代码无 LLM 成本）。
9. **章节修订 × 场景标记一致性**（承载总设计 §2.3 修订路径）：批量产物**先拆分再按章修订**（`shenbi-chapter-revision` 仍 updates `chapters/chapter-N.md` merge_prose，修订粒度不变）。修订合同扩展：修订不得删除/挪动 SCENE 标记行与场景末钩行。**修订后重验 = 新接线**（R3-C1：现状修订步 G4 只验 `*revision*.json`，正文从不复验——`chapter_revision.py:64-67` 跳过一切非 revision JSON）：step15 后对修订章 (a) 标记行 diff vs `chapters/chapter-N-pre-rev.md` 既有备份（chapter_loop.py:2091-2111）——标记数/次序变化即 FAIL；(b) 重跑 G4.cd 场景检查族（场景数 ≥2 + 钩声明-实际匹配）于修订后正文。FAIL → 回修订重派。

### 契约与注册同步清单（随分支落地一并核验）

- SKILL writes 变更（planning 双备忘/drafting 簇产物）→ `just lint-contracts` 绿 + `just generate`（deps.json/docs/skills diff 为空，禁手改）
- **brace 形态登记**（R3-I8）：`plans/chapter-{N+1}-plan.md`、`chapters/chapter-{N+1}-decisions.json`、审计簇 `{N+1}` 报告形态 → truth-files.yaml `patterns:` 条目（`{N-3}` 先例 :121-123）+ 各审计 skill writes 增 `{N+1}` brace 条目与簇 path-context 载荷约定（缺 = write-audit「未声明写入」GATE_FAIL，audit/write_audit.py:104-107；AmbiguousChapterError 路径 dispatch_helper.py:3955-3972 一并适配）
- **staging 提交批次扩展**（R3-I3）：CHAPTER_MEMO 提交批次（step.output_path 单 N + `staged_decisions_targets`，chapter_loop.py:1070-1123）扩展覆盖双备忘+双 decisions——audit-T5「staged sidecar 静默销毁」教训防复发
- **CHAPTER_STEPS 表变更**（R4-I7）：`PIPELINE_STEPS_VERSION`（chapter_loop.py:277-282）bump + 迁移表审查 + `test_chapter_steps_restructured` 快照更新（steps_done 按名键控、审计索引动态计算——插步 resume 安全已核，快照仍须同步）
- **G6 章节枚举排除后缀**（R4-I6）：g6.py:74 glob/`:81` 解析排除 `*-pre-rev.md`/`*-decisions.json`（`triggers.py:110`/`dispatch_helper.py:1701` 既有先例）——#72 使 pre-rev 备份常态化后 G6.1 计数膨胀/G6.2 重复章号假红
- `docs/framework/truth-files.yaml` + `site/framework/` 镜像：staging 簇产物条目、`chapters/chapter-N.md` producer 翻转 skill→pipeline（`context/` 条目 `producer: shared` 先例）
- `specs/INDEX.md` #72 内容字段同步（「scenes sidecar」措辞随 rev3 退役移除，R4-I5）

## 3. 风险与对策

| 风险 | 对策 |
|---|---|
| 章间弧线渗漏（2 章写成一条长弧） | 双备忘各自独立章尾拍 + 拆分器逐章字数带校验 + G4 逐章验钩；违例章级重派 |
| 批量上下文变大 | 6400 字低于已验证的 8000-10000 字单章负载，实际减负 |
| 场景标记漏写 | 拆分器硬失败熔断（沿用现协议） |
| 存量 10 章与新字数带共存 | §1 时序约束：#72-#79 间不对旧章跑 G2/G4/G6；删除归 #79 |
| 字数带上下界与 G2/G4 两套口径 | 施工面 1 消费方总表：地板=min、天花板=max、G2.6 口径统一 total_chars、工具一律读配置 |
| 修订改写致场景结构失效 | §1 耐久性合同（标记在章文件内）+ 施工面 9（标记 diff + 场景检查重验）|
| bundle 跨卷界 | 施工面 3b-①：卷末奇数章单章簇 |
| 番茄打包数学不可行域 | 施工面 2 场景预算两型规则（禁 1400-1800 灰域）+ v2 不可打包=熔断回 planning |

## 4. 验收

- 拆分器对批量产物确定性拆分，逐章字数带/场景数/钩匹配校验全绿（G0.9 声明：簇产物在 #79 前无真实样本——拆分器/G4 场景检查/v2 用例用构造输入（本仓结构性用例先例），**运行时派生变体放 tmp_path，不改 `tests/fixtures/` 仓库文件**；真实簇产物由 #79 验收回填）
- G4 逐章（非逐簇）通过；标记缺失路径熔断可用（负例测试）
- 番茄切分：每更 100% 落在声明的场景收束钩上、零场景中部切割（含跨章组更用例）；拆分器场景域负例（灰域 1450 场景熔断）与 v2 不可打包序列负例（如 1450/1450/1450 章）皆熔断可用
- `just check` 全绿；章数预算重排幂等复跑一致
- 地板/天花板/口径一致性四联测试：2800 过 / 2799 拒；4000 过 / 4001 拒；G2.6 与 G4.cd 同文同数（total_chars 口径）；floor 回退链 min→default→常量
- novel.json target_total_chapters=3300 口径：G0.3 ceil=3125、保量不等式 0.95×3200 ≥ 10M/3300 成立、volume_budget `_implied_total` 复算一致
- bundle 原子性：簇中途 crash 恢复重放幂等（T2 集成：staging 簇 → 拆分晋升 → 修订 → 重验全链）
- 卷界奇偶：卷末单章簇退化为 1 章路径可测
- 修订后重验：标记 diff（删/挪标记）与钩失配两负例皆 FAIL 回修订
- 测试层级映射：拆分器/G4 新检查/v2 切分 = T1 单元（构造输入）；chapter_loop 双章步进 + 恢复 + 审计簇化 + 修订重验 = T2 集成；#79 承接 T3 端到端
