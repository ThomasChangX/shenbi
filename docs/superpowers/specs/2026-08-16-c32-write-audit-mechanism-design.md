> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟥 P0 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C32）| **依赖:** 无前置（本簇是 C33 rc 分类与 C1 键空间对账的输入）| **范围:** src/shenbi/audit/write_audit.py、audit/snapshot.py、_matches_declared/_declared_patterns、API/IDE 派发路由 | **核心洞察:** 写审计是"纯假阳性机器"——合法 glob 声明写恒判未声明（3 次生产 GATE_FAIL），而删除/重建、非法 JSON 替换、API/IDE 路由三类真违规整体逃逸

# C32 · 写审计机制修复（write-audit-mechanism）

## 元信息
- 簇：C32（写审计机制缺陷 write_audit/snapshot diff），11 条，最高严重度 **P0**（F501/F502/F529 三条），证据等级=实验佐证（5 条 verified，含真实生产数据 3 次 GATE_FAIL）
- 成员：F501（代表）、F502、F503、F508、F515、F516、F518、F520、F528、F529、F532
- 来源：`docs/superpowers/audit-runs/2026-08-15/findings-ledger.md` Z5 初审 + Z5-review-r1/r2/r3/r4
- 关系：supersede `2026-08-14-audit-chain-design.md`（#10）的写审计面（F507/F512/F513 为上轮同族 ID）

## 背景与根因
写审计子系统（pre/post 快照 diff → declared 匹配 → OWNERSHIP field 级校验）的两个核心谓词各自失效：
1. **`_matches_declared` 不做 fnmatch**（F529，P0 verified）：契约原生 glob 写模式（`truth/*.md` 等 10 技能 11 条 `*` 契约）的合法写入全部误判"未声明写入"→ rc=2 阻断。真实生产数据 3 次 GATE_FAIL 实证。F520 判定"未声明写入检测结构性零真阳性"——快照面=声明写入面，越权写基本形态永不进审计。
2. **diff 谓词漏洞族**：整体删除逃逸（F502 P0：FileChange 不看 status）、删除+重建绕过 field 审计（F515）、非法 JSON 替换 violations=[]（F503 P1 verified）、未变更标 modified（F508）、parametric-glob 展开分支生产不可达（F528）。
3. **路由覆盖缺口**：API/IDE 路径整体绕过写审计（F518），docstring 反向声称。
4. **误拦级联**：既有 drift 误归属零改动技能 + rc=2 级联阻断（F516）；write_safety 按前缀而非契约分类（F532，review-resonance 契约写 audit_drift/resonance_trend 却被判 READ_ONLY 进并行波）。
5. **parametric 技能审计双向失效**（F501 P0 verified：误拦/空转）。

## 目标
1. `_matches_declared` 对契约 glob 正确 fnmatch；"未声明写入"从零真阳性变为可真阳性（快照面 ≠ 声明面时可检出）
2. diff 谓词对删除/重建/类型替换/null 键/非法 JSON 五种形态全部产生违规
3. 写审计覆盖全部三条派发路由（pipeline/API/IDE），rc 语义与 C33 失败分类对接
4. 生产 rc=2 假阳性清零（3 次历史 GATE_FAIL 场景回归测试）

## 任务分解
### R1 · `_matches_declared` fnmatch 修复（F529 + F501，P0，先行）
- 声明模式含通配符时按 `fnmatch` 语义匹配写入路径；parametric 契约（`truth/{concept}/*.md` 类）按 F528 展开分支接通（当前生产不可达）
- 回归用例：10 技能 11 条 `*` 契约的真实写入全部 PASS；未声明新路径仍 FAIL
- **验收**：3 次生产 GATE_FAIL 场景（Z5-review-r3 记录）在测试中复现为 PASS

### R2 · diff 谓词完备化（F502/F503/F515/F508）
- `compute_file_change` 处理 FileChange.status（deleted → record 级违规 + field 审计不豁免）
- 删除+重建（added with same path）按 field 级键集校验，不落入空 changed_top_keys 旁路
- 非法 JSON（JSONDecodeError）与顶层类型变化（dict→list）产生违规而非静默 ()（与 F534/F537 同点，本簇收口写审计侧）
- 未变更/双 None 不标 modified（F508）
- **验收**：每种形态一条 pytest 用例，violations 非空且归属正确技能

### R3 · 路由覆盖（F518）
- `dispatch_with_write_audit` 包住 API/IDE 派发路径（与 pipeline 同一 finally 钩子）；docstring 改为真实描述
- **验收**：API 路径派发后 write-audit.jsonl 有记录（用 tests/fixtures 真实输出驱动）

### R4 · 误归属与分类修正（F516 + F532）
- drift 归属以"本次 dispatch 实际写过的文件"为界（快照 diff 为空则零违规，不级联）
- write_safety 分类改读契约 writes/updates（去前缀启发）；修掉锁死误分类的测试（C14 协同：测试 pin 生产 bug 不修）
- **验收**：零改动技能派发后 rc=0；review-resonance 进 WRITE_SHARED 串行波

## 验收（簇级）
- `just check` 全绿；新增 `tests/unit/audit/` 用例覆盖 R1-R4 全部形态（fixture 用真实技能产物，G0.9）
- 生产重放：对 novel-output 真实树跑一次写审计，零假阳性 rc=2
- C32 全部 11 条 merged-into F501 回写关闭

## 风险
- R1 放宽匹配可能漏拦新形态越权——以 R2 谓词完备化对冲，两者必须同一 PR 合入，禁止只修 R1
- F529 修复后 rc=2 语义变化会影响 C33 重试决策（rc=2=确定性违规不重试）——C33 spec 依赖本 spec 完成后接线

## 验证命令
- fnmatch 回归（含 3 次生产 GATE_FAIL 场景）：`pytest tests/unit/audit/ -k "matches_declared or glob_contract" -q`
- 谓词完备化矩阵：`pytest tests/unit/audit/ -k "diff_predicate" -q`（delete/rebuild/type-swap/null-key/illegal-json 五形态）
- 路由覆盖：`pytest tests/unit/audit/ -k "route and audit" -q`（API/IDE 派发后 write-audit.jsonl 非空）
- 生产重放：对 novel-output 真实树跑写审计，`echo $?` 为 0（零假阳性 rc=2）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F501 <- F502-F503, F508, F515-F516, F518, F520, F528-F529, F532`
- 上轮承接：#10（audit-chain）的 F507/F512/F513 面随本簇关闭后归档；F533（rc 不可区分）归 C33 消费侧
