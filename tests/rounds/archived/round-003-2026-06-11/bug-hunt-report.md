# Bug-Hunt Report — Round 003 (2026-06-11)

**Date**: 2026-06-12
**Executor**: Claude (automated detection)
**Base R3**: `tests/rounds/round-003-2026-06-11/novel-output/`
**Bughunt copies**: `.../novel-output/<skill>-bughunt/`

---

## Summary

| # | Skill | Defect Type | Severity | Detected | Detection Method |
|---|-------|------------|----------|----------|-----------------|
| 1 | shenbi-faction-builder | Missing internal factional split | error | YES | Section content scan |
| 2 | shenbi-location-builder | Contradictory travel times | error | YES | Cross-file distance comparison |
| 3 | shenbi-pacing-design | Missing aftermath beat | error | YES | Table column completeness check |
| 4 | shenbi-plot-thread-weaver | Blank chapter (zero threads) | error | YES | Chapter-to-thread mapping scan |

**Result**: 4/4 defects detected. All severities match expected.

---

## 1. shenbi-faction-builder

### Defect Location
`world/factions/meidelan-maiban.md` — `### 内部矛盾` section (lines 36-46)

### Defect Description
The Meidelan comprador bourgeoisie faction (`梅德兰买办资产阶级`) is described as a completely unified entity with zero internal factional splits. The `### 内部矛盾` section explicitly states:

- "梅德兰买办资产阶级是一个高度统一的整体" (a highly unified whole)
- "三个分会之间不存在实质性的利益分歧或路线冲突" (no substantive interest differences or route conflicts)
- "当前激化程度：无" (current tension level: none)
- "潜在引爆点：无" (potential trigger points: none)

### Detection Analysis
**Rule violated**: Every faction must have at least one internal factional split (internal contradiction). The faction-builder specification requires each faction to document internal contradictions with specific tension types (路线之争/资源之争/派系之争/理念之争/继承之争).

**Detection method**: Scan the `### 内部矛盾` section of each faction file. If the section describes the faction as fully unified with no dissenting voices, zero tension level, and zero trigger points, flag as error.

**Original R3**: The `meidelan-maiban.md` file originally contained 3 internal tensions (主线张力, 第二张力, 第三张力) with specific characters, escalation levels, and trigger points.

**Detection result**: **DETECTED** — The internal contradictions section has been replaced with a monolithic unity narrative. The faction has zero documented internal splits, violating the mandatory internal conflict requirement.

---

## 2. shenbi-location-builder

### Defect Location
- `world/locations/铁脊城.md` — line 18: **行程时间**: 乘马约三日 (three days by horse)
- `world/locations/锻钢城.md` — line 18: **行程时间**: 快马半日可达 (half-day by fast horse)

### Defect Description
Both locations describe the same route (铁脊城 to 锻钢城, 40 km) but with contradictory travel times. 铁脊城 claims the journey takes "three days by horse" while 锻钢城 claims it is "a half-day ride by fast horse."

### Detection Analysis
**Rule violated**: Spatial consistency — the same route must have consistent travel time regardless of which direction it is described from. The distance between two fixed points is invariant.

**Detection method**: Cross-reference the `**行程时间**` fields between location pairs that reference each other as `最近地标`. For each pair A-B where A has B as nearest landmark and B has A as nearest landmark, verify that travel times are consistent (same order of magnitude).

**Comparison**:
- 铁脊城 → 锻钢城: "乘马约三日" (3 days)
- 锻钢城 → 铁脊城: "快马半日可达" (0.5 day)
- Distance: 40 km (consistent in both files)
- **Ratio**: 6:1 — direct contradiction

**Detection result**: **DETECTED** — Travel time for the same 40km route differs by a factor of 6x between the two location files. This is a spatial consistency violation.

---

## 3. shenbi-pacing-design

### Defect Location
`story/pacing.md` — 卷节奏分配 table, Volume 3 row (line 184)

### Defect Description
Volume 3 (chapters 31-50) has only 3 of the 4 required beats:
- 铺垫 (buildup): chapters 31-37, 35.0%
- 上升 (escalation): chapters 38-45, 40.0%
- 爆发 (explosion): chapters 46-50, 25.0%
- 余波 (aftermath): **MISSING** — column is empty ("—")

