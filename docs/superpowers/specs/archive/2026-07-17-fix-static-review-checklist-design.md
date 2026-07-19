# 修复审查清单完全静态 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** 无
> **目的:** 修复 `context/review-checklist-N.json` 在所有 56 章中静态不变——ai_blacklist 始终 14 项、hook_deliverables 始终 0——审查清单应随故事演进而更新。

---

## 1. 背景

### 1.1 发现（D21）

| 字段 | Ch1 | Ch20 | Ch40 | Ch55 |
|------|-----|------|------|------|
| transition_budget | 5 | 8 | 5 | 10 |
| ai_blacklist | 14 项 | 14 项 | 14 项 | 14 项 |
| hook_deliverables | 0 | 0 | 0 | 0 |

- `ai_blacklist` 始终 14 项——即使后期章节已有不同的 AI 疲劳词模式
- `hook_deliverables` 始终 0——即使计划中声明了要兑现的伏笔

### 1.2 影响

- 审查清单应随故事演进而收紧/调整约束
- 静态清单使后期章节不受益于前文积累的审查经验
- hook_deliverables=0 使起草 skill 缺少兑现提醒

---

## 2. 根因分析

Review checklist 由 `shenbi-context-composing` 生成。如果该步骤在 Ch1 后停止更新（或使用了缓存版本），所有后续章节将沿用第一版的清单。

---

## 3. 修复方案

### 3.1 强制每章重新生成 checklist

确保 `shenbi-context-composing` 每章重新运行（非缓存），且基于最新的 truth 文件状态生成清单。

### 3.2 Hook deliverables 自动填充

从 chapter plan 的 Section 7 hook ledger 中提取 `open/advance/resolve` 操作，自动填充到 checklist 的 `hook_deliverables` 字段。

---

## 4. 验证标准

1. 连续 3 章的 ai_blacklist 有变化（反映不同的 AI 风险模式）
2. hook_deliverables ≥ 计划中声明的 active hooks 数量
3. `just check` 全量通过
