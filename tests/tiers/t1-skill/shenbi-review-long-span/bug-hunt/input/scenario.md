# Bug-Hunt Test: shenbi-review-long-span

## Skill Under Test
`skills/shenbi-review-long-span/SKILL.md`

## Test Setup
A novel project exists with 10 drafted chapters. The long-span audit covers the last 5 chapters (chapters 6-10). Across these chapters, the 6-char phrase "他不禁想起了那" appears repeatedly:
- Chapter 6, paragraph 3: "他不禁想起了那"
- Chapter 7, paragraph 11: "他不禁想起了那"
- Chapter 8, paragraph 5: "他不禁想起了那"
- Chapter 9, paragraph 2: "他不禁想起了那"
- Chapter 10, paragraph 8: "他不禁想起了那"

This 6-char n-gram appears 5+ times across the last 5 chapters, which exceeds the repetition threshold defined in SKILL.md.

## Scenario
The agent runs a long-span audit on the last 5 chapters. The audit report at `audit/long-span-review.md` does not flag the repeated 6-char phrase "他不禁想起了那" that appears 5+ times across chapters 6-10. The n-gram repetition is not detected despite exceeding the threshold.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Chapters 6-10 | Repeated 6-char n-gram "他不禁想起了那" not flagged — appears 5+ times across last 5 chapters (ch6p3, ch7p11, ch8p5, ch9p2, ch10p8), exceeding repetition threshold per SKILL.md formula | error |

## Agent Task
Run shenbi-review-long-span audit on the last 5 chapters. Find the planted defect where a repeated 6-char phrase is not flagged.
