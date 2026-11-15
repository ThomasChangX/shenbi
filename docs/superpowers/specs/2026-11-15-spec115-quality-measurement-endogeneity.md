# Spec #115 · 质量测量内生性（quality-measurement-endogeneity）：P25 floor 分位语义拆除、外部读者判据锚定、自产自销回路阻尼

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit · B 异模型元审）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟠 P1
**补充证据（2026-11-15 实验执行）**：（1）外部锚定预注册 r2——32 条已评分行中低分带 ≤76 仅 2 章（ch2/ch3），r1 的 4/4/4 分层不可满足；改为 2/5/5（n=12 不变），见 `docs/research/2026-11-15-quality-external-anchor-prereg.md` §7，执行包 `reports/external-anchor-20261115/`（人工面板未运行）；（2）LLM 判官压缩——`deepseek-v4-pro` 对 7 章 1-7 五维评分全部落在 5-6，A/B 差 ≤0.2，Mann-Whitney p=0.75 或不可算（`reports/2026-11-15-goodhart-escape-execution.md` F4）——绝对分判官无判别力，支持「外部锚/人工面板」必要性；（3）「无正文出分」见 #109 补充证据。
**动机证据**：`docs/superpowers/specs/2026-11-15-spec106-resonance-floor-liveness.md:19`（`_effective_resonance_floor` = trailing 20 章 **P25**，clamp[50,80]）；`:27`（shadow 毕业判据「预期带 5-20% 章」）；`:41`（验收预期「ch2=74 等低分章命中」）vs `:19`（已评分行 <8 → `DEFAULT_RESONANCE_FLOOR=50`——ch2 在冷启动窗内，**按 T1 规则永不触发**，验收与规则自相矛盾）；`:45`（风险「floor 追涨棘轮」→ 缓解=cap=80）；本批离线回放（脚本附录 A，判据可重放）：`novel-xinghuo-vol1/truth/resonance_trend.md` 32 条已评分行→24 个可评估点，#106 规则实际点火 **2/24=8.3%**（ch14/16，score=77）；**同一分数序列打乱章序**（破趋势）5000 次置换零假设触发率 **21.2%（95% CI 8.3-29.2%）**——实际值落在零假设下缘；分数斜率 **+0.119/行**（≈+0.06/章，与 #110 动机节 +0.073/章同向）；floor 全窗 77-79，模式带 79（12/32）、sd=2.40、相对位置计数 相当73/更差19/**更好0**（#110 动机节）；`skills/shenbi-review-resonance/SKILL.md:70`（锚点先行：每维对 `benchmarks/anchors/AC-NNN` 做高/中/低相对定位）+ `:194-204`（锚点协议：每维分数必须回答「比锚点更好/相当/更差」）——**修正 #110 动机节行号引用**（`:103-116` 实为 chapter_role 阈值校准门，非锚点协议）；`benchmarks/anchors/AC-001.md`（`source_work: 诡秘之主`——锚点是外部工艺基准，不是本书自身历史分）；`docs/superpowers/specs/2026-11-15-spec103-highlight-distill.md:33`（drafting reads 加 `style/highlight_playbook.md`；style-learning anchors 半操作化**第四源**=本窗 resonance top 章段落）+ `:25`（手法卡出处章+引文 verbatim）——判官分→风格资产→drafting→同一判官的闭合回路；`src/shenbi/pipeline/revision_router.py:76`（`DEFAULT_RESONANCE_FLOOR=50`）+ `src/shenbi/pipeline/chapter_loop.py:3133-3143`（below-floor 只 `log.warning`）——#106 要接线的两个现状锚；外部效度面缺席：在飞 spec 全集（#97-#114）与 `docs/research/2026-11-15-*.md` **无一条**把 resonance 与体系外读者判据（人工盲评/平台留存/付费转化）对账，#110 的 κ/α/r 全部是判官间信度或判官间效度，不含体系外 criterion validity，#103 却把 resonance 高分章当「读者侧信号」使用（`:12`/`:33`）。

**触及的不变量维度**：情绪节奏（弱关联——resonance floor 为该维正向下限的接线面；本件改其语义与外部锚，不新增 check id）

---

## 0. 根因