The deviation note reads: "余波缺失——第3卷仅有铺垫/升级/爆发三拍，缺少余波"

### Detection Analysis
**Rule violated**: The 四拍循环 rule states: "每卷必须包含铺垫/升级/爆发/余波四拍，缺一拍即不合格" (Every volume must contain all four beats — missing one is an automatic fail).

**Detection method**: Parse the `卷节奏分配` table. For each volume row, verify that all 4 beat columns (铺垫段/上升段/爆发段/余波段) contain non-empty chapter ranges. Empty or dash-only cells indicate a missing beat.

**Additional findings**:
- The 自动化检查清单 line 239 incorrectly claims: "[x] 每卷四拍完整（铺垫/升级/爆发/余波），六卷共 24 拍全部填写" — this is a false positive in the self-check. Volume 3 only has 3 beats (23 total, not 24).
- The 逐卷校验 for Volume 3 shows: "35.0 + 40.0 + 25.0 = 100.0%" — only 3 terms, confirming the missing beat.
- No cross-volume compensation plan is documented for the missing V3 aftermath.

**Detection result**: **DETECTED** — Volume 3 is missing the aftermath beat. Only 3 of 4 required beats are present. The self-check checklist falsely claims all 24 beats are complete.

---

## 4. shenbi-plot-thread-weaver

### Defect Location
`outline/thread_map.md` — 章节线索推进表, Chapter 15 row (line 200)

### Defect Description
Chapter 15 has no thread assignment — all columns are empty:
```
| 15 | — | — | — | — |
```
No A-line (主推), no B/C-lines (副推), no crossing point (交叉点), no notes (备注). This is a "blank chapter" that advances zero threads.

### Detection Analysis
**Rule violated**: "每章有 >= 1 条线索推进" (Every chapter must advance at least 1 thread). The no-blank-chapters rule is fundamental to plot thread weaving.

**Detection method**: Scan the `章节线索推进表` rows. For each chapter, verify that the 主推 column is non-empty. An empty or dash-only 主推 column indicates a blank chapter.

**Additional findings**:
- The 空白检测 section (line 370) says "空白章节: 0" and "全部100章均有至少1条主推线索推进。空白章节数 = 0。合格。" — This self-check is a false negative; it incorrectly reports zero blank chapters when Chapter 15 is in fact blank.
- The 约束检查表 for Volume 1 (chapters 1-15) would show all threads (A1, A2, B1, B3, B4, B6) with increased gaps due to Chapter 15 contributing nothing. Specifically:
  - A1 max_gap would increase from 0 to 1 (gap between ch14 and ch16)
  - B4 (last seen ch14) would increase its max_gap from 4 to 5+ (exceeding P1 limit of 4)

**Detection result**: **DETECTED** — Chapter 15 is a blank chapter with zero thread advancement. The self-check's claim of zero blank chapters is a false negative. Additionally, this creates thread gap violations for B4 (exceeds max_gap=4).

---

## Detection Methodology Notes

All 4 defects were detected through systematic scanning of the output files against the skill specification rules:

1. **Faction builder**: Section content analysis — check that each faction's `内部矛盾` section documents at least 1 tension with non-zero escalation level and non-empty trigger points.
2. **Location builder**: Cross-file consistency check — for each location pair that mutually reference each other, compare travel times for the same route.
3. **Pacing design**: Table column completeness — verify all 4 beat columns per volume are non-empty; cross-validate with the逐卷校验 sum-of-terms count.
4. **Plot thread weaver**: Chapter coverage scan — verify every chapter in the章节线索推进表 has a non-empty 主推 column; cross-validate against the self-reported blank chapter count.

---

## File Manifest

### Bughunt copies (with injected defects):
- `novel-output/shenbi-faction-builder-bughunt/world/` — all 7 faction files + relations + aggregate
- `novel-output/shenbi-location-builder-bughunt/world/` — all 7 location files + aggregate
- `novel-output/shenbi-pacing-design-bughunt/story/` — pacing.md + scene-types.md
- `novel-output/shenbi-plot-thread-weaver-bughunt/outline/` — thread_map.md

### Pristine R3 (unmodified):
- `novel-output/shenbi-faction-builder/world/`
- `novel-output/shenbi-location-builder/world/`
- `novel-output/shenbi-pacing-design/story/`
- `novel-output/shenbi-plot-thread-weaver/outline/`
