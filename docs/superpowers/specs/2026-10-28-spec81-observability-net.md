# Spec #81 · 观测完备性之网（observability-net）：让记录足以持续优化系统与 prompt

**日期**：2026-10-28 ｜ **系列**：regen-vol1 收尾（与 #80 invariant-net 配对：#80 管「生成对不对」，#81 管「凭什么知道、凭什么改进」）
**状态**：Active（rev1 2026-10-29：设计审查轮 1 发现清偿——C1 归档模式改全量 blob/验收分期/逃逸舱检点钉死/API 面覆盖声明/L-A 例外条款） ｜ **动机证据**：`docs/regen-vol1-observability-mining.md`（Track A 手工首跑，五发现 O-1/O-2/O-3/A-1/B-1）

**触及的不变量维度**：无（观测域——dispatch 归档/trace 加性字段/逃逸舱硬化，不直接触及 13 维普查任何维度；其归档产物供 #80 的 mutant 重放与 `--as-of` 审计回放消费）

---

## 0. 背景与根因

Track A 挖矿证明：元数据层（trace/账本/取证/裁决）已能产出结构层优化结论，但两类分析永远不可行——
1. **因果归因**：O-2（style_profile 35 次失配）用尽现有记录仍不可裁决，因为没有 dispatch 时刻的文件快照；
2. **对照实验**：无 prompt/响应原文归档 → 任何 SKILL/prompt 改进只能等下一卷间接观察，无法回放验证。

根因与 #80 同构：**观测层也是反应式生长的**——失败路径有取证（canary #16/#17 定点补），成功路径无归档；WARN 有发出（`field_filter_missing_fields` ×64）无消费。本 spec 把观测从「事故取证」升级为「常备完备」。

**两条铁律**：
- **L-A 每个新增记录必须有具名消费者**（anti write-only oracle——prop_registry 与 O-3 的同一教训，观测层不得复发）；
- **L-B 记录自身不得重演「累积无界」**（settle 膨胀 ×2.8 的教训搬到日志层：内容寻址去重 + 配额熔断 + 滚动归档）。

**L-A 例外条款（recorder-first，仅限归档三件）**：dispatch 归档本体与 `feedback_ref`/`archive_path` 两字段允许**先记后用**——O-2 的教训是 dispatch 时刻状态不落档即永久不可考，等消费者齐备再开记等于放弃这段历史；其具名消费者为 P2 `dispatch_replay`（含 #80 mutant 重放/金丝雀/`--as-of` 回放，见 §5）。为防 write-only 无告警退化，P1 即付**最低消费者**：`observe_report` 归档覆盖行（派发数 vs 归档数对账 + blob 存在性 + 去重率，§3 表首行）。

---

## 1. dispatch 归档层（archive layer，= #80 所引 F21）

每次 **API 面派发**（`dispatch_helper._dispatch_via_api` 成功/失败两分支各落一档；失败分支与现有 `diagnostics/failed-write-*` 并存——前者是结构化归档，后者是即视取证）落 `observability/dispatches/{seq:05d}-{skill}-ch{N:03d}-a{attempt}.json`；genesis 派发（chapter=None）记 `ch000`：

```jsonc
{
  "seq": 122, "ts": "...", "skill": "shenbi-chapter-drafting", "chapter": 20, "attempt": 1,
  "model": "deepseek-v4-flash", "finish_reason": "stop",
  "skill_contract_sha256": "...",        // SKILL.md 的 git blob SHA——prompt 溯源锚（改版后可检漂移）
  "system_prompt_blob": "sha256:...",     // 完整 system prompt 进 blobs（同技能同卷高度去重）
  "user_prompt_blob": "sha256:...",       // 完整组装后 user prompt——任务指令+reads 全文+骨架注入+时间戳行，逐字节即模型所见
  "response_blob": "sha256:...",          // 响应正文
  "reads": [ {"path": "truth/current_state.md", "mode": "fields",
              "fields": ["系统演化阶段"],          // 契约声明（与 trace reads_manifest 同名键）
              "resolved_fields": ["系统演化阶段"], // 实际命中（archive 记录新增；manifest 不动）
              "matched_all": false,
              "blob": "sha256:..."} ],    // = 派发时刻磁盘原文快照（O-2 裁决口径）；过滤视图可由 fields 确定性重导
  "usage": {"prompt_tokens": 29213, "completion_tokens": 8102},
  "loop_id": 3, "feedback_ref": "sha256:..."   // §2
}
```

