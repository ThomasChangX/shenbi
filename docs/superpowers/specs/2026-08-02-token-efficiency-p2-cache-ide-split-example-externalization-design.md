# Token 效率 P2 效率优化：跨 dispatch 缓存 / IDE-CLI system-user 分离 / 重示例 SKILL.md 外置

> **Date:** 2026-08-02
> **Status:** Design（**Revised 2026-09-17** · 七轮修订：①价值门复核——§1 降级为不实施（审计波部分已被归档 spec #42/PR #153 的 C28 R1 字节等价读抑制实现，剩余非审计链缺口为纯磁盘 I/O，按本 spec 铁律 1 度量将归零）；②阶段 3 轮 1——§3.7 重设计为「body 瘦身 + 外置参考文件（运行时不注入）」，废弃 `dispatched_examples`；③轮 2——per-skill 实测重基线、外置边界规则（输出契约永不外置）、不可触碰不变量清单、G4 验收行撤除、引用行强制；④轮 3——存储改判 skill 自有目录（`_shared/` 被 test_skill_name_validation + YAGNI 双重证伪，零豁免零测试改动）、per-dispatch 频率口径；⑤轮 4——范围声明改继承集口径（当时计 11 个 >10KB，轮 7 修正确为 12；范围外最大候选 foreshadowing-lifecycle 剥离后实为第三——resonance/arc-payoff 居前且两者终版 SKIP 不裁）、arc-payoff 预裁 SKIP（示例块整体为 checker 锚定结构，净省 <500B）、resonance/pacing 范围对齐节边界、INDEX #6 注册卡同步；⑥轮 5——resonance 分解为仅填充值外置（机器契约结构 :129/:136/:142-149/:155-162/:169-176 全留，净省 ~0.4-0.6KB）、state-settling 预裁 SKIP（:231-232 强制输出 → 契约）——§3.6 对齐 G4 撤除裁决、T_D 补离线断言；⑦轮 6——resonance 诚实分解（408-521B，扣 146B 引用行净 262-375B）后阈值口径终裁 SKIP，引用行成本修正为实测 146B，chapter-pattern/pacing 净省按此重算（~741B/~723B）——**实施集终版 2 skill，一次性 ~1.46KB、稳态 ~0.12KB/章；T_C 残余价值边际，pass 主交付 = T_A + T_D + 分解证据**。§2/度量前提复核存活；全文行号按 main@4eedf14d 刷新）
> **Severity:** 🟡 Medium（效率优化，非阻塞；格式遵循度验证归 audit-run（G4 checker 不读 SKILL.md body，零信号——轮 2 裁决），且 P2 的度量前提——TokenLedger 接线——已由 PR #39 落地）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **系列:** Token 效率全栈 audit（效率优化轮，承接已归档总纲 [`archive/2026-08-01-pipeline-read-write-consistency-audit-design.md`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §6.3 P2 五项中的三项；另两项——shared_context serial 接线（3.2）、world_summarizer 落地（2.3 #8）——见 §0.2 分工）
> **依赖:** 已归档总纲 spec（决策原则、Cluster C 重复传输根因簇、§3.3/§3.9/§3.10 findings）；PR #39（TokenLedger API 路径接线 §3.1，是本 spec 全部收益的度量前提）；`src/shenbi/pipeline/{dispatch_helper,audit_context_cache,chapter_loop}.py`；`skills/shenbi-{chapter-pattern,review-resonance,review-arc-payoff,pacing-design,state-settling}/SKILL.md`
> **前置已完成（PR #39）:**
> - ✅ TokenLedger.record() 已接 API 路径（`_record_token_usage` → `_log_token_usage` → `TokenLedger`），`cost/token-ledger.jsonl` 一章 round 后非空——**本 spec 所有"prompt_tokens 下降"的可量化验证依赖此**
> - ✅ `_log_token_usage` 双形处理（bare Usage + response wrapper），streaming 路径不再静默早退
> - ⚠️ IDE-CLI 路径精确用量仍未记录（codex exec stdout 是 prose）——但 C10 起有 `estimated=True` 下界行兜底（见 §0.1 度量口径，Revised 2026-09-17）
> **范围:** 本 spec 只审 **P2 效率优化**——跨 dispatch 的重复传输（Cluster C）的缓存层、IDE-CLI 路径绕过 provider prompt cache、重 SKILL.md 内嵌示例的按需外置。**不审** P0 纯浪费（PR #39 已清）、不审 P1 契约一致（PR #39 已清）、不审采样/模型/重试（见子 spec #3 推理控制）、不审输出侧浪费（见子 spec #5）、不审确定性替换（见子 spec #4）。
> **Purpose:** 把总纲 §6.3 P2 五项中的三项（3.3 / 3.9 / 3.10）从"设计提议"推进到"可实施 plan"——各自定位根因、给出最小可行实现、标注 G4 回归风险与验证路径。P2 的本质是"动 prompt/调用结构本身"，与 P0/P1（删已有浪费）不同：**每一项都可能影响输出质量，必须准备回滚；运行时格式遵循度验证归 audit-run（G4 checker 不读 SKILL.md body，零信号——Revised 2026-09-17 轮 2 裁决）**。

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
| 3.10 | 5 个 >10K SKILL.md 内嵌重示例 | **本 spec §3** | 示例外置为维护者参考文档（Revised 2026-09-17：运行时不注入，非"按需 read"） |
| 3.2 | SharedAuditContext 漏接 serial audit_layer | **延后，并入子 spec #5**（输出侧 F9 审计交叉冗余同路径） | serial 审计波是输出侧审计冗余的同源问题；合并修避免两 spec 改同一函数 |
| 2.3 #8/#9 | world_summarizer.py + skills/_shared/ 未实现 | **延后，独立小 spec**（Revised 2026-09-17 轮 3：§3 改用 skill 自有目录，不建 `_shared/`——5 个外置文件无一共享，基建推迟到真实共享消费者出现） | world_summarizer 与共享基建另行立项 |

