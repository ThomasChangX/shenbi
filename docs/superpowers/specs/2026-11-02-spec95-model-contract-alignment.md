# Spec #95 · 模型契约对齐与上下文预算（model-contract-alignment）：教对、看全、锚住、别放大

**日期**：2026-11-02（**r1.2 2026-11-02 全量对抗式审计修订**——T2 落地面改 market_params 子键（顶层键红线）、T3 补字符总预算/current_state/blob 快照、T5 改 bundle 粒度、T6 改 reject 作用域对称、R4/R5 数字校正；**r1.3 2026-11-04 价值门驳斥修订**——R2/R3「0 处」改「常驻 0/瞬态反馈 3 次」口径（00145/00160/00167 反证）、R5 因果细化（提取已生效仍被 32K 帽截断+matrix 通用 head+tail 实录）、T1 补 gate 侧锚尾判定+defer 锚数据形正例、T3 改道升格既有 extractor 体系、T4 drafting 半边并既有 TARGETED-EDIT、T6 改标检查点所有权对称并划出覆写路径；**r1.4 2026-11-04 二轮驳斥勘误**——R2 证据链改真（00145 指令形当轮有效但不持久/00167 为回灌复刻，撤「指令形无效」句）、R5 单位澄清（blob bytes vs prompt chars：43,701 chars=103,077 bytes；提取零裁剪+总览 head 仅 1.5k）、T3 预算 75k→72k chars 留余量+锚修、验收 3 补覆写类复发单列记账）｜ **系列**：卷二实弹复盘批（regen-vol2 首四束实证） ｜ **状态**：Active（r1.4） ｜ **优先级**：🟠 P1（图例口径；r1 的 🔴 图标与 P1 不符，r1.2 修正）
**依赖**：T3 读面分窗复用 #81 窗口选取语义＋**#85 truth_format.py 解析基座**（Hook ID/表格行/H3 节界三面切片单源——T3 自带临时正则即 M6 第六方言，禁）；T4 反馈文案与 #88 gate-finding 契约衔接；其余独立。**批次时序（r1.1 注记，2026-11-02）：#85 先落 → 本 spec T1-T6 → 束4 验收 → 批次 A 其余**（验收窗内不混入行为保持重构——防接骨数归因污染）
**动机证据**：spec #84 Task 10 束1-3 实弹（2026-11-01/02，novel-xinghuo-vol1 ch37-41）：三束共 **9 次人工介入**（裁决 #02-#09 八条编号＋1 次未编号手工回灌；vol1-ledger「卷二开卷运行」节）；全部派发 `finish_reason=stop`（**零 API 截断**——不是输出上限问题）；dispatch blob 取证（observability/dispatches/00163 等 + blobs/ 逐字 prompt）。

**触及的不变量维度**：情绪节奏（弱关联——T2 卷期热协议参数化，仅 WARN 影子检查，不新增判定判据）；其余为 prompt/预算/反馈层，不改门禁判据与 truth 结构

---

## 0. 根因矩阵（八条，全部 blob/日志级证据——**模型不笨，是被教的、被截的、被放大坏的**）

