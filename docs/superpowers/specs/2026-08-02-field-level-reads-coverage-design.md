# 字段级 reads 覆盖率：三大 truth 文件的精准切片

> **Date:** 2026-08-02
> **Status:** Design
> **Severity:** 🟡 Medium（P1 契约一致 + 效率混合；浪费量大但字段名匹配有准确性风险）
> **方法:** [`systematic-debugging`](archive/2026-07-19-06-llm-context-engineering-design.md) skill 四阶段（Root Cause → Pattern → Hypothesis → Implementation）
> **系列:** Token 效率全栈 audit（契约层补漏，承接已归档总纲 [`archive/2026-08-01-pipeline-read-write-consistency-audit-design.md`](archive/2026-08-01-pipeline-read-write-consistency-audit-design.md) §3.7 + §6.2 P1 第二项；PR #39 plan T8 延后项）
> **依赖:** 已归档总纲（§3.7 finding、§6.2 P1 分级、07-18 §2.1 字段分析）；`src/shenbi/contracts/fields.py` `filter_to_fields`；`src/shenbi/pipeline/dispatch_helper.py` `_build_skill_prompt` read 循环；`skills/shenbi-{chapter-planning,chapter-drafting,context-composing,review-world-rules}/SKILL.md`；真实 round 输出 `novel-output/*/outline/volume_map.md` + `world/power_system.md`（section header 验证来源）
> **范围:** 本 spec 只审 **字段级 reads 过滤（Layer B）的覆盖率提升**——为三大 truth 文件（chapter-N.md / power_system.md / volume_map.md）在高频 skill 的 reads 声明精确 fields，使 dispatcher 只发相关 section 而非全文。**不审** P0 纯浪费（PR #39 已清）、不审 P2 cache/IDE/示例（见 P2 spec #6）、不审采样/模型/重试（见 #3）、不审输出侧（见 #5）、不审确定性替换（见 #4）。
> **Purpose:** 把总纲 §3.7 从"发现+提议"推进到"可实施"——解决 PR #39 T8 延后的根因（字段名需真实 round 输出验证）。本 spec 用 `novel-output/` 真实 round 的 section header 落证字段名，消除"声明错了无感知"的逃逸门风险。

---

## 1. 背景：字段级过滤机制现状

### 1.1 机制

dispatcher 的 `_build_skill_prompt` read 循环对每个 read 条目：
- **string 形**（`- chapters/chapter-N.md`）：全文发送。
- **dict 形**（`- file: chapters/chapter-N.md\n  fields: [主角状态, 当前场景]`）：调 `filter_to_fields(content, fields, path)`（`contracts/fields.py:83`），只提取匹配的 `## ` section。

`filter_to_fields` 的逃逸门：若声明的 field 在文件中**无匹配**，返回全文 + log WARN（`fields.py` 末尾）。这意味着"声明错了"无硬失败——LLM 仍收到全文，token 未省，但只 log 不 raise。

### 1.2 覆盖率现状（PR #39 后复验）

268 条 read 中 dict-form `fields:` 仅 35 条（13.1%），58/73 skill 从不用字段过滤。**三大文件零 fields 声明**（在高频 skill 中）：

| 文件 | 体积 | 高频消费 skill | 当前 fields 声明 |
|------|------|---------------|----------------|
| `chapters/chapter-N.md` | ~31KB | 35 个 skill 全文读（drafting/revision/context-composing/...） | ❌ 零 |
| `world/power_system.md` | ~28.8KB | review-world-rules / context-composing | ❌ 零 |
| `outline/volume_map.md` | ~26.3KB | chapter-planning / context-composing | ❌ 零（仅 foreshadowing-lifecycle 声明了 1 个 field，非高频 skill） |

### 1.3 浪费量

三大文件每次全发 ~86KB；若字段过滤生效可降至 ~3-5KB → 单次省 ~80KB。高频 skill（planning / drafting / context-composing）累计省 ~200-400KB/章。

---

## 2. 根因发现：字段名匹配的三类风险

### 2.1 风险 A：volume_map 的 section header 是动态的

`volume_map.md` 的 section header 是**卷标题**（`## 第一卷：觉醒之火（第1-15章）` / `## 第二卷：...`），每本书不同——不能用固定 field 名匹配。

证据：`novel-output/xinghuo-ranqiong/outline/volume_map.md` 的 headers（`grep "^## "`）：
```
## 第一卷：觉醒之火（第1-15章）
## 第二卷：铁与火（第16-35章）
## 第三卷：至暗时刻（第36-55章）
## 第四卷：燎原之势（第56-75章）
## 第五卷：星火燃穹（第76-100章）
## 汇总
```

**结论：** volume_map **不适合 `fields:` 字段过滤**（field 名无法跨书复用）。已有的 `_extract_volume_chapter`（`audit_context_cache.py:90`，按 chapter 号提取当前卷节点）才是正确抽象——但它当前只被 SharedAuditContext 调用，不在通用 read 路径。

