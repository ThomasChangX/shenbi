# Expected Output: shenbi-foreshadowing-plant Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Chapter 5 contains 12 foreshadowing operations (7 plant + 3 reinforce + 2 trigger), exceeding the ≤8 per-chapter budget by 4 operations | error | `truth/pending_hooks.md`: chapter 5 planting section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with individual hook metadata (all hooks have complete metadata fields)
- Issues with smokescreen exit strategies (all SMOKESCREEN hooks have documented exits)
- Issues with type/dimension classification (all hooks are properly classified)

## Expected Output Structure
- Quality check report with finding table
- Exact operation count breakdown (7 plant + 3 reinforce + 2 trigger = 12)
- Severity classification for the budget violation
