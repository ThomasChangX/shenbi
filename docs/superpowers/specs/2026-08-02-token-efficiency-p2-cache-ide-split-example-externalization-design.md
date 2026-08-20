# Token 效率 P2 效率优化：跨 dispatch 缓存 / IDE-CLI system-user 分离 / 重示例 SKILL.md 外置

> **Date:** 2026-08-02
> **Status:** Design
> **Severity:** 🟡 Medium（效率优化，非阻塞；单项收益需 G4 全量验证，且 P2 的度量前提——TokenLedger 接线——已由 PR #39 落地）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **系列:** Token 效率全栈 audit（效率优化轮，承接已归档总纲 [`archive/2026-08-01-pipeline-read-write-consistency-audit-design.md`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §6.3 P2 五项中的三项；另两项——shared_context serial 接线（3.2）、world_summarizer 落地（2.3 #8）——见 §0.2 分工）
> **依赖:** 已归档总纲 spec（决策原则、Cluster C 重复传输根因簇、§3.3/§3.9/§3.10 findings）；PR #39（TokenLedger API 路径接线 §3.1，是本 spec 全部收益的度量前提）；`src/shenbi/pipeline/{dispatch_helper,audit_context_cache,chapter_loop}.py`；`skills/shenbi-{chapter-pattern,review-resonance,review-arc-payoff,state-settling}/SKILL.md`
> **前置已完成（PR #39）:**
> - ✅ TokenLedger.record() 已接 API 路径（`_record_token_usage` → `_log_token_usage` → `TokenLedger`），`cost/token-ledger.jsonl` 一章 round 后非空——**本 spec 所有"prompt_tokens 下降"的可量化验证依赖此**
> - ✅ `_log_token_usage` 双形处理（bare Usage + response wrapper），streaming 路径不再静默早退
> - ⚠️ IDE-CLI 路径仍未记录用量（codex exec stdout 是 prose）——见 §3.9 + §0.1 决策原则的度量盲点
> **范围:** 本 spec 只审 **P2 效率优化**——跨 dispatch 的重复传输（Cluster C）的缓存层、IDE-CLI 路径绕过 provider prompt cache、重 SKILL.md 内嵌示例的按需外置。**不审** P0 纯浪费（PR #39 已清）、不审 P1 契约一致（PR #39 已清）、不审采样/模型/重试（见子 spec #3 推理控制）、不审输出侧浪费（见子 spec #5）、不审确定性替换（见子 spec #4）。
> **Purpose:** 把总纲 §6.3 P2 五项中的三项（3.3 / 3.9 / 3.10）从"设计提议"推进到"可实施 plan"——各自定位根因、给出最小可行实现、标注 G4 回归风险与验证路径。P2 的本质是"动 prompt/调用结构本身"，与 P0/P1（删已有浪费）不同：**每一项都可能影响输出质量，必须 G4 全量验证 + 准备回滚**。

---

## 0. 分工与决策原则

### 0.1 决策原则（继承总纲 §0.1，本 spec 强化度量要求）

质量 > token > 速度，但不应有浪费。**G4/gate 仍是唯一质量裁判**，但 P2 加一条：**任何 prompt/调用结构改动，必须用 PR #39 接好的 TokenLedger 度量"改前 vs 改后"的 prompt_tokens 差值**——无度量 = 不可证收益 = 不合并。

**度量盲点警告（IDE 路径）:** 若运行时走 IDE-CLI 路径（codex exec），TokenLedger 仍不记录用量（codex stdout 是 prose）。因此本 spec 的可量化验证**默认假设 API 路径**（`SHENBI_LLM_API_KEY` set）。IDE 路径的度量需先落地子 spec #3 的 codex `--json` usage-report，或 §3.9 本身的 system/user 分离使 IDE 路径也能走 API。

### 0.2 P2 五项归属（总纲 §6.3 的完整处置）

| 总纲 finding | 内容 | 归属 | 理由 |
|---|---|---|---|
| 3.3 | 跨 dispatch 文件 read_text 无缓存 | **本 spec §1** | Cluster C 核心，cache 层设计 |
| 3.9 | SKILL.md 全文每次 dispatch 重发 + IDE-CLI 绕 provider cache | **本 spec §2** | system/user 分离 + 前缀稳定 |
| 3.10 | 5 个 >10K SKILL.md 内嵌重示例 | **本 spec §3** | 示例外置到 fixture |
| 3.2 | SharedAuditContext 漏接 serial audit_layer | **延后，并入子 spec #5**（输出侧 F9 审计交叉冗余同路径） | serial 审计波是输出侧审计冗余的同源问题；合并修避免两 spec 改同一函数 |
| 2.3 #8/#9 | world_summarizer.py + skills/_shared/ 未实现 | **延后，独立小 spec 或并入本 spec §3** | world_summarizer 与 §3 示例外置共用 `_shared/` 基建；若 §3 落地则 #8/#9 自然解决一半 |

