# Bug-Hunt Test: shenbi-world-extraction

## Skill Under Test
`skills/shenbi-world-extraction/SKILL.md`

## Test Setup
A fantasy novel manuscript has been analyzed. The world extraction skill has been run, producing `tests/fixtures/world-rules-example.md`, `tests/fixtures/world-power-system-example.md`, `tests/fixtures/world-locations-example.md`, `tests/fixtures/world-story-bible-example.md`, and `tests/fixtures/chapter-plan-example.md`.

## Scenario
The world extraction has been completed. However, critical evidence and provenance violations exist:

1. **Insufficient evidence citations**: The rule "灵能总量在整个灵质海中恒定不变" at `tests/fixtures/world-rules-example.md` is stated with testable standards but carries no chapter.paragraph evidence citation at all. The SKILL.md requires >=2 independent textual evidence citations per extracted rule; none of the ten rules reference a specific manuscript passage as evidence.

2. **Hypothetical instead of textual evidence**: Each rule's 违规示例 entry illustrates violations with invented hypotheticals rather than citations to actual manuscript passages, so the rules cannot be traced back to the source text.

3. **story_bible.md format**: The story bible at `tests/fixtures/world-story-bible-example.md` is genuine 4-paragraph narrative prose, but the extraction carries no record of which manuscript passages fed each paragraph — the prose format is met while the traceability requirement is skipped.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/world-rules-example.md`: 规则一 | Rule evidence threshold violation — the rule "灵能总量在整个灵质海中恒定不变" carries zero chapter.paragraph citations; required >=2 independent textual evidence citations per rule | error |
| `tests/fixtures/world-rules-example.md`: 违规示例 entries | Evidence provenance violation — violations illustrated with invented hypotheticals such as "主角在战斗中灵能耗尽，下一章开头就恢复如初" instead of citations to actual manuscript passages | error |
| `tests/fixtures/world-story-bible-example.md` | Traceability skipped — 4-paragraph prose format is met but no record links each paragraph to the manuscript passages it was extracted from | error |

## Agent Task
Run shenbi-world-extraction quality check on the extracted world files. The agent must detect the missing evidence citations, the hypothetical-only provenance, and the skipped story-bible traceability.
