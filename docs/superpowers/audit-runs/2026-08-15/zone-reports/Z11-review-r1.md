# Z11 区第 1 轮复核报告（a+b 段合并，fresh context）

- **轮次**: 2026-08-15 轮 · review-r1
- **角度**: (a) 计数三方对账；(b) 内容级深核抽样（seed=20260815，每簇 ≥5 深读）；(c) 时间线一致性
- **复核对象**: zone-reports/Z11-a.md（F1101–F1119）+ zone-reports/Z11-b.md（F1151–F1161）共 30 条初审 finding
- **编号段**: 新增 F1162–F1170（9 条）
- **只读声明**: novel-output/ 等被审目录零创建/修改/删除；验证脚本仅写 /tmp/z11r1/（verify_a.py、verify_b.py）与复用初审遗留 /tmp/match_hypothesis_keys.py；未执行 pytest/shenbi-dispatch/pipeline/git 写操作；全部命令非交互（`</dev/null`）
- **复核方法**: 独立重算全部计数（三方对账：磁盘 vs state/manifest/index vs 文档/SKILL 声称）、decisions.json 全量 145 独立重分类、时间线 tz 归一化重排、67 文件污染扫描、深读 21 文件（chapters: ch1/2/9/20/30/40/48/55 的 META+正文；truth: current_state/book_spine/chapter_summaries/resonance_trend/audit_drift/pending_hooks；audits: ch22-anti-ai/ch48-pacing/ch24-resonance/ch49-resonance；plans: chapter-30-plan；snapshots: ch009/manifest）

---

## 总体结论

初审 30 条中 **27 条逐条复算通过（含 F1102 的 88/145 精确复现、F1158 的 0/10 digest 复跑）**，3 条存在事实性偏差需修正（F1112/F1118/F1107 证据计数），**无整条误报**。但复核发现一个初审完全遗漏的大类：**67 个生产产物（51 审计 + 16 decisions）内嵌 LLM 沙箱元叙述**（"只读沙箱无法写入，请手动复制"），证明写路径绕过（上轮 F1303 仅在 1 个 decisions 文件中实证）实为全域性模式；另发现 produced_at 时间戳系 LLM 编造（时序倒挂 10 处）、ch35 drafting-decisions 唯一缺失、上轮 4 条已 verified finding（F1311/F1312/F1314/F1316）在本轮台账中无承接。b 段"86/86 覆盖"实为清单相对覆盖——清单本身漏列 .hypothesis/ 下 1082 个磁盘文件。

---

## 一、漏报（新 finding F1162–F1170）

### F1162 | 67 个生产产物内嵌 LLM 沙箱元叙述："只读沙箱无法写入，请手动复制"污染 audits 全域 12 维度 | 漏报 | P1

- **证据**（实跑 `python3` 全树扫描，模式：`只读沙箱|read-only sandbox|无法(直接)?写入|can't write|手动(复制|写入|保存)`）:
  - 唯一命中文件 **67 个**：audits/ **51** 个（维度分布 pov×8、pacing×8、character×6、dialogue×6、world-rules×4、motivation×4、anti-ai×3、memo-compliance×3、continuity×3、sensitivity×2、resonance×2、foreshadowing×2；覆盖 35/56 章）+ decisions.json **16** 个
  - `novel-output/xinghuo-ranqiong/audits/chapter-15-pov.md:1`："审计分析已完成，但当前会话运行在只读沙箱中，无法将文件写入磁盘。以下为完整的审计报告内容——待沙箱权限放开后，可直接写入 `audits/chapter-15-pov.md`"
  - `audits/chapter-21-character.md:1`："The sandbox is read-only — I can't write files directly. The audit content is complete…"
  - `audits/chapter-49-motivation.md:127`："…请在可写环境中运行 `cat > audits/chapter-49-motivation.md` 并将上…"
  - `audits/chapter-24-resonance.md:1`："由于沙箱限制，我无法直接写文件，但所有证据均已收集完毕。"
