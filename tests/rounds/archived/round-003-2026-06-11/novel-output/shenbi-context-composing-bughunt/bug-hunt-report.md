# Bug-Hunt Report: shenbi-context-composing

**Date**: 2026-06-12
**Skill**: `skills/shenbi-context-composing/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- planted defect detected

---

## Detection Summary

| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | P1 item (chapter plan memo) was trimmed -- "章尾必须发生的改变" section missing from assembled context -- while lower-priority P2 recent summaries and P5 world rules are included in full, violating strict priority ordering (P1 > P2 > P5) | error | `context/chapter-2-context.md`: P1 section (L49), P2 section (L53-89), P5 section (L119-175) | YES |

## Detection Analysis

### Skill Rule Applied

**Iron Rule 1**: 优先级严格递减 -- P1 不可省略，P7 最先被裁剪。

**Priority Order** (from skill):
- P1 (must): 不裁剪
- P2 (must): 不裁剪
- P3-P4 (need): 有限裁剪
- P5-P7 (nice): 可裁剪

### Evidence

1. **P1 Trimmed** (`context/chapter-2-context.md` L49): The P1 section ends with an explicit note: "原章节计划中包含'章尾必须发生的改变'部分（约800字），因上下文组装长度限制已裁剪。" This confirms a P1 section was deliberately removed.

2. **P2 Complete** (L53-89): The P2 section contains full chapter summary for Chapter 1 including: key events (8 enumerated items), appearing characters, location changes, state changes, foreshadowing activity, and emotional trajectory. No trimming notes present.

3. **P5 Complete** (L119-175): The P5 section includes all 5 allowed world rules, each with detailed descriptions covering: rule text, data source, and chapter-2 implications. No trimming notes present.

### Priority Violation Analysis

The skill's priority table explicitly states:
- P1: "不裁剪" (must not be trimmed)
- P2: "不裁剪" (must not be trimmed)
- P5: Can be limited to 5 rules maximum (already at max)

The assembled context shows:
- P1 (priority 1): PARTIALLY TRIMMED -- "章尾必须发生的改变" section removed
- P2 (priority 2): FULL -- no trimming
- P5 (priority 5): FULL -- all 5 rules included

This violates Iron Rule 1 because: P1 was trimmed while lower-priority items P2 and P5 were NOT trimmed. The strict decreasing priority means P1 should never be trimmed before P2 or P5. If context length required trimming, P5 (world rules) should have been trimmed first, then P3/P4, before any P1 content is considered for removal.

### Detection Mechanism

The skill's context assembly process requires checking priority order. When reviewing the assembled context:
1. Check P1 section -- note the explicit "已裁剪" annotation
2. Check P2 section -- verify it is complete
3. Check P5 section -- verify it is complete
4. Compare: P1 trimmed, P2+P5 full => priority violation

The detection is straightforward because the P1 section contains a self-documenting note about the trim.

### Severity Classification

**error** -- P1 (chapter plan memo) is the highest-priority context item. Trimming it while keeping lower-priority items (P2 summaries, P5 world rules) intact means the drafting agent lacks critical information about what must change by chapter end. This could lead to chapters that fail to satisfy the plan's structural requirements.

## False Positive Analysis

No false positives. All other sections are correctly assembled:
- P3 contains maximum 3 hooks with urgency calculations and data sources
- P4 correctly notes no drift guidance exists yet (chapter 2, first chapter after ch1)
- P6 includes only characters appearing in chapter 2
- P7 presents style observations from chapter 1
- Near-chapter endings analysis reads actual chapter files
- Hook debt briefing sources from pending_hooks.md

## Conclusion

The planted defect (P1 trimmed while P2 and P5 remain full) was successfully detected by applying Iron Rule 1 of shenbi-context-composing. Detection relied on the explicit trim annotation in P1 and the complete P2/P5 sections, creating a clear priority inversion.
