# Z2 分区独立复核报告 r1（2026-08-15 轮）

- 复核 agent: Z2 fresh-context 独立复核（与初审无关）
- 复核方式: 38 文件全量重读 + 本轮专项角度（形状家族枚举 + 调用形状全仓核对）+ `uv run python -c` 行为验证 + git 考古
- 编号段: F224–F230（初审已用 F201–F223）
- 只读约束遵守: 未修改任何仓库文件（本报告除外）、未运行 pytest、未执行 shenbi-dispatch/pipeline

## 总结论

初审 23 条 finding 逐条抽查（含 7 组实跑复现）**无一虚构**，质量高。但初审在本区最核心的链路上有一个重大漏报：**Layer B 字段级 reads 过滤在生产中完全断裂（自 2026-07-20 dd1fc62 回归）**，初审 F201 还基于"该过滤在运行"的前提定级 P1，且 F210 汇总把 fields.py 列入"已接线"——与事实相反。本轮角度（调用形状核对）恰好命中此断裂。

---

## 一、漏报（新 finding）

### F224 | Layer B 字段级 reads 过滤全链路断裂：唯一生产调用点是不可达死代码（dd1fc62 回归） | error | P1
- 证据:
  - `src/shenbi/pipeline/dispatch_helper.py:581-589` — `reads: list[Any] = contract.get("reads", [])` 后 `if isinstance(read_path_entry, dict):` 取 `read_path_entry.get("fields", [])`；
  - `src/shenbi/contracts/legacy.py:169-176` — `_validate` 已把 reads 归一化为纯 `list[str]`，fields 存入独立的 `read_fields` 键；
  - `src/shenbi/pipeline/dispatch_helper.py:604-605` — `if fields:` 永假 → `filter_to_fields` 生产调用不可达；
  - `src/shenbi/gates/g1.py:102-144` — `check_fields_exist`（G1 侧字段存在性 WARN）**零生产调用方**（grep 全仓仅测试直接调用，`gate_G1` 从未调用它）。
- 根因: git 考古确认是回归。`git show dd1fc62`（2026-07-20，PR #19，标题自称 "fix: P0 blocking defects — dead paths"）把原先**正确**的接线 `fields_map = contract.get("read_fields", {}); fields = fields_map.get(resolved) or fields_map.get(read_path); if fields: filter_to_fields(...)` 替换为对已归一化 reads 列表做 dict 形状检查——该分支永假。即：一次"修死代码"的提交制造了新的死代码并静默关掉了整个 Layer B 特性，至今近一个月无人发现。
- 验证（实际运行）:
  ```
  $ uv run python -c "from shenbi.contracts.legacy import load_contract; c = load_contract('shenbi-foreshadowing-track'); print(c['reads'], c['read_fields'])"
  reads: ['chapters/chapter-N.md', 'truth/pending_hooks.md', 'truth/chapter_summaries.md']
  read types: ['str', 'str', 'str']          ← dict 分支永假的直接证据
  read_fields: {'truth/pending_hooks.md': ['活跃伏笔', '伏笔时间线'], ...}

  $ git show dd1fc62 -- src/shenbi/pipeline/dispatch_helper.py   # diff 显示旧代码用 read_fields 映射（正确）→ 新代码 dict 检查（永假）

  $ grep -rn "check_fields_exist" src tools --include="*.py" | grep -v def
  # 仅 dispatch_helper.py:1214 注释 + tests 直接调用 — gate_G1 内无调用
  ```
- 影响: ① 违反 AGENTS.md 显式契约 "The dispatcher filters file content to only declared fields before the LLM sees it (LangChain 'filtered portions' strategy)"；② 全仓 35 个 `{file, fields}` 声明全部无效，API/IDE 两条派发路由（dispatch_helper.py:1526/1738 → `_build_skill_prompt`）注入的是**全量 truth 文件**而非声明字段——显著 token 浪费（正是 Layer B 要省的那部分）；③ G1 侧字段漂移 WARN 同样从不发生（skill 作者看不到字段改名警告）。
- 建议方向: 恢复 dd1fc62 之前的 `contract["read_fields"]` 映射查找（或按 `_input_key` 键位查），同时接回 `check_fields_exist` 于 gate_G1；补一条"_build_skill_prompt 产物只含声明字段"的集成测试防回归。
- 定级依据: 决策表 P1 双触发（"违反 AGENTS.md 显式契约" + "显著 token 浪费"）。非 P0：执行结果不受污染，只是输入过量。

