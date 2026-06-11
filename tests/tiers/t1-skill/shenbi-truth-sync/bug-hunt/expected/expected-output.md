# Expected Output: shenbi-truth-sync Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Missed conflict — chapter 17 explicitly states Chen Wei discarded twin daggers and acquired longsword "Dawnbreaker", but the truth-sync output does not detect or flag the contradiction with `truth/character_profiles/chen-wei.md` which still lists "Twin daggers, named Shadow and Shade" | error | `sync/truth-sync-15-18.md`: Chen Wei weapon field; `truth/character_profiles/chen-wei.md`: weapon entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the location update (Chen Wei's location was correctly updated to "Frozen Wasteland border camp")
- Issues with scope precision (only chapters 15-18 were processed)
- Issues with auditability (before/after diffs are preserved for the location update)

## Expected Output Structure
- Quality check report with finding table
- Conflict detection analysis showing chapter 17 text vs truth file weapon entry
- Specific chapter text evidence for the weapon change
- Confirmation that the location update was correctly handled