**本 spec 聚焦 3.3 / 3.9 / 3.10 三项**。3.2 归子 spec #5；2.3 #8/#9 视 §3 实施时是否一并建 `_shared/` 而定。

---

## 1. Finding 3.3 — 跨 dispatch 文件缓存层（Cluster C 核心）

### 1.1 症状

同一 truth 文件在一章内被 5-8 个 dispatch 重复 `read_text` 并全文发给 LLM。`truth/pending_hooks.md` 被 22 个 skill 声明为 read，`chapter_summaries.md` 16 个，`character_matrix.md` 12 个（grep `skills/shenbi-*/SKILL.md` 计数，含 producer 自身契约）；单章链 planning→context→drafting→revision→state-settling 内 `pending_hooks` 至少读 3 次。

### 1.2 证据（PR #39 后行号）

- `dispatch_helper.py` `_build_skill_prompt` 的 read 循环：每次调用都 `content = full_path.read_text(encoding="utf-8")`（`_input_key` 调用点之上），无跨调用缓存。
- 对比：`_load_executor_config` / `_load_genre_config_cached` 是显式缓存的（module-level dict）。
- `SharedAuditContext`（`audit_context_cache.py`）是"本章已发文件集"的**局部实现**，但只覆盖 parallel 审计波的 4 个 truth 文件（world_rules / character_matrix / style_profile / pending_hooks），且只注入、不缓存非审计 dispatch。

### 1.3 根因

dispatcher 把每次 dispatch 视为独立无状态调用，没有"本章已发送文件集"的概念。`SharedAuditContext` 是这个概念的正确抽象，但作用域被限定在审计场景。

### 1.4 分类

冗余待去重（provider 端 prompt caching 在 API 路径能部分兜底；IDE-CLI 路径完全不兜底——见 §2）。

### 1.5 浪费量（需 TokenLedger 实证）

估算：单章 ~5-8 个非审计 dispatch × ~30-60KB truth 集合 = ~150-480KB 重发/章。**PR #39 后可用 TokenLedger 精确度量**（改前跑一章记 baseline，改后跑同章对比）。

### 1.6 质量影响

无（重复内容不影响输出）——**这是 P2 中唯一"真零质量风险"的项**，理论可直接做。但缓存失效语义（§1.7）若错会引入 stale-read 正确性 bug。

### 1.7 修复方案：content-hash 失效的 per-chapter 文件缓存

**核心设计:** 在 pipeline state 上挂一个 `chapter_file_cache: dict[str, str]`（key = `_input_key` 相对路径，value = 文件内容切片）。`_build_skill_prompt` 的 read 循环命中缓存则用缓存切片，未命中则 `read_text` + 入缓存。

**失效语义（总纲 Phase-2 C2 修复——content-hash，非 write-event）:**

repo 有 6+（实测 20）skill 同章既读又写 truth 文件（drift-guidance / foreshadowing-recall / memory-distill / state-settling 写 `pending_hooks` 后被下章 planning 读 等）。"写后失效"过宽（mid-chapter 对未变内容重读）或过窄（stale-read）。**正确语义:**

- 缓存不变式：`chapter_file_cache[k]` 反映文件 `k` 在**本章 planning phase 的内容**（章首快照）。
- 失效当且仅当：post-write bytes ≠ cached bytes（content-hash 比对）。
- 具体：每个 skill dispatch 完成后，检查其 `writes:`/`updates:` 契约中的 truth 文件；若磁盘当前内容 hash ≠ 缓存 hash，则 evict 该 key（下一 dispatch 重新 read）。
- 不做"写事件即失效"——因为同章内某 skill 写 `pending_hooks` 后，后续 skill 读到的是**新内容**，这恰恰是正确行为（不是 stale），不该 evict。

**替代方案（更保守，推荐首版）:** 缓存**只覆盖 read-only truth 文件**——即排除任何在 producer 自身 `writes:`/`updates:` 中的文件。`world_rules.md` / `character_matrix.md`（state-settling 写但章内其他 dispatch 读的是章首版）等明确"章首快照语义"的文件入缓存；`pending_hooks.md` / `current_state.md`（章内会被 append/update）不入缓存。**这避免了失效语义的复杂性，代价是少缓存几个高 churn 文件。**

