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
5. **分支/索引卫生**（T1502：孤儿分支携带 481 行独有 spec 未开 PR；T1507：3 squash-merge 未删远程 + 10 dependabot 未 triage + INDEX 计数 66/68/63 三处漂移；F771/F772：severity 校准争议条目——处置为核实 phase4 §4 已落账的 12 项校准并补提案引用注记（**2026-09-07 修订**：落账已由 PR #147 完成，见 R4））

## 目标
1. `audit-lint` 工具：校验 ledger 行格式（11 列、管道转义、ID 唯一）、分区清单并集=总表、final-report 统计=ledger 现值
2. 跨轮 ID 命名空间隔离（轮前缀或全局序号）+ verified 承接清单机制（新轮开跑时自动生成上轮未关闭 verified 条目清单）
3. 分支/PR 卫生一次性清偿 + INDEX 计数机械生成

## 任务分解
> 执行顺序：R1 → R2（承接生成器依赖行格式 lint 先落地，畸形行策略未定时解析不可靠）；R3/R4 与 R1/R2 无依赖可后置

### R1 · ledger 与记账 lint（F972 + F973 + F975 + F969 + F1176 + F979 + phase4 §0 注记）
- `tools/lint_audit_run.py`：列数/管道转义/ID 唯一/重复行检测（本轮 19 畸形行形态入库为反例）；分区清单 ↔ ledger ↔ final-report 三方计数对账（任何差值非零 FAIL）
- F979（标题列转录缺口，本批已回填）由本项行格式 lint 显式覆盖（标题≠ID 占位检查），随簇回写关闭
- **接线强制（防 dead-wire）**：justfile 增 `audit-lint` recipe 并纳入 `just check` 与 ci workflow——recipe 无参 = check 模式，固定 lint 全部 `docs/superpowers/audit-runs/*/` 现存 run 目录（脚本内置无参全目录模式；带 `<run-dir>` 参数 = 单目录模式）；历史冻结 run（2026-08-14/2026-08-15）**只加显式豁免注记，不改历史行**，修复策略只对未来 run 生效
- 豁免机制定义：豁免文件为 `<run-dir>/audit-lint-exemptions.json`，schema `{"exemptions": [{"check": "<检查类名>", "id": "<F/T 编号、行标识，或聚合检查的 run 级 id `run:<检查类名>`>", "reason": "<一句话>", "date": "YYYY-MM-DD"}]}`（计数对账类聚合检查无自然条目 ID，用 run 级 id 豁免整检查项）；唯一读方是 `lint_audit_run.py`（判定 FAIL 前加载，逐条匹配消音）；lint 自身校验豁免文件 schema 与「豁免 id 必须对应真实命中项」（豁免不命中 = FAIL，防豁免腐烂）；无豁免文件的 run 目录一律 strict
- **验收**：`just audit-lint`（无参全目录模式——F969/F972/F973 缺口在 2026-08-14 run、F975/F1176 在 2026-08-15 run，须两轮都被扫）——成员缺口 F969/F972/F973/F975/F1176 五类全部被抓出且以豁免注记闭合；`just check` 含该 lint 且全绿

### R2 · 跨轮命名空间与承接（F978 + F956 + F1177 + T513 + T1501）
- ledger ID 方案裁决：`F<轮标识>-NN` 或全局单调段（T/D 前缀同理）；写迁移注记而非改历史行（旧轮文件与既有 spec 的旧 ID 引用一律不动，新轮生效）
- 新轮启动脚本 `tools/generate_carryover.py`：从上轮 ledger 抽取 status=verified/open 的**全 severity** 条目（P0/P1/P2/M 一律纳入——F1177 本身为 P2、F969 为 P2，任何 severity 截断都会为该级复现 F1177 断链）生成承接清单文件 `carryover.md`（每条目一行 `<ID> <severity> <status> <标题摘要>`，grep 词边界可精确命中）；run 结束时的承接核验由 `lint_audit_run.py --verify-carryover`（或无参 check 模式自动执行）承担：diff 承接清单条目与本轮 ledger 的承接状态——未承接条目 FAIL，进 `just check`；**无承接文件的 run 目录跳过该检查**（首轮无上轮、冻结历史 run 无清单——跳过显式 log，非静默）
- T1501 的"修复被 revert 丢失"类问题由承接清单自然覆盖（盘上复现检查）
- **验收**：用 2026-08-14 轮生成承接清单 `carryover.md`，`grep -Ecw "F1301|F1302|F1320" docs/superpowers/audit-runs/2026-08-14/carryover.md` ≥3（ERE + 词边界精确匹配，防 F1301x 误配与 BRE 跨平台漂移）

