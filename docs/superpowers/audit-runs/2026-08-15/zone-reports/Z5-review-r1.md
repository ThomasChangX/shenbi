# Z5 独立复核报告 r1（fresh-context，2026-08-15 轮）

- 复核 agent: Z5-review（与初审者无关的独立上下文）| 编号段: F515–F524（初审已用 F501–F514）
- 复核对象: docs/superpowers/audit-runs/2026-08-15/zones/Z5.files 全部 13 文件（audit/ 5 + cost/ 5 + orchestration/ 3），全量重读（非 diff 抽查）
- 本轮新增角度: **调用形状全仓核对 + 声明面↔磁盘面对账**
  - 对 Z5 每个关键函数 grep 全部调用点核对实参形状 vs 签名（dispatch_skill ×11、TokenLedger.record、_log_token_usage、warn_if_over_budget、TraceWriter.append、audit_writes/snapshot_tree/record_audit_outcome/derive_output_files、check_escalation、check_scorer_agreement/flag_score_collapse）
  - 对每个声明面与磁盘实际做双向 diff（OWNERSHIP 矩阵 ↔ 技能契约 surface、truth-files.yaml 两份拷贝、MODEL_CONTEXT_LIMITS/PRICING ↔ dispatch_helper 常量、pyproject 入点、enums.py 单一词表 ↔ 全仓 Literal）
- 只读约束遵守: 除本报告外未创建/修改/删除任何仓库文件；未执行 pytest；未运行 shenbi-dispatch/pipeline。所有 `uv run python -c` 仅做 import/纯函数验证。
- 核心复核结论一句话: **初审的 14 条 finding 全部经独立复现成立、无一条整体误报；但初审把写审计当作"机制正确仅有参数化缺陷（F501）"来分析，实际写审计链当前在三条派发路由上没有任何一条能产生真阳性**（API/IDE 路由整链缺席 + legacy 路由快照根错位盲区 + parametric 技能恒误拦），另有 added 逃逸、drift 误归属、坏 YAML 崩溃三个初审未发现的机制性缺陷（均实跑复现）。

---

## 一、漏报（初审未发现；均附实跑证据）

### F515 | OWNERSHIP field 级"added"逃逸：新增文件 changed_top_keys 恒空，删除+重建可整体绕过 field 审计 | error | P1
- 证据: src/shenbi/audit/snapshot.py:99-100（`pre is None and post is not None → FileChange(status="added")`，changed_top_keys 取默认 `()`）+ src/shenbi/contracts/ownership.py:114-115（field 级只检查 `change.changed_top_keys ⊆ write_keys`）+ src/shenbi/audit/write_audit.py:61-64（有 OWNERSHIP 条目的文件跳过 file-level 声明检查）
- 根因: added 分支不计算新文件内容的顶层键；FileChange 携带的 diff 信息在 added 场景为空
- 验证（已运行）:
  ```
  $ uv run python -c "...compute_file_change('genre-config.json', None, '{\"anything\": 1, \"evil\": 2}'); check_write_ownership('shenbi-genre-config', ch)"
  ADDED genre-config (genre-config skill): added keys: () violations: []
  ```
- 影响: 对 (shenbi-genre-config, genre-config.json) 这类 field 级条目，"先删（F502 逃逸）再重建（本条逃逸）"= 任意内容整体替换不触发任何越权报告；即使只看 added 单边，新建文件的键集也完全不过审
- 对照: 2026-08-14-audit-chain-design.md R5 明确将 "deleted/added 零拦截" 并列为一族（F507, P1）；初审 F502 只覆盖了 deleted 半边
- 建议方向: added 时 `changed_top_keys = json.loads(post)` 的顶层键集（genesis 首建同样适用：首建键也应 ⊆ write_keys）
- 定级依据: 判定表 P1（正常路径可复现功能错误；与 spec R5 既定 P1 对齐）