**质量测量链三重内生：判据外部性不足、阈值来自被测分布、学习样本来自被测判官。** (1) resonance 的工艺锚点是外部基准（AC-NNN，诡秘等），但**没有任何体系外读者判据**校验这把尺子是否预测读者反应；实测「更好」计数 73/19/0——判官从不把任何生产章判到锚点之上，分数被压进 74-86 窄带；(2) #106 把「正向下限」实现为 trailing-20 **P25 分位数**：分位数下限的点火率是分数**斜率**的函数而非质量水平的函数（平稳分布下期望≈25%，实测 8.3% 只因分布上行），cap=80 又保证通胀到模式带 80 后 floor 永久失效——体系把「从未点火的 floor 50」换成了「点火率随时间衰减到 0 的 floor」；(3) #103 用 resonance 高分章做风格学习第四源并注入 drafting，判官分数成了下一轮被判章的学习信号，回路闭合但无 holdout、无阻尼、无稳定性判据。净效果：**质量面唯一变化的信号既无外部效度，又随自身趋势漂移，还被拿来训练下一轮**——#106 的「有牙」证明（`:41`）本身是分位数的算术产物。

**用户裁定（2026-11-15）**：不考虑在飞项目——vol1 仅回放报告（rank_alarm 序列/置换检验复现），不清洗不补评；零付费派发——外部判据走人工盲评预注册（$0 API），实弹随令；#106 的 `shadow` 缺省行为零变化。

**备选案已评估并否决**：「floor 直接改常量 80」——绝对值仍随判官宽大漂移，且 80 > 现模式带 79 会把多数章判 below，制造新的一刀切假阳性，无任何外部依据；「等 #107 第二模型判官」——第二 LLM 判官仍是同一原语，换模型只测 tier 效应，不提供体系外效度；「并入 #106 T2 毕业判据」——#106 的毕业判据正是 shadow 触发率，而本件已证触发率是分数斜率的函数（8.3% vs 零假设 21.2%），并入等于把 tautology 固化为验收。

## 1. 任务分解

### T1 · floor 语义拆分（含 #106 补充证据与内部矛盾修正）
- 两信号分离，命名与消费面分离：
  - `quality_floor_abs`：绝对质量下限，取值来自 T3 外部锚定（人工盲评后的章级分位/绝对带），**不由 trend 分布计算**、无 cap；
  - `rank_alarm`：现行 trailing-20 P25，保留为「分布漂移告警」；文档明确「平稳分布下期望点火≈25%」，禁止作为毕业/质量证据，不作「下限」命名。
- 修 #106 验收自相矛盾：删除或改写 `:41` 的「ch2=74 命中」——ch2 在冷启动窗内（<8 行）按 T1 规则必不触发；改为冷启动边界测试（前 8 行不触发、第 9 行起按规则断言）。
- 饱和哨兵：连续 20 章 `rank_alarm` 点火率 <5% 且 mean score 上升 ≥2 分 → WARN `floor_saturated_or_inflated`；点火率 >35% 且 mean 持平 → WARN `distribution_degraded`；两者进 drift-guidance 报告（只报不路由）。
- cap 语义：cap=80 只约束 `rank_alarm`；`quality_floor_abs` 无 cap（绝对下限不得被上限钉死）。

**判据**：`git grep -n "quality_floor_abs\|rank_alarm" src/` 双名存在且消费点分离；单测三条（ch2 冷启动不触发/饱和哨兵红测/两信号独立）；vol1 回放报告输出两信号序列（`rank_alarm` 8.3%，`quality_floor_abs` 待 T3）。

### T2 · 自产自销回路阻尼（#103/#106 联合，shadow）
- 学习样本 holdout：`highlight_playbook`/`style/anchors.md` 候选章不得是「同窗口内被同一判官版本评过分」的章；或每张手法卡注入前须有 T3 外部确认（二选一，plan 期定，预注册）；
- 回路稳定性仪表：卷界 `drift-guidance` 汇总（a）#110 T1 的分数形状三哨兵（sd/模值频率/通胀 slope）；（b）`src/shenbi/text/style_fingerprint.py` 的确定性风格指标趋势（句长 sd、对话比、比喻密度、段长 CV）——「分数上升 ∧ 风格指标压缩」同向出现 ≥2 卷 → `self_reinforcement_suspect` 报告行；
- 缺省 `resonance_policy.learning_loop: off|shadow|armed`，off=现状逐字节一致；armed 仅 T3 通过后由用户裁定。

**判据**：红测（合成「分数升+风格压缩」序列触发报告行；现状 vol1 回放仅报告）；`git grep` holdout/`self_reinforcement_suspect` 接线；off 模式差分零行为变化。

