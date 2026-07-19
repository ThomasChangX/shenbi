# 修复章节标题退化 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** 无
> **目的:** 修复章节标题从诗歌式命名退化为日期标签的问题——镜像了散文崩塌——并修复重复标题和 Ch40 违反命名规则。

---

## 1. 背景

### 1.1 发现（D1）

标题演变趋势：

| 阶段 | 标题示例 | 特征 |
|------|---------|------|
| Ch1-16 | 废料场、痕迹、沉、见、持、晨 | 诗歌式单字/双字 |
| Ch25-35 | 秋、又一天、冷、三天 | 过渡期 |
| Ch36-56 | Saturday、第四周Saturday、第五周周五、周三 | **日期标签** |

重复标题：`又一天` ×2（Ch27 + ?）、`Saturday` ×2（Ch36 + ?）

Ch40 违反规则：标题为 `第40章`（SKILL.md:125 禁止标题含章节号）

---

## 2. 修复方案

### 2.1 G4 标题检查

新增 `G4.cd.title` 检查：

```python
# 检查标题规则
if re.search(r'第\d+章', title):
    issues.append("G4.cd.title:contains_chapter_number")
if title in previous_titles:
    issues.append(f"G4.cd.title:duplicate_of_ch{previous_titles[title]}")
if re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|周[一二三四五六日])', title):
    issues.append("G4.cd.title:day_label_instead_of_thematic_name")  # WARN 非 HARD
```

### 2.2 Chapter planning prompt 增强

在 planning prompt 中增加标题要求：
- "标题应为 1-4 个汉字的主题性短语"
- "禁止使用星期/日期作为标题"
- "禁止包含章节序号"

---

## 3. 验证标准

1. 连续 10 章标题无日期标签
2. 0 重复标题
3. 0 标题含章节号
4. `just check` 全量通过
