# Token 效率 P2 效率优化：跨 dispatch 缓存 / IDE-CLI system-user 分离 / 重示例 SKILL.md 外置

> **Date:** 2026-08-02
> **Status:** Design（**Revised 2026-09-17** · 两轮修订：①价值门复核——§1 降级为不实施（审计波部分已被归档 spec #42/PR #153 的 C28 R1 字节等价读抑制实现，剩余非审计链缺口为纯磁盘 I/O，按本 spec 铁律 1 度量将归零）；②阶段 3 设计审查——§3.7 重设计为「body 瘦身 + 外置参考文件（运行时不注入）」，废弃 `dispatched_examples` 分发机制（无注入点/每章一次 dispatch 收益归零/重试负向交互三处致命），并补 lint 豁免与离线度量口径。§2/度量前提复核存活；全文行号按 main@4eedf14d 刷新）
> **Severity:** 🟡 Medium（效率优化，非阻塞；单项收益需 G4 全量验证，且 P2 的度量前提——TokenLedger 接线——已由 PR #39 落地）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **系列:** Token 效率全栈 audit（效率优化轮，承接已归档总纲 [`archive/2026-08-01-pipeline-read-write-consistency-audit-design.md`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §6.3 P2 五项中的三项；另两项——shared_context serial 接线（3.2）、world_summarizer 落地（2.3 #8）——见 §0.2 分工）
> **依赖:** 已归档总纲 spec（决策原则、Cluster C 重复传输根因簇、§3.3/§3.9/§3.10 findings）；PR #39（TokenLedger API 路径接线 §3.1，是本 spec 全部收益的度量前提）；`src/shenbi/pipeline/{dispatch_helper,audit_context_cache,chapter_loop}.py`；`skills/shenbi-{chapter-pattern,review-resonance,review-arc-payoff,state-settling}/SKILL.md`
> **前置已完成（PR #39）:**
> - ✅ TokenLedger.record() 已接 API 路径（`_record_token_usage` → `_log_token_usage` → `TokenLedger`），`cost/token-ledger.jsonl` 一章 round 后非空——**本 spec 所有"prompt_tokens 下降"的可量化验证依赖此**
> - ✅ `_log_token_usage` 双形处理（bare Usage + response wrapper），streaming 路径不再静默早退
> - ⚠️ IDE-CLI 路径精确用量仍未记录（codex exec stdout 是 prose）——但 C10 起有 `estimated=True` 下界行兜底（见 §0.1 度量口径，Revised 2026-09-17）
> **范围:** 本 spec 只审 **P2 效率优化**——跨 dispatch 的重复传输（Cluster C）的缓存层、IDE-CLI 路径绕过 provider prompt cache、重 SKILL.md 内嵌示例的按需外置。**不审** P0 纯浪费（PR #39 已清）、不审 P1 契约一致（PR #39 已清）、不审采样/模型/重试（见子 spec #3 推理控制）、不审输出侧浪费（见子 spec #5）、不审确定性替换（见子 spec #4）。
> **Purpose:** 把总纲 §6.3 P2 五项中的三项（3.3 / 3.9 / 3.10）从"设计提议"推进到"可实施 plan"——各自定位根因、给出最小可行实现、标注 G4 回归风险与验证路径。P2 的本质是"动 prompt/调用结构本身"，与 P0/P1（删已有浪费）不同：**每一项都可能影响输出质量，必须 G4 全量验证 + 准备回滚**。

---

## 0. 分工与决策原则

### 0.1 决策原则（继承总纲 §0.1，本 spec 强化度量要求）

质量 > token > 速度，但不应有浪费。**G4/gate 仍是唯一质量裁判**，但 P2 加一条：**任何 prompt/调用结构改动，必须用 PR #39 接好的 TokenLedger 度量"改前 vs 改后"的 prompt_tokens 差值**——无度量 = 不可证收益 = 不合并。

