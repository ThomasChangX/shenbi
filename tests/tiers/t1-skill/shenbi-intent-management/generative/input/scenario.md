# Generative Test: shenbi-intent-management

## Skill Under Test
`skills/shenbi-intent-management/SKILL.md`

## Test Setup
A novel project is between chapters. The human author has just provided new creative direction via a conversation:
- "I want the next arc to focus on the political intrigue in the capital. The main character should be forced to navigate court politics for the first time."
- "Also, the subplot with the missing artifact needs to reach a turning point soon."

Drift guidance at `guidance/drift-chapter-16.md` contains 4 warning-level items. The existing `truth/author_intent.md` contains the original creative vision.

## Agent Task
Run shenbi-intent-management to update the project's current focus. The agent must:
1. Organize the human's new creative input into the current focus
2. Merge all drift guidance items into the current focus
3. Assign P0/P1/P2 priorities per definitions
4. Never add any AI-generated creative suggestions
5. Ensure timestamp is after the most recent audit/drift
6. Follow YAML frontmatter schema for both files

## Seed Input
Human input from conversation, drift guidance from `guidance/drift-chapter-16.md`, existing intent from `truth/author_intent.md`
