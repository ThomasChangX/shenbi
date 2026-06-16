# Bug-Hunt Report: shenbi-short-outline

**Date**: 2026-06-12
**Skill**: `skills/shenbi-short-outline/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

---

## Detection Summary

| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Dead chapter -- Chapter 10 has zero thread advancement (pure transition) | error | `outline/short_story_map.md` L50-51 | YES |
| 2 | Act proportioning violation -- 40/30/30 split instead of required 20/60/20 | error | `outline/short_story_map.md` L21-32, L79 | YES |
| 3 | 3-step flow enforcement violation -- review step (复核) skipped | error | `outline/short_story_map.md` L82-85 | YES |

## Detection 1: Dead Chapter (Chapter 10)

### Defect Location
`outline/short_story_map.md` -- L50-51

### Defect Description
Chapter 10 is a pure transition chapter with zero thread advancement. Its task is described as geographic movement only, with推进线索 marked as "--" (no thread), and the备注 explicitly states the chapter has no conflict and no plot advancement:

L50-51:
```
| 10 | transition — 主角前往北部城市，沿途经历天气变化和地理景观转换 | — | 过渡章：人物地理位置移动，无冲突，无剧情推进 |
```

The推进线索 column reads "—" indicating that neither the main plot line, the subplot line, nor the emotional arc line is advanced in this chapter. The备注 column confirms "过渡章" (transition chapter) with "无冲突，无剧情推进" (no conflict, no plot advancement).

### Skill Rule Applied
**铁律四：每章有任务** -- "短篇的每章都必须推进至少 1 条线索，禁止'过渡章'"

**Evidence**: `outline/short_story_map.md` L50-51: `| 10 | transition — 主角前往北部城市，沿途经历天气变化和地理景观转换 | — | 过渡章：人物地理位置移动，无冲突，无剧情推进 |`

---

## Detection 2: Act Proportioning Violation

### Defect Location
`outline/short_story_map.md` -- L21-23, L31-32, L79

### Defect Description
The 15-chapter outline uses an act split of 40/30/30 instead of the required 20/60/20:

- L21-23: Act 1 (开端) spans chapters 1-8 (8 chapters = 40% of the intended 20-chapter total, but the declared total is effectively 20 chapters per L79)
- L31-32: Act 3 (收官) spans chapters 15-20 (6 chapters = 30%)

The三幕结构 section defines each act with chapter ranges that reflect the wrong proportions. Act 1 is too long (40% vs required 20%), Act 2 is too short at chapters 9-14 (30% vs required 60%), and Act 3 is too long (30% vs required 20%).

L79 explicitly confirms the wrong split:
> "三幕比例: 开端 40% (ch1-8) / 对抗 30% (ch9-14) / 收官 30% (ch15-20)"

The skill's三幕结构 specification defines the required proportions as 开端 20% / 对抗 60% / 收官 20%.

### Skill Rule Applied
**铁律五：故事弧清晰** -- "起承转合必须在 30 章内完成"

The act proportioning violation compromises the story arc's structural integrity: Act 2 (对抗/confrontation), which carries the main body of conflict development, is compressed to only 30% of the narrative space (instead of the required 60%). This leaves insufficient room for conflict escalation, subplot development, and turning points -- compromising the 起承转合 structure that 铁律五 requires to be clear.

**Evidence**: `outline/short_story_map.md` L79: `三幕比例: 开端 40% (ch1-8) / 对抗 30% (ch9-14) / 收官 30% (ch15-20)`

---

## Detection 3: Skipped Review Step

### Defect Location
`outline/short_story_map.md` -- L82-85

### Defect Description
The 3-step process required by the skill (生成 → 复核 → 修订) has been reduced to 2 steps (生成 → 修订), with the review step (复核) entirely skipped:

L82: "两步流程记录" (declares 2-step flow instead of 3-step)

L84-85:
```
- **Step 1 (生成)**: 2026-06-11 — 完成。基于 novel.json 和 truth/author_intent.md 生成 15 章完整压缩大纲...
- **Step 2 (修订)**: 2026-06-11 — 完成（0 轮修订）。生成后直接修订，无复核步骤。
```

The流程步骤 header also reflects this: "生成 ✓ → 修订 ✓" instead of "生成 ✓ → 复核 ✓ → 修订 ✓". Step 2 is labeled as "修订" when it should be "复核" -- the review step was entirely bypassed.

### Skill Rule Applied
**铁律一：三步流程不可跳** -- "生成 → 复核 → 修订，缺一步 = 质量不稳"

**Evidence**: `outline/short_story_map.md` L82: "两步流程记录". L85: "**Step 2 (修订)**: 2026-06-11 -- 完成（0 轮修订）。生成后直接修订，无复核步骤。"

### False Positive Check
Confirmed no clean content was incorrectly flagged. Checked: Chapters 1-9 and 11-15 all have substantive推进线索 values (主线, 主线+副线+情感, etc.) -- only Chapter 10 is a dead chapter. The story arc description (L11: "现代躺平大学生穿越至被法西斯侵略的魔法殖民地...") is clear and proper. The 5 turning points are reasonably distributed. Chapter count of 15 (declared) falls within the < 30 limit. The主线索/副线索/情感线 configuration (1+1+1) matches the required 3-thread model. Only the three defects above violate the skill's rules.