- **blob 策略（字节级复现的唯一路径）**：`user_prompt`/`response`/`system_prompt` 三者与逐 read 原文全部进内容寻址库 `observability/blobs/<sha256>`，哈希即指针。**不从 reads 重组 prompt**——组装嵌入任务指令、`wrap_untrusted_source` 横幅、`## Plan Skeleton` 注入（volume_map 派生）、#77/#78 强制节拍注入、逐派发 `Current time (UTC)` 行（`dispatch_helper.py:1391-1398`），皆不在 reads blob 内，重组不可行。去重估测：reads 重复注入率极高（genre-config ×130/卷），~40-60MB/卷原始文本 → blobs 实存 ~15-25MB。
- **plan 约束（接线摩擦，价值门驳斥轮实证）**：逐 read 原文快照需 `_build_skill_prompt` 回传 `raw_inputs`（现为 builder 内部局部量，返回元组不含）；prompt 级 blob 无此依赖（组装产物在 `_dispatch_via_api` 作用域内）。
- **覆盖面声明**：本层只盖 API 面——regen 实跑全走 API 面（挖矿 223 DISPATCH 全部出自 API）；IDE 面 `_dispatch_via_ide` 无 DISPATCH trace 且弃 reads_manifest（`dispatch_helper.py:3820` throwaway 注释自认），**记为已知覆盖洞，不静默**。
- **默认开启**（用户令「确保之后可以通过记录进一步优化」）；`SHENBI_ARCHIVE_DISPATCH=0` 可关（极端环境）。写档 fail-safe：归档失败不阻断派发（与 `_persist_failed_write_output` 同纪律），但记 `archive_write_failed` WARN 并计入 §3 消费报表。
- **配额熔断**：`observability/` 目录 > `SHENBI_ARCHIVE_QUOTA_BYTES`（默认 1GB，可配——测试可设 KB 级，§7 条 5 的离线形态）→ WARN + 跳过 blobs 新写（档与哈希照写）。**如实记档**：被跳过的 response 该次正文永久丢失；reads blob 仅当磁盘文件未变时可再导——而归档存在的意义正是证明「文件变没变」不可考——熔断即降级为「可验证（哈希在）不可复现（正文失）」。配额检查不逐派发全目录 walk：维护运行字节账 + 每 N 派发抽样校准。

## 2. trace 结构化补全（加性字段，schema_version 保持 1）

- **DISPATCH 增字段**（全部可选，旧事件兼容；`versioning.py` 的 `assert_monotonic` 只校验 schema_version 整数单调与未知高版本，payload 加键对其不可见；`_emit_dispatch_trace` docstring 明文「payload is a free dict, so no schema_version bump and no G7 chain impact」——结构性变更才升 v2 走 MIGRATIONS）：
  - `loop_id`：同 (skill, chapter) 的轮次序号——取自 `chapter_loop.py` 既有 `retry_counts`（`_retry_key(chapter, skill)` 键，:1587-1589），派发时快照；token 账本 `attempt` 只见 API 级重试（6 次/卷），循环层重派（drafting 10 轮）至今不可见（B-1）；
  - `feedback_ref`：重派反馈的 blob 哈希——循环反馈目前只活在代码里，「兜底反馈零信息」类问题（probe8 教训）从此有据可查（recorder-first，消费者 P2，见 §0 例外条款）；
  - `archive_path`：指向 §1 档案（同上）。
- **新事件 `RETRY`**：门检/监控触发的循环重派时记结构化原因（如场景算术差值 `{scene: 2, actual: 1995, band: [1800,2000]}`），替代只能翻 runner 日志的现状。`action` 为自由字符串（无枚举约束），G7 只验签名链+单调，新 action 直通。

## 3. 消费者契约（L-A 的机制化）

| 记录 | 具名消费者 | 层级 |
|---|---|---|
| dispatches 归档 | **P1 最低消费者**：`observe_report` 归档覆盖行（trace DISPATCH 数 vs 归档档数对账、blob 存在性抽检、去重率）；P2 起 `dispatch_replay` 骨架（喂 #80 mutant/金丝雀） | P1（覆盖行）→P2（replay） |
| trace `loop_id` | `tools/observe_report.py`（P1）：膨胀曲线 / loop depth / 失败簇 / 逃逸舱四表一键产出 | P1 |
| trace `RETRY` 事件 | `observe_report` 失败簇表：结构化原因聚类（替代翻 runner 日志） | P1 |
| trace `feedback_ref`/`archive_path` | `dispatch_replay`（P2）——recorder-first 例外见 §0 | P2 |
| 逃逸舱 WARN | **fail-fast 硬化**（检点钉死见下） | P1 |
| 契约 fields 声明 | **`tools/lint_reads_reconcile.py`**：所有 SKILL reads 的 `fields:` ↔ 项目内实际文件标题对账（`lint_decisions_sources` 三源对账同模式；O-1 类漂移在 CI 即红） | P2 |
| 归档写失败 WARN | `observe_report` 末行汇总 | P1 |

