# Z5 独立复核报告 r3（fresh-context，2026-08-15 轮）

- 复核 agent: Z5-review-r3（与初审者、复核 r1/r2 均无关的独立上下文）| 编号段: F529–F599（实用 F529–F530）
- 复核对象: docs/superpowers/audit-runs/2026-08-15/zones/Z5.files 全部 13 文件（audit/ 5 + cost/ 5 + orchestration/ 3），全量重读（非 diff 抽查）
- 本轮新增角度（与前两轮不同）: **计数 A vs B vs C 三方对账**——对 Z5 涉及的双源以上数字做三方核对:
  - (a) 真实产物对账: novel-output/test-validation 的 write-audit.jsonl 行数 vs trace.jsonl 的 GATE_FAIL/AUDIT_PASS 事件数 vs violations 计数与真值
  - (b) token 计数链: `llm_token_usage` 日志事件 vs state.token_usage 内存累计 vs TokenLedger 行数（含 resume 路径）
  - (c) summarize 三口径算术: 行数（非坏行）vs iter_records 数 vs total/by_skill/by_chapter 的 calls 之和
  - (d) 快照链: watch 模式数 vs snapshot dict 大小 vs checked_files 数
- 只读约束遵守: 除本报告外未创建/修改/删除任何仓库文件；未执行 pytest；未运行 shenbi-dispatch/pipeline；未 git add/commit。所有 `uv run python -c` 仅做 import/纯函数/临时目录验证（tempfile.TemporaryDirectory 退出即清理）；对 novel-output 真实产物只读计数。
- 核心复核结论一句话: **前三轮的 24 条 finding 无一整体误报；但计数对账角度在真实生产产物上直接命中一条前三轮全部漏掉、且有生产实证的 P0——`_matches_declared` 从不对裸 glob 契约（`truth/*.md` 等 10 技能 11 条目）做 fnmatch，导致合法 glob 声明写入全部误判"未声明写入"（真实数据: 3 次 GATE_FAIL 阻断）；另发现 state.token_usage 不持久化，resume 后两套成本汇总结构性分歧。初审报告还有两处"grep 验证过"的事实性断言被真实数据证伪。**

---

## 一、漏报（初审/r1/r2 均未发现；均附实跑证据）

### F529 | `_matches_declared` 从不 fnmatch 裸 glob 契约模式：10 技能 11 条 `*` 契约的合法写入全部误判"未声明写入"→ rc=2 阻断（真实生产数据 3 次 GATE_FAIL 实证） | error | P0
- 证据:
  - src/shenbi/audit/write_audit.py:29-36——`_matches_declared` 对每个 declared 模式只做两件事: `pat == relpath`（精确相等）或 `g = globs.get(pat); if g and fnmatch(relpath, g)`（**仅当 pat 是 truth-files.yaml 的 parametric 键**时才映射到 glob 再 fnmatch）。**从不执行 `fnmatch(relpath, pat)` 本身**——当 pat 自身就是裸 glob（含 `*`）时 `globs.get(pat)` 恒 None，两条分支全部落空 → 返回 False。
  - 契约面现实（初审声称"无 `*` 通配契约，grep 验证为空"——事实错误，见"误报"§1）: 10 个技能共 11 条裸 glob writes/updates——shenbi-worldbuilding(`truth/*.md`)、shenbi-truth-sync(`truth/*.md`)、shenbi-sequel-writing(`truth/*.md`)、shenbi-character-design(`characters/major/*.md`,`characters/minor/*.md`)、shenbi-character-extraction(同前两条)、shenbi-canon-import(`import/canon/*.md`)、shenbi-import-analysis(`import/analysis/*.md`)、shenbi-short-packaging(`import/packaging/*`)、shenbi-snapshot-manage(`snapshots/chapter-NNN/*`)(全仓 SKILL.md frontmatter 扫描输出，见验证记录)
  - 生产链路: snapshot 侧 `_expand_patterns`（src/shenbi/audit/snapshot.py:42-45）**正确展开**裸 glob（`elif "*" in pat: Path(root).glob(pat)`）→ 展开出的具体文件进 watch/pre/post；declared 侧 `derive_output_files` 原样返回 `truth/*.md`；审计循环对每个 watch 内文件调 `_matches_declared` → 裸 glob 匹配恒 False → write_audit.py:63-64 记"未声明写入: {rel}（不在 {skill} 契约 writes/updates）"——**判词本身与契约文件内容相矛盾**（`truth/*.md` 就写在契约里），且与框架自身 registry 矛盾（`resolves('truth/*.md', reg) == True`，legacy.py registry 验证通过）。
  - 真实生产实证（novel-output/test-validation/，legacy 审计路由产物）:
    - write-audit.jsonl: 4 行；shenbi-worldbuilding 3 行全部 `blocked: true`，每行 violations 恰为 2 个 glob 展开文件（`未声明写入: truth/bridge_tracker.md`、`未声明写入: truth/character_matrix.md`），`checked_files` = 7 = 5 个精确契约文件 + 2 个由 `truth/*.md` 展开的文件（glob 展开分支在生产的直接证据）；shenbi-escalation-review 1 行 pass、`checked_files=[]`（= F501 方向 b 的生产实证）。
    - trace.jsonl: `('GATE_FAIL','write-audit')×3 + ('AUDIT_PASS','write-audit')×1` 与 jsonl 行一一对应（record.py 计数链自洽——见"覆盖空洞"§1）。
    - 计数对账结论: **violations 总数 6 vs 去重后 2 vs 真实越权数 0**——三数全不一致，分歧根因即本条（同时是 F520"纯假阳性机器"结论的生产实数印证）。
