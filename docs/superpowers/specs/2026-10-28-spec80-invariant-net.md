# Spec #80 · 不变量之网：规范事实库、四槽门检、变异测试覆盖（invariant-net）

> **来源**：regen-vol1 运行（ch1-24）G3.4 评分 83.5 CONDITIONAL 暴露的五类跨章缺陷根因分析
> （裁决 #031 + rubric-score-24.md 五维伤口；系统性调试会话）。根因三层：L1 模型行为偏离；L2 五个「write-only oracle」
> 维度（有台账无门检）；L3 门体系反应式生长、从未做不变量普查。
> **方法**：declare-then-verify（钩系统 24 章零漂移的配方）推广到全部维度 + 变异测试闭环。
> **优先级**：🔴 P0（内容修复的 gate 保障依赖 P1）。
> **Status**: Active（rev1 2026-10-28 驳斥复核七项修正：counter-dup 基线/F16 副本语义/分期口径/契约升级纪律/表述订正）

## 0. 背景与根因（浓缩）

| 缺陷 | L1 直接原因 | L2 系统缺口 |
|---|---|---|
| ch20 骨哨双源 | drafting 发明交付拍（备忘写的是钥匙+哨响一下） | prop_registry 是 write-only oracle；G4.xc 物象环对母题物象**四重失效**（旧格式豁免 13/24 备忘、registry 首列键非正文子串、转移动词闭集不覆盖、memo `- 物象:` 声明行零存在）；审计单章视野 |
| ch19/20「林烽」回退 | planning 被关系档「林烽-X」键污染 | 叙事名约定无载体无门检；XC 只验白名单 |
| 《鉴录》计数互斥 | 相邻束 planning 各自猜数 | 计数无规范载体、无声明位、无单调门 |
| 金手指休眠 22 章 | 节点表 ch3-28 零轮回拍 | 卷级体感未分解为章级触点；无节奏门 |
| settle 把断裂炼成事实 | 分叉出第二把哨吞下矛盾 | 无状态机合法性校验 |

**统一结构：凡四槽（载体/声明/门检/审计）齐备的维度零漂移（MH 钩系统、红纸包链）；缺任一槽全部出事。**

## 1. 规范事实库与唯一查询面（facts store）

### 1.1 结构

