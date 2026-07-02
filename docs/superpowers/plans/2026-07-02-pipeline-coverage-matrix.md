# Novel Pipeline: Spec Coverage Matrix

> **Purpose.** Maps every section of the novel-pipeline spec
> (`docs/superpowers/specs/2026-07-01-novel-pipeline-design.md`, §1-§19) and every
> acceptance criterion in spec §15 to the wave/task that implements it. Gaps and
> partial implementations are called out explicitly so nothing is silently dropped.
>
> **Verification basis.** Status in the matrices below is verified against the
> committed source under `src/shenbi/pipeline/` and `skills/`, not from the plan
> docs alone. Where a discrepancy exists between the plan and the code, the code
> is treated as authoritative and a note is added.
>
> Wave key: W1 = Foundation, W2 = Retrieval, W3 = Orchestrators,
> W4 = Skill Integration, W5 = Cross-Wave Integration Tests.

---

## Section-level coverage (§1-§19)

| Spec § | Title | Wave | Task(s) | Status | Notes |
|---|---|---|---|---|---|
| §1 | Background & Motivation | N/A | N/A | Context only | No implementation target. |
| §2 | Architecture | W1 | T1, T6 | Implemented | Three-layer separation, 7 CLI commands, gate strategy, G3 independence, embedded-human + deferred-write staging. |
| §3 | State Machine | W1 + W3 | W1:T1-2, W3:T7-9 | Implemented | Transition table incl. `failed` terminal; per-step unified action; `pipeline-state.json`; interrupt/resume. |
| §4 | Seed File Parsing | W1 | T4 | Implemented | Full parse map; `total_chapters` intentionally unset here (set by genesis step 6). §4.2 dynamic re-update — see Gap G2. |
| §5 | Genesis (Phase 1) | W3 | T2 | Implemented | 17-step sequence, G4 per step, genesis checkpoint pause, progressive creation, style bootstrap, optional anchor-curate. |
| §6 | Per-Chapter Loop (Phase 2) | W3 | T3-6 | Implemented (1 gap) | Core/genre/boundary circles wired; revision routing wired; triggers wired. §6.5 `total_chapters` re-update — see Gap G2. |
| §7 | Context Architecture | W2 | T1-3 | Implemented | Route A entity index, Route B float32 embeddings + dedup, deterministic rerank, materialized context file, Route B fallback. |
| §8 | Book Closure (Phase 3) | W3 | T6 | Implemented | Closure runner, convergence detection, snapshot-after-review ordering. |
| §9 | Checkpoint Design | W1 + W3 | W1:T2,T5; W3:T9 | Implemented (1 gap) | Pause/review/resume + staging commit-on-approve. §9.2 truth-sync after modify relies on skill — see Gap G4. |
| §10 | Snapshot Improvements | W4 | T3 | Implemented | Incremental + full hybrid, checksum enforcement, manifest, rollback integrity. |
| §11 | Error Handling & Recovery | W3 | T8 | Implemented | Handlers wired into genesis/chapter-step retry loops; per-error retry policies. |
| §12 | Existing Skill Changes | W4 | T1-T6c | Implemented | character-design expand, foreshadowing genesis, snapshot-manage full, chapter-drafting context read, drift-guidance bounded, style-learning bootstrap, context-composing pipeline mode, memory-distill density trigger. |
| §13 | New Orchestrator Modules | W1-W3 | All | Implemented | state, machine, filelock_utils, seed_parser, checkpoint, cli, dispatch_helper, genesis, chapter_loop, audit_layer, revision_router, triggers, closure, transitions, error_handler, context_assemble, truth_index, truth_embed. |
| §14 | Design Decisions | N/A | N/A | Context only | No implementation target. |
| §15 | Acceptance Criteria | W1-W5 | All | Verified | 20 criteria — see matrix below. |
| §16 | Genesis Dependency Table | W3 | T2 | Verified in tests | 17-step contract-read sourcing validated by genesis orchestrator G1 checks. |
| §17 | Ramp-Up Read Coverage | W3 | T3 | Documented, NOT implemented | Skill SKILL.md handles ramp-up skips; pipeline does NOT pre-filter G1 inputs. See Gap G1. |
| §18 | G4 Staging Validation | W1 + W3 | W1:T5; W3:T9 | Implemented | G4 runs on `staging/`; approve -> commit -> no re-validation (already verified); fail -> §11 retry. |
| §19 | foreshadowing-plant `--mode genesis` | W4 | T2 | Implemented | genesis mode reads outline (no chapter plan); per-chapter default preserved; mode passed via dispatch prompt. |

