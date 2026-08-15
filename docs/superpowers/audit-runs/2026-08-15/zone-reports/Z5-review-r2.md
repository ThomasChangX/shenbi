# Z5 独立复核报告 r2（fresh-context，2026-08-15 轮）

- 复核 agent: Z5-review-r2（与初审者、复核 r1 均无关的独立上下文）| 编号段: F525–F599（实用 F525–F528；初审 F501–F514、r1 F515–F524）
- 复核对象: docs/superpowers/audit-runs/2026-08-15/zones/Z5.files 全部 13 文件（audit/ 5 + cost/ 5 + orchestration/ 3），全量重读（非 diff 抽查）
- 本轮新增角度（与前两轮不同）: **(a) 词表/字面量全仓双向核对**——FileChange.status、FileOwnership.level、TokenUsageRecord 字段、AuditResult 字段、trace action/ActorRole、drift 字符串词表，生产者↔消费者双向对账；**(b) 引用断链重扫**——Z5 各模块 docstring 声称的消费方/生产行为 vs 实际调用方存在性（含 spec 锚点存在性）
- 只读约束遵守: 除本报告外未创建/修改/删除任何仓库文件；未执行 pytest；未运行 shenbi-dispatch/pipeline。所有 `uv run python -c` 仅做 import/纯函数/临时目录验证（tempfile.TemporaryDirectory，退出即清理）。
- 核心复核结论一句话: **初审 14 条 + r1 10 条均独立复核成立、无一条整体误报；本轮词表双向扫描新发现 4 条漏报（读路径副作用、快照读取崩溃面、契约字段写-only、parametric-glob 死分支+docstring 落空），并证实 FileChange.status 词表在 src 内零消费、"cost 每 dispatch 落一行"的 docstring 声称与实际接线断链。**

---

## 一、漏报（初审与 r1 均未发现；均附实跑证据）

### F525 | TokenLedger 读路径构造即创建 cost/ 目录：读操作带 FS 副作用，且 cost 为普通文件时读路径直接崩溃 | error | P2（低影响）
- 证据: src/shenbi/cost/ledger.py:56（`__init__` 内无条件 `self.ledger_path.parent.mkdir(parents=True, exist_ok=True)`）+ src/shenbi/cost/report.py:40（`render_report` 纯读路径 `TokenLedger(project_dir).summarize()`）+ tools/lint_no_fs_mutation.py:78（`_PATH_WRITE_METHODS = {"write_text","write_bytes","unlink"}`、:80 `_WRITE_CHARS="wax"`——**mkdir 完全不在 lint 检测集内**，读路径副作用无护栏）
- 根因: 目录创建职责放在构造器而非写方法（`record()`）；任何"只想读"的构造（report、未来的 summarize 消费者）都产生副作用
- 验证（已运行）:
  ```
  $ uv run python -c "...p=TemporaryDirectory(); TokenLedger(p); print(before, after)"
  before: [] -> after: ['cost']                      # 读构造即建目录
  $ uv run python -c "...(p/'cost').write_text('file'); TokenLedger(p).summarize()"
  CRASH on READ path: FileExistsError [Errno 17] File exists  # exist_ok 只豁免目录
  ```
- 影响: `shenbi-cost report <dir>` 在从未有 API 计量的项目里留下一个空 `cost/` 目录；`cost` 恰为普通文件时报告命令崩溃
- 建议方向: mkdir 挪进 `record()`（唯一写入口）；或 `exist_ok` 外再捕 FileExistsError
- 定级依据: 判定表 P2（边界/错误处理缺陷）；实际影响小，如实标注低影响

### F526 | snapshot_tree 文件读取零异常防护：非 UTF-8 / 目录 / TOCTOU 均使审计链崩溃（F517 同族、不同触发面） | error | P2
- 证据: src/shenbi/audit/snapshot.py:59（`out[rel] = p.read_text(encoding="utf-8") if p.exists() else None`——无 try；exists 与 read 之间有竞态；exact 声明路径若为目录则 `p.exists()` 为 True）+ src/shenbi/dispatcher/executor.py:264（**pre 快照崩溃 → dispatch 根本不执行**）与 :284（**post 快照在 finally 内崩溃 → 掩盖 rc、record_audit_outcome 永不执行、write-audit.jsonl 行丢失**——与 r1 F517 相同的 Python finally 语义）
- 根因: 审计链假定 watch 面内文件恒为可读 UTF-8 文本；r1 F517 只覆盖了 parse_records 的坏 YAML 崩溃（write_audit.py:54），快照读取本身（更上游、两个时机各一次）无任何包裹
- 验证（已运行）:
  ```
  $ uv run python -c "...(root/'truth'/'pending_hooks.md').write_bytes(b'# x\n\n\xff\xfe binary \x00\n'); snapshot_tree(root, ['truth/pending_hooks.md'])"
  CRASH: UnicodeDecodeError 'utf-8' codec can't decode byte 0xff in position 5
  ```
