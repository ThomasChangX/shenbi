# META 块设计改进 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical（设计缺陷）
> **前置:** 无
> **目的:** 评估并改进 `<!--META-BEGIN-->...<!--META-END-->` 在章节交付文件中的嵌入策略——当前行为是设计如此，但存在下游消费风险。

---

## 1. 背景

### 1.1 现状

`shenbi-chapter-drafting` 的契约（`skills/shenbi-chapter-drafting/SKILL.md:95-130`）明确要求 `chapters/chapter-N.md` 包含 META 块：

```markdown
<!--META-BEGIN-->
## PRE_WRITE_CHECK
[核心任务、要兑现伏笔、本章禁忌、结尾模式、AI陷阱、共鸣缺口、转折词预算]
<!--META-END-->

# 章节标题
[正文内容]

<!--META-BEGIN-->
## POST_WRITE_SELF_CHECK
[转折词密度检查、章尾好奇心检查、反思/元叙事检查]
<!--META-END-->
```

**设计意图**（`SKILL.md:129`）：
> "下游解析器（字数统计、审计、评分）必须剥离 META 块后处理纯正文。"

下游剥离实现（`src/shenbi/gates/shared.py:120-121`）：
```python
c = re.sub(r"<!--META-BEGIN-->.*?<!--META-END-->", "", c, flags=re.DOTALL)
```

### 1.2 发现（2026-07-17 审计）

- 50/56 章（89%）包含 META 块
- 平均文件大小 31.3% 是 META 元数据
- 最严重：Ch24 达 49.9%（几乎一半是检查清单）
- 6 章无 META 块（Ch2/9/12/44/55——这些恰好是被修订元输出覆盖的损坏章节）

### 1.3 问题分析

虽然这是设计行为，但存在以下隐忧：

1. **下游消费风险**：任何不经 `shared.py` 处理直接读取 `chapters/chapter-N.md` 的消费者（人类读者、外部工具、未来 AI 阅读器）会看到内部检查清单
2. **文件语义混淆**：`chapter-N.md` 既是"可交付的小说章节"又是"内部质量控制文档"
3. **Git diff 噪声**：META 块变更（计划调整）与实际正文变更混在同一文件
4. **Token 浪费**：每章 ~31% 的 token 用于传输下游需剥离的内容

---

## 2. 方案对比

### 2.1 方案 A：META 块移至独立文件（推荐）

将 PRE/POST check 从 `chapter-N.md` 移至 `chapter-N-meta.md`：

**变更：**
- `shenbi-chapter-drafting` SKILL.md 输出契约：`writes` 增加 `chapters/chapter-N-meta.md`，`chapters/chapter-N.md` 中移除 META 块要求
- `shared.py:120-121`：移除 META 剥离逻辑（不再需要）
- 下游审计/评分 skill 读取 `chapter-N-meta.md` 获取自检数据

**优点：**
- `chapter-N.md` 成为纯粹的小说成品
- META 数据仍可被下游自动化消费
- 人类读者不会看到检查清单

**缺点：**
- 所有下游 skill 需更新读取路径（如果它们依赖 META 块字段）
- 破坏现有输出格式契约

### 2.2 方案 B：保持现状 + 强化文档

**变更：**
- 在 `docs/framework/` 中增加 "Chapter File Format" 文档，明确说明 META 块的存在和剥离方法
- 在 `SKILL.md` 输出格式部分增加醒目警告

**优点：**
- 零代码变更
- 不破坏现有契约

**缺点：**
- 不解决根本问题（文件语义混淆）
- 下游消费者仍需实现剥离逻辑

### 2.3 方案 C：YAML frontmatter 替代 HTML 注释

使用标准 YAML frontmatter 替代 `<!--META-BEGIN-->`：

```markdown
---
pre_check:
  core_task: ...
  hooks_to_fulfill: ...
  taboos: ...
post_check:
  transition_density: 0
  curiosity_check: pass
---

# 章节标题
[正文]
```

**优点：**
- 标准化格式，工具链原生支持
- 比 HTML 注释更易解析

**缺点：**
- 字段较多，frontmatter 会显著膨胀
- LLM 可能不严格遵守 YAML 格式

---

## 3. 推荐决策

**短期（本 spec）：方案 B**——保持现状 + 强化文档。

原因：
- META 块是经过深思熟虑的设计决策（`SKILL.md:129` 的注释证明设计者已意识到剥离需求）
- 31.3% 的平均污染率在剥离后不影响下游处理
- 方案 A 需要大量下游 skill 变更（关联 H1/H2/H3 等多个 spec）

**中期（后续 spec）：方案 A**——当 decisions.json 格式稳定（Spec H1）、修订系统修复（Spec H2）后，进行 META 块分离。

---

## 4. 实施内容

### 4.1 文档增强

1. **创建** `docs/framework/chapter-file-format.md`：
   - 说明 `chapter-N.md` 的完整格式规范
   - META 块的存在理由（质量控制自检）
   - 下游消费者剥离方法（引用 `shared.py:120-121`）
   - META 块字段定义

2. **更新** `skills/shenbi-chapter-drafting/SKILL.md:129`：
   - 将现有注释升格为醒目警告块
   - 增加 "META 块不构成小说正文的一部分" 的明确声明

### 4.2 可选：增加 G2 检查

在 `g2.py` 的章节文件检查中增加：
- `G2.meta_ratio`：META 块占比 > 50% 时 WARN（提示 planning 过度膨胀）

---

## 5. 验证标准

1. `docs/framework/chapter-file-format.md` 完整且准确
2. `SKILL.md` 更新后警告清晰可见
3. `just check` 全量通过（零代码变更）

---

## 6. 依赖关系

```
无前置依赖（文档变更）
  ↓
中期：依赖 Spec H1（JSON格式稳定）+ Spec H2（修订系统修复）后可推进方案A
```