| # | 故障现象（束1-3 实录） | 表面归因 | **真根因** | 证据锚 |
|---|---|---|---|---|
| R1 | planning 反复输出 `chapter_role: 推进/转折` 斜杠形（3 轮 planning 熔断的共同红项） | 模型不听话 | **SKILL prompt 自己教了斜杠**：枚举呈现为「高潮/兑现 \| 推进/转折 \| 过渡/铺垫」——把「档位分组」写成了「可用值」，模型照抄所见 | chapter-planning system blob（00163 派发）：`合法值：高潮/兑现 | 推进/转折 | 过渡/铺垫` |
| R2 | 每轮 plan 的 defer 行全部缺「至第N卷·KRn」锚（8-10 条 shadow WARN/轮，永不收敛） | 模型不会写 | **锚模板不在任何常驻 prompt**（system/契约 reads 0 处；仅瞬态失败反馈注入过 3 次——r1.3 修正原「0 处」绝对化表述；r1.4 修正证据链）——全 29 次 planning 派发扫描：凡输入含模板（00145 指令形/00167 手写回灌）response 全锚定（4/5 锚），凡不含（00163/00168/00169 等）response 全 0 锚——**瞬态注入当轮有效但不持久**（下轮无模板即归零），常驻化是解；数据形正例仍取（回灌复刻证明抄数据形最稳，00145 证指令形亦有效） | blob grep：常驻 system=0；user 数据形锚=00167×5（手写回灌）；00145 指令形 1→response 4 锚；00163/00168/00169 无模板→response 0 锚；WARN 每轮复现 |
| R3 | planning 冷三连（emotion 平/金句 静/尾拍 温）每束复发 | 模型没品味 | **卷二开卷热协议（T1-1 三件套）只存在于监控侧驱动 prompt 与瞬态反馈**（r1.3 修正口径：常驻输入零提及、瞬态反馈 2 次含三件套）——planning 常驻输入（system/契约 reads/卷纲节点）`热开篇`×0、`倒计时`×1 泛指，卷纲节点文字亦无温度信号；模型按承接节点字面产出低温计划是**理性**行为 | blob grep：常驻 `热开篇`=0（00163 system/user 双 0）；瞬态 00145/00167 反馈含三件套；spec #84 驱动 prompt 门面真相自证（「首四束唯一执法=驱动侧」） |
| R4 | drafting 稳定欠重（2275-2629 字 vs 2800 下限，~50% 尾部失败） | 模型偷懒 | ①**无范例章锚定**：prompt 里没有任何一章完整正文（ch39/40 正文 0 字节），长度只以数字传达（`3200`×2）——flash 档无 few-shot 时锚向「一次回复的自然长度」；②**长文裹 JSON 信封**（`content` 字符串里塞 6400+ 字中文正文+PRE/POST），模型倾向压缩以保 JSON 合法；③字数只在 scene-split **终检**才验——差 26 字也整束熔断重来 | draft41 user blob：113 段无正文范例、Output Format=JSON 信封；字数失败均在 scene-split 阶段发现。**r1.2 补**：drafting/revision 确为 `max_tokens=49152`+`thinking="low"`（executor_config:8-26），但 **settling 无 thinking 覆盖**（:36-42 只有 temperature/max_tokens），走 provider 默认——原表述对 settling 不成立 |
| R5 | settle `content_dropped` 三连败（ch41，每轮丢行数递增） | 模型违反增量契约 | **三重夹击**：①live 文件无界增长把 settle prompt 推到 94-96k tokens——**r1.3 细化/r1.4 单位澄清**：current_state 等六文件已有 extractor 接线在役（00189 哨兵×7 实录），真正推高项＝character_matrix **无专属 extractor**（00189 blob 169,169 bytes 原档仅走通用 head+tail：59,329 chars→保头块+末 14/36 章单元＝34,045，**中段直截**）＋pending_hooks **提取零裁剪**（详情节 42.2k chars 全保留——总览 head 仅 1.5k chars，体积全在详情；「点名」grounding 在 ch41 点名全部 14 钩）＋registries 类；②`_INPUT_MAX_CHARS_PER_FILE=32000`（chars 帽）把**提取零裁剪后**仍 43.8k chars 的 pending_hooks **拦腰截断——被裁掉的尾部正是它要更新的最新钩行**（00189-a1 实测链：原档 43,701 chars〔blob 103,077 bytes UTF-8〕→提取后 43,795 chars〔14/14 全保留+哨兵 94 chars〕→32,000；blob=pre-extractor 原档语义，observability/archive.py:251-258），模型对看不见的行只能重造；③96k 上下文里大体积数据在眼前，**数据模仿压倒指令遵循**（增量契约在 system 里写得很对，但模型抄了数据的形） | 增长曲线：ch23=68.6k → ch35=90.1k → ch41=**95.8-97k（95,835/97,000/95,850 三次，r1.2 取区间）** tokens（单调无界）；日志 `input_truncated file=staging/truth/pending_hooks.md kept_len=32000 original_len=41592`（17:01/17:03/17:06 三次 settle 全中）；00189 user prompt 实录：`[extractor:hooks_audit_scoped] 保留 14 段，省略 0 段`＋`[TRUNCATED 32000/43795]`；escalation-41-report：丢行数 1→4/5 递增 |
| R6 | settle 重试越试越糟（反馈放大回路） | — | 失败反馈说「你丢了 X 行」→ 模型的修复策略=**更多地重发整档**→丢更多行。反馈描述了症状没给出**操作路径**（「以 live 行集为基、只 append 新键行」） | 三轮失败的 completion 36k→24k→20k 且 dropped 递增；对比：监控侧把被丢行回植 staging 后一次通过（裁决 #08） |
| R7 | 修订改一处破两处（ch41 工食数字被修后又 canon 漂移） | 模型不稳 | 修订输出=**整章全量重写**（无 diff/场景级模式）——每次修 3 行都要重掷 3400 字全章骰；prompt 仅 12k（无全章上下文却要保全章） | revision prompt 12k/completion 13-21k 全章；ch37 修订成功 ch41 修订漂移=同机制骰运 |
| R8 | 束模式 follower 章检查点面不完整（ch38/40/42 staged 计划处置不对称） | — | **检查点所有权不对称（r1.3 改标）**：#72 已把 follower plan 纳入 leader 检查点 G4（chapter_loop:1625-1633）与 approve/commit（:1753-1763），但 **reject 面 `_checkpoint_staging_targets` 仍只清 leader**（cli.py:683-690 无 bundle_chapters follower 循环）——reject 后 follower staged 计划残留不一致。**r1.3 归因修正**：裁决 #05/#07/#09 的「覆写事故」发生在**重派写盘路径**（先于任何检查点决策），reject 对称**堵不住**它——该路径治本（dispatch 侧拒写 checkpoint-marked 文件／/tmp 纪律）显式不在本 spec 范围（见 §3） | 源码：cli.py:683-690（reject 无 follower）vs :734-744（commit 有循环）；裁决 #05/#07/#09 实录（staged 计划两度被重派冲掉＝写盘路径，非 reject 路径） |

