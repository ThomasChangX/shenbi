# Z9 区独立复核报告（review-r2，fresh context）

- 轮次: 2026-08-15 全项目深度审查
- 复核 agent: Z9-review-r2（只读；除本报告文件外未创建/修改/删除任何仓库文件；未 git add/commit；未运行 pytest/shenbi-dispatch/pipeline；novel-output 零接触）
- 输入: zone-reports/Z9-a.md（F901-F919）、Z9-b.md（F934-F950）、Z9-c.md（F967-F975）、Z9-review-r1.md（F951-F957）；findings-ledger.md（本轮 Z9 段 45 条）；zones/Z9{,-a,-b,-c}.files
- 本轮强制新角度（与 r1 引用断链重扫不复用）:
  - **(a) 上轮→本轮 findings 承接映射完备性**——上轮（2026-08-14）台账全部 P0/P1 共 **123 条**（5 P0 + 118 P1，含 D1-01；严格解析 783 行 + D1-01/02/03 = 786 行闭合，复证 Z9-c F969 口径）逐条判定"已承接/未承接/不再适用"
  - **(b) specs/INDEX 活性核对**——INDEX 活跃数 vs specs/ 实况；归档 spec 修复声称 vs thread-reports/T10.md 交叉对账
- 编号段: F976-F999（实际使用 4 条：F976-F979）
- 临时脚本仅写 /tmp/z9r2/（parse_ledger.py / parse2.py / prev_hi.py / map_ids.py / domain_match.py / domain2.py / build_map.py / missed.py，均只读）

---

## 0. 总体结论

1. **承接映射完备率 121/123（98.4%）**：123 条上轮 P0/P1 中，117 条已承接（本轮 finding 复现 / 活跃 spec 登记 / 报告显式引用）或修复消除（12 条，其中 4 条为本轮盘面独立复核证实）；**2 条零承接且盘上复现**（F140、T501）→ 立案 F976/F977（P1×2）；另有 2 条（F1301/F1302）已由 Z11-r2 以 F1177 立案（本轮确认不重复计）。
2. **误报 0 条**：r1 的 7 条（F951-F957）与 c 段 9 条（F967-F975）共 16 条全部独立重证成立（§4）；2 处计数口径注记（不推翻结论）。
3. **specs/INDEX 活性 PASS**：登记 23 = 磁盘 23（+INDEX 自身 24 文件）；归档 101 文件与 Z9-b 机械结论一致；归档 spec 唯一 "Done" 声称（pipeline-never-completes，PR #42）与 T10 §二 9/9 结构核验一致；T1001 行号漂移恶化与 F934 同根因（PR #42 +61 行未回填），跨归档/活跃两域（§2）。
4. **新增基础设施类 finding**：两轮台账 ID 命名空间系统性碰撞（72/123 高危 ID 被本轮复用为不同 finding，F978）；本轮 ledger Z9-c 段 9 行标题列未转录（F979）。
5. **收敛判定：未收敛**（本轮出现新 P1×2，软收敛序列中断；建议定向处置而非全量 r3，见 §7）。

严重度分布（本轮新增）：**P1×2（F976/F977）+ P2×1（F978）+ M×1（F979）**。

---

## 1. 角度 (a)：上轮 P0/P1 → 本轮承接映射（完整表）

### 1.1 方法与机械基础

- 上轮台账解析：容错列解析（标题内未转义管道致列右移）+ 全行严重度单元扫描 → 783 F/T/Z 行 + 3 条 D 前缀行（D1-01 P1、D1-02/D1-03 P2）= **786**，严重度 P0=5/P1=118/P2=496/M=166/F417='—'——与 Z9-c F969、上轮 final-report §5 终值**逐项吻合**。
- 高危集合：5 P0 + 118 P1 = **123 条**（F417 非高危不计；D1-02/D1-03 P2 不计）。
- 判定路径（按序）：① 本轮 ledger/报告/线程对旧 ID 的显式引用（96/123 命中）；② 同域 finding 匹配（标题/关键词对本轮 637 ledger 行）；③ 活跃 spec 登记（#3-#26 的 R 项/P2 清单）；④ T10 修复核验；⑤ 以上皆无 → 盘上复现检查（本轮亲核 8 项：F140/T501/F247/T502/F700/F1303/F3AF/F313）。

### 1.2 判定汇总

