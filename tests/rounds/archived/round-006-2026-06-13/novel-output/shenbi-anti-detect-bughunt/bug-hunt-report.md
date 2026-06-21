---
skill: shenbi-anti-detect
test_type: bug-hunt
---

## Detection Summary

| Defect ID | Status | Location | Violated Rule | Evidence |
|-----------|--------|----------|---------------|----------|
| D001 | DETECTED | `tests/fixtures/chapter-plan-example.md` L42 | SKILL.md 铁律#1 | Contradiction between hard rules |

## Planted Defects

1. **D001**: Hard Rule contradiction in fixture file. Detected at `tests/fixtures/chapter-plan-example.md` L42. Violates SKILL.md 铁律#1 "去重原则" and 铁律#2 "世界铁律互不矛盾".

## False Positive Check

False positives: 0
误报: 0
All flagged issues correspond to planted defects. No hallucinated findings.