### 1.8 验证（需 TokenLedger + G4）

| 标准 | 当前（PR #39 后） | 目标 |
|---|---|---|
| 同章同文件 read_text 次数 | baseline（TokenLedger 可间接推算） | 下降（read-only truth 文件每章 1 次） |
| `cost/token-ledger.jsonl` prompt_tokens（同章 baseline vs 改后） | baseline | 下降 ≥150KB/章估算值的对应 token |
| G4 全 skills | PASS | PASS（质量铁律不退让；FAIL 即回滚） |
| read→write→read 序列（stale 验证） | n/a | 不返回 stale slice（若用保守方案则 N/A——high-churn 文件不入缓存） |

---

## 2. Finding 3.9 — IDE-CLI system/user 分离 + system 前缀稳定

### 2.1 症状

同一 skill 在一章内被多次 dispatch 时，其 ~3-14KB 的 SKILL.md 每次都作为 system prompt 全量发送。最大的 5 个：`review-resonance` 13,987 字节 / `review-arc-payoff` 13,354 / `chapter-pattern` 11,582 / `pacing-design` 11,089 / `state-settling` 10,996（PR #39 核实，每章被发 N 次）。

### 2.2 证据（PR #39 后行号）

- `dispatch_helper.py` `_build_skill_prompt`: `system_prompt = _strip_autogen_blocks(skill_file.read_text(...))`（PR #39 已剥离 auto-gen 块，但 SKILL.md body 本身仍每次重读重发）。
- **IDE-CLI 路径绕过 provider cache:** `_dispatch_via_ide`（`dispatch_helper.py` def ~:1575）把 `full_prompt = f"{system_prompt}\n\n{user_prompt}"`（`:1621`）拼成单 stdin 字符串，`subprocess.run(cmd, input=full_prompt, ...)`。provider prompt cache 要求 system 与 user 分离、system 前缀字节稳定——拼接成单字符串完全绕过。
- `_find_ide_cli`（`:1570`）构造 `codex exec --skip-git-repo-check -c sandbox_permissions=workspace-write -C {dir} -`——**无 `--system` flag**，stdin 是唯一输入通道。

### 2.3 根因

dispatcher 把 system prompt 当"每次重新组装的字符串"，而非"跨调用稳定的可缓存前缀"。

### 2.4 分类

冗余待去重（API 路径靠 provider cache 部分兜底；IDE-CLI 路径完全不兜底）。

### 2.5 浪费量

review 类一章 ~13 个器 × ~13KB ≈ ~170KB/章（API 路径有 cache 抵消大半；IDE-CLI 路径全损）。

### 2.6 质量影响

无。

### 2.7 修复方案：双形态（默认 + stretch）

**默认形态（必做，低风险）:** 保证 system prompt 跨 dispatch **字节稳定**——同一 skill 同一章内多次 dispatch 时，`_strip_autogen_blocks` 的输出应确定性（无时间戳/随机）。当前实现已满足（read_text + 确定性 regex sub），但需加一个回归测试固化"同 skill 同文件两次 _build_skill_prompt 的 system_prompt 字节相等"。这使 API 路径的 provider cache 命中率最大化。

**强形态（stretch，需 CLI 能力验证）:** IDE-CLI 路径 system/user 分离——**前提是 codex/zcode CLI 支持 system 参数**。plan 阶段必须先验证：

```
codex exec --help | grep -i system     # 是否有 --system / --system-prompt flag
zcode --help | grep -i system
```

- **若支持:** `_find_ide_cli` 构造命令时加 system flag，`subprocess.run` 用 `input=user_prompt`（stdin 只走 user），system 走 flag。
- **若不支持:** 强形态放弃；只做默认形态（system 前缀稳定），IDE 路径仍拼接但至少为未来 codex `--json` / system 支持预留接口。**不可强行 hack（如把 system 塞进 codex 的 config 文件）——维护成本高于收益。**

### 2.8 验证

| 标准 | 当前 | 目标 |
|---|---|---|
| 同 skill 同章两次 dispatch 的 system_prompt 字节相等 | 未测（应是 True） | 回归测试固化 |
| API 路径 provider cache hit rate | 未度量 | 上升（需 provider 返回 cache hit 指标；DeepSeek 自动缓存） |
| IDE 路径 prompt cache hit rate | 0（单 stdin） | 若 CLI 支持 system flag 则上升；否则维持 0 + 记录为已知限制 |
| G4 全 skills | PASS | PASS |

