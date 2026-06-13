# Bug-Hunt Test: shenbi-import-analysis

## Skill Under Test
`skills/shenbi-import-analysis/SKILL.md`

## Test Setup
A novel manuscript exists at `tests/fixtures/chapters/` with 12 source chapters. The 8-pass import analysis pipeline has been run, producing output at `tests/fixtures/import/analysis/` (01_parse.md through 08_state.md).

## Scenario
The import analysis pipeline completed all 8 passes. However, the output at `tests/fixtures/character-profile-example.md` contains a fabricated character detail that cannot be traced to any passage in the source text. Specifically:

1. **Fabricated fact**: The character analysis claims that the protagonist "grew up in a coastal village" and "learned swordsmanship from a retired navy captain." Neither of these details appears anywhere in the 12 source chapters. The protagonist's actual origin (a mountain town) is described in chapter 3, paragraph 7.

2. **Missing traceability**: Several extracted facts in the character pass and the plot pass lack chapter.paragraph references. At least 8 extracted facts have no source citation at all.

3. **Pipeline violation**: Pass 4 (plot) output references data from Pass 7 (highlights), which should not yet exist at that point in the pipeline. The serial/parallel dependencies defined in the DOT flowchart are violated.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/character-profile-example.md`: protagonist profile | Fabricated fact — "grew up in a coastal village" and "learned swordsmanship from a retired navy captain" with no source passage in any of the 12 chapters | error |
| `tests/fixtures/character-profile-example.md` and `tests/fixtures/chapter-plan-example.md` | Missing traceability — at least 8 extracted facts lack chapter.paragraph references | error |
| `tests/fixtures/chapter-plan-example.md`: data dependency section | Pipeline correctness violation — Pass 4 references data from Pass 7, violating serial/parallel dependency order | error |

## Agent Task
Run shenbi-import-analysis quality check on the 8-pass output. The agent must detect the fabricated character detail, the missing traceability citations, and the pipeline dependency violation.