### F516 | 既有 drift 被归咎于"本次未写入该文件的技能"：pre==post 零改动仍 GATE_FAIL rc=2，级联阻断后续所有 watcher | error | P1
- 证据: src/shenbi/audit/write_audit.py:51-56（drift 检测对 watch 面内每个"post 存在"的 .md 一律执行，判据仅看 post 内容，**不看该文件本次是否被改动**）+ src/shenbi/dispatcher/executor.py:286-288（`audit_ok=False 且 rc==0 → rc=2`）
- 根因: drift 归属以"文件在 watch 面内"为准而非"本次 dispatch 造成了 drift"；drift 一旦产生（前一个技能的坏写入或人工编辑），持久存在
- 验证（已运行，文件 pre==post 完全未变）:
  ```
  $ uv run python -c "...audit_writes('shenbi-state-settling', {'truth/pending_hooks.md': drift_content}, {'truth/pending_hooks.md': drift_content})"
  drift: ("drift: id=h1 key=type md='伏笔' != YAML=None", ...共 7 条)
  violations: ()  blocked: True
  ```
- 影响: legacy 路由上，pending_hooks.md 一旦出现 cross-section drift，**每一个**把该文件列入 writes/updates 的技能（plant/track/resolve/state-settling 等）即便零写入也会被 rc=2 拦截，直到人工修复 truth 文件——审计的"写越权/漂移归属"事实错误 + 流水线停滞
- 建议方向: drift 判定仅对 `change` 非空（本次实际改动）或 drift 集合在 pre→post 间扩大（新增 drift）的文件触发
- 定级依据: 判定表 P1（可复现功能错误 + 级联阻断；"不确定取更高"）

### F517 | watched truth md 含坏 YAML 时 audit_writes 直接崩溃：finally 块异常掩盖 rc/原始异常，write-audit.jsonl 行丢失 | error | P1
- 证据: src/shenbi/records/parser.py:37-40（`yaml.safe_load(body)` 无 try；非列表时 `raise ValueError`）+ src/shenbi/audit/snapshot.py:110 与 src/shenbi/audit/write_audit.py:54（parse_records 调用无任何包裹）+ src/shenbi/dispatcher/executor.py:283-288（audit_writes 在 `finally:` 内调用——Python 语义：finally 内新异常取代进行中异常/返回值）
- 根因: 审计链假定 truth md 恒可解析；LLM 写侧完全可能产出坏 YAML（flow mapping 语法错、## hooks 块解析为 dict 等）
- 验证（已运行）:
  ```
  $ uv run python -c "...audit_writes('shenbi-foreshadowing-track', {pre:正常}, {post:'## hooks\\n{ state: <<<< broken'})"
  CRASH: ParserError while parsing a flow mapping ... expected ',' or '}'
  $ （post='## hooks\\nstate: just-a-map'）
  CRASH: ValueError ## hooks block 必须解析为列表；实际 dict
  ```
- 影响（三层）: (1) dispatch 成功（rc=0）时审计崩溃取代返回 → shenbi-dispatch CLI 以未控异常退出而非干净的 rc=2；(2) `record_audit_outcome` 永不执行 → write-audit.jsonl 行丢失，直接违反 record.py 模块文档的核心承诺"绝不静默丢弃审计结果"；(3) dispatch 自身抛异常时 finally 崩溃掩盖原始异常（仅存于 `__context__`）
- 同时修正初审 F503 的 md 侧子论断（见"误报/子论断修正"§2.3）
- 建议方向: write_audit/snapshot 对 parse_records 包裹 try，坏解析降级为一条 drift/violation（fail-closed 但不崩）
- 定级依据: 判定表 P1（正常路径可复现功能错误——LLM 写坏 YAML 是常态失败模式；审计记录丢失）

### F518 | 写审计在 API/IDE 两条派发路由上整体缺席；dispatch_helper 模块文档仍声称"复用 write-audit 而非绕过" | error | P1
- 证据: src/shenbi/pipeline/dispatch_helper.py:3-5（docstring: "Reuses the existing ``dispatch_with_write_audit`` (write-overreach detection) via the dispatcher CLI **rather than bypassing it**"）vs :1855-1870 路由实现（API key → `return _dispatch_via_api(...)`；IDE CLI → `_dispatch_via_ide(...)`；两者内部均无任何 write-audit 调用）+ src/shenbi/dispatcher/cli.py:11（`dispatch_with_write_audit` 全仓唯一生产调用方 = shenbi-dispatch CLI，即仅 legacy 路由 3 到达）
- 验证（已运行）:
  ```
  $ grep -rn "dispatch_with_write_audit" src/ tests/ --include="*.py" | grep -v tests/
  src/shenbi/pipeline/dispatch_helper.py:3: Reuses the existing ``dispatch_with_write_audit`` ...（仅 docstring）
  src/shenbi/dispatcher/cli.py:11: from shenbi.dispatcher.executor import dispatch_with_write_audit as dispatch
  src/shenbi/dispatcher/executor.py:243: def dispatch_with_write_audit(...)
  ```