- **加重证据（质量链完整性）**: `audits/chapter-49-resonance.md:5` 与 `audits/chapter-51-resonance.md:31` 明文承认"**确定性 helper 无法在只读沙箱中执行，校准门阈值、置信度降级、§5.4 分流均为手动计算**"——resonance 评分（≥65 阈值门控）有 2 章为 LLM 手算而非确定性 helper 输出。
- **根因**: 运行以只读沙箱 + 手动落盘模式执行（DEBUG_USE_MANUAL_CREATE.md 自证），LLM stdout 被原样保存进目标路径，无任何产物净化/元叙述检查。
- **验证**: `python3 /tmp/z11r1/verify_b.py` [D] 节 + 上述专项扫描（脚本留存 /tmp/z11r1/）
- **影响面**: 审计文件是 review-summary 聚合、drift-guidance、state-settling 的输入源；51/722 审计被污染 + 2 章 resonance 分数非确定性计算。上轮 F1303 仅实证 chapter-14-decisions.json 1 例，初审 a 段未扫描 audits 内容污染。
- **建议方向**: 产物落盘前元叙述过滤（模式库）或修订运行模式为可写沙箱；resonance 手算章的分数应标记不可信。

### F1163 | decisions.json `produced_at` 为 LLM 编造：三种时区格式混用、51/52 秒位=00、tz 归一化后 10 处章序倒挂、与机器时间戳直接矛盾 | 漏报 | P2

- **证据**（`python3` 逐文件提取 + `datetime.fromisoformat` 归一化）:
  - 时区格式统计：`Z`×37、`+0800`×11、`+08:00`×4——同一产物族 3 种写法（decisions-schema.md 仅要求 "ISO 8601 timestamp"）
  - 秒位分布：`00`×51 / `28`×1；分钟位 `00`×19、`30`×12——机器时间戳不可能呈现此分布（唯一例外 ch9 的 `09:01:28+0800`）
  - **10 处真倒挂**（tz 归一化后章序时间回退）：ch3(07-16T12:00Z)→ch4(06:30Z) 回退 330min；ch29(07-17T02:20Z)→ch31(00:00+08) 回退 620min；ch46(14:26Z)→ch47(07:30Z) 回退 416min；ch44→ch45 回退 90min 等（全表见 /tmp/z11r1/ 运行记录）
  - **与机器时间戳矛盾**: ch5 drafting decisions `produced_at=2026-07-16T06:50:00Z`，而 ch5 快照文件名（机器生成）`chapter-005-20260715T232231.md`——管线顺序为 drafting→审计→快照，决策时间不可能晚于快照时间近 8 小时（无论快照戳按 UTC 还是 +08 解释均矛盾）
- **根因**: produced_at 由 LLM 凭"感觉"生成圆整时间，无 dispatcher 注入；schema 校验不查时区一致性
- **验证**: `python3 /tmp/z11r1/verify_a.py` [B] 节 + 归一化专项脚本
- **影响面**: 下游按 produced_at 排序/新鲜度判断全部失真；F1102 的 schema 合规扫描未覆盖时间戳语义维度
- **建议方向**: dispatcher 落盘时覆盖 produced_at 为墙钟；G4-decisions 增查时区格式统一

### F1164 | ch35 drafting-decisions 唯一缺失：56 章中唯一无 drafting sidecar 的章，超时-升级-重试循环后未再生 | 漏报 | P2

