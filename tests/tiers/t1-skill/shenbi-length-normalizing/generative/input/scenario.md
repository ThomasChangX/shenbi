# Generative Test: shenbi-length-normalizing

## Skill Under Test
`skills/shenbi-length-normalizing/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `drafts/chapter-5.md` that is 5600 words. The target chapter length is 4000 words (the chapter is 40% over target).

## Agent Task
Run shenbi-length-normalizing on the over-length chapter. The agent must:
1. Compress the chapter toward the 4000-word target without adding or removing narrative events
2. Reject if compression would exceed the 25% floor gate
3. Keep final word count within target +-15% (soft), +-30% (hard)
4. Preserve voice; do not introduce AI-typical phrasing during compression
5. Ensure compression deepens content rather than shallow cutting
6. Complete a consistency checklist confirming no narrative changes

## Seed Input
Drafted chapter from `drafts/chapter-5.md` (5600 words, target 4000 words)