- 影响: Tier B 写所有权审计（OWNERSHIP 强制、cross-section drift、越权检测）只在 legacy/T1 路由生效；生产 API 模式（有 token ledger 的那条真实 LLM 路由）上写越权**结构性零检测**——F502/F503/F515 等所有逃逸在 API 路由上甚至不需要逃逸（无审计可逃）
- 对照: docs/superpowers/specs/2026-08-14-audit-chain-design.md R4（编号 F512, P1, Status=Design, 未修复）——上轮已发现，本轮 Z5 初审未承接
- 建议方向: API/IDE 路径接入同一 pre/post 快照审计，或在 docstring 显式降级声明
- 定级依据: AGENTS.md 显式契约 "Gates G0–G7 enforce quality at every stage—no gate can be skipped"（P1 第一条）+ 文档↔代码漂移

### F519 | 审计快照根 = 框架仓库根（PROJECT_DIR=REPO_ROOT）而非项目/round 目录：非参数化技能审计全盲，executor 内 G2 与审计观测面不同根 | error | P1
- 证据: src/shenbi/dispatcher/executor.py:29-31（`REPO_ROOT = parents[3]; PROJECT_DIR = REPO_ROOT`，即 shenbi 框架仓库本身）+ :264/:284（`snapshot_tree(PROJECT_DIR, watch)`）+ 同函数 :209（G2 却用 `derive_output_files(skill, chapter, round_dir, ...)` 绝对路径——观测面根不一致）+ src/shenbi/gates/shared.py:25（PROJECT 即仓库根）+ tests/unit/dispatcher/test_executor_audit.py:18,42（`monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)` 掩蔽错位，与 spec R1 所述一致）
- 根因: 快照根硬编码框架仓库根；技能实际写 novel 项目目录/round_dir
- 影响: legacy 路由上非参数化技能的 pre/post 全部取样自框架仓库（无对应文件 → 恒 None）→ 真实写入不可见（审计空转、恒 rc=0 放行）；与 F501 叠加后 legacy 路由呈"非参数化全盲 + 参数化恒误拦"的双向失效——**写审计当前不存在能产生真阳性的输入**
- 验证: 代码行号如上；另 phantom 复现（F520）证明 watch 内文件即使双侧都不存在也会进入 violations
- 对照: 2026-08-14-audit-chain-design.md R1（F513, P1, Design, 未修复，验收标准"round_dir 写越权被拦截"未达成）——本轮 Z5 初审未承接
- 建议方向: 快照根改 round_dir/project_dir（spec R1 修复方案）
- 定级依据: spec R1 既定 P1；门控机制静默失效

### F520 | "未声明写入"检查结构性只能产生假阳性：观测面 ⊆ 声明面，真越权（面外写入）永不入镜 | error | P2
- 证据: src/shenbi/dispatcher/executor.py:236-241（watch = `derive_output_files(skill, chapter, ctx)` = 契约 writes+updates 解析）+ src/shenbi/audit/write_audit.py:19-26（declared = `derive_output_files(skill)` 同一契约同源）+ :62-64（"未声明写入"仅对 watch 内文件触发）——`set(pre)|set(post)` 恒 ⊆ declared 的解析面，唯一分歧源是 parametric 解析差（即 F501）
- 验证（已运行——零改动、双侧不存在的文件也触发，证明该检查现存唯一输出是误报）:
  ```
  $ uv run python -c "...audit_writes('shenbi-chapter-drafting', {p:None,...}, {p:None,...})"  # pre==post==None
  violations: ('未声明写入: chapters/chapter-3-decisions.json（...）', '未声明写入: chapters/chapter-3.md（...）')
  ```
