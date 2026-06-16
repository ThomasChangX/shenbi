# Bug-Hunt Report: shenbi-plot-thread-weaver
**Date**: 2026-06-12
**Skill**: `skills/shenbi-plot-thread-weaver/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

## Detection Summary
| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Chapter 15 advances zero threads -- no main thread, no secondary thread, no crossing point; blank chapter violates no-blank-chapters requirement | error | `outline/thread_map.md` L200 | YES |

## Detection 1: Blank Chapter 15 -- Zero Thread Advancement
### Defect Location
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-plot-thread-weaver-bughunt/outline/thread_map.md` -- L200

### Defect Description
In the chapter-by-chapter thread advancement table, Chapter 15 at L200 has no thread assignment: `| 15 | --- | --- | --- | --- |`. The row contains only dashes in all four data columns (main thread, secondary thread, crossing point, notes). This means Chapter 15 advances exactly zero plot threads -- no A-line, no B-line, no C-line. Every other chapter in the 100-chapter map has at least one main thread and often multiple secondary threads. For example, the adjacent Chapter 14 at L199 has B1 as main thread, and A1/A2/B4 as secondary threads. Chapter 16 at L201 has A1 as main thread and A2/B1/B3/B6 as secondary threads. Chapter 15 is the sole blank chapter in the entire 100-chapter thread map.

The blank detection section at L370-L373 confirms this: "空白章节: 1" with the note "第15章无任何主推线索推进。空白章节数 = 1。不合格。" (Chapter 15 has zero main thread advancement. Blank chapter count = 1. Unqualified.)

### Skill Rule Applied
**铁律一: 每章至少推进1条线索**: "空白章 = 浪费章节；多线并进章必须有明确主次"

**Evidence**:
- `thread_map.md` L200: `| 15 | --- | --- | --- | --- |` -- all four data columns contain only dashes, indicating zero thread contact
- `thread_map.md` L184-L201: Chapter-by-chapter thread advancement table rows for chapters 1-15 -- Chapter 14 (L199) has B1/A1/A2/B4; Chapter 16 (L201) has A1/A2/B1/B3/B6; only Chapter 15 has all dashes
- `thread_map.md` L370-L373: "空白检测" section explicitly identifies Chapter 15 as a blank chapter with count = 1
- SKILL.md L35: "1. **每章至少推进 1 条线索** -- 空白章 = 浪费章节；多线并进章必须有明确主次"
- SKILL.md L168-L169: "可自动检查的计数规则 -- 空白章节数 = 0 -- > 0（任意一章无主推）"
- SKILL.md L228: Anti-Rationalization: `"空白章是给读者喘息"` -> Reality: `"喘息 = 信息密度降低 != 线索零推进；可让 C 线短小推进"`

### False Positive Check
Confirmed no clean content incorrectly flagged. Checked: All other 99 chapters (1-14, 16-100) have at least one main thread. Chapter constraints for P0 max_gap and P1 max_gap are correctly computed and correctly marked as N (no violation) in the constraint check tables at L291-L364. The cross-volume transition at L382 (`卷1->卷2: A1, A2, B1, B3, B4, B6 -- 第15章纸条地址 -> 第16章林烽按地址找到联络点`) suggests Chapter 15 should have thread content but the thread advancement table omits it. The defect is isolated to Chapter 15's empty row.