- 影响: (a) pre 时机：合法 dispatch 被未控异常整体阻断（可用性故障）；(b) post 时机：审计记录丢失 + 掩盖 dispatch 真实结果（F517 已确立的机制，这里多一个触发源）
- 建议方向: read_text 包 try，非 UTF-8/不可读降级为 `None` + WARN（fail-open 但留痕），或降级为一条 violation（fail-closed 不崩）
- 定级依据: 判定表 P2（边界处理缺陷）。不沿用 F517 的 P1：F517 的 P1 依赖"LLM 写坏 YAML 是常态失败模式"，而 watch 面内出现二进制/非 UTF-8 文件在当前全文本写入链（API/IDE 均写 UTF-8 文本）下概率显著更低

### F527 | 契约字段写-only 词表：FileChange.status 在 src 零消费；AuditResult.skill、TokenUsageRecord.timestamp/.model 零读者 | error | M
- 证据:
  - `grep -rn '\.status' src/shenbi/audit/ src/shenbi/contracts/ownership.py src/shenbi/dispatcher/executor.py` → **0 命中（exit 1）**；`FileChange(` 全仓构造仅 snapshot.py:100/102/104/106/111/118（生产）与 tests/unit/contracts/test_ownership.py、tests/unit/audit/test_snapshot.py:34-55（断言仅存于测试）
  - src/shenbi/audit/record.py:23-35：`record_audit_outcome(round_dir, skill, result)` 用独立 `skill` 参数，从不读 `result.skill`（executor.py:285-286 传同一值，不会分歧，但 AuditResult.skill 为写-only 字段）
  - `grep -rn '\.timestamp\b|\.model\b' src/shenbi/cost/ src/shenbi/pipeline/dispatch_helper.py` → 0 读者；report.py 消费面仅 prompt/completion/total_tokens、calls、estimated_cost_usd、skill、chapter（ledger.py:126-139）
- 根因: 数据契约按"forensic 完备性"设计字段，未按消费面裁剪或补读者
- 验证: grep 输出如上（均已实际运行）；report.py:38-81 全读确认无 model/timestamp 引用
- 影响与意义: (a) **证实并强化 F502/F508**——check_write_ownership 对 status 整体（不止 "deleted"）零消费，"unchanged 缺失"（F508）确为纯 latent；F502 的一行修复将引入该词表的首个 src 消费者；(b) model 字段零读者 + F523（未知模型乐观回退）叠加：多模型混合部署的成本报告完全不披露 model 构成，单价差异不可见
- 建议方向: report 的 per-skill 表加 model 列（或最少在混模型时注记）；AuditResult.skill 二选一（删字段或让 record 用 result.skill）
- 定级依据: M（无行为错误；词表/契约卫生问题）

### F528 | snapshot.py parametric-glob 展开分支生产不可达：docstring "重新展开使新增文件可见" 对 parametric 契约落空，跨章越权写结构性不可见 | error | P2
- 证据: src/shenbi/audit/snapshot.py:37-41（`glob_pat = globs.get(pat)` 分支，键为**原始 parametric literal**，如 `chapters/chapter-N.md`）+ src/shenbi/dispatcher/executor.py:238（watch = `derive_output_files(skill, chapter, ctx=ctx)`——**恒返回已解析 literal**，如 `chapters/chapter-1.md`）→ `globs.get("chapters/chapter-1.md")` 恒 None → 永走 exact 分支（:46-47）；snapshot_tree 生产唯一调用方即 executor（grep 确认 :264/:284 仅两处）
- 根因: 展开器的键空间（原始 parametric 形态）与唯一生产调用方传入的形态（已解析 literal）错位；`resolve_or_skip_ctx` 从不回传原始 literal（_shared.py:50-59）
- 验证（已运行）:
  ```
  $ uv run python -c "...root 下建 chapters/chapter-1.md、chapter-2.md"
  parametric_globs keys: [('chapters/chapter-N.md', 'chapters/chapter-*.md'), ...]
  A: snapshot_tree(root, ['chapters/chapter-N.md'])  -> ['chapters/chapter-1.md', 'chapters/chapter-2.md']   # 原始形态：glob 分支可见全部章文件
  B: derive_output_files('shenbi-chapter-drafting', chapter=1) -> ['chapters/chapter-1.md', 'chapters/chapter-1-decisions.json']
     snapshot_tree(root, B) -> {'chapters/chapter-1.md': 'one', 'chapters/chapter-1-decisions.json': None}    # executor 实际形态：chapter-2.md 不可见
  ```