**本 spec 聚焦 3.3 / 3.9 / 3.10 三项**。3.2 归子 spec #5；2.3 #8/#9 延后独立立项（轮 3 裁决）。

---

## 1. Finding 3.3 — 跨 dispatch 文件缓存层（Cluster C 核心）

> **Revised 2026-09-17（价值门复核 · 降级为不实施）**：本节所述"无跨调用缓存"在审计波已不成立——归档 spec #42/PR #153 的 C28 R1 落地了 `SharedAuditContext.raw_files` 字节等价读抑制（覆盖 chapter-N / world/rules / character_matrix / style_profile / pending_hooks 五文件，`_build_skill_prompt` :690 命中检查，章界于审计波起点整建）。剩余缺口（非审计主链 step 1-8 / revision / audit_layer / genesis / closure / triggers 不注入 shared_context，chapter_summaries / current_state 不在 raw_files）为**纯磁盘 I/O 去重**——缓存命中在 `filter_to_fields`（:699）之前且字节等价，**不减少 prompt 发送字节**；§1.5 的 token 浪费估算与 §1.8 的 prompt_tokens 下降行系错位归因（真实的输入侧 token 削减归 Layer B 字段过滤（spec #65）与本 spec §3 示例外置）。按本 spec 铁律 1（无度量 = 不可证收益 = 不合并），T_B 不实施。高 churn truth 文件的"每章发送一次"语义是另一种更高风险的设计（改每 dispatch 的 prompt 内容），不在本 spec 范围。

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

### 1.8 验证（**已随 T_B 降级作废，2026-09-17 · 防误采用横幅**——下表为历史设计，勿据此实施）

| 标准 | 当前（PR #39 后） | 目标 |
|---|---|---|
| 同章同文件 read_text 次数 | baseline（TokenLedger 可间接推算） | 下降（read-only truth 文件每章 1 次） |
| `cost/token-ledger.jsonl` prompt_tokens（同章 baseline vs 改后） | baseline | 下降 ≥150KB/章估算值的对应 token |
| G4 全 skills | PASS | PASS（质量铁律不退让；FAIL 即回滚） |
| read→write→read 序列（stale 验证） | n/a | 不返回 stale slice（若用保守方案则 N/A——high-churn 文件不入缓存） |

---

## 2. Finding 3.9 — IDE-CLI system/user 分离 + system 前缀稳定

### 2.1 症状

