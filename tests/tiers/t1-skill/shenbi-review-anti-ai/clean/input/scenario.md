# Clean Test: shenbi-review-anti-ai

## Skill Under Test
`skills/shenbi-review-anti-ai/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 6 at `drafts/chapter-6.md`. The SKILL.md defines a checklist of 10 deterministic anti-AI pattern checks. All 10 checks are executed and all return PASS. No AI-pattern violations detected.

## Scenario
No defects. All 10 anti-AI checks are executed and pass. The chapter text is free of AI-typical patterns.

## Agent Task
Run shenbi-review-anti-ai audit on chapter 6. Expected: report zero issues, all 10 checks PASS.
