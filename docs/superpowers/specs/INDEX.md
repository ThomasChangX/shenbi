# Spec 执行索引

> **最后更新**：2026-11-18（#109 完结归档 PR #361——bundle 审计覆盖正确性全链；前次同日 #109 r3 PR #359/#360）
> **活跃 spec 数**：16

本页只追踪活跃（待执行）spec，**表行序即推荐执行顺序**（依据见「排序依据」节）；优先级标注（🟥 Critical/🔴 P0 → 🟠 High/P1 → 🟡 Medium/P2 → ⚪ 批量）仅作 tie-breaker 与视觉分层。**spec 详情（动机证据/根因/任务分解/验收）以 spec 文件本体为唯一权威**，本页只留一句话范围与依赖——INDEX 不做 spec 的第二份拷贝（拷贝必漂移）。已完成/驳回的 spec 移至 `archive/`，编号 append-only 不重排不复用（系列/依赖按编号交叉引用）；归档历史查 `archive/` 与 `git log`。

**立项预答义务（v7.1）**：新立项 spec 须附**价值门预答栏**（④博弈路径清单＋⑤候选机制清单——`single-model-sdd-prompt.md` 阶段 1 五问后两问的立项侧前置）；缺栏＝价值门首查项（命中 REWRITE 补栏＝白付一轮 docs PR＋价值门重跑——#89/#90/#91/#92 四连每件一轮的实证成本）。

**维度登记**：活跃 spec 的「触及的不变量维度」写在 spec 文件本体（lint face-4 数据源，2026-11-17 起）。

---

## 执行队列

