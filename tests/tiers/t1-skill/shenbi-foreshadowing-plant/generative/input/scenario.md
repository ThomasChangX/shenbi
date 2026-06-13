# Generative Test: shenbi-foreshadowing-plant

## Skill Under Test
`skills/shenbi-foreshadowing-plant/SKILL.md`

## Test Setup
A novel project exists with a chapter 5 memo that contains 3 OPEN hook items in the hook ledger. Truth files include `tests/fixtures/pending-hooks-example.md` with 6 existing active hooks. The project is ready to plant foreshadowing before drafting chapter 5.

## Agent Task
Run shenbi-foreshadowing-plant to produce planting output for chapter 5. All operations must stay within the ≤8 per-chapter budget. Every new hook must have complete metadata (type, dimension, subtlety, cultivation_interval, max_distance, escalation_curve, depends_on — depends_on must never be omitted). Every SMOKESCREEN must have a documented exit strategy. Read `tests/fixtures/pending-hooks-example.md` first to avoid duplication. Planting guidance must reference scene type appropriateness. All hooks must be classified with type (GENUINE/SMOKESCREEN/SIDE_SHADOW) and dimension (THEMATIC/CHARACTER/SYMBOLIC/STRUCTURAL).

## Seed Input
Chapter 5 plan from `tests/fixtures/chapter-plan-example.md` and existing hooks from `tests/fixtures/pending-hooks-example.md`
