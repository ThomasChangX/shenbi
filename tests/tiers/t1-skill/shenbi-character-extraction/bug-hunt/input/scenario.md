# Bug-Hunt Test: shenbi-character-extraction

## Skill Under Test
`skills/shenbi-character-extraction/SKILL.md`

## Test Setup
A novel manuscript with 15 chapters has been analyzed. The import analysis output at `tests/fixtures/character-profile-example.md` identifies 6 characters. The character extraction skill has been run, producing character cards at `tests/fixtures/characters/` (protagonist.md, major/*.md, minor/*.md) and `tests/fixtures/character-profile-example.md`.

## Scenario
The character extraction has been completed. However, the output contains a fabricated personality trait:

1. **Fabricated trait**: The protagonist's character card at `tests/fixtures/character-profile-example.md` lists "cynical sense of humor" as a personality tag. Reviewing all 15 source chapters, no passage supports this trait. The protagonist's dialogue is consistently earnest and direct. There is no quoted passage with a chapter.paragraph reference that demonstrates cynical humor.

2. **Missing voice fingerprint**: The speech pattern section for the secondary character (Li Wei) lacks any statistical extraction from actual dialogue. It contains only generic descriptions like "speaks formally" without word frequency, sentence length, or catchphrase analysis from the source text.

3. **Missing relationship entry**: Characters "Chen Ming" and "Old Zhang" share 3 interaction scenes (chapters 4, 8, 11) but have no entry in `tests/fixtures/character-profile-example.md`.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/character-profile-example.md`: personality section | Fabricated trait — "cynical sense of humor" has no supporting passage in any source chapter | error |
| `tests/fixtures/character-profile-example.md`: speech patterns section | Voice fingerprint missing — only generic descriptions, no statistical extraction from actual dialogue | error |
| `tests/fixtures/character-profile-example.md` | Relationship network incompleteness — Chen Ming and Old Zhang share 3 interaction scenes but have no relationship entry | error |

## Agent Task
Run shenbi-character-extraction quality check on the extracted character cards. The agent must detect the fabricated personality trait, the missing voice fingerprint, and the absent relationship entry.
