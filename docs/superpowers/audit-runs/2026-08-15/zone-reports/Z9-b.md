# Z9-b 段报告 — docs/superpowers/specs/（127 文件）+ 2 prompt 文档

> 审查轮：2026-08-15 · 只读 · 编号段 F934-F950
> 覆盖：机械核验 127/127（100%）+ 深读 31/127（23 活跃 spec 全文 + INDEX + 2 prompt 全文 + 6 份归档抽样）

## 0. 覆盖统计

| 项 | 数 |
|---|---|
| 区清单文件 | 127（2 prompt + INDEX + 23 活跃 + 101 归档） |
| 机械核验（头部 schema/交叉引用/词表/注册表闭合/清单闭合） | 127/127 |
| 深读 | 23 活跃 spec 全文 + INDEX.md 全文 + full-project-audit-prompt.md 全文 + single-model-sdd-prompt.md 全文 + 归档 6 份（pipeline-never-completes 全文；read-write-consistency 总纲结构+关键节；2026-07-19-01 定点行；inference-control 结构+§2.9；positive-quality-gates-design 头部+:63；p-1.e README 头部） |
| file:line 引用核验 | 活跃 spec 全量提取 73 处，其中 ~40 处逐条对照源码 |
| 未覆盖文件 | **0** |

## 1. 机械核验结果（/tmp 脚本 + grep/awk）

