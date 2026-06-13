# Generative Test: shenbi-genre-config

## Skill Under Test
`skills/shenbi-genre-config/SKILL.md`

## Test Setup
A novel project exists with completed worldbuilding output. A default `tests/fixtures/genre-config-example.json` exists but needs to be configured for the novel's genre.

## Agent Task
Run shenbi-genre-config to configure the genre settings for the novel. Produce a properly configured `tests/fixtures/genre-config-example.json`. Ensure a backup is created before modification, modifications don't contradict existing audit corrections, banned words ≤50 and caution words have viable replacements, audit dimensions are selectively enabled (no false positive floods), all changes require explicit human sign-off, and the JSON is well-formed with all required fields.

## Seed Input
Existing genre-config from worldbuilding output based on `tests/fixtures/outline-example.md`