| 判定 | 条数 | 说明 |
|---|---|---|
| A. 断链复现（本轮新立） | **2** | F140、T501——零承接 + 盘上复现 → F976/F977 |
| B. 断链（他区已立） | 2 | F1301/F1302 → Z11-r2 F1177（本轮确认，不重复立案） |
| C. 修复消除 | 12 | PR #42 R1-R6/F304/F340/F341 组件 + T10 #1；其中 F247/F524/F313/T502 为**本轮盘面独立复核补充证实**（T10 未单列） |
| D. 不再适用 | 2 | F325（上轮已裁定误报 FP=1）；F700（前提消失：现盘 CHAPTER_STEPS 43 项，step_index=16 在界内） |
| E. 承接-活跃 spec（无独立本轮 finding） | 15 | 以 2026-08-14 审计派生的 23 份活跃 spec 登记为权威承接（含 T1/T14 线程待交付项） |
| F. 承接-本轮 finding | 90 | 同域复现（多数升级/强化，如 F397→F360 P0） |

### 1.3 完整映射表（123 行；"→"右侧为本轮承接证据）

**A. 断链复现（2）**

| 上轮 | 域 | 判定与承接 |
|---|---|---|
| F140 (P1) | d1/Z4 | ❌ 零承接 + 盘上复现（本轮亲核：`scoring.py:282 def main() -> dict` + `pyproject.toml:60 shenbi-score = "shenbi.scoring:main"` → 成功路径 `return result`（:461-462）经 console wrapper `sys.exit(dict)` 退出码 1）→ **F976** |
| T501 (P1) | T5/Z1-Z3 | ❌ 零承接 + 盘上复现（本轮亲核：`dispatch_helper.py:1383-1390 _is_retryable` 仅认 httpx.TimeoutException/HTTPStatusError；:1539 client=OpenAI(...)；`.venv` 实测 openai.APITimeoutError/APIStatusError 均**非** httpx 子类 → retry=retry_if_exception(_is_retryable) 永不重试）→ **F977** |

**B. 断链（Z11-r2 已立 F1177，2）**

| 上轮 | 域 | 判定与承接 |
|---|---|---|
| F1301 (P1) | Z11 | ❌→F1177（56/56 章节头缺失，Z11-r2 实跑复现，本轮沿用其证据未重扫） |
| F1302 (P1) | Z11 | ❌→F1177（META 契约，5 章无 META + ch40 `## META`，同上） |

**C. 修复消除（12；★=本轮盘面独立复核补充证实）**

| 上轮 | 修复证据 |
|---|---|
| F324 (P0) | PR #42 R1 中文卷界（T10 §二 ✅ `_read_cn_volume_boundaries` 等 9 面） |
| F353 | PR #42 R2 `update_total_chapters` 单一写点（T10 ✅） |
| F371 | PR #42 R3 G4 目录参数化 + closure step10 `snapshots/chapter-NNN/`（T10 ✅） |
| F373 | PR #42 R4b 四消费者接线（T10 ✅） |
| F379 | PR #42 R4/R5 PathContext 跨路由（T10 ✅） |
| F304 | PR #42 F304 `except RetryExhaustedError`→ESCALATION（T10 ✅ cli.py:313-325） |
| F340 | PR #42 F340 `_apply_reject_redo`/`_reset_retry_budget`（T10 ✅） |
| F341 | PR #42 F341 `_auto_settle_parallel` 全守卫体镜像（T10 ✅） |
| F247 ★ | PR #42 R4b：本轮亲核 `audit/_shared.py:36-49 derive_output_files(skill, chapter, round_dir, ctx)` 经 `resolve_or_skip_ctx` 解析 N——declared 面 N 不解析缺陷已消除（T10 未单列此条） |
| F524 ★ | PR #42 R4b 组件：derive_output_files 签名现收 chapter/ctx（同上亲核） |
| F313 ★ | PR #42 R5 组件：`closure.py:148-162 _closure_step_context` 6/10→chapter、2→arc、4/5→volume——closure step 6 卷号替章号已修（T10 §二 R5 行） |
| T502 ★ | PR #42 F340 组件 `_reset_retry_budget`（cli.py:524/:565，本轮盘面确认 REJECT 重做路径清零预算；approve 路径未核验，注记） |

**D. 不再适用（2）**