同一 skill 在一章内被多次 dispatch 时，其 SKILL.md 每次都作为 system prompt 全量发送。**本 spec 的 5 个目标文件是 finding 3.10 的继承集（2026-08-01 审计时的最大五文件；Revised 2026-09-17 轮 4 口径修正）**：`review-resonance` 14,829 字节 / `review-arc-payoff` 13,799 / `state-settling` 12,322 / `chapter-pattern` 12,191 / `pacing-design` 11,338（PR #39 核实原值 13,987/13,354/11,582/11,089/10,996）。**范围外注记（诚实披露）**：截至 2026-09-17 全仓已有 12 个 SKILL.md >10KB，其中 `foreshadowing-lifecycle`（13,292 B 原始，剥离后 12,828 B，现为全仓剥离后第三——resonance 14,373 / arc-payoff 13,350 居前，且两者终版均 SKIP 不裁）每章 dispatch、`review-group-character`（12,100）、`genre-config`（11,416）均晚于 08-01 审计诞生或长大——**不在本 spec 范围**（核心原则 7 单 spec 原子性：范围随 finding 3.10 继承，不随体积漂移扩张；后续候选另行立项/记 master 台账）。各目标频率见 §3.5 表。

### 2.2 证据（PR #39 后行号）

- `dispatch_helper.py` `_build_skill_prompt`: `system_prompt = _strip_autogen_blocks(skill_file.read_text(...))`（PR #39 已剥离 auto-gen 块，但 SKILL.md body 本身仍每次重读重发）。
- **IDE-CLI 路径绕过 provider cache:** `_dispatch_via_ide`（`dispatch_helper.py` def :2449，Revised 2026-09-17 行号）把 `full_prompt = f"{system_prompt}\n\n{user_prompt}"`（:2495）拼成单 stdin 字符串，`subprocess.run(cmd, input=full_prompt, ...)`（:2505-2507）。provider prompt cache 要求 system 与 user 分离、system 前缀字节稳定——拼接成单字符串完全绕过。
- `_find_ide_cli`（:2428）构造 `codex exec --skip-git-repo-check -c sandbox_permissions=workspace-write -C {dir} -`——**无 `--system` flag**，stdin 是唯一输入通道。

### 2.3 根因

dispatcher 把 system prompt 当"每次重新组装的字符串"，而非"跨调用稳定的可缓存前缀"。

### 2.4 分类

冗余待去重（API 路径靠 provider cache 部分兜底；IDE-CLI 路径完全不兜底）。

### 2.5 浪费量

review 类一章 ~13 个器 × 6-14KB（Revised 2026-09-17 复测口径：多数 review SKILL.md 6-9KB，最大两器 ~14KB）——量级 ~100-170KB/章（API 路径有 cache 抵消大半；IDE-CLI 路径全损）。

### 2.6 质量影响

无。

### 2.7 修复方案：双形态（默认 + stretch）

**默认形态（必做，低风险）:** 保证 system prompt 跨 dispatch **字节稳定**——同一 skill 同一章内多次 dispatch 时，`_strip_autogen_blocks` 的输出应确定性（无时间戳/随机）。当前实现已满足（read_text + 确定性 regex sub），但需加一个回归测试固化"同 skill 同文件两次 _build_skill_prompt 的 system_prompt 字节相等"。这使 API 路径的 provider cache 命中率最大化。

**强形态（stretch，需 CLI 能力验证）:** IDE-CLI 路径 system/user 分离——**前提是 codex/zcode CLI 支持 system 参数**。plan 阶段必须先验证：

```
codex exec --help | grep -i system     # 是否有 --system / --system-prompt flag
zcode --help | grep -i system
```

- **若支持:** `_find_ide_cli` 构造命令时加 system flag，`subprocess.run` 用 `input=user_prompt`（stdin 只走 user），system 走 flag。**离线断言（轮 5 M10）**：配套测试断言构造出的 cmd 确实经 flag 路由 system 内容（而非仍拼接进 stdin）——强形态的验证不靠人眼。
- **若不支持:** 强形态放弃；只做默认形态（system 前缀稳定），IDE 路径仍拼接但至少为未来 codex `--json` / system 支持预留接口。**不可强行 hack（如把 system 塞进 codex 的 config 文件）——维护成本高于收益。**

### 2.8 验证（Revised 2026-09-17 · 表中 provider/IDE cache hit rate 与"G4 全 skills"三行属历史设计——本 pass 验收一律离线纯函数口径（§0.1），真实 dispatch 面归后续 audit-run；权威验收表见 §5）

| 标准 | 当前 | 目标 |
|---|---|---|
| 同 skill 同章两次 dispatch 的 system_prompt 字节相等 | 未测（应是 True） | 回归测试固化（T_A，离线） |
| API 路径 provider cache hit rate | 未度量 | 本 pass 不度量（需真实 dispatch；后续 audit-run） |
| IDE 路径 prompt cache hit rate | 0（单 stdin） | 若 CLI 支持 system flag 则架构上可达；否则维持 0 + 记录为已知限制 |

