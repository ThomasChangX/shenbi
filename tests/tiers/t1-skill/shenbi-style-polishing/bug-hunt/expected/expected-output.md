# Expected Output: shenbi-style-polishing Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Content violation — character emotional reaction changed from cold silence ("pressed her lips together, said nothing") to tearful anger ("surge of anger and hurt, tears welling"), altering character behavior and scene tone | error | `drafts/chapter-7-polished.md`: Lin Yue's reaction scene vs original |
| 2 | Content violation — plot event altered: door-slamming action added that was absent in original draft, changing character behavior and scene dynamics | error | `drafts/chapter-7-polished.md`: Lin Yue's exit vs original |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with word count stability (other changes are within bounds)
- Issues with AI-flavor introduction (other prose changes are stylistically appropriate)
- Issues with restraint on purely stylistic changes (sentence rhythm, word choice in non-affected areas)

## Expected Output Structure
- Quality check report comparing original vs polished
- Each content violation clearly identified with before/after text
- Severity classification as content preservation violations
- Distinction between acceptable style changes and unacceptable content changes