| 编号 | 优先级 | spec 文件 | 状态 | 一句话范围 | 依赖 |
|------|--------|-----------|------|-----------|------|
| #93 | 🟠 P1 | `2026-11-01-spec93-threshold-authority.md` | Design r3 | 阈值权威化：lint 改 import 执法＋删 allowlist 第三源＋`--strict` 接线＋定价契约单源＋trend 列常量覆盖三消费者＋疲劳词门-契约键形接线（T6） | 无（justfile 前序解锁 #116） |
| #116 | 🟠 P1 | `2026-11-15-spec116-gate-discriminative-power.md` | Design r1 | 门禁判别力仪表：真 G4 回放（10 散文门 50/50 恒真）→ `just gate-power`＋恒真登记＋WARN 哨兵＋六项标定提案（不改门行为，用户逐项裁定） | justfile 链 #92→#93→#116；T4 变异器 #108 后换装 |
| #110 | 🟠 P1 | `2026-11-15-spec110-judge-reliability-harness.md` | Design r1 | 评审信度 harness：判官间一致性/效度/分布形状离线报告（κ≈0、α=0.311、更好=0/32 实证）＋在飞 spec 判据营养接线 | 独立；数据卫生面消费 #109 T4 口径 |
| #117 | 🟠 P1 | `2026-11-15-spec117-audit-evidence-verifiability.md` | Design r1 | 审计证据可验证性：发现级 parser＋G4.av.evidence_* 逐字/行号/规则名对账＋消费三态（28.2% 引述无逐字来源实证） | #105 已核销；justfile #92→#116→#117 |
| #107 | 🟡 P2 | `2026-11-15-spec107-reviewer-model-tier.md` | Design r1 | 评评分档：executor_config per-skill model 键单源接线＋量表 A/B 预注册（默认行为零变化差分钉死；第二模型随用户令） | #92 已完结（dispatch_helper 同文件无冲突）；A/B 随令 |
| #111 | 🟠 P1 | `2026-11-15-spec111-extractor-shape-contract.md` | Design r1 | extractor 形状契约：两形状并认＋应用率哨兵＋truth 增长曲线＋全量读面收编（44 次生产 reads 全空转实证） | #92→#105/#107→#109→#111 链尾 |
| #112 | 🟠 P1 | `2026-11-15-spec112-chapter-loop-properties.md` | Design r1 | chapter_loop 性质测试：12 条不变量文档化＋hypothesis 状态机＋已知反例回归收编（E-3/E-9 P1 先修；E-11 挂账用户裁定） | #109 后链尾 |
| #103 | 🟡 P2 | `2026-11-15-spec103-highlight-distill.md` | Design r1 | 高光复盘与成功传染：确定性选章（median+5 相对阈值）＋三层归因手法卡 playbook＋anchors 第四源（读者信号接范文环）＋老化变奏 | 独立（消费管道现成） |
| #115 | 🟠 P1 | `2026-11-15-spec115-quality-measurement-endogeneity.md` | Design r1 | 质量测量内生性：P25 分位语义拆分（rank_alarm vs 绝对 floor）＋风格回路 holdout＋外部锚定预注册（点火 8.3% vs 置换零假设 21.2% 实证） | #105→#106→#109→#115；SKILL 面 #110 后；drift/style 面 #103 后 |
| #94 | 🟡 P2 | `2026-11-01-spec94-interface-honesty.md` | Design r2.2 | 接口诚实批：modes 清障＋cli 引擎出鞘（orchestration/checkpoint_flow 搬家）＋scoring 归一化＋DispatchContext 收拢＋文档诚实小批 | T4/T6 前序（#87/#85）已完结 → 实质独立 |
| #96 | 🟡 P2 | `2026-11-04-spec96-anti-ai-tell-alignment.md` | **Active** r2 | 反 AI 检测方法论对齐：双源对标（blader/humanizer-zh）＋五缺口＋四任务；检测器导向硬闸全保留（用户裁定：两目标并存） | #95 T1 词表单源落地后＋批次 A 清偿后启动 |
| #102 | 🟠 P1 | `2026-11-15-spec102-declared-deviation.md` | Design r1 | 声明式计划偏离：deviations[] 申报＋G4.dec 扩展＋三择一裁定＋硬边界三条——修「计划腔」服从性结构层 | #96 后（同碰 drafting SKILL 面） |
| #104 | 🟠 P1 | `2026-11-15-spec104-power-system-expansion.md` | Design r1 | 力量体系卷界扩容：power_system.md 双区化＋TRIGGER_STEPS 扩容群＋G4.ps.expand 四检查（前层不可变/单调/编年/钩可达） | 无硬依赖；建议 #102/#103 实弹后施工 |
| #108 | 🟡 P2 | `2026-11-15-spec108-audit-recall-canary.md` | Design r1 | 审核灵敏度探针：确定性变异器目录＋dry-run 默认 harness＋召回矩阵——审计召回第一元指标（实弹 ≈$0.35 随令） | 独立（dry-run 零成本）；实弹随用户令 |
| #113 | 🟡 P2 | `2026-11-15-spec113-untrusted-delimiting.md` | Design r1 | 不可信文本定界加固：wrap 原语六通道扩展＋反引号伪围栏防御＋注入抵抗力 A/B 预注册 | chapter_loop 链 #112 后；review_checklist 面 #96→#105 后 |
| #114 | 🟡 P2 | `2026-11-15-spec114-escalation-triage.md` | Design r1 | escalation 自动分诊：同门首次三振机器反馈升级/内容争议留人审＋裁决书机器可读索引（16 份中 12 份确定性三振实证） | #105 T4 后；#112 后链尾 |

## 排序依据（2026-11-15 全队列重排，压缩存档）

1. **最深依赖链先开闸**：`#105→#106→#109→{#111,#112,#115,#113,#114}` 为全队最深链且 #109 是唯一 🔴 P0；链头 #105 已核销（PR #351）→ 现队头 #106。
2. **前序欠账早清**：#93（批次 A 残件，无依赖）插位第 3 解锁 #116/#110/#117；#107/#103 分别为 #111/#115 链前序提序。
3. **#96 后半场闸门**：#94/#96 排 12/13 位，#102/#104（写作工艺批）随 #96 后展开；#108 独立 dry-run 排后；#113/#114 双链尾收尾。

付费实弹面不受本序约束（#108 实弹束/#113 A/B/#107 A/B/#115 T3 人工面板均随用户令）。