---

## 3. Finding 3.10 — 重 SKILL.md 内嵌示例外置

### 3.1 症状

最大的 5 个 SKILL.md 把参考矩阵、算例、样例报告全嵌在 body 里，每次 dispatch 全发。`chapter-pattern` 含 13×13 模式转移矩阵 + Shannon 熵逐步算例 + 多输出模板；`review-resonance`/`review-arc-payoff` 各 ~6 个填好的样例评分报告；`state-settling` 65 行人工审批门禁模板。

### 3.2 证据

- `shenbi-chapter-pattern/SKILL.md`: 13×13 矩阵（模式：引入/升级/转折/揭示/决战/沉淀/日常/训练/探索/阴谋/逃亡/回忆/总结）+ 熵算例（`H = -Σp·log₂p` 逐步计算）。
- `shenbi-state-settling/SKILL.md`: `:171` "人工审批门禁" 模板（`:176` 起门禁文档格式，`:225` 审批签名行）。
- `skills/_shared/` 目录**仍不存在**（PR #39 确认 2.3 #9 未落地）。
- `world_summarizer.py` **仍不存在**（2.3 #8 未落地）；`audit_context_cache.py:84` 的 `_summarize_if_large` 仍是 `text[:max_chars]` 裸截断。

### 3.3 根因

skill 作者把"教学示例"和"每次执行的指令"混在同一文件；没有"按需 read 的 fixture" vs "必发的指令"分离。

### 3.4 分类

冗余待去重（示例对已熟练的执行是参考，不是每次必读）。

### 3.5 浪费量

5 skill × ~3-5KB 可外置示例 ≈ ~15-25KB system prompt 冗余，× N dispatch 放大。

### 3.6 质量影响

**低-中（P2 中风险最高的一项）:** 删示例可能影响首次执行的格式遵循度。需 G4 验证"无示例时输出格式仍达标"。

### 3.7 修复方案：示例外置 + 首次带、后续引用

**目录基建:** 建 `skills/_shared/`（同时解决 2.3 #9）。每个外置示例是独立 `.md` 文件，如 `skills/_shared/chapter-pattern-matrix.md`、`skills/_shared/review-resonance-examples.md`。

**外置判定（逐 skill）:**
- `chapter-pattern`: 矩阵 + 熵算例外置到 `_shared/chapter-pattern-reference.md`；body 保留"何时查矩阵"的指令 + 一个最小化引用。
- `review-resonance` / `review-arc-payoff`: 样例评分报告外置到 `_shared/<skill>-examples.md`；body 保留评分维度定义 + 输出格式模板（不含填好的样例）。
- `state-settling`: 65 行审批门禁模板压到 15 行（07-18 §4.4 row 5 原案）或外置到 `_shared/state-settling-gate-template.md`。

**分发策略（关键，避免"外置了但每次还是全发"）:**
- **首次 dispatch（同 skill 同章）:** body 指令 + 外置示例都发（确保格式遵循）。
- **后续 dispatch:** 只发 body 指令 + 一行引用（"完整示例见 _shared/X.md，本章首次 dispatch 已提供"）。
- 实现：`_build_skill_prompt` 维护一个 `dispatched_examples: set[str]`（per chapter），首次 read 外置文件并入 user prompt，后续跳过。

**与 §1 缓存层的协同:** 外置示例文件本身是 read-only truth-like 文件，自然落入 §1 的 chapter_file_cache——首次 read 后缓存，后续 dispatch 命中缓存（但"是否发送"由 `dispatched_examples` 控制，缓存只省 read_text 不省发送）。

### 3.8 验证（需 G4 全量 + 格式遵循度对比）

| 标准 | 当前 | 目标 |
|---|---|---|
| 5 skill 的 system prompt 字符数 | baseline | 下降 ~3-5KB/skill |
| G4 对 5 skill（首次 dispatch 带示例） | PASS | PASS |
| G4 对 5 skill（后续 dispatch 不带示例） | 未测 | **PASS（核心验证——若 FAIL 则该 skill 不外置或改"每次带"）** |
| 输出格式遵循度（首次 vs 后续） | baseline | 无退化（人工抽查 + G4 结构分） |

### 3.9 回滚预案

每个 skill 外置是**独立可回滚**的。若某 skill 的后续 dispatch（无示例）G4 FAIL，立即把该 skill 的分发策略改回"每次带示例"（`dispatched_examples` 不生效），外置文件保留但不引用。**不强求 5 个全成功——成功率即便 3/5 也是 ~9-15KB/章收益。**

