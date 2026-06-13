# Bug-Hunt Test: shenbi-chapter-revision

## Skill Under Test
`skills/shenbi-chapter-revision/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `tests/fixtures/chapter-draft-example.md`. An audit has been completed and produced the following findings:
- Finding A1 (warning): A character named Lin Yue refers to her sword as "Frostbite" but in the truth file `tests/fixtures/character-profile-example.md` the sword is named "Frostveil".
- Finding A2 (warning): Paragraph 14 describes the market as "bustling with afternoon crowds" but chapter 8 established the scene takes place at dawn.

The agent runs shenbi-chapter-revision to fix these two audit findings.

## Scenario
The revision at `tests/fixtures/chapter-draft-example.md` fixes both audit findings but introduces a scope violation: a new subplot element is added. In paragraph 9, the revision introduces a mysterious stranger watching from the shadows who was never mentioned in the original draft or any truth file. This stranger is described in detail (dark cloak, silver eyes) and the protagonist notices them, creating a new narrative thread unrelated to either audit finding.

Additionally, the revision is significantly longer: the original chapter was 4200 words; the revised version is 5100 words (a 21% increase, exceeding the ±15% length constraint).

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: paragraph 9 | Scope violation — revision introduces a new subplot character (mysterious stranger in dark cloak with silver eyes) unrelated to any audit finding | error |
| `tests/fixtures/chapter-draft-example.md`: full document | Length constraint violation — revision is 5100 words vs original 4200 words (21% increase, exceeds ±15% limit) | error |

## Agent Task
Run shenbi-chapter-revision quality check on the revised chapter. The agent must detect both the scope violation (new plot element unrelated to audit findings) and the length constraint violation.
