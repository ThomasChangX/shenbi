# Expected Output: shenbi-review-character Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Speaking character 小贩 not assessed — character has 3 dialogue lines in `drafts/chapter-8.md` (paragraphs 12, 14, 17) but is absent from BDI coverage in audit report | error | `audit/character-review-ch8.md`: missing entry; `drafts/chapter-8.md`: paragraphs 12, 14, 17 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with 林墨's BDI assessment (it is complete and correct)
- Issues with 苏晴's BDI assessment (it is complete and correct)
- Issues with 老陈's BDI assessment (it is complete and correct)

## Expected Output Structure
- Character audit report with BDI coverage table
- Finding table identifying the missing character
- Evidence citing specific dialogue lines the character speaks
- Fix recommendation: add BDI assessment entry for 小贩
