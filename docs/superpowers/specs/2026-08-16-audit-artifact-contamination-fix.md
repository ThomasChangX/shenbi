> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-08 · 阶段 1 价值门 REWRITE：派发层根因已由 main 后续合并根治，存量缩量 109→52) | **Severity:** 🟠 P1
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C18，候选元根因 G）| **代表 finding:** F1171 | **簇规模:** 17 条 | **严重度上限:** P1
> **范围:** novel-output/ 全树（生产树 xinghuo-ranqiong/ 存量清洗为主；validation-results/ 历史记录注记）、src/shenbi/pipeline/dispatch_helper.py（验证性任务）、产物 lint（tools/ + CI，作用域 novel-output 全树） | **证据等级:** 实验佐证（Z11 双轮复扫 + 2026-09-08 驳斥复核 14 存活/3 降级/0 驳回）
> **与既有 spec 关系:** R5（revision 摘要覆写正文）属数据丢失簇 #7；本 spec 只管污染清洗与产物 lint，不重复 #7 内容；C25（#63）T1504 novel-output 反忽略出库为协同边

# C18 · 生产产物污染清洗与派发沙箱修复（artifact-contamination）

## 背景（根因 + 证据 · 2026-09-08 修订）

**根因（历史）**：LLM 派发沙箱的写权限制未在派发层解决，把"只读沙箱无法写入，请手动复制"的元叙述泄漏进产物；同时手动/DEBUG 模式跑出的自证缺陷（手算分数、时间戳编造）混入生产树。

**派发层现状（已根治，本 spec 只做验证）**：`src/shenbi/pipeline/dispatch_helper.py`（原 spec 误写 `dispatcher/dispatch_helper.py`，该路径已不存在）现为产物捕获模式——prompt 强制 `### FILE:` 标记、派发层解析后代写入 project_dir；IDE CLI 带 `sandbox_permissions=workspace-write`（L2407，codex 路径；zcode 路径自认未测）；`helper_injection.py` 把确定性 helper 结果预注入 prompt（#33 T1a）。src/skills/tools 全域元叙述模式 0 命中——**新增污染源已断**。残余任务仅为 zcode CLI 分支 sandbox flag 的验证性接线确认。

代表证据（2026-09-08 main HEAD 亲证）：
- **F1171**（P1，降级存活）：存量元叙述污染宽模式族（手动复制/只读沙箱/无法写入/请手动/manually copy/read-only sandbox/cannot write）union 计数 **52 文件**（audits 27 + snapshots 18 + chapters 5 + plans 2——**chapters/plans 的 7 个命中全部是 `*-decisions.json` sidecar**，非 md 正文；lint 扫描全文件类型，md 正文叙事性「手动」字样不属模式族；原指控 109，staging/decisions 层元叙述模式已由 #21/#20 后续合并清零（staging 仍有 1 文件带 F1163 伪时间戳签名，归任务 8 裁决）；正文污染反增 1→5），全部在 xinghuo-ranqiong 旧产物（2026-07-15~07-19）
- **F1162**（P1，降级存活）：维度覆盖已改善至 55/56 章 13 类（原指控 35/56），ch56 缺 6 类；但 **2 章 resonance 手算自证存活**：`audits/chapter-49-resonance.md:5`、`chapter-51-resonance.md:31` 均自证"确定性 helper 无法在只读沙箱中执行…均为手动计算"
- **F1108**（P1，存活）：审计冗余 audits ~7.5MB（du -sk 口径）对正文 ~2.0MB（3.65x），snapshots ~12.7M 内嵌审计全文二次嵌埋
- **F1172**（P2，存活）：ch51 resonance 手算 trend 错值——「近3章均值」与评分明细表对不上（场景临场感实算 16.0 报 13.7、文笔质感实算 18.3+ 报 16.3 等）；「超出阈值 >5」断言为假（70−65=5 恰在 ±5 边界带，与自身"无维度在阈值±5内"矛盾）
- **F1165**（P2，存活·精确复现）：pipeline-state.json audit_reports vs 磁盘对账缺 **117 项**（resonance 55 + review-summary 55 + ch56 整章：audit_results 键在但值为空 dict，磁盘 7 文件未入账）——与上轮 F1311 数字一字不差，无 lint 则会第三次发生
- P2 族存活：F1117（validation-report FAIL 集如实滞留）、F1118（DEBUG_USE_MANUAL_CREATE.md 132 行自证缺陷/脱轨）、F1119（三树结构漂移）、F1163（同伪整点签名·plan 审查扩面：**~15 个完整串重复组 ~65 文件（以 lint 基线实测分组为准）**（全部整点零分零秒——framework 现行写 `datetime.now(UTC).isoformat()` 真实时刻，整点零分零秒批量形态即 manual-era 编造族；最大组 2026-07-17T00:00:00Z 14 文件、2026-07-16T12:00:00Z 14 文件、2026-07-16T00:00:00Z 7 文件）；ch7/ch8 12:00:00Z vs ch9 resonance 09:23 倒挂；真实时间不可考，**修复不得发明新时间**）、F1164（ch35 缺 decisions）、F1166（G4 marker 混入 07-19 验证运行写生产树）、F1167（texture 配置 true 但 audits 0 文件）、F1168（truth-index 停留早期态：仅 3 个顶层键 19 条实体，truth/ 13 文件未索引）、F1173（ch49/51 手算 vs ch50 引用 helper 输出的可用性矛盾）、F1174（ch35 超时重试无账）
- 降级：F1169（M）`.hypothesis/patches/` 13 文件 17 例 → 现 **4 patch 4 例**，仍无 applied/voided 落账
- 批量：F1170（M）2 个 0 字节 lockfile 在场（xinghuo-ranqiong 与 test-validation 的 pipeline-state.json.lockfile）

