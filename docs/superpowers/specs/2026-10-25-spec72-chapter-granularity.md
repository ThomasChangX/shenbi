# Spec #72 · 平台章粒度改革（chapter-granularity）

> **Date:** 2026-10-25 | **Status:** Active (Revised 2026-10-25 R1 驳斥复核施工面修正 + R2 设计审查修复：修订×场景标记一致性 / 天花板口径统一 / 卷界奇偶 / 钩匹配谓词钉死) | **Severity:** 🟥 P0（地基） | **方法:** 方案 C——平台章原生粒度 + 场景簇批量派发（一次派发 2 章）+ 声明式发布切分 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** 无 | **范围:** genre-config 常量与平台参数（含契约闭键集四站）/ novel.json 章数口径 / chapter-planning 与 chapter-drafting 双章 bundle 契约 + chapter_loop 派发循环 / 确定性拆分器 + scenes 索引 / G4 逐章校验扩展 / 章节修订×场景标记一致性 / release_split v2 / volume-budget 重排接线

> 源自 2026-10-25 总设计 `2026-10-25-novel-market-overhaul-design.md` §2（诊断背景与决策路径见总设计 §0）。用户决策：双平台（起点粒度生成为主、番茄发布层适配）；方案 C（原生+批量派发）。总设计 §2.3「修订路径：批量产物先拆分再按章修订（修订粒度不变）」由施工面 9 承载（R2-C1 修复）。

## 1. 定位与边界

- 问题：`chapter_word.default=7600` 锚定了 1316 章的生成粒度，每万字节拍数 ≈1（头部 ≈3）；release_split 启发式切分不带爽点/钩子意识，切分点打乱节拍布局。
- 本 spec 改生成与发布的**粒度合同**，不改内容规则（引擎/节奏归 #73/#74）。
- 卷界按字数锚定不变（12 卷历史锚不动）；旧九章全弃，无迁移包袱，旧启发式直接退役。
- **存量时序约束**（rev1）：本 spec 落地后、#79 删旧章前，不对 `novel-xinghuo-vol1` 现存 10 章（约 7600 字/章）执行 G2/G4/G6（新字数带下 G2/G4 必红；G6.1 期望章数 1563 vs 存量 10 亦红）——G6 与 G2/G4 同列禁跑（R2-M2）。pipeline-state 的 1316 章口径由 #74 重排 + volume-budget `--apply` 收敛；并存期间唯一预期红面 = volume-budget 的 `re_budget_pending`（设计内报告，非误报；G0.3 只报告 ceil 从不对比 novel.json，无其他消费方炸）。
- **场景标记的耐久性合同**（R2-C1 修复核心）：`<!--SCENE-->` 场景标记**保留在终稿章文件内**（独占一行的 HTML 注释，正文渲染不可见）；`===CH:n===` 章界标记只存在于 staging 簇产物。发布层生成更文本时剥离标记（读者永远看不到）。场景边界的真源 = 章文件内标记（修订存活、G4 可随时复验）；scenes.jsonl 降级为**幂等派生索引**（可从章文件随时重导）。

## 2. 施工面

