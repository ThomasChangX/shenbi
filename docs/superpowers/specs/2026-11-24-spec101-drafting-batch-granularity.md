# Spec #101 · 草写批粒度可配置化（drafting-batch-granularity）：`bundle_chapters` 单源开关＋scene-split 单章容形＋双章教面按开关生效

**日期**：2026-11-24（编号沿用台账预留的「#101 候选」；提交史无 `spec #101` 匹配，不触发已完成未归档预检）｜ **系列**：实弹续跑解堵（vol2 束8/9 台账定论立项）｜ **状态**：Design（r1，2026-11-24）｜ **优先级**：🔴 P0（台账 2026-11-09 建议 P1；按 ch37–50 实证升 P0，用户可降回）
**动机证据**（台账 `novel-xinghuo-vol1/vol1-ledger.md`，2026-11-09 用户令「按你的建议执行」的对照探针）：
- `:470`「核心结论：双章批粒度 = 草写约束振荡的根因（容量假设确证）。单章批对照探针（同模型/同教面/prompt 仅去 ch50 块+改单章指令）：ch49-only 首派 3494（场景 1322/1140/1040）、ch50-only 首派 3234/3265——双双 in-band、validate_split 零 issue、钩全落款、prop_handoff 0」；「同一模型单章首派 2/2 全过，双章批 0/8 首派全过」；
- `:472`「首派带内率对照：双章批 0/2（束9）vs 单章批 2/2（探针）——#100 教学+clause 在单章面已足，双章面失守于容量而非教学」；
- `:480`「分叉落点（新 spec 候选 #101）：草写批粒度可配置化/单章制——`bundle_chapters` 当前恒 [N,N+1]（volume_map 派生），scene-split 硬校验 bundle 章集==[N,N+1]；单章批需框架开关（drafting 侧单章 + scene-split 章集匹配 + settle follower 语义 + review 面）。建议优先级 P1（生产税：每章省 2-8 派）」——自 2026-11-09 至今未立项（2026-11-24：`specs/` 与 `archive/` 无 #101 文件、INDEX 无行、`bundle_chapters` 仍恒两章、运行配置无任何批粒度键）；
- **生产税实测**：草写派发（token 账本）ch43／45／47 各 6 次、ch49 一批 18 次——每批只产两章；升级检查点（`pipeline-state.json` checkpoint_history）每章 ch1–24 为 0.25 次、ch25–36 为 0.50 次、ch37–50 为 25 次／14 章≈1.8 次；其中 4 条裁决反馈自述失败形态为「约束丢持振荡：每轮只修上轮反馈项，已修项回退」「约束交换：字数带与声口密度互相挤兑（第3派带过声口挂、第4派声口修好带又塌）」——均为双章各自硬门互挤；
- **代码触点**（HEAD `3311a0af`）：`src/shenbi/pipeline/chapter_loop.py:1528`（`bundle_chapters`——`[chapter, chapter+1]`，卷界 singleton；**单一来源函数**）；全部 16 处调用点都经它取成员集（chapter_loop 11 处、`cli.py:698/:756`、`dispatch_helper.py:1361`、`gates/g4/state_settling.py:273/:357`）；`:1803`（`_BUNDLE_DISPATCH_SKILLS = {shenbi-chapter-planning, shenbi-chapter-drafting}`）；`:1559-1583`（`split_bundle`／`validate_split` 章集校验）；`src/shenbi/pipeline/scene_splitter.py:3-4`（bundle 契约自述「one drafting dispatch = 2 consecutive chapters」）、`:81`（「1-2 chapters from one bundle (singleton at volume ends)」）；
- **反证边界**（如实登记，防过度承诺）：单章不保证首派过门——2026-11-15 Goodhart r2 单章重跑「G4.cd 通过率：A 1/9（11.1%）vs B 2/9（22.2%）」（`reports/2026-11-15-goodhart-r2-single-chapter.md:10`），主导失败项是 `voice_density`。本件目标是消除**双章互挤型**振荡及由它产生的重派税与升级税，不是把首派过门率提到 1。

