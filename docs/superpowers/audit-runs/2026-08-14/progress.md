# 审计进度 — 2026-08-14
## 阶段状态机
| 阶段 | 状态 | 轮次历史 |
|---|---|---|
| 0 清点与基线 | done | D1 ①-⑫ 全部运行并归档；3 findings (D1-01~03) |
| 1 整体层审查 | done | 8 维度全部有结论；8 findings F0-01~08 |
| 2 分区深度审查 | done | 全部区 G2 通过（人类裁决：无新 P0/P1 判据）；Z1/Z5 字面收敛；ledger 465 findings | 轮次历史：Z1(13→9→5→6→4→6→1→2→6→2→3→2→2→…) Z2(20→6→8→3→7→1→2→3→2→…) Z3(22→11→10→8→11→7→5→1→3→…) Z4(19→12→9→6→10→6→3→11→3→…) Z5(12→4→8→6→6→2→0✓收敛) Z6(11→8→10→7→3→3→1→3→2→5→2→…)；F325 误报撤销；P0×1(F324)、P1×25+（含 F397 append_dedup 数据丢失贴 P0）；Z7-Z11 待派发 |
| 3 线程 | done | T1-T15 全部完成：98 线程 findings（T1×8 T2×5 T3×5 T4×4 T5×5 T6×5 T7×6 T8×16 T9×11 T10×2 T11×9 T12×6 T13×6 T14×7 T15×8）；关键：T1-01 decisions 零门校验、T301 字段过滤死码、T501 tenacity 死码、T8 56% fixtures mock、T9-01 lint 白名单洞、T12-01/02 注入链 |
| 4 聚类校准 | done | 去重 35 条 merged；F364 校准升 P0（Z3 补复核确认）；抽查 40/40 通过；根因簇图 10 簇 |
| 5 spec 产出 | in_progress | 1 总纲 + N 子 spec + M 批量 |
| 6 覆盖证明+裁决 | done | G1 通过（0 unreviewed）；G6 meta-audit 228 ok / 0 fake；final-report 产出；**等待 G7 人类裁决** |
## 抽样种子登记（阶段 0 生成，禁止事后修改）
- D2 漂移抽样清单 (seed=20260814，活跃文档引用全验；归档 spec 引用归 T10/T15；高风险文档 AGENTS/架构/契约/gates 由 Z9 全查):
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:36 → error_handler.py:36-37
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:37 → error_handler.py:40-57
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:38 → error_handler.py:60-81
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:51 → chapter_loop.py:203-244
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:52 → audit_layer.py:44-53
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:66 → skills/shenbi-chapter-revision/SKILL.md:9-10
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:67 → revision_router.py:199
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:68 → parallel_dispatch.py:189-249
      - docs/superpowers/specs/2026-08-01-output-side-waste-audit-design.md:116 → revision_router.py:199
      - docs/superpowers/specs/2026-08-01-deterministic-skill-replacement-audit-design.md:18 → 2026-06-22-positive-quality-gates.md:7
      - docs/superpowers/specs/2026-08-01-deterministic-skill-replacement-audit-design.md:44 → 2026-07-19-01-truth-file-and-state-accumulation-design.md:42
      - docs/superpowers/specs/2026-08-01-deterministic-skill-replacement-audit-design.md:102 → dispatch_helper.py:1030-1037
      - docs/superpowers/specs/INDEX.md:32 → error_handler.py:36-37
      - docs/superpowers/specs/INDEX.md:32 → parallel_dispatch.py:189-249
      - docs/superpowers/specs/INDEX.md:32 → revision_router.py:199
      - docs/framework/chapter-file-format.md:48 → src/shenbi/gates/shared.py:120-121
- 阶段 4 抽查: seed=20260814，从已 verified findings 中按 (id_hash % 100) < 10 抽取 ≥10%（规则固定：按 ledger 行序 hash，禁止事后挑选）
- G6 meta-audit: seed=20260814，≥20% per-file 报告条目，按区成层（每区≥1条；Z3/Z4/Z5/Z11 与低置信度文件必抽；区内按 path 确定性 hash 排序取前 k 条；k = max(1, round(n*0.20))；Z7 共 182 条、Z8 20、Z9 43、Z11 256 等按上表）
## 会话日志（追加式）
### 2026-08-14 会话 1
- 完成: 阶段 1 整体层审查——8 维度全部有结论；8 findings (F0-01~08) 录入（skills 计数漂移 / deps.json 契约缺 5 skill / gate 文档漂移 / INDEX 计数 / dispatch-subagent 引用 / py 版本三元不一致 / SECURITY weekly 声明 / coverage 注释漂移）
- 下一步: 阶段 2——Z5/Z6 复核收敛 → Z1-Z4 收报告核实 → Z7-Z11 派发
- 待核实 findings: F500-F512 (Z5), F601-F611 (Z6) 已核实 verified；Z5-01 (novel-output decisions.json 83/145 无效) 待 Z11 深查