### 2.2 风险 B：power_system 的 section header 是固定的

`power_system.md` 有固定 header（适合字段过滤）：
```
## 总览
## 等级表
## 进阶规则
## 能力边界
## 代价机制
## 力量天花板
## 跨级战斗参考
## 与世界观核心主题的关系
## 力量体系设计汇总
```

不同 skill 需要不同 subset：
- `review-world-rules`：需 `能力边界` + `代价机制` + `力量天花板`（审一致性），不需 `等级表` 细节。
- `context-composing`：需 `等级表` + `总览`（给 drafting 提供当前能力上限上下文），不需 `跨级战斗参考`。

### 2.3 风险 C：chapter-N.md 的 section header 极少且半结构化

`chapter-N.md` 的 header 只有 `## PRE_WRITE_CHECK`（auto-gen 元数据）+ `# 第N章：<标题>`（正文标题）。正文本身是连续 prose，**没有 `## ` section 可过滤**。

**结论：** chapter-N.md **不适合字段过滤**——它的"浪费"是正文过长（~31KB），但正文是连续叙事无法按 section 切。减少 chapter-N.md token 的正确方向是 P2 spec #6 的示例外置（drafting 不需要读前章全文，只需摘要）或确定性替换 spec #4 的 snapshot 机制，**非本 spec 范围**。

### 2.4 修正后的可实施范围

| 文件 | 可字段过滤？ | 本 spec 处置 |
|------|------------|-------------|
| `power_system.md` | ✅ 固定 header | **本 spec §3：声明 fields** |
| `volume_map.md` | ❌ 动态卷标题 | **本 spec §4：把 `_extract_volume_chapter` 接入通用 read 路径**（非 fields，是提取器） |
| `chapter-N.md` | ❌ 连续 prose 无 section | **不在本 spec 范围**——归 P2 spec #6 §1 cache（章首快照）+ §3 示例外置 |

---

## 3. Finding：power_system.md 字段级声明

### 3.1 修复方案

为消费 `power_system.md` 的 skill 声明精确 fields：

| skill | 当前 read | 应声明 fields | 理由（从 skill body 反推） |
|-------|----------|-------------|--------------------------|
| `review-world-rules` | 全文 ~28.8KB | `[能力边界, 代价机制, 力量天花板, 跨级战斗参考]` | 审查目标是"能力体系一致性"——边界/代价/天花板是审查依据；等级表细节 + 进阶规则是 reference |
| `context-composing` | 全文 | `[等级表, 总览, 力量天花板]` | 为 drafting 提供能力上限上下文——等级表 + 天花板是必须；进阶规则/代价是 revision 时才细审 |

### 3.2 验证

- 字段名对照 `novel-output/*/world/power_system.md` 的真实 `## ` header（§2.2 已落证）——**必须在 plan 实施时 grep 确认 header 名字节匹配**（`filter_to_fields` 的 NFKC 归一化会处理全角/空白差异，但 header 文本本身必须对得上）。
- `filter_to_fields` 的逃逸门（field 不匹配返回全文 + WARN）：plan 必须加一步"跑一章后 grep structlog 无 `field_not_found` WARN"——确保声明的 field 真匹配。
- G4 对 review-world-rules / context-composing 仍 PASS（字段过滤后 LLM 仍有所需上下文）。

### 3.3 度量（TokenLedger，PR #39 前提）

改前 vs 改后，review-world-rules + context-composing 的 `prompt_tokens` 下降（power_system 从 ~28.8KB 降至 ~8-12KB，省 ~16-20KB/次）。

---

## 4. Finding：volume_map.md 提取器接入通用 read 路径

### 4.1 现状

`_extract_volume_chapter`（`audit_context_cache.py:90`）已实现按 chapter 号提取当前卷节点（读 volume_map，找 `## 第X卷` section，返回当前章所在卷的节点文本）。但：
- 只被 `build_shared_audit_context` 调用（审计场景）。
- `chapter-planning` / `context-composing` 的通用 read 路径仍全文读 volume_map（~26.3KB）。

### 4.2 修复方案

在 `_build_skill_prompt` 的 read 循环中，对 `volume_map.md` 的 read **特殊处理**：
- 若 read 条目是 `outline/volume_map.md` 且当前 `chapter` 已知：调 `_extract_volume_chapter(volume_map_text, chapter)` 只发当前卷节点（~500B-2KB），非全文。
- 若 chapter 未知（如 foundation phase）：全文读（兜底）。

**实现选择（plan 阶段定）:**
- **选项 A（契约层）:** 新增 dict-form read 的 `extractor:` 字段（`- file: outline/volume_map.md\n  extractor: volume_chapter`），dispatcher 按 extractor 名调对应提取函数。**优点：** 通用，未来其他动态-header 文件可复用。**缺点：** 扩展契约 schema。
- **选项 B（dispatcher 硬编码）:** `_build_skill_prompt` read 循环里 `if full_path.name == "volume_map.md" and chapter: content = _extract_volume_chapter(content, chapter)`。**优点：** 零契约变更。**缺点：** volume_map 特殊化，不可泛化。

