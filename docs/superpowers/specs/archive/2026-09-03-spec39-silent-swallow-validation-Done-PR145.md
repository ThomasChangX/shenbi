> **Date:** 2026-08-16 | **Status:** Done (PR #145, Revised 2026-09-03) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C13，原 35 条 → 现存 30 条 active）| **代表 finding:** F535 | **严重度上限:** P1（F535/F708/F709/F133/F132）| **涉及文件面:** gates/（g4 generic、g7_trace、g5、g6_checks）、scoring.py（数值域）、contracts/（paths、fields）、records/（parser、drift）、dispatcher/（executor、modes）、audit/write_audit、orchestration/escalation_bridge、skill_utils/（style_learning/compute_stats、escalation/check）、各 g4 子 checker 校验完备性

# 静默吞错与部分校验面修复（audit-silent-swallow-partial-validation）

## 修订记录（2026-09-03 · SDD #39 阶段 3 审查后）

- **剔除 4 条已修**（价值门驳斥复核实证，main 已含等效修复）：F103（scoring G3 except-pass 已被 spec #38/PR #142 的 run_subprocess_json 守卫取代）、F637（`is not True` 严格判定已由 spec #13/PR #74 落地于 g0_config_coherence.py:123-125）、F624（双计数已由 spec #27/PR #107 删除）、F233 主面（extract_h2_sections 已 first-wins 显式，残余"重复 H2 无 WARN"保留在本 spec T3）。
- **追加剔除 F522**（plan 审查 R1 复核，2026-09-03）：全仓 structlog 调用零 `extra=` kwarg（grep 实证）；truth_index.py 的 `extra=` 是 IndexEntry dataclass 字段非日志调用；cost/estimate.py:61,79 是 stdlib logging 的合法 `extra=` 用法（字段平铺进 record，载荷不丢）——原指控形态（载荷丢失/嵌套）在 main 上不存在，F522 判已修/不适用剔除。
- **行号/路径重钉**：F507→`src/shenbi/audit/write_audit.py:36`；F513→`src/shenbi/orchestration/escalation_bridge.py:20`；F749→`src/shenbi/gates/g4/chapter_drafting.py:42-50`（修复对象是 src 检查器，非 ledger 所记测试文件）；F610→`src/shenbi/skill_utils/style_learning/compute_stats.py:363-370`。
- **部分存活收窄**：F133（分值域已 REJECT >100，残余 = 负权重静默路径）；F218（.raw 中间文件无清理残余，原"随 C12 T2"委托方 #38 已归档未覆盖 → 收归本 spec T3）；F219（internal.py:22-24 报错指引引用从不读取的 SHENBI_LLM_API_KEY → 收归本 spec T3）；F607（first-wins 已定且注记 F658，残余 = 静默无 WARN）。
- **F116 权界定界**：本 spec 只做「含逗号路径 fail-fast」（见 T3），协议层重设计（JSON 数组/重复 flag）归 C34（spec #48）所有——避免双头修复。C34 滞后不阻塞本 spec。

## 背景

与 C12（裸崩面）互补的另一半边界：错误不崩但被静默吞掉、校验只做部分面——错误降级为静默的错误结果，绿灯与正确性脱钩。五类证据（30 条 active）：

1. **门禁失败被吞（P1 核心）**：F535（G7 _read_only_events 遇中段坏行静默 break 截断事件列表——插入非法 JSON 行后链校验只跑前缀即 PASS，防篡改门可绕过，verified）；F507（audit/write_audit.py:36 裸 except Exception 吞错 return []）；F708（g5.py:151 正则仅 1 个捕获组、:157 m.group(2) 必然 IndexError 被 :169 except 吞 → G5.3 数值一致性检测整段死代码，测试 pin 而不修，P1）；F709（g6_checks.py:68 future_knowledge 守卫数学上不可达——intro_map 首见赋值后 cn 只增，`intro_map[re_ent] > cn` 恒假，测试 pin，P1）。
2. **假值与数值域**：F133（零/负权重静默路径——scoring.py:62 `weight=int(cells[2])` 允许负值，:216-225 仅守 total_weight==0，负权重膨胀 final_score，实测 120 分判 PASS 的残余面）；F132（NaN/bool 穿透 validate——scoring.py:204-208 isinstance 不排 bool、NaN 过双比较 False 穿透，非 RFC JSON 落盘）。
3. **解析器部分校验/静默覆盖**：F217（dispatcher/executor.py:80-81/:116-117 对 ContractError 静默回退 file_type→"chapter"、inputs→[]，绕过契约错误）；F116（G2/G4 逗号拼接文件列表协议，路径含逗号即错位——消费方 gates/cli.py:93,120、phase_runner.py:257,260；生产方 executor.py:131、scoring.py:390、dispatch_helper.py:2699、phase_runner.py:257,260）；F207/F208/F209/F228（contracts/paths.py:103-121 family 占位符缺值静默回退 chapter 语义/`count=1` 后第二个占位符取章值/:143 NNN 项无界 str.replace/anchor 语义丢失——路径解析部分匹配静默错向）；F367（pipeline/genesis.py:375 skills_done 非幂等 append，REJECT 重做后重复记录）；F606（records/drift.py:113-124 只遍历 md_rows 的单向检测，YAML 有而 md 缺的 id 永不报告）；F607（drift.py:82 重复 id first-wins 静默无披露）；F623（records/parser.py:48 静默丢非 dict 元素，无 WARN/计数）。
4. **checker 只验表面**：F420（g4/review_arc_payoff.py:34 子地板检查只验 "15" 字样出现，违规地板仍 PASS）；F421（g4/character_design.py:68-70/:179 同目标同时 PASS check 与 must_fix 失败——矛盾审计记录）；F422（review_arc_payoff.py:102、review_resonance.py:121 证据正则 `:\d+` 可被时间戳满足）；F430（g4/genre_config.py:29 仅校验 fps[0]，其余文件静默忽略）；F405（g4/generic.py:189-191 否定过滤用首个出现位置，双向误判）；F410（g7_trace.py:22-29 坏行 break 无 WARN、无行数对账，尾部截断不可检测）；F749（chapter_drafting.py:42-50 hook_fulfillment 扫全 plan 文本而非 docstring 声称的 Section 7）；F610（compute_stats.py:363-370 read_chapters 两处裸 except 吞读错误）；F513（escalation_bridge.py:20 `val > 0` 丢 0 分）。
5. **杂项静默**：F381（orchestration/escalation_bridge.py:31 volume_objective_met 缺省 True 吞掉，skill_utils/escalation/check.py:56 默认值/:88 判定 未知即 True，无显式 SKIP 标注）；F137（scoring.py:119/:128 applicability 缺格默认 Yes fail-open）；T305（contracts/fields.py filter_to_fields 非 md/json 扩展静默直通不过滤）。

## 修复目标

1. 零"吞门禁"：门禁/审计链路上的 except Exception 一律要么窄化异常类型、要么转化为结构化 FAIL/WARN + 日志——`except Exception: pass/return []/continue` 在 gates/scoring/audit 路径绝迹。
2. 校验语义完备：数值合法域（权重>0 且有限、分数有限非 bool）前置校验；checker 验证语义而非字样。
3. 解析器部分匹配/静默覆盖全部改为显式错误或 WARN + 披露计数。

## 任务分解

- **T1 · 吞门禁清剿（F535/F507/F708/F709/F610）**：G7 坏行不 break（跳过 + 记 tamper 候选 + 跳过行数披露，链校验对截断敏感）；write_audit 吞错改窄化 + WARN + 计数；g5 正则捕获组根因修复（单位组改捕获组）解 pin 测试；future_knowledge 守卫逻辑修正（按章号排序两遍扫描或在读入时维护 intro 章节，使"知道未来章节引入的实体"可检出）并解 pin；read_chapters 吞错改 WARN + 跳过计数。防复发：ruff BLE001/blind-except 规则接入 CI（per-file-ignores 白名单显式列出豁免点）。
- **T2 · 数值域（F133/F132）**：权重合法域（w>0；total_weight≠100 时负权重参与即 FAIL 而非 WARN 后照算）；NaN/inf 在 validate_scores 拒绝（math.isfinite）；bool 显式排除（isinstance(x, bool) 先拒）。
- **T3 · 路径/字段/协议解析完备（F207/F208/F209/F228/F116/F217/F367/F607/F623 + F233 残余 + F218/F219）**：family 占位符缺值显式错误（不回退 chapter）；第二 family 占位符显式错误；replace 改有界/精确替换；anchor 分支不丢语义（AC-NNN 与 family 各自替换后再走 chapter 语义）；**F116 fail-fast**：所有 `,`.join 门禁文件列表的**生产点**统一前置校验（路径含逗号 → 显式错误）——生产点清单：dispatcher/executor.py:131、scoring.py:390、pipeline/dispatch_helper.py:2699、phase_runner.py:257/260（phase_runner 兼生产与消费）；实现收敛为一个共享校验 helper（如 `validate_file_list()`），协议迁移归 C34/#48，本 spec 不改协议；ContractError 不静默回退（fail-fast 或显式降级注记日志）；skills_done 改 set 语义；drift 重复 id WARN+first-wins（与 F658 决策兼容，不改语义只补披露）；parser 非 dict 元素 WARN + 丢弃计数；重复 H2 补 WARN（F233 残余）；F218 .raw 中间文件读后清理（finally unlink）；F219 internal.py 报错指引改指向实际可用入口（detect_mode 语义）。
- **T4 · checker 语义化（F420/F421/F422/F430/F405/F410/F749/F513/F606）**：子地板解析数值（提取分值与地板比较，非字样匹配）；PASS check 与 must_fix 同目标互斥（矛盾记录消除）；证据格式锚定（排除时间戳形态：行首/锚点上下文要求）；genre_config 全文件遍历；否定过滤全位置扫描；G7 坏行 WARN + 与文件总行数对账披露；hook_fulfillment 扫描范围对齐 Section 7（解析 Section 7 边界后扫描，docstring 同步）；val>=0（0 分保留）；drift 双向检测（md↔YAML 两个方向都报）。
- **T5 · 杂项（F381/F137/T305）**：未知卷目标显式 SKIP 标注（不默认 True）；applicability 缺格 FAIL（fail-closed，存量产物影响先盘点再切换）；未知扩展名 WARN。
- **T6 · 回归集**：每条 P1/P2 用"违规构造样本 → 检出"翻转用例。**G0.9 合规声明**：对抗性违规输入作为测试内联数据写在 test 代码内，**不入 tests/fixtures/**（G0.9 约束 fixtures 目录只放真实产物）；scenario 型测试输入仍引用 `tests/fixtures/` 真实产物。逐条锚点清单（pytest marker `c13_regression`）：F133/F132/F207/F208/F209/F228/F116/F217/F367/F420/F421/F422/F430/F405/F410/F535/F708/F709/F606/F607/F623/F513/F749/F381/F137/T305/F233残余 各 ≥1 用例（F116 断言覆盖全部 4 个生产点），`pytest -m c13_regression` 全绿为验收。任务面实际覆盖 31 项（T1 5 + T2 2 + T3 12 + T4 9 + T5 3，F233 以残余形态计入；F522 剔除后 T4 为 9）。

## 批量清理（纯 M 成员）

- F137/F209/F218/F219/F367/F381/F421/F422/F430/F513/F623/T305 随 T3/T4/T5 批量处置（F218/F219 原委托 C12 T2，#38 已归档未覆盖，残余已收归本 spec T3——跨 spec 交割核销：本 spec 验收 4 含 F218/F219 断言；F522 已剔除见修订记录）。

## 验收标准

1. `git grep -n "except Exception" src/shenbi/gates/ src/shenbi/scoring.py src/shenbi/audit/` 输出中每处有窄化/结构化处理（人工清单核销）+ BLE001 lint 规则在 CI 生效（F507/F535/F610 断言；F103 已修不再重复断言）。
2. 校验完备性回归套件（T6）全绿：`uv run pytest -m c13_regression` ——F133 负权重 120 分构造 → FAIL/REJECT；F420 违规地板样本 → FAIL；F535 插入非法行 → tamper 检出；F708 数值冲突样本 → 守卫生效；F709 未来知识样本 → 检出；F116 含逗号路径 → 显式错误；F217 契约损坏 → 无静默回退。
3. `uv run shenbi-validate G4 <skill> <files>` 对含逗号路径显式报错而非静默错位（F116 fail-fast 断言）。
4. F218 断言：dispatch .raw 中间文件在读后不残留（测试驱动）；F219 断言：internal 模式报错文案不含 SHENBI_LLM_API_KEY 误导。
5. `just check` 全绿。

## 风险与回滚

- 风险：窄化异常可能暴露此前被吞的真实故障使轮次显性失败——预期收紧，配 WARN 过渡；fail-closed（F137）对存量产物影响先盘点再切换；F708/F709 解 pin 测试需同步改断言，防止简单删测试；F116 fail-fast 对存量含逗号路径调用方是行为收紧（此前是静默错位，属纠错非破坏）。
- 回滚：T1 逐点独立提交；lint 规则先 per-file-ignores 白名单过渡；回归套件常驻防回退。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C13（原 35 条；**active 30 条**，剔除 5 条已修）：

F103 F116 F132 F133 F137 F207 F208 F209 F217 F218 F219 F228 F233 F367
F381 F405 F410 F420 F421 F422 F430 F507 F513 F522 F535 F606 F607 F610
F623 F624 F637 F708 F709 F749 T305

剔除：F103（#38 修）、F637（#13 修）、F624（#27 修）、F233 主面（F264 顺带修，WARN 残余留 T3）、F522（plan 审查复核：指控形态在 main 不存在）。