- 根因: 匹配器假设 declared 模式只有两种形态（精确路径 / parametric 键），漏了第三种（契约直接声明的裸 glob——registry.globs 含 `truth/*.md` 等 32 个条目，契约 schema 合法允许）。
- 验证（已运行）:
  ```
  $ uv run python -c "..._declared_patterns('shenbi-worldbuilding')"
  declared: ['novel.json','genre-config.json','world/story_bible.md','world/rules.md','world/locations.md','truth/*.md']
  globs.get('truth/*.md') -> None
  _matches_declared('truth/bridge_tracker.md') = False
  _matches_declared('truth/character_matrix.md') = False
  _matches_declared('truth/pending_hooks.md') = False
  fnmatch.fnmatch('truth/bridge_tracker.md', 'truth/*.md') = True   # 直接 fnmatch 本可命中
  ```
- 影响面: 世界观构建（genesis 阶段）与 truth-sync/sequel-writing 等技能在 legacy 审计路由上，只要项目 truth/ 下存在 .md 文件（真实项目恒成立——test-validation 当前 truth/ 下就有 4 个 .md），dispatch 结果即被误判 GATE_FAIL rc=2，"blocked before tier advance"（executor.py:243-247 docstring）——正常路径被系统性阻断。
- 建议方向: `_matches_declared` 补第三分支 `if "*" in pat and fnmatch.fnmatch(relpath, pat): return True`（或统一改走 registry 概念/parametric/glob 三态解析）；连带补裸 glob 契约的审计测试（现有 test_write_audit.py 全用精确路径技能，恰好绕开本分支——与 F501 的测试盲区同型）。
- 定级依据: 与 F501 同族同级——(a) 正常路径功能错误且有生产实证（3 次真实阻断）；(b) 审计器对契约声明面的静默不认（"契约被静默违反"字面方向）。保守下限亦为强 P1；按"不确定取更高"与 F501 先例取 **P0**。

### F530 | state.token_usage 不入 checkpoint（to_dict/from_dict 均无该字段）: resume 后 print_token_summary 只报 post-resume 用量，与 ledger 累计永久分歧 | error | P2
- 证据:
  - src/shenbi/pipeline/dispatch_helper.py:1327-1336——`token_usage` 是运行期动态挂载属性（`if not hasattr(state, "token_usage"): state.token_usage = {}`），非 PipelineState 声明字段
  - src/shenbi/pipeline/state.py:228-294——`to_dict` 显式字段表（version/genesis/chapter_loop/.../config 共 17 键，无 token_usage）；:299+ `from_dict`/`from_json` 同样不恢复
  - src/shenbi/pipeline/machine.py:31-36——resume 路径 `load_state` 经 `PipelineState.from_json(...)` 重建 state；pipeline/cli.py:405/:500/:579 均消费
  - src/shenbi/pipeline/chapter_loop.py:948——`print_token_summary(state)` 每章完成时输出（"Token usage by skill"）
  - 三方计数链: `llm_token_usage` 日志事件（dispatch_helper.py:1302，不看 state 恒发）≥ state.token_usage 累计（需 state 真值，F504 已覆盖缺口）vs TokenLedger 行数（需 state 真值；API 路由 project_dir 为必填位置参数 dispatch_helper.py:1493，会话内与 counter B 同步）——**会话内 B=C 一致（本轮差分实测 summarize 三口径亦自洽，见验证记录），跨 resume B 重置归零而 C 持续累计** → 两套成本汇总（章末日志 summary vs `shenbi-cost report`）结构性分歧
