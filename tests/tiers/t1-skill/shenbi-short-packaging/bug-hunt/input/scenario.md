# Bug-Hunt Test: shenbi-short-packaging

## Skill Under Test
`skills/shenbi-short-packaging/SKILL.md`

## Test Setup
A 20-chapter short novel has been completed. The short packaging skill has been run, producing packaging materials at `tests/fixtures/import/packaging/` (titles.md, blurbs.md, selling_points.md, cover_prompt.md, keywords.md).

## Scenario
The short packaging has been completed. However, the blurb contains a major spoiler:

1. **Spoiler in blurb**: The primary blurb at `tests/fixtures/chapter-draft-example.md` (version 1) reveals the chapter's closing beat. Specifically, it quotes the closing line "本身就是一种危险的开始" verbatim — the chapter-ending cognitive hook. The blurb should only tease the conflict setup without revealing the closing line.

2. **Missing evidence in selling points**: Two of the four selling points in `tests/fixtures/chapter-draft-example.md` lack chapter.paragraph citations. Selling point 2 (the debt-trap scene built on "灵能修炼贷款") and selling point 4 (the caste-rule hook "灵能僭越罪") have no specific text references.

3. **Cover prompt missing fields**: The cover prompt at `tests/fixtures/chapter-draft-example.md` includes subject and scene but is missing color palette and style keywords.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: blurb version 1 | Spoiler violation — reveals the chapter's closing line "本身就是一种危险的开始" verbatim | error |
| `tests/fixtures/chapter-draft-example.md`: points 2 and 4 | Evidence backing violation — 2 selling points lack chapter.paragraph citations | error |
| `tests/fixtures/chapter-draft-example.md` | Cover prompt usability violation — missing color palette and style keywords fields | error |

## Agent Task
Run shenbi-short-packaging quality check on the packaging materials. The agent must detect the spoiler in the blurb, the uncited selling points, and the incomplete cover prompt.