| 上轮 | 依据 |
|---|---|
| F325 | 上轮已裁定误报撤销（台账 FP=1 即此条） |
| F700 | 前提消失：`CHAPTER_STEPS` 现盘 43 项（idx16=linguistic-drift-check 在界内），"越界恒真断言"不成立；残留小疵：测试注释仍标 "# review-resonance"（Z7 域 M 级观察，不立案） |

**E. 承接-活跃 spec 登记（15）**

| 上轮 | spec 承接 | 备注 |
|---|---|---|
| D1-01 | #15 deps-supply-chain（pyproject:17+dev 组 sentence-transformers；Z9-b 复核成立） | T13 输入 |
| T1-01 | #19 decisions-chain | T1 线程待交付 |
| T1-02 | #19 | 同上 |
| T1-03 | #19（`_validate_json_output` 仅语法校验） | Z8-r1/Z2-r3 有交叉引用 |
| T14-01 | #24 tooling-gate-chain（确定性助手零强制） | T14 线程待交付 |
| T14-04 | #21 truth-write-path + #24（write_truth_file 接线面） | F1175 快照实证互补 |
| F216 | #13 config-governance（genre_config.py:94 形态，Z9-b/r1 复核成立） | |
| F303 | #26 snapshot-subsystem-wiring（自 F303 拆分，INDEX #26 内容字段自记） | Z11-b F1153-F1157 邻接 |
| F701 | #18 fixture-authenticity（无效测试簇） | 同属 Z7 F701-F743 属级 |
| F703 | 归 T11 正向结论（"无竞态"）张力项 | 待 G7 复核注记 |
| F754 | #18（8 rubric-only scaffold R 项） | |
| F815 | #18（import-analysis 链断 R 项） | |
| F903 | #23 z8-contract-drift（45 条 P2 清单） | |
| F905 | #23（review-sensitivity 双重调度） | |
| F906 | #23（genre-config 字段级 reads 漂移） | |

**F. 承接-本轮 finding（90）**

| 上轮 | → 本轮承接 | 上轮 | → 本轮承接 |
|---|---|---|---|
| F1300 (P0) | F1101 (P0 verified)+F1175 | F602 | F604（establish_baseline 零调用） |
| F302 (P0) | 部分修复（T10#1 接线 ✅）+残留 F301/F302/F504/F505/F1115 | F612 | F602/F603 族（is_drift 门控链）+spec #11 |
| F364 (P0) | F318 (P1 裁决升)+F1108/F1109 | F620 | F376（DriftEscalationError 生产不可达） |
| F397 (P0) | F360 (P0 verified)+F1104 (P1 同簇) | F637 | F238 (P1)+F362 |
| F0-02/F1212 | F905+F759+F815（5 技能未登记族）+F1033 | F640 | F630 (P0 materialize_progress) |
| F115 | F104 (P1)+F757 (P1)+F137 (M) | F702 | F710/F726 族（GR.2+测试锁死） |
| F158 | F105 (P1) | F750 | F754 (P1 expected-output 证据路径) |
| F163 | F101 (P1) | F751 | F751 (P0 内容级断链) |
| F201 | F224 (P1 verified)+F201/F836（同域族） | F752 | F752 (P1 单 fixture 多角色) |
| F214 | F320 (P2)+F449 (P1) | F753 | F762/F784 邻域+spec #18 |
| F218 | F239 (P2 系统化)+F201/F836 | F755 | F104/F757（=F115 线） |
| F227 | F239 (P2) | F800/T801 | F777 (P1 9 复制体草稿) |
| F235 | F501 (P0 写审计系统性失效簇) | F801 | F778 (P2) |
| F300 | F308 (P1) | F802 | F764(b) (M 多章节身份) |
| F301 | F321+F305+F359（串行不可达族） | F803 | F839/F840/F776 族 |
| F305 承接注 | F305 (P1 并行审计零 G3/G4) | F804 | F751 (P0) |
| F326 | F532+F309（部分修复 F341 后残余） | F806 | F779 (P1 伪造快照) |
| F345 | F305 (P1) | F807 | F756/F776/F788 族（calibration） |
| F354 | F309 (P1) | F811 | F784 (P2 死 fixture) |
| F3AF | F320 (P2，dispatch_helper:1977-1990 伪造 scorer) | F814 | F762+spec #18 |
| F401 | F446+F449/F450（g_reconcile 键空间） | F819 | F751 族+spec #18 |
| F402 | F447 (P2) | F901 | F815 (P1，foreshadowing-lifecycle 写未声明) |
| F404/F458 | F465 (P2)（P2.5 空串双例同族） | F950 | F873 (P1)+F1004 (P1)（DEPRECATED 双面） |
| F408 | F408 (P2，同 ID 同域再现——少数非碰撞复用) | F953 | spec #23（Z9-b 抽验） |
| F432 | F759/F905（根因面：5 技能未登记→G7 不可达） | F1001 | F812 (P1，显式引 "2026-08-14 F1001/R5 未修") |
| F444 | F630+F449/F450 族（G3.x 证据链） | F1002 | F870+F869 (P1×2) |
| F507 | F502 (P0) | F1003 | F869 (P1) |
| F512 | F518+F501 (P0) 族 | F1004 | F873+F1004 |
| F513 | F501 族（快照根错位并入） | F1009 | F1011 (P2 描述非触发式) |
| F601 | F602 (P1) | F1011 | F803 (P1，book-spine-init reads——交叉承接) |
| F1214/T9-01 | F1015/F1016 (P2)+F1027 (M) | F1303 | F1162/F1171（手动路径根因族）+F1102/F237 |
| F1304 | F1102 (P0) | F1305 | F237 (P1，更强：145/5) |
| F1307 | F1152+F815 | F1309 | F1113 (P2) |
| F1310 | F1104 (P1 同簇，显式提及) | F1313 | F1115 (P1) |
| T7-01 | F304 (P1)+F1105+F532 | T7-02 | F238 (P1)+F362 |
| T7-03 | F1110+F318+F1171 | T7-06 | F869/F870/F882 |
| T12-01 | T1206 (P2) | T12-02 | T1201 (P1)/T1206/T1207+spec #22（双轨） |
| T14-03 | F867 (P1) | T201/T302 | F004 (P2)；T302 假阴性面未见独立复现（工具未变，G7 注记） |
| T301 | F224/F201/F836 | T802 | F778 (P2) |
| T803 | F779 (P1) | T804 | F756/F776 族 |
| T805 | F784 (P2) | T806 | F762+spec #18 |
| T807 | F754 (P1) | T808 | F751 (P0) |
| T809 | F839/F840/F776 | Z11-01 | F1102 (P0) |