### 2026-08-14 会话 1（续）
- 完成: 阶段 2 补全（Z7-Z11 初审，发现 56% fixtures mock）；阶段 3 线程 T1-T15 全部（98 findings）；阶段 4 聚类校准；阶段 5 12 spec + INDEX；阶段 6 G1/G6 通过 + final-report
- 下一步: **G7 人类裁决**——汇报 final-report 摘要，等待指示（结束 / 继续某簇 / 追加审查）

### 2026-08-14 会话 1（续 2）
- Z3.review2 迟到通知核验：F325 撤销 / F305 降回 P2 已生效；发现 F343/F344（M 级）漏录 → 补录台账（行 177-178），final-report 统计 761→763（M 155→157，P2 483→481 顺带修正，verified 635→637）
- 复核实测：pipeline/cli.py:294-296 传 int 0 vs genesis.py:246 传 None（F343）；write_safety.py:24-25 注释 vs chapter_loop.py:187 lifecycle 并发路径（F344）

### 2026-08-14 会话 1（续 3）
- Z4.review3 迟到通知核验：F440-F445 全部已登记（F440/F441 merged-into-F431；F442/F443/F445 verified；F444 P1 specced）
- 发现 F444（P1）台账标 specced 但无 spec 引用 → 补 gate-effectiveness-design.md R9（G3.3 output_files 层级错位恒 SKIP，含 F419/F431 家族 except 附带修复）

### 2026-08-14 会话 1（续 4）
- Z5.review3 迟到通知核验：F525/F526/F527/F528/F530 已登记（F527 merged-into-F233 正确）；发现 F529 漏录（跨区 records/ 单向 drift 检测）→ 补录，台账 763→764（P2 481→482）
- F524 P1 异议已满足（台账提前升级 P1 + specced）；F514 维持 resolved

### 2026-08-14 会话 1（续 5）
- Z1.review3 通知核验：F128-F133 六条全部漏录（台账 0 条）→ 补录（P2×3: F128/F129/F133；M×3: F130/F131/F132），台账 764→770（P2 482→485，M 157→160，verified 638→644）
- F109 M→P2 异议确认已生效；F115 P1 维持；R1 对 F105 的 "G5.3 静默 SKIP" 事实修正（真实为 PASS）已记录于报告 §3

### 2026-08-14 会话 1（续 6）
- Z3.review4 迟到通知核验：F353-F363 全部已登记（P1×2: F353/F354 specced；P2×6: F355-F360；M×3: F361-F363），锚点 11/11，与通知一致，无漏录
- **发现严重度标注不一致（G7 待裁决）**：阶段 4 产物把簇 1（pipeline 永不完成）标 "P0 族/5 独立根因"（phase4-root-cause-clusters.md:5-9、pipeline-never-completes-design.md R1-R5 各标 P0、final-report:32 "P0×5"），簇 2 标 "P0×4"（final-report:33）；但台账仅 F324/F397/F364/F1300 为 P0，簇 1 的 F353/F371/F373/F379 与簇 2 的 F640/F326 均为 P1。Z3.review4:204 复核 agent 明确把 F353 升级留待阶段 4 处置，阶段 4 未在台账落实升级 → 待 G7 裁决：P0 簇标注是"批次优先级"还是"成员级升级"

### 2026-08-14 会话 1（续 7）
- Z4.review4 迟到通知核验：F446-F455 全部已登记（9×P2 + 1×M，全 verified），锚点 10/10，无漏录
- F444 证据修正同步：review4 证明 output_files 键在任何生产 progress 形状都不存在（非 review3 的 "test_type 层" 说法）→ 已更新 gate-effectiveness-design.md R9 证据行

### 2026-08-14 会话 1（续 8）
- Z6.review5 迟到通知核验：F640-F642 全部已登记（F640 P1 specced；F641/F642 P2 verified），锚点 3/3，无漏录
- **G7 待裁决项补充证据**：data-loss spec R3/R4 亦按 P0 编写（F640 "materialize_progress 零生产者→覆盖 progress.json"、F326 "并行 post-draft 写竞态"），台账两者均 P1；Z6.review5 复核 agent 对 F640 注明"触发即破坏，建议升 P0 条件已注明"（零生产者 + 无条件 safe_write 覆盖真实 progress.json = 数据丢失 + 错误结果；steps_done%5==0 即触发）。与续 6 记录的簇 1/簇 2 P0 标注问题同源，统一待 G7 裁决

### 2026-08-14 会话 1（续 9）
- Z6.review6 迟到通知核验：F643 已登记（P2 specced，config-governance spec 统一修复条目）；F601 软异议（可辩 P2）不影响裁决（P1 维持）；F642 证据勘误已同步台账（META 剥离后 (45,46) 仍 0.637>0.6，剥离 META 不足以修复，需重新标定）
- F640 补充证据：compact/migrate_from_progress 零生产调用（F640 证据中 migrate.py:30 实为死路径），Tier A 整体未接线——已并入 F640