- 影响: (a) snapshot.py:52-54 docstring 声称的"每次（pre/post）都重新展开，使 dispatch 新写的文件出现在 post"对 parametric 契约不成立（重展开机制从未触发，可见性仅来自 exact 分支的 exists() 轮询）；(b) chapter-1 的 dispatch 越权写 chapter-2.md 不进 pre/post——F520"面外写入不可见"的具体新实例（跨章维度）；(c) 分支呈 production-dead / test-alive 僵尸（tests/unit/audit/test_snapshot.py:25 恰用原始形态喂入保活），与 F506 同型但更轻
- 建议方向: watch 传入时保留原始 parametric literal（与 F501 的 declared 侧修复同根同向），或 _expand_patterns 对 resolved 路径反查所属 glob
- 定级依据: 判定表 P2（死代码 + 文档↔代码漂移）；功能后果已被 F520 的系统性结论涵盖，本条补具体位置与 docstring 断言

### 补强（不占新编号）
1. **F504 补强（本轮角度 b 唯一 docstring 断链命中）**: src/shenbi/cost/ledger.py:3-4 模块文档断言 "Each API dispatch appends one self-contained record"——实际 11 个 dispatch_skill 调用点仅 3 处传 state=（chapter_loop.py:1274/2831/3003 实看 kwargs 确认；parallel_dispatch.py:86-91 kwargs 至 shared_context 止，无 state），`if state:` 门控（dispatch_helper.py:~1310 实看）下 8 条路径不落账。docstring 声称的生产行为与接线事实漂移，root cause 归 F504，此处补 Z5 属地内的文档面。
2. **F507 补强（第二处同模式死防御）**: src/shenbi/dispatcher/executor.py:237-240 `_audit_watch_paths` 的 `try/except ContractError: return []` 为死臂——derive_output_files 已在内部吞掉 ContractError（_shared.py:60-61 恒返回 list，从不 raise）。与 write_audit.py:25-26 裸 except 同族的第二处（此处在 Z5 消费链上）。
3. **F513/F506 补强**: escalation_bridge.py:22 `except (ValueError, IndexError)` 的 IndexError 臂不可达——:17 `len(cells) >= 7` 已守卫 `cells[6]`（:19）。

---

## 二、误报（对初审**和** r1 均可反驳的）

**无整体误报。** 初审 14 条（F501–F514）与 r1 10 条（F515–F524）逐条独立复核，全部成立。本轮 fresh 复核的关键实证：

- F501/F502/F503/F508/F509/F515/F516/F520 机制: 代码级重读确认——ownership.py:114-115（field 级只查 changed_top_keys）、:120-124（record_create 只查 deleted/modified）、:125-135（record_field 只查 new/deleted ids + modified keys）、snapshot.py:99-104（added/deleted 早退不带 diff 信息）、:103-104（pre==post → "modified"）、:82-83（`str(r.get("id"))` 键坍缩）、write_audit.py:51-56（drift 只看 post 不看本次是否改动）
- F504: 11 个 dispatch_skill 调用点 fresh grep（输出见任务记录）；3 处 chapter_loop 多行 kwargs 逐一看（均含 state=state）；8 处未传（含 parallel_dispatch.py:86-91 多行形式核到 kwargs 结尾）
- F505: dispatch_helper TokenLedger.record 调用处 `getattr(state, "chapter", 0) or 0` 实看；_dispatch_via_api 本地 chapter 变量实看（r1 补强成立）
- F518: 路由代码实看（dispatch_helper.py:1858-1870: API key → `_dispatch_via_api`，IDE → `_dispatch_via_ide`，均无 write-audit）
- F519/executor 快照根: executor.py:30-31（`PROJECT_DIR = REPO_ROOT`）、:264/:284 实看
- F521: 实跑 `load_contract('shenbi-foundation-review')` → writes+updates = `['foundation/review_report.md']`，genre-config.json 不在面内（死条目确认）
- F522/F523: estimate.py:44-57/:16-21/:35-48 代码复核与 r1 一致
- F524: compute_drift.parse_trend（:161-209，表头定位语义）代码实读确认
- r1 §8 非问漏项抽查: `diff docs/framework/truth-files.yaml site/framework/truth-files.yaml` → 无输出（两份相同，成立）