（表内"同域族"指本轮以集群/强化形式承接；上轮→本轮严重度变化多处为升级，如 F507 P1→F502 P0、F397 P0→F360 P0+F1104 P1 裁决。）

### 1.4 映射完备性结论

- **未承接且盘上复现 = 2 条**（F140/T501）——按 Z11-r2 F1177 先例立案（F976/F977），且两者均为 P1 断链复现（§8.1 表 P1 行字面命中）。
- 映射的**基础设施风险**：72/123（59%）上轮高危 ID 被本轮台账复用为**不同** finding（如 prev F115 评分维度 no-op vs 本轮 F115 rglob 回退；prev F1001 drift-guidance vs 本轮 F1001 ci.yml）——裸 ID 跨轮检索会产生系统性假阳性（本轮映射初版 78/123 "已承接" 中约 50 条为碰撞假象，经域匹配人工校正）→ F978。
- Z9-c §4 的 16 组映射经本轮系统化验证**全部成立**，无修正。

---

## 2. 角度 (b)：specs/INDEX 活性核对 + 归档修复声称 vs T10 交叉对账

| 项 | 结果 | 验证 |
|---|---|---|
| INDEX "活跃 spec 数：23" vs specs/ 实况 | **PASS** | `ls specs/*.md` = 24 文件 = 23 spec + INDEX.md 自身 |
| INDEX ↔ 磁盘双向闭合 | **PASS**（r1 已证，本轮复核计数一致） | 23=23，差集空 |
| 归档规模 | 101 文件（顶层 92 + `2026-06-15-p-1.e-foundation-completion/` 内 9） | `find archive -type f` = 101——Z9-b 机械结论精确成立 |
| INDEX 编号引用活性 | 仅 #6 不可解析（F936 已立）；#39/#40 为 PR 号；#3-#5/#7-#26 全部活跃 | grep 全 INDEX |
| 归档 "Done" 声称 vs T10 | **一致**：唯一 Done 状态归档 spec（2026-08-14-pipeline-never-completes，PR #42）的 R1-R6+F340/F341/F304 与 T10 §二 9/9 结构面核验吻合 | T10.md §二 |
| 行为级声称（"post-merge just check EXIT=0 2887+4 passed 85.34%"） | T10 §五.2 已披露不可静态核验（本轮无新增证据，不立案） | — |
| T1001 行号漂移 | 恶化（+22→+43）与 **F934（活跃 spec 漂移）同根因**：PR #42 对 dispatch_helper.py +61 行后归档/活跃两域 spec 均未回填 | T10.md §四 |
| T1002/T1003 | 闭环/勘误与 Z9-b/Z9-c 无冲突 | T10.md |
| 22 条声称清单完备性 | **PASS**：上轮 artifacts（final-report/progress/meta-audit）全量 grep 修复声称语，无第 23 条遗漏（仅 2 处行文性提及） | grep 输出见 /tmp/z9r2 |