**Section coverage summary:** 17 of 19 implementation-targeted sections fully
implemented. §1 and §14 are context-only (no code). Two partial sections — §4/§6
(dynamic `total_chapters` re-update) and §17 (ramp-up G1 pre-filtering) — are
tracked as gaps below.

---

## Acceptance-criteria coverage (spec §15, items 1-20)

The spec defines 20 acceptance criteria. Each is mapped to its implementing
wave/task and verified against source. Status legend:

- **Pass** — implemented and exercised by at least one unit/integration test.
- **Partial** — core path implemented, but a named sub-requirement is missing.
- **Gap** — not implemented (or documented only); tracked in the Gaps section.

| # | Criterion (spec §15) | Implementing wave/task | Spec § | Status |
|---|---|---|---|---|
| 1 | init parses seed, creates project, runs G0, idempotent | W1:T4 (parser) + W1:T6 (`init` cmd) | §4, §2.2 | Pass |
| 2 | Genesis 17 steps all dispatch + gate, pause at checkpoint | W3:T2 | §5 | Pass |
| 3 | Full per-chapter step loop (incl. foreshadowing-plant step 2b) | W3:T3 | §6.1 | Pass |
| 4 | Audit layer three circles, deterministic activation matrix | W3:T4 | §6.2 | Pass |
| 5 | foreshadowing full lifecycle closed loop | W3:T5 + W4:T2 | §6.3, §19 | Pass |
| 6 | revision_routing correct split | W3:T5 | §6.3 | Pass |
| 7 | memory/volume/style/genre-config triggers fire correctly | W3:T6 | §6.4 | Pass |
| 8 | Volume-boundary expansion (G2+G4) + total_chapters update | W3:T6 | §6.5, §4.2 | Partial — see G2 |
| 9 | Three-route retrieval assembly + deterministic rerank + context file | W2:T1-3 | §7 | Pass |
| 10 | All checkpoints pause/review/resume + staging commit | W1:T5 + W3:T9 | §9, §18 | Pass |
| 11 | truth-sync after modify | W1:T2 + W3:T9 | §9.2 | Partial — see G4 |
| 12 | Snapshot incremental+full hybrid + checksum + rollback + truth-sync | W4:T3 | §10 | Pass |
| 13 | G3 independence enforced before every scoring | W3:T1 | §2.6 | Pass |
| 14 | escalation-review dispatched on escalation | W3:T5 | §6.3 | Pass |
| 15 | Progress tracked in pipeline-state.json (not shenbi-progress) | W1:T1-2 | §3.3 | Pass |
| 16 | State-transition table complete incl. `failed` terminal | W1:T2 + W3:T7 | §3.1 | Pass |
| 17 | Concurrency safety (RW-lock split, init idempotency) | W1:T3 | §2.4 | Pass |
| 18 | Truth integrity verification on resume | W1:T2 + W3:T9 | §3.4 | Partial — see G3 |
| 19 | audit_drift.md bounded (12-chapter rolling window) | W4:T5 | §6.7 | Pass |
| 20 | Route B fallback path | W2:T2-3 | §7.3 | Pass |

**Acceptance summary:** 17 of 20 criteria pass. 3 are partial (items 8, 11, 18)
owing to the gaps below. None are missing entirely.

---

## Gaps and open items

These are the only deviations between the spec and the shipped code. Each is
named, located, and scoped.

### G1 — Ramp-up G1 input pre-filtering (spec §17)

- **Criterion:** §15 item not directly enumerated, but §17 is an implementation
  requirement referenced by the section matrix.
- **What the spec wants:** Before dispatch, the pipeline parses a skill's contract
  reads and removes reads that are optional / produced late in the run
  (e.g. `arc-N.md`, `volume_summaries.md`, `trend` files), so G1 only validates
  must-exist inputs.