子论断级修正: **无新的**。r1 已修正的两处（F504 计数 10→11、F503 md 侧子论断）经本轮复核均正确。

---

## 三、覆盖空洞（本轮角度的扫描结论）

1. **词表双向对账总表（角度 a，此前两轮未做过）**:
   | 词表 | 唯一定义源 | 生产者 | src 消费者 | 结论 |
   |---|---|---|---|---|
   | FileChange.status | contracts/ownership.py:22 | snapshot.py 6 处 | **0**（仅测试断言） | 写-only 词表 → F527 |
   | FileOwnership.level | contracts/ownership.py:31 | 同文件 | 同文件（:114/:120/:125） | 闭环，无漂移 |
   | TokenUsageRecord 8 字段 | cost/ledger.py:38-47 | record() | 6/8（timestamp、model 零读者） | → F527 |
   | AuditResult 4 字段 | audit/_shared.py:30-35 | audit_writes | violations/drift/checked_files 有读者；**skill 无** | → F527 |
   | trace action | 无 Literal（trace/event.py:61 `action: str`） | MATERIALIZE/COMPACTION/LEGACY_MIGRATION/GATE_FAIL/AUDIT_PASS（全仓 grep） | 无语义消费（G7 只验 hash 链，g7_trace.py:53 经 verify_chain） | 自由字符串词表——不违反 enums 声明（无 Literal 即无 import 义务），但词表治理未覆盖 action，记录为空洞 |
   | ActorRole "GATE" | contracts/enums.py:9 | record.py:46 等 4 处 | 类型约束 | 词表内，合规 |
   | drift 字符串 | 无（自由文本两种形态: drift.py:84/:92） | detect_cross_section_drift | 仅透传入 jsonl/trace，无解析器 | 无机械断链；但与 compute_drift.DriftKind（MONOTONIC_DECLINE/BELOW_MEAN_2SIGMA/VOLUME_DECLINE）构成**两套互不相通的 "drift" 词表**（write-audit.jsonl 的 drift 行 vs truth/audit_drift.md 的 findings），术语重叠无机械链接，读者易混淆 |
2. **docstring 声称消费方/行为核对（角度 b）: 13 文件全部核对，除 cost/ledger.py:3（并入 F504 补强）外全部成立**——_shared.py "executor.py will top-level import derive_output_files"（executor.py:16 属实）；pricing.py 引用 `_ENV_LLM_MODEL`/`_DEFAULT_MODEL`（dispatch_helper.py:67/:74 属实，镜像成立）；record.py TraceWriter seam（trace/writer.py:65-100 append 关键字签名逐参匹配；pydantic ValidationError ⊂ ValueError、corrupt trace 末行 JSONDecodeError ⊂ ValueError，均仍在 record.py:52 捕获面内——seam 的"签名失败不丢审计"承诺成立）；estimate.py "Used to WARN..."（dispatch_helper.py:1555 唯一调用点，注入 structlog logger）；snapshot/write_audit 的"判据 12"（records/drift.py:1、parser.py:1 同引，docs/superpowers/plans/specs 锚点存在）；escalation_bridge "spec §6.3"（check.py:1 同引，锚点存在）；cost/__init__ "spec 16"（archive/2026-07-19-03 plan 存在）；escalation_bridge kwargs ↔ check_escalation 签名（check.py:53-64）逐参匹配；scoring_bridge `result["agreed"]` ↔ check_scorer_agreement 返回键（scoring.py:247-251）匹配。
3. **write-audit.jsonl 零程序化读者**: src/+tools/ grep 仅 record.py 自身（写方）与 tests；`--write-audit-drift` 是 compute_drift 写 truth/audit_drift.md 的开关、与 write-audit.jsonl 无关（本轮曾疑为读者，读码排除）。record.py 称其为"Tier B 审计结果的真理之源"——现态为 forensic-only（人工/G7 不读它；trace.jsonl 侧的 AUDIT_PASS/GATE_FAIL 事件才有 G7 hash 链消费者）。docstring 未声称程序化读者，不断链，记录为观测。
4. **读路径副作用维度**（→ F525）与**快照读取崩溃面维度**（→ F526）: 前两轮分别聚焦调用形状与声明面↔磁盘面对账，未扫描"构造器副作用"与"读取 I/O 异常面"。
5. **lint 检测盲区**: tools/lint_no_fs_mutation.py 不检测 mkdir（检测集仅 write_text/write_bytes/unlink/open(w|a|x)/os+shutil 变更）——F525 的副作用因此无护栏，顺带确认 cost/ledger.py 在 PERMANENT_ALLOWLIST（:33-39）整体豁免。