**逃逸舱 fail-fast 检点（钉死四元组）**：
- **检点 id**：`escape_hatch_drift`，HARD 语义——FAIL 时停循环、走既有 escalation checkpoint 暂停人工（漂移非重派可愈，**禁止烧 retry 预算**）；以 GATE_FAIL 形态落 trace（gate marker）。
- **计数键**：`(path, fields)`——O-1 实际漂移单元。不用 `(project, path)`：多技能读同文件不同 fields 声明时（planning 失配 vs drafting 匹配交错读 style_profile），交错复位互掩真漂移、或异技能偶发失配凑满 3 次假 FAIL。
- **复位规则**：同键 `matched_all=true` 的读复位该键连击计数。
- **缺失语义**：`observability/escape-hatch-state.json` 不存在 → PASS（既有项目/特性前历史不追溯失败——向后兼容硬约束）。
- `fields.py` 逃生舱（spec #9 R3 / F218）保留——契约错了不该断生成；但**同键连发 3 次**证明是漂移不是偶发，必须浮出为检点失败。计数器写侧在派发路径 reads_manifest 构建点（`_build_skill_prompt` 共享路径——API/IDE 两面都计数，与 §1 归档的 API 面覆盖洞解耦）；写走 `truth_io` `.lockfile` flock 纪律（并行审计波共享计数器，无 lost-update）。

## 4. 保留与轮转（L-B）——P2 批

- `dispatches/` 按 `--through <ch>` 滚动压缩为 `dispatches-001-060.tar.zst`（对齐 `just pool-archive`/`ledger-archive` 的窗口纪律）；
- blobs 引用计数：滚动归档后零引用 blob 回收；
- `observability/index.jsonl`：每派发一行指针（seq/skill/chapter/sha），跨 run 聚合查询不触 tar。
- **P1 过渡**：以上三者均 P2；P1 `observe_report` 直接扫 `dispatches/*.json`（单卷 ~500 档量级可承受）。

## 5. 与 spec #80 的接线

- #80 §1 查询面 `--as-of N` 的跨章审计回放、§5 金丝雀、§3 mutant 重放，全部消费本 spec §1 归档——**#80 文档中 F21 即本节**（#80 归档版 :85 声明在案；三消费方均在 #80 P2 路线图，近期具名消费者=本 spec §3 表）；
- #80 facts store 的投影层省流（settle ×2.8 膨胀的根治）以本 spec `observe_report` 的膨胀曲线为验收度量；
- 两 spec 共享伤口语料：`tests/fixtures/invariant-mutants/` 供门检红测，`observability/` 供 prompt 改进回放——职责不重叠。

## 6. 分期

- **P1（本批起）**：§1 归档 + blobs 去重 + DISPATCH 三加性字段 + RETRY 事件 + 逃逸舱 fail-fast + `observe_report` 骨架（四表 + 归档覆盖行）+ O-1 一行修复（已随挖矿提交）。
  - **P1 验收（离线形态，SDD 代码交付边界内——F947 纪律，fixtures/tmp_path 驱动，禁真实 dispatch）**：归档写档 + blob 去重 + `user_prompt_blob` 解引用字节级复现；fail-fast 3 次触发与四元组语义（复位/缺失 PASS/键隔离）。
  - **运行侧验收（运行验证阶段动作，不在 SDD 边界内——#80 先例）**：regen 续跑 2 束后 `observability/` 可字节级复现任一 drafting 派发的 prompt 与 reads。
- **P2**：`lint_reads_reconcile` + feedback 归档 + `dispatch_replay` 骨架（输入=归档+改版 SKILL，输出=diff 报告；**不名 `replay`**——与 `trace/replay.py`（签名链撕裂恢复，判据 7 I6b）同名异物）+ 归档滚动工具（§4 三件）。
- **P3**：A/B harness（同 dispatch 双 prompt 变体对照）+ 跨 run 聚合看板（卷间膨胀/失败率趋势）。

## 7. 验收（本 spec 完成定义——分期标注；P1 期交付时 1/2/5 的离线形态须绿，3/4 为 P2 期定义）

1. **[P1 离线]** fixture 语料上 `observe_report` 一键产出四表+归档覆盖行，数字与 token-ledger/trace 交叉对账一致；**[运行侧]** 下一卷任意 5 章窗口同口径复演（运行验证阶段）；
2. **[P1 离线]** O-2 复演防护：人为制造字段漂移（改 style_profile 一节标题）→ 同键 3 次派发内 `escape_hatch_drift` FAIL（escalation 路由，非 retry）；交错匹配读复位、状态文件缺失 PASS 两语义同批钉；
3. **[P2]** `lint_reads_reconcile` 对当前 20 技能全绿；对注入的 O-1 突变（旧字段名）红；
4. **[P2]** 回放演示：取一次归档 drafting 派发，在改版 SKILL.md 下 `dispatch_replay` 产出可 diff 的对照输出（P3 前以手工脚本形态即可）；
5. **[P1 离线]** 体积与熔断：`SHENBI_ARCHIVE_QUOTA_BYTES` 设 KB 级实测熔断路径（WARN + 跳 blobs + 档照写 + 降级记档）；**[运行侧]** 单卷 `observability/` ≤80MB（去重后）在下一卷实测。
