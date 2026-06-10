# Expected Output: shenbi-review-memo-compliance Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Section "key_scenes" verdict inflated — marked "fulfill" but only 2 of 4 required scenes present; missing: "confrontation with guardian spirit" and "escape through underground river" | error | `audit/memo-compliance-ch7.md`: key_scenes verdict; `plans/chapter-7-plan.md`: key_scenes section lists 4 items; `drafts/chapter-7.md`: only scenes 1 and 2 present |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other memo sections that are genuinely fulfilled (verdicts are correct)
- Issues with the 2 scenes that are present (they are correctly implemented)

## Expected Output Structure
- Section-by-section verification table with fulfill/partial/missing verdict
- Per-section item checklist showing which items are present/absent
- Finding table identifying the inflated verdict
- Fix recommendation: either add the missing scenes to the chapter or change verdict to "partial"
