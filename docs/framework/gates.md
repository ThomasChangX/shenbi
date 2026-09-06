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

## Result schema: sampling disclosure (C29)

Gate result JSON (`GateResult`, `src/shenbi/status.py`) carries two optional
disclosure keys introduced by C29 (spec #43):

- `checks[].input_sampled: true` — attached by a check when any of its input
  text was read as a clipped prefix (`clip_with_disclosure()` in
  `gates/shared.py`, replaces raw `[:3000]`/`[:5000]` slicing).
- `sampling_disclosed: "n/m checks ran on sampled input"` — top-level summary
  aggregated by `gate_G5`/`gate_G6`, persisted in gate-marker JSON by
  `write_gate_marker` and surfaced in the G7.13 re-run note.

Both keys are additive (`GateResult` is `total=False`); consumers reading only
`status`/`checks` are unaffected. Count-based sampling caps
(`files_sampled`/`findings_capped`) are documented in
[_sampling-policy.md](sampling-policy.md).