---

## 3. Finding 3.10 — 重 SKILL.md 内嵌示例外置

### 3.1 症状

最大的 5 个 SKILL.md 把参考矩阵、算例、样例报告全嵌在 body 里，每次 dispatch 全发。`chapter-pattern` 含 13×13 模式转移矩阵 + Shannon 熵逐步算例 + 多输出模板；`review-resonance`/`review-arc-payoff` 各恰 1 个填满分的样例评分报告（Revised 轮 4 复测，原记 ~6 个系高估）；`state-settling` ≈55 行人工审批门禁模板（Revised 2026-09-17 复测行数，原记 65 行）。

### 3.2 证据

- `shenbi-chapter-pattern/SKILL.md`: 13×13 矩阵（模式：引入/升级/转折/揭示/决战/沉淀/日常/训练/探索/阴谋/逃亡/回忆/总结）+ 熵算例（`H = -Σp·log₂p` 逐步计算）。
- `shenbi-state-settling/SKILL.md`: `:172` 起"人工审批门禁"模板（格式段约 :177 起，审批签名行 :226，Revised 2026-09-17 行号，≈55 行）。
- `skills/_shared/` 目录至 2026-09-17 仍不存在（审计时代证据：finding 2.3 #9 未落地；Revised 轮 4 注：本 spec 已改用 skill 自有目录方案，不再创建 `_shared/`——见 §3.7 目录裁决）。
- `world_summarizer.py` **仍不存在**（2.3 #8 未落地）；`audit_context_cache.py:118-122` 的 `_summarize_if_large` 仍是截断式（截断时追加 `[TRUNCATED n/m]` 披露行；调用点 :77/:83——Revised 2026-09-17 行号）。

### 3.3 根因

skill 作者把"教学示例"和"每次执行的指令"混在同一文件；没有"面向维护者的参考文档"与"必发的指令/输出契约"分离（Revised 2026-09-17：措辞随重设计更新——外置物是运行时不注入的参考文档，非"按需 read 的 fixture"）。

### 3.4 分类

冗余待去重（示例对已熟练的执行是参考，不是每次必读）。

### 3.5 浪费量（Revised 2026-09-17 轮 3 · per-skill 实测重基线 + 频率表）

阶段 3 实测各段字节数后，原"5 skill × ~3-5KB ≈ ~15-25KB"系高估（把输出契约段误计为可外置）。**per-skill 可外置上限（实测段字节 → 保留骨架后净省估计）**：

| skill | 可外置段（实测字节） | 机器契约/输出契约段（保留 inline） | 净省估计 | dispatch 频率 | 裁决 |
|---|---|---|---|---|---|
| review-resonance | （诚实分解后 408-521 B：维度行填充值 :131-134 + 门判定示例 :139-140 ± 结果行 :126——其中 :126 的三合法结果枚举属结构非教学值） | 六列表头 :129（g4 `_DETAIL_COLS`）+ 列名注记 :136 + verdict 围栏规范 :142-149（`match_verdict_scoped`）+ `calibration:`/`anchors:` 块 :155-162（spec #33 T1b 框架消费）+ `### 共鸣短板` append-only 写语义 :151-153（drift-guidance 依赖）+ trend 追加块 :167-176（drift CLI 契约，含 :175 填充行）+ 声明行 :121 + 记录语义 :178 | **净省 262-433 B**（扣 146B 引用行） | 每章 1 次（CHAPTER_STEPS） | **预裁 SKIP（轮 6 C1 终裁）**——与 arc-payoff（实测 523B）/state-settling（~531-560B）同口径：净省 <500B 一律跳过，无豁免 |
| review-arc-payoff | （填充值实测 523 B） | 示例块 :121-159 整体为 checker 锚定结构（`_DETAIL_COLS`、5 维度行、门判定/子底线）；R2 声明行 :118-119 | **<500B** | 每卷/弧 1 次（closure.py:88 / triggers.py:245；audit_layer:109 章触发已禁用） | **预裁 SKIP**（轮 4 C2） |
| chapter-pattern | 熵公式段 + 逐步算例 :296-332（887 B） | 13×13 矩阵（输出模板内）+ 熵评级阈值 :334 + 输入文档化要求 :344+（helper_injection 已代算熵值，公式段属教学） | **净省 ~741 B**（887B − 146B 引用行） | 每 6 章 1 次（audit_layer:111）+ closure | 实施 |
| pacing-design | 三线比例 + 场景类型完整节 :84-110（869 B） | EXACT 节标题输出模板（:122 起）+ `### 4. 单调性检测阈值`（:111-121 运行时检测指令） | **净省 ~723 B**（869B − 146B 引用行） | 创世 1 次/项目（genesis.py:67）+ 手动 re-dispatch（triggers.py 无自动触发） | 实施 |
| state-settling | （交叉验证示例行 ≈531-560 B；门禁模板 :177-226 本身全是占位符骨架） | :231-232 明示"必须输出跨文件交叉验证表"——输出契约；门禁骨架 :172-226 同为输出物 | **净省 ≈0.5KB 边缘/低于阈值** | 每章 1 次（CHAPTER_STEPS） | **预裁 SKIP**（轮 5 I5：:232 强制输出 → 契约；与 arc-payoff 同口径） |