| # | 检查 | 命令 | 结果 |
|---|---|---|---|
| a1 | INDEX↔磁盘双向闭合 | `python3` 解析 INDEX `**文件**：` vs `ls specs/*.md` | **PASS**：INDEX 登记 23 = 磁盘 23，双向差集空，编号无重复（3,4,5,7-26，缺 6=已归档） |
| a2 | 活跃 spec 数声明 | `sed -n '4p' INDEX.md` | **PASS**："活跃 spec 数：23" 与实际一致 |
| b | 归档与"不追踪归档"约定 | INDEX 全文 grep archive 引用 | **PASS**：INDEX 无归档条目；series 字段仅引用 archive/2026-08-01-pipeline-read-write-consistency-audit-design.md（目标存在）；`archive/...` 为链接显示文本非死链 |
| c | 头部块完整性 | 全 blockquote 解析 Date/Status/Severity/系列/依赖/范围 | 活跃 23 份 **全部齐备**（2026-08-01/08-13 三份为 8 行 blockquote，字段在 5-8 行）；归档 6 月代 spec 无头部（历史格式，冻结不动，不计 finding）；归档 7 月代起有头部 |
| d | 交叉引用有效性 | spec 内 `#N` 与文件名引用解析 | 见 F936（#6 编号不可解析）、F943（2026-08-13-* 文件名死链）、F944（prompt T14 archive 误标）、F937（§J）；其余 `#3/#10/#16/#20/#39/#40` 均可解析（PR 号或活跃编号） |
| e | Status/Severity 词表 | 全量归一 | Status：Design×40 / Done (PR #N)×1 / Rejected/Executed×0 / 非常规：`Consolidated Design`×2、`设计中（Design）`×2、`Design（待批准…）`×2、`Design（v1 已交付…）`×1（活跃）、超长 Done 摘要×1——**全部在归档**（除 08-13 一份带修订注，属刻意），可接受 |
| f | 区清单↔磁盘闭合 | zone files vs `specs.rglob` | **PASS**：双向差集空 |
| g | p2-batch 分区计数 | 逐节 bullet 计数 | **PASS**：3/26/43/52/67/26/29/17/4/1/11/8，和=287=声明值；节内无重复 ID |
| h | prompt v3 数字声称复验 | prompt 内 awk 命令重跑 2026-08-14 台账 | **PASS**：P0 5/P1 118/P2 492/M 165；词表外 6 行（F417/F627/F149/F653/F160/F1205）；总行 787=header+786 数据行（ID 匹配 785+1 行格式损坏）；false-positive 1；final-report 同时含 781（手抄）与 786（机械）——prompt 的 A6 叙述与磁盘一致 |

## 2. 关键 file:line 证据时效性核验（活跃 spec → 当前 main HEAD）

仍成立（机制在，行号准）：error_handler.py:36-37（重试常量）、executor.py:264/284 snapshot_tree(PROJECT_DIR)、executor dispatch() G1/G2 先于 dispatch_codex（~209-227）、contracts/skills/genre_config.py:94 `if disabled and self.custom_rules:`、schemas/decisions.py:33 `has = rationale is not None`、phase_runner.py:216 G4 传 round_dir、g3.py:151-153 skill 层读 output_files + :188 except 面窄、gates/g_reconcile.py 无 removesuffix("-scores")、baseline.py:24 establish_baseline 零生产调用、linguistic_drift.py:215/218 off-by-one、AGENTS.md:87-89 escape-hatch 契约、pyproject.toml:17 注释+dev 组 sentence-transformers、test_truth_embed.py:122 / test_context_assemble.py:167 永久 skip、skills/ 74 目录 vs AGENTS "69"、novel-output pending_hooks truth 9886B vs staging 4171B（F1308 实证）、crash_recovery.py:66 atexit + :144-148 无条件 clear_staging、#26 chapter_loop.py:248 step15 + :1641 死函数带 pyright ignore、_resolve_g4_files:565、modes/codex.py:44/61-66、D1 工具清单 9 个全部存在、plans/INDEX.md 存在、.superpowers 已 gitignore。

已漂移：见 F934 汇总（PR #42 2026-08-15 合并重排 chapter_loop/dispatch_helper 后 ~9 组行号失效，其中 cost-ledger 的"仅一处传 state"计数也失效）。

---

## 3. 逐份条目

### docs/superpowers/specs/INDEX.md
- 处置: deep-read（机械 23 登记全核 + 深读全文）
- 声称检查的不变量: [登记↔磁盘双向闭合；编号唯一不重复；排序符合声明规则；归档不追踪；archive 链接有效；活跃数声明准确]
- findings: [F935, F936, F937]
- 验证命令: [python3 双向 diff → 差集空；排序 rank 函数比对 → 4 处错位；`grep "#6" INDEX` ×5 处 + `grep "#6" archive/2026-08-14-pipeline-never-completes-*.md` → 0 命中；`grep "§J"` → INDEX:38 唯一，归档推理 spec 实际为 `#### 2.9`（:122）]
- 置信度: high

### 2026-08-14-data-loss-cluster-design.md（#7）
- 处置: deep-read（全文 29 行）
- 声称检查的不变量: [R1-R5 证据 file:line 时效；验收可执行；crash_recovery/chapter_loop 机制仍在]
- findings: [F934（:2405-2419→实际 2431 一带；:1165→实际 1178）, F947（R1 "连续 3 章"、z11 联动验收需真实 dispatch）]
- 验证命令: [`sed -n '66p;144,148p' crash_recovery.py` → atexit.register + clear_staging 属实；`grep -n ThreadPoolExecutor chapter_loop.py` → :2431]
- 置信度: high

### 2026-08-14-cost-ledger-design.md（#12）
- 处置: deep-read（全文）
- 声称检查的不变量: [R1 接线计数与行号；R2 no-op 转义仍在；验收可执行]
- findings: [F934（计数失效：'仅 :2794 一处传 state' → 现 1274/2831/3003 三处传 state；:2794 已是 revision-skip 代码）, F947（验收'真实 pipeline 运行后'与 SDD 核心原则 8 冲突）]
- 验证命令: [`grep -n "dispatch_skill(" chapter_loop.py` → 3 处均带 state=state；`grep -n 'u003c' dispatch_helper.py` → :747 `content.replace("<", "\u003c")` 恒等替换仍在（F300 机制成立，行号 734→747）]
- 置信度: high

### 2026-08-14-full-project-audit-design.md（#17 总纲）
- 处置: deep-read（全文）
- 声称检查的不变量: [覆盖统计与台账机械对账；簇图与执行顺序自洽；G5(b) 第三条腿存在]
- findings: [F939]
- 验证命令: [awk 台账统计 → 786 行（P0 5/P1 118/P2 492/M 165），spec 声称 467 且 4+45+318+98+1=466≠467；spec 正文无每-finding 行/子 spec 清单；INDEX #17 内容字段"子 spec #6-#16 父条目"未含 #18-#26]
- 置信度: high

### 2026-08-01-output-side-waste-audit-design.md（#4）
- 处置: deep-read（全文 173 行）
- 声称检查的不变量: [error_handler/revision_router/parallel_dispatch 引用时效；与总纲 §3.1/§3.5 引用有效；INDEX 依赖描述与 spec 一致]
- findings: [F948（:36 常量名 typo MAX_DISPATCH_DETRIES）, F947（验证法"mock 一个 G4 FAIL 章节"与 G0.9/核心原则 8 冲突）]
- 验证命令: [`sed -n '36,37p' error_handler.py` → MAX_DISPATCH_RETRIES=2/MAX_AUDIT_RETRIES=3 成立；总纲归档文件 `#### 3.1/#### 3.5` 存在（:185/:223）；revision_router.py:199、parallel_dispatch.py:189-249 仍准确]
- 置信度: high

### 2026-08-13-full-project-audit-prompt-design.md（#5）
- 处置: deep-read（全文 343 行）
- 声称检查的不变量: [v2/v3 修订记录与正文一致；TOC/门/线程计数自洽；§9 产出文件名有效]
- findings: [F942, F943]
- 验证命令: [grep 计数：§3 阶段表 'T1-T11 十一条'、§5 G2 '11 条线程'、§8 目录树 'Z1..Z10'+'T1..T9'、§11 TOC 'Z1-Z10'/'T1-T9'、§12 'Z1-Z10/T1-T9' vs §6 'Z1-Z11'/§7 'T1-T11'；§9 引用 2026-08-13-*.md 两处 → 磁盘为 2026-08-14-*]
- 置信度: high

### 2026-08-14-gate-effectiveness-design.md（#8）
- 处置: deep-read（全文）
- 声称检查的不变量: [R1-R9 证据时效；验收可执行]
- findings: [F934（:1921-1945→伪造 scorer 实际 1984-1985；:2907-2917→G3 实际 2944-2946；genre_config.py:94 正确（contracts/skills 文件））]
- 验证命令: [grep 'pipeline-g3-scorer' dispatch_helper.py → :1984-1985；`grep -n "run_gate_g3" chapter_loop.py` → :2946；`sed -n '94p' contracts/skills/genre_config.py` → 精确命中；phase_runner.py:216 / g3.py:151-153,188 / decisions.py:33 / codex.py:44 全部精确命中]
- 置信度: high

### 2026-08-14-contract-single-source-design.md（#9）
- 处置: deep-read（全文）
- 声称检查的不变量: [AGENTS.md:87-89 契约引用；skills 计数 74 vs 69；deps.json 断言抽验]
- findings: 无（R5 的 69 vs 74 复验成立：`ls skills/ | wc -l` = 74，AGENTS.md 仍称 69——缺陷在 AGENTS 侧，属 Z9 其他文件/他区，spec 记录准确）
- 验证命令: [`sed -n '87,89p' AGENTS.md` → escape-hatch 全文+WARN 属实]
- 置信度: high

### 2026-08-14-audit-chain-design.md（#10）
- 处置: deep-read（全文）
- 声称检查的不变量: [executor 快照根证据；G4 目录参关联]
- findings: 无（executor.py:244 为 dispatch_with_write_audit def、:264/:284 snapshot_tree(PROJECT_DIR) 属实；R4/R5 机制面未复核到反例）
- 验证命令: [`grep -n "snapshot_tree\|PROJECT_DIR" executor.py` → :31/:142/:264/:284]
- 置信度: high

### 2026-08-14-drift-chain-design.md（#11）
- 处置: deep-read（全文）
- 声称检查的不变量: [baseline 零调用；off-by-one；is_drift 门控；吞异常]
- findings: [F934（:2023→实际 2052；:2722-2727→实际 2758-2765）]
- 验证命令: [grep establish_baseline src/ → 仅 __init__ 重导出零生产调用（F602 成立）；`sed -n '215,218p' linguistic_drift.py` → max(...,5.0) vs >5.0 成立；:2052 `if result.is_drift:`；:2758-2765 except Exception 吞 :2062 raise DriftEscalationError（F620 成立）；另 :2022 死函数现带 pyright ignore 标记——强化死链论断]
- 置信度: high

### 2026-08-14-config-governance-design.md（#13）
- 处置: deep-read（全文）
- 声称检查的不变量: [向量清单与 g0_config_coherence 机制对应（抽 1 项）]
- findings: 无
- 验证命令: [`sed -n '94p' contracts/skills/genre_config.py`（F666 相关 disabled-and-custom_rules 形态属实）]
- 置信度: medium（未逐向量核验 g0 源码）

### 2026-08-14-deps-supply-chain-design.md（#15）
- 处置: deep-read（全文）
- 声称检查的不变量: [pyproject 注释/dev 组；两个永久 skip 测试]
- findings: 无
- 验证命令: [`sed -n '17p;47p' pyproject.toml` + `sed -n '122p' test_truth_embed.py` + `sed -n '167p' test_context_assemble.py` → 三处精确命中]
- 置信度: high

### 2026-08-14-fixture-authenticity-design.md（#18）
- 处置: deep-read（全文 83 行）
- 声称检查的不变量: [F8xx 断言抽验 2 项；验收机械可执行]
- findings: 无（验收'闭包扫描 0 断链'可机械执行）
- 验证命令: [F805/F821/F822 抽验：`grep -l target_platform novel.json`→无；`wc -l sensitive_words/stop_words` 形态断言与本区 Z7-a 交叉一致，未重跑全量]
- 置信度: medium（依赖 Z7 区结论交叉，未独立重跑全量 fixture 扫描）

### 2026-08-14-decisions-chain-design.md（#19）
- 处置: deep-read（全文 65 行）
- 声称检查的不变量: [_resolve_g4_files 证据；producer prompt 证据；P2 清单边界=decisions 链]
- findings: [F934（:725→实际 738）, F938（T12-03..06、T14-02/05/06/07 与 #22/#24 逐字重复）]
- 验证命令: [`grep -n "_resolve_g4_files" chapter_loop.py` → :565 精确；`grep -n "must conform" dispatch_helper.py` → :738；diff 跨 spec T12-04/T14-05 行 → IDENTICAL]
- 置信度: high

### 2026-08-14-z11-output-contracts-design.md（#20）
- 处置: deep-read（全文）
- 声称检查的不变量: [F1308 字节数实证；验收可执行]
- findings: [F947（R3 验收'真实项目 progress.json…token-ledger.jsonl 存在且有记录'需真实 pipeline 产物）]
- 验证命令: [`wc -c novel-output/xinghuo-ranqiong/{truth,staging/truth}/pending_hooks.md` → 9886/4171 精确命中]
- 置信度: high

### 2026-08-14-truth-write-path-design.md（#21）
- 处置: deep-read（全文）
- 声称检查的不变量: [R1 双写者 2 行实证；R3 staging 分叉]
- findings: [F949]
- 验证命令: [`cat truth/resonance_trend.md` → 现仅 1 数据行（ch55，9 列表头），无 'Ch{N}' 7 列形态、无双行；pending_hooks 分叉字节成立]
- 置信度: medium（'2 行'可能审计时点为真，但该文件 git 历史仅 1 次 commit（dd1fc62），故更可能当时即不准确）

### 2026-08-14-security-injection-design.md（#22）
- 处置: deep-read（全文）
- 声称检查的不变量: [T12-01/02 机制面抽验；与 #19 重复边界]
- findings: [F938（重复的另一端）]
- 验证命令: [`sed -n '61,66p' modes/codex.py` → codex exec -C 直跑属实（T12-02 写面主张成立）]
- 置信度: high

### 2026-08-14-z8-contract-drift-design.md（#23）
- 处置: deep-read（全文 96 行）
- 声称检查的不变量: [F953/F1002/F1008 抽验；P2 清单无跨 spec 重复]
- findings: 无
- 验证命令: [抽验 `grep -n "chapter_loop.py:1090-1168"`（F958 内引用）→ 该范围存在；F-numbers 与 #18/#25 无 ID 交叠（机械 diff）]
- 置信度: medium（45 条 P2 未逐条重取证据，与 Z8 主区报告交叉）

### 2026-08-14-tooling-gate-chain-design.md（#24）
- 处置: deep-read（全文 69 行）
- 声称检查的不变量: [R1b 字段过滤死线抽验；F1209 已知项复验；P2 边界]
- findings: [F938（T14-02/05/06/07 重复的另一端）]
- 验证命令: [`sed -n '5,8p' .github/dependabot.yml` + `sed -n '7p' embeddings-smoke.yml` → 两处引用的 spec 路径确已移入 archive/（F1209 M 级成立，spec 已登记）]
- 置信度: high

### 2026-08-14-stats-determinism-design.md（#14）
- 处置: deep-read（全文）
- 声称检查的不变量: [子项 2 抽验]
- findings: 无
- 验证命令: [`sed -n '215,218p' linguistic_drift.py` 同源；引号桶/熵分母未逐条重算（与 Z6 区交叉）]
- 置信度: medium

### 2026-08-14-minor-findings-batch-design.md（#16）
- 处置: deep-read（全文 46 行）
- 声称检查的不变量: [条目计数=98；分区结构完整；ID 无重复]
- findings: [F940]
- 验证命令: [python3 ID 计数 → unique 127（含 F1102-F1116/F1318/F1320/T6-05 后补），声明 98；Z7-Z11 节含 8 行 `- ## …` 伪标题 bullet；Z3 行内 F3AA/F3AD 各出现 2 次]
- 置信度: high

### 2026-08-14-p2-batch-design.md（#25）
- 处置: deep-read（全文 313 行）
- 声称检查的不变量: [分节计数=声明 287；ID 唯一；F1100/F1101/F0-05/F125 抽验]
- findings: [F941, F946]
- 验证命令: [分节计数全对（见 §1.g）；ID 无重复；F0-05 与 F125 同指 command-to-give.md:48→不存在脚本，git 证实删除 commit 0f68102='PR-22'（F0-05 对，F125 'PR-20' 错）；F1101 自身'订正行号' 1059-1065 现又漂至 1072-1074]
- 置信度: high

### 2026-08-15-snapshot-subsystem-wiring-design.md（#26）
- 处置: deep-read（全文）
- 声称检查的不变量: [死三件套/平行实现/step15/rollback deferred 证据；三路验收可执行；#6 交叉引用可解析]
- findings: [F936（'见 #6 修订注'仅编号无文件名，归档文件内无 #6 标记）]
- 验证命令: [`grep -n "create_differential_snapshot\|_snapshot_chapter_files\|pre-revision-snapshot" chapter_loop.py` → :59/:1641（pyright ignore）/:1748/:248 属实；`sed -n '154p' crash_recovery.py` 平行实现存在；验收三路均可机械执行（manifest 存在性/git grep/just check）]
- 置信度: high

### 2026-08-01-deterministic-skill-replacement-audit-design.md（#3）
- 处置: deep-read（全文 205 行）
- 声称检查的不变量: [9 先例表、测试文件存在性、archive 引用、核心洞察与后续审计一致]
- findings: [F934（:1030-1037→实际 1072-1074，F1101 的'订正值'亦漂）, F945, F946（:18 引用的另一面）]
- 验证命令: [tests/unit/pipeline/test_truth_io.py、tests/pipeline/test_snapshot_diff.py、tests/unit/gates/g4/test_context_composing.py 均存在；`2026-06-22-positive-quality-gates.md:7` → plans/archive 同名文件存在且 :7 即分层 prose；`grep "9 次"` → spec:10 与 INDEX #3 内容字段均沿用]
- 置信度: high（F946 为 medium）

### docs/superpowers/full-project-audit-prompt.md（v3）
- 处置: deep-read（全文 494 行）
- 声称检查的不变量: [机制自洽（G4 双轨/G5 命令/G6 分层/§3.5 角度库/§1.6 无人值守）；全部数字声称机械复现；工具/路径引用有效；rubric 内联完整]
- findings: [F944]
- 验证命令: [§1.g/h 全部复现（P0 5/P1 118/P2 492/M 165、786、词表外 6、FP 1）；D1② 9 个工具路径全部存在；唯一路径错误=T14 'archive/2026-08-01-deterministic…'（archive 无此文件，实际在 specs/ 根）；G5(a)(b) awk 命令可原样执行；§10 反合理化 31 行 vs 设计 spec 账面 8+6+9=23——差异因 v1 实交付表大于设计 spec 示例表，未计 finding（无法以现盘证据定罪）；T1-T16/Z1-Z11 计数全文一致]
- 置信度: high

### docs/superpowers/single-model-sdd-prompt.md（v6）
- 处置: deep-read（全文 310 行）
- 声称检查的不变量: [阶段编号 0-12 自洽；引用路径存在（plans/INDEX、AGENTS §PR Review Protocol、.superpowers gitignore、tools/lint_status_strings）；裁决表/状态机无矛盾；停机条款事实准确]
- findings: [F950]
- 验证命令: [`ls plans/INDEX.md` ✓；`grep '.superpowers' .gitignore` ✓；批处理停机 ③ '本仓 23 份活跃 spec 全部产自同一次 2026-08-14 audit' → `grep -l 'Date:\*\* 2026-08-1[45]' specs/*.md` = 20/23（#3/#4=2026-08-01、#5=2026-08-13）]
- 置信度: high

### 归档簇 docs/superpowers/specs/archive/**（101 文件）
- 处置: 机械全量 101 + 深读抽样 6（pipeline-never-completes 全文 / read-write-consistency 总纲 / 2026-07-19-01 / inference-control / positive-quality-gates-design / p-1.e README）
- 声称检查的不变量: [与 INDEX 零登记（约定一致）；头部/词表时代一致性；被活跃 spec 引用的归档锚点有效（§3.1/§3.5/:42,:176,:283/§2.9/#6 修订注）；归档内已知 broken links（T1508）不新增]
- findings: 无新增（T1508 已知 M 项复验成立；#6 'F303 拆分声明' 即 #26 所指修订注——内容存在，解析问题记 F936；6 月代无头部属历史格式非缺陷）
- 验证命令: [`grep -n '#### 3.1\|#### 3.5' archive/2026-08-01-pipeline-read-write-consistency-*.md` → :185/:223 ✓；`sed -n '42p;176p;283p' archive/2026-07-19-01-*.md` → 与 #3 §1.3 引用语义吻合 ✓]
- 置信度: high（抽样 6/101，其余机械覆盖）

---

## 4. findings 总表

F934 | 活跃 spec file:line 证据经 PR #42（2026-08-15 合并）后系统性漂移，其中 cost-ledger 的"仅一处传 state"计数已失效 | error | P2 | cost-ledger:7（chapter_loop.py:2794→现 1274/2831/3003 三处传 state；2794 现为 revision-skip）；dispatch_helper 734→747、1165→1178、725→738；gate-eff 1921-1945→1984-1985、2907-2917→2944-2946；drift-chain 2023→2052、2722-2727→2758-2765；data-loss 2405-2419→2431；deterministic 1030-1037→1072-1074 | 根因：spec 定稿后 main 大改未回填行号/计数 | grep 对照（见 §2/§3 各条目输出）| 执行前按 SDD 阶段 2 机械漂移核对统一回填；cost-ledger R1 需重述接线现状
F935 | INDEX 排序违反自身声明（🟠 P1 的 #26 排在 ⚪ Low #16 与 🟡 P2 #25 之后） | error | P2 | INDEX.md:154-169（#16→#25→#26 相邻序）vs INDEX.md:6 排序规则 | 根因：#26 后追加未按优先级插队 | `python3` rank 排序比对 → 4 处错位 | #26 移至 P1 段（#24 后）；或明示"追加例外"
F936 | 编号交叉引用 #6 不可解析：INDEX 5 处 + #26 系列/正文引用 #6，归档文件与 archive/ 目录均无编号标记 | error | P2 | INDEX.md:29,160,163-168；2026-08-15-snapshot…:2；archive/2026-08-14-pipeline-never-completes-design.md 全文 grep "#6"=0 | 根因：归档时编号只活在 git log（-S '### #6 '） | grep 输出如上 | 归档 spec 头部加 `编号: #N` 回填，或 INDEX 侧建编号→归档文件映射节
F937 | INDEX #4 依赖字段引用不存在章节 "§J"（归档推理控制 spec 实为 §2.9） | error | M | INDEX.md:38 vs archive/2026-08-01-inference-control-audit-design.md:122（`#### 2.9 finish_reason=length 完全未检测`）| 抄写笔误 | grep '§J' INDEX → 唯一命中且目标无此节 | 改 §2.9（与 #4 spec 正文一致）
F938 | 活跃 spec 间 P2 条目逐字重复：T12-03/04/05/06 在 #19+#22，T14-02/05/06/07 在 #19+#24 | error | P2 | decisions-chain.md:38-41,46-49 vs security-injection.md:15-18、tooling-gate-chain.md:44-47（diff IDENTICAL）| 补齐 spec 批量粘贴未做归属裁决 | diff 输出 IDENTICAL ×2 抽验 | 指定唯一 owner spec（建议随主题归 #22/#24），另一侧改为指针
F939 | #17 总纲统计与最终台账不闭合且自身加总差 1；G5(b) 三方对账第三条腿（总纲行数）缺位 | error | P2 | 2026-08-14-full-project-audit-design.md:7-8（467 vs 4+45+318+98+1=466；机械台账 786：P0 5/P1 118/P2 492/M 165）+ 全文无每-finding 行/子 spec 清单；INDEX.md:29 "子 spec #6-#16" 未含 #18-#26 | 阶段 5 中途快照未随补齐 spec 更新 | awk 台账统计（§1.h）| #17 补"快照时点+终值对账"注记或重出统计；INDEX 内容字段补 #18-#26
F940 | #16 M 批量 spec 计数漂移（声明 98，正文 unique 127）+ Z7-Z11 节结构损坏（伪标题 bullet）+ Z3 行内 F3AA/F3AD 重复 | error | P2 | minor-findings-batch.md:2（98 条）vs python3 计数 127；:25-42（`- ## Z1 整体层…` 8 行）；:13 | 后补条目追加未同步头部/未走真标题 | 计数与结构输出如上 | 头部改实数或分批；伪标题转真 `##`；Z3 去重
F941 | #25 同一问题双重登记且 PR 归因冲突（F0-05=PR-22 正确 vs F125=PR-20 错误） | error | M | p2-batch-design.md:17 vs :32；git log --diff-filter=D tests/dispatch-subagent.sh → 0f68102 'PR-22' | 双人/双轮录入未去重 | git log 输出 | 删 F125 并入 F0-05
F942 | 设计 spec（#5）v1 遗留计数与自身及交付物矛盾：§3 'T1-T11/十一条'、§5 '11 条线程'、§8 树 'Z1..Z10/T1..T9'、§11/§12 'Z1-Z10/T1-T9' vs §6 'Z1-Z11'、§7 'T1-T11'、交付 v3 'T1-T16' | error | P2 | 2026-08-13-full-project-audit-prompt-design.md:137,173,234-236,309-310,323 | 修订以 §0/§0.1 追加、未回改正文底数 | grep 计数（§3 条目）| 正文底数一次性同步 v3 现状（或在 §0/§0.1 显式声明"正文计数以本节为准"）
F943 | 设计 spec §9 预写文件名成死链：2026-08-13-minor-findings-batch-design.md / 2026-08-13-full-project-audit-design.md（实际 2026-08-14-*） | error | P2 | 同文件 :272,274；磁盘 ls specs/ | 产出日跨天未回填 | ls 对照 | 引用改实际文件名或参数化 $AUDIT_DATE
F944 | 审计 prompt v3 T14 依据把活跃 spec #3 误标为 archive | error | P2 | full-project-audit-prompt.md:336（`archive/2026-08-01-deterministic-skill-replacement-audit-design.md`）；archive/ 无此文件（ls rc=1），实际在 specs/ 根 | 编写时预期其将归档 | ls 验证如上 | 删 'archive/' 前缀或改"specs/（活跃 #3）"
F945 | #3/INDEX 沿用 "已 9 次实现确定性替换"，被 T14-07（#19/#24）纠正为"实现 16、接线 ~5"，无勘误注 | error | P2 | deterministic…:10 + INDEX.md:139 vs decisions-chain.md:49/tooling…:47 | 后续审计推翻先验数字未回写 | grep '9 次' 双文件 | #3 头部加一行勘误指向 T14-07；INDEX #3 内容字段同步
F946 | #25 F1100 疑似误报：deterministic spec :18 的 `2026-06-22-positive-quality-gates.md:7` 可精确解析到 plans/archive 同名文件且 :7 即分层定义（prose）；F1100 假定目标为 specs/archive/…-design.md 并断言断链 | error | P2 | p2-batch-design.md:287 vs `sed -n '7p' plans/archive/2026-06-22-positive-quality-gates.md`（内容= L1/L2/L3 分层句） | 双档案同名文件歧义下未做全库解析 | sed 输出（分层句在 :7）| F1100 改为"双档歧义需消歧"或降 false-positive；修复动作从"补 -design 后缀"改为"注明完整路径"
F947 | 部分活跃 spec 验收/验证依赖真实 LLM dispatch 或手写 mock，与 SDD v6 核心原则 8 / G0.9 冲突，plan 阶段不改写即 BLOCKED | error | P2 | cost-ledger:8（真实 pipeline 运行后）；data-loss:10（连续 3 章）；z11:17（真实项目…有记录）；output-side-waste:45,60（mock 章节/跑一章审计） | 审计 spec 按"理想验证"措辞，未按可执行验收措辞 | 引用行如上 + single-model-sdd-prompt.md:31,274 | plan 必填字段阶段统一改写为 fixtures/单测表达
F948 | 输出侧 spec 常量名 typo：MAX_DISPATCH_DETRIES（实为 MAX_DISPATCH_RETRIES） | error | M | 2026-08-01-output-side-waste-audit-design.md:36 | 笔误 | grep error_handler.py:36 | 随 M 批量订正
F949 | truth-write-path R1 实证过期：'ch55 出现 2 行/7 列 Ch{N}' 与现盘不符（现仅 1 行、9 列 `{N}` 表头；文件仅 1 次 commit） | error | P2 | truth-write-path-design.md:8 vs novel-output/xinghuo-ranqiong/truth/resonance_trend.md（1 数据行） | 证据行文与磁盘脱节或当时口径不同 | cat/head 如上 | 执行前重取证据（双写者主张可能仍成立，需重验）
F950 | SDD prompt v6 停机条款事实错误："本仓 23 份活跃 spec 全部产自同一次 2026-08-14 audit"（实际 20/23，#3/#4=08-01、#5=08-13） | error | M | single-model-sdd-prompt.md:246 | 概括失准 | grep Date 头统计 → 20/23 | 改"20/23 产自 2026-08-14 审查（余 3 份为 08-01/08-13 系列）"

严重度分布：P2×14 / M×3 / P0×0 / P1×0。
（判级说明：全部为文档↔磁盘漂移、注册表自洽、findings 质量问题；所涉底层缺陷（F300/F397/F216 等）本身仍在代码中且已有 spec 覆盖，未发现新数据损坏或契约静默违反，故无 P0/P1。）

## 5. 低置信度清单

- F946（F1100 误报定性）：medium——specs/archive 确有 `-design` 同名文件且其 :7 非分层表，F1100 的后半句对该文件成立；但引用名（无 -design）与 plans/archive 文件精确匹配且内容吻合，"断链"定性至少不完整。
- F949（resonance_trend 2 行实证过期）：medium——磁盘现状明确，但无法排除审计时点读取的是 staging/快照副本。
- #23 z8 / #18 fixture / #14 stats 三份的 P2 子项证据：medium——抽验通过但未逐条重取（依赖 Z6/Z7/Z8 主区交叉）。

## 6. 未覆盖文件

无（127/127 机械全覆盖；活跃 23 + prompt 2 + INDEX 全文深读；归档 101 机械全量 + 6 份抽样深读）。