### F225 | write_semantics `key` meta 全仓零消费者（18 处声明为死数据） | dead-wire | P2
- 证据: `src/shenbi/contracts/legacy.py:76-90`（`key` 进入 meta→write_semantics）；声明分布实测 `updates.key`×17 + `writes.key`×1；消费端 grep：dispatch_helper.py:1095 取 semantics 后仅 :1142 读 `mode`（且只用于 log.info），`key` 无任何读取点。
- 验证: `grep -rn 'get("key")\|\["key"\]' src/shenbi --include="*.py"` → 零命中。
- 根因: `key` 声明为"state-settling 直接调 write_truth_file 时用"（dispatch_helper.py:1076-1080 注释），但契约层从未提供读取接口，语义键在调用方另行手写——契约声明与执行各说各话。
- 建议方向: 要么让 write_truth_file 调用点从 write_semantics 读 key（单一源），要么从 SKILL.md 契约中删掉 key 字段。

### F226 | `no_op_behavior: skip_write` 从未被消费：docstring 声称 honoring 但 skip_paths 无任何调用方传入 | error | P2
- 证据: `src/shenbi/pipeline/dispatch_helper.py:1067,1070`（docstring "honoring no_op_behavior ... honors only no_op_behavior: skip_write (paths in skip_paths ...)"）；:1064/1088（`skip_paths` 形参默认 None → `skip = skip_paths or set()` 恒空集）；两个生产调用点 :1670/:1782 均不传 skip_paths；全仓 grep `no_op_behavior` 仅命中 docstring 与 legacy.py 注释，无代码读取。
- 声明方: 4 个技能实测声明 `no_op_behavior: skip_write`（shenbi-anti-detect:16、shenbi-style-polishing:22、shenbi-chapter-revision:21、shenbi-length-normalizing:18）。
- 根因: 特性只完成了"声明 + G0 校验存在性"半环，执行半环从未接线；文档（docstring）超前于实现。
- 验证: `grep -rn "no_op_behavior" src/shenbi --include="*.py"` → 仅 dispatch_helper.py:1067/1070 docstring + legacy.py:80 docstring。
- 建议方向: 在 `_write_parsed_outputs` 内从 `semantics[rel_path].get("no_op_behavior")` 派生 skip 集，或修正 docstring 并在契约文档标注未实现。

### F227 | 字段声明指向不存在的键：review-group-character 声明 `fields: [povMode]`，genre-config.json 无此键 | error | P2
- 证据: `skills/shenbi-review-group-character/SKILL.md:59`（`- {file: genre-config.json, fields: [povMode]}`）与 :256（"读取 genre-config.json 的 povMode"）；实测两个真实 `novel-output/*/genre-config.json` 顶层 8 键不含 povMode，`pacing` 子对象仅 hardRange/maxChaptersPerCycle/minChaptersPerCycle/softRange。
- 验证（实际运行）: `json.load` 两文件 → `['approval','auditDimensions','chapterTypes','customRules','fatigueWords','pacing','updated','version']`。
- 根因: povMode 曾属 genre-config 产出（docs/specs 归档可见），产出侧移除后消费声明未同步——与 F214（tropeInventory 同类漂移）同族，但方向相反（消费侧指向已删除的键）。
- 影响: 当前被 F224 掩盖（过滤死了没人发现）；**一旦修复 F224**，该声明将每次触发零匹配 escape-hatch → 全文件 + WARN，Layer B 对该技能退化为无效。
- 建议方向: 与 F224 修复联动：先全仓校验 35 个 dict+fields 声明的字段在真实文件中可匹配，再接线。

### F228 | resolve_contract_path 中 family 占位符命中后提前 return，同路径 AC-NNN 的 anchor 语义丢失 | error | P2（潜伏）
- 证据: `src/shenbi/contracts/paths.py:104-120` — family 分支 `return resolve_chapter_path(path, chapter)`（:117）先于 anchor 分支（:118-120）执行，共现时 AC-NNN 被 `resolve_chapter_path` 的无界 `NNN` 替换成章号。
- 验证（实际运行）:
  ```
  resolve_contract_path('audits/arc-N/AC-NNN.md', 25, PathContext(chapter=25, arc=2, anchor=7))
  → 'audits/arc-2/AC-025.md'   （期望 AC-007.md）
  ```
- 现状: grep 全部 SKILL.md + truth-files.yaml，无任何声明路径同时含 family-N 与 AC-NNN（anchor-curate 只写 AC-NNN，escalation-review 只写 escalation-N）——与 F208 同族的潜伏缺陷（共现占位符处理不全）。
- 建议方向: family 替换后不提前 return，先做 AC-NNN anchor 替换再委托 bare-N 语义；与 F207/F208 一并修。

