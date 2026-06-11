# Generative Test: shenbi-state-settling

## Skill Under Test
`skills/shenbi-state-settling/SKILL.md`

## Test Setup
A novel project has completed chapter 22 at `drafts/chapter-22.md`. The chapter contains multiple explicit state changes: a character death, a location change, a relationship shift, a new item acquired, and a skill upgrade. Truth files exist at `truth/` including `truth/character_profiles/`, `truth/location_registry.md`, `truth/relationship_map.md`, `truth/ability_registry.md`, and `truth/item_tracker.md`.

## Agent Task
Run shenbi-state-settling to extract all changes from chapter 22. The agent must:
1. Extract only explicitly stated changes (no inferences)
2. Evaluate all 9 change categories
3. Tag direct vs. implied changes correctly
4. Append changes incrementally without rewriting truth files
5. Hold all updates behind the human approval gate
6. Ensure cross-reference consistency across related truth files

## Seed Input
Chapter draft from `drafts/chapter-22.md`, existing truth files from `truth/`
