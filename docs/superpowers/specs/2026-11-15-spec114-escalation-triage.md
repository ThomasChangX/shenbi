# Spec #114 · escalation 自动分诊（escalation-triage）：门禁三振分诊矩阵、裁决书机器可读索引、vol1 回放分诊报告

**日期**：2026-11-15｜ **系列**：多专家审计批（expert-audit）｜ **状态**：Design（r1，2026-11-15）｜ **优先级**：🟡 P2
**动机证据**：`novel-xinghuo-vol1/audits/escalation-*-report.md` 16 份触发信号分布（2026-11-15 解析）：**12/16 为确定性 G4 门禁三振**（`G4.cp.scene_budget` ×3［ch5/35/39］、`g4_retry_exhausted` settling 族 ×3［ch3/15/41］、planning G4 硬闸 ×4［ch33/37/47 + 重试桥 ×1］、`ss.identity_row_match` ×1［ch29］）+ planning 派发失败 ×1 + 其余 2——人审带宽被**机器门禁僵局**占用，内容争议类人审为少数；同门复发模式：scene_budget 族跨 ch5/35/39 三次独立升级（人审每次重裁同类问题）；`novel-xinghuo-vol1/adjudications/` 31 份裁决书**格式异构机器不可读**（解析实验：正则抽决策行仅 8/31 成功——头格式三种变体「裁决书 #NNN —/裁决 #NNN —」、决策行位置不定）；决策回流无结构化通道（`#106 T3 override-resonance` 只覆盖 resonance 一面；裁决口径如 adjudication-001「卷界铁律 619 章/12 卷」散落文档无索引）；`executor_config.toml:188-195`（评审预算注释自认 "deferred to P1 pilot"——同族欠账文化对照）；`chapter_loop.py:2007-2049`（`_escalate_step_failure` 单一出口——分类信息在 reports 有、在路由无）。

**触及的不变量维度**：无（人审带宽基建——不改任何叙事维度门检）

---

## 0. 根因

**escalation 是单一出口，把「机器能自愈的」与「必须人裁的」混在同一通道**：门禁三振的本质是「确定性反馈不够好」（同门禁重复失败=反馈文案/示例缺位，#105 T4 的 G4_FORMAT_EXAMPLES 族缺口正是其根源之一），却消耗最贵的人审决策；同时裁决书作为体系最高质量的人类决策资产，是散落文档不是数据——#106 想接 human_overridden 回流时发现无通道，是同一根因的另一个面。

**用户裁定（2026-11-15）**：分诊只动「同门禁可机器反馈升级」类；**内容争议类一律保留人审**；裁决书不强制改人写格式（索引旁挂，append_dedup 机器维护）。

**备选案已评估并否决**：「全面 auto-retry 加码（三振改五振）」——掩盖反馈质量根因且拉长熔断时间；「裁决书全面结构化改版」——31 份存量是人写资产不回改，新格式强制会降低人审体验（本件索引路线零侵入）。

## 1. 任务分解

### T1 · 门禁三振分诊矩阵
- `pipeline/escalation_triage.py`：输入=失败技能+gate check id+失败形态（retry_feedback 摘要）；输出=「机器反馈升级」（gate 类别 ∈ {声明行格式族/数值对账族/结构保全员族} 且**同 check id 本项目首次三振** → 升级反馈=差分模板［期望行格式示例+本产出 diff 锚——G4_FORMAT_EXAMPLES 差集补齐为前置，#105 T4 面］+ 重派一轮）或「人审保留」（内容争议/同 check id 二次以上三振/形态未分类——**防机器死循环**）；
- 分诊决策落 escalation 报告头部（机器可读行：`triage: machine-feedback|human|repeat`）。

**判据**：单测三分支（首次三振声明族→machine-feedback；同 id 二次→human；未分类→human）；`git grep triage:` 报告头模板命中。

### T2 · 裁决书机器可读索引
- `adjudications/INDEX.md`（append_dedup，ledger_archive 先例）：每行 `编号 | checkpoint | 决策 | 一句话摘要 | 口径键`；解析器容错三变体头格式；既有 31 份一次性回放建索引（**只读源文件产索引，不改源**）。

**判据**：索引落盘 31 行；断言工具（`just adjudication-lint <dir>` 或并入 audit-lint）对新裁决提醒补行（WARN 级）。

### T3 · vol1 回放分诊报告
- 对 16 份 escalation 回放 T1 矩阵：预期 machine-feedback 命中清单（scene_budget 首现 ch5 等）/human 保留清单（repeat 项 ch35/39 等）+ 若当时有此机制可省的人审次数估算——**只报不写**，为分诊矩阵阈值提供第一批实证。

**判据**：回放报告落盘 `reports/escalation-triage-replay-<ts>.md`；两清单计数与动机证据节口径一致（12 门禁类中 repeat 判定 ≥3）。

## 2. 验收
1. T1-T3 判据全绿；
2. 回放报告证明矩阵有牙（repeat 类被拦入 human——机器死锁不可能）；
3. 首个适用运行窗观察：escalation 总量中 human 占比上升（机器可愈类被消化）、同 check id 三振复发率下降。

## 3. 风险
- 误分诊吞真缺陷——保留面从严三分（内容争议/重复/未分类全人审）+ machine-feedback 只加一轮重派不豁免门禁（门禁仍是硬闸）；
- 分诊与 G7 审计面混淆——分诊只动 escalation 出口路由，G7 静态审计不动；
- **共享文件面**：`chapter_loop.py` `_escalate_step_failure` 面排在 #105→#106→#109→#112→#113 链尾；G4_FORMAT_EXAMPLES 面与 #105 T4 共享——**#105 先**；escalation-review SKILL 不改（报告头由框架注入）。
