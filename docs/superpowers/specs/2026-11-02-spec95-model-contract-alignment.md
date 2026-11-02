# Spec #95 · 模型契约对齐与上下文预算（model-contract-alignment）：教对、看全、锚住、别放大

**日期**：2026-11-02（**r1.2 2026-11-02 全量对抗式审计修订**——T2 落地面改 market_params 子键（顶层键红线）、T3 补字符总预算/current_state/blob 快照、T5 改 bundle 粒度、T6 改 reject 作用域对称、R4/R5 数字校正）｜ **系列**：卷二实弹复盘批（regen-vol2 首四束实证） ｜ **状态**：Active（r1.2） ｜ **优先级**：🟠 P1（图例口径；r1 的 🔴 图标与 P1 不符，r1.2 修正）
**依赖**：T3 读面分窗复用 #81 窗口选取语义＋**#85 truth_format.py 解析基座**（Hook ID/表格行/H3 节界三面切片单源——T3 自带临时正则即 M6 第六方言，禁）；T4 反馈文案与 #88 gate-finding 契约衔接；其余独立。**批次时序（r1.1 注记，2026-11-02）：#85 先落 → 本 spec T1-T6 → 束4 验收 → 批次 A 其余**（验收窗内不混入行为保持重构——防接骨数归因污染）
**动机证据**：spec #84 Task 10 束1-3 实弹（2026-11-01/02，novel-xinghuo-vol1 ch37-41）：三束共 **9 次人工介入**（裁决 #02-#09 八条编号＋1 次未编号手工回灌；vol1-ledger「卷二开卷运行」节）；全部派发 `finish_reason=stop`（**零 API 截断**——不是输出上限问题）；dispatch blob 取证（observability/dispatches/00163 等 + blobs/ 逐字 prompt）。

**触及的不变量维度**：情绪节奏（弱关联——T2 卷期热协议参数化，仅 WARN 影子检查，不新增判定判据）；其余为 prompt/预算/反馈层，不改门禁判据与 truth 结构

---

## 0. 根因矩阵（八条，全部 blob/日志级证据——**模型不笨，是被教的、被截的、被放大坏的**）