**度量口径（Revised 2026-09-17）:** IDE-CLI 路径自 C10（spec #36 T5/F796）起每次 dispatch 落一条 `estimated=True` 下界行（`_record_estimate_row`，dispatch_helper :1799 def / :2559 调用，覆盖 system+user 拼接全文）——字节级削减在 IDE 路径已可按**下界口径**度量。精确 completion 用量仍需 API 路径或 codex `--json` usage-report（子 spec #3 域）。本 spec 的验收度量一律用离线纯函数 `estimate_prompt_tokens`（`src/shenbi/cost/estimate.py`）对构建出的 prompt 求值，不触发真实 dispatch（核心原则 8）。

### 0.2 P2 五项归属（总纲 §6.3 的完整处置）

| 总纲 finding | 内容 | 归属 | 理由 |
|---|---|---|---|
| 3.3 | 跨 dispatch 文件 read_text 无缓存 | ~~本 spec §1~~（**Revised 2026-09-17 降级不实施**：审计波已归 #42/PR#153，剩余缺口纯 I/O 无 token 收益，见 §1 复核注记） | Cluster C 核心，cache 层设计（已裁决） |
| 3.9 | SKILL.md 全文每次 dispatch 重发 + IDE-CLI 绕 provider cache | **本 spec §2** | system/user 分离 + 前缀稳定 |
| 3.10 | 5 个 >10K SKILL.md 内嵌重示例 | **本 spec §3** | 示例外置到 fixture |
| 3.2 | SharedAuditContext 漏接 serial audit_layer | **延后，并入子 spec #5**（输出侧 F9 审计交叉冗余同路径） | serial 审计波是输出侧审计冗余的同源问题；合并修避免两 spec 改同一函数 |
| 2.3 #8/#9 | world_summarizer.py + skills/_shared/ 未实现 | **延后，独立小 spec 或并入本 spec §3** | world_summarizer 与 §3 示例外置共用 `_shared/` 基建；若 §3 落地则 #8/#9 自然解决一半 |

**本 spec 聚焦 3.3 / 3.9 / 3.10 三项**。3.2 归子 spec #5；2.3 #8/#9 视 §3 实施时是否一并建 `_shared/` 而定。

---

## 1. Finding 3.3 — 跨 dispatch 文件缓存层（Cluster C 核心）

> **Revised 2026-09-17（价值门复核 · 降级为不实施）**：本节所述"无跨调用缓存"在审计波已不成立——归档 spec #42/PR #153 的 C28 R1 落地了 `SharedAuditContext.raw_files` 字节等价读抑制（覆盖 chapter-N / world/rules / character_matrix / style_profile / pending_hooks 五文件，`_build_skill_prompt` :690 命中检查，章界于审计波起点整建）。剩余缺口（非审计主链 step 1-8 / revision / audit_layer / genesis / closure / triggers 不注入 shared_context，chapter_summaries / current_state 不在 raw_files）为**纯磁盘 I/O 去重**——缓存命中在 `filter_to_fields`（:698）之前且字节等价，**不减少 prompt 发送字节**；§1.5 的 token 浪费估算与 §1.8 的 prompt_tokens 下降行系错位归因（真实的输入侧 token 削减归 Layer B 字段过滤（spec #65）与本 spec §3 示例外置）。按本 spec 铁律 1（无度量 = 不可证收益 = 不合并），T_B 不实施。高 churn truth 文件的"每章发送一次"语义是另一种更高风险的设计（改每 dispatch 的 prompt 内容），不在本 spec 范围。

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

同一 skill 在一章内被多次 dispatch 时，其 ~3-15KB 的 SKILL.md 每次都作为 system prompt 全量发送。最大的 5 个（Revised 2026-09-17 复测）：`review-resonance` 14,829 字节 / `review-arc-payoff` 13,799 / `state-settling` 12,322 / `chapter-pattern` 12,191 / `pacing-design` 11,338（PR #39 核实原值 13,987/13,354/11,582/11,089/10,996，全部微增；每章被发 N 次）。

### 2.2 证据（PR #39 后行号）

