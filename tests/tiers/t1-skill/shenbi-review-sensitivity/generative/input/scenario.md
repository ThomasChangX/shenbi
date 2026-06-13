# Generative Test: shenbi-review-sensitivity

## Skill Under Test
`skills/shenbi-review-sensitivity/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 15 at `tests/fixtures/chapter-draft-example.md`. The project's `tests/fixtures/novel-example.json` specifies the target platform. Platform fatigue list and sensitivity rules are at `tests/fixtures/config/platform-rules/`.

## Agent Task
Run shenbi-review-sensitivity audit on chapter 15. Produce a complete sensitivity audit report including:
1. Platform rule application check
2. Fatigue list word scan
3. Content sensitivity assessment
4. Cultural sensitivity review

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`, platform rules from `tests/fixtures/config/platform-rules/`, novel config from `tests/fixtures/novel-example.json`
