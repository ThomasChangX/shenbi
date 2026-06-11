# Expected Output: shenbi-volume-consolidation Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Unresolved hook completeness violation — Hook H005 "The northern signal fire" (status: ACTIVE, planted chapter 10) is missing from the unresolved hooks list in the volume 1 consolidation report | error | `consolidation/volume-1/report.md`: unresolved hooks section; `truth/pending_hooks.md`: H005 entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with H001, H002, H003 (correctly listed)
- Issues with H004 exclusion (correctly excluded because RESOLVED)
- Issues with volume summary word count (within 500-word limit)
- Issues with narrative arc accuracy (major events are traceable)
- Issues with retrievability (per-chapter summaries accessible)

## Expected Output Structure
- Quality check report with finding table
- Comparison of `truth/pending_hooks.md` active hooks vs report unresolved hooks list
- Specific identification of H005 as the missing hook
- Confirmation that H004 exclusion is correct
