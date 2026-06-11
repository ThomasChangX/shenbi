# Generative Test: shenbi-chapter-revision

## Skill Under Test
`skills/shenbi-chapter-revision/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `drafts/chapter-15.md`. An audit has been completed and produced three findings:
- Finding B1 (error): A character references an event that has not happened yet (chapter 15 refers to the battle of Northgate, but that battle occurs in chapter 18).
- Finding B2 (warning): The character Wei Jun's eye color is described as brown, but `truth/character_profiles/wei-jun.md` says green.
- Finding B3 (warning): A foreshadowing callback references item "shadow-mark" but `truth/foreshadowing_pool.md` lists it as "shadow-mark of the ancients".

Truth files are at `truth/`, the original draft is at `drafts/chapter-15.md`, and the audit report is at `audits/chapter-15-audit.md`.

## Agent Task
Run shenbi-chapter-revision to fix all three audit findings in the chapter draft. The agent must:
1. Fix finding B1 by removing or reworking the anachronistic reference to the battle of Northgate
2. Fix finding B2 by correcting Wei Jun's eye color to green
3. Fix finding B3 by using the correct foreshadowing item name "shadow-mark of the ancients"
4. Keep all changes within ±15% of original length
5. Introduce no new plot elements, characters, or narrative threads
6. Preserve all plot, character, and foreshadowing content unrelated to the findings

## Seed Input
Original draft from `drafts/chapter-15.md`, audit report from `audits/chapter-15-audit.md`, character profiles from `truth/character_profiles/`, foreshadowing pool from `truth/foreshadowing_pool.md`