| # | 故障现象（束1-3 实录） | 表面归因 | **真根因** | 证据锚 |
|---|---|---|---|---|
| R1 | planning 反复输出 `chapter_role: 推进/转折` 斜杠形（3 轮 planning 熔断的共同红项） | 模型不听话 | **SKILL prompt 自己教了斜杠**：枚举呈现为「高潮/兑现 \| 推进/转折 \| 过渡/铺垫」——把「档位分组」写成了「可用值」，模型照抄所见 | chapter-planning system blob（00163 派发）：`合法值：高潮/兑现 | 推进/转折 | 过渡/铺垫` |
| R2 | 每轮 plan 的 defer 行全部缺「至第N卷·KRn」锚（8-10 条 shadow WARN/轮，永不收敛） | 模型不会写 | **锚模板从未进任何 prompt**（0 处）——门禁要求一个模型从未见过的字面格式 | blob grep：`至第N卷·KRn` system=0/user=0；WARN 每轮复现 |
| R3 | planning 冷三连（emotion 平/金句 静/尾拍 温）每束复发 | 模型没品味 | **卷二开卷热协议（T1-1 三件套）只存在于监控侧驱动 prompt**——planning 输入零提及（`热开篇`×0、`倒计时`×1 泛指），卷纲节点文字亦无温度信号；模型按承接节点字面产出低温计划是**理性**行为 | blob grep `热开篇`=0；spec #84 驱动 prompt 门面真相自证（「首四束唯一执法=驱动侧」） |
| R4 | drafting 稳定欠重（2275-2629 字 vs 2800 下限，~50% 尾部失败） | 模型偷懒 | ①**无范例章锚定**：prompt 里没有任何一章完整正文（ch39/40 正文 0 字节），长度只以数字传达（`3200`×2）——flash 档无 few-shot 时锚向「一次回复的自然长度」；②**长文裹 JSON 信封**（`content` 字符串里塞 6400+ 字中文正文+PRE/POST），模型倾向压缩以保 JSON 合法；③字数只在 scene-split **终检**才验——差 26 字也整束熔断重来 | draft41 user blob：113 段无正文范例、Output Format=JSON 信封；字数失败均在 scene-split 阶段发现。**r1.2 补**：drafting/revision 确为 `max_tokens=49152`+`thinking="low"`（executor_config:8-26），但 **settling 无 thinking 覆盖**（:36-42 只有 temperature/max_tokens），走 provider 默认——原表述对 settling 不成立 |
| R5 | settle `content_dropped` 三连败（ch41，每轮丢行数递增） | 模型违反增量契约 | **三重夹击**：①live 文件无界增长（character_matrix 190KB/pending_hooks 113KB/current_state 91KB，+3-5KB/章）把 settle prompt 推到 94-96k tokens；②`_INPUT_MAX_CHARS_PER_FILE=32000` 把 41-45k 字符的 pending_hooks **拦腰截断——被裁掉的尾部正是它要更新的最新钩行**，模型对看不见的行只能重造；③96k 上下文里 120KB 全文件数据在眼前，**数据模仿压倒指令遵循**（增量契约在 system 里写得很对，但模型抄了数据的形） | 增长曲线：ch23=68.6k → ch35=90.1k → ch41=**95.8-97k（95,835/97,000/95,850 三次，r1.2 取区间）** tokens（单调无界）；日志 `input_truncated file=staging/truth/pending_hooks.md kept_len=32000 original_len=41592`（17:01/17:03/17:06 三次 settle 全中）；escalation-41-report：丢行数 1→4/5 递增 |
| R6 | settle 重试越试越糟（反馈放大回路） | — | 失败反馈说「你丢了 X 行」→ 模型的修复策略=**更多地重发整档**→丢更多行。反馈描述了症状没给出**操作路径**（「以 live 行集为基、只 append 新键行」） | 三轮失败的 completion 36k→24k→20k 且 dropped 递增；对比：监控侧把被丢行回植 staging 后一次通过（裁决 #08） |
| R7 | 修订改一处破两处（ch41 工食数字被修后又 canon 漂移） | 模型不稳 | 修订输出=**整章全量重写**（无 diff/场景级模式）——每次修 3 行都要重掷 3400 字全章骰；prompt 仅 12k（无全章上下文却要保全章） | revision prompt 12k/completion 13-21k 全章；ch37 修订成功 ch41 修订漂移=同机制骰运 |
| R8 | 束模式 follower 章无 memo 检查点（ch38/40/42 计划被草写直接消费） | — | 架构缺口：planning 一次产两章计划，memo 检查点只挂头章——人工重写的 follower 计划在检查点前即被管线吞掉（束2/3 各发生一次覆写事故） | 裁决 #05/#07 实录（staged 计划两度被重派冲掉） |

**用户假设裁定**：「每章膨胀的 context 是否压迫输出」——**成立且已量化**（R5 曲线+截断日志）；但 API 层无输出截断（finish_reason 全 stop），压力机制是「截断致盲写」+「长上下文指令遵循衰减」两支，不是预算顶。

## 1. 任务分解

### T1 · 契约同步器：gate 词表 ⇄ prompt 单源（修 R1/R2）
- **先立显式枚举常量（r1.2 前置）**：`CHAPTER_ROLE_VALUES` 等从 regex alternation 提为常量（现 `(高潮|兑现|推进|转折|过渡|铺垫)` 内联在 chapter_planning.py:742；金句位 regex :118 只编码 `燃`）——lint 与 checker 共读同一常量，否则「机器可读清单」无源可抽；
- `tools/lint_gate_prompt_contract.py`（进 `just check`）：对**有枚举的检查**（34 个 `g4_*` 函数中列出清单，非全部）校验对应 SKILL.md 含 **verbatim 模板块**（合法值逐行列出+一个最小正例），禁止手写分组斜杠；
- 修 chapter-planning SKILL.md：枚举改逐行清单（`高潮`/`兑现`/`推进`/`转折`/`过渡`/`铺垫` 各占一行 + 「只许单值」明示）；补 defer 锚模板行 `至第N卷·KRn（N=卷号, n=KR 号，须在 volume_map 在盘）` 与场景钩「声明⊆末行逐字」谓则说明；
- 红测：对现行 SKILL 跑 lint=FAIL（斜杠形+锚缺失），修复后 PASS。