结论：角度 (b) 未发现 INDEX 活性缺口或修复声称-核验矛盾；T1001+F934 构成跨归档/活跃的同一漂移根因族，建议统一以符号引用（函数/常量名）替换 file:line 后一并回填。

---

## 3. 漏报（F976-F979）

### F976 | 上轮 F140（P1）断链复现：shenbi-score 成功路径恒 exit 1 | error | P1
- 证据: `src/shenbi/scoring.py:282` `def main() -> dict[str, Any]:`；`:461-462` `emit_json(result); return result`（成功路径无 sys.exit(0)）；`pyproject.toml:60` `shenbi-score = "shenbi.scoring:main"`——console script wrapper 执行 `sys.exit(main())`，非 int 对象 → stderr 打印 dict + **退出码 1**
- 根因: 上轮 F140（P1）立案后未修复、本轮零承接（全 corpus grep "F140"/"shenbi-score" + Z4/phase1 exit-code 相关行核对——本轮 F463 覆盖 marker exit 3、F435 覆盖假 FAIL，均非此面）
- 验证: `grep -n "def main\|sys.exit\|return result" src/shenbi/scoring.py` → 282/293/313/360/377/432/461-462；成功路径唯一出口 = return dict
- 影响面: `shenbi-score`（AGENTS.md 权威入口）每次成功评分退出码 1——调用方按退出码判失败；command-to-give.md 声称的 0/1/2/3 四态语义中 0 态不可达（`python -m shenbi.scoring` 直跑不受影响，属入口差异掩蔽）
- 建议方向: main 末尾 `sys.exit(0)`（或 entry 包一层 int 退出码）；补 Z4 属主确认 + 上轮 F140 承接登记
- 定级依据: §8.1 "上轮 P1 findings 断链复现" 字面命中

### F977 | 上轮 T501（P1）断链复现：tenacity 重试层对 openai SDK 异常永不触发 | error | P1
- 证据: `src/shenbi/pipeline/dispatch_helper.py:1383-1390` `_is_retryable` 仅 `isinstance(httpx.TimeoutException)` / `isinstance(httpx.HTTPStatusError)` 两分支；`:1457 retry=retry_if_exception(_is_retryable)` 装饰 `_call_llm_streaming_with_retry`；`:1539 client = OpenAI(`；`.venv` 实测 `issubclass(openni.APITimeoutError, httpx.TimeoutException)` = **False**、`issubclass(openai.APIStatusError, httpx.HTTPStatusError)` = **False**
- 根因: 上轮 T501（P1）未修复、本轮零承接（全 corpus "_is_retryable" 0 命中；F1116"重试无反馈变化"为计量面、T13 为供应链面，均非此面）
- 验证: 上述 grep + python issubclass 复算（只读 import，无仓库写入）
- 影响面: API 路径 429/5xx/timeout 零重试（`stop_after_attempt(3)` 形同虚设）——生产长跑 pipeline 的瞬态失败直接冒泡
- 建议方向: `_is_retryable` 增加 openai.APIConnectionError/APIStatusError(status in set) 分支（或捕 openai.RateLimitError 等）；转 Z1-Z3 属主；上轮 T501 承接登记
- 定级依据: 同 F976（上轮 P1 断链复现）