- `dispatch_helper.py` `_build_skill_prompt`: `system_prompt = _strip_autogen_blocks(skill_file.read_text(...))`（PR #39 已剥离 auto-gen 块，但 SKILL.md body 本身仍每次重读重发）。
- **IDE-CLI 路径绕过 provider cache:** `_dispatch_via_ide`（`dispatch_helper.py` def :2449，Revised 2026-09-17 行号）把 `full_prompt = f"{system_prompt}\n\n{user_prompt}"`（:2495）拼成单 stdin 字符串，`subprocess.run(cmd, input=full_prompt, ...)`（:2505-2507）。provider prompt cache 要求 system 与 user 分离、system 前缀字节稳定——拼接成单字符串完全绕过。
- `_find_ide_cli`（:2428）构造 `codex exec --skip-git-repo-check -c sandbox_permissions=workspace-write -C {dir} -`——**无 `--system` flag**，stdin 是唯一输入通道。

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

最大的 5 个 SKILL.md 把参考矩阵、算例、样例报告全嵌在 body 里，每次 dispatch 全发。`chapter-pattern` 含 13×13 模式转移矩阵 + Shannon 熵逐步算例 + 多输出模板；`review-resonance`/`review-arc-payoff` 各 ~6 个填好的样例评分报告；`state-settling` ≈55 行人工审批门禁模板（Revised 2026-09-17 复测行数，原记 65 行）。

### 3.2 证据

- `shenbi-chapter-pattern/SKILL.md`: 13×13 矩阵（模式：引入/升级/转折/揭示/决战/沉淀/日常/训练/探索/阴谋/逃亡/回忆/总结）+ 熵算例（`H = -Σp·log₂p` 逐步计算）。
- `shenbi-state-settling/SKILL.md`: `:172` 起"人工审批门禁"模板（格式段约 :177 起，审批签名行 :226，Revised 2026-09-17 行号，≈55 行）。
- `skills/_shared/` 目录**仍不存在**（PR #39 确认 2.3 #9 未落地）。
- `world_summarizer.py` **仍不存在**（2.3 #8 未落地）；`audit_context_cache.py:118-122` 的 `_summarize_if_large` 仍是截断式（截断时追加 `[TRUNCATED n/m]` 披露行；调用点 :77/:83——Revised 2026-09-17 行号）。

### 3.3 根因

skill 作者把"教学示例"和"每次执行的指令"混在同一文件；没有"按需 read 的 fixture" vs "必发的指令"分离。

### 3.4 分类

冗余待去重（示例对已熟练的执行是参考，不是每次必读）。

### 3.5 浪费量

5 skill × ~3-5KB 可外置示例 ≈ ~15-25KB system prompt 冗余，× N dispatch 放大。

### 3.6 质量影响

**低-中（P2 中风险最高的一项）:** 删示例可能影响首次执行的格式遵循度。需 G4 验证"无示例时输出格式仍达标"。

### 3.7 修复方案（Revised 2026-09-17 · 阶段 3 设计审查后重设计）：body 瘦身 + 外置参考文件（运行时不注入）

> **重设计理由（阶段 3 audit 轮 1 C1/C3/I4/I5）**：原"首次带、后续引用"分发策略（`dispatched_examples` per-chapter state）三处致命：① `_build_skill_prompt`（:601）无 state 参数、两条路径调用点（:2168/:2478）不传 state——照字面实现只能是模块级可变全局（章界重置 / pause-resume 泄漏 / ThreadPool 并发竞态 / 10+ 调用方兼容全未定义）；② 主链每 skill 每章恰一次（chapter_loop:3056 CHAPTER_STEPS 循环），同章重复 dispatch 的真实来源只有 G4 失败重试（:3038-3047 纠正反馈注入）——首发全量示例、收益只在第二次以后 ≈ 零收益搬家；③ 重试恰是模型最需要格式示范的时刻（刚在结构校验上失败），此时撤示例是负向交互，且"本章首次 dispatch 已提供"对每次都是全新对话的模型实例是伪陈述。

**新设计：无条件 body 瘦身——每次 dispatch 的 system prompt 都变小，收益不依赖章内 dispatch 次数。**

**目录基建:** 建 `skills/_shared/`（同时解决 2.3 #9 的基建半边）。外置示例是面向 skill 作者/维护者的参考文档，运行时**不注入**（对齐 `anti-ai-reference.md` 先例与 `lint_contract_prose.py:63` 的既有裁决"捆绑参考文件，dispatcher 不注入"）。配套改动：`tools/lint_registry_reconcile.py` `_r1_skill_closure`（:307）跳过 `_` 前缀目录——否则 `_shared` 入 live 集触发 R1 missing-live 假阳性。

