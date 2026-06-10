# T2 Phase Rubric: Foundation

Phase: foundation-review → chapter-revision → truth-sync → style-learning
Seed: Full mini-project (genesis + architecture + drafting output)

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Handoff integrity | 20% | Every skill receives correctly structured input from previous skill; missing fields = -5% per field |
| 2 | Cross-skill consistency | 20% | Zero contradictions between outputs of different skills (e.g., chapter-revision doesn't violate foundation-review findings) |
| 3 | State propagation accuracy | 15% | Truth files updated by skill N correctly read by skill N+1; stale reads = -10% per instance |
| 4 | Phase output completeness | 15% | All files expected at phase end present and non-empty |
| 5 | Regression within phase | 15% | No skill's output during T2 scores below its T1 score on same input |
| 6 | Execution time | 5% | No single skill exceeds 10 minutes; total phase under 60 minutes |
| 7 | Human gate compliance | 10% | Every hard-gate pause respected |

## Kill Switch
Any skill's output scores below its T1 score on same input → phase = 0.

## Expected Output Files
- foundation/review_report.md
- chapters/ (revised chapter files)
- truth/ (synchronized state files)
- style/style_profile.md