- 根因: 审计观测面按声明面构造（性能取向，初审交叉验证#2 已注记"扫描面之外的越权写结构性不可见"并接受为代价），但未指出推论：write_audit.py:63-64 的检查因此是纯假阳性机器（真阳性恒不可能），其存在本身构成虚假保证
- 说明: 初审在交叉验证#2 以"代价"口吻带过且未编号定级，本条补足定性；F501 已覆盖其假阳性方向，本条聚焦"检查不可能有真阳性"这一独立事实
- 建议方向: 观测面改为 registry 全量 truth 概念面（或至少 OWNERSHIP 全条目文件集），声明面继续按契约
- 定级依据: 判定表 P2（死逻辑/虚假保证）

### F521 | OWNERSHIP 矩阵含不可达死条目：(shenbi-foundation-review, genre-config.json) 的文件不在该技能契约 surface 内 | error | P2
- 证据: src/shenbi/contracts/ownership.py:78-80（read-only 条目）+ 对账实跑（声明面↔磁盘面双向 diff）:
  ```
  $ uv run python -c "...for skill, rel in OWNERSHIP: c=load_contract(skill); print(rel in c['writes']+c['updates'])"
  shenbi-foundation-review  genre-config.json  in-contract-surface: False  (writes+updates=['foundation/review_report.md'])
  （其余 5 条目均 True）
  ```
- 根因: 审计循环只遍历 watch（= 契约 surface）内文件；该 OWNERSHIP 条目引用的文件对本技能永不进入 pre/post → "foundation-review 只读 tropeInventory"的防写声明从未被执行
- 建议方向: 审计观测面纳入 OWNERSHIP 全条目文件（与 F520 同一修复），或删除该死条目
- 定级依据: 判定表 P2（声明面↔实际面 dead-wire）

### F522 | warn_if_over_budget 的 extra= 载荷在两种 logger 类型下语义分裂：stdlib 默认路径静默丢失、structlog 生产路径嵌套在 "extra" 键下 | error | P2
- 证据: src/shenbi/cost/estimate.py:44（默认 `logging.getLogger`）+ :49-57（`log.warning(msg, extra={...})` stdlib 惯用法）vs src/shenbi/pipeline/dispatch_helper.py:1555（生产传 structlog `logger=log`）+ src/shenbi/logging.py:27-42（structlog configure，`extra` 作为普通 event_dict 键）
- 验证（已运行）:
  ```
  $ uv run python -c "...std = logging.getLogger('shenbi.cost.estimate'); std.addHandler(StreamHandler(buf)); std.warning('prompt_approaching_context_limit', extra={'estimated_tokens': 999})"
  stdlib output: 'prompt_approaching_context_limit\n'   # 载荷全部丢失
  ```
- 影响: 默认 logger 路径（无注入时）告警不带 estimated_tokens/context_limit——运维看不到关键数字；structlog 路径载荷可见但嵌套于 "extra" 键，与框架其余结构化日志的扁平 kv 约定不一致
- 建议方向: 统一改为 `log.warning("...", estimated_tokens=..., context_limit=...)`（两种 logger 均安全）
- 定级依据: 判定表 P2（边界/错误处理缺陷；M/P2 之间按"不确定取更高"取 P2）

### F523 | 未知模型上下文上限回退到最大值 1M：注释自称 "Conservative" 但回退方向是乐观的，告警对小上下文模型静默失火 | error | P2
- 证据: src/shenbi/cost/estimate.py:16-21（注释 "Conservative per-model context limits... Unknown models fall back to the default entry" + `_DEFAULT_CONTEXT_LIMIT = 1_048_576` 即表中最大值）+ :35-36（`MODEL_CONTEXT_LIMITS.get(model, _DEFAULT_CONTEXT_LIMIT)`）+ :47-48（80% 阈值随 limit 水涨船高）
- 根因: 回退方向选择与"保守"声明相反——SHENBI_LLM_MODEL 指向未登记的小上下文模型（经自定义 SHENBI_LLM_BASE_URL 接 OpenAI 兼容端点是文档支持的部署形态，dispatch_helper.py:1541）时，阈值按 1M 计 → 超限告警永不触发 → 昂贵的 context-overflow API 失败回到无预警状态（本模块的存在目的）
- 验证: 代码对照（未构造真实小上下文模型端点实测，判定基于阈值算术：threshold = int(1M×0.8)）
- 建议方向: 未知模型回退到偏小值（如 128K）或显式告警"model not in MODEL_CONTEXT_LIMITS, using default"
- 定级依据: 判定表 P2（边界处理缺陷 + 注释↔行为方向矛盾）

