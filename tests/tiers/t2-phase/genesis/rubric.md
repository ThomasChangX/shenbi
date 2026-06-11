# T2 Phase Rubric: Genesis

Phase: worldbuilding → power-system → faction-builder → location-builder → character-design → relationship-map
Seed: tests/fixtures/outline-example.md

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Handoff integrity | 20% | Every skill receives correctly structured input from previous skill; missing fields = -5% per field |
| 2 | Cross-skill consistency | 20% | Zero contradictions between outputs of different skills (e.g., character-design doesn't violate worldbuilding rules) |
| 3 | State propagation accuracy | 15% | Truth files updated by skill N correctly read by skill N+1; stale reads = -10% per instance |
| 4 | Phase output completeness | 15% | All files expected at phase end present and non-empty |
| 5 | Regression within phase | 15% | No skill's output during T2 scores below its T1 score on same input |
| 6 | Execution time | 5% | No single skill exceeds 10 minutes; total phase under 60 minutes |
| 7 | Human gate compliance | 10% | Every hard-gate pause respected |

## Kill Switch
Any skill's output scores below its T1 score on same input → phase = 0.

## Expected Output Files
- novel.json
- genre-config.json
- world/story_bible.md
- world/rules.md
- world/locations.md
- world/power_system.md
- world/factions.md
- characters/protagonist.md
- characters/relationships.md
- truth/ (all templates)