**触及的不变量维度**：字量结构（弱关联——双章各自字数带硬门是互挤面之一，本件不改带值与门检）；情绪节奏、叙事纪律（POV/声口）（弱关联——声口密度门与字数带互挤是观测到的形态，不改判定判据）

---

## 0. 根因

双章批把两章的全部硬门（字数带、场景预算、声口密度、钩落款、prop_handoff…）压进一次派发，写手模型在固定输出预算下无法同时满足，表现为约束交换振荡；框架侧 `bundle_chapters` 恒返回两章，生产上没有任何开关可以退回单章。教学面（#95／#100）已被探针证明在单章面足够。

**用户裁定（待裁三项）**：(a) 优先级——本件按实证标 P0，台账原建议 P1；(b) 开关缺省值——建议「缺省保持双章（行为零变化），vol1 自 ch51 起显式开单章」；(c) 在飞项目——本件不含回填／迁移工具，按 AGENTS.md contract-upgrade 纪律走显式声明路径：开关只影响其开启之后的 bundle 解析，已存在的双章产物（plans／chapters／decisions／snapshots 的 N、N+1 对）不重写；vol1 现停于 ch49/50 双章束的 settle 重派，续跑前须先由 #121 解堵。

**备选案已评估并否决**：
- 「手植 bundle／人工手术续跑」（束5 #14 先例）——每两章一次人工，生产税不消，只是把振荡成本转成人力；
- 「提高写手档位或输出预算硬扛双章」——#98／#100 已证问题在约束数而非预算；分档实验（#107）尚未裁定；
- 「全局改单章、删除 bundle 机制」——卷界 singleton、settle 双块、review 跟班章读等语义都以 bundle 成员集为轴，删除面过大；单源开关即覆盖；
- 「规划保持双章、仅草写拆单」——不否决，列为 T2 的备选形态 (ii)，plan 期按教面改动量二选一。

## 1. 任务分解

### T1 · 单源开关
- 配置键 `drafting_batch_size: 1|2`，缺省 2（＝现状，差分零变化）；落点 plan 期定（倾向运行配置层，与 `per_chapter_review_enabled`／`chapter_memo_review_required` 同层——属运行策略而非文体配置）；
- `bundle_chapters(project_dir, chapter)` 读取该键：＝1 时返回 `[chapter]`——16 处调用点自动传导（卷界 singleton 语义不变）；
- 判据：单测三分支（＝1 恒 singleton／＝2 与缺省逐字节现状〔vol1 volume_map 真 fixture〕／非法值 fail-loud）；`git grep` 证明除 `bundle_chapters` 外无第二处解析批粒度。

### T2 · 双章教面按开关生效
- 草写／规划派发 prompt 的「双章指令块」（第二章块、「两章各自硬门」措辞）在＝1 时不注入；follower 路径（`chapter_loop.py:1838/:1869/:1977/:2674/:4878`）在 singleton 下自然为空集——逐一核对无「至少两章」隐含假设；
- `split_bundle`／`validate_split` 接受 singleton 章集（台账 `:480` 称现行硬校验章集==[N,N+1]——plan 首步核对其现行位置）；
- 规划侧是否同步单章，plan 期二选一：(i) 规划＋草写都单章（探针即此形态，证据最强——**默认**）；(ii) 规划保持双章、仅草写单章（保情节连续性，需 planning 产物被单章草写消费的接缝）；
- 判据：dry-run manifest——＝1 时 drafting 派发 prompt 无第二章块；singleton bundle 过 `validate_split`；planning／drafting／settle／review 各一次 fixture 演练全绿。