### T2 · 卷期参数下沉：热协议进管线（修 R3）
- **落地面（r1.2 钉死）**：genre-config **顶层键是 12 键闭集**（`contracts/ownership.py:41` GENRE_KEYS；`genre_config.py:165-173` 对未知顶层键直接 ValueError；SKILL.md:341/:434 明文「不得自造顶层键」）——`volume_opening_protocol` 必须挂 **`market_params.volume_opening_protocol` 子键**（`GenreConfig.market_params` 类型允许 `dict[str, dict[...]]`，:53）；**r2.2 复核**：现有 validator **已容忍未知子键**（`genre_config.py` docstring 明示「子键多余不拒」），无需扩白名单；但 `market_params` 值类型限定为**扁平标量**，故须定义 `volume_opening_protocol` 子键 schema（扁平标量）+ SKILL.md 子键文档；若需结构校验则**新增**（非扩）；**若坚持顶层则属 breaking contract**：GENRE_KEYS 12→13 + Pydantic/ownership/SKILL 三源同步 + 四站测试，须用户裁定；
- **注入三处接线（r1.2）**：①contract `reads` 增 genre-config 投影子键（`fields.py:97` 的字段过滤只支持**顶层键**，子键必须走 read extractor）；②chapter-planning 现只读 `chapter_word`、chapter-drafting 只读 `fatigueWords/pacing/chapterTypes`——两 skill 的 reads 都要改；③冷三连影子检查（`emotion_tone∈{平}`+`金句位∈{静}`+尾拍温 同现 → WARN 进台账）作为 **#82 共享冷谓词的更严 WARN 子集**（#82 已定义 `tone∈{悲,惧,平} 且 金句位非燃`），给新 check id 并在 `docs/framework/invariants.md` 维度 8 门检列登记；
- **驱动 prompt 不撤（r1.2）**：T2 未落门级替代前，`docs/regen-vol2-driver-prompt.md:19` 的「唯一执法」条款保留；T2 落地后同批改写该文档，不得让「spec 说已降级、prompt 说唯一执法」双源并存。

### T3 · settle 读面分窗与指令保底（修 R5 上半）
- settle reads 改**分窗**：pending_hooks 只注入「总览表 + active 钩 + 本章触及钩的详情节」（其余节以 `（已归档引用：MHnn…）` 一行带过；规模实测：113,741 字节/14 个 `### MHnn（…）` H3 详情节，2026-11-02）；character_matrix 只注入本章出场角色行+键结构样例；**current_state（91,583 字节）同批纳入分窗（r1.2——R5 列了三处无界源，原 T3 只分前两个）**——窗口选取语义参照 #81 归档窗口先例，**三面切片（钩 ID/表格行/节界）一律 import #85 truth_format.py**（HOOK_ID_RE/split_table_cells/iter_sections(level=3)；自带临时正则=M6 复发，禁）；
- 目标上限：settle prompt 恒 ≤60k tokens——**r1.2 关键**：现无 **settle 专属**上限，真正总闸是 `_INPUT_MAX_CHARS_TOTAL=128000`（dispatch_helper.py:315，注释按英文 4 chars/token 估算 ≈32K，中文实测 ≈95.8k tokens）——须给 settle **独立字符总预算（~75k chars）**并在**组装函数内断言**（不只是测试），窗口后仍超则按钩优先级降级；
- 截断语义保底：`_budgeted_truncate` 后在 user prompt 顶部注入 `【截断告知】以下文件数据不完整（截断清单+缺多少）`——**r1.2：per-file 哨兵已存在（dispatch_helper.py:399/:446/:1220-1225 `[TRUNCATED k/n chars]`）**，本项是升级为顶部汇总块，避免重复实现/双口径；
- **回放源（r1.2）**：不得用 live 路径（staging 已清、live truth 随卷二续跑增长）——从 `observability/dispatches/00189` 的 `reads[*].blob`（内容寻址快照：character_matrix 169KB/pending_hooks 103KB 等）固化为 fixture，断言 60k 预算；tokenizer 估算规则一并钉死。

### T4 · 失败反馈改操作路径（修 R6）
- `content_dropped` 反馈模板改为三段式：①被丢行 verbatim 清单 ②指令「以上行原样保留于输出（作为基底行），仅在其后追加本章新键行」③一个最小正例（live 两行+新一行）；**r1.2 规模控制**：实测丢 4-5 行、每行 100-200 字 ≈1-2KB，可控；清单去重 + 上限 N 行（默认 20）+ 优先列**未出现在截断窗口内**的行（当前反馈只有 `content_dropped:{n}行 e.g. {shown}`——state_settling.py:185）；
- drafting 字数类反馈同理：报「场景 i 差 N 字（现 X/需 ≥Y）+ 建议扩拍位（对白/动作/感官各一）」——禁止只报症状。

