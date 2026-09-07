# Bug-Hunt Test: shenbi-character-design

## Skill Under Test
`skills/shenbi-character-design/SKILL.md`

## Test Setup
A novel project exists with character design output in `tests/fixtures/characters/`:
- `tests/fixtures/character-profile-example.md` — protagonist profile with voice markers
- `tests/fixtures/character-profile-example.md` — antagonist profile with voice markers
- `tests/fixtures/character-profile-example.md` — mentor character with voice markers
- `tests/fixtures/character-profile-example.md` — relationship matrix

## Scenario
The character design output has been generated. Upon review, the mentor character's profile reuses the protagonist's voice profile verbatim — the same speech-pattern entries, catchphrases, and register appear under both characters, so their dialogue is indistinguishable. This violates the voice distinctness requirement.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/character-profile-example.md` (protagonist) and `tests/fixtures/character-profile-example.md` (mentor): voice_profile sections | Voice distinctness violation — both profiles carry the identical speech-pattern entry "习惯用现代中国网络用语和流行文化梗对比异世界现实" and the same catchphrase set, so protagonist and mentor are indistinguishable in dialogue | error |

## Agent Task
Run shenbi-character-design quality check on the existing character output. The agent must detect that two characters have indistinguishable voice profiles.