**用户假设裁定**：「每章膨胀的 context 是否压迫输出」——**成立且已量化**（R5 曲线+截断日志）；但 API 层无输出截断（finish_reason 全 stop），压力机制是「截断致盲写」+「长上下文指令遵循衰减」两支，不是预算顶。

## 1. 任务分解

### T1 · 契约同步器：gate 词表 ⇄ prompt 单源（修 R1/R2）
- **先立显式枚举常量（r1.2 前置）**：`CHAPTER_ROLE_VALUES` 等从 regex alternation 提为常量（现 `(高潮|兑现|推进|转折|过渡|铺垫)` 内联在 chapter_planning.py:749±；金句位 regex :125 只编码 `燃`）——lint 与 checker 共读同一常量，否则「机器可读清单」无源可抽；
- **gate 侧锚尾兜底（r1.3 新增，r1.4 补实现注记）**：现 regex `chapter_role\s*[:：]\s*(高潮|…)` **前缀匹配实测放行斜杠形**（`chapter_role: 推进/转折` match=True→G4.cp.chapter_role PASS——协调者亲测复现）——值域判定改**锚尾单值**（`re.MULTILINE` 下行尾锚定，拒斜杠/多值形——现 :749 为全文 search 无行锚，不加 MULTILINE 的 `$` 只匹配文末），与枚举常量同源；现役 42 份 plan 的 chapter_role 行全为裸 `key: value` 形，锚尾判定零误伤合法形；lint 只管 SKILL 文件、不管模型输出，gate 侧兜底是斜杠形的唯一拦截面；
- `tools/lint_gate_prompt_contract.py`（进 `just check`）：对**有枚举的检查**（34 个 `g4_*` 函数中列出清单，非全部）校验对应 SKILL.md 含 **verbatim 模板块**（合法值逐行列出+一个最小正例），禁止手写分组斜杠；
- 修 chapter-planning SKILL.md：枚举改逐行清单（`高潮`/`兑现`/`推进`/`转折`/`过渡`/`铺垫` 各占一行 + 「只许单值」明示）；补 defer 锚模板说明 `至第N卷·KRn（N=卷号, n=KR 号，须在 volume_map 在盘）`＋**数据形最小正例**（r1.4 口径：一行实值形如 `→ defer 至第2卷·KR3` 的完整 defer 行——常驻化解决持久性〔00168/00169 无模板即 0 锚〕；数据形正例是回灌复刻证明的最稳形态、00145 证指令形亦有效故为加固非唯一解）、场景钩「声明⊆末行逐字」谓则说明；
- 红测：对现行 SKILL 跑 lint=FAIL（斜杠形+锚缺失），修复后 PASS；**gate 锚尾判定红绿测（r1.3）：`chapter_role: 推进/转折` 必 FAIL**。