1. **常量与参数**（rev1 重写 + R2 补全上下界）：
   - `novel-xinghuo-vol1/genre-config.json`：`chapter_word` 7600/7200/12000 → **3200/2800/4000**；note 重写（双平台口径 + 保量数学见下 + 番茄更带 1800 下限的用户决策依据——旧模板 note 的「平台红线 2000」为 2200 单档检索口径，#72 双平台决策取代之，R2-M3）
   - 新增顶层键 `primary_platform: "qidian"`（枚举 `qidian|fanqie`，**optional**——归入 `_OPTIONAL_TOP_KEYS` 语义（R2-I4），存量 fixture 无此键不断负载；缺省时消费方回退 v1 默认）；番茄更带进 `chapter_word` 子块：`fanqie_update: {min: 1800, max: 2800}`
   - **闭键集四站同步**：`src/shenbi/contracts/ownership.py` GENRE_KEYS（:39-52 frozenset，R2-M1 订正行号）+ `src/shenbi/contracts/skills/genre_config.py`（Pydantic 字段 + `_top_level_keyset` :51-64 + `_OPTIONAL_TOP_KEYS` :21-22）+ `skills/shenbi-genre-config/SKILL.md`（模板 chapter_word 块 :122-126 现为 2200/2000/4500 → 3200/2800/4000 + note 重写 + 顶层闭键集规则行 :323/:416 两处同步——顺带修既有漂移「9 必填（含 tropeInventory）」实为 8 必填）
   - `novel-xinghuo-vol1/novel.json`：`target_total_chapters` 1400→**3300**（保量自洽：10M/3300≈3030 ≤ 3040 = 0.95×3200；预算章数语义 = 允许 5.6% 余量，同旧 1400 vs 1316 口径）；`total_chapters` 不手改——保持 volume-budget `--apply` 写回通道（实际重排归 #74）
   - **地板与天花板口径统一**（R2-C2 扩全）：`chapter_word_floor()`（shared.py:130-152）改读 `chapter_word.min`，三调用方 G2.6 / G4.cd / G4.ln.below_floor 一并生效；G2.7 天花板弃硬编码（`CHAPTER_WORD_CEILING`/`_is_important_chapter` 的 10000/4500 双档，g2.py:209-211）改读 `chapter_word.max`（4000）；G4.ln.above_ceiling 同源。**消费方总表**：`{G2.6, G4.cd, G4.ln 地板} → min`；`{G2.7, G4.ln 天花板, 拆分器带, release_split v2 番茄带} → max / fanqie_update`（一律读配置单源，禁工具内硬编码——probe escalation #9 同型教训）；`{G0.3 ceil, volume_budget _implied_total, length_normalizing 提示层目标} → default`；G6.1 期望章数推导读 default（现状 g6.py:60 不变）。**大章概念退役**：4000 为全书统一天花板，战役/审判等大节拍由发布层场景组更承接（内容层归 #73/#74）
   - 总章数 ceil(1000万÷3200) = **3125 章**；volume_budget `word_floor` 口径随地板统一改 min（R2-M5 权衡明示：2800-3199 章不再触发 budget 保量预警，聚层安全网改由 ±3 漂移守卫 + G0.3 保量不等式承担——接受）
