# Spec #95 · 模型契约对齐与上下文预算（model-contract-alignment）：教对、看全、锚住、别放大

**日期**：2026-11-02 ｜ **系列**：卷二实弹复盘批（regen-vol2 首四束实证） ｜ **状态**：Active（r1） ｜ **优先级**：🔴 P1
**依赖**：T3 读面分窗可复用 #81 归档层产物；T4 反馈文案与 #88 gate-finding 契约衔接；其余独立
**动机证据**：spec #84 Task 10 束1-3 实弹（2026-11-01/02，novel-xinghuo-vol1 ch37-41）：三束共 **9 次人工接骨**（裁决 #02-#09，vol1-ledger「卷二开卷运行」节）；全部派发 `finish_reason=stop`（**零 API 截断**——不是输出上限问题）；dispatch blob 取证（observability/dispatches/00163 等 + blobs/ 逐字 prompt）。

**触及的不变量维度**：无（prompt/预算/反馈层——不改门禁判据与 truth 结构）

---

## 0. 根因矩阵（八条，全部 blob/日志级证据——**模型不笨，是被教的、被截的、被放大坏的**）

| # | 故障现象（束1-3 实录） | 表面归因 | **真根因** | 证据锚 |
|---|---|---|---|---|
| R1 | planning 反复输出 `chapter_role: 推进/转折` 斜杠形（3 轮 planning 熔断的共同红项） | 模型不听话 | **SKILL prompt 自己教了斜杠**：枚举呈现为「高潮/兑现 \| 推进/转折 \| 过渡/铺垫」——把「档位分组」写成了「可用值」，模型照抄所见 | chapter-planning system blob（00163 派发）：`合法值：高潮/兑现 | 推进/转折 | 过渡/铺垫` |
| R2 | 每轮 plan 的 defer 行全部缺「至第N卷·KRn」锚（8-10 条 shadow WARN/轮，永不收敛） | 模型不会写 | **锚模板从未进任何 prompt**（0 处）——门禁要求一个模型从未见过的字面格式 | blob grep：`至第N卷·KRn` system=0/user=0；WARN 每轮复现 |
| R3 | planning 冷三连（emotion 平/金句 静/尾拍 温）每束复发 | 模型没品味 | **卷二开卷热协议（T1-1 三件套）只存在于监控侧驱动 prompt**——planning 输入零提及（`热开篇`×0、`倒计时`×1 泛指），卷纲节点文字亦无温度信号；模型按承接节点字面产出低温计划是**理性**行为 | blob grep `热开篇`=0；spec #84 驱动 prompt 门面真相自证（「首四束唯一执法=驱动侧」） |
| R4 | drafting 稳定欠重（2275-2629 字 vs 2800 下限，~50% 尾部失败） | 模型偷懒 | ①**无范例章锚定**：prompt 里没有任何一章完整正文（ch39/40 正文 0 字节），长度只以数字传达（`3200`×2）——flash 档无 few-shot 时锚向「一次回复的自然长度」；②**长文裹 JSON 信封**（`content` 字符串里塞 6400+ 字中文正文+PRE/POST），模型倾向压缩以保 JSON 合法；③字数只在 scene-split **终检**才验——差 26 字也整束熔断重来 | draft41 user blob：113 段无正文范例、Output Format=JSON 信封；字数失败均在 scene-split 阶段发现 |
| R5 | settle `content_dropped` 三连败（ch41，每轮丢行数递增） | 模型违反增量契约 | **三重夹击**：①live 文件无界增长（character_matrix 190KB/pending_hooks 113KB/current_state 91KB，+3-5KB/章）把 settle prompt 推到 94-96k tokens；②`_INPUT_MAX_CHARS_PER_FILE=32000` 把 41-45k 字符的 pending_hooks **拦腰截断——被裁掉的尾部正是它要更新的最新钩行**，模型对看不见的行只能重造；③96k 上下文里 120KB 全文件数据在眼前，**数据模仿压倒指令遵循**（增量契约在 system 里写得很对，但模型抄了数据的形） | 增长曲线：ch23=68.6k → ch35=90.1k → ch41=95.8k tokens（单调无界）；日志 `input_truncated file=staging/truth/pending_hooks.md kept_len=32000 original_len=41592`（17:01/17:03/17:06 三次 settle 全中）；escalation-41-report：丢行数 1→4/5 递增 |
| R6 | settle 重试越试越糟（反馈放大回路） | — | 失败反馈说「你丢了 X 行」→ 模型的修复策略=**更多地重发整档**→丢更多行。反馈描述了症状没给出**操作路径**（「以 live 行集为基、只 append 新键行」） | 三轮失败的 completion 36k→24k→20k 且 dropped 递增；对比：监控侧把被丢行回植 staging 后一次通过（裁决 #08） |
| R7 | 修订改一处破两处（ch41 工食数字被修后又 canon 漂移） | 模型不稳 | 修订输出=**整章全量重写**（无 diff/场景级模式）——每次修 3 行都要重掷 3400 字全章骰；prompt 仅 12k（无全章上下文却要保全章） | revision prompt 12k/completion 13-21k 全章；ch37 修订成功 ch41 修订漂移=同机制骰运 |
| R8 | 束模式 follower 章无 memo 检查点（ch38/40/42 计划被草写直接消费） | — | 架构缺口：planning 一次产两章计划，memo 检查点只挂头章——人工重写的 follower 计划在检查点前即被管线吞掉（束2/3 各发生一次覆写事故） | 裁决 #05/#07 实录（staged 计划两度被重派冲掉） |