### T2 · 卷期参数下沉：热协议进管线（修 R3）
- **落地面（r1.2 钉死）**：genre-config **顶层键是 12 键闭集**（`contracts/ownership.py:41` GENRE_KEYS；`genre_config.py:165-173` 对未知顶层键直接 ValueError；SKILL.md:341/:434 明文「不得自造顶层键」）——`volume_opening_protocol` 必须挂 **`market_params.volume_opening_protocol` 子键**（`GenreConfig.market_params` 类型允许 `dict[str, dict[...]]`，:53）；**r2.2 复核**：现有 validator **已容忍未知子键**（`genre_config.py` docstring 明示「子键多余不拒」），无需扩白名单；但 `market_params` 值类型限定为**扁平标量**，故须定义 `volume_opening_protocol` 子键 schema（扁平标量）+ SKILL.md 子键文档；若需结构校验则**新增**（非扩）；**若坚持顶层则属 breaking contract**：GENRE_KEYS 12→13 + Pydantic/ownership/SKILL 三源同步 + 四站测试，须用户裁定；
- **注入三处接线（r1.2）**：①contract `reads` 增 genre-config 投影子键（`fields.py:97` 的字段过滤只支持**顶层键**，子键必须走 read extractor）；②chapter-planning 现只读 `chapter_word`、chapter-drafting 只读 `fatigueWords/pacing/chapterTypes`——两 skill 的 reads 都要改；③冷三连影子检查（`emotion_tone∈{平}`+`金句位∈{静}`+尾拍温 同现 → WARN）作为 **#82 共享冷谓词的更严 WARN 子集**（#82 已定义 `tone∈{悲,惧,平} 且 金句位非燃`，实现于 text/recall_weight.py:205 `cold_chapter`），给新 check id 并在 `docs/framework/invariants.md` 维度 8 门检列登记；**WARN 落点（r1.3 澄清，r1.4 锚修）**：走 shadow 通道（新 id 按 #82 纪律登记 `GATE_TO_SHADOW_KEY`——gates/g4/shadow.py:28 定义〔:36 为表内行〕，未列 id 反而保 HARD（:74-75 `loc is None → return None` fail-safe），须显式入表才 WARN 化；WARN 事件落 trace.jsonl 可查）——vol1-ledger 是手账、无自动 sink，**接骨度量不依赖 WARN 计数**（验收 3 仍按 ledger 人工条目+escalation 双列核对）；
- **驱动 prompt 不撤（r1.2）**：T2 未落门级替代前，`docs/regen-vol2-driver-prompt.md:19` 的「唯一执法」条款保留；T2 落地后同批改写该文档，不得让「spec 说已降级、prompt 说唯一执法」双源并存。