- `truth/facts/<dimension>.json`——按维度分文件（identity / props / counters / knowledge / promises(钩) / emotion），schema 校验（pydantic 或 jsonschema）。
- **增量 op 协议**：settle 只发结构化事件（`{op: prop.transfer, prop: 骨哨(旧线), from: 帖木哥, to: 那罕, evidence: "chapter-20.md L218"}`），facts store 应用 op 并校验**状态机合法性**（无来源的二次获得=拒收）。这同时根治 matrix/整档 content_dropped 族（模型不再重写整档）。
- **投影层**：现有 truth/*.md 变成从 facts 渲染的投影（渲染器 `truth/project.py`；Markdown 面向人/LLM 的可读性不变，投影头部带 `> projected from facts/<dim>.json — do not edit`）。迁移分两期（见 §6），存量 Markdown 表在迁移前保持现状不阻塞。
- **查询面**：`shenbi-facts query --dim props --chapter 20 [--as-of N]`——返回该维完备事实（含 as-of 历史态，供跨章审计回放）。消费方：chapter-planning 上下文装配（替代猜）、G4 门检 oracle、审计契约 reads、金丝雀审计。

### 1.2 首批入库维度（P1）

props（owner+事件链+状态机）、counters（鉴录名数等单调计数）、identity（人物别名→叙事名映射+当前叙事名）。P2 迁移 promises(钩)——pending_hooks 证据行保留 Markdown 投影，规范态进 facts。

## 2. 不变量普查（四槽契约）

`docs/framework/invariants.md`：13 维×四槽表——恒等(identity)、时间、空间(location)、持有与经手(props)、枚举计数(counters)、知识态(who-knows-what)、承诺与债务(钩)、情绪节奏、能力活性(金手指/体感)、叙事纪律(POV/声口)、字量结构、发布卫生、防剧透。每维四槽：载体（facts 库）/声明（memo 结构化行）/门检（check id）/审计（审计契约 reads）。**任何维度缺槽=文档化的已知洞**。

`tools/lint_invariant_coverage.py`（进 just check）：扫全部 check id + facts schema + 审计契约，对照普查表——缺槽即红。

spec 模板新增必填节：「触及的不变量维度」。

## 3. 变异测试式门检覆盖（CI 环——不打地鼠的核心机制）

`tests/fixtures/invariant-mutants/`：每维一个破坏语料（从本次运行真实伤口导出 + 合成变异体）。mutant 计数口径（rev1）：表 6 行实含 8 体（time-regress/pov-flip/gender-flip 三合成体）；**P1 交付 3 体**（name-swap/prop-chain-break/counter-dup），余 5 体随 P2 维度落地：

| mutant | 来源 |
|---|---|
| name-swap（叙事名回退） | ch20 原始语料（林烽×12）——已入库 `ch20-name-swap-prop-break.md` |
| prop-chain-break（无源交付） | ch20 L218 原始拍——已入库（同上文件） |
| counter-dup（计数互斥） | ch8+ch9 原始计数行拼接——ch9 半份已入库 `ch09-counter-dup.md`；**rev1：矛盾在 ch8↔ch9 跨文件（ch8:247「第三个名字」vs ch9 pre-rev「第一页两个名字」），单文件内部自洽不可判红，P1 须补 ch8 计数行基线 fixture 或 facts/counters 种子（count=3 基线 vs ch9 声明 2+1）** |
| time-regress / pov-flip / gender-flip | 合成（已有红测先例；P2） |
| motif-dormant（体感窗口休眠） | ch3-8 备忘序列（P2） |
| settle-illegal-op（分叉吞矛盾） | ch19-20 settle 的骨哨双条目（P2，依赖 F16s） |

`tests/gates/test_invariant_mutants.py`：断言每个 mutant 至少被一个门 FAIL。**新增任何不变量维度必须同时新增 mutant**（lint_invariant_coverage 校验 mutant 覆盖=维度覆盖；P1 分期口径=校验 P1 维度子集 props/counters/identity 的覆盖）。变异体全被拦=网眼无洞的机器证明。

## 4. 六个门检/机制修复（F15-F20，挂在 facts store 上）

- **F15 叙事名**：facts/identity `narration_name`（本卷=那罕）+ 别名集（林烽）——name_registry 现状无法派生（登记名「临」备注「全卷一致」与实际叙事名相悖、旌名行含两个不同人物），显式载体必要；G4.xc `narration_name`——剥对白叙述段出现别名即 FAIL（备忘 `[旧名回溯]` 豁免闪回）。
- **F16 物象经手链**：memo 母题物象行结构化 `物件@op`（持有/传递/获得/遗失）；G4.cp 声明对 facts 现态合法；G4.cd 正文「非 owner 人名+物件+交接动词共现」未声明传递即 FAIL（动词族须覆盖「抽出/揣着」形态——#75 闭集对本伤口假阴性）；settle op 经状态机校验（F16s）。**实体副本语义**（rev1）：同母题新实体（修复后 ch20 帖木哥之哨与老驼之哨并存）与非法再获得必须可区分（机制留 plan；硬约束：修复后 ch20 双实体并存语料必须全绿）。**契约升级纪律**（rev1）：新备忘必填字段对 in-flight regen-vol1（24 章已结算）须同批带 backfill/生效策略，旧备忘豁免必须 WARN 可见——禁止静默跳过（#75 旧格式豁免 13/24 静默死法不重演）。
- **F17 计数器**：facts/counters 单调；memo 必须声明 `计数: <名> N+1`（planning 从查询面读）；G4.cd 正文计数词=声明值。
- **F18 体感触点节奏**：genre-config `pacing.core_motif_touch: {motif, max_gap:5}`；volume_outlining 增「卷级体感→章级触点拍」分解步；G4.cp 滑窗检查。
- **F19 审计视野**：continuity/foreshadowing 契约 reads 增 facts 查询面产物（props/identity/counters 完备集）。
- **F20 术后全门**：`just gates-sweep <dir> --chapter N`（全门+叙事名清扫+物象/计数检查）；监控侧绕行手术后强制。
- **F21 dispatch 归档**：→ **spec #81 §1**（归档层归观测域管辖；本 spec 的 mutant 重放、金丝雀、`--as-of` 审计回放消费其产物）。

## 5. 运行环：金丝雀审计

每 10 章（或每束 per-chapter 检点）：独立 subagent 拿 `shenbi-facts query` 完备答案 + 章节全文做全链核对（G3.4 模式制度化）；入 driver-prompt 附件协议。

## 6. 分期

- **P1（本次 SDD 代码交付边界）**：facts store 骨架（props/counters/identity 三维）+ 查询面 + F15/F16/F17 + 普查文档 + lint_invariant_coverage + **真实伤口 mutant 导入**（含 rev1 的 counter-dup ch8 基线补全）。验收：三 mutant 全 FAIL；ch20/ch9 修复后语料全绿（F947 离线化：fixtures 断言，不涉真实 dispatch）。**契约升级合规**：备忘新字段 backfill/生效策略同批交付。
- **P2**：F18/F19/F20 + 金丝雀 + 体感触点拍生成 + P1 复评通过的后续束实弹验证。**运行验证阶段**（rev1 明确）：验收 4（ch25-26 实弹束）与验收 5（G3.4 复评 round 2 ≥86）属本阶段运行侧动作（付费 dispatch + 写项目状态），不在 SDD 代码交付边界内——P1 交付其**框架就绪**（planning 可读查询面、memo 契约已扩、门检零误报由 mutant+修复语料双证）。
- **P3**：promises/情绪等剩余维度迁入 facts；Markdown 全投影化；settle 增量 op 全面替代整档重写。

## 7. 验收（P1-P3 全期完成定义；P1 本次 SDD 验收=条 1-3）

1. `uv run pytest tests/gates/test_invariant_mutants.py` 全绿（P1 三 mutant 全被拦；全期 8 mutant）
2. `lint_invariant_coverage` 进 just check 且绿（普查表无未声明缺槽；mutant 覆盖=维度覆盖——P1 校验 P1 维度子集，全量随 P2/P3 扩）
3. regen-vol1 修复后语料过 F15/F16/F17（ch20 叙事名零别名+双实体并存全绿、骨哨声明合法、计数链单调）——fixtures 驱动离线断言
4. （P2 运行侧）一个新束（ch25-26）实弹：planning 读查询面、memo 带结构化声明、门检零误报
5. （P2 运行侧）G3.4 复评 round 2 ≥86 且跨章不变量维度 ≥80
