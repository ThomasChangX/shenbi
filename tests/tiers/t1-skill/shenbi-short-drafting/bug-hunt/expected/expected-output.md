# Expected Output: shenbi-short-drafting Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Sequential generation violation — chapter 3 drafted at T+45min before chapter 2's truth files existed at T+52min; chapter 3 was generated without chapter 2's state information | error | Generation log timestamps vs `truth/chapter-2-state.md` creation time |
| 2 | Cross-chapter consistency failure — protagonist's cloak changed from "crimson" (chapter 4) to "blue" (chapter 6) with no scene or transition explaining the change | error | `chapters/chapter-4.md` vs `chapters/chapter-6.md`: cloak description |
| 3 | Per-chapter audit rigor violation — chapter 8 audit explicitly skipped with note "rushed schedule" | error | `reports/batch-summary.md`: chapter 8 row |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with revision discipline for chapters that were revised (all capped at 3 rounds)
- Issues with batch summary format (it is complete for all other chapters)
- Issues with chapters 1, 2, 4, 5, 7, 9-12 which are correctly generated

## Expected Output Structure
- Quality check report covering all 12 chapters
- Timestamp analysis proving out-of-order generation
- Cross-chapter prop/position consistency check
- Per-chapter audit completeness verification