**外置判定（逐 skill，body 保留什么/外置什么）:**
- `chapter-pattern`: 13×13 矩阵 + 熵逐步算例外置到 `skills/_shared/chapter-pattern-reference.md`；body 保留模式名清单 + "何时参考哪种模式"的决策指令 + 输出格式模板。
- `review-resonance`: 填满分的样例评分报告外置到 `skills/_shared/review-resonance-examples.md`；body 保留评分维度定义 + 输出格式模板（空骨架，非填好样例）。
- `review-arc-payoff`: 同上 → `skills/_shared/review-arc-payoff-examples.md`。
- `pacing-design`: 目标比值表 + 节奏原则模板同理 → `skills/_shared/pacing-design-reference.md`。
- `state-settling`: ≈55 行人工审批门禁长模板压缩到 ~15 行骨架（07-18 §4.4 row 5 原案）或外置 `skills/_shared/state-settling-gate-template.md`（逐 skill 落地时定）。

**body 引用行的诚实表述（若引用）:** 只写"完整算例/样例见仓库 `skills/_shared/<file>`（面向维护者的参考，运行时不注入）"——禁止"本章已提供"类对无记忆新会话的伪陈述。引用一律**裸文件名形态**（满足 `lint_contract_prose.py:186` 的 `"/" not in cref` 约束；`skills_root.glob(f"*/{base}")` 可命中 `_shared/` 下文件）。

**度量（铁律 1 的离线表达，核心原则 8）:** 改前/改后对 5 skill 各在测试内真实构建 `_build_skill_prompt`，对 system_prompt 用 `estimate_prompt_tokens`（`src/shenbi/cost/estimate.py` 纯函数）计差——不触发真实 dispatch。

**逐 skill rollout 步骤:** 每完成一个 skill 的瘦身即跑该 skill 的 G4 校验 + 全量 `just check`（防 R2 decl→body 证据因删段断裂，见 §3.9 回滚）。

### 3.8 验证（Revised 2026-09-17 · 全离线；真实 dispatch 面的格式遵循度验证归 audit-run/T1 generative 机制，本 pass 不做——核心原则 8 + F947）

| 标准 | tier | 方式 | 当前 | 目标 |
|---|---|---|---|---|
| 5 skill system prompt 字节数 | T1 | 离线：测试内构建 `_build_skill_prompt` 直接量 | 14,829 / 13,799 / 12,322 / 12,191 / 11,338 B | 各降 ~3-5KB |
| 5 skill system prompt 的 estimate_prompt_tokens 差 | T1 | 离线纯函数（`src/shenbi/cost/estimate.py`） | baseline 同上 | 下降，数值进验收证据 |
| `shenbi-validate G4 <skill>` × 5 | T1 | 只读 CLI | PASS | PASS（瘦身 body 后仍过；**注**：chapter-pattern 不在 G4_CHECKER_SKILLS——仅 generic 校验，证据弱一档，已知不对称） |
| `just check` 全量（含 lint_registry_reconcile R1 / lint_contract_prose） | T1 | just | PASS | PASS（`_shared` `_` 前缀豁免后不红） |
| 运行时格式遵循度（真实 dispatch） | — | 本 pass 不做 | n/a | 归后续 audit-run 验证（G0.9 真实产物回流 fixtures） |

### 3.9 回滚预案（Revised 2026-09-17）

每个 skill 的 body 瘦身是**独立可回滚**的。若某 skill 瘦身后的 G4 校验或 `just check` FAIL，立即恢复该 skill 的内嵌示例（git revert 该 skill 的改动），外置文件保留但不引用。**不强求 5 个全成功——成功率即便 3/5 也是 ~9-15KB/章收益。**

---

## 4. 实施顺序与依赖

