# Spec #100 T0 核验报告：首派欠带族 = POST 自检虚报（2026-11-09）

**核对人**：SDD 协调者（`/sdd-next 100` 会话）｜**口径**：`total_chars_md_text`（全字符剥后，与 G4.cd/word_band 同源）
**证据源**：`novel-xinghuo-vol1/`（trace.jsonl / pipeline-manifest.json / observability blobs / plans / chapters）

---

## §0 原假设驳斥（H1/H2/H3）

| 原假设 | 结论 | 证据 |
|---|---|---|
| H1 场景预算与字数带脱钩 | **驳斥** | 首派 user prompt 数据区已含 `目标字数 3200`+`场景1 1050/场景2 1100/场景3 1050`（00248 prompt blob 行 299/310-313；读面 `## 1. 当前任务` 的 H2 body 含 `### 场景预算与收束钩`）；模型 PRE 自检亦引用同量级数字 |
| H2 无首派目标锚 | **驳斥** | 双重锚已落地：plan 逐场景预算（上）+ spec #95 T5 上一通过章全文 EXEMPLAR（首派常驻，blob 第 9 行 `## EXEMPLAR CHAPTER`） |
| H3 带下限贴沿 | **降级为结构备注** | 六章 plan 预算实测 3200-3400（不贴 2800 下沿）；`3×900=2700<2800` 仅算术张力备注，不作操作性根因 |

## §1 六章首派 POST 声明 vs 实测（H4 成立表）

| 章 | 首派实测 total | POST 声明总计 | 声明/实测 | 判定 |
|---|---:|---:|---:|---|
| ch43 | 2256 | 2885 | 1.28 | 欠带 -19%；虚报 28% |
| ch44 | 1788 | 2373 | 1.33 | 欠带 -36%；虚报 33% |
| ch45 | 2881 | 3360 | 1.17 | 总额在带；场景 2/3 落灰域（876/821<900） |
| ch46 | 2052 | 3400 | 1.66 | 欠带 -27%；虚报 66% |
| ch47 | 2288 | 3210 | 1.40 | 欠带 -18%；**虚报 40%** |
| ch48 | 1646 | 3250 | 1.97 | 欠带 -41%；**虚报 97%** |

- 5/6 章首派总额欠带（-18%~-41%）；**束5-7 四章 POST≈PRE（ch45/46 数值逐位相同）**——自检不是测量而是复述计划预算。
- 口径勘误：ch45 的 2889 系场景和/chapter_band 口径，word_band 口径为 2881。

## §2 死线三证（检测能力在场、首派消费缺失）

1. **manifest 分布**：`cd.post_wordcount_precision` 共 **34 个 gate entry / 13 条唯一 WARN**，漂移 **2.1%-15.5%**（ch37 4.4%、ch38 6.6%、ch45 2.8%、ch46 6.8%、final ch48 2.9%）——全部为**已晋升且在带**的章，G4 只落 WARN。
2. **rewind issues 零 precision 行**：trace 全部 `monitor_rewind` 事件（seq 1070/1129/1195/1204 等）issues 列表无 precision 行；全 trace 零 `precision` 字样。
3. **被 word_band 拒的首派短 bundle 未跑 G4.cd**：`_run_scene_split_step` 在 `commit_staging` 前 `return issues`（chapter_loop.py:1558-1559 vs :1565），promotion 不发生 → G4.cd 不运行。通过 validate_split 的首派在 promotion 后仍跑 G4，只是 WARN 不进反馈。

## §3 触发覆盖与 first-retry 基线（T3 线 3）

- **触发覆盖 4/6**（false in-band claim = declared ∈ 带 ∧ actual < 下限）：ch43（2885/2256）、ch46（3400/2052）、ch47（3210/2288）、ch48（3250/1646）命中；ch44 声明本就出带（2373）、ch45 实测在带（2881）不触发 → 非 no-op。
- **first-retry 基线**（第一次重派 POST 声明/实测）：ch47 3358/3511=**4.6%**、ch48 3100/3015=**2.8%**（对应 T3 线 3 目标 ≤2%）。
- 束7 `monitor_rewind` RETRY 计数基线 = **6**（bundle 级；「loop 8→2→3→8」系 issue 数简写非 loop 数）。
- 「第二轮带内率」基线 2/2（首重派即入带）——**无 headroom**，降为天花板防回归指标。
