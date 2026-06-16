# Bug-Hunt Report: shenbi-chapter-revision

## Defect Detection Results

### Defect 1: Scope violation — new subplot character introduced during revision
- **Detected**: yes
- **Location**: `chapter-1-revised.md` — appended section containing "穿深色斗篷的身影...银色的眼睛"
- **Violated Rule**: SKILL.md scope rule — "修订只修复审计发现的问题，不引入新角色/新情节"
- **Evidence**: The revised chapter contains a new character ("穿深色斗篷的身影，银色的眼睛") that does not correspond to any audit finding. This is a scope violation — revision must only address identified issues.
- **Severity**: error

### Defect 2: Length constraint violation — 21% increase exceeds ±15% limit
- **Detected**: yes
- **Location**: `chapter-1-revised.md` — total word count ~5100 vs original ~4200
- **Violated Rule**: SKILL.md length constraint — "修订后字数变化不超过原始±15%"
- **Evidence**: Revision increases word count by approximately 900 words (21%), exceeding the ±15% (630 words) limit. The appended content significantly inflates the chapter.
- **Severity**: error

## Summary
- Defects planted: 2, Detected: 2/2, False positives: 0
