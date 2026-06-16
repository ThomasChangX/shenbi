# Bug-Hunt Report: shenbi-foreshadowing-plant

**Date**: 2026-06-12
**Skill**: `skills/shenbi-foreshadowing-plant/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- planted defect detected

---

## Detection Summary

| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Chapter 5 contains 12 foreshadowing operations (7 plant + 3 reinforce + 2 trigger), exceeding the <= 8 per-chapter budget by 4 operations | error | `truth/pending_hooks.md`: Chapter 5 planting summary section | YES |

## Detection Analysis

### Skill Rule Applied

**Iron Rule 1**: 每章操作必须 <= 8 条 -- 包括 plant、reinforce、trigger、resolve；超出预算的伏笔必须延迟到下章。

### Evidence

The injected `pending_hooks.md` Chapter 5 planting summary (L184-227) shows:

**已种植项**: 9 plant operations (hook-101 through hook-106, hook-ch5-001 through hook-ch5-003)
**已强化项**: 3 reinforce operations (hook-012, hook-015, hook-018)
**已触发项**: 2 trigger operations (hook-003, hook-007)

**密度核算** table (L219-227) confirms:
```
| plant | 7 |
| reinforce | 3 |
| trigger | 2 |
| resolve | 0 |
| 合计 | 12 / 8 |
```

The total of 12 operations exceeds the iron rule budget of 8 by 4 operations.

### Detection Mechanism

The skill's flow (`Check density budget (<= 8 operations)`) explicitly checks operation count per chapter. Reading the density accounting table in the output reveals `合计: 12 / 8`, which directly violates the budget constraint.

### Severity Classification

**error** -- This is a hard budget violation. The skill's iron rule states the 8-operation limit is non-negotiable. Operations beyond the budget must be deferred to subsequent chapters.

## False Positive Analysis

No false positives. All other aspects of the planting output are correct:
- Hook metadata fields (type, dimension, subtlety, cultivation_interval, max_distance, escalation_curve) are complete for all entries
- SMOKESCREEN hooks (hook-ch5-002) have documented exit strategies
- Cross-thread dependencies are properly recorded
- Type/dimension classifications match the skill's taxonomy

## Conclusion

The planted defect (12 operations exceeding the 8-per-chapter budget) was successfully detected by applying Iron Rule 1 of the shenbi-foreshadowing-plant skill. Detection is unambiguous: the density accounting table explicitly shows `12 / 8`, and the skill flow includes a dedicated "Check density budget" step.