### 2026-08-14 会话 1（续 10）
- Z1.review9 迟到通知核验：F148-F153 全部已登记；发现 F149 行登记时漏严重度列（P2 缺失，类别 error 后直接接证据列）→ 修复为 13 列标准格式（P2 就位），台账 P2 485→486，final-report 同步
- 注：F149 标题内嵌 `\ |` 会误导按固定索引 split("|") 的统计脚本，已用精确严重度模式核对（P0×5/P1×118/P2×486/M×160/总770）

### 2026-08-14 会话 1（续 11）
- Z6.review7 迟到通知核验：F644-F646 全部已登记（P2；F645 specced stats-determinism），锚点 3/3，无漏录
- F642 勘误反勘误：review6 的 "剥离 META 后 0.637>0.6" 被 review7 反驳（同法剥离 0.570 与 review5 一致；前 200 字符 0.865 表明正文开头模板化）→ 台账注记更新为 review7 最终结论（修复需剥离 META + 阈值重标定并施）
- 跨区观察（sensitivity 双轮重复派发）建议 Z3 核查——已记录

### 2026-08-14 会话 1（续 12）
- Z6.review8 迟到通知核验：F647/F648 已登记（P2；F648 specced stats-determinism），锚点 2/2，无漏录
- F642 裁定：review8 第三次重放确认 raw 0.6267/剥离 0.5700，review6 的 0.637 裁定无效 → 台账注记更新（review5/review7/review8 三票一致）
- 收敛观察：Z6 稳定在"新发现均 P2 潜伏"区间（收敛曲线末段 3→2），复核 agent 建议评估收敛目标改为"无 P0/P1"——与人类已给 Z2/Z3/Z4/Z6 的判据一致，无需新裁决

### 2026-08-14 会话 1（续 13）
- Z1.review12 迟到通知核验：F158（P1 specced，gate-effectiveness 补充条目——phase 路径穿越）与 F159（M）已登记；发现 F160 漏录（cli_utils.emit_json BrokenPipeError，M）→ 补录，台账 770→771（M 160→161）

### 2026-08-14 会话 1（续 14）
- Z6.review9 迟到通知核验：F649-F652 已登记；发现 F653 漏录（parse_markdown_table 空行不终止表）→ 补录，台账 771→772（P2 486→487）
- **F642 裁定第四次反转（F649 终结之争）**：SequenceMatcher.ratio() 参数顺序不对称（autojunk）——生产顺序 0.6367（review6 真值）、交换顺序 0.570（review5/7/8 伪影）、autojunk=False 0.77；review8"裁定否定 review6"不成立；F642 修复需剥离 META + 对称化 + 阈值重标定三者并施。方法论教训：多轮同法复现同一数字仍可能是伪影（记录为反 rationalization 案例）
- 复核 agent 建议：收敛判定改"无 P0/P1"或对争议数字跨轮方法交叉审查——与人类已给判据一致

### 2026-08-14 会话 1（续 15）
- phase4-spotcheck 迟到通知核验：40/40 通过（证据充分 40/结论准确 40/失败 0）；三对跨区重复已合并（F527→F233、F534→F269、F537→F260）
- **G7 待裁决项第 3 项（新增）**：抽查报告指出 F269(Z2,M)≡F534(Z5,P2)、F260(Z2,M)≡F537(Z5,P2) 两对合并后严重度口径不一致（主条目保留 M，被合并方为 P2，Z5 为审计链所有者区判定更权威）——抽查报告自称"记录性，非升级依据"，未擅自改严重度，待 G7 统一
- 低置信 P1 边界观察（F228/F245/F498/F146）已按先例维持原判；F326 证据行瑕疵（lifecycle 保守默认归类）已记录

### 2026-08-14 会话 1（续 16）
- T6 迟到通知核验：**T6-01~T6-05 五条全部漏录**（T 系列唯一缺失线程）→ 补录（P2×4 + M×1），台账 772→777（P2 487→491，M 161→162，verified 646→651）
- pickle 边界不存在（全仓 0 命中）、并发原语清单、F326 契约级新证据（docstring "Zero data conflict" 与 state-settling updates 矛盾）——均已记录

### 2026-08-14 会话 1（续 17）
- Z10 迟到通知核验：F1200-F1219 中 19 条已登记；发现 F1205 漏录（run_pipeline.sh auto-approve 关键词过宽）→ 补录，台账 777→778（P2 491→492）
- Z10 关键澄清已记录：benchmarks/anchors 非空洞（11 个 AC 锚点被运行时消费，真正空洞是 tests/benchmark/）；T201 家族新增 lint_contract_graph 实例（F1200）；F1202 codex-plugin diff 空转；F0-07 家族两半（F1207 新 + F1215 已知）
