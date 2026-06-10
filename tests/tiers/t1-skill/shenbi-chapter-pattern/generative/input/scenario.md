# Generative Test: shenbi-chapter-pattern

## Skill Under Test
`skills/shenbi-chapter-pattern/SKILL.md`

## Test Setup
A novel project has 12 completed chapters. Chapter drafts exist at `drafts/chapter-1.md` through `drafts/chapter-12.md`. The SKILL.md defines 13 pattern types (e.g., action, dialogue-heavy, revelation, romance, mystery, etc.) with hard limits on consecutive patterns and minimum distribution requirements.

## Agent Task
Run shenbi-chapter-pattern to analyze the pattern distribution across chapters 1-12. The agent must:
1. Classify each chapter into ≥1 of the 13 defined patterns per SKILL.md definitions
2. Enforce hard limits on consecutive patterns (no more than 3 consecutive same-pattern chapters)
3. Calculate Shannon entropy for the pattern distribution
4. Provide a next-chapter recommendation naming specific primary/secondary patterns and patterns to avoid
5. Verify minimum distinct patterns in rolling windows

## Seed Input
Chapter drafts from `drafts/chapter-1.md` through `drafts/chapter-12.md`, pattern definitions from `skills/shenbi-chapter-pattern/SKILL.md`