## 目标

1. **派发层验证（原"根治"降级）**：确认捕获模式 + helper 预注入覆盖 zcode CLI 分支（未测注记），产出验证证据而非新开发
2. **产物 lint 拦截**：新增产物污染 lint（元叙述标记模式族、手算分数自证、时间戳单调性、state↔磁盘对账），挂 tools/ + CI（`just check` 面）
3. **存量清洗**：52 文件按层（audits 27/snapshots 18/chapters 5/plans 2）清洗，清洗前后 lint 计数对照可复验
4. 修复可信度重建：手算分数机器重算覆盖、时间戳/marker/truth-index/对账缺口逐项补账

## 任务分解

### T1 · 派发层验证 + 审计体积治理
1. 验证性任务：zcode CLI 分支 sandbox flag/捕获模式接线确认——机制 = **命令行构造断言测试**（现状：`_find_ide_cli` 对 codex/zcode 返回同一份 codex 专属 argv；单测 monkeypatch `shutil.which` 分别解析两 CLI，断言共享 argv 含捕获模式参数、不含元叙述注入，子进程不实际 spawn；zcode 专属 flag 未测记 deviation）+ **人工抽查 = 审查命令行构造输出与既有捕获产物 fixture**（禁真实 dispatch，F947 离线化）；zcode/codex 路径各 ≥1 例，结果记入 run 记录；确认无第三套写路径语义
2. 审计体积治理（F1108）· 增量核实：聚合层**代码**已在 main（`src/shenbi/pipeline/audit_aggregate.py`；生产树 audits/ 尚无 aggregate 产物，未在该树跑过）；本 task 只做两件事——(a) 核实现行代码是否仍有快照写入时嵌埋审计全文的路径（grep 快照写入模块；若嵌埋纯属历史 dispatch 行为则记 deviation 不开发），(b) 快照体积收益归 T3.6 存量剥离

### T2 · 产物 lint
3. 新增 lint（tools/ 脚本 + `just check`）：(a) 元叙述标记模式族（中英 7 模式）；(b) 手算自证模式（"手动计算/手算"与数值并存）；(c) 时间戳校验——同文件产物链内单调性 + **跨文件同完整时间戳签名**（≥2 文件共享同一完整 ISO 时间戳串且整点零分零秒；跨文件乱序仍为合法不校验）；(d) state↔磁盘对账（`state["chapter_loop"]["chapter_states"][<N>]["audit_results"]["audit_reports"]` 为 **list[相对路径]**——对账磁盘 `audits/chapter-N-*.md` 文件，两分支：磁盘文件路径未入账 / 清单容器为空或键缺失，堵 F1165 类回归；仅静态树）。**per-check 豁免清单覆盖全部四 check**，与 lint 同 repo 维护，豁免条目不计入命中计数
4. lint 对 novel-output 全树跑出基线报告 = T3 清洗清单的机械来源

