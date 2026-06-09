---
name: shenbi-review-anti-ai
description: Use when a finished chapter needs an AI-pattern audit against fatigue words, structural tells, and genre-config prohibitions
---

# Anti-AI 审计

这是默认激活的审计技能（每章必查）。

## 流程

```dot
digraph review_anti_ai {
    "Read chapter content" -> "Read genre-config.json (fatigueWords + prohibitions)";
    "Read genre-config.json" -> "Run deterministic checks (checklist.md)";
    "Run deterministic checks" -> "Compile results";
    "Compile results" -> "Passed?";
    "Passed?" -> "Report PASS" [label="yes"];
    "Passed?" -> "Report issues with severity" [label="no"];
    "Report issues with severity" -> "Suggest specific fixes";
}
```

## 数据契约

- **Reads:** `chapters/chapter-N.md`, `genre-config.json`
- **Writes:** report only
- **Updates:** none

## 铁律

1. **不信任"看起来还行"** — 每条检查必须逐一执行，不允许跳步
2. **先确定性后判断** — 确定性检查（零 LLM 成本）先跑，发现问题就不需要继续
3. **error 级别 = 必须修复** — error 级别问题不通过修订不能放过
4. **warning 级别 = 建议修复** — 3+ warning 也需要修订

## 检查执行

完整检查清单在 `checklist.md`。执行顺序：

1. 段落等长检测 (CV)
2. "不是…而是…"句式
3. 破折号
4. 转折词密度
5. AI 标记词
6. 疲劳词（从 genre-config）
7. 元叙事/编剧旁白
8. 分析报告术语
9. 集体反应套话
10. 禁忌词（从 genre-config）

## 输出格式

```markdown
## Anti-AI 审计报告

**章节**: 第N章
**字数**: XXXX
**结果**: 通过 / 有瑕疵 / 不通过

### 检查结果

| # | 检查项 | 结果 | 详情 |
|---|--------|------|------|
| 1 | 段落等长 | PASS | CV=0.32 |
| 2 | 不是…而是… | PASS | 未检测到 |
| 3 | 破折号 | ERROR | 第3段含"——" |
| ... | | | |

### 评分: X/10 通过

### 建议修复
- [ERROR] 第3段破折号：将"他深吸一口气——这不可能" → "他深吸一口气。这不可能。"
```

## Anti-Rationalization

| Excuse | Reality |
|--------|---------|
| "AI味读者看不出来" | 平台 AIGC 检测算法看得很清楚，降权直接影响收入 |
| "只有1个error，可以放过" | 1个error = 1个平台检测标记点 |
| "检查太多太慢了" | 确定性检查10秒完成，修30章500个error要3天 |
