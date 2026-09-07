# Bug-Hunt Test: shenbi-character-extraction

## Skill Under Test
`skills/shenbi-character-extraction/SKILL.md`

## Test Setup
A novel manuscript with 15 chapters has been analyzed. The import analysis output at `tests/fixtures/character-profile-example.md` contains the protagonist card. The character extraction skill has been run, producing character cards at `tests/fixtures/characters/` (protagonist.md, major/*.md, minor/*.md) and `tests/fixtures/character-profile-example.md`.

## Scenario
The character extraction has been completed. However, the output contains an unevidenced personality trait:

1. **Missing trait evidence**: The protagonist's character card at `tests/fixtures/character-profile-example.md` lists "幽默自嘲" among the frontmatter personality_tags. Reviewing the card body, no tag carries a quoted source passage with a chapter.paragraph reference — the traits are asserted, not evidenced.

2. **Missing voice fingerprint**: The speech pattern section for the secondary character lacks any statistical extraction from actual dialogue. It contains only generic descriptions like "speaks formally" without word frequency, sentence length, or catchphrase analysis from the source text.

3. **Missing relationship entry**: The protagonist and his mentor 老政委 share Act-2 mentor interactions, but the card has no relationship network section at all in `tests/fixtures/character-profile-example.md`.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/character-profile-example.md`: personality section | Evidence gap — tag "幽默自嘲" (like all personality_tags) is asserted without any supporting passage citation from the source chapters | error |
| `tests/fixtures/character-profile-example.md`: speech patterns section | Voice fingerprint missing — only generic descriptions, no statistical extraction from actual dialogue | error |
| `tests/fixtures/character-profile-example.md` | Relationship network incompleteness — protagonist and mentor 老政委 interact across the arc but no relationship section exists | error |

## Agent Task
Run shenbi-character-extraction quality check on the extracted character cards. The agent must detect the unevidenced personality trait, the missing voice fingerprint, and the absent relationship section.
