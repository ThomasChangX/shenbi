> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C13，35 条）| **代表 finding:** F103 | **严重度上限:** P1（F103/F535/F637/F708/F709）| **涉及文件面:** scoring.py（G3 集成）、gates/（g4 generic、g7_trace、g5、g6_checks）、contracts/（paths、executor）、records/（parser、drift）、dispatcher/、write_audit、escalation_bridge、trace/materialize、style_learning/compute_stats、各 g4 子 checker 校验完备性

# 静默吞错与部分校验面修复（audit-silent-swallow-partial-validation）

## 背景

与 C12（裸崩面）互补的另一半边界：错误不崩但被静默吞掉、校验只做部分面——错误降级为静默的错误结果，绿灯与正确性脱钩。五类证据：

1. **门禁失败被吞（P1 核心）**：F103（scoring T1 G3 集成 `except Exception: pass` 静默吞掉门禁失败——门禁可被静默跳过，verified）；F535（G7 _read_only_events 遇中段坏行静默 break 截断事件列表——非法 JSON 行插入可绕过防篡改门，verified）；F507（write_audit 裸 except Exception 吞错）；F708（g5.py m.group(2) 必然 IndexError 被 except 吞 → G5.3 数值一致性检测整段死代码，测试 pin 而不修，P1）；F709（g6_checks future_knowledge 守卫数学上不可达——intro_map[ent] > cn 恒假，测试 pin，P1）。
2. **假值绕过校验**：F637（Rule 1 临界维度禁用可被非-False 假值绕过：0/"false"/None——需 `is False` 判定，P1）；F133（零/负权重静默路径——实测 final_score=120 判 PASS excellent）；F132（NaN/bool 穿透 validate——NaN 输出非 RFC JSON）；F202 关联面归 C9。
3. **解析器部分校验/静默覆盖**：F233（fields 解析器对重复 H2 静默覆盖，只留最后一个同名节）；F217（executor 对 ContractError 静默回退 file_type→"chapter"、inputs→[]，绕过契约错误）；F116（G2/G4 逗号拼接文件列表协议，路径含逗号即错位）；F207/F208/F209/F228（paths.py family 占位符回退 chapter 语义/第二占位符取 chapter 值/无界 replace/anchor 丢失——路径解析部分匹配静默错向）；F367（genesis.skills_done 非幂等 append，REJECT 重做后 18 条记录）；F606/F607（records/drift 单向检测 + 重复 id 静默覆盖）；F623（_parse_body 静默丢非 dict 元素）；F624（subagent_completion_count 双计数）。
4. **checker 只验表面**：F420（review_arc_payoff 子地板检查只验证 "15" 字样出现，违规地板仍 PASS）；F421（同目标同时 PASS check 与 must_fix 失败——矛盾审计记录）；F422（证据正则 `:\d+` 可被时间戳满足）；F430（genre_config checker 仅校验 fps[0]，其余文件静默忽略）；F405（g4 generic clean 检查否定过滤用首个出现位置，双向误判）；F410（g7_trace 无法检测尾部截断，撕裂行静默停止）；F749（hook_fulfillment 扫全 plan 文本而非 Section 7，docstring 与实现漂移）；F610（read_chapters 裸 except Exception 吞读错误）；F513（escalation_bridge val>0 丢 0 分）；F522（warn extra= 载荷丢失/嵌套）。
5. **杂项静默**：F381（卷目标未知默认 True 吞掉）；F137（applicability 缺格默认 Yes）；T305（非 md/json 扩展静默直通不过滤）。

## 修复目标

1. 零"吞门禁"：门禁/审计链路上的 except Exception 一律要么窄化异常类型、要么转化为结构化 FAIL + WARN 日志——`except Exception: pass` 在 gates/scoring/write_audit 路径绝迹。
2. 校验语义完备：假值判定用严格判据（is False/is None）；数值合法域（权重>0、有限数）前置校验；checker 验证语义而非字样。
3. 解析器部分匹配/静默覆盖全部改为显式错误或 WARN。

## 任务分解

- **T1 · 吞门禁清剿（F103/F535/F507/F708/F709）**：scoring G3 集成改窄异常 + FAIL 透传；G7 坏行不 break（跳过+记 tamper 候选，计数披露）；write_audit 吞错改 WARN+计数；g5 IndexError 根因修复（正则捕获组）解 pin 测试；future_knowledge 守卫逻辑修正并解 pin。防复发 lint：`git grep -nA1 "except Exception" src/shenbi/gates src/shenbi/scoring.py` 人工清单 + ruff BLE001/blind-except 规则接入 CI。
- **T2 · 假值与数值域（F637/F133/F132）**：禁用判定 `is False`；权重合法域（0<w，重归一化或 FAIL）；NaN/inf 在 validate 拒绝（非 RFC JSON 不落盘）。
- **T3 · 路径/字段解析完备（F207/F208/F209/F228/F233/F116/F217/F367）**：family 占位符缺值显式错误（不回退 chapter）；重复 H2 WARN+保留策略显式；文件列表协议改 JSON 数组或转义分隔符（与 C34 路径契约联动）；ContractError 不静默回退（fail-fast 或显式降级注记）；skills_done 改 set 语义。
- **T4 · checker 语义化（F420/F421/F422/F430/F405/F410/F749/F606/F607/F610/F513/F522）**：违规构造样本驱动的逐 checker 修复（子地板解析数值、矛盾记录互斥、证据格式锚定、全文件遍历、否定过滤全位置、撕裂行 WARN、扫描范围对齐 docstring、drift 双向检测、重复 id 报错、读错误 WARN+跳过计数、val>=0、extra 载荷序列化修正）。
- **T5 · 杂项（F381/F137/T305）**：未知卷目标显式 SKIP 标注；applicability 缺格 FAIL（fail-closed）；未知扩展名 WARN。
- **T6 · 回归集**：每条 P1/P2 用"违规构造样本 → 检出"翻转用例（当前样本 → PASS，修复后 → FAIL），形成校验完备性回归套件。

## 批量清理（纯 M 成员）

- F137/F209/F218/F219/F367/F381/F421/F422/F430/F513/F623/F624/T305 随 T3/T4/T5 批量处置（F218/F219 dispatcher 杂项随 C12 T2 提取器一并）。

## 验收标准

1. `git grep -n "except Exception" src/shenbi/gates/ src/shenbi/scoring.py` 输出中零 `pass` 体（每处有窄化/结构化处理，人工清单核销）（F103 断言）。
2. 校验完备性回归套件（T6）全绿：F133 的 120 分构造样本 → FAIL；F420 违规地板样本 → FAIL；F535 插入非法行 → tamper 检出；F708/F709 构造样本 → 守卫生效。
3. `uv run shenbi-validate G4 <skill> <files>` 对含逗号路径/多文件清单零错位（F116 断言）。
4. `just check` 全绿。

## 风险与回滚

- 风险：窄化异常可能暴露此前被吞的真实故障使轮次显性失败——预期收紧，配 WARN 过渡一周；fail-closed（F137/F381）对存量产物影响先盘点。F708/F709 解 pin 测试需同步改断言，防止简单删测试。
- 回滚：T1 逐点独立提交；lint 规则先 WARN 周期；回归套件常驻防回退。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C13（35 条，代表 F103）：

F103 F116 F132 F133 F137 F207 F208 F209 F217 F218 F219 F228 F233 F367
F381 F405 F410 F420 F421 F422 F430 F507 F513 F522 F535 F606 F607 F610
F623 F624 F637 F708 F709 F749 T305