- **证据**: `ls novel-output/xinghuo-ranqiong/chapters/chapter-35*` → 仅 `chapter-35.md` + `chapter-35-revision-decisions.json`，**无 `chapter-35-decisions.json`**；其余 55 章全部齐备（`python3` glob 计数 drafting=55/revision=34）。state `chapter_states['35'].steps_done` 含 `shenbi-chapter-drafting` 且 `status=complete`。`DEBUG_USE_MANUAL_CREATE.md:124`："Chapter 35 超时: state-settling 超过 900s → escalation checkpoint → 重试成功"；`pipeline-state.json checkpoint_history[1]`：ch35 escalation approve 2026-07-16T22:11。
- **根因**: 超时重试路径只恢复 state 步骤标记，不回补丢失的 sidecar 产物
- **验证**: `python3 -c "..."`（chapters glob + state 读取，见 /tmp/z11r1/verify_a.py 输出后追加）
- **影响面**: AGENTS.md decisions-sidecar 契约在 1/56 章静默断链；ch35 的下游 decisions 消费者无料可读
- **建议方向**: 重试成功路径校验本步骤全部契约产物存在；G4-decisions 修复后按章断言

### F1165 | state audit_reports 与磁盘 117 项脱节（resonance+review-summary 全 55 章不入账 + ch56 全部 7 项）——上轮 F1311 verified 本轮无承接 | 漏报 | P2

- **证据**（独立集合差）: 磁盘 722 审计维度对 vs state `audit_reports` 并集 605 → **117 项在盘不入账**：resonance×55、review-summary×55、ch56 的 anti-ai/character/continuity/foreshadowing/memo-compliance/pacing/pov×7；ch56 `audit_reports=None`；反向（账有盘无）0 项
- **根因**: 上轮 F1311（verified）：parallel wave 只记 core+genre 任务 output_path，resonance/review-summary 走独立路径
- **验证**: `python3 /tmp/z11r1/verify_a.py` [A6] 节
- **影响面**: 状态审计链（F338/F339 家族）对两个最关键的聚合产物（共鸣审计、汇总审计）系统性失明；本轮 a 段 F1114 只记 ch56 缺 5 审计，未提全量 117 脱节
- **建议方向**: audit_reports 语义补全或显式声明"仅 wave 内审计"

### F1166 | 污染 gate-marker 仍在场：`G4-review-resonance-generative.json`（2026-07-19 验证运行写入）——上轮 F1312 verified 本轮无承接 | 漏报 | P2

- **证据**: `novel-output/xinghuo-ranqiong/gate-markers/G4-review-resonance-generative.json` 时间戳 `2026-07-19T15:01:49.885588+00:00`、`gate=G4-generic-gen`、files=`audits/chapter-1-resonance.md`；对照正牌 `G4-shenbi-review-resonance-generative.json`（07-17T12:58:51、gate=G4-review-resonance、files=chapter-55）。22 个 marker 中此 1 个系 07-19 validation 运行以 xinghuo 为替身目录写入（validation-report:4,34 佐证）
- **根因**: 上轮 F1312（F513 根错位家族）：验证运行把 marker 写进生产项目 gate-markers/
- **验证**: `python3` 读 22 marker 全量时间戳（本轮实跑）
- **影响面**: 22 个 marker 中混入非本运行产物，任何按 marker 重建运行时间线/审计链的尝试被污染；本轮 F1111 讨论了 marker 覆写但未提污染 marker
- **建议方向**: 清理该 marker；验证运行强制独立输出目录

### F1167 | genre-config `texture=true` 而磁盘 0 个 texture 审计文件——上轮 F1314 verified 本轮无承接 | 漏报 | P2

- **证据**: `novel-output/xinghuo-ranqiong/genre-config.json` `auditDimensions: {... "texture": true}`；`ls audits/ | grep -c texture` → **0**；`config-change-log.jsonl` 单条记录 "Re-enabled texture audit… Disabled state let 26 chapters of system-term density explosion go undetected"（old=true/new=true 无操作条目，时间戳 07-19 晚于运行结束——上轮 F1316 证据同时复现且本轮亦未承接）
- **根因**: 上轮 F1314：运行期 texture 未生效（cascade-skip 或配置未接线），配置与产物脱节
- **验证**: 本轮实跑（上述三条命令输出）
- **影响面**: 变更日志自证"26 章系统词密度爆炸未被检测"——与本次叙事抽读独立互证（ch27+ 参数化风格爆发，ch31-39 开篇句完全相同，见 §三）
- **建议方向**: texture 配置与产物对齐；config-change-log 等值变更过滤