### T3 · 外部读者判据锚定（预注册，人工面板，非付费 API）
- 落盘 `docs/research/2026-11-15-quality-external-anchor-prereg.md`：12 章分层（resonance 低/中/高各 4），3 名盲评人（不知 resonance 分），5 维读者反应 rubric（继续读意愿/情绪冲击/记忆点/代入感/推荐意愿），ICC + Spearman ρ vs resonance overall；
- 预注册判据：ρ≥0.5=resonance 可作读者代理；0.3≤ρ<0.5=弱代理（只能作 rank 信号）；ρ<0.3=不可作读者代理（撤 #103 的「读者信号」定位）；
- `quality_floor_abs` 由盲评低分位确定（分位值**先于**看数据声明，plan 期钉死；不得看完再定）；
- 预算：6 人时（3 人 × 12 章 × 10 分钟）+ **$0 API**；停机：任一评委中途看到 resonance 报告 → 该评委作废；章文件研究期变更 → 该章作废。

**判据**：预注册文档存在且含臂/判据/停机/预算四节；无派发。

### T4 · 消费面收编（spec 文本修订）
- #106 T2 毕业判据改写：不得以「触发率 5-20%」单指标毕业；须（a）`quality_floor_abs` 经 T3 有效，（b）`rank_alarm` 报告稳定，二者缺一维持 shadow；
- #103 T1：anchors 第四源与 playbook 消费以 T3 结果为门——ρ<0.3 时回退结构指标，不把 resonance 分引入风格学习；
- #110 T2 营养接线补一行：报告须同时报「分布形状」与「外部锚定效度」，κ/α 不得单独作为判官可用性结论。

**判据**：三份 spec 文本含引用行（grep 可证）；#103/#106/#110 执行 plan 前置检查单条目存在。

## 2. 验收
1. T1-T4 判据全绿；
2. 差分：`resonance_policy` 缺省/off 下对 vol1 续跑零行为变化（route/日志仅新增 shadow 面）；
3. 回放报告：`rank_alarm` 8.3% 与置换零假设 21.2% 可复现（同脚本同输入同输出）；
4. 外部锚定预注册文档落盘且未执行；T3 实弹随令；
5. 反例：合成「分数单调升+分布压缩」序列被饱和/自增强哨兵捕获。

## 3. 风险
- 人工评审主观性/疲劳 → 3 人 ICC 门槛（ICC<0.5 则外部锚无效，不得用于定 floor）；
- P25 回放对 trend 蛀洞敏感（26-48 偶数章 pending）→ 复用 #106 T3 完整性告警；回放报告须先报有效行数；
- **共享文件面**：`revision_router.py`/`chapter_loop.py` 与 #106/#109 同文件——施工序 **#105 → #106 → #109 → #115**（#106 落接线、#109 落 per-n、#115 改语义；每 plan 首步 re-anchor）；`skills/shenbi-review-resonance/SKILL.md` 与 #110 T3 同文件——**#110 → #115**；drift-guidance/style 面与 #103 同文件——**#103 先**（#115 只加 shadow 仪表）；
- #106 若已按原 P25 语义执行，#115 T1 变成 patch——本件以「T1 覆盖 #106 T1 的分位语义」为显式前置；INDEX 依赖已钉 #106 未执行；
- 外部锚定只覆盖 vol1/单书，跨书迁移性另议（B5 的已知边界）。

## 附录 A · 回放判据（离线可重放）
- 输入：`novel-xinghuo-vol1/truth/resonance_trend.md` 表行（chapter/四维/overall/confidence/human_overridden），过滤 `human_overridden=true`，得 32 条已评分行；
- 规则：i≥8 起，`floor = clamp(percentile(prev 20, 0.25), 50, 80)`，`trigger = score_i < floor`（线性插值分位；与 #106 T1 同口径，plan 期钉死实现）；
- 结果：可评估 24 点，触发 ch14/16（77<78/79）→ 8.3%；分数斜率 +0.119/行（最小二乘）；
- 置换零假设：同分数多重集打乱 5000 次、seed=20261115，触发率 mean 21.2%、p2.5 8.3%、p97.5 29.2%；
- 饱和推演：模式带 79、sd 2.40、斜率 +0.06/章 → 约 15 章后 P25 触 cap 80，`score<80` 比例随通胀趋 0。
