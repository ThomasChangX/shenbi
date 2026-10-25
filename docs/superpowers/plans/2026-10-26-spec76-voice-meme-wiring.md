# Spec #76 实施计划 — 声口与梗位执行层

> Spec: `docs/superpowers/specs/2026-10-25-spec76-voice-meme-wiring.md`（rev4 GO）
> 全部 task infra（契约/闸/gates 模块/共享词表）→ 协调者亲自实现；数据面离线跑+取证

## Task 1: voice_lexicon 共享词表 + genre_config 数值域

- **Create** `src/shenbi/text/voice_lexicon.py`：`ACCOUNTING_VERBS`（账房动词族**封闭多字形集**：折旧/入账/对账/盘点/结余/亏空/利息/挂账/冲销/清账…版本化注释；**单字排除**——裸「记」在旧九章每章 8-26 次，计入即证伪 0/9 验收（plan R1 审查实测），多字形集下九章实测全 0-1 信号）、`SELF_MOCK_RE`（自嘲反问收尾句式）、`catchphrases_from_card(text) -> list[str]`（frontmatter catchphrases 列表提取：yaml.safe_load 先例（chapter_drafting.py:210-214）；**类括注剥离**——`（初期）` 等尾注剥去取净串，xinghuo-ranqiong fixture 卡五条全带括注，净串口径方可用）、`distinct_voice_signals(body, catchphrases) -> int`（去重信号计数：catchphrase 原串 ∪ 动词族 ∪ 句式，各计一次）
- **Modify** `src/shenbi/contracts/skills/genre_config.py`：market_params 校验增 `voice_density_min.min_per_chapter ∈ [0,5]`、`meme_quota.per_volume ∈ [1,20]`、`quote_type_quota.burning_per_volume ∈ [0,10]`（可选键；缺省代入在 lint 消费端，validator 无副作用）
- **Test**: 词表提取/计数（真卡 fixture protagonist 卡 catchphrases + 构造 body）、三键三态/越域用例
- **复杂度**: infra；**test_kind**: tdd_red_green

## Task 2: plan_format v2 机制（G4.cp/G4.cd 版本条件化）

- **Modify**:
  - `skills/shenbi-chapter-planning/SKILL.md`：模板段1 增 `plan_format: v2` 行（首行）与「声口要求」行（protagonist 口癖/句式要点）；reads 增 `characters/protagonist.md`（全卡读声明）
  - `src/shenbi/gates/g4/chapter_planning.py`：两查分立——令牌值合法（非 v1/v2 FAIL）；v2 ⇒ 声口要求行存在（缺 = FAIL）；v1 无新义务
  - `src/shenbi/gates/g4/chapter_drafting.py`：金句位正则版本条件化——v2 章（memo 令牌/PRE 形态可判）金句位须 `静/燃｜写法｜落点` 且三点同步（memo→PRE→钩行）；v1 旧格式持续 PASS（CI fixtures/旧九章回归不破坏）；贫嘴密度检查（v2 dispatch 域 FAIL / v1 独立复跑 WARN——`voice_lexicon.distinct_voice_signals` 对照 `voice_density_min.min_per_chapter`）
  - `skills/shenbi-chapter-drafting/SKILL.md`：强制段正文（消费备忘声口要求行 + 金句位类型声明 + 三点同步义务）
- **Test**: 令牌真值表（缺席=v1 默认不 FAIL；在场值∉{v1,v2}=FAIL；v2⇒声口行存在，缺=FAIL）；v1 全旧路径 PASS（既有 fixtures 复跑——#75 回归集 chapter-1..10 全带 v1 金句位）；密度 v2 达标/不达标；金句位三点不一致 FAIL
- **契约升级声明**: plan_format v2 opt-in；新批 memo 起 v2；v1 路径持续可跑（#75 回归集/CI fixtures 依赖）
- **复杂度**: infra；**test_kind**: tdd_red_green + characterization（v1 旧路径）

## Task 3: G4.vo 梗位行结构 + lint_voice_meme 工具

- **Modify** `src/shenbi/gates/g4/volume_outlining.py`：梗位行结构校验（**段存在而 0「」跨度才 FAIL**；梗位段/行整体缺席维持既有 P2-6 WARN 路径——卷二+ 过渡态政策下缺席≠FAIL，不翻红存量卷）
- **Create** `tools/lint_voice_meme.py`：
  - `--mode chapter <dir> --chapter N`：贫嘴密度（v2 判据=memo 令牌）报告
  - `--mode volume <dir> --volume N`：**文件谓词**——仅 `chapter-N.md`，排除 `*pre-rev*`/快照件（G2 快照豁免同款口径，防双份计数）；梗位配额（卷纲梗位段「」跨度 → 正文精确串计数 vs `meme_quota.per_volume`，缺额 WARN 行 `[梗位] <名> n/m——下章 PRE_WRITE_CHECK 补触` 打印供 audit_drift）；燃句配额（v2 章分母 vs `quote_type_quota.burning_per_volume`）；登场条件化 catchphrase 窗（登场集=volume_map 节点表名集，未登场不检）
  - `--mode blind`：确定性盲认（构造五角色语料内置 + 标记分类器 argmax，平票/零标记=无归属计漏认；≥4/5 + 分离边际）
- **Test**: `tests/unit/tools/test_lint_voice_meme.py`（构造语料 G0.9 豁免：计数正确性/缺额 WARN 格式/盲认含混淆与零标记行/登场条件化）
- **fixture 声明**: `tests/fixtures/outline-example.md:1190` 梗位行为旧格式（ASCII 引号/`／` 分隔）——不入新句法 characterization，已知旧格式不校正（真实项目 volume_map 四处全匹配新句法，实数据验收以项目数据为准）
- **复杂度**: infra；**test_kind**: tdd_red_green

## Task 4: 验收全量 + #77 校准条款 + 收尾

- 实数据离线：chapter 模式对旧九章（v1 WARN 路径 + 密度报告**真阳性**——多字形集口径下 0/9 章达下限；若实测有个别章达标，验收以「≤4/9 章达标」的 spec 原始诊断措辞为准并贴实测分布）；volume 模式卷一（梗位可提取项恰 1 = 「班味的内核全球统一」，预期输出该项 0/3 缺额 WARN；记账式吐槽为未引号形态型不入精确串）；blind 模式过
- `docs/superpowers/specs/2026-10-25-spec77-style-fingerprint-warn.md` 增校准条款（喻体域口径=比喻句喻体；字面记账动词用法不入 #77 口径；阈值以实测分布校准——引用 #76 词表）
- deviations：多角色注入 deferred/卷二+ 常驻接线 deferred（各卷 outlining）/真盲测 T1 CI 外；`just check` EXIT=0

## 验收覆盖表

| spec §3 | task | 验证 |
|---|---|---|
| 贫嘴密度（旧九章真阳性+构造零误报+参数唯一真源） | T1+T2 | pytest 词表/密度用例 + 实数据 chapter 模式 0/9 报缺 |
| 梗位（结构 FAIL/全覆盖/缺额 WARN 可消费/0/3 如实） | T3+T4 | pytest + volume 模式实跑输出 |
| 盲认（确定性 ≥4/5+边际；T1 CI 外声明） | T3 | blind 模式 + pytest 混淆/零标记用例 |
| 金句双型（v2 机制/三点同步/v1 不破坏/卷级计数） | T2+T3 | pytest 版本条件化用例 + 既有 G4.cd fixtures 复跑 |
| genre 数值域定档 | T1 | pytest 三态/越域 |
