> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C35）| **依赖:** 无（纯流程/工具面，不碰生产代码）| **范围:** audit-run 目录流程、findings-ledger 格式校验器、跨轮承接清单、git 分支卫生 | **核心洞察:** 审计闭环自身无 lint——上轮 verified 条目本轮零承接（F1177）、跨轮 F 编号 72/123 碰撞（F978）、ledger 19 行畸形行，都是"审计的审计"缺失的症状

# C35 · 审计过程自身卫生（audit-process-hygiene）

## 元信息
- 簇：C35（审计过程自身缺陷：编号复用/记账缺口/回写断链），18 条，最高严重度 P1（F771/F772 severity-dispute 条目），证据等级=实验佐证
- 成员：F1177（代表）、F767、F768、F771、F772、F894、F956、F969、F972、F973、F975、F978、F979、F1176、T513、T1501、T1502、T1507
- 来源：Z7/Z8/Z9 各复核轮 + thread-reports/T15.md、T5.md

## 背景与根因
审计自身的产物（ledger、分区清单、final-report、跨轮承接）没有任何机械校验，缺陷四类：
1. **跨轮承接断链**（F1177：上轮 F1301/F1302/F1320 三条 verified 本轮零承接且盘上复现，F1315-F1317 部分承接无映射；T513：上轮 T503/T504/T505 断链重立；T1501：revert 丢 g5 修复，follow-up 悬空 2 个月）
2. **ID 命名空间碰撞**（F978：跨轮 F 编号重叠 72/123——同 ID 不同 finding；F956：跨审计代编号复用；本轮 phase4 已吃到此苦头：ledger 19 行畸形重复行）
3. **记账缺口**（F969：final-report 统计 781 vs 786 自相矛盾；F973：zones 并集 2755 vs table-A 2738 差 17；F975：分区清单漏登 d1/coverage.xml；F1176：b 段加法笔误 1082→1083；F972：15 行仅 10 列 + 未转义管道）
4. **断言与可复现性**（F767：弱断言清点不完整；F768："96 tests collected"未指名文件不可复现；F894：跨段重复立案与同缺陷异处置——11 个 .gitkeep 三段 6 立案 5 放行）
5. **分支/索引卫生**（T1502：孤儿分支携带 481 行独有 spec 未开 PR；T1507：3 squash-merge 未删远程 + 10 dependabot 未 triage + INDEX 计数 66/68/63 三处漂移；F771/F772：severity 校准争议条目——处置为按 phase4 §4 提案执行）

## 目标
1. `audit-lint` 工具：校验 ledger 行格式（11 列、管道转义、ID 唯一）、分区清单并集=总表、final-report 统计=ledger 现值
2. 跨轮 ID 命名空间隔离（轮前缀或全局序号）+ verified 承接清单机制（新轮开跑时自动生成上轮未关闭 verified 条目清单）
3. 分支/PR 卫生一次性清偿 + INDEX 计数机械生成

## 任务分解
### R1 · ledger 与记账 lint（F972 + F973 + F975 + F969 + F1176 + phase4 §0 注记）
- `tools/lint_audit_run.py`：列数/管道转义/ID 唯一/重复行检测（本轮 19 畸形行形态入库为反例）；分区清单 ↔ ledger ↔ final-report 三方计数对账（任何差值非零 FAIL）
- **验收**：对 2026-08-15 audit-run 跑一遍——已知 5 类缺口全部被抓出（修复历史数据或显式豁免注记）；CI 可选 job 接入

### R2 · 跨轮命名空间与承接（F978 + F956 + F1177 + T513 + T1501）
- ledger ID 方案裁决：`F<轮标识>-NN` 或全局单调段（T/D 前缀同理）；写迁移注记而非改历史行
- 新轮启动脚本：从上轮 ledger 抽取 status=verified/open 的 P0/P1 生成承接清单文件，run 结束时 diff 承接状态——未承接条目 FAIL
- T1501 的"修复被 revert 丢失"类问题由承接清单自然覆盖（盘上复现检查）
- **验收**：用 2026-08-14 轮生成承接清单，F1301/F1302/F1320 出现在其中（演示断链会被抓）

### R3 · 断言清点与处置一致性（F767 + F768 + F894）
- 审计 prompt 模板补两规则：跨段重复立案须显式 merged 标注；"N tests"类声称必须附文件名与命令
- F894 的同缺陷异处置：phase4 clustering 已建立 merged-into 机制（737 条），本条随回写关闭
- **验收**：下一轮 audit prompt（full-project-audit-prompt.md v4 修订）含上述两规则

### R4 · 分支与 INDEX 卫生（T1502 + T1507 + F771/F772）
- T1502：孤儿分支 docs/token-efficiency-p2-spec 开 PR 或 cherry-pick 后删除（481 行 spec 去留由内容裁：若与现行 spec 重复则记录后弃）
- 删 3 个已 squash-merge 远程分支；dependabot 10 条 triage（升级或闭合并记录理由）
- INDEX 计数改脚本生成（活跃数=目录扫描），消除手工 66/68/63 漂移
- F771/F772：按 phase4-clustering.md §4 严重度校准提案执行（11 项升/降级 + 已采纳注记核对），只改 ledger 严重度列并留提案引用
- **验收**：`git branch -r` 无已合并残留；INDEX 计数与目录扫描一致；severity 校准 11 项落账

## 验收（簇级）
- `just check` 全绿（lint_audit_run 若入 CI，先对本轮数据生成豁免清单）
- C35 全部 18 条 merged-into F1177 回写关闭

## 风险
- R2 的 ID 方案变更影响所有引用旧 ID 的 spec/文档——只做"新轮生效"，旧轮文件不动；本批 2026-08-16 spec 仍用旧 ID 引用
- R4 severity 校准动 ledger 严重度列——与"审计不改 ledger"的轮内纪律冲突，故安排为轮后修复动作并逐条留提案引用（phase4 §4）

## 验证命令
- audit-lint 对账：`python3 tools/lint_audit_run.py docs/superpowers/audit-runs/2026-08-15`（已知 5 类缺口全被抓出或显式豁免）
- 承接演示：用 2026-08-14 轮 ledger 生成承接清单，`grep -c "F1301\|F1302\|F1320" <carryover>` ≥3
- 分支卫生：`git branch -r | wc -l`（已合并远程分支删除后核对）；INDEX 计数与 `ls docs/superpowers/specs/*.md | wc -l` 对账
- severity 校准：ledger 中 phase4 §4 的 11 项提案逐条落账（F131/F1103/F1105/F376/F536/F351/F004/F005/F438/F355/F007/F796——含二选一项）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F1177 <- F767-F768, F771-F772, F894, F956, F969, F972-F973, F975, F978-F979, F1176, T513, T1501-T1502, T1507`
- 软残条注记：F764（C24）与 F1176（本簇）为 phase4 §6 软残条，回写时保留原文
