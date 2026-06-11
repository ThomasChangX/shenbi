# T3 Pipeline Rubric: Import-Form

Seed: tests/fixtures/report-example.txt → import-analysis → character-extraction → world-extraction → canon-import

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | End-to-end data integrity | 15% | All extracted files consistent with source text; no contradictions between extraction outputs |
| 2 | Extraction fidelity | 15% | All extracted characters/world/events traceable to source with zero fabrication; unconfirmed items list is exhaustive |
| 3 | Cross-extraction consistency | 15% | Characters extracted in character-extraction match those identified in import-analysis; world rules in world-extraction consistent with import-analysis story bible |
| 4 | Import completeness | 15% | All 4 import skills produce output; character files, world files, canon files, and analysis all present |
| 5 | Evidence coverage | 10% | ≥80% of extracted facts have chapter.paragraph evidence; <20% marked "unconfirmed" |
| 6 | Source coverage completeness | 10% | All major characters, plot events, and world rules from the source text are captured; <5% of significant elements missed |
| 7 | Full project file completeness | 5% | import/analysis/*, characters/*, world/*, import/canon/* all present and non-empty |
| 8 | Import report quality | 10% | Analysis summary has accurate statistics; downstream task checklist is complete and actionable |
| 9 | Cross-extraction consistency | 5% | Characters in character-extraction exist in import-analysis; world rules consistent with story bible |

## Kill Switch
Any fabricated fact not marked "unconfirmed" → pipeline = 0.
Any chapter fails sensitivity audit (platform-prohibited content) → pipeline = 0.