---

## 4. 实施顺序与依赖

```
PR #39（P0+P1 + TokenLedger 度量前提）—— 已合并
        │
        ▼
本 spec 的 plan（按风险升序）:
        ├─ T_A  §2 默认形态（system 字节稳定回归测试）         风险: 极低
        ├─ T_B  §1 保守缓存（read-only truth 文件 only）        风险: 低（无失效语义）
        ├─ T_C  §3 示例外置（逐 skill，可回滚）                 风险: 中（G4 格式遵循）
        └─ T_D  §2 强形态（IDE system/user 分离，需 CLI 验证）  风险: 中（依赖 CLI 能力）
```

**顺序理由:**
- T_A 先（纯回归测试，零代码行为改变，固化当前隐式契约）。
- T_B 次（保守缓存无失效语义，收益最稳）。
- T_C 再次（逐 skill 可回滚，风险可控）。
- T_D 最后（依赖外部 CLI 能力验证，可能 stretch 放弃）。

**与子 spec #5（输出侧）的协同:** 若 #5 先落地 shared_context serial 接线（3.2），则 §1 的缓存层与之共享"per-chapter state"基建——plan 阶段需协调避免重复实现。

---

## 5. 验证标准（数值化，全部依赖 TokenLedger）

| 标准 | 当前（PR #39 后 baseline） | 目标 |
|---|---|---|
| 同章同 read-only truth 文件 read_text 次数 | baseline（T_B 前度量） | 每章 1 次（T_B） |
| 同 skill 同章两次 dispatch 的 system_prompt 字节 | 未测 | 相等（T_A 回归测试） |
| 5 skill system prompt 字符数 | 13,987 / 13,354 / 11,582 / 11,089 / 10,996 | 各降 ~3-5KB（T_C） |
| 一章 round 的 `cost/token-ledger.jsonl` 总 prompt_tokens | baseline（PR #39 后可度量） | 下降（三项合计） |
| G4 全 skills | PASS | PASS（任何一项 FAIL 即回滚该单项） |
| `just check` | PASS | PASS |

---

## 6. 铁律（3 条，P2 专属）

1. **度量先于优化。** P2 每一项的收益必须用 PR #39 接好的 TokenLedger 度量"改前 vs 改后"。无度量的"应该更快"不合并。IDE 路径的度量盲点（§0.1）须在验证报告中显式声明。
2. **G4 FAIL 即回滚，无例外。** P2 是"动 prompt/调用结构"，与 P0/P1（删已有浪费）不同——每一项都可能影响输出质量。T_C 的逐 skill 外置必须独立可回滚；T_B 的缓存失效若致 stale-read 立即 evict-all + 回滚。
3. **不造未验证的抽象。** §1 的 cache 层首版用保守方案（read-only truth only），不先搞 content-hash 失效引擎（YAGNI）。§2 的 IDE system/user 分离若 CLI 不支持就不做，不强 hack。

---

## 7. 与已归档总纲 + 兄弟子 spec 的关系

- **承接总纲 §6.3 P2:** 本 spec 把 3.3/3.9/3.10 三项从"提议"推进到"可实施"。3.2 归子 spec #5，2.3 #8/#9 视 §3 实施而定。
- **依赖 PR #39:** TokenLedger 接线是全部度量的前提；`_input_key` 相对路径键是 §1 缓存 key 的基础；`_strip_autogen_blocks` 是 §2 system 字节稳定的前置（已剥离 auto-gen 块）。
- **不重复审:** 采样/模型/重试 → 子 spec #3；输出侧浪费 → 子 spec #5；确定性替换 → 子 spec #4。本 spec 只管"输入侧的重复传输 + system prompt 结构 + 示例体重"。

---

## 8. 依赖关系图

```
PR #39（P0+P1 + TokenLedger）  已合并
        │
        ├─ §1 (3.3 缓存层) ──── 依赖: _input_key (PR #39) + TokenLedger 度量
        ├─ §2 (3.9 IDE 分离) ── 依赖: _strip_autogen_blocks (PR #39) + CLI 能力验证
        └─ §3 (3.10 示例外置) ── 依赖: skills/_shared/ 基建 + G4 格式验证
                │
                ▼
        各自独立 plan + 实施 + G4 验证 ──► 归档本 spec
```

本 spec 是 **design，不实施**。P2 各项实施前需另写 plan 并批准。
