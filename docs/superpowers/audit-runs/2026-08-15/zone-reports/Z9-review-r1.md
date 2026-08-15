# Z9 区独立复核报告（review-r1，fresh-context）

- 轮次: 2026-08-15 全项目深度审查
- 复核 agent: Z9-review（只读；除本文件外未创建/修改/删除任何仓库文件；未 git add/commit；未运行 pytest/dispatch/pipeline）
- 输入: zone-reports/Z9-a.md（F901-F919）、Z9-b.md（F934-F950）、Z9-c.md（F967-F975）
- 本轮角度: **引用断链重扫**——对 findings 涉及文档 + 抽样文档做全量出站引用（file:line、相对链接、命令、spec/plan 编号、F 编号）vs 目标存在性核验；初审按预登记抽样，本轮全引
- 编号段: F951-F957（实际使用 7 条）

## 0. 复核范围与机械核验结果

| 项 | 结果 | 验证方式 |
|---|---|---|
| 初审 findings 重证 | **43/43 成立，0 误报**（Z9-a 19 条 + Z9-b 17 条 + Z9-c 9 条，每条独立重跑证据命令） | 见 §1 各段 |
| mkdocs nav 全链 | **PASS**：16 行 nav（13 叶页面 + 3 节头）全部指向存在文件 | python 解析 mkdocs.yml nav 段逐条 exists() |
| AGENTS.md 命令清单 vs justfile/pyproject | **PASS**：`just check/test/gate/dispatch/pipeline-init/status/review/resume` 与 justfile recipe 逐项吻合；4 个 entry point（shenbi-validate/dispatch/score/phase）在 pyproject.toml:56-59 登记且 CLI 签名一致（G0/G2/G4 参数序、score 的 `--test-type`、phase 的 `--round-dir`、dispatch 的 `<skill> <test_type> <round_dir> [prompt]`） | `uv run <entry> --help`/误参 usage 输出 + gates/cli.py:69-135 逐参比对 |
| specs/INDEX ↔ 磁盘双向 diff | **PASS**：登记 23 = 磁盘 23，双向差集空，无重复编号 | python 双向集合 diff |
| plans/INDEX ↔ 磁盘双向 diff | **FAIL（复现 F967）**：:4 "已归档 66"、:23 "63 个已完成" vs 磁盘 68（06 月 30 + 07 月 33 + 08 月 5）；INDEX 对 archive/ 的 markdown 链接数为 0（无链接层断链，仅计数漂移）；另见漏报 F954（同行 3 项附加过期字段） | python 双向 diff + `ls plans/archive | cut -c1-7 | uniq -c` |
| Z9.files(400) ↔ 磁盘闭合 | **PASS**：差集仅为本轮（2026-08-15）自身产物，属设计排除；Z9-a 40 + Z9-b 127 + Z9-c 233 = 400 | python 对账 |

## 0.1 全引用断链重扫统计（本轮角度主产出）

