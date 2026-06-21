# Bug-Hunt Report: shenbi-short-drafting

**Date**: 2026-06-12
**Skill**: `skills/shenbi-short-drafting/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all 3 planted defects detected

---

## Detection Summary

| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Sequential generation violation -- chapter 3 drafted at T+45min before chapter 2's truth files existed at T+52min; chapter 3 was generated without chapter 2's state information | error | `short/batch-summary.md`: generation timeline log; `truth/chapter-2-state.md` creation timestamp | YES |
| 2 | Cross-chapter consistency failure -- protagonist's cloak described as "crimson" (ch4: "深红色的斗篷") then "blue" (ch6: "蓝色斗篷") with no scene or transition explaining the change; position/prop inconsistency | error | `short/chapter-4.md` L7 vs `short/chapter-6.md` L7: cloak color descriptions | YES |
| 3 | Per-chapter audit rigor violation -- chapter 8 audit explicitly skipped with note "rushed schedule"; no audit performed | error | `short/batch-summary.md`: chapter 8 row in status table, per-chapter audit details, and overall statistics | YES |

---

## Detection 1: Sequential Generation Violation

### Skill Rule Applied

**Iron Rule 1**: 批量生成必须按顺序 -- 第1章先于第2章，禁止并行生成（依赖前一章状态）

**Generation Strategy rationale**: "第N章依赖第1-(N-1)章的状态。并行生成 = 状态假设不一致 = 角色 OOC。顺序生成 = 每章都有'前一章的实际输出'作为锚点。"

### Evidence

The generation timeline log in `batch-summary.md` shows:

```
| chapter-2.md 生成完成         | T+17min |
| chapter-3.md 生成开始         | T+45min |
| chapter-3.md 生成完成         | T+58min |
| truth/chapter-2-state.md 创建 | T+52min |
| truth/chapter-2-foreshadow.md 创建 | T+52min |
```

Chapter 3 generation started at T+45min and completed at T+58min. However, chapter 2's truth files (`chapter-2-state.md` and `chapter-2-foreshadow.md`) were not created until T+52min. Since chapter 3 was already being generated from T+45min, it could not have read chapter 2's state information.

### Detection Mechanism

The generation timeline log exposes the timestamp ordering:
1. Read the timeline log
2. Compare chapter N generation start time vs chapter (N-1) truth file creation time
3. If chapter N started before chapter (N-1) truth files exist => sequential dependency violated

### Severity

**error** -- Sequential generation is an iron rule because writing chapter 3 without chapter 2's actual state means character positions, time flow, information state, and relationships may be inconsistent. The entire chapter may need to be rewritten if chapter 2's state contradicts assumptions made during chapter 3's drafting.

---

## Detection 2: Cross-Chapter Consistency Failure

### Skill Rule Applied

**Iron Rule 4**: 跨章一致性必查 -- 修订后必须重读相邻 2 章确认一致性

**Cross-chapter consistency dimensions** (from skill):
- 角色位置: 与上章末位置是否一致
- 时间线: 与上章末时间是否衔接
- 信息状态: 主角已知信息是否一致
- 关系状态: 与上章末关系是否一致
- 风格: 与前 3 章风格指纹偏差

### Evidence

**Chapter 4** (`chapter-4.md` L7):
> 林烽没有去参加那场只有三个人的葬礼。他在仓库里画图。**身上那件深红色的斗篷**从渣堆那边走到仓库，肩头落了一层矿灰——斗篷是前两天用矿渣提炼的茜草根染的，颜色深得像凝固的血。

The cloak is explicitly described as "深红色的" (crimson), established as an existing possession dyed with madder root.

**Chapter 6** (`chapter-6.md` L7):
> 林烽在仓库里被爆炸声震醒。他翻身坐起来，**抓过那件从市场上换来的蓝色斗篷**披上——斗篷的布料粗糙，在肩上磨出一道浅痕。

The cloak is now described as "蓝色" (blue), and as "从市场上换来的" (traded from the market).

### Inconsistency Analysis

1. **Color**: "深红" (crimson) in ch4 vs "蓝" (blue) in ch6
2. **Origin**: "用矿渣提炼的茜草根染的" (dyed with madder root from slag) in ch4 vs "从市场上换来的" (traded from the market) in ch6
3. **No transition**: Chapters 4, 5, and 6 contain no scene where the protagonist acquires or swaps the cloak. Chapter 5 takes place in the same mining camp context.

This is both a prop inconsistency (cloak color) and a continuity violation (no acquisition event).

### Detection Mechanism

The cross-chapter consistency check requires reading adjacent chapters. The prop/position dimension specifically checks for object descriptions:
1. Read chapter 4: note cloak = crimson, acquired from personal dyeing
2. Read chapter 5: check for any cloak-related event (none found)
3. Read chapter 6: note cloak = blue, from market trade
4. Compare: color changed, origin changed, no transition scene exists

### Severity

**error** -- Prop inconsistencies break reader immersion. Readers who notice the crimson cloak in chapter 4 will be confused by the blue cloak in chapter 6 without explanation. This is a basic continuity error.

---

## Detection 3: Per-Chapter Audit Rigor Violation

### Skill Rule Applied

The skill's audit chain requirement: "每章必须通过的审计" including memo-compliance, anti-ai, character, motivation, pacing, and continuity.

**Metric requirement**: "每章的所有 blocking / critical / AI 痕迹 = 0 才能算通过"

### Evidence

1. **Status Table** (`batch-summary.md` L18):
   `| 8 | 3510 | skipped — rushed schedule | 0 | 未审计 |`

2. **Per-Chapter Audit Details** (`batch-summary.md`):
   `| 8 | — | — | — | 审计跳过（进度紧张，未执行） |`

3. **Overall Statistics** (`batch-summary.md`):
   `- 未审计章节数: 1（ch8 审计跳过）`

4. **Step 2 Record**:
   `**第8章审计因进度紧张跳过**`

### Violation Analysis

Chapter 8 was published without any audit. The skill requires 6-dimension audit for every chapter. "Rushed schedule" is not a valid reason to skip audit per the skill's anti-rationalization table:

| Excuse | Reality |
|--------|---------|
| "审计太慢，跳过" | 跳过审计 = 30 章隐患积累 = 整书返工 |

### Detection Mechanism

The batch summary table explicitly shows chapter 8 with "skipped — rushed schedule" and "0" revision rounds. The per-chapter audit details confirm no audit was performed. The overall statistics confirm one chapter was not audited.

### Severity

**error** -- Skipping audit on any chapter means no quality check was performed. The chapter could contain AI-ism, character OOC, plot hole, or pacing issues with no review. The skill's anti-rationalization explicitly warns against skipping audits.

---

## False Positive Analysis

No false positives:
- Chapters 1, 2, 4, 5, 7, 9-15 are correctly generated with proper audit records
- Revision counts for all audited chapters are within the <= 3 round limit
- Word counts for all chapters meet the floor requirement (ch8: 3510 >= 3000)
- Batch summary table column names match the exact required format for all properly audited chapters

## Conclusion

All three planted defects were successfully detected:

1. **Sequential violation**: Detected by reading the generation timeline log and comparing chapter 3's start time (T+45min) vs chapter 2's truth file creation time (T+52min), which violates Iron Rule 1.

2. **Cloak inconsistency**: Detected by cross-chapter prop comparison -- "深红斗篷" (ch4) vs "蓝色斗篷" (ch6) with no transition scene, which violates Iron Rule 4's cross-chapter consistency requirement.

3. **Skipped audit**: Detected by reading the batch summary status table and audit detail table -- chapter 8 explicitly marked "skipped -- rushed schedule", violating the per-chapter audit requirement.