**口径（轮 6 终裁）**：收益按 **per-dispatch 净省**计（扣 146B 强制引用行）。**实施集终版 2 skill（chapter-pattern/pacing）行和 ~1.46 KB**（一次性口径）；稳态每章净省 ≈ chapter-pattern/6 ≈ **~0.12 KB/章**，pacing 按项目一次性贡献。**resonance/arc-payoff 预裁 SKIP（阈值口径：净省 262-375B / 523B−146B=377B 均 <500B）；state-settling SKIP（定性裁决：净省 588B 超阈值，但动无 G4 安全网的输出契约模板，588B 边际收益不值格式漂移风险）**——五文件的重段主体是 checker/机器/输出契约结构，可外置的教学填充值占比极小；这是 finding 3.10 前提的部分驳斥：重 ≠ 可外置。**净省 <500B 的 skill 一律跳过，无豁免**。IDE 路径（无 provider cache，字节全价）下上述节省全额兑现。诚实结论：T_C 的残余价值为边际（一次性 ~1.5KB + 稳态 ~0.12KB/章），本 pass 的主要交付是 T_A（字节稳定回归测试）+ T_D（IDE system/user 分离，plan 阶段 CLI 验证）+ 本节完整分解证据；T_C 两个边际 skill 的实施以"净省 ≥500B 规则内达标"为据，逐 skill 可独立回滚。

### 3.6 质量影响

**低-中（P2 中风险最高的一项）:** 删填充值可能影响首次执行的格式遵循度。Revised 2026-09-17：G4 checker 不读 SKILL.md body（零信号），格式遵循度验证归后续 audit-run（§3.8）；本 pass 的机械防护 = 结构全留（骨架含全部 checker 锚定标记）+ 逐 skill 回滚。

### 3.7 修复方案（Revised 2026-09-17 · 阶段 3 设计审查后重设计）：body 瘦身 + 外置参考文件（运行时不注入）

> **重设计理由（阶段 3 audit 轮 1 C1/C3/I4/I5）**：原"首次带、后续引用"分发策略（`dispatched_examples` per-chapter state）三处致命：① `_build_skill_prompt`（:601）无 state 参数、两条路径调用点（:2168/:2478）不传 state——照字面实现只能是模块级可变全局（章界重置 / pause-resume 泄漏 / ThreadPool 并发竞态 / 10+ 调用方兼容全未定义）；② 主链每 skill 每章恰一次（chapter_loop:3056 CHAPTER_STEPS 循环），同章重复 dispatch 的真实来源主要是 G4 失败重试（:3038-3047 纠正反馈注入；另有审计阻塞修订循环 :3225-3258 与 resonance 重评上限（其 SKILL.md:117 最多 2 次重评）——轮 4 M5 补正）——首发全量示例、收益只在第二次以后 ≈ 零收益搬家；③ 重试恰是模型最需要格式示范的时刻（刚在结构校验上失败），此时撤示例是负向交互，且"本章首次 dispatch 已提供"对每次都是全新对话的模型实例是伪陈述。

**新设计：无条件 body 瘦身——每次 dispatch 的 system prompt 都变小，收益不依赖章内 dispatch 次数。**

