# regen-vol1 观测记录挖矿报告（Track A）

**日期**：2026-10-28 ｜ **对象**：`novel-xinghuo-vol1`（genesis + ch1-24，2026-10-26/27 两日）
**目的**：证明「已记录的 trace/账本/取证/裁决可以在多大程度上支撑系统与 prompt 优化推断」，并把发现映射到 spec #80/#81。
**方法**：仅用项目目录既有落盘物做交叉分析（无新增埋点）——这正是 spec #81 要固化的 `observe_report` 的手工首跑。

---

## 摘要（五发现）

| # | 发现 | 量级 | 处置 |
|---|---|---|---|
| O-1 | `foundation/review_report.md` 契约字段漂移：planning 声明 `建议修复`，regen 产出标题 `建议修复（按文件定位）` → 逃生舱全量注入 | 29 次（ch1-23 每次奇数章 planning） | 已修（producer 侧对齐，见 §C）；fail-fast + 字段对账 lint 入 spec #81 P1 |
| O-2 | `style/style_profile.md` 字段失配 35 次（drafting 29 + resonance 6，跨两日），但今日文件全匹配 → **dispatch 时刻文件状态不可考** | 35 次 | 归档缺口活证据 → spec #81 §1 dispatch 归档 |
| O-3 | 逃逸舱 WARN（`field_filter_missing_fields`）连发 64 次，无任何门/lint 消费——write-only oracle 复发于日志层 | 64 次 | 逃逸舱 fail-fast 硬化 → spec #81 §3 |
| A-1 | settle prompt 膨胀 19K→72K（×2.8），session28 架构发现在 regen 运行复现且更重 | ×2.8 | facts 投影层（spec #80 §1）+ spec #80 P3 |
| B-1 | drafting 场景算术循环最深 10 轮，每轮全价重发 prompt | 10 轮/章 | 循环增量反馈 → spec #81 §2 |

---

## 数据源与口径

| 源 | 规模 | 记录什么 |
|---|---|---|
| `trace.jsonl` | 491 事件（223 DISPATCH / 267 AUDIT_PASS / 1 GATE_FAIL），带签名+schema 单调 | 每派发：skill/chapter/model/finish_reason/attempt/reads（路径+模式+matched_all） |
| `cost/token-ledger.jsonl` | 287 行 | 每派发 tokens/成本/attempt |
| `diagnostics/failed-write-*.md` | 38 份 | 写阶段失败的 LLM 原文取证 |
| `adjudications/*.md` | 31 份 | 监控侧裁决（含根因） |
| `gate-markers/*.json` | 20 技能 | G4 结果 |

**口径缺口（本报告的天花板）**：无 dispatch 时刻 prompt/响应快照、无成功路径响应原文、无中间草稿。O-2 即此缺口的活证据。

---

## A. Prompt 构成与膨胀（trace.reads × token-ledger）

**成本与体量总表**（总 $2.44 / prompt 7.84M / completion 4.81M，completion 占比 38%）：

| skill | 成本 | 派发 | 平均输入 | 备注 |
|---|---|---|---|---|
| chapter-drafting | $0.756 | 64 | 21.3K | 循环最深 10 轮 |
| state-settling | $0.321 | 22 | 42.6K | 膨胀 ×2.8（19K→72K） |
| chapter-planning | $0.248 | 33 | 43.3K | **全程最重**；O-1 贡献 ~10K/次 |
| foreshadowing-lifecycle | $0.197 | 17 | 30.0K | |
| review-group-factual | $0.117 | 16 | 39.2K | |
| chapter-revision | $0.110 | 14 | 13.1K | |

**注入频次 top**：genre-config.json ×130、pending_hooks ×69、audit_drift ×68、style_profile ×66、current_state ×63。字段切片模式 310/1806（17%）——字段级 reads 的省流潜力大部分尚未兑现（O-1/O-2 两文件恰是本应切片却全程逃逸的）。

**膨胀归因**：
- **planning 43K 最重**：O-1 使 27.9KB 的 review_report 全量注入每次 planning（本应只注入「建议修复」一节），约 10K tokens/次 ≈ planning 平均输入的 1/4。
- **settle ×2.8**：累积 truth 无界的架构问题（session28 发现）在本运行复现且更重——spec #80 facts 投影层 + P3「增量 op 替代整档重写」的实弹依据。
- **drafting 10 轮循环**：场景算术反馈每轮重发全量 prompt（21K×10）——增量反馈（只发差值段落+算术表）是最大单项优化。

---

## B. 失败流行病学（diagnostics × ledger loop depth × trace）