### F524 | resonance_trend.md 存在第三个消费者 parse_trend 且格式契约互斥：管线写入侧只满足死桥（cells[6]），活 CLI 消费者需要 dim 表头 → 解析恒空、resonance 漂移检测静默空转 | error | P2
- 证据: src/shenbi/skill_utils/drift_detection/compute_drift.py:161-183（parse_trend 定位"第一个含请求 dim 名的表头行"，找不到表头 → `{d: []}` 全空返回）+ :27（RESONANCE_DIMS = ["情感落地",...,"overall"]）vs src/shenbi/pipeline/chapter_loop.py:1366-1371（`_build_resonance_trend_row` 只写数据行 `| Ch{N} | - | - | - | - | - | {overall} |`，**无表头**、五个 dim 占位 "-"，docstring 明言格式为死桥 parse_resonance_scores 维护）
- 验证（已运行）:
  ```
  $ printf '| Ch1 | - | - | - | - | - | 85 |\n| Ch2 | ... | 82 |\n' > /tmp/.../resonance_trend.md
  $ uv run python -c "...parse_trend(path, RESONANCE_DIMS)"
  headerless pipeline-style rows -> {'情感落地': 0, '场景临场感': 0, '文笔质感': 0, '读者回报': 0, 'overall': 0}
  ```
- 影响: 对管线生成的项目跑 `python -m shenbi.skill_utils.drift_detection`（__main__ 入口存在），resonance 维度全部 0 样本 → §8.3 resonance 漂移静默不检测；初审判 F506 时只识别两套来源（死桥 vs chapter_loop 逐章报告），漏了第三套（parse_trend，header 语义）与写入侧的真实兼容矩阵：**写入格式满足唯一不运行的消费者、不满足唯一在运行的消费者**
- 建议方向: 写入侧补一行 dim 表头（桥的 "overall" 行过滤与 parse_trend 的表头定位可同时满足），三消费者共用一个格式常量
- 定级依据: 判定表 P2（跨区声明分裂/静默空转；CLI 工具非热路径）

---

## 二、误报（初审发现但站不住的）

**无整体误报。** 初审 14 条（F501–F514）我逐条独立复核，全部成立：

- F501/F502/F503/F508/F509/F515 相关机制全部经 `uv run python -c` 独立复现（输出见上文各节及验证记录），与初审描述一致
- F504: 8 个无 `state=` 调用点逐一核对了**完整调用形式**（含多行 keyword 形式），确认无一在后续行传 state；chapter_loop 3 处有 state；`if state:` 门控在 dispatch_helper.py:1310 属实
- F505: `PipelineState` 无 chapter 属性实跑确认（state.py:79 的 `chapter` 属于 `CheckpointData`，非 PipelineState）；并补强——`_dispatch_via_api` 本地就有正确的 `chapter` 变量（dispatch_helper.py:1514-1520）却未传入 `_log_token_usage`（:1583/:1639），修复在调用点随手可得
- F506/F507/F510/F511/F512/F513/F514: grep/读码复核与初审一致（orchestration 包生产零 import；裸 except；实例锁 + 每次新建实例；任意 0-100 数值抓取；不可达 return 2；val>0；Literal 词表漂移）

仅两处**子论断级修正**（不动摇 finding 本体）：

1. **F504 的调用点计数**: 初审写"grep 全部 dispatch_skill( 调用点（10 处）"，实际 11 处（3 传 state + 8 未传 = 11）。所列 8 个未传位置完整准确，仅总数笔误。
2. **F503 的 md 侧不对称子论断**: 初审称"md 侧同场景会被判为'删除全部记录'而拦截（parse_records→[]）"。该论断仅对**不含 `## hooks` 段**的垃圾文本成立（extract_yaml_block→""→[]）；若垃圾文本含坏 YAML 的 `## hooks` 块，parse_records 直接抛 ParserError/ValueError → audit_writes 崩溃而非"拦截"（见 F517 实跑）。"md 侧比 json 侧更不易逃逸"的方向性结论仍成立，但机制描述不完整，且崩溃形态比初审认知的更糟（丢审计行 + finally 掩盖）。

---

## 三、覆盖空洞（初审报告未覆盖的文件/维度）