**目录裁决（Revised 2026-09-17 轮 3 C1+I1 · 放弃 `_shared/`，改用 skill 自有目录）:** 原"建 `skills/_shared/`"方案被证伪：① `tests/unit/contracts/test_skill_name_validation.py:28-32` 枚举 skills/ 全部子目录（仅 `is_dir()` 过滤）验名，`_shared` 不合 `^[a-z0-9][a-z0-9-]*$`（`contracts/loader.py:58`）→ just check 必红；② 5 个外置文件无一跨 skill 共享，`_shared/` 是为推迟的消费者（world_summarizer #8/#9）预建的投机基建（YAGNI）。**改用 skill 自有目录**——对齐双先例 `skills/shenbi-chapter-drafting/anti-ai-reference.md`、`skills/shenbi-review-era/era-reference.md`：外置文件如 `skills/shenbi-review-resonance/review-resonance-examples.md`，dispatcher 只注入 `SKILL.md` 不注入同目录其他文件，裸文件名引用同样命中 `lint_contract_prose.py:186` branch-b 的 `skills_root.glob(f"*/{base}")` 存在性检查（dead-link 防护等价）。**不需要** lint_registry_reconcile 豁免、**不需要**目录不变量、**不需要**改任何测试。`_shared/` 基建推迟到真实共享消费者落地时（2.3 #8/#9 的基建半边随之外置——不再由本 spec 解决）。

**外置边界规则（阶段 3 轮 2 I2 · 铁律级）:** **绝不外置模型必须在输出中复现的内容**——输出模板、固定矩阵/表头、checker 校验的 EXACT 节标题（pacing-design :120+ 段、chapter-pattern 13×13 矩阵、state-settling 门禁文档骨架均属此类，保留 inline）。**只外置填满的教学示例、演示算例、参考速查表**。原 §3.7 初稿把矩阵/节奏模板列入外置对象系误判，已纠正。

**不可触碰不变量（阶段 3 轮 2 I4 · 瘦身时一律保留）:** DOT flowchart（五文件各 1 处）、`## Anti-Rationalization` 表（chapter-pattern:378 / review-resonance:225 / review-arc-payoff:179 / pacing-design:288 / state-settling:255）、硬门/铁律段、Route 表、decisions sidecar 的 body 声明段（state-settling frontmatter :17 + :281+ 附近）、frontmatter 契约（reads/writes/updates + decisions 声明）。

**外置判定（Revised 轮 4 · 按 §3.5 表逐 skill，文件放各自 skill 目录）:**
- `review-resonance`: **预裁 SKIP（轮 6 C1 终裁）**——诚实分解（维度行填充值 + 门判定示例 ± 结果行）后净省 262-433B < 500B，与 arc-payoff/state-settling 同口径；样例块主体为机器契约结构（表头/围栏/calibration 块/trend 契约/写语义 :151-153），教学填充值占比极小。
- `review-arc-payoff`: **预裁 SKIP（轮 4 C2）**——示例块 :121-159 整体为 checker 锚定结构（g4/review_arc_payoff.py 要求输出复现 `_DETAIL_COLS` 六列表头、5 维度行名、门判定/伏笔兑现子底线），可外置的填充值实测 523 B，净 377B <500B 跳过阈值；:118-119 的"审计报告写出至 `audits/volume-N-payoff.md`："是 declared write 目标的唯一 body 证据，本就不可动。
- `chapter-pattern`: **矩阵保留 inline**（输出契约）；熵计算公式段 + 逐步算例（:296-332）外置到 `skills/shenbi-chapter-pattern/chapter-pattern-reference.md`；**`### 熵评级阈值`（:333）与 `### 熵计算公式输入文档化要求`（:344+）运行时必需，保留 inline**（框架已由 helper_injection.py:162-168 确定性代算熵值——公式段属教学）。
- `pacing-design`: **EXACT 节标题输出模板（:122 起 `## 输出格式`）与 `### 4 单调性检测阈值`（:111-121，运行时检测指令）保留 inline**；三线比例 + 场景类型完整节（:84-110，869 B）外置到 `skills/shenbi-pacing-design/pacing-design-reference.md`。
- `state-settling`: **SKIP（定性裁决，轮 7 修正口径）**——:231-232 明示"必须输出跨文件交叉验证表"，:233-253 为该输出契约的展示模板；交叉验证示例行实测 734B、净省 588B **超**阈值——但动一个无 G4 安全网的输出契约模板、为 588B 承担格式漂移静默风险不值（裁决依据与 arc-payoff 的阈值口径不同，结论一致）。