2. **chapter-planning 双章 bundle**（`skills/shenbi-chapter-planning/SKILL.md`）：一次派发输出两份独立备忘（writes 增 `chapter-(N+1)-plan.md` + 对应 decisions sidecar）——各自章尾张力拍、场景字数预算（2-3 场景/章）、**每场景收束钩声明（钩原文一行，供 drafting 逐字落款与 G4 精确匹配）**；共享一次上下文读取。
3. **chapter-drafting 场景簇契约**（`skills/shenbi-chapter-drafting/SKILL.md`）：一次派发 = 连续 2 章（约 6400 字）；输出带标记的簇产物 `staging/chapter-N-bundle.md`（`uses_staging` 既有约定——落 chapters/ 会被 G6.1 glob `chapter-*.md` 误计，R2-I7 取证）+ 两份章级 decisions sidecar 直写 `chapters/`（decisions 属 LLM 产物，拆分器不得代造）；**每场景末行 = 备忘声明的收束钩原文**（逐字，R2-I6 谓词：声明文本剥空白后为场景末非空行的子串）；每章末尾必须落在备忘声明的章尾钩上。
3b. **chapter_loop 派发循环改造**（`src/shenbi/pipeline/chapter_loop.py`）：CHAPTER_STEPS（:143-264）单章步进 → 双章 bundle 步进：planning 一次产两备忘、context 组装覆盖两章、drafting 一次产簇（uses_staging）、游标/checkpoint/ghost-chain 守卫按双章语义。**约束（R2-I2/I5 钉死）**：① bundle 不跨卷界——卷末奇数章 = 单章簇（planning/drafting 退化为 1 章，step1 卷界 checkpoint 后重新对齐偶数配对）；② step 完成度 bundle 原子（两章同进退）；③ ghost-chain 守卫要求两份拆分产物齐备；④ 拆分器确定性幂等——crash 后从 staging 簇产物重放即可恢复，staging 簇保留至该章全链收束（随既有 staging 清扫）；⑤ 审计按簇派发但**报告工件保持逐章**（`chapter-{n}-review-summary.md` 等下游 `_get_audit_history`/G3 形态零改动——簇 prompt 一次产出两章报告）。
4. **确定性拆分器**（`src/shenbi/pipeline/scene_splitter.py` 新增）：读 staging 簇产物，按 CH 标记拆 `chapters/chapter-N.md`（+N+1）；校验每章字数带 2800-4000（读配置）、场景标记数 ≥2、CH/SCENE 标记完整（缺失=硬失败 exit 1，熔断重派——沿用现协议，失败归类既有 `FailureClass.DETERMINISTIC_GATE`，不新增状态域，R2-M6）；**剥离 CH 标记、保留 SCENE 标记**（§1 耐久性合同）；写 scenes.jsonl 索引行（章号/场景数/每场景末行钩原文——幂等可重导，不存绝对字符位）。**必须被 chapter_loop 接线调用**（drafting 簇产物 → 拆分 → 章文件 + scenes.jsonl + manifest 记账）——独立存在零调用 = dead-wire 禁止。G2/G4 作用于拆分后章文件；staging 簇不进 G2 章检查（拆分器硬校验即其门）。计数口径：字数统计剥标记行（既有 strip 工具扩展）。
5. **G4 逐章校验扩展**（`src/shenbi/gates/g4/chapter_drafting.py`）：现状 `chapter_end_hook`（:435-484）已按文件（=逐章）执行启发式——rev1 订正原文措辞；**新增**：每章场景数 ≥2（读章文件内 SCENE 标记，不依赖 sidecar）；收束钩「声明 vs 实际」匹配（plan 备忘每场景钩声明 ↔ 章文件各场景末行，谓词见施工面 3）；标记行不参与字数/疲劳等既有检查计数。
6. **release_split v2**（`tools/release_split.py`）：起点档 1 章=1 更（重题直发）；番茄档以场景为原子打包（打包域=已收束窗口场景序列，允许跨章组更），硬规则四条——每更 1800-2800 字（读 `chapter_word.fanqie_update`）、更边界只落 SCENE 边界（读章文件标记，非 sidecar 偏移——修订失配免疫）、每更必须以声明的场景收束钩收尾、禁切场景中部，违反即切分失败；更文本剥离标记。旧启发式分类器退役（SCENE_TRANSITION_WORDS/TIERS 常量）。**已收束窗口数据源**：pipeline-manifest.json 逐章闸记录（已收束=该章全部 per-chapter 闸 PASS）。**CLI 合同不破**（R2-M4）：位置参数 dir + `--platform`（缺省改读 `genre-config.primary_platform`，无键回退 v1 默认）保留；`--title-pattern`/`--renumber-published` 语义随起点档直发保留。**同批重写债披露**：`tests/unit/tools/test_release_split.py` 38 用例随 v2 重写为声明式切分用例。冻结机制保留——当前项目零已发布更 = 零冲突退役窗口，v2 须在任何真实发布前落地。
7. **volume-budget 重排接线**（`src/shenbi/pipeline/volume_budget.py`，rev1 订正路径）：章数数学随 default=3200 自动生效（`_implied_total` :190-205）；`word_floor` 口径随地板统一改 min（施工面 1 权衡）；`--apply`（:329-340）保持只写 novel.json `total_chapters` + 骨架同步。卷内章数按 3200 重排（卷一 45.6 万字 → 约 143 章）——重排执行归 #74，本 spec 只接数学与工具。
8. **审计批量**：LLM 审计同维度按簇批量派发（×1.19 而非 ×2.4）——落点 `chapter_loop.py:3010-3121` 审计两波 prompt（`Execute {skill} for chapter {n}` :3060/:3094 → 簇形态）+ `_wave_savepoint` :3079/:3117 按簇记账；报告工件逐章（施工面 3b-⑤）；G2/G4 逐章执行（本地代码无 LLM 成本）。
9. **章节修订 × 场景标记一致性**（R2 新增，承载总设计 §2.3 修订路径句）：批量产物**先拆分再按章修订**（修订粒度不变，`shenbi-chapter-revision` 仍 updates `chapters/chapter-N.md` merge_prose）。修订合同扩展：修订不得删除/挪动 SCENE 标记行与场景末钩行（G4 修订后复跑即复验——既有 G4 复跑路径）；修订后 scenes.jsonl 该章行由拆分器索引重导（幂等，本地零成本）。

