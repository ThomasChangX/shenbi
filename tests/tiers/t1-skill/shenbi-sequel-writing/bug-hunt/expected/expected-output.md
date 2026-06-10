# Expected Output: shenbi-sequel-writing Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Historical immutability violation — chapter 25 checksum mismatch: current (a1b2c3d4...) vs snapshot (e5f6a7b8...); paragraph changed from "hesitant and uncertain" to "confident and determined" | error | `chapters/chapter-25.md` vs `snapshots/chapter-030/manifest.json` |
| 2 | Drift detection missing — pre-writing report contains no drift detection section; behavioral, voice, style, and setting drift checks all absent | error | `reports/sequel-pre-writing.md` |
| 3 | Human intent confirmation timing violation — writing started at T+30min but intent re-confirmed at T+120min; confirmation must occur before any writing begins | error | Writing log timestamps vs intent confirmation record |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with context reconstruction, which correctly rebuilds all 6 categories
- Issues with chapters 26-30, whose checksums match their snapshots
- Issues with pre-writing report sections other than drift detection

## Expected Output Structure
- Quality check report covering the sequel writing process
- Checksum verification for all published chapters against snapshot manifest
- Drift detection section presence verification
- Human intent confirmation timing analysis