**引用行为（阶段 3 轮 2 I6 · 强制）:** 每个新建外置文件**必须**在对应 skill body 中有引用行（无引用的外置文件 = dead wire；contract-prose R1 的 skill-bundle 分支会对裸文件名引用做存在性检查，构成机械防护）。引用行用**裸文件名**且诚实表述，如："完整样例见维护者参考 `review-resonance-examples.md`（本 skill 目录内，运行时不注入；输出格式以本文件模板为准）"——禁止斜杠路径（`lint_contract_prose.py:186` 的 `"/" not in cref` 约束）与"本章已提供"类伪陈述。

**G4 重试路径的取舍（阶段 3 轮 2 I5 · 有意接受）:** 无条件瘦身下，G4 失败重试 dispatch（chapter_loop:3038-3047）同样失去示例——原设计逻辑③的顾虑对新设计同样成立。裁决：**接受，不加重试注入代码**。理由：重试 prompt 自带纠正反馈（G4 失败明细是比样例更强的格式信号）+ body 保留空骨架模板；维持本 pass 零 `src/shenbi/` 生产代码改动的爆炸半径。若后续 audit-run 显示重试通过率退化，回滚对应 skill 或另行立项重试注入。

**度量（铁律 1 的离线表达，核心原则 8）:** 改前/改后对实施集 skill（终版 2 个 + SKIP 三者的分解证据）在测试内真实构建 `_build_skill_prompt`，对 system_prompt 用 `estimate_prompt_tokens`（`src/shenbi/cost/estimate.py` 纯函数）计差——不触发真实 dispatch。

**逐 skill rollout 步骤:** 每完成一个 skill 的瘦身即跑全量 `just check`（contract-prose R2 的 decl→body 证据检查是实际防护面；G4 checker 不读 SKILL.md body，无信号，见 §3.8）。

### 3.8 验证（Revised 2026-09-17 轮 2 · 全离线；G4 行撤除——checker 不读 SKILL.md body，对 body 瘦身零信号，且 tests/fixtures 无这 5 skill 产物（G0.9 禁手造），格式遵循度归后续 audit-run）

| 标准 | tier | 方式 | 当前 | 目标 |
|---|---|---|---|---|
| 参与瘦身的各 skill system prompt 字节净降 | T1 | 离线：测试内构建 `_build_skill_prompt` 直接量 | 见 §3.5 表实测段字节 | **≥ §3.5 各行净省估计下限**；低于下限的 skill 按规则跳过并记录 |
| system prompt 的 estimate_prompt_tokens 差 | T1 | 离线纯函数（`src/shenbi/cost/estimate.py:49`） | baseline 同上 | 下降，数值进验收证据 |
| `just check` 全量（含 contract-prose R1+R2 / registry-reconcile R1） | T1 | just | PASS | PASS（自有目录方案零豁免零测试改动 + 裸文件名引用 + 不变量保全） |
| 外置文件引用存在性 | T1 | 由 contract-prose R1 skill-bundle 分支机械保障 | n/a | 每个新建外置文件在对应 skill body 有裸文件名引用 |
| 运行时格式遵循度（真实 dispatch） | — | 本 pass 不做（核心原则 8 + F947） | n/a | 归后续 audit-run 验证（G0.9 真实产物回流 fixtures）；若退化按 §3.9 回滚 |

### 3.9 回滚预案（Revised 2026-09-17 轮 2）

每个 skill 的 body 瘦身是**独立可回滚**的。回滚触发：(a) 该 skill 的验收净降低于 §3.5 下限且裁决跳过失败；(b) `just check` 因该 skill 的改动变红且不可修；(c) 后续 audit-run 显示格式遵循度退化。回滚动作：git revert 该 skill 的瘦身 commit，外置文件与引用行一并移除。**不强求全量成功**——按 §3.5 表（轮 6 终裁），实施集 2 skill（chapter-pattern/pacing）行和 ~1.46KB（一次性），稳态 ~0.12KB/章；resonance/arc-payoff/state-settling 三者同口径预裁 SKIP，净省 <500B 一律跳过。

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

**与子 spec #5（输出侧）的协同:** ~~若 #5 先落地 shared_context serial 接线（3.2），则 §1 的缓存层与之共享"per-chapter state"基建~~（Revised 2026-09-17：§1 已降级，无缓存层可共享；仅当未来重裁 T_B 时才需与 #5 协调 state 基建。）

---

## 5. 验证标准（Revised 2026-09-17 · T_B 降级传导 + tier/离线切分）