### R3 · 断言清点与处置一致性（F767 + F768 + F894）
- 审计 prompt 模板（full-project-audit-prompt.md，本 spec 为授权修订载体）补两规则：跨段重复立案须显式 merged 标注；"N tests"类声称必须附文件名与命令
- F894 的同缺陷异处置：phase4 clustering 已建立 merged-into 机制（737 条），本条随回写关闭
- **验收**：本 spec 落地后 `grep -n "跨段重复立案\|N tests" docs/superpowers/full-project-audit-prompt.md` 命中两新增规则文本

### R4 · 分支与 INDEX 卫生（T1502 + T1507 + F771/F772）
- T1502：~~孤儿分支 docs/token-efficiency-p2-spec 开 PR 或 cherry-pick 后删除~~（**阶段 2 修订 2026-09-07**：分支已在 main 历史中被清除、无处置记录——本项降为「记录裁决 + 回写关闭」，481 行 spec 内容 grep main 零副本，按记录后弃处置）
- 删已 squash-merge 未清的远程分支（现核：`origin/docs/archive-spec44-c30` 1 支，`git branch -r --merged origin/main` 为准）；dependabot 10 条 **triage 决策记录**（每条 upgrade/close + 理由，写入本 spec 交付的 triage 记录文件；**实际升级/合并不在本 spec 范围**——依赖升级动 uv.lock/生产代码，与「不碰生产代码」边界冲突，另开 chore 批次执行）
- INDEX 计数改脚本生成（`tools/count_active_specs.py`：目录扫描活跃条目并核对 INDEX 头计数，差值非零 FAIL；纳入 `just check`），消除手工 66/68/63 漂移
- F771/F772：按 phase4-clustering.md §4 严重度校准提案执行（~~11 项~~ **12 项**升/降级 + 已采纳注记核对），只改 ledger 严重度列并留提案引用（**阶段 2 修订 2026-09-07**：12 项校准已在 main 落账（总纲记账 pass PR #147 一并完成）——本项降为「逐项核实 + 补提案引用注记 + 回写关闭」，不改严重度列）
- **验收**：`git branch -r` 无已合并残留；INDEX 计数与目录扫描一致；severity 校准核实+注记完成

## 验收（簇级）
- `just check` 全绿（audit-lint 已纳入 check；对 2026-08-14/15 冻结 run 的豁免清单随本 spec 落地）
- C35 全部 18 条 merged-into F1177 回写关闭

## 风险
- R2 的 ID 方案变更影响所有引用旧 ID 的 spec/文档——只做"新轮生效"，旧轮文件不动；本批 2026-08-16 spec 仍用旧 ID 引用
- ~~R4 severity 校准动 ledger 严重度列~~（已由 PR #147 落账，本 spec 仅核实+注记，风险消解）
- R4 dependabot triage 若发现升级紧迫（安全补丁类），记录中标注 urgent 并建议立即开 chore PR，不在本 spec 内升级

## 验证命令
- audit-lint 对账：`just audit-lint docs/superpowers/audit-runs/2026-08-15`（成员缺口 F969/F972/F973/F975/F1176 全被抓出且以豁免注记闭合）
- 承接演示：用 2026-08-14 轮 ledger 生成承接清单，`grep -Ecw "F1301|F1302|F1320" docs/superpowers/audit-runs/2026-08-14/carryover.md` ≥3
- 分支卫生：`git branch -r --merged origin/main` 除 origin/main 与 origin/HEAD 符号引用外为空；INDEX 计数与 `tools/count_active_specs.py` 输出一致（自动核对，差值非零 FAIL；条目内 prose 计数漂移不在此检查面，属已知残口记 deviation）
- severity 校准：phase4 §4 12 项提案逐项核实注记（F131/F1103/F1105/F376/F536/F351/F004/F005/F438/F355/F007/F796——含二选一项已裁 F007=P2）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F1177 <- F767-F768, F771-F772, F894, F956, F969, F972-F973, F975, F978-F979, F1176, T513, T1501-T1502, T1507`
- 软残条注记：F764（C24）与 F1176（本簇）为 phase4 §6 软残条，回写时保留原文
