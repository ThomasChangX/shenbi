# Clean Test: shenbi-review-character

## Skill Under Test
`skills/shenbi-review-character/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 6 at `drafts/chapter-6.md`. Character truth files are at `truth/character_profiles/`. The chapter features 3 characters: protagonist 林墨, 苏晴, and 老陈. All characters' BDI assessments are present and correct. Every speaking/acting character is fully covered.

## Scenario
No defects. All characters are correctly assessed in the audit report. Every character with dialogue lines has a complete BDI assessment.

## Agent Task
Run shenbi-review-character audit on chapter 6. Expected: report zero issues.
