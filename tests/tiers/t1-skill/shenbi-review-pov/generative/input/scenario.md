# Generative Test: shenbi-review-pov

## Skill Under Test
`skills/shenbi-review-pov/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 13 at `drafts/chapter-13.md`. The chapter is written in limited POV. Chapter summaries at `truth/chapter_summaries.md` record all events and who was present.

## Agent Task
Run shenbi-review-pov audit on chapter 13. Produce a complete POV audit report including:
1. POV type identification and consistency
2. Knowledge audit — every piece of character knowledge verified against acquisition channel
3. Information leakage detection
4. Head-hopping detection (unauthorized POV switches)

## Seed Input
Drafted chapter from `drafts/chapter-13.md`, chapter summaries from `truth/chapter_summaries.md`