### T3 · settle 读面分窗与指令保底（修 R5 上半）——**r1.3 改道：升格既有 extractor 体系，非新建**
- **既有基座（00189 实证在役）**：`extract_hooks_audit_scoped`（read_extractors.py:92-138；总览 FULL+点名详情节+省略哨兵）与 `extract_recent_increments`（:294-365；章键表尾窗）已由 settling SKILL reads 声明接线（current_state/particle_ledger/emotional_arcs/subplot_board/chapter_summaries/timeline=recent_increments、pending_hooks=hooks_audit_scoped；dispatch loop 接线 dispatch_helper.py:903/:1082；00189 user prompt 哨兵×7 生效实录）——**新建分窗=维护面翻倍，禁**；character_matrix 无专属 extractor，走 `_strip_meta`+通用 `chapter_scoped_head_tail`（169,169B→59,329 chars→保头块+末 14/36 章单元＝34,045，中段章单元直截）；
- **真新增五件（r1.3 清单化，r1.4 修正②③④）**：①**character_matrix「本章出场角色行」定向提取器**（替代通用 head+tail 的中段盲截；表格行切片 import #85 truth_format.split_table_cells；grounding 面=chapter_summaries「出场角色」列现成在盘）②**hooks 窗语义强化**——active 钩纳入+「点名」grounding 过宽治理（ch41 点名全部 14 钩零裁剪、详情节 42.2k chars 全保留即体积所在——总览 head 仅 1.5k chars 无需预算；active 判定源=总览表「当前生命周期」列，ACTIVE/RESOLVED 过滤先例 extract_threads_overview read_extractors.py:414-456）③**settle 专属字符总预算并在组装函数内断言**（r1.4：实测配比 ≈0.80 tokens/char（95,835/119,928），60k tokens 目标对应 **72k chars 预算**留 ~4% 余量——75k 贴线无余量；现无 settle 专属上限，真正总闸 `_INPUT_MAX_CHARS_TOTAL=128000`（dispatch_helper.py:316）按中文实测 ≈95.8k tokens 失守——窗口后仍超则按钩优先级降级）④**顶部截断汇总块**（per-file 哨兵已存在 dispatch_helper.py:398-400/:447 `[TRUNCATED k/n chars]`，:1220-1225 为 input_truncated WARN 日志循环、:1231-1232 _cap_single 调用；升级为 user prompt 顶部 `【截断告知】以下文件数据不完整（截断清单+缺多少）` 汇总，不重复实现/双口径）⑤**降级路径预算行为**（`extractor_failed_fulltext` 回全文后 32K 拦腰截断复发面——降级时的预算须与正常路径同受总预算约束）；三面切片（钩 ID/表格行/节界）一律 import #85 truth_format.py（HOOK_ID_RE/split_table_cells/iter_sections(level=3)；自带临时正则=M6 复发，禁）；
- **回放源（r1.2 保留）**：不得用 live 路径（staging 已清、live truth 随卷二续跑增长）——从 `observability/dispatches/00189` 的 `reads[*].blob`（pre-extractor 原档快照：character_matrix 169,169B/pending_hooks 103,077B 等 15 项全在盘）固化为 fixture，断言 60k 预算；tokenizer 估算规则一并钉死。

### T4 · 失败反馈改操作路径（修 R6）
- `content_dropped` 反馈模板改为三段式：①被丢行 verbatim 清单 ②指令「以上行原样保留于输出（作为基底行），仅在其后追加本章新键行」③一个最小正例（live 两行+新一行）；**r1.2 规模控制**：实测丢 4-5 行、每行 100-200 字 ≈1-2KB，可控；清单去重 + 上限 N 行（默认 20）+ 优先列**未出现在截断窗口内**的行（当前反馈只有 `content_dropped:{n}行 e.g. {shown}`——state_settling.py:185）；
- drafting 字数类反馈（r1.3 改合并升格）：与既有长度族反馈+TARGETED-EDIT 通道（chapter_loop.py:1178-1232；前稿全文+扩不重写指令、escalation #024 先例、#83 T4 打摆切换「字数缺口按反馈实测值补足，不重掷全章」）**合并升格**——在其上改报「场景 i 差 N 字（现 X/需 ≥Y）+ 建议扩拍位（对白/动作/感官各一）」，**不平行新建第二套反馈模板**；禁止只报症状。

### T5 · 草写长度锚定与早检（修 R4）
- drafting prompt 注入**范例章**：上一通过章全文（首章用 fixture 标准章）——`+3.5k tokens` 换长度稳定（成本可忽略）；
- 落盘前**本地早检**：dispatch 输出解析后即数字数（split_bundle+total_chars 已有），低于带即带差值反馈——**r1.2 改粒度**：bundle 模式下一步 dispatch 产双章、无单章 md 输出（chapter_loop.py:179-189 step 4 无 output_path），**主线路=束级早检 + 按章定向反馈 + 整束重派**；「单章重试」需先拆 bundle，列 Phase 2；
- （Phase 2，实测主线路不奏效再拆）双章 bundle 拆两次单章派发——拆后 T5 的单章重试与 T6 的场景级 patch 才自然。