### F1168 | xinghuo truth-index.json 停留 genesis 态：仅索引 林烽/relationships/7 hooks/10 rules，实际主角团 冷/光/安静/白气 全部缺席 | 漏报 | P2

- **证据**: `novel-output/xinghuo-ranqiong/truth-index.json` 全文：`characters` 仅 2 条（`relationships`、`林烽`→protagonist.md）；而 `truth/current_state.md`「参数当前位置」表的前排参数为 冷/光/安静（白气/门框/深度 等 10+ 参数），56 章中后 36 章正文 林烽 出现≤1 次或 0 次（本轮叙事扫描）。索引重建函数 `_maybe_rebuild_truth_index`（chapter_loop.py:836）经 `git log -S` 确认 **dd1fc62 / 2026-07-20 加入，晚于运行窗口**——本运行产物是"修复前死接线期"实证（与 F1115 token-ledger 同类）
- **根因**: 运行期无章节后索引重建；genesis 态索引从未更新
- **验证**: `python3 -c "json.load(truth-index.json)"` + `git log -S "_maybe_rebuild_truth_index"`
- **影响面**: 任何基于 truth-index 的检索（Route A）对本书实际叙事实体 0 命中——context 组装质量受损的直接机制证据
- **建议方向**: 与 F1115 同批：修复后重跑最小 pipeline 验收索引随章演化

### F1169 | .hypothesis/patches/（13 文件、17 个 `via('discovered failure')` 显式回归例）从未套用：tests/ 内 0 命中，确定性回归层随 F1158/F1159 一同归零 | 漏报 | P2

- **证据**: `grep -rn "via('discovered failure')" .hypothesis/patches/*.patch | 计 17 处`；`grep -rn "discovered failure" tests/` → **0 命中**；patch 目标文件 `tests/property/gates/test_capability_fs_properties.py`（8 补丁）、`tests/property/stats/test_percentile_properties.py`（2）、`tests/property/cjk/test_tokenize_frozen.py`（2）、`test_entropy_properties.py`（1）。抽验 percentile 根因修复确实在位（compute_stats.py:100-107 `P50: values[n//2]` 与 median 同源，docstring 自述"旧 bug"），但发现期失败例未按 hypothesis 建议固化为 `@example()`
- **根因**: hypothesis 的显式例补丁需人工套用，无流程检查；patch 文件本身被根 .gitignore 压制不入库（同 F1159 机制）
- **验证**: 本轮实跑上述 grep；根因抽验 `sed -n '80,130p' src/shenbi/skill_utils/style_learning/compute_stats.py` + 读 test_percentile_properties.py
- **影响面**: F1158（样本全 stale）+F1159（样本不入库）+ 本条（补丁未套用）三者叠加，2026-06-30 发现的全部 17 个失败反例在当前测试套件中无任何确定性重放路径；仅靠随机 @given 可能再次覆盖
- **建议方向**: 把 17 个显式例人工合入对应测试文件（一次性小 PR）；hypothesis 升级或 CI 检查 patches/ 非空即套用提醒

### F1170 | 顶层残留 0 字节 `pipeline-state.json.lockfile`（mtime=07-20 拷贝入库时间）| 漏报 | M

- **证据**: `ls -la novel-output/xinghuo-ranqiong/pipeline-state.json.lockfile` → `-rwxr-xr-x 1 … 0 Jul 20 10:29`；运行结束后锁文件未清理，作为历史产物入库
- **验证**: 本轮实跑 ls
- **建议方向**: 无需处置（历史产物只读）；框架侧 atexit/中断路径补锁清理并在 manifest 校验中排除

---

## 二、误报/事实修正（逐条复读初审 30 条）

**结论：无整条误报。3 条证据级修正如下；其余 27 条（F1101–F1106、F1108–F1117、F1119、F1151–F1161）全部独立复算通过。**

