> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C37——43 条最大 P1 簇）| **依赖:** 在 C3/C7/C19(#26)/C28 各"接线裁决"spec 之后执行（本簇只清理其余 spec 未认领的死面）；与 C14 协同（直测死函数的自证测试随删除下线）| **范围:** src/shenbi 全域（error_guidance/recovery、volume_align、compact、迁移器、CONDITIONAL_STEPS、死参数/死字段/死常量）+ CI dead-code 检查 | **核心洞察:** 每一批"已实现但零接线"的功能都在说谎（docstring 声称 consumed by CLI boundary、注释声称 cli.py resume 调用）——死代码不只是浪费，它是**假防线**：读者与审计都以为机制存在。无 vulture 式执法使 43 处横散

# C37 · 死代码清理与零接线执法（dead-code-enforcement）

## 元信息
- 簇：C37（框架功能零接线/死代码横散，无 dead-code 执法），43 条，最高严重度 P1（F793/F886 verified、F903 P1），证据等级=实验佐证
- 成员：F108（代表）+ F109-F110、F118、F226、F230、F243、F313-F316、F319、F321、F325、F343、F345-F346、F356、F366、F368、F378、F427、F471、F512、F611、F622、F631-F636、F641-F642、F706、F793、F886、F903、F1027、T301、T1506、T1605、T1612
- 来源：Z1/Z2/Z3/Z4/Z6/Z7/Z8/Z9/Z10 + T3/T15/T16 线程

## 背景与根因
三类死面混杂，处置策略不同，必须分桶而不是一刀切删除：
- **A 类·假防线**（最危险）：docstring/注释/文档声称被消费但实际零调用——F108/F109（error_guidance 全部 doc_url 指向不存在文档、action 引用不存在脚本、与 recovery 双双零消费者但 docstring 谎称）、F378（_validate_state_consistency 死线且注释谎称接线）、F903（G0.13 工具哈希阻断承诺静默失效）、F230（from_markdown 永不填充 chapter_sequence，G4 no_beat_data 分支不可达）、F886（P1 verified：genesis-context/*.md 写后全仓零消费——种子实质内容在 genesis 断流，这是"死输出"不是死代码）、F311 面（curated 零消费者，已在 C30 处置）
- **B 类·成批死模块/死机制**：F314（volume_align 整模块）、F315/F793（CONDITIONAL_STEPS 死表 + _should_run_recall/_should_run_drift 死函数被直测）、F316/F631（compact 双实现零调用）、F632（migrate_from_progress 零调用）、F319（review_checklist split 段）、F321（串行审计分支不可达）、F313/T1605（truth-index 重建即弃/零读者）、F345（dispatch_skill timeout 死参数）、F346（snapshot_retention 死配置旋钮）、F366（%5 物化节拍永不触发）、F368（retry_feedback 永不清理）、F633-F636（drift/escalation 四组零调用触发器与接线）、F622（escalation/foreshadowing_recall CLI 零引用）、F641/F642（records/text 半数导出零消费）、F110（7 个异常类从未 raise）、F243（OutputKind.EPHEMERAL 死值）、F512（不可达 return 2）、F118（死参数散点）、F427（三个复制粘贴 checker）、F706（g4/conftest 死 fixture）、F1027（lint_status_strings 面）、T1506（legacy.py 命名 + re-export shim 残留）、T1612（_genre_config_cache 死缓存）
- **C 类·修复雏形**（删或接线由对应簇裁决）：F471（ProgressDoc/SummaryDoc 零使用）、F325（_verify_truth_integrity 返回值被忽略——C30 R2 认领接线）、F226（no_op_behavior: skip_write 零消费）、F356（audit_context_cache 死字段）、F611（RHETORICAL 死正则）

根因：**无执法**。CI 没有 dead-code 检查（vulture/`pyright: reportUnusedFunction` 全仓关闭式标注散布），删除恐惧（"以后可能用"）+ 直测死函数的自证测试（F793 点名的 F727/F730 模式，C14 簇）使死面只进不出。

## 目标
1. 43 处每处一裁决：**接线**（移交对应簇 spec）/ **删除**（本 spec 执行）/ **显式 deferred**（登记理由与复活条件），零"无主"残留
2. 假防线优先：A 类全部消除（要么真接线要么删声称）
3. CI 引入 dead-code 执法（vulture 白名单制），防回归

## 任务分解
### R0 · 分桶裁决表（先于一切动作）
- 产出 `docs/superpowers/audit-runs/2026-08-15/c37-triage.md`：43 条 × 三桶（wire→认领簇 spec 编号 / delete→本 spec / defer→理由）。裁决规则：对应簇 spec 已存在的机制面交其认领（快照→#26/C19；truth 写→C3；helper→C7；性能缓存→C28 R2；`_verify_truth_integrity`→C30 R2；`chapter_summary` 死字段→C28）；无认领且近三轮无引用者删；有明确设计意图但无预算者 defer（≤5 条）
- **验收**：表覆盖 43/43；每条有桶归属与执行者

### R1 · A 类假防线清除（优先）
- error_guidance/recovery（F108/F109）：整模块删除或最小接线（若 dispatcher 想要错误指引则接线+修 doc_url；默认删）；F903：G0.13 承诺从文档删除或恢复 enforcement；F378/F886：注释/文档改为真实描述，genesis-context 零消费问题移交 C30/C1 裁决（其内容断流是产品缺陷不只是卫生）
- **验收**：`git grep -l "error_guidance" -- src/ docs/` 结果与裁决一致；声称"consumed/caller"的注释与真实调用图一致（抽查 5 处）

### R2 · B 类批量删除/合并（按 R0 表执行）
- 死模块/死表/死参数/死常量/死导出按表删（预计 ≥30 条落此桶）；F427 三 checker 合一；F110/F243/F512/F118 等散点同 PR 批量清；T1506 legacy.py 改名 + shim 删除；T1612 死缓存删除（C28 R2 不修它）
- 每删一处同步删除其直测（C14 协同：死函数的自证测试不许存活）
- **验收**：`just check` 全绿；vulture 基线清零（见 R3）；删除清单与 R0 表一一对应

### R3 · CI dead-code 执法
- vulture（置信度 ≥80 + 白名单文件）或 basedpyright reportUnusedFunction 定向开启入 ci.yml；白名单=显式 deferred 项 + 公共 API 面；`just check` 同步（C25 合写面）
- **验收**：新增一个零调用函数 → CI FAIL；白名单内项 → PASS

### R4 · 直测死函数治理移交
- F793 系统化的"死函数被直测"模式移交 C14（弱断言簇）批量处置：删除伴随死代码删除而自动消失，其余自证壳改真实行为断言
- **验收**：C14 spec 验收含"直测对象全部为生产可达路径"

## 验收（簇级）
- `just check` 全绿（含新 dead-code 门）；R0 表 43/43 关闭；C37 全部成员 merged-into F108 回写
- 删除后 `uv run pytest -n auto` 无 skip 增量（死测试随删）

## 风险
- **最大风险：删掉别簇要接线的面**——R0 表是硬闸，未经表认领的删除禁止合入；快照/compact/truth-index 面在 #26/C19/C3 裁决前冻结
- A 类中 F886 不是删了完事——genesis 种子断流是内容缺陷，删除只清"假输出"，内容恢复移交产品裁决（尾注移交，不在本簇范围）
- vulture 误报公共 API——白名单评审与 deferred 项季度复核（写进 R3 白名单文件头）

## 验证命令
- 分桶覆盖：`python3 -c "import re,pathlib; t=pathlib.Path('docs/superpowers/audit-runs/2026-08-15/c37-triage.md').read_text(); print(len(re.findall(r'^\|', t))-2)"`（=43）
- 假防线抽查：`git grep -n "error_guidance\|Consumed by CLI" -- src/ docs/` 与裁决一致
- dead-code 门：`uv run vulture src/shenbi --min-confidence 80`（基线清零，白名单外）
- 负例：新增零调用函数 → `just check` FAIL
- 直测随删：`uv run pytest -n auto -q` 无 skip 增量
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F108 <- F109-F110, F118, F226, F230, F243, F313-F316, F319, F321, F325, F343, F345-F346, F356, F366, F368, F378, F427, F471, F512, F611, F622, F631-F636, F641-F642, F706, F793, F886, F903, F1027, T301, T1506, T1605, T1612`
- 冻结面注记：快照三件套（#26/C19）、truth upsert 原语（C3）、drift baseline（C7）、genre-config 缓存（C28 R2 已声明不修 T1612 而删）——R0 表中对应行标"wire→认领簇"不计删除桶