1. **派发路由维度完全缺失**（→ F518）: 初审交叉验证#1 沿 dispatch_helper 核对了 cost 接线、交叉验证#2 分析了 audit_writes 的扫描集，但从未回答"audit_writes 到底在哪些路由上被调到"。答案（仅 legacy 路由 3）改变整个 Z5 区的严重度分布——F502/F503/F515 的"逃逸"在 API/IDE 路由上是"无审计可逃"。spec 2026-08-14-audit-chain-design.md R4 已立案（P1, Design），Z5 作为 audit 包属主应承接。
2. **快照根维度缺失**（→ F519）: 初审逐一分析了 snapshot.py 的 diff 语义，未核对 `snapshot_tree(root, ...)` 的 root 实参是框架仓库根。spec R1（P1, Design）同案未承接。
3. **"真阳性不可能"综合结论缺失**: F501 的方向(b)只覆盖"chapter 提取失败→watch 空→空转"；实际还有"chapter 提取成功但根错位→非参数化盲区/参数化幻影键恒触发"（F519/F520 实跑）。三条路由合看的系统结论——**当前写审计在任何输入下都无法产生一条真阳性**——初审未形成。
4. **第二处测试掩蔽点**: 初审只指出 tests/unit/audit/test_write_audit.py 用手工 dict；tests/unit/dispatcher/test_executor_audit.py:20-23/:39-42 还 **stub 掉 derive_output_files 本身**，使 F501 在 executor 级测试同样不可见，两处掩蔽叠加。
5. **resonance 第三消费者**（→ F524）: F506 的"两套来源并存"盘点漏了 compute_drift.parse_trend。
6. **F511 的 bool 噪声**: `isinstance(v, (int,float))` 把 JSON 布尔 `true` 计为 1.0 分（实跑: `{'passed': True,...} → [1.0, 94.0, 3.0]`），F511 的噪声面比初审描述再大一档（作为 F511 补强，不另立编号）。
7. **enum 词表漂移的全量对账**: F514 只举 ownership.py:22；全仓对账另有 10+ 处 Literal 未入 enums.py，其中 **schemas/decisions.py:16 重定义了同名 `Severity = Literal["low","medium","high"]`，与 enums.Severity（BLOCKING/CRITICAL/MINOR）词表冲突**——正是 enums.py 文档声明要消灭的"词汇分裂"以同名异值形态复发（并入 F514 异议证据，见下）。
8. 非问漏项确认: docs/framework/truth-files.yaml 与 site/framework/truth-files.yaml 逐字节相同（diff 无输出）——site 镜像无漂移；pyproject 入点 shenbi-cost/shenbi-dispatch/shenbi-validate 均在（:58-59,64）；pricing↔dispatch_helper 模型名/环境变量镜像成立（pricing.py:16,27 ↔ dispatch_helper.py:70,74）；check_escalation 桥接 kwargs 与签名逐参匹配；TraceWriter.append 关键字调用签名匹配、actor_role="GATE" ∈ ActorRole。PRICING 费率本身（0.14/0.28 per 1M）注释自认未确认，无法外部验证——未验证，不立案。

---

## 四、严重度异议（无权改定级，仅提异议+理由）

1. **F514 M → 建议 P2**: 判定表将"文档↔代码漂移"列为 P2。enums.py:1 的"所有 Literal 必须从此处 import"是规范性声明，全仓 10+ 处 Literal 违反（ownership.py:22,31、base.py:29、schemas/registry.py:26,45、schemas/decisions.py:15-18、linguistic_drift.py:56,221、cjk.py:77），且 decisions.py:16 的同名 `Severity` 异值重定义使"从错模块 import Severity"零报错地拿到另一套词表——比初审举的单点漂移严重一档。M 仅应留给无规范声明冲突的笔误级问题。
2. **F513 M → 弱异议建议 P2**（供仲裁）: 判定表"边界/错误处理缺陷"= P2，`val > 0` 丢弃 0 分（escalation 语义下的崩塌极端信号）字面命中；初审降 M 的理由（dead-wire 包含）不属判定表规则。可辩护点：F508（无消费者）维持 P2 而 F513（死路径）降 M 的区分标准是"所在函数是否被生产调用"——snapshot.compute_file_change 在 legacy 路由真实执行而 parse_resonance_scores 零调用，该区分自洽。故仅列弱异议，倾向维持亦可接受。
3. 其余定级复核意见: F501/F502/F504 P0 成立（"契约被静默违反导致错误执行"/"数据丢失"/"TokenLedger 少计"均有字面命中且实跑复现）；F503 P1、F505 P1 成立（F505 补强：正确 chapter 在调用点作用域内现成可用）；F506/F507/F508/F509/F510/F511 P2 与判定表相符；F512 M 成立。无降级异议。