| 标准 | tier / 方式 | 当前 | 目标 |
|---|---|---|---|
| ~~同章同 read-only truth 文件 read_text 次数~~ | — | ~~baseline~~ | ~~每章 1 次（T_B）~~ **行随 T_B 降级作废** |
| 同 skill 同文件两次 `_build_skill_prompt` 的 system_prompt 字节相等 | T1 离线 | 未测 | 相等（T_A 回归测试） |
| 参与瘦身 skill 的 system prompt 字节净降 | T1 离线（测试内构建；**基线以剥离 autogen 块后的 system prompt 为准**——即 `_build_skill_prompt` 实际产出与 `estimate_prompt_tokens` 实际度量的口径，原始文件字节仅作参考） | 原始文件字节 14,829/13,799/12,322/12,191/11,338；剥离后基线在 plan/实施时测定并固化为测试常量 | 各达 §3.5 表净省下限（实施集终版 2 skill 行和 ~1.46KB；resonance/arc-payoff/state-settling 同口径预裁 SKIP 并记录） |
| 5 skill system prompt 的 estimate_prompt_tokens 差 | T1 离线纯函数 | baseline 同上 | 下降，数值进验收证据（T_C） |
| 一章 round 的 `cost/token-ledger.jsonl` 总 prompt_tokens | 真实 run（本 pass 不触发，核心原则 8） | IDE 路径有 estimated=True 下界行 | T_C 合并后的真实章节收益由后续 audit-run 验证，非本 pass 验收面 |
| `just check`（含 G4 全 skills 不变性） | T1 只读 CLI | PASS | PASS（G4 checker 不读 SKILL.md body，本 pass 零 checker 变更；任何 lint FAIL 即回滚对应 skill 的 body 瘦身） |

---

## 6. 铁律（3 条，P2 专属）

1. **度量先于优化。** P2 每一项的收益必须用可复现的度量表达"改前 vs 改后"（本 pass 用 `estimate_prompt_tokens` 离线纯函数 + TokenLedger 的 estimated 下界行口径，见 §0.1）。无度量的"应该更快"不合并。IDE 路径的下界口径须在验证报告中显式声明。
2. **G4 FAIL 即回滚，无例外。** P2 是"动 prompt/调用结构"，与 P0/P1（删已有浪费）不同——每一项都可能影响输出质量。T_C 的逐 skill body 瘦身必须独立可回滚（Revised 2026-09-17：T_B 已降级，原缓存失效条款随废）。
3. **不造未验证的抽象。** ~~§1 的 cache 层首版用保守方案（read-only truth only），不先搞 content-hash 失效引擎（YAGNI）。~~（T_B 降级随废）§2 的 IDE system/user 分离若 CLI 不支持就不做，不强 hack。

---

## 7. 与已归档总纲 + 兄弟子 spec 的关系

- **承接总纲 §6.3 P2:** 本 spec 把 3.3/3.9/3.10 三项从"提议"推进到"可实施"。3.2 归子 spec #5，2.3 #8/#9 视 §3 实施而定。
- **依赖 PR #39:** TokenLedger 接线是全部度量的前提；~~`_input_key` 相对路径键是 §1 缓存 key 的基础~~（Revised 2026-09-17：§1 已降级，此依赖随废）；`_strip_autogen_blocks` 是 §2 system 字节稳定的前置（已剥离 auto-gen 块）。
- **不重复审:** 采样/模型/重试 → 子 spec #3；输出侧浪费 → 子 spec #5；确定性替换 → 子 spec #4。本 spec 只管"输入侧的重复传输 + system prompt 结构 + 示例体重"。

---

## 8. 依赖关系图

```
PR #39（P0+P1 + TokenLedger）  已合并
        │
        ├─ ~~§1 (3.3 缓存层)~~ ── Revised 2026-09-17 降级不实施（归档 #42/PR#153 已覆盖审计波；剩余纯 I/O）
        ├─ §2 (3.9 IDE 分离) ── 依赖: _strip_autogen_blocks (PR #39) + CLI 能力验证
        └─ §3 (3.10 示例外置) ── 依赖: skill 自有目录外置（先例 anti-ai-reference.md）+ contract-prose 裸文件名引用 + just check
                │
                ▼
        T_A（§2 默认形态测试）→ T_C（§3 body 瘦身，逐 skill 可回滚）→ T_D（§2 强形态，CLI 门控）──► 归档本 spec
```

本 spec 是 **design，不实施**。P2 各项实施前需另写 plan 并批准。