### 契约与注册同步清单（R2-I7，随分支落地一并核验）

- SKILL writes 变更（planning 双备忘/drafting 簇产物）→ `just lint-contracts` 绿 + `just generate`（deps.json/docs/skills 生成物 diff 为空，禁手改）
- `docs/framework/truth-files.yaml` + `site/framework/` 镜像：staging 簇产物条目、`chapters/chapter-N.md` producer 翻转 skill→pipeline（对照 `context/` 条目 `producer: shared` 先例）、scenes.jsonl 新条目（`producer: pipeline`）

## 3. 风险与对策

| 风险 | 对策 |
|---|---|
| 章间弧线渗漏（2 章写成一条长弧，第二无独立钩） | 双备忘各自独立章尾拍 + 拆分器逐章字数带校验 + G4 逐章验钩；违例章级重派 |
| 批量上下文变大 | 6400 字低于已验证的 8000-10000 字单章负载，实际减负 |
| 场景标记漏写 | 拆分器硬失败熔断（沿用现协议） |
| 存量 10 章（7600 字）与新字数带共存 | §1 时序约束：#72-#79 间不对旧章跑 G2/G4/G6；删除归 #79 |
| 字数带上下界与 G2/G4 两套口径 | 施工面 1 消费方总表：地板=min、天花板=max、工具一律读配置 |
| 修订改写致场景索引失效 | §1 耐久性合同（标记在章文件内）+ 施工面 9（修订合同 + 幂等重导）|
| bundle 跨卷界 | 施工面 3b-①：卷末奇数章单章簇 |

## 4. 验收

- 拆分器对批量产物确定性拆分，逐章字数带/场景数/钩匹配校验全绿（构造结构输入 + 既有真实章 fixture 改造——G0.9 结构性用例豁免面：簇产物在 #79 前无真实样本，拆分器/G4 场景检查/v2 用例用构造输入（本仓先例：对抗性段落布局/账本态内联构造），真实簇产物落地后由 #79 验收回填）
- G4 逐章（非逐簇）通过；标记缺失路径熔断可用（负例测试）
- 番茄切分：每更 100% 落在声明的场景收束钩上、零场景中部切割（含跨章组更用例）
- `just check` 全绿；章数预算重排幂等复跑一致
- （rev1）G2/G4 硬地板=2800 与拆分器字数带下界一致性：同章 2800 字两闸皆过、2799 皆拒（测试表达）
- （R2-C2）G2.7 天花板=4000 一致性：4000 过、4001 拒（与上条成对）
- （rev1）novel.json target_total_chapters=3300 口径：G0.3 ceil=3125、保量不等式 0.95×3200 ≥ 10M/3300 成立、volume_budget `_implied_total` 复算一致（测试表达）
- （R2-I5）bundle 原子性：簇中途 crash 恢复重放幂等（T2 集成测试：staging 簇 → 拆分 → 修订 → 索引重导全链）
- （R2-I2）卷界奇偶：卷末单章簇退化为 1 章路径可测
- 测试层级映射：拆分器/G4 新检查/v2 切分 = T1 单元（构造输入）；chapter_loop 双章步进 + 恢复 + 审计簇化 = T2 集成；#79 承接 T3 端到端重生成验收