### T6 · 修订 diff 化 + 束检查点补位（修 R7/R8）
- chapter-revision 输出改「场景级替换清单」（`场景n: <全文>` 列表，未列场景不动）——prompt 注入受影响场景定位，不再全章重写；**r1.2 补全契约面**：需确定性 applier + patch 载体 schema（`merge_prose` 目前只是 `contracts/enums.py:43` 的 Literal 枚举、无实现；dispatch_helper:1288-1388 只特判 append_dedup），PRE/POST/场景钩随替换重生成，G2 字数/G4.cd 全章复核顺序写进 plan；先落 SKILL 契约变更再改 prompt；
- **束模式检查点（r1.3 改标：检查点所有权对称——非覆写事故的修复）**：#72 已把 follower plan 纳入 leader 检查点 G4（chapter_loop:1625-1633）与 approve/commit（:1753-1763）；真缺口＝**reject 作用域只含 leader**（cli.py:683-690 `_checkpoint_staging_targets` 无 bundle_chapters follower 循环 vs commit :734-744）——修对称（reject 清单镜像 commit 的 follower 循环）+检查点 artifact/context 明列两章；**不新增第二检查点**；**覆写事故路径（重派写盘先于任何检查点决策，reject 对称救不了）显式划出本 spec 范围**（治本=dispatch 侧拒写 checkpoint-marked 文件／/tmp 纪律，如束4 复发另立，见 §3）。

## 2. 验收

1. `just check` 含 gate-prompt 契约 lint 且现行 SKILL 全 PASS；
2. **00189 blob 快照回放**（reads[*].blob 固化 fixture，非 live 路径）：settle 组装 prompt ≤60k tokens（**组装函数内断言**，非仅测试）；截断汇总块在截断时必然出现（单测）；
3. 束4（ch43/44）以修复后管线重跑：**≤1 次人工接骨**——**接骨度量（r1.2 定义，r2.2 复核）**＝vol1-ledger「卷二开卷运行」节内人工处理条目（`裁决 #` 块/手工手术记录）＋pipeline escalation 数，评审时按同节逐条重数；**束1-3 账面基线=8 条裁决（#02-#09，其中 #04/#07 为正文引用）＋1 次未编号手工回灌＝9**（全节 `- **裁决` 块头 4 个、唯一编号 8 个——评审以「编号集合＋手工条目」双列核对，不按子串瞎数）；**r1.4 记账条款：覆写类复发（重派写盘路径，§3 划出面）单列记账——计入总人工介入数并触发另立，但不计入 T1-T6 修复效果的接骨归因**；planning 零斜杠形/零锚缺失（shadow WARN 清零或仅剩误报候选）；
4. **束级早检**在 drafting 捕获≥1 次字数失败且整束重派通过（或全绿无失败）；单章重试属 Phase 2（拆 bundle 后）；
5. 单测面：枚举 lint 红测→绿、**gate 锚尾判定拒斜杠形（红绿测，r1.3）**、分窗组装快照（**升格既有 extractor 面上的 matrix 定向提取器+settle 字符总预算组装内断言**）、反馈模板含 verbatim 行清单、修订 patch schema/applier 校验、reject 作用域含 follower（红测）。

## 3. 不做面（防过度施工）

- 不换模型、不加档（thinking/温度维持现状——先修「教的对、看的全」，模型分档实验只在 T1-T5 达标仍不过验收时另立）；
- 不动门禁判据与 truth 文件结构（#82/#83 域——r1.2 更正：原写 #88/#91，二者分别是 finding 契约与状态并发）；
- 不做全语料 truth 压缩重构（分窗只动 read 面；写面结构归 #82/#83——r1.2 更正：原写 #81/#90，二者是观测与契约数据面）；
- 不提前拆双章 bundle（T5 可选项实测后再议）；
- **覆写事故治本不在本 spec（r1.3 显式划出）**：重派写盘冲掉人工 plan 的路径（裁决 #05/#07/#09）先于任何检查点决策——dispatch 侧拒写 checkpoint-marked 文件／/tmp 纪律属写守卫域，如束4 复发另立；T6 只修 reject/commit 所有权对称。

## 4. 与在档 spec 的关系

- 上游实证：spec #84 Task 10 束1-3（vol1-ledger 裁决 #02-#09 为故障台账）；
- 复用：#81 窗口选取语义＋#85 truth_format.py 解析基座＋**既有 read_extractors 体系（r1.3：hooks_audit_scoped/recent_increments 在役，T3 升格不新建）**〔r1.1 口径修正：原「#81 归档窗口」产物级复用收窄为窗口语义先例——切片语法基座归 #85〕、#88 finding 契约（T4 反馈格式）、既有长度族反馈/TARGETED-EDIT 通道（T4 drafting 半边合并升格）；
- 下游：束4 重跑即本 spec 验收场，亦是 #84 Task 10 解冻条件。