### F1112 | 修正：context 文件为 ch1, ch3–12, 55, 56——**ch2 缺失**，初审"ch1–12, 55, 56"表述错误 | 事实修正（finding 本体成立）

- 反证命令: `ls novel-output/xinghuo-ranqiong/context/ | grep 'chapter-.*-context\.md'` → 13 文件，章集 `{1,3,4,5,6,7,8,9,10,11,12,55,56}`；`ls context/ | grep 'chapter-2'` → 空（rc=1）
- 即缺 context 的完成章为 **44 章**（ch2 + ch13–54），非 41 章。DEBUG 文档:86 自身记录"13个"与之相符。F1112 的主体断言（state 声称 composing 完成但大量章无 context 产物）与 medium 置信度维持不变。

### F1118 | 修正：retry_feedback 54 条记录**在场且与 DEBUG 文档精确一致**——"重试史被压缩丢失或文档失实，二者必居其一"为伪二分 | 事实修正（finding 主体成立）

- 反证命令: `python3 -c "import json; rf=json.load(open('novel-output/xinghuo-ranqiong/pipeline-state.json'))['chapter_loop']['retry_feedback']; print(len(rf))"` → **54**（DEBUG:记录 54 条 精确吻合）；按技能分布：review-resonance×35、chapter-drafting×14、chapter-planning×4、state-settling×1，覆盖 42 章
- 即重试史并未丢失、文档亦不失实；丢失的只是每章 `audit_retry_count` 计数字段（F1103 死字段问题的既知表现）。F1118 中叙事脱轨部分经本轮加强：林烽（genesis 主角）在正文中 ch19 后骤降、ch34 起 0 出现；ch22–26 五章开篇句逐字相同（"醒来时手指在内袋表面停住。"）、ch33–35 开篇同为"醒来时冷在面部。"——公式化复现强度高于初审描述，与 F1167 的 texture 失检互证。P2 维持。

### F1107 | 修正：证据计数 "128/722 审计文件含 BLOCKING" 不可复现 | 事实修正（finding 本体成立且经语义复读加强）

- 复算: `grep -rl "BLOCKING" audits/ | wc -l` → **165**（含 55 份 review-summary 自身）；剔除 review-summary → **110** 文件；`chapter-22-anti-ai.md` 单文件 12 处。初审 "128" 无法用任何自然口径复现（疑为某次中间过滤的产物）
- 本体验证: 55/55 份 summary 均 `**BLOCKING Issues**: 0`（正则含 bold 复算）；直接深读 `audits/chapter-48-pacing.md:22,51,57`（"BLOCKING — 远超maxChaptersPerCycle(15)"、"判定: BLOCKING（累积周期）"）与 `chapter-22-anti-ai.md:4-5`（"结果: 不通过（BLOCKING）"）——汇总抑制的断言成立且证据更强（48 章 pacing 连续 4 章引用链 Ch44→Ch48）。P1 维持。

### 其余 27 条复核清单（要点）

