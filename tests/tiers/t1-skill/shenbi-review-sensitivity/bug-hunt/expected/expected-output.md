# Expected Output: shenbi-review-sensitivity Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Prohibited word "白痴" not flagged — word appears in chapter 6 paragraph 9 dialogue ("你这个白痴，怎么连这个都不懂！") and is listed in `config/platform-rules/qidian-fatigue-list.json` as prohibited for target platform | error | `drafts/chapter-6.md`: paragraph 9; `config/platform-rules/qidian-fatigue-list.json`: fatigue list entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other content in the chapter (no other sensitivity violations)
- Issues with non-prohibited vocabulary (correct usage)

## Expected Output Structure
- Platform rule application checklist
- Fatigue list word scan results
- Finding table with the missed prohibited word
- Fix recommendation: replace "白痴" with a platform-safe alternative