- 根因: token 计数双轨设计（内存累计 + 持久账本）只持久化了后者；resume 是受支持的一等流程（`just pipeline-resume`，AGENTS.md 列出）
- 验证（已运行）:
  ```
  $ uv run python -c "...s.token_usage={...}; s2=PipelineState.from_json(s.to_json()); print(hasattr(s2,'token_usage'))"
  token_usage after round-trip: <absent>   hasattr: False
  ```
- 影响: 任何 resume 之后的章末/per-skill token summary 只含 post-resume 数据且无任何"不含 resume 前用量"的提示——运维据日志 summary 做预算判断会系统性低估；账本侧（report）才是全量。信息层缺陷、账本无损，故 P2 而非 P1。
- 建议方向: to_dict 增补 `token_usage` 键 + from_dict 恢复；或 print_token_summary 改读 ledger 并删除内存累计轨（单轨化）
- 定级依据: 判定表 P2（边界/缺陷；resume 是正常但非默认路径；ledger 数据无损）

---

## 二、误报（对初审/r1/r2 可反驳的断言）

前三轮 24 条 finding（F501–F528）经本轮 fresh 抽验**无一整体误报**；本轮复核实点: F501（parametric 侧 declared 缺失机制经 escalation-review 生产行 checked=[] 再确认）、F504/F505 链、F520（真实数据 6 violations/0 真阳性直接印证）、F517/F525/F526/F528 机制复读成立。但初审报告有**两处"grep 验证过"的事实性断言被真实数据证伪**（子论断级误报，F529 的证据基础）:

1. **初审交叉验证#2: "无 `*` 通配契约，grep 验证为空"——事实错误**。全仓 SKILL.md frontmatter 扫描实为 10 技能 11 条裸 glob 契约（清单见 F529）。漏检根因: 初审对 `contracts/*.py`/`skills/*.py` 的 writes grep——但契约不在 .py 里，在 SKILL.md frontmatter（legacy.py:1-9 明言 frontmatter contract 块是唯一可编辑位置）。snapshot.py 未覆盖行处置中同句重复（"grep 全部 contracts/skills/*.py 的 writes 无 `*` 模式，生产不可达"）。
2. **初审 snapshot.py 覆盖处置: "43-45（raw `*` 通配模式展开）: acceptable（防御分支）…生产不可达"——事实错误**。真实 write-audit.jsonl 的 worldbuilding 行 `checked_files` 恰含 2 个由 `truth/*.md` 展开的文件——snapshot.py:42-45 是**活跃生产路径**，且其正确性与 write_audit.py:29-36 的缺陷（F529）合谋制造了"观测面可见、声明面不认"的假阳性。该分支处置应从 acceptable 改为 must-test。

---

## 三、覆盖空洞（本轮角度扫描结论）

1. **真实产物三方对账维度三轮缺失**（→ F529）: 初审/r1/r2 的全部验证均为代码推演 + 构造输入复现；对仓库内真实审计产物（novel-output/test-validation 的 write-audit.jsonl 4 行 + trace.jsonl）从未做"行数 vs 事件数 vs 违规真值"计数核对。该角度一次命中: (a) 新 P0（F529）的生产实证；(b) F501 方向 b 的生产实证（escalation-review 行 checked=[]，审计空转后 AUDIT_PASS）；(c) F520 的生产实数（6 violations / 0 真阳性）；(d) record.py seam 计数链在生产数据上自洽（4 行 ↔ 4 事件 ↔ 3 blocked）——record.py 本身无计数问题，缺陷全部位于上游 audit_writes。
2. **token 计数持久化链未查**（→ F530）: 前三轮核了"谁传 state"（F504）与"chapter 键恒 0"（F505），未核 state.token_usage 自身的生命周期（checkpoint 序列化面）。
3. **契约形态学假设未验证**: 代码注释/报告反复以"精确路径 + parametric"两态描述契约面（write_audit.py 匹配器、初审 F501 分析"declared 永不含 parametric literal"），registry.globs 的 32 个裸 glob 条目与 11 条契约引用从未进入任何一轮的形态枚举——这是 F529 横跨三轮未被发现的直接原因。
4. 非问题确认（计数角度的负结果，如实记录）: (a) summarize 三口径算术差分实测一致——临时账本 3 行 + 1 坏行: 非空行 4-坏 1=3 == iter_records 3 == total calls 3 == Σby_skill 3 == Σby_chapter 3，total_tokens 167 == Σby_skill 167；(b) 快照链计数一致: worldbuilding watch 6 模式（5 精确+1 glob）→ snapshot dict 7 条（5 精确含不存在 + 2 glob 展开）→ checked_files 7，无丢漏；(c) API 路由内 counter B 与 counter C 同调用点同步（project_dir 必填），会话内无分歧——F530 的分歧仅在 resume 边界；(d) 真实项目 `**/*score*.json` 数为 0 → F511 噪声在该项目尚无实害（latent）。

