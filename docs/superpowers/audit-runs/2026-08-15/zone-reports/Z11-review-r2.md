# Z11 区第 2 轮复核报告（运行时产物，fresh context）

- **轮次**: 2026-08-15 轮 · review-r2
- **复核对象**: r1 收敛判定遗留的三项专项动作（F1162 元叙述污染权威复扫 / b 段 1082 文件清单缺口处置 / 上轮 verified findings 跨轮承接断链核查）
- **编号段**: 新增 F1171–F1177（7 条：P1×1 · P2×5 · M×1）；另有 r1 报告级事实修正 2 处（F1162 计数、1082 off-by-one）
- **只读声明**: novel-output/ 等被审目录零创建/修改/删除；全部脚本只写 /tmp/z11r2/（scan_meta.py、scan_meta2.py、recon_r1.py、delta_check.py、final_scan.py、gap_files.py）；未执行 pytest/shenbi-dispatch/pipeline/git 写操作；全部命令非交互（`</dev/null`）
- **方法**: 中英文完整模式库（33 个变体）全树精确扫描 + 逐文件命中行人工裁决（11 个仅弱模式命中文件逐条读行排除 FP）；抽样 5 污染文件深读消费链；ch49/ch51 手算算术独立复算；22 条上轮 verified 逐条对当前磁盘机械复验

---

## 专项 a：F1162 元叙述污染权威复扫

### a.1 权威计数（完整模式库全树扫描）

模式库（33 变体，比 r1 的 6 变体宽）：`只读沙箱|沙箱限制|沙箱权限|沙箱环境|待沙箱|沙箱为只读|沙盒…只读|read-only…沙箱|无法…写入|不能写入|无法保存|无法落盘|未能写入|无法写文件|无法创建文件|无法直接写|只读权限|只读模式|手动复制/写入/保存/落盘/创建|请手动|权限放开|可写环境|请将…写入|请将…保存|需人工写入|手动计算|写入磁盘|写入硬盘|保存至|read-only sandbox|sandbox is read-only|read-only mode|can't/cannot/unable to write/save/create|manually copy|by hand|write to disk|write files directly|write access|no write permissions|filesystem is read-only|writing to the filesystem is blocked`。

**权威总数：109 个文件**（novel-output/ 全树，truth/ 与 test-validation/、validation-results/ 均 0 命中）。

