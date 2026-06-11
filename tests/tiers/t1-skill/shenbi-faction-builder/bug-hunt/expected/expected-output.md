# Expected Output: shenbi-faction-builder Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Order of Ash has no internal factional split — described as fully unified with zero internal dissent | error | `world/factions/order-of-ash.md`: internal structure section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the Iron Syndicate (has proper internal split)
- Issues with the Dawn Collective (has proper internal split)
- Issues with cross-faction dynamics (explicit relationships exist between factions)
- Issues with interest-driven realism (all factions have explainable interest logic)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of the missing internal conflict in Order of Ash
- Severity classification for each issue