- **38 份失败取证中 30 份是 review-group 族**（5 组各 6 份），聚成两簇：`20261026T2159-2201` 与 `T2312-2314`。两簇 = 两次系统性事故 × 5 组连坐 × ~3 轮重试——**单点格式事故级联到全部评审组**，非孤立技能问题。
- planning 失败 4 份（ch1 创世首章调参期）；highpoint/revision/drafting 各 1。
- API 级 attempt>1 仅 6 次（全部创世族）——**重试压力不在 API 层而在门检循环层**（drafting 10 / planning 6 / settle 3），token 账本的 attempt 字段看不见循环层重派，这是记录口径盲区（spec #81 §2 loop_id 补全）。

---

## C. 逃逸舱失配（本次挖矿新发现）

**O-1（已验证根因，已修）**：`skills/shenbi-chapter-planning/SKILL.md` 声明 `fields: [建议修复]`；regen 产出的 `foundation/review_report.md` 标题为 `## 建议修复（按文件定位）`。精确匹配（`fields.py:35` NFKC+空白归一后全等）失败 → 逃生舱全量返回（27897 字符注入，本应 3520，**该 read 省 87%**）。

**修复定向的关键证据**：reality-lock 测试（ch118 旧运行语料）显示旧运行的标题就是 `建议修复`，且 foundation-review 自身 SKILL 输出模板（L127）钉的正是 `### 建议修复`——即 **producer 模板与两代消费契约一贯正确，regen 运行时模型偏写了模板**（连标题层级都从 `###` 偏成 `##`），且产出无门校验对模板的忠实度。四槽画像：声明✓ 载体✗ 门检✗。因此修复走 producer 侧对齐而非改契约：契约保持 `建议修复`；项目文件标题归位 `## 建议修复`；系统修复 = 逃逸舱 fail-fast（3 次内浮出）+ `lint_reads_reconcile`（spec #81 §3）。**根因类**：consumer 在 producer 自由格式输出上声明精确字段 + 产出忠实度无门。

**O-2（不可归因，归档缺口活证据）**：style_profile 35 次失配跨两日，但用**当前**文件复测三个声明字段全部命中（`matched_all=True`）。要么文件中途被重生成、要么当时契约不同——**没有 dispatch 时刻快照，永远无法裁决**。这是「为什么需要 spec #81 §1」的最直接论据。

**O-3**：`field_filter_missing_fields` WARN 连发 64 次无人消费。若任何门/lint 盯住它，O-1 在 ch1 就会暴露，而不是 24 章后靠挖矿发现。

---

## D. 裁决维度画像（31 份裁决书）

| 族 | 数 | 说明 |
|---|---|---|
| state-settle | 6（含重沉降 ×2） | 最重族；matrix 增量语义 + follower 登记 |
| planning escalation | 4 | ch1×3 + ch5/ch7——契约固化后消失 |
| genesis | 4 | 创世调参期 |
| chapter-memo | 3 | F6 备忘丢失族（已根因修复） |
| per-chapter | 3 | 评审族 retry 收束 |
| drafting/scene-split | 2 | 字数三环 |
| 代感复查 | 1 | 五处跨章硬断裂（裸名/骨哨/计数三类伤口 → spec #80 F15-F17） |

内容伤口与 spec #80 门检一一对应：裸名 113 处→F15、骨哨双条目→F16、计数链→F17。跨章不变量维度 55 分的最弱项即此三类。

---

## E. 修复映射

| 修复 | 层级 | 去向 |
|---|---|---|
| O-1 producer 侧对齐（契约保持 `建议修复`；项目文件标题归位；reality-lock 三绿） | 立即（本批） | 本批提交 |
| truth-files.yaml patterns 补 `chapters/chapter-{N+1}.md`（上批 5ed419b4 settle 契约的遗留孤儿读）+ dispatcher 测试期望同步 F12 双 read | 立即（本批） | 本批提交 |
| 逃逸舱 fail-fast（同文件 matched_all=false ≥3 次 → 门检 FAIL） | 系统 | spec #81 §3 P1 |
| 字段对账 lint（契约 fields ↔ 实际文件标题，lint_decisions_sources 模式） | 系统 | spec #81 §3 P2 |
| dispatch 归档（prompt/响应原文 + reads 内容寻址快照） | 系统 | spec #81 §1 P1（F21） |
| DISPATCH 加性字段（loop_id / feedback_ref / archive_path）+ 循环层重派结构化 | 系统 | spec #81 §2 P1/P2 |
| settle 投影层 / drafting 循环增量反馈 | 系统 | spec #80 §1+P3 / spec #81 §2 |
| review-group 级联（一事故五组连坐） | 观察 | 待归档落地后按 prompt 证据定位格式事故根因 |

---

## 结论

**现有记录已足以支撑结构层优化的推断分析**（本报告全部发现仅用既有落盘物）；**不足以支撑 prompt 文本级因果优化**（O-2 类问题永远不可裁决、改进无法 A/B 验证）。补齐归档（spec #81）后，下一卷起两类都可行。