### F978 | 两轮审计台账 ID 命名空间系统性碰撞：72/123 上轮 P0/P1 ID 被本轮复用为不同 finding | error | P2
- 证据: 程序化比对（/tmp/z9r2/map_stage1.json）：72 个上轮高危 ID 在本轮 ledger 同号存在而内容不同（例：prev F115=评分维度过滤 no-op vs 本轮 F115=rglob 回退；prev F1001=drift-guidance 契约 vs 本轮 F1001=ci.yml；prev F901=foreshadowing writes vs 本轮 F901=command-to-give 断链）；两轮均按区段分配号段且区构成漂移（上轮 Z8=skills 契约 vs 本轮 Z10=同域），碰撞为结构性而非偶然
- 根因: 审计 prompt 沿用同一号段方案跨轮复用，无代际前缀；r1 F956 已立 F8/F9/F10 跨代复用（M），本条为其在两大台账间的扩大实例
- 验证: `python3 /tmp/z9r2/build_map.py`（same_id_row 路径计数 72）；抽样双行标题对照（§1.3 表 F 组多行注"碰撞"）
- 影响面: 跨轮承接核查/聚类/G7 检索按裸 ID grep 会命中错误行——本轮映射初版即产生 ~50 条假"已承接"；未来轮次与工具化对账同险
- 建议方向: 台账 ID 加轮次前缀（如 `R2-F140`）或本轮 ledger 头部声明"ID 仅本轮内唯一，跨轮引用须带 audit-run 日期限定"；阶段 4 聚类输入生成时统一限定

### F979 | 本轮 findings-ledger Z9-c 段 9 行（F967-F975）标题列未转录（title=ID 占位） | error | M
- 证据: `findings-ledger.md:480-488`——`| F967 | F967 | error | P2 | 见 Z9-c | …` 9 行标题列均为自身 ID；全 ledger 扫描 title==ID 共恰此 9 行（其余 628 行正常）
- 根因: progress 续10 修复"Z9-a 19 条整体漏转录"时的批量补录脚本对 Z9-c 段填充了占位符未回填（与上轮 F972 补录行缺陷同族）
- 验证: `python3 -c`（title==ID 扫描，见 /tmp/z9r2 会话输出：9 行，行号 480-488）
- 影响面: G5 机械统计/聚类按标题去重与检索时该 9 条不可辨识（内容需回 Z9-c.md 查）
- 建议方向: 从 Z9-c.md §1 表回填 9 行标题列

---

## 4. 误报/事实修正（复读 r1 的 7 条 + c 段 9 条）

**整条误报：0 条。16/16 独立重证成立。**

| ID | 重证命令/结果 |
|---|---|
| F951 | `head -1 command-to-give.md` → 引 `plans/2026-06-11-test-framework.md`；ls → No such file；archive/ 命中 ✓ |
| F952 | `find . -name validate-gate.py`（排 .git）→ 0；`phase_runner.py/scoring.py` 存在 ✓ |
| F953 | `sed -n 26,29p` → 节头后直接下一节头 ✓ |
| F954 | INDEX:23 "63 个…2026-06 ~ 07…#1–#19" vs `ls archive \| cut -c1-7 \| uniq -c` → 30/33/5 ✓ |
| F955 | design spec :226 `audit-runs/2026-08-13/`；磁盘仅 2026-08-14/2026-08-15 ✓ |
| F956 | spec:62 自有 `[F10]` 编号；上轮 ledger `^\| F10 ` → 0 ✓ |
| F957 | `CODESPAN_PATTERN = re.compile(r"\`([.\w][\w./-]*\.\w+)\`")` + 白名单 8 文档原文在盘 ✓ |
| F967 | INDEX:4 "已归档 66"/:23 "63" vs `ls archive \| wc -l` = 68 ✓ |
| F968 | 独立脚本（窄口径 `specs/YYYY-MM-DD-*.md`）→ 23 distinct 全 DRIFT（basename 命中 archive/）、**0 TRUE-DEAD** ✓ |
| F969 | final-report:28 "781（655…）" vs :57 "786" + 本轮台账机械计数 786 ✓ |
| F970 | 修正解析（report 列 fullmatch + 剥离 `#anchor`）→ `zone-reports/Z7.md`/`Z8.md` 引用行 **1008 行**、目标不存在 ✓ |
| F971 | coverage.xml line-rate="0.8728"（head 截断复核）vs final-report:15 "85.16%" ✓ |
| F972 | F514 行 10 列、F417 严重度 '—' ✓ |
| F973 | zones 并集 2755 vs table-A 2738（sort -u 复算）✓ |
| F974 | 63 全未勾/2 混合/0 全勾/3 无框 ✓ |
| F975 | Z9-c.files 233 行 vs `find 2026-08-14 -type f` = 165 ✓ |