### T3 · 存量清洗（按层分批，基线计数以首跑 lint 为准，预期 52：audits 27 + snapshots 18 + chapters 5 json + plans 2 json）
5. audits 层（27）：剥离元叙述块保留实质；ch49/ch51 手算自证句剥离 + 维度分**保留原值并加 provenance 注记**（`manual-era score, retained`）——机器重算仅覆盖确定性层：calibration 校准门（`skill_utils/calibration/confidence.py::calibrate_confidence`）、§5.4 分流（`pipeline/revision_router`）、近3章均值算术（F1172 错值以重算值覆盖，旧值留档于 run 记录 `docs/superpowers/audit-runs/2026-09-08-c18-cleanup/`，不留在 novel-output 内以免再触 lint(b)）；重算脚本落位同 run 记录目录（oneoff，非 src/ 常驻）
6. snapshots 层（18）：存量剥离内嵌审计全文（快照体积收益所在）
7. chapters 层（5）+ plans 层（2，均为 `*-decisions.json` sidecar）：剥离 sidecar 内元叙述字段/文本；ch35 补 drafting-decisions（F1164）；`skill_utils/review_resonance/` 空壳包（#33 T1b 删除后遗留）顺手清理
8. F1163（~15 组逐组裁决，不发明新时间）：全部 ~65 文件（完整 ISO 串跨文件重复且整点零分零秒）——md 产物在伪时间戳行旁加 provenance 注记（`fabricated manual-era timestamp, true time unrecoverable`），json sidecar 保留原值；**全部登记进 lint(c) 豁免清单**（附组裁决理由）——lint(c) 对豁免登记文件跳过签名 check，验收对账以「全树签名命中文件数 == 豁免登记数」动态相等为准；清洗（快照剥离等）顺带移除签名行时同 commit 同步收缩豁免清单保持等式。F1166/F1168/F1174：marker 清除、truth-index 重生成、verdict 重试补账；**F1165 补账**：117 项回填 `chapter_states` `audit_reports`（resonance 55 + review-summary 55 逐路径补入对应章；ch56 7 文件补入 ch56 `audit_results`）——回填后 lint(d) 全树 0 命中，不豁免；F1162 的 ch56 缺 6 类维度审计**不在本 spec 补生成**（离线不可重算 LLM 审计，F947；记 deviation 出范围）
9. F1169：`.hypothesis/patches/`（在仓库根、git-ignored、Hypothesis 库自动再生缓存，非生产回归例）——处置改为确认 `git check-ignore` 覆盖 + 记 deviation 出范围，**不做 applied/voided 落账**（对每次测试运行再生的本地缓存落账不可持久复验）；F1170：2 个 0 字节 lockfile 删除
10. 孤儿自证类（lint 模式零命中但事实存活）：F1118 `DEBUG_USE_MANUAL_CREATE.md`（132 行 DEBUG 手册）移出生产树入 run 记录归档；F1117 `novel-output/validation-results/validation-report.md`（FAIL 集如实滞留，在 xinghuo 树外——lint 范围按 novel-output 全树而非仅 xinghuo）文件头加 provenance 注记（historical manual-run record）；F1119 三树结构漂移——novel-output/ 加 README 声明三树用途与漂移裁决（xinghuo=生产、test-validation=测试、validation-results=历史手动验证记录，不互为镜像）；F1167 `genre-config.json` `auditDimensions.texture: true` 与 audits 0 文件失配——**保持 true 不翻转**（G0.cc 一致性门禁将 texture 禁用列为 CRITICAL，E34 根因，需人工批准），失配作为已文档化已知态记入 novel-output/README（实施期改判，spec-deviations T7）；F1173 ch50 引用 helper 输出真伪不可裁决——ch49/51 provenance 注记时一并注记 ch50 引用行不可复核

## 验收标准（真实数据可复验）

1. 产物 lint 全树跑批：清洗前基线计数 N（以首跑 lint 输出为准，预期 52）留存于 run 记录，清洗后同一 lint 命令以退出码 0 + 0 命中通过（命中计数不含豁免清单条目；命令行与模式族以 lint 定义为准，前后对照可复验）
2. 派发层验证：命令行构造断言测试绿（zcode/codex 分支各 ≥1 例，断言 argv 含捕获模式、不含元叙述注入）+ 人工抽查（审查构造输出与既有捕获产物 fixture，不 spawn 子进程），结果记入 run 记录
3. 确定性层机器重算：ch49/ch51 的 calibration/分流/近3章均值重算值落盘，脚本与输入可从仓库复现（`skill_utils/calibration` + `pipeline/revision_router`，无 LLM 依赖）；ch51 trend 错值以重算值覆盖，旧值留档 run 记录；维度分保留原值 + provenance 注记（LLM 裁判分不可离线重算——review_resonance 三路模型已按 #33 T1b 删除，spec 2026-09-08 修订承认此边界）
4. F1169 处置复验：`git check-ignore .hypothesis/patches/<任一现存patch>` 命中（确认 git-ignored 出范围）；F1170 lockfile 删除后 `find novel-output -name "*.lockfile" -size 0` 0 输出；F1163 裁决对账机械复验：全树整点零分零秒完整串重复组命中文件数 == lint(c) 豁免清单登记数（初始 ~65/15 组，清洗收缩后同步），豁免外 lint(c) 签名 check 0 命中

## 风险与回滚

- **风险**：清洗 52 文件动生产树——分批 commit + 每批前后 lint 计数对照；正文与快照层清洗前打 git tag 便于整体回退
- **风险**：audit 聚合层改变审计报告结构，下游读者（G7、审计波读者技能）契约同步——登记进 C1 对账面
- **风险**：state 对账 lint 需容忍合法滞后（运行中产物），避免假阳性阻断 CI——lint 只跑 novel-output 静态树
- **回滚**：lint 带 flag 可关闭；清洗批次按 tag revert

## 簇成员清单（17 条，自查用 · 2026-09-08 复核状态）

F1108 存活, F1117 存活, F1118 存活, F1119 存活, F1162 降级存活（覆盖 35/56→55/56；手算 2 章仍存）, F1163 存活·扩面（三处→15 组 ~65 文件同伪整点签名族）, F1164 存活, F1165 存活, F1166 存活, F1167 存活, F1168 存活, F1169 降级（13 文件 17 例→4 patch 4 例）, F1170 存活, F1171 降级存活（109→52）, F1172 存活, F1173 存活, F1174 存活 —— 合计 14 全量存活 + 3 降级存活 = 17 条，0 驳回
