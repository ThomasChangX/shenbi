# Expected Output: shenbi-relationship-map Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Protagonist-antagonist relationship has no evolution plan — start state, turning points, and expected end state are all missing | error | `characters/relationships.md`: protagonist-antagonist entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other relationships (they all have complete evolution plans)
- Issues with interest grounding (all relationships are properly grounded)
- Issues with character reference integrity (all referenced characters exist)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of the missing evolution plan fields
- Severity classification for each issue