| Finding | 复核结果 | 独立证据 |
|---|---|---|
| F1101 | ✓ 精确复现 | ch2=1035B/ch9=642B/ch12=1506B/ch44=1229B/ch55=104B；ch55 非空白 89 字符；ch9 快照 `## Chapter 9` 段=毁损正文逐字（快照自证失能，与 F1109 互证） |
| F1102 | ✓ 精确复现 | 独立重分类：extra_data 67 + expecting_value 5 + expecting_comma 9 + control_char 2 = 83 解析失败 + 5 必填键缺失 = **88/145**；fully-valid 57/145。新增枚举违规明细（basis 非枚举 ~60 处、handling 非枚举 ~90 处、severity 非枚举 22 处、rationale>100 字 84 处）——均落入 F1102 伞内，不另立 |
| F1103 | ✓ | revision_count {0:56}、resonance null 56/56、audit_retry_count {0:56}；磁盘 34 revision-decisions |
| F1104 | ✓ | `第N章` 全集 = {55,56} |
| F1105 | ✓ | resonance_trend 单行 ch55；audit_drift 仅 Ch55（全文复读） |
| F1106 | ✓ | 磁盘 13 truth 文件 vs truth-files.yaml 概念集，仅 `truth/state_snapshot-pre-rev.md` 不在词表 |
| F1108 | ✓ | audits=6.2MB vs chapters(.md)=1.33MB = 4.66x；snapshots=12.9MB |
| F1109 | ✓ | ch009 快照首段=chapter-9.md 毁损文本；manifest 51 条与 51 文件精确一致（本章新增确认：manifest↔磁盘零缺口，快照时间戳随章单调） |
| F1110 | ✓ 精确复现 | staging plan-decisions 55 个、解析失败 **38**（初审数字精确）；pending_hooks 4171B vs 9886B |
| F1111 | ✓ | drafting marker files=[chapter-56.md]、`G4.dec SKIP no files`；revision marker checks=[] status=PASS（marker JSON 原文复读） |
| F1113 | ✓ | progress.json 171B 全文复读 |
| F1114 | ✓ | closure=pending/closure_step=0；last_snapshot={}；checkpoint_history 2 条；ch56 step_index=9 |
| F1115 | ✓ | `find -name "token-ledger*"` → NONE |
| F1116 | ✓ | trace 4 行键集无 finish_reason；三行 GATE_FAIL 时间间隔 0.67/0.66s（精确复算）；write-audit violations 逐字相同 |
| F1117 | ✓ | validation-report:12 BLOCKED、:34 substitute、:65 manifest NOT FOUND、:76 G0.16 HIGH |
| F1119 | ✓ | xinghuo 无 trace/write-audit（grep 0）；test-validation truth-index 空壳；genesis-context 6 vs 9 文件 |
| F1151/F1152 | ✓ | 根 truth/ 2 文件；yaml 无 bridge_tracker（grep 0）而 index.json 有；消费者/来源链与初审一致 |
| F1153–F1155 | ✓ | spec-deviations/audit-T5/T8 对应行复读 |
| F1156 | ✓ | executor_config.toml:31-32 deferred 注释在；INDEX.md 无温度条目 |
| F1157 | ✓ | progress.md:54-62 8 个未勾选 Phase 复读 |
| F1158 | ✓ 复跑 | `/tmp/match_hypothesis_keys.py` 重跑 → `matched: 0/10`、58 个 @given 函数 |
| F1159 | ✓ | `git check-ignore -v` → .gitignore:80 `.hypothesis/` 压制 |
| F1160 | ✓ | .benchmarks 单文件单条目 |
| F1161 | ✓ | console log accounts.google.com 1 命中 |

---

## 三、覆盖空洞