| 层 | 文件数 | 说明 |
|---|---|---|
| audits/ | **55** | 12 维度全覆盖：dialogue×9、pov×8、pacing×7、motivation×6、character×5、memo-compliance×4、continuity×4、anti-ai×3、world-rules×3、resonance×3、sensitivity×2、foreshadowing×1；覆盖 **37/56 章** |
| snapshots/ | **37** | 二次嵌埋（快照=章节+审计拼接设计，F1109）：同一元叙述文本在仓库存两份；含 4 个 audits 层未命中的章（ch5/25/46/48——污染源为 state-settling 输出而非 audits） |
| staging/plans/ | **9** | plan-decisions.json（F1110 的 38 个不可解析暂存件的直接病灶） |
| chapters/*.json（decisions） | **7** | ch9/14/16/31/33-revision/40/42——F1102 "concatenated_extra_data=67" 的组成部分 |
| chapters/chapter-N.md（正文） | **1** | **chapter-35.md:338**（38,650B 完整正文章，`<!--META-END-->` 之后尾随「因运行环境为 read-only 沙箱，文件未实际写入磁盘——需由管道层提取上述内容并写入对应路径」）——**正文交付物本身被污染**，此前未被任何轮次发现 |
| truth/ | 0 | 正面结论：truth 文件本体干净（或已被管线干净落地） |

与 r1/协调者数字对账：r1 报 67（51 audits+16 decisions）——用 r1 原模式复跑得 **68**（38 audits+4 chapters+24 snapshots+2 staging），**r1 的分层（51+16、0 快照）不可复现**（"16 decisions" 实为 7 个 chapters decisions + 9 个 staging plan-decisions 的合并误标）；协调者窄模式 44+ 与本扫描 audits=55 相容。**109 为完整模式库下的权威计数**（差异全部来自模式库宽度，非事实分歧）。

### a.2 抽样 5 文件深读——下游消费链影响

| 样本 | 污染位置 | 进入的消费链 | 影响 |
|---|---|---|---|
| `audits/chapter-51-resonance.md` | L31（§5.4 分流自认手算） | drift-guidance 链（audit_drift/resonance_trend 的声明写入者） | 自称"追加至 resonance_trend/audit_drift"但 truth 侧仅 ch55 有记录——**污染输入+传播断裂双重失效**；trend 均值算术错误（见 a.3） |
| `audits/chapter-15-pov.md` | L1-3 头部 + L150 尾部 | review-summary 聚合链（ch15-review-summary 存在且报 11 reviews/0 BLOCKING；state 605 账本含此文件） | 污染文本被聚合 LLM 原样摄入；计数/判定未受影响（内容级污染） |
| `chapters/chapter-9-decisions.json` | L107（合法 JSON 结束后追加英文元叙述） | decisions 消费链（下游技能按 `reads:` 消费） | 即 F1102 concatenated_extra_data 的病灶本体：JSON 不可解析 → 下游静默失败 |
| `staging/plans/chapter-40-plan-decisions.json` | L227（"Pipeline Note: The sandbox is read-only…"） | staging 晋升链 | 从未晋升（F1110），死滞留；与 F1164（ch35 唯一缺失 drafting-decisions）同属重试路径病灶 |
| `snapshots/chapter-005-…md` | L2161/2188/2305/2332/2359/2541（**6 次**重复） | state-settling 捕获链 | "All 8 files … output above with `### FILE:` markers … To persist these to the staging directory, copy each `### FILE:` block"——8 个 truth 文件以手动捕获模式输出且重试 6 次；声称 "chapter_summaries.md — Full Ch5 summary appended" 而 truth/chapter_summaries.md 仅含 ch55/56（F1104 机制实证，见 F1175） |

### a.3 ch49/ch51 resonance 手算分数对 floor 门控与 trend 的影响

- **floor 门控（≥65）结果稳健**：ch49 overall 79（21+20+22+16，和独立复算正确）、ch51 overall 70（16+18+20+16，正确）；两章均为 推进/转折 角色（阈值 ≥65、无维度子地板），裕量 +14/+5，即便分数有 ±5 手算误差也不会翻转放行判定。
- **但 ch51 的边界断言为假**：§5.4 写 "超出阈值 >5"——实际 70−65=**5**，恰在 SKILL §5.4 的 ±5 边界带内（判定"明确通过"本身成立，因其本为通过章，但作为 gate 论证的理由是算错的）。
- **ch51 trend 均值 3/5 行不可复现**：以其自报分数表（ch48/49/50/51）复算——场景临场感 claimed 13.7（prior3=16.00 / with-current=15.67 均不符）、文笔质感 claimed 16.3（18.67/18.33 均不符）、读者回报 claimed 15.3（仅与 prior3 吻合）；情感落地 17.0 与 overall 66.7 仅与 with-current 吻合。**五行三窗口两错值**——手算错误的直接实证。且 ch49 用"近2章"、ch51 用"近3章（含当前章）"，方法学窗口也不一致。
- **传播被（意外地）阻断**：resonance_trend.md 仅 ch55 一行、state resonance_score 56/56 null（F1103/F1105），review-summary 不传播 resonance 分数（ch49/ch51 summary 无 resonance 字样）——**错误数字止步于审计文件本体**，未进入 truth 聚合。若 appends 曾落地，drift-guidance 将消费错误均值。
- 附：ch49 review-summary 报 "Reviews executed: 11" 而磁盘 12 份单项审计——resonance 对汇总器不可见，与 F1165/F1311 的两路记账盲区互证。

---

## 专项 b：b 段清单缺口（1082→实际 1083 文件）机械核验与处置表

实跑（`/tmp/z11r2/gap_files.py`）：Z11-b.files 列出 86，b 段根（.hypothesis/.benchmarks/.playwright-mcp/truth/.superpowers）磁盘 1169，**缺口 1083**（r1 写 1082 系自身算术 off-by-one：1067+13+2+1=1083）。

| 类别 | 文件数 | 处置判定 | 依据 |
|---|---|---|---|
| `.hypothesis/constants/` | **1067** | **cache-ignored** | hypothesis 6.155.2 按模块内容哈希组织的本地执行缓存；gitignored（根 .gitignore:80）；随任意测试运行再生。mtime 跨 2026-06-16 → 2026-08-15（无 GC，同 F1158 stale-key 疾病但无害） |
| `.hypothesis/patches/` | **13** | **needs-review → 已审（F1169）** | 本轮复验 `via('discovered failure')` 仍 17 处、mtime 全部 2026-06-30 未变——r1 F1169 结论原样有效，无新增 |
| `.hypothesis/unicode_data/` | 2 | **generated-excluded** | hypothesis 内置 unicode 14.0.0 charmap/codec 数据，工具自管 |
| `.playwright-mcp/page-*.yml` | 1 | **generated-excluded** | 2026-07-04 浏览器会话的页面 a11y 树快照（与 F1161 console log 同会话），gitignored 会话产物 |

**审计环境完整性备注（非本 agent 所为，本 agent 未运行 pytest）**：constants/ 有 **28 个文件 mtime=2026-08-15**（审计窗口内本机测试活动写入；.hypothesis/ 父目录 mtime 已滚动至 08-16 00:00 本地）。examples/ 未新增（仍 43 样本）——不影响 F1158 结论。
**coverage-ledger 修正输入**：b 段"86/86（100%）"应改为"清单相对覆盖 86/86，绝对覆盖 86/1169（7.4%），缺口 1083 全部裁决为 cache-ignored/generated-excluded/已审（F1169），无新增需审项"。

---

## 专项 c：上轮（2026-08-14）verified findings 跨轮承接核查

上轮 Z11 域 verified 共 22 条（F1300–F1318、F1320–F1322，无 F1319）。逐条对当前磁盘 + 本轮（a/b/r1/r2）产物：

| 上轮 ID | 内容（严重度） | 当前磁盘状态（本轮实证） | 本轮承接 |
|---|---|---|---|
| F1300 | 5 章覆写（P0） | 复现（同 5 章） | ✅ F1101 |
| **F1301** | **56/56 章无 `# Chapter N:` 头（P1）** | **复现：56/56 首 15 行无该头**（本轮实跑） | ❌ **零承接**（a/b/r1 报告与台账均无） |
| **F1302** | **6 章无 META + ch40 `## META`（P1）** | **复现：5 章无 META（ch2/9/12/44/55，即 F1101 被毁章）+ ch40 `## META`**（ch22 已恢复 META-BEGIN，故 6→5） | ❌ **零承接** |
| F1303 | DEBUG 手动创建路径（P1） | 复现且升级为全域模式 | ✅ F1162（r1 显式挂接） |
| F1304 | 83/145 decisions 无效（P1） | **恶化：88/145**（r1 独立复算） | ✅ F1102 |
| F1305 | 57/145 schema 违反（P1） | 复现（F1102 伞内枚举违规明细） | ✅ F1102（伞内） |
| F1306 | revision-decisions 兜底违 schema（P2） | 复现（F1102 伞内） | ✅ 伞内（无独立拆分） |
| F1307 | 根 truth 三源分裂（P1） | 复现 | ✅ F1151/F1152 |
| F1308 | staging truth 不一致（P2） | 复现（4171B vs 9886B） | ✅ F1110 |
| F1309 | progress.json 空壳（P1） | 复现（171B） | ✅ F1113 |
| F1310 | closure=pending（P1） | 复现 | ✅ F1114 |
| F1311 | audit_reports 117 脱节（P2） | **精确复现：本轮独立重算 state 605 vs 磁盘 722，盘有账无 117（resonance×55+review-summary×55+ch56×7），账有盘无 0** | ✅ F1165（r1） |
| F1312 | 污染 marker（P2） | 复现（07-19 marker 在场） | ✅ F1166（r1） |
| F1313 | token-ledger 缺席（P1） | 复现（全仓 0 个） | ✅ F1115 |
| F1314 | texture=true 0 文件（P2） | 复现（`ls audits \| grep -c texture`→0） | ✅ F1167（r1） |
| F1315 | ch56 审计 6/13 维缺失（P2） | 复现：磁盘 7 份（缺 dialogue/motivation/resonance/sensitivity/world-rules+review-summary） | ⚠️ 部分（F1114 记 5+summary，未按 13 维框架重述；F1165 记账侧） |
| F1316 | config-change-log 无操作条目（P2） | **复现：单条 `old=true/new=true`、ts=2026-07-19T05:48:59 晚于运行结束**（本轮实跑 cat） | ⚠️ 嵌入 F1167 证据段，无独立条目 |
| F1317 | blocked 写入仍落盘（P2） | 部分：GATE_FAIL 拦了 bridge_tracker（盘无），但 character_matrix.md 仍在 test-validation/truth/；escalation AUDIT_PASS `checked_files: []` 空洞放行 | ⚠️ 部分（F1116 记录了 GATE_FAIL 本身，未记残留/空洞放行） |
| F1318 | hypothesis committed 声明失效（M） | 复现+升级 | ✅ F1159（M→P1） |
| **F1320** | **DEBUG 计数漂移 1226 vs 实际（M）** | **复现：DEBUG 自称 1226 文件/52 快照，实际 1229 文件/52 目录项（51 快照+manifest）/22 marker** | ❌ **零承接** |
| F1321 | plan-decisions 滞留 staging 55 个（P2） | 复现+恶化（55 在场，38 不可解析） | ✅ F1110 |
| F1322 | state_snapshot-pre-rev 未登记（M） | 复现 | ✅ F1106 |

**断链结论**：完全断链 3 条（F1301/F1302 均为 **P1** 契约违反、F1320 为 M），部分承接无映射注记 3 条（F1315/F1316/F1317）。r1 发现的"F1311/F1312/F1314/F1316 未闭环"中前三者已由 r1 自身 F1165/F1166/F1167 补承接，F1316 仍仅嵌入他条证据段。→ 立新 finding **F1177**。

---

## 新 findings（F1171–F1177）

### F1171 | F1162 权威复扫：全树元叙述污染实为 109 文件（r1 报 67 且分层不可复现）——扩展至正文交付物（ch35）与快照二次嵌埋（37） | 漏报扩展+证据修正 | P1

- **证据**（`python3 /tmp/z11r2/final_scan.py`，33 变体模式库，输出留存 /tmp/z11r2/final_scan_out.txt）:
  - 权威计数 109 = audits 55 + snapshots 37 + staging/plans 9 + chapters decisions 7 + **chapters/chapter-35.md 1**；truth 0；维度分布 dialogue×9/pov×8/pacing×7/motivation×6/character×5/memo-compliance×4/continuity×4/anti-ai×3/world-rules×3/resonance×3/sensitivity×2/foreshadowing×1，覆盖 37/56 章
  - **正文污染**：`chapters/chapter-35.md:338`（38,650B 完整章）`<!--META-END-->` 后尾随 "以上为修订管线的完整产出。因运行环境为 read-only 沙箱，文件未实际写入磁盘——需由管道层提取上述内容并写入对应路径。"——ch36+ 的 context-composing/审计消费章全文时摄入该段
  - **快照二次嵌埋**：37 个快照因"章节+审计拼接"设计（F1109）内嵌同一批元叙述（如 `snapshots/chapter-005…:2161` "Since the sandbox is read-only, they are output above with `### FILE:` markers"），其中 ch5/25/46/48 四章的污染源是 state-settling 输出而非 audits（证明该模式不限于审计技能）
  - **r1 计数不可复现**：r1 原模式复跑得 68（38 audits+4 chapters+24 snapshots+2 staging），非 67；"51 audits+16 decisions、0 快照"的分层无任何口径可复现（16=7 chapters decisions+9 staging plan-decisions 的误合并）
- **根因**: 同 F1162（只读沙箱+手动落盘模式，stdout 原样入盘，无净化）；r1 低估源于模式库仅 6 变体（漏 沙盒/只读权限/只读模式/请将…写入/写入磁盘/保存至 等中文变体与 unable-to/write-access 等英文变体）
- **验证**: final_scan.py + delta_check.py（11 个仅弱模式命中文件逐行人工裁决，全部为真污染，含 `chapter-23-memo-compliance.md:97` "请将上述内容写入 audits/chapter-23-memo-compliance.md"）
- **影响面**: F1162 影响面修正——51/722 审计 → 55/722 审计 + 37/51 快照 + 9/55 暂存 plan-decisions + 7/89 chapters decisions.json + **1/56 正文章**；快照嵌埋使同一污染文本在仓库存两份（叠加 F1108 的 ~34% 冗余）
- **建议方向**: 同 F1162；另：模式库应固化进产物落盘前的净化检查（33 变体清单见本报告 a.1）；ch35 尾段属可机械剥离的尾随块

### F1172 | ch51 resonance 手算 trend 五行三窗口两错值 + §5.4 "超出阈值>5"断言为假（70−65=5 恰在边界带）——铁律3 违反的实际后果实证 | error | P2

- **证据**: `audits/chapter-51-resonance.md:74-78`（claimed 场景临场感 13.7/文笔质感 16.3/读者回报 15.3/情感落地 17.0/overall 66.7）vs 以其自报表（:52-55，ch48=22/19/21/15/77、ch49=21/20/22/16/79、ch50=14/9/13/15/51、ch51=16/18/20/16/70）复算：prior3=16.00/18.67/15.33/19.00/69.00，with-current=15.67/18.33/15.67/17.00/66.67——13.7 与 16.3 两个值任何窗口都算不出；`:37` "超出阈值 >5" 而 70−65=5
- **根因**: 确定性 helper 未执行（:31 自认），LLM 手算均值/边界
- **验证**: `python3` 独立复算（见 a.3 表）
- **影响面**: 错误数字止步于审计文件（resonance_trend 仅 ch55、review-summary 不传播 resonance、state null）——若 appends 落地，drift-guidance 将消费错误均值；ch49 的近2章 vs ch51 的近3章窗口不一致使 trend 语义本身漂移
- **建议方向**: 同 F1162（resonance 手算章分数标记不可信）；helper 强制化 + trend 行由 CLI 生成

### F1173 | 确定性 helper 可用性自相矛盾：ch49/51 自认手算 vs ch50 引用 helper JSON 输出——同一运行 3 章内三态（手算/有输出/重试），xinghuo 无 trace 无法裁决真伪 | error | P2

- **证据**: `audits/chapter-50-resonance.md`（§5.4 节）逐字引用 `$ python -m shenbi.skill_utils.calibration …→ {"reported":"low","calibrated":"low",…}` 与 `review_resonance …→ {"path":"human_review","overall":51,…,"near_threshold":false,…}` 两段 helper 输出；而 ch49:5 / ch51:31 明言 "确定性 helper 无法在只读沙箱中执行…均为手动计算"。ch50（07-17T09:58）介于 ch49（09:02 重试记录）/ch51（10:26）之间。xinghuo 无 trace.jsonl/write-audit（F1119）→ ch50 的 helper 输出无法证实真实执行（亦可能为 LLM 复述格式编造）；test-validation 侧 escalation-review 的 AUDIT_PASS `checked_files: []` 展示了空洞放行如何发生
- **根因**: 无计量链（F1115/F1116 家族）使 helper 执行不可溯源；或三章分属不同权限的会话
- **验证**: 三文件原文对照 + `python3 -c` 读 trace 键集（xinghuo 侧不存在）
- **影响面**: 全部 55 份 resonance 审计的确定性组件（阈值选择/置信度降级/分流）可信度均无法与磁盘证据区分真假
- **建议方向**: dispatcher 记录 helper 调用及其 stdout 摘要进 trace；修复后重跑验证

### F1174 | 35 章 resonance 首评 G4 verdict 不合格（no_valid_verdict）全部经重试才在场——盘上报告均为第二次尝试产物，而 state audit_retry_count 56/56=0 | error | P2

- **证据**: `pipeline-state.json chapter_loop.retry_feedback` 共 54 条，其中 `chN-shenbi-review-resonance` 35 条，must_fix 全部为 `G4.rr.verdict:chapter-N-resonance.md:no_valid_verdict`（如 ch49：2026-07-17T09:02:52 FAIL，checks 内 detail_table/evidence 均 PASS）；chapter_states 全 56 章 `audit_retry_count: 0`
- **根因**: verdict 行格式首评不合规（与元叙述头部挤占格式强相关——35 个重试章与污染章集合大面积重叠，因果未证但相关显著）；重试计数器死字段（F1103 家族）
- **验证**: `python3` 遍历 retry_feedback 计数 + must_fix 抽样
- **影响面**: 盘上 resonance 报告是"格式修正后的重写版"，首评原文已丢弃——评分 provenance 断一层；F1103 的死计数使该历史对 state 读者不可见
- **建议方向**: 重试时保留首评（如 .attempt1 后缀）；audit_retry_count 回写

### F1175 | state-settling 以 `### FILE:` 手动捕获模式输出 8 个 truth 文件且重试 6 次；"Ch5 summary appended" 声称 vs chapter_summaries 仅 ch55/56——F1104 根因修正：**已生成未落盘**（部分可自快照恢复） | error | P2

- **证据**: `snapshots/chapter-005-20260715T232231.md:2161,2188,2305,2332,2359,2541`（6 次重复块）"All 8 files for shenbi-state-settling (Chapter 5) have been produced. Since the sandbox is read-only, they are output above with `### FILE:` markers … To persist these to the staging directory, copy each `### FILE:` block to the corresponding path under `staging/truth/`"+ 逐文件摘要表（含 "chapter_summaries.md — Full Ch5 summary appended … ✅"）；而 `truth/chapter_summaries.md` 仅 `## 第55章/第56章`（F1104）。快照 L428-533 存有 ch5 的摘要级分析内容（信念/欲望/角色任务/对话量）——**恢复路径存在**（ch5-55 有快照；ch1-4 无）
- **根因**: LLM 以 stdout+手动捕获模式产出 truth 更新，捕获层未落盘（F1162/F1303 同根因）；非"技能未运行"
- **验证**: 快照原文 + truth 文件对照（本轮实跑）
- **影响面**: F1104（53 章摘要缺失）的根因叙述修正：内容已生成、传输丢失、快照内部分可恢复——**对 F1104 裁决注记**：'从未生成'的降级理由不完全成立（生成物在快照 stdout 内）；'部分可恢复'又弱化 P0 的不可恢复要件。维持裁决 P1，两要点均供终裁参考
- **建议方向**: 快照 ### FILE: 块离线提取回填 1-54 章摘要（一次性脚本，勿手改 truth 之外产物——回填属修复动作不在本审计内执行）

### F1176 | b 段清单缺口处置落账：1083（非 1082）文件全数裁决（1067 cache-ignored / 13 已审 F1169 / 3 generated-excluded），28 个 constants 在审计窗口内被本机测试活动写入 | coverage | M

- **证据**: `/tmp/z11r2/gap_files.py` 输出（listed=86, disk=1169, missing=1083；分类分布与 mtime 直方图见专项 b 表）；r1 的 1082 为 1067+13+2+1 的算术笔误
- **根因**: b 段清单生成时只递归到 examples/ 一层；hypothesis 运行缓存全量缺席
- **验证**: 脚本留存 /tmp/z11r2/；patches 复验 17 例未变
- **影响面**: coverage-ledger 的"86/86=100%"失真；处置表（专项 b）为修正输入
- **建议方向**: coverage-ledger 按专项 b 表落账；审计窗口内 constants 写入记入环境完整性备注

### F1177 | 上轮 verified 承接断链：F1301（P1 章节头 56/56 缺失）/F1302（P1 META 契约）/F1320（M DEBUG 计数漂移）三条本轮零承接且盘上复现；F1315/F1316/F1317 部分承接无映射注记 | process | P2

- **证据**: 台账 grep（`grep -n 'F1301\|F1302\|F1320\|F1315\|F1316\|F1317' 2026-08-15/findings-ledger.md` → 0 命中）；磁盘复现（本轮实跑）：56/56 章首 15 行无 `# Chapter N:` 头；5 章无 META（ch2/9/12/44/55）+ ch40 `## META`（ch22 较上轮恢复）；DEBUG 自称 1226/52 vs 实际 1229/22 marker/51 快照+manifest；config-change-log 单条 `old=true/new=true` ts=07-19T05:48:59；test-validation/truth/character_matrix.md 在 GATE_FAIL 后仍在盘而 bridge_tracker.md 不在
- **根因**: 跨轮台账无"上轮 ID→本轮 ID"映射机制；a 段 fresh-context 重扫时未携带上轮清单
- **验证**: 专项 c 全表（22/22 逐条）
- **影响面**: 两条 P1 级契约违反在当前轮汇总中不可见——跨轮汇总会低估 Z11 缺口（正是 r1 §三.3 预警的落地）
- **建议方向**: 台账为 F1301/F1302/F1320 补登记（可并入本条或另立）；建立 ledger 映射列；F1316 从 F1167 证据段提为独立注记

---

## r1 报告事实修正（报告级，非新 finding）

1. **F1162 计数**：67（51 audits+16 decisions）→ 权威 109（55+37+9+7+1），分层与总数均修正（详见 F1171）。finding 本体（P1、全域模式、resonance 手算）维持且加强。
2. **1082**：→ 1083（r1 自身分解式 1067+13+2+1 的加法笔误）。
3. **F1165 复确认**：本轮独立重算精确复现 605/722/117（resonance×55+review-summary×55+ch56×7，账有盘无 0）——r1 数字无误，无需修正（注：audit_reports 实际位于 `chapter_states[N].audit_results.audit_reports`，r1 未写明路径，本轮已核）。

---

## 收敛判定

- **收敛**: r1 的三专项遗留动作全部闭环——(a) 权威计数 109 文件 + 5 链深读 + 手算算术复算完成；(b) 1083 文件全数机械裁决，无新增需审项（patches 风险已由 F1169 覆盖且未变化）；(c) 22 条上轮 verified 逐条对盘，断链收敛为 3 完全 + 3 部分，全部有磁盘级证据。r1 的核心判定（F1162 存在性、resonance 手算、117 脱节）本轮独立复算全部成立。
- **不收敛点（需台账/终裁动作）**: ① F1162/F1171 计数修正应回写 ledger 描述行（"67 个…44+ 量级证实"→"109 个权威计数"）；② F1301/F1302/F1320 需补登记（F1177）；③ F1104 裁决收到 F1175 的双向新证据（已生成未落盘↔快照部分可恢复），维持 P1 但请终裁复核注记；④ F1173 的 helper 真伪问题依赖 trace 修复后重跑，本轮不可裁决。
- **下一轮建议**: Z11 机械对账已三轮稳定，可停止人工复扫；剩余开放动作全部是台账/登记类（半日内可完成）。若还有一轮，唯一值得再扫的是元叙述模式库对 **dist/site 等文档树**的误入库检查（本轮范围限 novel-output，未扫 docs 树）。

## 复核统计

- 新增：**7 条**（P1×1：F1171；P2×5：F1172–F1175、F1177；M×1：F1176）
- 事实修正：2 处（F1162 计数分层、1082→1083）
- 上轮承接核查：22/22 条全覆盖（✅13 · ⚠️部分 3 · ❌断链 3 · 升级承接 1[F1318→F1159]、伞内 2[F1305/F1306 归 F1102]）
- 只读合规：novel-output/ 零写入；脚本仅 /tmp/z11r2/；无 pytest/dispatch/pipeline/git 写