**用户假设裁定**：「每章膨胀的 context 是否压迫输出」——**成立且已量化**（R5 曲线+截断日志）；但 API 层无输出截断（finish_reason 全 stop），压力机制是「截断致盲写」+「长上下文指令遵循衰减」两支，不是预算顶。

## 1. 任务分解

### T1 · 契约同步器：gate 词表 ⇄ prompt 单源（修 R1/R2）
- `tools/lint_gate_prompt_contract.py`（进 `just check`）：抽取每个 G4 检查的**机器可读合法值清单**（枚举/字面模板——chapter_planning.py 现有 regex/常量为源），校验对应 SKILL.md 含 **verbatim 模板块**（合法值逐行列出+一个最小正例），禁止手写分组斜杠；
- 修 chapter-planning SKILL.md：枚举改逐行清单（`高潮`/`兑现`/`推进`/`转折`/`过渡`/`铺垫` 各占一行 + 「只许单值」明示）；补 defer 锚模板行 `至第N卷·KRn（N=卷号, n=KR 号，须在 volume_map 在盘）` 与场景钩「声明⊆末行逐字」谓则说明；
- 红测：对现行 SKILL 跑 lint=FAIL（斜杠形+锚缺失），修复后 PASS。

### T2 · 卷期参数下沉：热协议进管线（修 R3）
- genre-config 增 `volume_opening_protocol`（卷首 N 章：热开篇定义/亲口目标出口/倒计时锚声明字段），planning/drafting prompt 自动注入；冷三连影子检查（`emotion_tone∈{平}`+`金句位∈{静}`+尾拍温 同现 → WARN 进台账）；
- 驱动 prompt 降级为「监控侧复核」而非唯一执法（与 #82/#83 门转正后并轨）。

### T3 · settle 读面分窗与指令保底（修 R5 上半）
- settle reads 改**分窗**：pending_hooks 只注入「总览表 + active 钩 + 本章触及钩的详情节」（其余节以 `（已归档引用：MHnn…）` 一行带过）；character_matrix 只注入本章出场角色行+键结构样例——复用 #81 归档工具的窗口逻辑；
- 目标上限：settle prompt 恒 ≤60k tokens（断言测试：以 ch41 工件回放组装，断言 token 预算）；
- 截断语义保底：`_budgeted_truncate` 后在 user prompt 顶部注入 `【截断告知】以下文件数据不完整（截断清单+缺多少）`——被截数据须被模型知晓为不完整（禁止静默中段）。

### T4 · 失败反馈改操作路径（修 R6）
- `content_dropped` 反馈模板改为三段式：①被丢行 verbatim 清单 ②指令「以上行原样保留于输出（作为基底行），仅在其后追加本章新键行」 ③一个最小正例（live 两行+新一行）；
- drafting 字数类反馈同理：报「场景 i 差 N 字（现 X/需 ≥Y）+ 建议扩拍位（对白/动作/感官各一）」——禁止只报症状。

### T5 · 草写长度锚定与早检（修 R4）
- drafting prompt 注入**范例章**：上一通过章全文（首章用 fixture 标准章）——`+3.5k tokens` 换长度稳定（成本可忽略）；
- 落盘前**本地早检**：dispatch 输出解析后即数字数（split_bundle+total_chars 已有），低于带即带差值反馈**单章重试**（不整束熔断）；
- （可选，二期）双章 bundle 拆两次单章派发——先以上两项实测，不奏效再拆。

### T6 · 修订 diff 化 + 束检查点补位（修 R7/R8）
- chapter-revision 输出改「场景级替换清单」（`场景n: <全文>` 列表，未列场景不动）——prompt 注入受影响场景定位，不再全章重写；
- 束模式补 follower 章 memo 检查点：`bundle_chapters()` 的非头章在 planning 步后各挂一次 memo 审查（或合并为「束计划审查」单检查点覆盖两章）。

## 2. 验收

1. `just check` 含 gate-prompt 契约 lint 且现行 SKILL 全 PASS；
2. ch41 工件回放：settle 组装 prompt ≤60k tokens（断言测试）；截断告知块在截断时必然出现（单测）；
3. 束4（ch43/44）以修复后管线重跑：**≤1 次人工接骨**（对照束1-3 的 3-5 次/束）——r1 验收的实弹面，允许以「接骨数≤1」记录达标；planning 零斜杠形/零锚缺失（shadow WARN 清零或仅剩误报候选）；
4. drafting 字数失败在早检层捕获≥1 次且单章重试通过（或全绿无失败）；
5. 单测面：枚举 lint 红测→绿、分窗组装快照、反馈模板含 verbatim 行清单、修订输出 schema 校验。

## 3. 不做面（防过度施工）

- 不换模型、不加档（thinking/温度维持现状——先修「教的对、看的全」，模型分档实验只在 T1-T5 达标仍不过验收时另立）；
- 不动门禁判据与 truth 文件结构（#88/#91 域）；
- 不做全语料 truth 压缩重构（分窗只动 read 面；写面结构归 #81/#90）;
- 不提前拆双章 bundle（T5 可选项实测后再议）。

## 4. 与在档 spec 的关系

- 上游实证：spec #84 Task 10 束1-3（vol1-ledger 裁决 #02-#09 为故障台账）；
- 复用：#81 归档窗口（T3）、#88 finding 契约（T4 反馈格式）；
- 下游：束4 重跑即本 spec 验收场，亦是 #84 Task 10 解冻条件。