1. **b 段清单缺口（1082 文件未列入）**: `zones/Z11-b.files` 的 .hypothesis 条目仅 45 个（.gitignore、.gitkeep、43 样本）。磁盘实况：`.hypothesis/constants/` **1067 文件**（mtime 跨 2026-06-16 → 2026-08-15，hypothesis 6.155.2 运行缓存，按模块内容哈希组织）、`.hypothesis/patches/` **13 文件**（上轮审计明确引用过）、`.hypothesis/unicode_data/` 2 文件、`.playwright-mcp/page-*.yml` 1 文件均不在清单。"86/86（100%）"是清单相对覆盖；任务简报声称的 ".hypothesis/ 全部" 未达成。其中 patches/ 直接产出 F1169。
2. **审计窗口内区内容被写入**: `.hypothesis/constants/` 有 **28 个文件 mtime=2026-08-15**（08:47–13:34，最早晚于本轮初审产物时间）——本机在审计窗口内执行过 hypothesis 测试（constants 为测试执行期写入）。examples/ 未新增（仍 43 样本、mtime 6-30/7-1），不影响 F1158 结论，但"运行时产物区在被审计期间被同仓测试活动改写"应记入审计环境完整性备注（非本复核 agent 所为，本 agent 未运行 pytest）。
3. **上轮 verified findings 的台账承接断链**: 2026-08-14 轮 Z11 域 F1311（117 audit_reports 脱节）、F1312（污染 marker）、F1314（texture 配置脱节）、F1316（config-change-log 无操作条目）、F1301/F1302（章节头/META 契约）在本轮 a 段报告与 F11xx 台账中均无承接条目；其中 4 项本轮实证仍在场（F1165–F1167 及 config-change-log 单条无操作复读）。若台账策略是"上轮 open 项不重复编号"，应在 ledger 中显式标注映射，否则跨轮汇总会低估 Z11 缺口。
4. **context/review-checklist-N.json（56 文件）内容未深审**: 初审按计数处理（56/56 ✓），本轮抽读 1 份（ch30，结构完好含 ai_blacklist 14 词）；未逐份校验 checklist 与 genre-config 一致性——低风险，记为残留空白。
5. **ch35 升级路径的中间产物**（escalation 相关 staging/日志）在初审与上轮均未定位（retry_feedback 有 54 条但 escalation 专属记录仅 checkpoint 1 行）——升级流程的可审计性本身薄弱，已由 F1164 部分覆盖。

---

## 四、严重度异议表

| Finding | 初审判定 | 异议 | 理由 |
|---|---|---|---|
| F1104 | P0 | 建议复核方考虑 P1 | "数据损坏/丢失（不可恢复）"要件不满足——53 章摘要属**从未生成**而非已生成后丢失（丢失的是生成机会，正文仍在）；上轮同证据簇 F1310 判 P1、同根因姊妹项 F1105 判 P2，F1104 的 P0 与同簇定级不一致。P0 的另一要件"静默错误结果"也弱：下游 context-composing 拿到的是空选择集而非错误结果。**注：按铁则本复核不单方降级，仅提异议**；若维持 P0，建议同步说明 F1105 为何不同级 |
| F1115 | P1 | 无异议（维持） | 运行早于修复属既知，但该产物是 cost-ledger spec 的验收基线，P1 合理 |
| F1102/F1101 | P0 | 无异议（维持） | 88/145 与 5 章毁损均精确复现，定级依据充分 |
| F1159 | P1 | 无异议（维持） | 双重死亡 + 0/10 复跑成立 |
| F1108 | P1 | 无异议 | 4.66x 复算成立（初审 4.64x 因分母含 89 个 decisions.json 微差，不影响结论） |

---

## 五、收敛判定意见

- **收敛**: 30 条初审经 fresh-context 独立复算，**0 整条误报、3 条证据级修正**，核心数字（88/145、2/56、38/55、55/55、0/10）全部精确复现——初审质量高，证据链可靠。
- **不收敛点（需下一轮或台账动作）**: ① F1162（67 文件沙箱元叙述污染）为全域性新类别，初审对其零覆盖，建议下一轮针对 audits 内容净化做专项；② b 段清单补录 .hypothesis/constants|patches|unicode_data 与 page yml 后重扫（F1169 已提前覆盖 patches 实质风险）；③ 上轮 4+ 条 verified finding 的跨轮承接映射需在 findings-ledger 显式登记；④ F1104 定级异议待裁决。
- **下一轮建议减抽样**: chapters/decisions 的机械对账已两轮稳定，可转为只跑脚本；深读预算转向 audits/ 内容净化、truth-index 随章演化验收（修复后）、以及 escalation 路径可审计性。

## 复核统计

- 新增：**9 条**（P1×1：F1162；P2×7：F1163–F1169；M×1：F1170）
- 误报：**0 条整条误报**；事实修正 3 条（F1112、F1118、F1107）
- 覆盖空洞：5 项（含 1082 文件清单缺口）
- 严重度异议：1 条（F1104 P0→建议复议 P1）
