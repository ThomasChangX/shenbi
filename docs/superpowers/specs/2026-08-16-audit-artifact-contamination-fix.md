> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-08 · 阶段 1 价值门 REWRITE：派发层根因已由 main 后续合并根治，存量缩量 109→52) | **Severity:** 🟠 P1
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C18，候选元根因 G）| **代表 finding:** F1171 | **簇规模:** 17 条 | **严重度上限:** P1
> **范围:** novel-output/xinghuo-ranqiong/（生产树存量清洗）、src/shenbi/pipeline/dispatch_helper.py（验证性任务）、产物 lint（tools/ + CI） | **证据等级:** 实验佐证（Z11 双轮复扫 + 2026-09-08 驳斥复核 14 存活/3 降级/0 驳回）
> **与既有 spec 关系:** R5（revision 摘要覆写正文）属数据丢失簇 #7；本 spec 只管污染清洗与产物 lint，不重复 #7 内容；C25（#63）T1504 novel-output 反忽略出库为协同边

# C18 · 生产产物污染清洗与派发沙箱修复（artifact-contamination）

## 背景（根因 + 证据 · 2026-09-08 修订）

**根因（历史）**：LLM 派发沙箱的写权限制未在派发层解决，把"只读沙箱无法写入，请手动复制"的元叙述泄漏进产物；同时手动/DEBUG 模式跑出的自证缺陷（手算分数、时间戳编造）混入生产树。

**派发层现状（已根治，本 spec 只做验证）**：`src/shenbi/pipeline/dispatch_helper.py`（原 spec 误写 `dispatcher/dispatch_helper.py`，该路径已不存在）现为产物捕获模式——prompt 强制 `### FILE:` 标记、派发层解析后代写入 project_dir；IDE CLI 带 `sandbox_permissions=workspace-write`（L2407，codex 路径；zcode 路径自认未测）；`helper_injection.py` 把确定性 helper 结果预注入 prompt（#33 T1a）。src/skills/tools 全域元叙述模式 0 命中——**新增污染源已断**。残余任务仅为 zcode CLI 分支 sandbox flag 的验证性接线确认。

代表证据（2026-09-08 main HEAD 亲证）：
- **F1171**（P1，降级存活）：存量元叙述污染宽模式族（手动复制/只读沙箱/无法写入/请手动/manually copy/read-only sandbox/cannot write）union 计数 **52 文件**（audits 27 + snapshots 18 + chapters 5 + plans 2；原指控 109，staging/decisions 层已由 #21/#20 后续合并清零；正文污染反增 1→5），全部在 xinghuo-ranqiong 旧产物（2026-07-15~07-19）
- **F1162**（P1，降级存活）：维度覆盖已改善至 55/56 章 13 类（原指控 35/56），ch56 缺 6 类；但 **2 章 resonance 手算自证存活**：`audits/chapter-49-resonance.md:5`、`chapter-51-resonance.md:31` 均自证"确定性 helper 无法在只读沙箱中执行…均为手动计算"
- **F1108**（P1，存活）：审计冗余 7.3MB 对正文 2.0MB（3.65x），snapshots 12M 内嵌审计全文二次嵌埋
- **F1172**（P2，存活）：ch51 resonance 手算 trend 错值——「近3章均值」与评分明细表对不上（场景临场感实算 16.0 报 13.7、文笔质感实算 18.3+ 报 16.3 等）；「超出阈值 >5」断言为假（70−65=5 恰在 ±5 边界带，与自身"无维度在阈值±5内"矛盾）
- **F1165**（P2，存活·精确复现）：pipeline-state.json audit_reports vs 磁盘对账缺 **117 项**（resonance 55 + review-summary 55，ch56 整章无 audit_results 键）——与上轮 F1311 数字一字不差，无 lint 则会第三次发生
- P2 族存活：F1117（validation-report FAIL 集如实滞留）、F1118（DEBUG_USE_MANUAL_CREATE.md 132 行自证缺陷/脱轨）、F1119（三树结构漂移）、F1163（ch7/ch8 时间戳同为伪造整点 12:00:00 vs ch9 09:23 倒挂）、F1164（ch35 缺 decisions）、F1166（G4 marker 混入 07-19 验证运行写生产树）、F1167（texture 配置 true 但 audits 0 文件）、F1168（truth-index 仅 3 条 genesis 实体，truth/ 13 文件未索引）、F1173（ch49/51 手算 vs ch50 引用 helper 输出的可用性矛盾）、F1174（ch35 超时重试无账）
- 降级：F1169（M）`.hypothesis/patches/` 13 文件 17 例 → 现 **4 patch 4 例**，仍无 applied/voided 落账
- 批量：F1170（M）2 个 0 字节 lockfile 在场（xinghuo-ranqiong 与 test-validation 的 pipeline-state.json.lockfile）