```
PR #39（P0+P1 + TokenLedger 度量前提）—— 已合并
        │
        ▼
本 spec 的 plan（按风险升序）:
        ├─ T_A  §2 默认形态（system 字节稳定回归测试）         风险: 极低
        ├─ T_B  §1 保守缓存（read-only truth 文件 only）        ~~降级不实施（Revised 2026-09-17：审计波已被 #42/PR#153 实现；剩余缺口纯 I/O 无 token 收益，铁律 1 度量归零）~~
        ├─ T_C  §3 示例外置（逐 skill，可回滚）                 风险: 中（G4 格式遵循）
        └─ T_D  §2 强形态（IDE system/user 分离，需 CLI 验证）  风险: 中（依赖 CLI 能力）
```

**顺序理由:**
- T_A 先（纯回归测试，零代码行为改变，固化当前隐式契约）。
- ~~T_B 次（保守缓存无失效语义，收益最稳）。~~（Revised 2026-09-17：降级不实施，理由见 §1 复核注记）
- T_C 再次（逐 skill 可回滚，风险可控）。
- T_D 最后（依赖外部 CLI 能力验证，可能 stretch 放弃）。

**与子 spec #5（输出侧）的协同:** 若 #5 先落地 shared_context serial 接线（3.2），则 §1 的缓存层与之共享"per-chapter state"基建——plan 阶段需协调避免重复实现。

---

## 5. 验证标准（Revised 2026-09-17 · T_B 降级传导 + tier/离线切分）

| 标准 | tier / 方式 | 当前 | 目标 |
|---|---|---|---|
| ~~同章同 read-only truth 文件 read_text 次数~~ | — | ~~baseline~~ | ~~每章 1 次（T_B）~~ **行随 T_B 降级作废** |
| 同 skill 同文件两次 `_build_skill_prompt` 的 system_prompt 字节相等 | T1 离线 | 未测 | 相等（T_A 回归测试） |
| 5 skill system prompt 字节数 | T1 离线（测试内构建） | 14,829 / 13,799 / 12,322 / 12,191 / 11,338 B | 各降 ~3-5KB（T_C） |
| 5 skill system prompt 的 estimate_prompt_tokens 差 | T1 离线纯函数 | baseline 同上 | 下降，数值进验收证据（T_C） |
| 一章 round 的 `cost/token-ledger.jsonl` 总 prompt_tokens | 真实 run（本 pass 不触发，核心原则 8） | IDE 路径有 estimated=True 下界行 | T_C 合并后的真实章节收益由后续 audit-run 验证，非本 pass 验收面 |
| G4 5 skill + `just check` | T1 只读 CLI | PASS | PASS（任何一项 FAIL 即回滚该 skill 的 body 瘦身） |

---

## 6. 铁律（3 条，P2 专属）

1. **度量先于优化。** P2 每一项的收益必须用可复现的度量表达"改前 vs 改后"（本 pass 用 `estimate_prompt_tokens` 离线纯函数 + TokenLedger 的 estimated 下界行口径，见 §0.1）。无度量的"应该更快"不合并。IDE 路径的下界口径须在验证报告中显式声明。
2. **G4 FAIL 即回滚，无例外。** P2 是"动 prompt/调用结构"，与 P0/P1（删已有浪费）不同——每一项都可能影响输出质量。T_C 的逐 skill body 瘦身必须独立可回滚（Revised 2026-09-17：T_B 已降级，原缓存失效条款随废）。
3. **不造未验证的抽象。** ~~§1 的 cache 层首版用保守方案（read-only truth only），不先搞 content-hash 失效引擎（YAGNI）。~~（T_B 降级随废）§2 的 IDE system/user 分离若 CLI 不支持就不做，不强 hack。

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
        ├─ ~~§1 (3.3 缓存层)~~ ── Revised 2026-09-17 降级不实施（归档 #42/PR#153 已覆盖审计波；剩余纯 I/O）
        ├─ §2 (3.9 IDE 分离) ── 依赖: _strip_autogen_blocks (PR #39) + CLI 能力验证
        └─ §3 (3.10 示例外置) ── 依赖: skills/_shared/ 基建 + lint 豁免 + G4 结构验证
                │
                ▼
        T_A（§2 默认形态测试）→ T_C（§3 body 瘦身，逐 skill 可回滚）→ T_D（§2 强形态，CLI 门控）──► 归档本 spec
```

本 spec 是 **design，不实施**。P2 各项实施前需另写 plan 并批准。