### F229 | FileOwnership.read_keys 零消费者，foundation-review 的 OWNERSHIP 条目完全装饰性 | dead-wire | P2
- 证据: `src/shenbi/contracts/ownership.py:33`（read_keys 字段定义）、:77-80（foundation-review 条目仅 read_keys={"tropeInventory"}、write_keys 空）；`check_write_ownership`（:101-136）只读 write_keys；grep `.read_keys` 全仓（排除本模块）零命中。
- 根因: Tier B 审计设计里读越权检测未实现（audit/writes 只查写面），但矩阵已收录读键，制造"读所有权已被执行"的假象。
- 验证: `grep -rn "read_keys" src tools --include="*.py" | grep -v contracts/ownership.py` → 零命中。
- 建议方向: 删 read_keys 或实现读越权检查；至少在模块 docstring 注明"read_keys 目前无执行点"。与 F214（tropeInventory 键本身已不存在）叠加：该条目引用的键在真实文件中也不存在。

### F230 | PacingDesign.from_markdown 永不填充 chapter_sequence；G4 的 no_beat_data 分支不可达 | dead-code | P2
- 证据: `src/shenbi/contracts/skills/pacing_design.py:82,125-129`（`chapter_sequence: list[str] = []` 从未赋值）→ `_no_three_consecutive_same`（:65-74）在唯一生产消费路径（g4/pacing_design.py:47 → from_markdown）永不触发；`src/shenbi/gates/g4/pacing_design.py:50-52` 的 `if not model.beats: mf.append("G4.pd.no_beat_data")` 不可达——beats 为空时 `_four_beats_present` 先抛 ValidationError 走 except 分支（:53-56）。
- 验证（实际运行）: 构造只提及部分拍/场景类型的 rhythm 文档 → `from_markdown` 直接 raise（`missing beats: {...}` 或 `expected 6-12 scene types, got 4`），永远到不了 `no_beat_data` 检查。
- 根因: from_markdown 的解析能力（拍/线/场景类型）与模型校验器集合（另含 chapter_sequence 三连同型检查）不对齐；死分支是防御性代码写在错误的层。
- 建议方向: from_markdown 补 chapter_sequence 解析（或删 `_no_three_consecutive_same` 对 markdown 路径的伪装）；G4 删除不可达分支。与 F223（首匹配正则污染）同文件修复。

---

## 二、误报（初审站不住的条目）

**逐条复核后无完全站不住的条目**。实跑复现了 F202（禁用维度+空 customRules 通过）、F203（嵌套 JSON 误取内层）、F207（arc-25 应为 arc-2）、F208（volume-25 应为 volume-3）、F212（medium 强制 rationale）、F223（散文污染：4 个已知类型词即触发 "expected 6-12 scene types, got 4"）、F214（真实文件 8 键无 tropeInventory）、F205（derive_file_type('shenbi-chapter-drafting') → 'decisions'，g2.py:83-84 跳过 .md，round-exec.sh 无 G4）——全部成立。

唯一需要修正的是 **F210 汇总明细中的一处事实错误**（部分误报）:
- 初审 F210 汇总把 `fields（多消费方）` 列入"已接线"清单——不实。`filter_to_fields` 全仓唯一生产调用点（dispatch_helper.py:605）不可达（见 F224），`match_field` 仅被 fields.py 内部使用。fields.py 属于**未接线**层，应从 F210 的"已接线"清单移出并指向 F224。
- 同理，初审 fields.py 节的验证叙述"fixture 抽查: ... chapter-drafting 声明的 3 字段当前全匹配（bug 未被现实触发）"隐含"过滤在生产运行"的前提——该前提错误（过滤根本不运行），此叙述应随 F224 修正。

---

## 三、覆盖空洞

1. **Layer B 集成测试缺失（F224 直接成因）**: `tests/unit/pipeline/test_field_filtering.py` 与 `tests/unit/contracts/test_fields.py` 只测 `filter_to_fields` 函数本体，无任何测试断言"_build_skill_prompt 产出的 user_prompt 只包含声明字段"——dd1fc62 回归因此漏网近一个月。修复 F224 时必须补此层测试。
2. **load_contract 归一化形状无契约锁定**: "reads 恒为 list[str]、fields 在 read_fields"这一形状约定无测试守护，调用方（dispatch_helper）对形状的假设漂移时无信号。建议加一条断言形状的契约测试。
3. **skip_paths 参数（dispatch_helper.py:1064）零调用方**: 参数连同 no_op_behavior 语义（F226）既无生产也无测试覆盖。
4. **占位符共现形状未测**: test_path_context.py 13 tests 覆盖单占位符/载体行主线，但双 family（F208）、family+anchor 共现（F228）、ctx 缺 family 值（F207）三种形状组合零覆盖——初审在 F207/F208 已各自记录"无测试"，F228 补充第三种组合。
5. 初审标注的 must-test 项全部维持: dispatcher/cli.py 整模块（F216）、SHENBI_G1_SKIP_READS 块与 dispatch_exception 路径（executor.py:182-201,271-282）、genre_config 规则 7（F202）、legacy.py 归一化守卫（71/73/88）、decisions rationale 长度上限（35/58）、registry version!=1（87）。

