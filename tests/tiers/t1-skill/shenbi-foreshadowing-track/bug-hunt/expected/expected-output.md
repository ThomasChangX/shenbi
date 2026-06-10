# Expected Output: shenbi-foreshadowing-track Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Core hook hook-001 (玉佩秘密) with core_hook: true is marked ABANDONED — iron rule violation: core hooks must never be abandoned | error | `truth/pending_hooks.md`: hook-001 entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with non-core hooks that were properly advanced (their state transitions have textual evidence)
- Issues with density budget reporting (budget is properly reported)
- Issues with expiry detection (expiring hooks are correctly flagged)

## Expected Output Structure
- Quality check report with finding table
- Identification of the core hook protection violation
- Severity classification for the iron rule breach