| 批次 | 文档数 | 出站引用数 | 扫描器告警 | 人工裁决 |
|---|---|---|---|---|
| Z9-a findings 涉及 + 根级（targets_a，22 文件） | 22 | 102 | 10 | 8×truth/*（技能契约的项目内路径，非仓路径）+ 2×tests/build_registry.py（roadmap 明示"延期未建"）→ **0 真断链** |
| 抽样未涉及文档（targets_b，12 文件：framework 5 + adr 4 + getting-started 2 + roadmap） | 12 | 21 | 10 | 同上两类误报 → **0 真断链** |
| 活跃 spec 23 + prompt 2 + INDEX 2（targets_spec） | 27 | 236 | 24 | glob/占位符/brace 展开 18 误报；4 处人工深查（superpowers/archive/ 为 v6 变更注自纠、snapshot.py 为提案路径、token-efficiency-p2-spec 为 git 分支名、audit-runs/2026-08-13/ 见 F955）→ **0 新真断链 + 1 同族补充位** |
| plans/archive 全量 68 | 68 | 34 个 spec 引用 | — | 32 DRIFT（basename 全部命中 specs/archive/）+ 0 真死链（**精确复现 F968**） |
| F 编号闭合（27 文件 vs 2026-08-14 findings-ledger 679 ID） | 27 | 全部 F 引用 | 4 | F1303-F1305 为区间语法（个体存在）、F0xx 为占位符、F10 见 F956；**0 硬断链** |
| spec/plan 编号引用（活跃 spec 内 `#N`） | 23 | 仅 #6（snapshot-wiring:2） | — | 即 F936 已立案项，无其他不可解析编号 |
| **合计** | **129** | **≈393** | **44+34** | **新增真断链 1（F951）+ 同族补充 5 处（F952-F956）** |

抽样未涉及文档的实际构成为 framework 5（chapter-file-format/dispatcher/gates/scoring/logging）+ adr 4（0001-0004）+ getting-started 2（first-novel/installation）+ roadmap/api×2/REVIEW_EVIDENCE/adr-index（根级 9 份 *.md 全部被初审 findings 涉及，以同目录零 findings 文档替代）+ 活跃 spec #13（初审 medium 置信，本轮深读）。

## 1. 初审 findings 重证明细（分段）

### Z9-a 段（F901-F919）：19/19 成立
- F901 复现：`ls tests/dispatch-subagent.sh`→No such file；`git log --diff-filter=D`→0f68102。F902 **原样复现**：`just --dry-run pipeline-init outline-example.md ./my-novel --auto`→`error: justfile does not contain recipe '--auto'`（exit=1）。F903 复现：`grep -rn "_tool_hashes" src/`→仅 g0.py:80,128 注释 + schemas/deps.py:62 声明，零 gate 消费；G0.13=independence markers（g0.py:552-590）。F904：74 目录 vs 四处 69/67 声称。F905：`grep -c "review-group\|foreshadowing-lifecycle" docs/skills/index.md`→0；deps.json 侧 python 对账→未登记恰为该 5 技能。F906：t1-skill 目录 70。F907：`grep -o 'kind: ...' | sort -u | wc -l`→16。F908：VALID_SEVERITY 含 medium（decisions.py:12）、`requires = severity in ("medium","high") or manual_override`（:36）；文档 :67-68 仅列 low/high 且自身示例 :33 用 medium。F909：pyproject 六规则全 "none"、executionEnvironments 仅 tests。F910：ignore_errors=true 在 :91。F911：plugin-manifest 仅 ci.yml:69 注释；.codex-plugin/ 在 .gitignore:20。F912：security.yml 无 cron；nightly cron 注释态。F913：G7 最大编号 G7.16（数值排序）；TOOL_TAMPER 0 命中；_tool_hashes 残留 3 个已删文件键。F914-F918 逐条文本/命令证实。F919：goal-prompt:3/71 "20 万字" vs outline-example.md:7 100000。
- 附注（非异议）：F907 初审引 overview.md:141/166，本轮另见同文件 :152/:177 两处同句（"完整 15 类见/The full 15 categories"），属同 finding 的附加证据位；F914 行号为 :18（初审 :19，±1）。

### Z9-b 段（F934-F950）：17/17 成立
- F934 抽验 3 组全中：dispatch_skill( 三处带 state（chapter_loop.py:1274/2831/3003）、:2794 现为 `state.add_step_done`、output-side 常量行 :36。F935：直接读序证实 #16(⚪Low)→#25(🟡P2)→#26(🟠P1) 相邻逆序（至少 2 处违反 :6 声明的排序规则）。F936：INDEX 引 #6 位于 :25/:29/:160/:163/:167；archive/2026-08-14-pipeline-never-completes-design.md `grep -c "#6"`→0。F937：INDEX:38 "§J" vs 归档推理 spec 实际 `#### 2.9`（:122）。F938：diff decisions-chain:38-41 vs security-injection:15-18→IDENTICAL。F939：4+45+318+98+1=466≠467。F940：#16 spec unique ID token 复计 132（初审 127，正则差异，均≫98）。F941：p2-batch :17(F0-05, PR-22 对) vs :32(F125, PR-20 错)。F942：design spec :137 "T1-T11 十一条"、:173 "11 条线程"、:309/:310/:323 "Z1-Z10/T1-T9" vs :182/:204 与交付 v3 的 T1-T16。F943：:272/:274 引 2026-08-13-* 文件名（实际 2026-08-14-*）。F944：prompt:336 `archive/2026-08-01-deterministic-...`（实际在 specs/ 根）。F945：INDEX:139 与 deterministic:10 "已 9 次实现"。F946 独立确认：`plans/archive/2026-06-22-positive-quality-gates.md` 存在且 :7 即分层句。F947：四份 spec 验收行原文属实（cost-ledger:8/data-loss:10/z11:17/output-side:45,60）。F948：spec:36 typo 原文在。F949：resonance_trend.md 现盘 1 数据行 9 列。F950：`grep -l "Date:** 2026-08-1[45]" specs/*.md`→20/23。
- 附注（非异议）：台账数据行严格解析为 782 行（初审 Z9-b/Z9-c 口径 786/787）——差异来自 21 条畸形行（10 列×19 + 未转义管道×2）的解析归责，material 结论（final-report 781 过期）不变。

### Z9-c 段（F967-F975）：9/9 成立
- F967：66/63 vs 68（30+33+5）复现。F968：脚本复跑→32 DRIFT + 0 TRUE-DEAD（与初审完全一致）。F969：final-report "781（655…）" 在盘、T 行 103、INDEX 活跃 23。F970：coverage-ledger 2850 个 zone-report 锚点中缺失目标恰为 {'Z8.md':100, 'Z7.md':908}。F971：coverage.xml `line-rate="0.8728"` vs final-report:15 "85.16%"。F972：畸形行精确复计 21（≥初审 15，方向一致）。F973：zones 并集 2755 − table-A 2738 = 17，反向 0。F974：63 全未勾 + 2 混合 + 3 无框。F975：Z9-c.files 无 coverage.xml，磁盘 165 文件。

## 2. 漏报（初审未立案，本轮新发现）

### F951 | command-to-give.md:1 引用已归档的 plan 路径（断链重扫命中） | error | P2
- 证据: command-to-give.md:1 `按 docs/superpowers/plans/2026-06-11-test-framework.md 执行测试轮次`；目标实际位于 `docs/superpowers/plans/archive/2026-06-11-test-framework.md`
- 根因: plan 归档（移入 archive/）时未回写执行协议首行引用——与 F968（归档 plan→spec 方向 32 处）互为镜像的 plan 方向断链；Z9-a 的 command-to-give 条目核验了 round-exec.sh/lock-tool-hashes.sh 存在性但漏扫首行
- 验证: `ls docs/superpowers/plans/2026-06-11-test-framework.md`→No such file or directory；`ls docs/superpowers/plans/archive/2026-06-11-test-framework.md`→存在
- 建议方向: 路径补 `archive/` 段，或引用改为"plans/ 按 basename 解析"约定（与 F968 建议统一）

### F952 | command-to-give.md:24 工具名 validate-gate.py 全仓不存在（F903 未涵盖的同行文件名漂移） | error | P2
- 证据: command-to-give.md:24 `修改 validate-gate.py / scoring.py / phase-runner.py 后…`；`find . -name "validate-gate.py"`（排除 .git/site）→0 命中
- 根因: F903 立案了该行的 G0.13 语义失效，但三个工具名中 validate-gate.py 已随 src 布局迁移消亡（gates/cli.py 等取代）、phase-runner.py 现名 phase_runner.py；文件名漂移本身未入案
- 验证: `find . -name "validate-gate.py"`→空；`ls src/shenbi/phase_runner.py src/shenbi/scoring.py`→存在
- 建议方向: 随 F903 修复一并更正为现路径（src/shenbi/gates/、scoring.py、phase_runner.py）

### F953 | command-to-give.md "第二步：确认进度" 为空节 | error | M
- 证据: command-to-give.md:26-28——`### 第二步：确认进度` 后直接接 `### 第三步`，节体为零行
- 根因: 内容删除残留（疑为 summarize_round/update_progress 删除事件的连带残骸，同 F913 根因族）
- 验证: `sed -n '26,29p' command-to-give.md`→节头后无内容
- 建议方向: 补写该步骤（如读 progress.json）或删节并重排步骤号

### F954 | plans/INDEX.md:23 三项附加过期：PR 范围、日期域、最近归档项 | error | P2
- 证据: plans/INDEX.md:23 `63 个已完成的 plan…按日期排序（2026-06 ~ 07）。这些 plan 对应的 PR 已全部合并到 main（#1–#19）`；:38-45 "最近归档项" 最新仅到 2026-07-19-19
- 根因: F967 仅立案计数漂移（66/63 vs 68）；同文件还有——(a) archive 含 2026-08-02×4 + 2026-08-15×1，"2026-06 ~ 07"日期域过期；(b) 新归档对应 PR #20/#26/#28/#39/#42（pr20-followup/issue24/pipeline-never-completes 等 plan 头部与 INDEX:12 自证），"#1–#19"范围过期；(c) "最近归档项"列表缺 5 项
- 验证: `ls docs/superpowers/plans/archive | cut -c1-7 | uniq -c`→30/33/5；`grep -m2 "PR #" plans/archive/2026-08-02-pr20-followup-*.md`→PR #20；INDEX:12 自记 "#6 pipeline-never-completes（PR #42，2026-08-15）"
- 建议方向: 随 F967 修复一并刷新（或仿 specs/INDEX 改为不追踪归档明细）

### F955 | prompt 设计 spec :226 预写审计目录 2026-08-13/（F943 未列的第三处同族漂移） | error | M
- 证据: 2026-08-13-full-project-audit-prompt-design.md:226 `审计状态目录：docs/superpowers/audit-runs/2026-08-13/`；磁盘 audit-runs/ 仅 2026-08-14、2026-08-15
- 根因: 与 F943（:272/:274 文件名预写跨天）同根因——设计日 08-13、执行日 08-14；F943 证据列未含此目录级引用
- 验证: `ls docs/superpowers/audit-runs/`→2026-08-14 2026-08-15；sed :226 原文在
- 建议方向: 并入 F943 修复（引用参数化 $AUDIT_DATE 或改实际目录）

### F956 | F8/F9/F10 跨审计代 finding 编号命名空间复用 | error | M
- 证据: 2026-08-01-output-side-waste-audit-design.md:62 `### 2.3 [F10] revision 读原始 glob 无去重`（该 spec 自有 F8/F9/F10 编号体系）；2026-08-14 findings-ledger 中 F8/F9 为含义完全不同的 ID，F10 不存在（`grep -c "^| F10 "`→0）；specs/INDEX.md:39 以无命名空间限定的 "F8/F9/F10" 转述
- 根因: 两代审计沿用同一 "F" 前缀、无代际前缀区分；fresh 读者按 2026-08-14 台账解析会错配（F8/F9）或落空（F10）
- 验证: ledger grep 如上；output-side spec §2.x 标题自带定义（自包含，故仅 M）
- 建议方向: 转述处加限定（如 "08-01 audit F10"）或在两代编号间加代际前缀；随 M 批量 spec（#16）处置

## 3. 误报

**0 条。** 43/43 初审 findings 独立重证全部成立（§1）。两处初审自标低置信项本轮独立确认：
- Z9-b F946（F1100 疑似误报的元判断）：`plans/archive/2026-06-22-positive-quality-gates.md:7` 存在且内容即分层 prose——F1100 的"断链"定性确实不完整，F946 维持。
- Z9-b F949（resonance_trend 实证过期）：现盘确认 1 数据行/9 列表头，"2 行 7 列 Ch{N}"与磁盘不符，F949 维持。

## 4. 覆盖空洞

### F957 | 文档断链 CI 防线（test_docs_accuracy.py）盲区：F901/F951 类断链可无感穿过 | coverage | P2
- 证据: tests/integration/test_docs_accuracy.py:16-25 仅白名单 8 份根级文档；:30 正则 `` `([.\w][\w./-]*\.\w+)` `` 只匹配**单个无空格 token 的反引号路径**——command-to-give.md:48 的 `` `bash tests/dispatch-subagent.sh <skill> …` ``（含空格，F901）与 :1 的裸路径（非反引号，F951）均不可见；:48 的 `bash tests/lock-tool-hashes.sh` 同因含空格不可见（该文件恰存在，属侥幸）
- 根因: 防线设计窄于文档实际引用形态（带前缀命令、裸路径、跨行引用）
- 验证: 正则复算 command-to-give.md 全文可命中路径仅 `outline-example.md`、`tests/fixtures/`（均存在）→ 测试恒绿
- 建议方向: 正则扩展至"反引号内含路径子串"与 8 文档外的 docs/ 主文档；或按本轮角度沉淀为 tools/lint_repo_consistency.py 的新检查项

**接受风险披露（无需新案）**：
1. audit-runs/2026-08-14/zone-reports 110 份仅机械批扫 + 3 抽读（Z9-c DV1 裁量已披露）——本轮按引用角度抽查未发现新断链形态，维持裁量。
2. specs/archive 101 份深读仅 6——本轮补扫 2 处年份前缀引用（deterministic:18/:44、p2-batch:287）均可后缀解析，残余风险低。
3. **空洞已闭**：spec #13 config-governance 初审 medium 置信（"未逐向量核验 g0 源码"）——本轮抽验 3/4 向量机制成立（g0_config_coherence.py:92 `is False`、:89 `auditDimensions` 整键 get、genre_config.py:94 已由初审核过），#13 的记录准确性可升 high 置信。

## 5. 严重度异议

**无升级/降级建议，43 条全部维持。** 边界判定的复核理由：
- **F903 维持 P1（P0 候选被拒）**：虽字面触及"契约被静默违反"，但 _tool_hashes 锁是纵深防御检查（攻击者需先获 src/ 写权限），无数据损坏路径；按"文档承诺 vs 代码现实漂移 + 安全语义"落 P1 恰当。
- **F902 维持 P1**：README 快速开始命令逐字执行失败（本轮原样复现 `error: justfile does not contain recipe '--auto'`），命中"新用户按文档操作失败"。
- **F904/F917 维持 P2/M**：AGENTS.md 的 69 计数与 tests/rounds 是**自身陈述过期**（陈述即缺陷本体），不构成"违反 AGENTS.md 显式契约"的 P1 情形（该条款指行为违反既有契约）。
- **F912 维持 P2**：SECURITY.md "weekly" 失实属安全文档漂移（CodeQL weekly 属实），非 AGENTS 契约或功能路径失败。
- **F913 维持 P2**：goal-prompt.md:13 自带 "起始环境 2026-06-13" 快照标记，无活跃消费方（仅 test_docs_accuracy.py 文件清单与审计 prompt 提及），过期属快照性质而非活跃误导。
- Z9-c 全段（F967-F975）P2×4 + M×5 与证据权重相称（归档物/台账自洽类，无用户路径损害）。

## 6. 汇总

| 类别 | 数量 | 编号 |
|---|---|---|
| 漏报 | 6 | F951(P2) F952(P2) F953(M) F954(P2) F955(M) F956(M) |
| 误报 | 0 | —（初审 43/43 成立；2 条自标低置信项获独立确认） |
| 覆盖空洞 | 1 立案 + 3 披露 | F957(P2)；接受风险 2 项、已闭空洞 1 项（#13 置信升级） |
| 严重度异议 | 0 | 全部维持（含 1 项 P0 候选审查后拒绝） |

全引用扫描：**129 文档 / ≈393 出站引用 / 新真断链 1（F951）+ 同族补充 5 处**；断链防线盲区 1（F957）。三段初审的引用抽样与机械核验结论经全量重扫后**无一被推翻**，本轮新增发现集中在 command-to-give.md 的引用完整性与 plans/INDEX 的归档明细滞后。
