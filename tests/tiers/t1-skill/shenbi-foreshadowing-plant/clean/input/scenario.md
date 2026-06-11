# Clean Test: shenbi-foreshadowing-plant

## Skill Under Test
`skills/shenbi-foreshadowing-plant/SKILL.md`

## Test Setup
A novel project exists with correct foreshadowing planting output for chapter 5:
- `truth/pending_hooks.md` — chapter 5 planting section lists 7 total operations (3 plant + 2 reinforce + 2 trigger), within the ≤8 budget
- All new hooks have complete metadata: type, dimension, subtlety, cultivation_interval, max_distance, escalation_curve, depends_on
- Both SMOKESCREEN hooks have documented exit strategies in notes
- No duplication with existing hooks (pending_hooks.md was read before planting)
- Planting guidance references appropriate scene types (daily paragraphs, dialogue segments)
- All hooks properly classified with type (GENUINE/SMOKESCREEN/SIDE_SHADOW) and dimension (THEMATIC/CHARACTER/SYMBOLIC/STRUCTURAL)

## Scenario
All foreshadowing planting content is correct and follows all skill rules. No budget violations, no missing metadata, no smokescreen without exit strategy.

## Agent Task
Run shenbi-foreshadowing-plant quality check on the existing planting output. Expected result: report zero issues.