**推荐选项 A**（与 dict-form `fields:` 的扩展模式一致；`extractor:` 是 `fields:` 的动态版——前者按函数提取，后者按 header 匹配）。

### 4.3 验证

- chapter-planning / context-composing 的 volume_map read 从 ~26.3KB 降至 ~500B-2KB。
- `_extract_volume_chapter` 的现有测试（若有）仍 PASS；加测试：chapter=3 返回第二卷节点（非全文）。
- G4 对 chapter-planning / context-composing 仍 PASS。
- 度量：TokenLedger prompt_tokens 下降。

---

## 5. 假设与验证（每条一行）

| # | 假设 | 验证 |
|---|------|------|
| §3 | power_system 的固定 header 跨书一致 | grep `novel-output/*/world/power_system.md` 的 `## ` header 对比（≥2 本书） |
| §3 | 声明的 field subset 覆盖 skill 实际需要 | 跑一章 + grep structlog 无 `field_not_found` WARN + G4 PASS |
| §4 | `_extract_volume_chapter` 返回的节点足够 chapter-planning 决策 | G4 对 chapter-planning PASS + 人工抽查 plan 质量 |
| §4 | chapter 未知时全文兜底不破坏 foundation phase | foundation phase round 的 G4 PASS |

---

## 6. 修复方案分级

### 6.1 P1（本 spec 实施）

| finding | 修复 | 风险 | 验证 |
|---------|------|------|------|
| §3 power_system fields | review-world-rules + context-composing 声明 fields | 低（field 不匹配有 WARN 逃逸门 + 全文兜底） | G4 PASS + 无 WARN + TokenLedger 下降 |
| §4 volume_map extractor | 接入 `_extract_volume_chapter`（选项 A：`extractor:` 契约字段） | 中（契约 schema 扩展 + 提取器函数注册机制） | G4 PASS + 提取返回正确卷节点 |

### 6.2 显式不做

- **chapter-N.md 字段过滤：** 连续 prose 无 `## ` section，不适合字段过滤。减少 chapter-N token 归 P2 spec #6（cache 章首快照 + 示例外置）+ 确定性替换 #4（snapshot）。
- **volume_map 的 `fields:` 声明：** 动态卷标题无法用固定 field 名；必须用提取器（§4）。

---

## 7. 验证标准（数值化）

| 标准 | 当前 | 目标 |
|---|---|---|
| power_system.md 在 review-world-rules 的发送体积 | ~28.8KB（全文） | ~8-12KB（4 fields） |
| volume_map.md 在 chapter-planning 的发送体积 | ~26.3KB（全文） | ~500B-2KB（当前卷节点） |
| `>5KB reads` 的字段级覆盖率（含 extractor） | ~13% | ≥30%（三大文件中 2 个覆盖；chapter-N 归 P2/#4） |
| `filter_to_fields` 逃逸门 WARN 数 | 未测 | 0（所有声明的 field 匹配真实 header） |
| G4（review-world-rules / context-composing / chapter-planning） | PASS | PASS |
| TokenLedger prompt_tokens（改前 vs 改后） | baseline | 下降 |

---

## 8. 铁律

1. **字段名必须落证真实文件。** power_system 的 fields 声明前，grep `novel-output/*/world/power_system.md` 的 `## ` header 对比 ≥2 本书确认一致。不可从 skill body 推测——body 描述的是概念名，header 是字节匹配键。
2. **逃逸门 WARN 即缺陷。** `filter_to_fields` field 不匹配返回全文 + WARN——plan 实施后跑一章，structlog 出现 `field_not_found` WARN 即 field 声明错，必须修（不可接受"全文兜底"作为常态）。
3. **volume_map 不用 fields 用 extractor。** 动态 header 文件不可假装能字段过滤——用 `_extract_volume_chapter` 提取器，或接受全文。

---

## 9. 依赖关系

```
PR #39（TokenLedger 度量前提）—— 已合并
        │
        ▼
本 spec:
  ├─ §3 power_system fields ─── 依赖: 真实 round header 验证（novel-output/）+ filter_to_fields
  └─ §4 volume_map extractor ── 依赖: _extract_volume_chapter（已存在）+ 契约 schema 扩展（extractor: 字段）
        │
        ▼
  各自 plan + 实施 + G4 验证 ──► 归档本 spec
```

与 P2 spec #6 的边界：本 spec 管"读什么字段"（精准切片），#6 管"读过的缓存"（避免重发）。两者互补不冲突——本 spec 的 fields 声明减少单次体积，#6 的 cache 减少重复发送次数。

本 spec 是 **design，不实施**。实施前需另写 plan 并批准。
