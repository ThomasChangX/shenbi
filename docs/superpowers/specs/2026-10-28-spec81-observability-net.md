# Spec #81 · 观测完备性之网（observability-net）：让记录足以持续优化系统与 prompt

**日期**：2026-10-28 ｜ **系列**：regen-vol1 收尾（与 #80 invariant-net 配对：#80 管「生成对不对」，#81 管「凭什么知道、凭什么改进」）
**状态**：Active ｜ **动机证据**：`docs/regen-vol1-observability-mining.md`（Track A 手工首跑，五发现 O-1/O-2/O-3/A-1/B-1）

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

---

## 1. dispatch 归档层（archive layer，= #80 所引 F21）

每次派发落一档 `observability/dispatches/{seq:05d}-{skill}-ch{N:03d}-a{attempt}.json`：

```jsonc
{
  "seq": 122, "ts": "...", "skill": "shenbi-chapter-drafting", "chapter": 20, "attempt": 1,
  "model": "deepseek-v4-flash", "finish_reason": "stop",
  "system_prompt_sha256": "...", "user_prompt_sha256": "...",
  "response_sha256": "...",          // 正文存 blob，档里只放哈希与指针
  "reads": [ {"path": "truth/current_state.md", "mode": "fields", "matched_all": false,
              "blob": "sha256:...", "resolved_fields": [...]} ],
  "usage": {"prompt_tokens": 29213, "completion_tokens": 8102},
  "loop_id": 3, "feedback_ref": "sha256:..."   // §2
}
```

- **正文与 reads 快照进内容寻址库** `observability/blobs/<sha256>`：reads 重复注入率极高（genre-config ×130/卷），去重后估测 ~40-60MB/卷原始文本 → blobs 实存 ~15-25MB。
- **默认开启**（用户令「确保之后可以通过记录进一步优化」）；`SHENBI_ARCHIVE_DISPATCH=0` 可关（极端环境）。写档 fail-safe：归档失败不阻断派发（与 `_persist_failed_write_output` 同纪律），但记 `archive_write_failed` WARN 并计入 §3 消费报表。
- **接线点**：`dispatch_helper._dispatch_via_api` 成功/失败两分支各加一次落档（失败分支与现有 `diagnostics/failed-write-*` 并存——前者是结构化归档，后者是即视取证）。
- **配额熔断**：`observability/` 目录 >1GB → WARN + 跳过 blobs 新写（档与哈希照写，可后补）——L-B 的硬防线。

## 2. trace 结构化补全（加性字段，schema_version 保持 1）

- **DISPATCH 增字段**（全部可选，旧事件兼容；`versioning.py` 单调约束不破坏，结构性变更才升 v2 走 MIGRATIONS）：
  - `loop_id`：同 (skill, chapter) 的轮次序号——token 账本 `attempt` 只见 API 级重试（6 次/卷），循环层重派（drafting 10 轮）至今不可见（B-1）；
  - `feedback_ref`：重派反馈的 blob 哈希——循环反馈目前只活在代码里，「兜底反馈零信息」类问题（probe8 教训）从此有据可查；
  - `archive_path`：指向 §1 档案。
- **新事件 `RETRY`**：门检/监控触发的循环重派时记结构化原因（如场景算术差值 `{scene: 2, actual: 1995, band: [1800,2000]}`），替代只能翻 runner 日志的现状。

## 3. 消费者契约（L-A 的机制化）

| 记录 | 具名消费者 | 层级 |
|---|---|---|
| dispatches 归档 | `replay` 骨架（P2，喂 #80 mutant/金丝雀）+ `observe_report` | P2 |
| trace 新字段 | `tools/observe_report.py`（P1）：膨胀曲线 / loop depth / 失败簇 / 逃逸舱四表一键产出 | P1 |
| 逃逸舱 WARN | **fail-fast 硬化**：同文件 `matched_all=false` 连续 ≥3 次 → G 检点 FAIL（不再只 WARN） | P1 |
| 契约 fields 声明 | **`tools/lint_reads_reconcile.py`**：所有 SKILL reads 的 `fields:` ↔ 项目内实际文件标题对账（`lint_decisions_sources` 三源对账同模式；O-1 类漂移在 CI 即红） | P2 |
| 归档写失败 WARN | `observe_report` 末行汇总 | P1 |

**逃逸舱硬化语义**：`fields.py` 逃生舱（spec #9 R3 / F218）保留——契约错了不该断生成；但**同文件连发 3 次**证明是漂移不是偶发，必须浮出为门检失败。计数器按 (project, path) 存 `observability/escape-hatch-state.json`。

## 4. 保留与轮转（L-B）

- `dispatches/` 按 `--through <ch>` 滚动压缩为 `dispatches-001-060.tar.zst`（对齐 `just pool-archive`/`ledger-archive` 的窗口纪律）；
- blobs 引用计数：滚动归档后零引用 blob 回收；
- `observability/index.jsonl`：每派发一行指针（seq/skill/chapter/sha），跨 run 聚合查询不触 tar。

## 5. 与 spec #80 的接线

- #80 §1 查询面 `--as-of N` 的跨章审计回放、§5 金丝雀、§3 mutant 重放，全部消费本 spec §1 归档——**#80 文档中 F21 即本节**；
- #80 facts store 的投影层省流（settle ×2.8 膨胀的根治）以本 spec `observe_report` 的膨胀曲线为验收度量；
- 两 spec 共享伤口语料：`tests/fixtures/invariant-mutants/` 供门检红测，`observability/` 供 prompt 改进回放——职责不重叠。

## 6. 分期

- **P1（本批起）**：§1 归档 + blobs 去重 + DISPATCH 三加性字段 + RETRY 事件 + 逃逸舱 fail-fast + `observe_report` 骨架（四表）+ **O-1 一行修复**（本批已随挖矿提交）。验收：regen 续跑 2 束后 `observability/` 可字节级复现任一 drafting 派发的 prompt 与 reads。
- **P2**：`lint_reads_reconcile` + feedback 归档 + `replay` 骨架（输入=归档+改版 SKILL，输出=diff 报告）+ 归档滚动工具。
- **P3**：A/B harness（同 dispatch 双 prompt 变体对照）+ 跨 run 聚合看板（卷间膨胀/失败率趋势）。

## 7. 验收（本 spec 完成定义）

1. 下一卷任意 5 章窗口：`observe_report` 一键产出四表，数字与 token-ledger/trace 交叉对账一致；
2. O-2 复演防护：人为制造字段漂移（改 style_profile 一节标题）→ 3 次派发内 fail-fast FAIL；
3. `lint_reads_reconcile` 对当前 20 技能全绿；对注入的 O-1 突变（旧字段名）红；
4. 回放演示：取一次归档 drafting 派发，在改版 SKILL.md 下 replay 产出可 diff 的对照输出（P3 前以手工脚本形态即可）；
5. 体积：单卷 `observability/` ≤80MB（去重后），超限熔断路径实测触发一次。