## 目标

1. **派发层验证（原"根治"降级）**：确认捕获模式 + helper 预注入覆盖 zcode CLI 分支（未测注记），产出验证证据而非新开发
2. **产物 lint 拦截**：新增产物污染 lint（元叙述标记模式族、手算分数自证、时间戳单调性、state↔磁盘对账），挂 tools/ + CI（`just check` 面）
3. **存量清洗**：52 文件按层（audits 27/snapshots 18/chapters 5/plans 2）清洗，清洗前后 lint 计数对照可复验
4. 修复可信度重建：手算分数机器重算覆盖、时间戳/marker/truth-index/对账缺口逐项补账

## 任务分解

### T1 · 派发层验证 + 审计体积治理
1. 验证性任务：zcode CLI 分支 sandbox flag/捕获模式接线确认（fixtures 回放等价路径，禁真实 dispatch——F947 离线化）；确认无第三套写路径语义
2. 审计波体积治理（F1108）：审计报告默认聚合/去冗后落盘，快照内不再嵌埋审计全文（对齐 output-side-waste 聚合层设计）

### T2 · 产物 lint
3. 新增 lint（tools/ 脚本 + `just check`）：(a) 元叙述标记模式族（中英 7 模式）；(b) 手算自证模式（"手动计算/手算"与数值并存）；(c) 时间戳单调性（同产物链内）；(d) state↔磁盘对账（audit_reports vs 文件，堵 F1165 类回归）
4. lint 对 novel-output 全树跑出基线报告 = T3 清洗清单的机械来源

### T3 · 存量清洗（按层分批，52 文件）
5. audits 层（27）：剥离元叙述块保留实质；ch49/ch51 手算分数用 skill_utils 确定性 helper 重算覆盖，旧值留档对比
6. snapshots 层（18）：内嵌审计全文随 T1.2 聚合不再产生；存量剥离
7. chapters 层（5）+ plans 层（2）：行级剥离元叙述；ch35 补 drafting-decisions（F1164）
8. F1163/F1166/F1168/F1174：时间戳更正、marker 清除、truth-index 重生成、verdict 重试补账
9. F1169：4 个 patch 回归例 applied/voided 二态落账；F1170：2 个 0 字节 lockfile 删除

## 验收标准（真实数据可复验）

1. 产物 lint 全树跑批：清洗前基线 52 文件计数留存于 run 记录，清洗后同一 lint 报告 0 命中（前后对照可复验）
2. 派发层验证：fixtures 回放等价路径产物 0 元叙述（lint + 人工抽查双确认）
3. 手算分数替换：ch49/ch51 机器重算值落盘，脚本与输入可从仓库复现（确定性 helper，无 LLM 依赖）；ch51 trend 错值以重算值覆盖
4. `git grep -l "手动复制\|只读沙箱" novel-output/` 0 命中（模式族以 lint 定义为准）
5. F1169 的 4 个 patch 回归例状态落账（applied/voided 二态）；F1170 lockfile 删除后 `find novel-output -name "*.lockfile" -size 0` 0 输出

## 风险与回滚

- **风险**：清洗 52 文件动生产树——分批 commit + 每批前后 lint 计数对照；正文与快照层清洗前打 git tag 便于整体回退
- **风险**：audit 聚合层改变审计报告结构，下游读者（G7、审计波读者技能）契约同步——登记进 C1 对账面
- **风险**：state 对账 lint 需容忍合法滞后（运行中产物），避免假阳性阻断 CI——lint 只跑 novel-output 静态树
- **回滚**：lint 带 flag 可关闭；清洗批次按 tag revert

## 簇成员清单（17 条，自查用 · 2026-09-08 复核状态）

F1108 存活, F1117 存活, F1118 存活, F1119 存活, F1162 降级存活, F1163 存活, F1164 存活, F1165 存活, F1166 存活, F1167 存活, F1168 存活, F1169 降级(17→4), F1170 存活, F1171 降级(109→52), F1172 存活, F1173 存活, F1174 存活
