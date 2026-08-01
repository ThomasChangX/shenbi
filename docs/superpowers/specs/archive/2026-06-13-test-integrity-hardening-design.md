# Test Framework Integrity Hardening Design

**Date**: 2026-06-13
**Status**: Draft
**Motivation**: R5 round exposed 12 integrity violations — self-scoring, gate bypass, batch-generated outputs, mid-round code patching. All caused by structural gaps in the test framework, not by missing rules.

## Root Causes

1. **No T2/T3 protocol** — command-to-give.md only covers T1; T2/T3 have no step-by-step execution steps
2. **Gates are soft blocks** — G5/G6 FAIL does not prevent scoring from proceeding
3. **No provenance** — score files don't record who scored, whether gates passed, or when
4. **No post-round verification** — G7 checks structure but not whether gates actually passed against real files

## Design: Three Layers

### Layer 1: Guidance (Protocol + State Machine)

#### T2/T3 protocol in command-to-give.md

Append after the existing "第五步：推进" section. Two new sections:

**第六步：T2 Phase 执行**

For each phase in `tests/tiers/deps.json` → `t2-phases`:

1. `python3 tests/phase-runner.py start <phase> --round-dir <round-dir> --project-dir <round-dir>/project-output`
2. For each skill in the phase's `prerequisites` list, in order:
   - `python3 tests/phase-runner.py pre-skill <phase> <skill> --round-dir <round-dir>`
   - Read `skills/<skill>/SKILL.md`, execute skill, output to `<round-dir>/project-output/`
   - `python3 tests/phase-runner.py post-skill <phase> <skill> --round-dir <round-dir> --project-dir <round-dir>/project-output`
3. `python3 tests/phase-runner.py pre-score <phase> --round-dir <round-dir>`
4. Dispatch independent scoring subagent (same isolation rules as T1)
5. `python3 tests/scoring.py tests/tiers/t2-phase/<phase>/rubric.md <score-file> --test-type generative --round-dir <round-dir>`
6. `python3 tests/phase-runner.py post-score <phase> <score-file> --round-dir <round-dir>`
7. `python3 tests/phase-runner.py finalize <phase> --round-dir <round-dir> --project-dir <round-dir>/project-output>`

**第七步：T3 Pipeline 执行**

For each pipeline in `tests/tiers/deps.json` → `t3-pipelines`:

1. Confirm all T2 phases finalized and ≥ 94 (read from `summary.json`)
2. `python3 tests/validate-gate.py G6 <pipeline> <round-dir> <round-dir>/project-output`
3. Dispatch independent scoring subagent
4. `python3 tests/scoring.py tests/tiers/t3-pipeline/<pipeline>/rubric.md <score-file> --test-type generative --round-dir <round-dir>`
5. Record to `<round-dir>/t3-reports/<pipeline>-generative-scores.json`

#### phase-runner.py

Location: `tests/phase-runner.py`

State machine with subcommands. Does NOT dispatch subagents — only checks preconditions and records state.

**State file**: `<round-dir>/phase-state/<phase>.json`

```json
{
  "phase": "genesis",
  "state": "started",
  "steps": [
    {"action": "start", "timestamp": "...", "g5_status": "PASS"},
    {"action": "post-skill", "skill": "shenbi-worldbuilding", "timestamp": "...", "g2": "PASS", "g4": "PASS"},
    {"action": "post-skill", "skill": "shenbi-power-system", "timestamp": "...", "g2": "PASS", "g4": "PASS"}
  ]
}
```

States: `created` → `started` → `skills_done` → `scored` → `finalized`

Each subcommand checks the current state and refuses to proceed if preconditions aren't met. State transitions are append-only.

**Subcommands**:

| Command | Precondition | Action |
|---------|-------------|--------|
| `start <phase>` | None | Run G5, write state=started if PASS |
| `pre-skill <phase> <skill>` | state=started | Check upstream gate markers exist |
| `post-skill <phase> <skill>` | state=started | Run G2+G4. Write G4 gate marker only if PASS (G2 does not write markers) |
| `pre-score <phase>` | state=started, all skills have markers | Check expected outputs exist |
| `post-score <phase> <file>` | state=skills_done | Verify score file exists, record result in state file (does NOT run scoring.py) |
| `finalize <phase>` | state=scored | Re-run G5, verify markers, set state=finalized |

### Layer 2: Hard Check (Gate Markers + scoring.py enforcement)

#### validate-gate.py writes PASS markers

When a gate returns PASS and `round_dir` is provided, write a marker file to:

`<round-dir>/gate-markers/<gate>-<target>-<test-type>.json`

The marker contains the full PASS JSON output (timestamp, checks) plus a `files_checked` field listing the file paths that were validated. G7.13 uses this list to re-validate the same files.

Implementation: in `main()`, after parsing gate result, if status == "PASS" and round_dir is available, write marker. For G4, the round_dir comes from the existing `--round-dir` CLI argument. For G6, same.

