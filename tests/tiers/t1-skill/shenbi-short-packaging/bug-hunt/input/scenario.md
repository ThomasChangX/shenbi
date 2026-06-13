# Bug-Hunt Test: shenbi-short-packaging

## Skill Under Test
`skills/shenbi-short-packaging/SKILL.md`

## Test Setup
A 20-chapter short novel has been completed. The short packaging skill has been run, producing packaging materials at `tests/fixtures/import/packaging/` (titles.md, blurbs.md, selling_points.md, cover_prompt.md, keywords.md).

## Scenario
The short packaging has been completed. However, the blurb contains a major spoiler:

1. **Spoiler in blurb**: The primary blurb at `tests/fixtures/report-example.txt` (version 1) reveals the climax resolution from act 3. Specifically, it states "After the protagonist sacrifices their powers to seal the rift, the world is saved and they live as an ordinary person." The sacrifice and the sealing of the rift are the act 3 climax (chapters 17-18). The blurb should only tease the conflict setup without revealing the resolution.

2. **Missing evidence in selling points**: Two of the four selling points in `tests/fixtures/report-example.txt` lack chapter.paragraph citations. Selling point 2 ("The betrayal scene is emotionally devastating") and selling point 4 ("The magic system is original and well-structured") have no specific text references.

3. **Cover prompt missing fields**: The cover prompt at `tests/fixtures/report-example.txt` includes subject and scene but is missing color palette and style keywords.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/report-example.txt`: blurb version 1 | Spoiler violation — reveals act 3 climax resolution (protagonist sacrifices powers, seals rift, lives as ordinary person) | error |
| `tests/fixtures/report-example.txt`: points 2 and 4 | Evidence backing violation — 2 selling points lack chapter.paragraph citations | error |
| `tests/fixtures/report-example.txt` | Cover prompt usability violation — missing color palette and style keywords fields | error |

## Agent Task
Run shenbi-short-packaging quality check on the packaging materials. The agent must detect the spoiler in the blurb, the uncited selling points, and the incomplete cover prompt.
