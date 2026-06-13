# Clean Test: shenbi-genre-config

## Skill Under Test
`skills/shenbi-genre-config/SKILL.md`

## Test Setup
A novel project exists with a properly configured genre-config:
- `tests/fixtures/genre-config-example.json` — well-formed JSON with all required fields, backup exists at `genre-config.json.bak`, banned words ≤50, caution words have viable replacements, audit dimensions selectively enabled, all changes have explicit human sign-off

The modification log shows backup creation before every change. No modifications contradict existing audit corrections. The fatigue word list is balanced.

## Scenario
All genre-config content is correct and follows all skill rules. No missing backups, no contradictory changes, no JSON errors.

## Agent Task
Run shenbi-genre-config quality check on the existing configuration. Expected result: report zero issues.