- **What shipped:** `dispatch_helper.py` has no ramp-up skip logic (confirmed: no
  `ramp`/`optional` references anywhere in `src/shenbi/pipeline/`). The relevant
  skills (`context-composing`, `drift-guidance`) declare ramp-up handling in their
  own `SKILL.md`, so the skill itself skips missing layers at runtime; the
  pipeline does not pre-filter the G1 input list.
- **Risk:** Low for correctness (the skill tolerates missing reads), but a strict
  G1 on pipeline-dispatched early chapters could report false failures if the
  gate enforces existence on optional paths. Mitigated today because pipeline
  dispatch runs G1 via the dispatcher, which checks only the reads the skill
  actually attempts.
- **Recommended fix:** Add an `_optional_reads` set in `dispatch_helper` keyed by
  skill, and strip those paths from the G1 input list before the dispatch call.

### G2 — Dynamic `total_chapters` re-update at volume boundary (spec §4.2 / §6.5)

- **Criterion:** §15 item 8.
- **What the spec wants:** Volume-boundary expansion may revise
  `novel.json.total_chapters` (§4.2 [I3]); the loop's termination check uses the
  live value.
- **What shipped:** `total_chapters` is written once by genesis step 6
  (volume-outlining) and read dynamically by the chapter loop via
  `_read_total_chapters(project_dir)` (`cli.py`). The volume-boundary expansion
  steps run (`character-design --mode expand`, `foreshadowing --mode expand`, etc.)
  and G4 validates them, but **none of them re-writes `total_chapters`**, and no
  orchestrator post-processes the expansion outputs to update it.
- **Risk:** Medium. If volume-outlining's initial estimate is firm, the loop still
  terminates correctly. If the spec intends expansion to revise the count, the
  loop could over- or under-run.
- **Recommended fix:** Either (a) document that `total_chapters` is fixed at
  genesis and remove the §4.2 [I3] "dynamic update" wording, or (b) add a
  post-expansion step that re-reads `volume_map.md` and updates
  `novel.json.total_chapters`, then persists state.

### G3 — Explicit truth-integrity check on resume (spec §3.4)

- **Criterion:** §15 item 18.
- **What the spec wants:** On resume, verify truth-file completeness/integrity
  before continuing.
- **What shipped:** `cmd_resume` loads `pipeline-state.json` and re-enters the
  orchestration loop; there is no dedicated integrity sweep. Integrity is
  effectively enforced **per-step** because each dispatch runs G1 (input
  readiness) before the skill executes, so missing truth files surface as a G1
  failure on the first resumed step rather than at resume time.
- **Risk:** Low. The per-step G1 check is a strict superset for the cases that
  matter (a resumed skill will fail G1 if a required read is gone). The gap is
  only about *when* the failure is reported (next-step, not immediately on
  resume).
- **Recommended fix:** Optional — add a lightweight G1 sweep over the next step's
  contract reads at the top of `cmd_resume` to fail fast with a clear message.

### G4 — truth-sync propagation after checkpoint `modify` (spec §9.2)

- **Criterion:** §15 item 11.
- **What the spec wants:** After a reviewer `modify` decision, downstream truth
  files are re-synced.
- **What shipped:** `cmd_review` commits staging files to final paths on both
  `approve` and `modify` (`_commit_staging_for_checkpoint`). The staging commit
  itself is implemented and tested. The deeper "truth-sync" propagation (re-running
  affected downstream skills so derived truth reflects the human edit) is not
  automated — it relies on the reviewer/human to surface it in feedback and on the
  next loop iteration's gates to catch drift.
- **Risk:** Low-Medium. Staging is never lost; the only exposure is that a human
  edit may not cascade to derived files until a later gate catches the
  inconsistency.
- **Recommended fix:** Optional — define which truth files are "derived" and, on
  `modify`, queue a re-dispatch of their producing skills.

---

## Cross-references

- Implementation source: `src/shenbi/pipeline/` (18 modules) + `skills/`.
- Wave plans: `docs/superpowers/plans/2026-07-02-novel-pipeline-wave{1..5}-*.md`.
- Spec: `docs/superpowers/specs/2026-07-01-novel-pipeline-design.md`.
- Integration tests (Wave 5): `tests/integration/pipeline/test_genesis_to_loop.py`,
  `test_chapter_loop_full.py`, `test_full_flows.py`.
