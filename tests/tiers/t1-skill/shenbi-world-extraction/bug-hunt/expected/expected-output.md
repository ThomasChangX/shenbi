# Expected Output: shenbi-world-extraction Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Rule evidence threshold violation — mana depletion rule has only 1 citation (chapter 12.3) instead of required >=2; a second passage exists at chapter 7.15 but was not cited | error | `world/rules.md`: mana depletion rule |
| 2 | Violation-based inference missing — all rules derived exclusively from successful magic use; no rules inferred from failures, near-misses, or behavioral avoidances (e.g., protagonist avoiding casting when exhausted in chapter 5) | error | `world/rules.md`: all rules section |
| 3 | Prose format violation — story_bible.md is a 12-item bulleted list instead of the required 4-paragraph narrative prose format | error | `world/story_bible.md`: full document |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with location coverage, which correctly includes atmosphere, function, and first appearance
- Issues with power system completeness, which has all required fields
- Issues with consistency between rules and story bible content

## Expected Output Structure
- Quality check report covering all world output files
- Evidence citation count analysis per rule
- Violation-based inference gap identification
- Format compliance check for story_bible.md