Gates that write markers: G4, G6. G2 does not write markers (it's a per-file format check, not a skill-level gate).

#### scoring.py requires gate markers

Add `--round-dir <path>` argument to scoring.py. When provided:

1. Infer tier and target from rubric path (reuse existing path-parsing logic at scoring.py:204-205 which already extracts skill_name from rubric directory structure):
   - Path contains `t1-skill/` → extract skill name, check `gate-markers/G4-<skill>-<test-type>.json`
   - Path contains `t2-phase/` → read `deps.json` prerequisites, check `gate-markers/G4-<skill>-generative.json` for each
   - Path contains `t3-pipeline/` → check `gate-markers/G6-<pipeline>.json`
2. If any required marker is missing → exit(3) with error message listing missing markers (exit code 3 distinguishes from exit code 2 which is score validation failure)
3. If `--round-dir` is not provided → skip marker check (backward compatible for development)

### Layer 3: Audit (G7 post-round verification)

Add four new checks to G7 in validate-gate.py:

#### G7.13: Gate re-run verification

Iterate all files in `<round-dir>/gate-markers/`. For each marker:
- Parse gate, target, test-type from filename pattern `<gate>-<target>-<test-type>.json`
- Re-run the corresponding gate function using the marker's `files_checked` list as `file_paths`
  - For G4 markers: `gate_G4(target, test_type, files_checked, round_dir)` — `target` is the skill name
  - For G6 markers: `gate_G6(pipeline_name=target, round_dir=round_dir, project_dir=<round-dir>/project-output)` — `project_dir` is reconstructed as `<round-dir>/project-output` (same convention as T3 protocol)
- If re-run result is FAIL but marker records PASS → VIOLATION (G7 FAIL)

Note: phases with `g4_checker: null` in deps.json (audit, management, import, foundation, short-story) use `g4_generic_generative` as fallback. These markers are still valid — the generic checker is the gate function for these skills.

#### G7.14: Score timeline consistency

For all score files in `t1-reports/`, `t2-reports/`, `t3-reports/`:
- Score file mtime must be > output file mtime (can't score before output exists)
- Score file mtime must be > gate marker mtime (can't score before gate passes)
- Violation → TIMELINE_VIOLATION (G7 WARN, not blocking)

#### G7.15: Score pattern suspiciousness

For all generative score files, grouped by tier:
- Compute score vectors (tuple of dimension scores)
- If ≥3 skills share identical score vector → DUPLICATE_PATTERN warning
- If score file has no `scorer` field or scorer is "MISSING" → NO_PROVENANCE warning
- These are warnings, written to `summary.json` `audit_warnings` array, not blocking

#### G7.16: Phase state verification

For each phase in `summary.json` `t2_scores`:
- Check `<round-dir>/phase-state/<phase>.json` exists and state is "finalized"
- If phase has score but state is not finalized → INCOMPLETE_PHASE (G7 FAIL)

For each pipeline in `summary.json` `t3_scores`:
- Check `<round-dir>/gate-markers/G6-<pipeline>.json` exists
- If missing → MISSING_GATE (G7 FAIL)

Note: T3 pipelines do NOT use phase-runner.py. They go directly through G6 validation and independent scoring, as shown in the T3 protocol steps.

#### Audit result handling

| Check | Blocking | Written to |
|-------|----------|-----------|
| G7.13 gate re-run mismatch | Yes (FAIL) | must_fix |
| G7.14 timeline violation | No (WARN) | summary.json audit_warnings |
| G7.15 pattern/provenance | No (WARN) | summary.json audit_warnings |
| G7.16 phase state mismatch | Yes (FAIL) | must_fix |

### summary.json additions

```json
{
  "audit_warnings": [
    {"type": "DUPLICATE_PATTERN", "severity": "warn", "message": "8 skills share identical score vector in t1 generative"},
    {"type": "NO_PROVENANCE", "severity": "warn", "message": "29 t1 score files lack scorer field"}
  ]
}
```

## Files Modified

| File | Change |
|------|--------|
| `command-to-give.md` | Add 第六步 (T2) and 第七步 (T3) protocol sections |
| `tests/validate-gate.py` | Write gate markers on PASS; add G7.13–G7.16 checks |
| `tests/scoring.py` | Add `--round-dir` flag; verify gate markers before scoring |
| `tests/phase-runner.py` | New file. State machine for T2/T3 execution |

## What This Does NOT Prevent

- An agent determined to fake results can forge gate markers and score files. The audit layer (G7.13) catches this by re-running gates against actual files.
- An agent can skip using phase-runner.py entirely. The guidance layer reduces motivation, not ability.
- An agent can modify validate-gate.py mid-round. No hash lock is applied. The audit layer re-runs gates with the current code, so if code was patched to always PASS, G7.13 won't catch it. This is an accepted limitation.

## R6 Execution Plan

After implementing these changes, R6 must be re-run from scratch:

1. T1: Re-run all 58 skills using existing protocol (fix the 29 batch-generated outputs)
2. T2: Use phase-runner.py to execute all 9 phases
3. T3: Use G6 gate + independent scoring for all 3 pipelines
4. G7: Post-round audit must pass with zero VIOLATIONS