**事实修正注记（2 处，不动摇结论）**：
1. **F968 计数口径**：c 段报 "34 distinct/32 DRIFT/2 OK-orig"，本轮窄口径（仅 `specs/` 前缀 .md 引用）得 "23/23/0"。差异为引用提取正则的涵盖面（c 含非 `specs/` 前缀形态），两口径核心结论一致（批量漂移、**0 真死链**）。建议台账引用时注明口径。
2. **F970 复核方法警示**：coverage-ledger 报告列大量形如 `zone-reports/Z9.md#AGENTS.md` 的锚点后缀——按子串解析会产生全量假缺失（本轮初版脚本即如此，~2000 假告警）；须 fullmatch+剥离 anchor。c 段原结论（恰 Z7.md/Z8.md 两目标缺失）经修正解析精确复现。

---

## 5. 覆盖空洞

1. **线程未交付依赖**：本轮 T1-T9/T14-T16 线程 pending（仅 T10-T13 在盘）——§1.3-E 组 15 条"承接-specced"中 T1-01/02/03、T14-01/04 等 6 条的终局承接须待线程轮复核；若线程轮漏跑即为新断链（移交协调者排程校验）。
2. **域匹配判定面**：123 条中 27 条经关键词域匹配 + 抽验锚定（非逐条打开源码复核）；其中 8 条本轮亲核盘面（§1.3-C/D 标 ★ 与 A 组）。残余风险：同域不同 facet 的错配（已在表内以"族"标注缓解）。
3. **novel-output 依赖披露**：F1301/F1302/F1303 的盘上状态沿用 Z11-r2 实证（其扫描为全树机械+人工裁决），本轮未重扫（novel-output 只读红线 + 避免重复额度）。
4. **F976/F977 属主归属**：两缺陷实体在 Z4（scoring CLI）与 Z1-Z3（dispatch 重试）域，本轮以 Z9 承接映射角度立案；实体级复核（如评分退出码对 CI 的影响面、重试缺失的生产日志证据）应由属主区/线程认领。

---

## 6. 严重度异议表

**无升级/降级异议。** 本轮复核的 45+16 条全部维持原级。边界说明：
- F976/F977 定 **P1**：§8.1 "上轮 P1 findings 断链复现" 字面命中（两者的底层缺陷本身亦为上轮 P1 级：文档化退出码契约违反 / 生产重试面死亡）。
- F978 定 **P2**：承接映射基础设施缺口（§8.1 P2 行"承接映射缺口"命中）；虽本轮实操中造成 ~50 条假阳性映射，但可由人工校正兜底，未污染最终台账。
- F979 定 **M**：台账 9 行转录占位，内容在 Z9-c.md 完整在案（文案级缺失，无语义损失）。
- F903/F902 维持 P1（沿用 r1 §5 判定理由，本轮无新证据推翻）。

---

## 7. 收敛判定

- **轮次计数**: 初审三段 45 条 → r1 +7（P2×4 + M×3，零误报）→ **r2 +4（P1×2 + P2×1 + M×1，零误报）**。
- **硬收敛标准**（连续复核零新 finding）: 未达——r1/r2 均有新产出。
- **软收敛标准**（连续轮 ≤3 且无新 P0/P1）: **序列中断**——r2 出现新 P1×2（F976/F977）。Z9 当前状态：**未收敛**。
- **处置建议**（定向，无需全量 r3）：
  1. F976-F979 落账（F979 可由协调者直接回填标题列）；
  2. F976/F977 转交 Z4/Z1-Z3 属主做实体确认（各一条 grep 级验证即可闭合）；
  3. F978 并入阶段 4 聚类输入规范（跨轮 ID 限定）；
  4. 完成后 Z9 可判软收敛（本轮两大强制角度——承接映射与 INDEX 活性——的发现面已穷尽：123/123 判定完毕、INDEX 双向闭合、22 条声称对账完毕）。

---

## 8. 只读声明

除本报告文件外未创建/修改/删除任何仓库文件；全部脚本与中间产物仅写 /tmp/z9r2/；novel-output 零接触（未调用任何 resolve/normalize 类函数——涉及盘面核验均为 grep/sed/python 只读解析 + `.venv` import 检查（openai/httpx 类层次，无副作用））；未执行 pytest/shenbi-dispatch/pipeline/git 写操作。