---

## 四、严重度异议（无权改定级，仅提异议+理由）

1. **支持 r1 对 F514 的 M→P2 异议，并补新证据**: 本轮词表扫描发现 enums.py 不仅存在"10+ 处 Literal 未从其 import"的违反，**部分词表连单一来源都未建立**——FileChangeStatus / FileOwnershipLevel 类型在 enums.py 中不存在（contracts/enums.py:11-16 仅 Severity/Verdict/CPZone/ActorRole 四项），ownership.py:22/:31 的两个 Literal"想 import 也没处 import"。词表治理缺口比"违反声明"深一层，维持 M 与判定表"文档↔代码漂移=P2"不符的判断。
2. 其余定级复核意见: F501/F502/F504 P0、F503/F505/F515–F519 P1、F506/F507/F508/F509/F510/F511/F520–F524 P2、F512/F513 M 均与判定表相符，无新异议。r1 对 F513 的弱异议（M→P2）本轮无新证据，维持"倾向 P2 亦可接受、维持 M 自洽"的中立。
3. 自评新 finding 定级依据已随条目注明: F525 P2（边界缺陷，低影响）、F526 P2（F517 同族但触发概率显著更低，不继承 P1）、F527 M（无行为错误）、F528 P2（死代码+文档漂移+越权盲区实例）。

---

## 五、验证记录汇总（本轮实跑清单）

| 验证 | 命令要点 | 结果 |
|---|---|---|
| F525 复现 | 临时目录 `TokenLedger(p)`（不写） | `before: [] -> after: ['cost']` |
| F525 边界 | `(p/'cost')` 为普通文件后 summarize | `FileExistsError [Errno 17]` |
| F526 复现 | watched md 写入 `\xff\xfe\x00` 字节后 snapshot_tree | `UnicodeDecodeError` 崩溃 |
| F528 复现 | snapshot_tree(原始 literal) vs (executor 已解析 watch) | A 全章可见 / B 仅 chapter-1 |
| F521 抽查 | `load_contract('shenbi-foundation-review')` | surface=['foundation/review_report.md'] |
| F504 复核 | grep dispatch_skill 11 处 + 3 处多行 kwargs 实看 | 3 传 state / 8 未传 |
| FileChange.status 消费 | grep `.status`（audit/ownership/executor） | 0 命中（exit 1） |
| timestamp/model 读者 | grep `.timestamp`/`.model`（cost/ + dispatch_helper） | 0 命中（exit 1） |
| result.skill 读者 | grep（record.py） | 0 命中（exit 1） |
| trace action 词表 | grep `action="` 全仓 | 5 种自由字符串，无 enum |
| orchestration 引用 | grep src/+tests/ | 仅 tests + chapter_loop.py:1356 注释 |
| truth-files 双拷贝 | diff docs/ vs site/ | 相同 |
| spec 锚点 | 判据 12 / §6.3 / spec 16 | 锚点均存在 |

## 六、汇总表

| 编号 | 标题 | 类别 | 严重度 | 与初审/r1 关系 |
|---|---|---|---|---|
| F525 | TokenLedger 读路径 mkdir 副作用（cost 为文件时读崩溃） | error | P2 | 漏报（读路径副作用维度缺失） |
| F526 | snapshot_tree 读取零防护：非 UTF-8/目录/TOCTOU 崩溃（pre 阻断 dispatch / finally 掩盖 rc） | error | P2 | 漏报（F517 的上游同族触发面） |
| F527 | 契约字段写-only：FileChange.status 零 src 消费；AuditResult.skill、timestamp/model 零读者 | error | M | 漏报（词表双向核对产出） |
| F528 | parametric-glob 展开分支生产不可达 + docstring "重新展开"落空 + 跨章越权不可见 | error | P2 | 漏报（F520 具体新实例 + 新位置） |
| —（补强） | ledger.py:3 docstring "Each API dispatch"断链（F504）；executor.py:237-240 死 ContractError 臂（F507）；escalation_bridge 死 IndexError 臂（F513） | — | — | 补强 |
| —（误报） | 无整体误报（初审 14 + r1 10 均成立；无新子论断修正） | — | — | — |
| —（异议） | 支持 r1 F514 M→P2，新证据：FileChangeStatus/FileOwnershipLevel 在 enums 无单一来源 | — | — | 严重度异议 |