---

## 四、严重度异议（无权改定级，仅提异议）

- **F201 P1 → 建议 P2**: F201 引用的生产调用点（dispatch_helper.py:605）本身不可达（F224），escape-hatch 部分匹配语义违反当前**生产影响为零**，属潜伏缺陷。建议 F201 降 P2 并与 F224 合并处置（修复接线时同步改为逐字段匹配）；P1 的"现实触发面"由 F224 承担。若评审坚持"违反 AGENTS.md escape-hatch 条款即 P1"，保留亦可，但应在条目中注明"当前触发面=0（调用点死代码）"。
- **F210 P2 → 可考虑升 P1（弱异议）**: F210 是"契约层未接线"的 umbrella；本轮证实其范围比初审更大（fields.py 也在内，见 F224）。鉴于 AGENTS.md 声称的派生关系大面积不成立，整体按 P1 umbrella 亦说得通。仅提异议，不定级。
- 其余条目（F202/F203 P1；F204-F209/F211-F223 P2/M）定级与决策表逐条对照后**无异议**。

---

## 五、本轮专项角度发现摘要

### (a) 契约 schema 形状家族枚举 vs 解析分支覆盖
全仓 69 技能 frontmatter 实测分布:
- `reads` 家族: **228 str + 35 dict{file,fields} + 2 dict{file}（无 fields）**——三种形状 `_normalize_read_item` 全覆盖；dict 多余键会被静默丢弃（无现实例）；fields 无 .md/.json 之外扩展名声明（passthrough 分支无现实实例）。
- `writes`/`updates` 家族: **100% dict 形**（87+36），`_normalize_write_item` 的 str 分支零现实实例（容错分支）；meta 键分布 mode×123 / key×18 / no_op_behavior×4——其中 **key 与 no_op_behavior 零消费**（F225/F226），mode 仅 log。
- 字段声明质量: 35 个 dict+fields 中发现 1 例指向不存在键（povMode，F227）——形状合法但语义悬空，在过滤死线的现状下不可见。
- 结论: 解析分支覆盖完备，**消费端接线**才是缺口（F224/F225/F226/F229 四条互证同一模式：声明→归一化之后断线）。

### (b) 关键公共函数调用形状全仓核对
- `filter_to_fields`: 生产调用点 1 处（dispatch_helper.py:605）——形状正确但**不可达**（F224）；测试调用 7 处形状正确。
- `load_contract`/`load_registry`/`bootstrap_registry`: 16 个生产调用点形状全部匹配（无参/单 skill 参数）；无第二 frontmatter 读取器违反 loader-uniqueness。
- `resolve_contract_path`/`resolve_or_skip_ctx`/`parse_path_context`/`format_path_context`/`build_trigger_context`/`resolve_volume_path`: executor×4、dispatch_helper×8、closure×3、triggers×3、audit/_shared×1——实参形状全部匹配（含 kwargs ctx 传递），无参数错位；`resolve_volume_path` 非死代码（closure.py:198 消费）。唯一断裂不是形状错位而是**调用方对返回形状的错误假设**（dispatch_helper 假设 reads 保留 dict 形，实际已归一化为 str）——这正是形状家族核对的价值所在。
- `derive_output_files`/`derive_input_files`/`dispatch_codex`/`dispatch_internal`: 全部调用点位置参数/kwargs 形状核对无误。

## 汇总

| 类别 | 数量 | 条目 |
|---|---|---|
| 漏报 | 7 | F224(P1)、F225(P2)、F226(P2)、F227(P2)、F228(P2)、F229(P2)、F230(P2) |
| 误报 | 0 全假 + 1 处部分误报 | F210 汇总"fields 已接线"子句 |
| 覆盖空洞 | 5 项 | 见第三节 |
| 严重度异议 | 2 | F201 P1→P2（强）；F210 P2→P1（弱） |
