# Bug-Hunt Report: shenbi-power-system

**Date**: 2026-06-12
**Skill**: `skills/shenbi-power-system/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

---

## Detection Summary

| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Level 3→4 (凝核→化形) advancement rules section completely missing | error | `world/power_system.md` L70-72 (between) | YES |
| 2 | Cost table row for 3→4 has all five dimensions marked as "（缺失）" | error | `world/power_system.md` L202 | YES |
| 3 | Level 4 化形阶 omitted from the base recovery rate sequence | error | `world/power_system.md` L214 | YES |

## Detection 1: Missing Advancement Rules for Level 3→4

### Defect Location
`world/power_system.md` -- the section between L70 and L72

### Defect Description
The advancement rules section for Level 3 (凝核) → Level 4 (化形) has been entirely deleted. The file proceeds directly from `### 等级 2（通脉）→ 等级 3（凝核）` (L63-L70) to `### 等级 4（化形）→ 等级 5（知理）` (L72-L79). Every other level transition (1→2, 2→3, 4→5, 5→6, 6→7, 7→8, 8→9, 9→10) has a fully populated advancement rules subsection with trigger conditions, duration, failure cost, resource requirements, and probability. Level 3→4 is the sole exception.

### Skill Rule Applied
**铁律一：能力必有代价** -- "任何力量使用都必须有可见的代价（资源/时间/身体/道德/社交）；无代价的力量 = 神力"

**Evidence**: Lines 63-70 contain the 2→3 advancement rules. Lines 72-79 begin the 4→5 advancement rules. The expected `### 等级 3（凝核）→ 等级 4（化形）` heading and its content are absent.

### False Positive Check
Confirmed no clean content was incorrectly flagged. Checked: all other 8 level transitions (1→2, 2→3, 4→5, 5→6, 6→7, 7→8, 8→9, 9→10) have complete advancement rules with all five required dimensions present. Only 3→4 is missing.

---

## Detection 2: Empty Cost Table Row for 3→4

### Defect Location
`world/power_system.md` L202

### Defect Description
In the "各阶升级总代价表" (advancement cost summary table), the row for 3→4 has all five cost dimensions replaced with "（缺失）":

```
| 3→4 | （缺失） | （缺失） | （缺失） | （缺失） | （缺失） |
```

All five cost dimensions (资源代价, 时间代价, 身体代价, 道德代价, 社交代价) are marked as missing. Every other row in the table (1→2 through 9→10) contains substantive cost data.

### Skill Rule Applied
**铁律一：能力必有代价** -- "任何力量使用都必须有可见的代价（资源/时间/身体/道德/社交）；无代价的力量 = 神力"

**Evidence**: `world/power_system.md` L202: `| 3→4 | （缺失） | （缺失） | （缺失） | （缺失） | （缺失） |`

### False Positive Check
Confirmed no clean content was incorrectly flagged. Checked: all other 9 rows in the cost table (1→2, 2→3, 4→5, 5→6, 6→7, 7→8, 8→9, 9→10) are fully populated with non-"缺失" values. Only the 3→4 row is empty.

---

## Detection 3: Level 4 Omitted from Recovery Rate Sequence

### Defect Location
`world/power_system.md` L214

### Defect Description
In the "使用代价" section describing base recovery rates, the sequence of levels jumps from Level 3 (凝核阶) directly to Level 5 (知理阶), omitting Level 4 (化形阶):

> "恢复速率约为凝核阶每小时恢复10%总量，知理阶25%，破界阶40%，融道阶60%，开位阶80%，造律阶理论上全时满恢复"

The sequence lists Levels 3, 5, 6, 7, 8, 9 -- Level 4 化形阶 is the only tier excluded from the recovery rate enumeration.

### Skill Rule Applied
**铁律五：能力有边界** -- "每个等级必须明确'能做什么/不能做什么'，模糊的能力边界 = 后期崩盘"

**Evidence**: `world/power_system.md` L214: "恢复速率约为凝核阶每小时恢复10%总量，知理阶25%，破界阶40%，融道阶60%，开位阶80%，造律阶理论上全时满恢复"

### False Positive Check
Confirmed no clean content was incorrectly flagged. Checked: Levels 1-3 and 5-9 all have ability boundaries documented in the "能力边界" section. Level 4 has ability boundaries (L150-154) but its cost dimension (recovery rate) is incomplete. The recovery rate list enumerates 6 out of 7 applicable levels, with only 化形阶 missing.
