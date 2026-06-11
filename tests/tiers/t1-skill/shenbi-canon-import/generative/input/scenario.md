# Generative Test: shenbi-canon-import

## Skill Under Test
`skills/shenbi-canon-import/SKILL.md`

## Test Setup
A fanfic project is being set up. The original work is a 50-chapter web novel. The target fanfic mode is "CP" (character pairing). No canon files have been generated yet.

## Agent Task
Run shenbi-canon-import on the original work in CP mode. The agent must:
1. Extract all 5 sections: world, character, event, relationship, timeline
2. Apply CP mode filtering rules consistently across all sections
3. Cite original work (chapter/paragraph) for every canon entry
4. Declare all deviations from original in a deviations list
5. Ensure zero silent mixing of mode behaviors
6. Produce non-empty output for all 5 sections

## Seed Input
Original work at `source/` (50-chapter web novel), fanfic mode: CP