---

## 四、严重度异议（无权改定级，仅提异议+理由）

1. 无新异议。前三轮全部定级（F501/F502/F504 P0；F503/F505/F515–F519 P1；P2 ×12；M ×3）经本轮复核与生产数据印证，维持。r1 对 F514 的 M→P2 异议、r1/r2 对 F513 的弱异议，本轮无新证据，维持原立场。
2. 自评定级依据已随条目注明: F529 P0（F501 同族 + 生产实证 + 契约面被审计器静默不认；保守下限强 P1）、F530 P2（信息层分歧、账本无损、resume 边界）。

---

## 五、验证记录汇总（本轮实跑清单）

| 验证 | 命令要点 | 结果 |
|---|---|---|
| F529 复现 | `_matches_declared` ×3 文件 vs 直接 fnmatch | False ×3 / fnmatch True |
| F529 契约面 | 全仓 SKILL.md frontmatter 扫描 writes/updates 含 `*` | 10 技能 11 条裸 glob |
| F529 registry | `resolves('truth/*.md')` / `resolves('truth/bridge_tracker.md')` | True / True |
| F529 生产对账 | write-audit.jsonl 计数 | 4 行 / 3 blocked / 6 viol（全假阳性）/ 21 checked |
| F529 trace 对账 | trace.jsonl action 计数 | GATE_FAIL×3 + AUDIT_PASS×1，与 jsonl 一一对应 |
| F501(b) 实证 | escalation-review 行 | checked_files=[]（审计空转后 pass） |
| F501 parametric 侧 | `derive_output_files('shenbi-escalation-review')` vs chapter=5 | [] vs ['audits/escalation-5-report.md'] |
| F530 复现 | PipelineState round-trip | token_usage `<absent>`，hasattr False |
| F530 resume 路径 | machine.py load_state + cli.py 3 处消费 | from_json 重建确认 |
| summarize 差分 | 临时账本 3 好行+1 坏行 | 行数==records==calls==Σskill==Σchapter==3；tokens 167==Σ167 |
| 快照链计数 | watch 6 模式→snapshot 7→checked 7 | 一致 |
| F511 真实噪声 | novel-output/test-validation `**/*score*.json` | 0 文件，avg=None（latent） |
| state chapter 属性 | （F505 抽验复认） | PipelineState 无 chapter 声明 |

## 六、汇总表

| 编号 | 标题 | 类别 | 严重度 | 与初审/r1/r2 关系 |
|---|---|---|---|---|
| F529 | `_matches_declared` 不认裸 glob 契约 → 10 技能合法写入误判未声明写入 rc=2（生产 3 次 GATE_FAIL 实证） | error | P0 | 漏报（契约第三形态 + 真实产物对账维度缺失） |
| F530 | state.token_usage 不持久化，resume 后日志 summary 与 ledger 分歧 | error | P2 | 漏报（token 计数持久化链未查） |
| —（误报） | 无整体误报；初审两处"grep 验证过"断言证伪（"无通配契约"、"snapshot 43-45 生产不可达"） | — | — | 子论断级误报（F529 证据基础） |
| —（异议） | 无新异议 | — | — | — |

## 收敛判定意见

- 本轮新 finding: **2 条（P0×1, P2×1）**。
- **G4 软收敛未达成**（标准: 无新 P0/P1 且 ≤3 新——本轮出现新 P0）；硬收敛（0 新）亦未达成。
- 判定依据: F529 不是边角缺陷——它横跨三轮未被发现、有真实生产阻断记录（3 次 GATE_FAIL）、影响 10 个技能（含 genesis 必经的 worldbuilding 与 truth-sync），且与 F501 合流后写审计的"未声明写入"检查在三类契约形态（parametric、裸 glob、面外）上**全部失效**。在 F529 修复并补裸 glob 契约审计测试之前，不宜宣布 Z5 收敛。
- 建议下一步: (1) triage F529（一行 fnmatch 补齐 + 测试矩阵扩到裸 glob 技能）；(2) 勘误初审报告两处事实断言；(3) F530 随 F504 的 ledger 修复一并处理（单轨化方向）；(4) 下一轮若复核，角度建议: 修复后回归验证 + 对 truth-sync/character-design 等其余 9 技能跑同款真实产物对账（本仓 test-validation 仅覆盖 worldbuilding/escalation-review 两技能）。