---

## 五、验证记录汇总（本轮实跑清单）

| 验证 | 命令要点 | 结果 |
|---|---|---|
| F501 复现 | `derive_output_files('shenbi-chapter-drafting', chapter=3)` vs 无 chapter；audit_writes | watch 2 文件 / declared=[] / 2 条"未声明写入" |
| 幻影键（F520 证据） | pre==post==None 零改动 | 仍 2 条 violations |
| F502 复现 | compute_file_change(pre→None) + check_write_ownership(track) | violations=[] |
| F515 复现 | compute_file_change(None→任意 JSON) + check_write_ownership(genre-config) | keys=() violations=[] |
| F503 复现 | post='garbage not json' | keys=() violations=[] |
| F516 复现 | pre==post 含 drift 内容，skill=state-settling | 7 条 drift，blocked=True |
| F517 复现 | post 含坏 YAML ## hooks 块 ×2 形态 | ParserError / ValueError 崩溃 |
| F508/F509 复现 | (None,None)/('x','x')；无 id 记录 diff | 均 'modified'；('None', frozenset) 幻影 |
| F504 复核 | 11 个 dispatch_skill 调用点完整形式核对 | 3 传 state（chapter_loop:1274/2831/3003），8 未传 |
| F505 复核 | `hasattr(PipelineState(), 'chapter')` | False（state.py:79 的 chapter 属 CheckpointData） |
| F506 复核 | grep orchestration 包生产 import | 仅 tests/unit/orchestration/test_bridges.py |
| F521 对账 | OWNERSHIP 6 条目 × load_contract surface | foundation-review 条目 False（死条目） |
| F522 复现 | stdlib logger + extra= | 输出行不含载荷 |
| F511 补强 | bool 计分 | True→1.0 入均分 |
| F524 复现 | parse_trend 读 headerless 管线行 | 全 dim 0 样本 |
| truth-files 双拷贝 | diff docs/ vs site/ | 相同 |
| 13 模块 import | 全部 import | OK |

## 六、汇总表

| 编号 | 标题 | 类别 | 严重度 | 与初审关系 |
|---|---|---|---|---|
| F515 | OWNERSHIP added 逃逸（删除+重建整体绕过 field 审计） | error | P1 | 漏报（spec R5 另半边） |
| F516 | 既有 drift 误归属零改动技能，rc=2 级联阻断 | error | P1 | 漏报 |
| F517 | 坏 YAML truth 使审计崩溃，finally 掩盖 + 审计行丢失 | error | P1 | 漏报（并修正 F503 子论断） |
| F518 | API/IDE 路由整体绕过写审计，docstring 反向声称 | error | P1 | 漏报（spec R4 未承接） |
| F519 | 快照根=框架仓库根，G2 与审计观测面不同根 | error | P1 | 漏报（spec R1 未承接） |
| F520 | "未声明写入"结构性零真阳性（纯假阳性机器） | error | P2 | 漏报（初审以"代价"带过未定级） |
| F521 | OWNERSHIP 死条目 foundation-review/genre-config.json | error | P2 | 漏报（对账新角度） |
| F522 | warn extra= 载荷 stdlib 丢失/structlog 嵌套 | error | P2 | 漏报（调用形状新角度） |
| F523 | 未知模型上下文上限乐观回退，告警失火 | error | P2 | 漏报 |
| F524 | parse_trend 第三消费者表头契约与写入侧互斥，解析恒空 | error | P2 | 漏报（跨区） |
| —（误报） | 无整体误报；F504 计数笔误（10→11）、F503 md 侧子论断修正 | — | — | 子论断修正 |
| —（异议） | F514 M→P2（同名 Severity 词表分裂）；F513 M→P2 弱异议 | — | — | 严重度异议 |
