# Clean Test: shenbi-chapter-revision

## Skill Under Test
`skills/shenbi-chapter-revision/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `tests/fixtures/chapter-draft-example.md`. An audit produced two findings:
- Finding A1 (warning): Sword name mismatch — "Frostbite" in text vs "Frostveil" in truth file.
- Finding A2 (warning): Time-of-day inconsistency — "afternoon crowds" but scene established as dawn.

The revised chapter at `tests/fixtures/chapter-draft-example.md` is fully correct:
- Finding A1 fixed: sword name corrected to "Frostveil"
- Finding A2 fixed: market description changed to "bustling with the first light of dawn"
- No new plot elements, characters, or narrative threads introduced
- Original word count 4200; revised word count 4350 (3.6% increase, within ±15%)
- All blocking/critical/AI-trace counts unchanged or decreased
- Plot, character details, and foreshadowing fully preserved

## Scenario
All revision content is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-chapter-revision quality check on the revised chapter. Expected result: report zero issues.
