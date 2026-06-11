# Expected Output: shenbi-foreshadowing-resolve Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Hook-002 (师姐身世) has CP=250 (above 200 threshold) but was deferred without resolution — iron rule violation: CP > 200 requires mandatory immediate action | error | `truth/pending_hooks.md`: hook-002 entry; resolution report |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with lower-CP hooks that were properly deferred (CP below 200 can be deferred)
- Issues with smokescreen handling (SMOKESCREEN hooks include truth revelation)
- Issues with volume completeness (all active hooks are inventoried)

## Expected Output Structure
- Quality check report with finding table
- Identification of the Chase Power threshold violation
- Severity classification for the iron rule breach