### T3 · settle 与 review 面的 follower 语义
- `gates/g4/state_settling.py:273/:357` 经 `bundle_chapters` 取成员集——singleton 下「双章块齐」检查自然只要求本章块；核对 #99（基底行保真）在 singleton 下无假阳性；
- review 跟班章读（`chapter-{N+1}` 契约声明，`633bcf8d`）在＝1 时解析不到文件——须确认走 OPTIONAL_READS 缺读不报错；
- 判据：fixture 项目（真产物副本）开关两态下 settle G4 与四组 review 的 dry-run 均无 FAIL；跟班章缺读零 ERROR。

### T4 · 实弹验收（随用户令，预注册）
- 对象：vol1 ch51 起连续 ≥6 章，开关＝1；
- 预注册判据（跑前冻结）：①草写派发数／章 p50 下降（基线：ch43／45／47 每批 6 派、ch49 每批 18 派，每批两章）；②「双章互挤型」重派（反馈同时点名两章章号且分属不同 check id 族）计数＝0；③escalation ≤3 次／6 章（基线 ch37–50 ≈1.8 次／章）；④字数带首派带内率**只记录不作硬判据**（见反证边界）；⑤回退条件：连续 2 章草写三振 → 关回双章并记录；
- 判据：报告落 `reports/`；五项逐项判定；成本记录。

## 2. 验收
1. T1–T3 判据全绿、缺省行为差分零变化；
2. T4 实弹报告（随令）；
3. `just check` 全绿。

## 3. 风险
- **规划连续性下降**（形态 (i) 下每章独立规划）——备选形态 (ii)＋既有跨章审计（long-span／arc-payoff）兜底；T4 ⑤ 回退条件；
- **singleton 下的未测分支**（16 处调用点）——T3 fixture 演练＋#112 性质测试（I9「wave savepoint 覆盖 bundle 全员」）交叉；
- **粒度切换的兼容**：用户中途在卷内关回双章时，leader 章 N 在＝2 下要求 N+1 存在——plan 期核对切换章的成员集解析；必要时约束「切换只允许在卷界」（登记）；
- **共享文件面**：`chapter_loop.py` 最热文件——顺序 **#121 → #101 → #122 → #112／#113／#114**；`scene_splitter.py` 无在飞冲突；教面改动与 #96／#102（drafting／planning SKILL 同文件）——本件只动「双章指令块」的注入条件，不改教学正文，撞面按共享文件表规约 plan 首步 re-anchor。

## 4. 立项预答（价值门 ④⑤ 前置）

**④ 博弈路径清单**：
- 开关＝1 但教面仍注入双章块（模型照写两章）→ T2 dry-run manifest 断言；
- 开关只改草写、settle／review 的 follower 语义没跟上 → T3 两态演练；
- 卷内混合粒度（切换章）解析出错 → 风险第 3 条；
- 写手在单章下仍振荡（非双章型，如 `voice_density` 单门不过）→ 不在本件范围，T4 ⑤ 回退并转 #122（修订证据面）。

**⑤ 候选机制清单**（buy-before-build）：`bundle_chapters` 单源（升格既有，覆盖成员集解析 100%）；卷界 singleton 语义（既有 `parse_volume_spans`）；运行策略配置键（`per_chapter_review_enabled` 等先例）；#98／#100 的分档与 clause 机制（已证单章面足够，不重做）。无新建机制。

**测量语义回执（v8.1 L1–L5，触及面：实弹判据）**：L1 构念与口径——「双章互挤型重派」须机器可判（反馈同时含两章章号且分属不同 check id 族），不靠人工归类；L2 未触及；L3 活性——判据③阈值（3 次／6 章）与基线（≈11 次／6 章）间距远大于观测波动（单章 0–4 次）；L4 可判别性——判据①②③均为计数型，n=6 章可判；首派带内率明示不作硬判据（单章 1/9–2/9 的历史读数在 n=6 下不可判）；L5 时点保真——基线取 ch37–50 同一模型档（deepseek-flash）的同期读数，不混入更早的 pro 档章节。
