# Expected Output: shenbi-review-world-rules Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Numerical cross-reference failure — character 林墨's age stated as "二十五岁" (25) in chapter text contradicts truth file value of 17 | error | `drafts/chapter-5.md`: paragraph 4; `truth/character_profiles/lin-mo.md`: field `age` |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other numerical claims in the chapter (dates, distances are consistent with truth files)
- Issues with non-numerical world rules (correct)

## Expected Output Structure
- Numerical cross-reference table mapping text claims to truth file values
- Finding table with the age discrepancy
- Truth file + field reference for verification
- Fix recommendation: change "二十五岁" to "十七岁" to match truth file, or update truth file if the chapter is correct
