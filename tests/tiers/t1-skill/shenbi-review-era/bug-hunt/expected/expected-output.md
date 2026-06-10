# Expected Output: shenbi-review-era Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Anachronism — modern slang "给力" and "点赞" in Ming Dynasty setting; these terms are internet-era vocabulary (post-2000) incompatible with declared time period (1368-1644) | error | `drafts/chapter-3.md`: paragraph 7; `novel.json`: time_period field |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with period-appropriate vocabulary in other paragraphs
- Issues with artifacts and institutions that are historically accurate for the Ming Dynasty

## Expected Output Structure
- Artifact/vocabulary/institution verification table against declared time period
- Finding table with the anachronistic slang
- Time period reference from novel.json
- Fix recommendation: replace "给力" with period-appropriate expression (e.g., "妙极") and "点赞" with period-appropriate gesture (e.g., "击掌" or "称妙")
