# Generative Test: shenbi-volume-outlining

## Skill Under Test
`skills/shenbi-volume-outlining/SKILL.md`

## Test Setup
A novel project exists with completed story architecture output. No volume outline files exist yet.

## Agent Task
Run shenbi-volume-outlining using the story architecture output as context. Produce all required volume outlines in `tests/fixtures/story/volumes/`. Ensure KRs map to specific chapter ranges (no vague statements), each volume has a tension wave pattern (buildup/rising/explosion/aftermath), every volume ending (except the final) leaves ≥1 tangible hook, early chapters may deviate for world-building (golden chapters), surface/personal/deep conflicts are explicitly advanced, and chapter counts match KR complexity.

## Seed Input
Story architecture output produced by shenbi-story-architecture from `tests/fixtures/outline-example.md`