### T5 · 草写长度锚定与早检（修 R4）
- drafting prompt 注入**范例章**：上一通过章全文（首章用 fixture 标准章）——`+3.5k tokens` 换长度稳定（成本可忽略）；
- 落盘前**本地早检**：dispatch 输出解析后即数字数（split_bundle+total_chars 已有），低于带即带差值反馈——**r1.2 改粒度**：bundle 模式下一步 dispatch 产双章、无单章 md 输出（chapter_loop.py:179-189 step 4 无 output_path），**主线路=束级早检 + 按章定向反馈 + 整束重派**；「单章重试」需先拆 bundle，列 Phase 2；
- （Phase 2，实测主线路不奏效再拆）双章 bundle 拆两次单章派发——拆后 T5 的单章重试与 T6 的场景级 patch 才自然。

### T6 · 修订 diff 化 + 束检查点补位（修 R7/R8）
- chapter-revision 输出改「场景级替换清单」（`场景n: <全文>` 列表，未列场景不动）——prompt 注入受影响场景定位，不再全章重写；**r1.2 补全契约面**：需确定性 applier + patch 载体 schema（`merge_prose` 目前只是 `contracts/enums.py:43` 的 Literal 枚举、无实现；dispatch_helper:1288-1388 只特判 append_dedup），PRE/POST/场景钩随替换重生成，G2 字数/G4.cd 全章复核顺序写进 plan；先落 SKILL 契约变更再改 prompt；
- **束模式检查点（r1.2 改判）**：R8 归因不准——#72 已把 follower plan 纳入 leader 检查点的 G4（chapter_loop:1625-1633）与 approve 提交（:1753-1763）；真正缺口是 **reject 作用域只含 leader**（cli.py:683-690 vs commit 的 :734-744）——修 `_checkpoint_staging_targets` 与 commit 对称、检查点 artifact/context 明列两章；**不新增第二检查点**（裁决 #03/#07 的事故是「重派覆写人工 plan」，第二检查点发生在覆写之后，救不了）。

## 2. 验收

1. `just check` 含 gate-prompt 契约 lint 且现行 SKILL 全 PASS；
2. **00189 blob 快照回放**（reads[*].blob 固化 fixture，非 live 路径）：settle 组装 prompt ≤60k tokens（**组装函数内断言**，非仅测试）；截断汇总块在截断时必然出现（单测）；
3. 束4（ch43/44）以修复后管线重跑：**≤1 次人工接骨**——**接骨度量（r1.2 定义，r2.2 复核）**＝vol1-ledger「卷二开卷运行」节内人工处理条目（`裁决 #` 块/手工手术记录）＋pipeline escalation 数，评审时按同节逐条重数；**束1-3 账面基线=8 条裁决（#02-#09，其中 #04/#07 为正文引用）＋1 次未编号手工回灌＝9**（全节 `- **裁决` 块头 4 个、唯一编号 8 个——评审以「编号集合＋手工条目」双列核对，不按子串瞎数）；planning 零斜杠形/零锚缺失（shadow WARN 清零或仅剩误报候选）；
4. **束级早检**在 drafting 捕获≥1 次字数失败且整束重派通过（或全绿无失败）；单章重试属 Phase 2（拆 bundle 后）；
5. 单测面：枚举 lint 红测→绿、分窗组装快照（含 current_state 与字符总预算）、反馈模板含 verbatim 行清单、修订 patch schema/applier 校验、reject 作用域含 follower（红测）。

## 3. 不做面（防过度施工）

- 不换模型、不加档（thinking/温度维持现状——先修「教的对、看的全」，模型分档实验只在 T1-T5 达标仍不过验收时另立）；
- 不动门禁判据与 truth 文件结构（#82/#83 域——r1.2 更正：原写 #88/#91，二者分别是 finding 契约与状态并发）；
- 不做全语料 truth 压缩重构（分窗只动 read 面；写面结构归 #82/#83——r1.2 更正：原写 #81/#90，二者是观测与契约数据面）；
- 不提前拆双章 bundle（T5 可选项实测后再议）。

## 4. 与在档 spec 的关系

- 上游实证：spec #84 Task 10 束1-3（vol1-ledger 裁决 #02-#09 为故障台账）；
- 复用：#81 窗口选取语义＋#85 truth_format.py 解析基座（T3 两半）〔r1.1 口径修正：原「#81 归档窗口」产物级复用收窄为窗口语义先例——切片语法基座归 #85〕、#88 finding 契约（T4 反馈格式）；
- 下游：束4 重跑即本 spec 验收场，亦是 #84 Task 10 解冻条件。
