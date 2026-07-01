# Gates

Shenbi uses 8 validation gates to enforce pipeline integrity:

| Gate | Purpose |
|------|---------|
| G0 | Round creation environment check |
| G1 | Pre-dispatch input validation |
| G2 | Output file validation |
| G3 | Scoring readiness |
| G4 | Skill-specific quality checks |
| G5 | T2 phase boundary |
| G6 | T3 pipeline integrity |
| G7 | Post-round audit |

Run via `just gate <Gx> [args]` or `uv run shenbi-validate <Gx>`.
