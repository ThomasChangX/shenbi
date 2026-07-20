# Spec 11: End-to-End Validation Protocol

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Validation Plan (non-repair)
> **Merged from:** `2026-07-17-end-to-end-validation-after-fixes-design.md`, `2026-07-17-fix-chapter-size-time-uncorrelated-design.md` (absorbed as performance baseline)
> **Purpose:** Define a complete verification protocol to validate all 10 consolidated specs after implementation, establish a performance baseline from chapter timing analysis, and provide regression risk mitigations with per-spec rollback instructions.

---

## 1. Executive Summary

After all 10 consolidated specs are implemented across the Shenbi pipeline, no defined verification protocol exists to confirm effectiveness and rule out regressions. This spec provides that protocol. It also establishes a performance baseline from chapter timing analysis.

> **IMPORTANT — Provenance of the timing figures in this spec:** The Pearson r = -0.002 (chapter size vs. generation time), the "35 resonance retries = 65% of time," the "79-93 min" heavy-retry range, and the "14 drafting retries = 25% of time" figures are **analytic claims carried over from the original investigation's source spec (`2026-07-17-fix-chapter-size-time-uncorrelated-design.md`), not output of any committed script.** No code in the codebase computes a Pearson correlation, and **no per-chapter timing dataset currently exists** (there is no `elapsed`/`generation_time`/`chapter_time`/`duration` field in `progress.json` or anywhere else in the repo) that would let these numbers be recomputed today. These figures are reproduced here as a *prior* to be validated; **building the per-chapter timing collection infrastructure is itself a required deliverable of this validation protocol** (see Section 2.4 and the new Stage 3 timing-instrumentation check). Until that instrumentation exists, the before/after comparison below is an analytic hypothesis, not a reproducible measurement.

With that caveat, the baseline hypothesis is: chapter size and generation time are uncorrelated (Pearson r = -0.002). The hypothesized bottleneck is retry loops -- 35 resonance retries accounting for 65% of time on the slowest chapters. Fixing root-cause G4 format conflicts (Spec 2: Output Validation) is projected to reduce heavy-retry chapters from 79-93 minutes to approximately 15 minutes.

---

## 2. Performance Baseline: Chapter Size and Time Are Uncorrelated (Analytic Prior, To Be Validated)

> **Reproducibility note:** The findings below are **analytic claims from the original investigation, not reproducible from code today.** No committed script computes the Pearson coefficient, and no per-chapter timing field (`elapsed`/`generation_time`/`chapter_time`/`duration`) exists in `progress.json` or elsewhere in the repository, so these numbers cannot currently be recomputed. Section 2.3 makes timing-instrumentation a required part of this protocol so the baseline can be re-established empirically.

### 2.1 Empirical Findings

Analysis of 56 generated chapters revealed (per the original investigation's source spec):

- **Pearson correlation coefficient r = -0.002** between chapter size (word count) and generation time. Chapter size has zero predictive power for generation time.

- **Top 5 slowest chapters (79-93 minutes):** All driven by retry loops, not text length.
  - `shenbi-review-resonance`: 35 retries (65% of total time)
  - `shenbi-chapter-drafting`: 14 retries (25% of total time)

- **Fastest chapters (10-13 minutes):** Zero retry chapters.

- **Single-point bottleneck:** `shenbi-review-resonance` retries due to G4 format conflicts between the resonance scorer's expected output format and the LLM's actual output.

### 2.2 Optimization Opportunity

Fixing the root cause of G4 format conflicts (Spec 2: Output Validation) directly eliminates the primary reason for resonance retries. Expected impact (projected against the analytic baseline above):

| Metric | Before Fix | After Fix (Projected) |
|--------|-----------|----------------------|
| Heavy-retry chapter time | 79-93 min | ~15 min |
| Resonance retry rate | ~35 retries on worst chapters | < 10% |
| Average chapter time (zero-retry baseline) | 10-13 min | 10-13 min (unchanged) |
| Average chapter time (overall) | ~25-30 min | ~15-18 min |
| Total time savings for 100 chapters | — | ~16-20 hours |

### 2.3 This Spec's Role

This spec does not contain independent fixes -- it provides the verification protocol to confirm that all other specs' fixes work as intended. The performance baseline serves as a before/after reference point for timing validation.

### 2.4 Required: Per-Chapter Timing Collection Infrastructure

Because the analytic baseline in 2.1 cannot currently be reproduced, this protocol REQUIRES building timing-collection instrumentation as a precondition for validating Section 2.2's projections. Specifically:

- Add a per-chapter timing record to `progress.json` (e.g. an `elapsed`/`generation_time` field keyed by chapter, plus per-skill and per-retry breakdown). No such field exists in the codebase today.
- Emit timing events during the chapter loop (`chapter_loop.py` / `dispatch_helper.py`) and retry loops so resonance/drafting retry counts and durations are captured.
- Persist a timing dataset sufficient to recompute the Pearson coefficient and the retry-share-of-time statistics independently of the original investigation.

Until this instrumentation exists, the r = -0.002 figure and the 65% / 25% / "79-93 min" statistics must be treated as unverified analytic claims rather than measured results. The Stage 3 smoke test includes a check that timing data has actually been recorded (see Stage 3 checklist).

---

## 3. Four-Stage Verification Protocol

### Stage 1: Unit Verification

**Goal:** Confirm all code-level changes compile and pass static analysis without regression.

**Command:**
```bash
just check
```

This runs: ruff (linting) + mypy (type checking) + basedpyright (type checking) + pytest (unit tests).

**Pass criteria:**
- Zero failures across all four tools
- All existing unit tests pass (244+ tests across `tests/unit/gates/` and `tests/unit/pipeline/`)
- No new type errors or lint violations introduced

**Key verification areas:**
- Gate modules: `g0.py`, `g1.py`, `g2.py`, `g3.py`, `g4/*.py`, `g5.py`, `g6.py`, `g7.py`
- Pipeline modules: `chapter_loop.py`, `context_assemble.py`, `dispatch_helper.py`, `review_checklist.py`, `audit_layer.py`
- New modules: `plan_skeleton.py` (if created), updated `snapshot.py` functions

### Stage 2: Mini-Pipeline (3 Chapters)

**Goal:** Verify end-to-end pipeline execution on a small scale, catching integration issues that unit tests cannot detect.

**Setup:**
```bash
uv run pipeline init mini-test --seed test-seed.md
uv run pipeline run mini-test --auto --max-chapters 3
```

**Verification checklist (per chapter):**

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Staging residue | `ls staging/` | Directory empty after each chapter |
| Context file generation | `ls context/chapter-*-context.md` | N context files for N chapters |
| Review checklist files | `ls context/review-checklist-*.json` | Delta files exist for each chapter; template exists once |
| decisions.json validity | `python -c "import json; json.load(open('decisions.json'))"` per chapter round | `json.loads()` succeeds; `model_validate()` passes |
| Revision decisions | Check `decisions.json` for each chapter | Revision decisions present for all applicable routes |
| Gate markers | Check `gate-markers/pipeline-manifest.json` | Manifest exists; all expected skills have G4 entries |
| Snapshot coverage | `ls snapshots/chapter-00[1-3]-*.json` | Snapshot exists for each chapter |
| Character archives | `ls characters/major/`, `ls characters/minor/` | Directories non-empty after Genesis |
| Volume map context | Check chapter plan content | Plan references volume_map structure |

**Pass criteria:** All checks pass for all 3 chapters. Zero staging residue. Zero JSONDecodeError in any decisions.json.

### Stage 3: Smoke Test (10 Chapters)

**Goal:** Verify quality metrics hold over a sustained run, detecting drift and cumulative issues.

**Setup:**
```bash
uv run pipeline run mini-test --auto --max-chapters 10 --resume
```

**Verification checklist:**

| Metric | Threshold | Method |
|--------|-----------|--------|
| System term density | < 30 per mille (‰) throughout all 10 chapters | Audit drift analysis on `audit_drift.md` |
| Density monotonicity | Density does not monotonically increase across chapters | Compare density trend across chapters 1-10 |
| Resonance retry rate | < 10% of chapters trigger resonance retries | Parse pipeline logs for retry events (requires timing instrumentation from Section 2.4 to also record retry counts/durations) |
| Context file coverage | 100% (10 context files for 10 chapters) | `ls context/chapter-*-context.md \| wc -l` |
| decisions.json validity | 100% (all 10 chapters have valid decisions.json) | Batch validate all decisions files |
| Protagonist presence | >= 3 mentions per chapter | grep protagonist name in each chapter |
| Word count range | [2000, 8000] per chapter | `word_count_md()` on each chapter file |
| Plan-to-content alignment | Key term match rate >= 80% with volume_map (from baseline 0%) | Compare plan terms vs chapter content terms |
| Snapshot coverage | 100% (10 snapshots for 10 chapters) | `ls snapshots/chapter-*.json \| wc -l` |
| Major character archives | >= 3 major character files created | `ls characters/major/*.md \| wc -l` |
| Per-chapter timing data | 100% (10/10 chapters have an elapsed/duration record) | Verify `progress.json` contains timing field per chapter (infrastructure from Section 2.4) |

**Additional Stage 3 checks:**
- `review-checklist-template.json` exists and is referenced by all delta files
- `bridge_tracker.md` shows updated states for bridges whose activation chapters fall within the 10-chapter range
- `character_matrix.md` has slug-based cross-references updated per chapter
- No `json.JSONDecodeError` in any pipeline log
- `pipeline-manifest.json` contains hierarchical entries for all 10 chapters

### Stage 4: Quality Gates

**Goal:** Final quality gate sweep to confirm production readiness.

**Checklist:**

| Gate | Check | Pass Criteria |
|------|-------|---------------|
| G0 | Contract calibration | All contracts valid, hashes match |
| G1 | Input readiness | All declared reads exist on disk |
| G2 | Output structure | All outputs parse correctly; `G2.meta_ratio` < 50% for all chapters |
| G3 | Scoring independence | No scoring function reads its own output |
| G4 | Skill-specific structure | No HARD G4 failures (legitimate triggers excepted); `G4.cd.major_chars` >= 3; `G4.cd.minor_chars` >= 2 |
| G5 | Coverage completeness | Audit reports cover all review skills |
| G6 | Phase transitions | All phase state transitions valid |
| G7 | Pipeline integrity | Phase state + gate markers verified end-to-end |

**Pass criteria for Stage 4:**
- No HARD G4 failures (triggered escalations are acceptable; format-driven failures are not)
- No `json.JSONDecodeError` in any pipeline log across all 10 chapters
- No staging residue at any checkpoint
- All chapter word counts within [2000, 8000] range
- Snapshot coverage: 100% (all chapters have differential snapshots)
- `just check` passes with zero failures

---

## 4. Timeline Budget

| Stage | Estimated Time | Cumulative |
|-------|---------------|-----------|
| Stage 1 (unit) | ~2 minutes | 2 minutes |
| Stage 2 (3-chapter mini-pipeline) | ~45-60 minutes (3 chapters * 15-20 min) | ~1 hour |
| Stage 3 (10-chapter smoke test) | ~2.5-3 hours (10 chapters * 15-18 min) | ~3.5-4 hours |
| Stage 4 (quality gates) | ~10 minutes | ~4 hours |
| **Total** | **~4 hours** | |

---

## 5. Regression Risk Mitigations

### 5.1 Rollback Strategy

Each consolidated spec's changes are concentrated in a small set of files. Rollback uses `git revert` on the implementing commit(s):

| Spec | Primary Files Changed | Rollback Command |
|------|----------------------|-----------------|
| Spec 1 (Truth File) | `truth_index.py`, `truth_io.py`, `state-settling` SKILL.md, `chapter_loop.py` | `git revert <commit>` |
| Spec 2 (Output Validation) | `dispatch_helper.py`, `g2.py`, `g4/decisions_validator.py`, `g4/chapter_revision.py`, `g4/review_resonance.py` | `git revert <commit>` |
| Spec 3 (Dispatch Safety) | `chapter_loop.py`, `dispatch_helper.py`, `checkpoint.py` | `git revert <commit>` |
| Spec 4 (Context Persistence) | `context_assemble.py`, `context_curation.py`, `chapter_loop.py`, `drift_detection/linguistic_drift.py` | `git revert <commit>` |
| Spec 5 (Content Quality) | `g4/chapter_drafting.py`, `chapter_loop.py`, `context-composing` SKILL.md | `git revert <commit>` |
| Spec 6 (Pipeline Architecture) | `chapter_loop.py`, `dispatch_helper.py`, SCR extractor, `context_assemble.py` | `git revert <commit>` |
| Spec 7 (Infrastructure) | `phase_runner.py`, `crash_recovery.py`, `dispatch_helper.py`, `executor.py`, `state.py` | `git revert <commit>` |
| Spec 8 (LLM Context) | `dispatch_helper.py`, `context_assemble.py`, various SKILL.md files | `git revert <commit>` |
| Spec 9 (Content Planning) | `context_assemble.py`, `plan_skeleton.py`, `character-design` SKILL.md, `chapter-drafting` SKILL.md | `git revert <commit>` |
| Spec 10 (Data Storage) | `dispatch_helper.py`, `chapter_loop.py`, `context-composing` SKILL.md, snapshot logic | `git revert <commit>` |

After any rollback, re-run Stage 1-2 verification to confirm restoration.

### 5.2 Known Risk Areas

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Old pipeline state format incompatible with new code | Medium | Stage 1 unit tests cover state loading (`test_state.py`, `test_machine.py`) |
| Content size guard (Spec 3: Dispatch Safety and File Integrity) falsely triggers on legitimate concise rewrites | Low | Threshold is conservative (20%), WARN only |
| Linguistic drift detection (Spec 4: Context Persistence) false-positives on experimental style | Low | WARN/HARD/ESCALATE three-tier; requires consecutive triggering |
| G4 feedback format examples not effective on certain LLM models | Medium | Preserve original check IDs; examples are additive, not replacement |
| Plan skeleton (Spec 9) too rigid, stifles LLM creativity | Low | Section 5 (Key Decisions) is fully LLM-generated; skeleton provides guidance only |
| Differential snapshot (Spec 10) hash mismatch on legitimate file updates | Low | Hash verification is WARN-level only; truth file content is fully backed up |

---

## 6. Validation Checklist (Comprehensive)

### Pre-Validation

- [ ] All 10 consolidated specs have implementation complete
- [ ] `just check` passes with zero failures on implementation branch
- [ ] Test seed document (`test-seed.md`) is ready and representative
- [ ] Pipeline init succeeds: `uv run pipeline init validation-run --seed test-seed.md`

### Stage 1: Unit

- [ ] `ruff check` -- zero errors
- [ ] `mypy` -- zero errors
- [ ] `basedpyright` -- zero errors
- [ ] `pytest` -- zero failures

### Stage 2: Mini-Pipeline (3 Chapters)

- [ ] Chapter 1 completes with all audits + revision
- [ ] Chapter 2 completes with all audits + revision
- [ ] Chapter 3 completes with all audits + revision
- [ ] Zero staging residue after each chapter
- [ ] `progress.json` updated after each chapter
- [ ] `context/` has 3 context files
- [ ] `context/review-checklist-template.json` exists
- [ ] `context/review-checklist-chapter-[1-3].json` exist
- [ ] `decisions.json` valid for all 3 chapters
- [ ] `gate-markers/pipeline-manifest.json` contains hierarchical entries
- [ ] `snapshots/` has 3 differential snapshots (`.json` format, not `.md`)
- [ ] `characters/major/` non-empty after Genesis
- [ ] `characters/minor/` non-empty after Genesis
- [ ] Chapter plans reference volume_map structure

### Stage 3: Smoke Test (10 Chapters)

- [ ] All 10 chapters complete
- [ ] System term density < 30 per mille in all chapters
- [ ] Density does not monotonically increase
- [ ] Resonance retry rate < 10%
- [ ] Per-chapter timing data recorded for all 10 chapters (`progress.json` timing field exists; Section 2.4 instrumentation built)
- [ ] Context file coverage: 100% (10/10)
- [ ] decisions.json validity: 100% (10/10)
- [ ] Protagonist presence: >= 3 mentions per chapter
- [ ] Word count: [2000, 8000] for all chapters
- [ ] Plan-to-content key term match >= 80%
- [ ] Snapshot coverage: 100% (10/10)
- [ ] Major character archives: >= 3
- [ ] `bridge_tracker.md` updates for bridges in activation range
- [ ] `character_matrix.md` slug references updated
- [ ] No `json.JSONDecodeError` in pipeline logs

### Stage 4: Quality Gates

- [ ] G0: all contract hashes match
- [ ] G1: all declared reads exist on disk
- [ ] G2: all outputs parse; `G2.meta_ratio` < 50% for all chapters
- [ ] G3: no scoring function reads its own output
- [ ] G4: no HARD failures (legitimate triggers excepted); `G4.cd.major_chars` >= 3; `G4.cd.minor_chars` >= 2
- [ ] G5: audit report coverage complete
- [ ] G6: all phase state transitions valid
- [ ] G7: phase state + gate markers verified

### Post-Validation

- [ ] Performance: average chapter time < 18 minutes (measured from timing instrumentation built in Section 2.4; the "~25-30 min" baseline is an analytic prior from the original investigation, not a reproducible measurement, and must be re-established empirically before comparison)
- [ ] No regressions detected vs pre-fix baseline (baseline re-measured using the new timing instrumentation)
- [ ] All verification criteria from merged source specs satisfied

---

## 7. Dependencies

This spec depends on all 10 other consolidated specs being fully implemented. It is the final verification gate before declaring the fix cycle complete.

```
Spec 1  (Truth File and State Accumulation)
Spec 2  (Output Validation and Format Enforcement) ← directly enables performance improvement
Spec 3  (Dispatch Safety and File Integrity)
Spec 4  (Context Persistence and Linguistic Drift Prevention)
Spec 5  (Content Quality Gates and Review Optimization)
Spec 6  (Pipeline Architecture Optimization)
Spec 7  (Pipeline Infrastructure and Resilience)
Spec 8  (LLM Context Engineering)
Spec 9  (Content Planning and Deliverable Design)
Spec 10 (Data Storage Optimization)
  └── This Spec (End-to-End Validation Protocol)
```

The performance improvement projected in Section 2.2 is primarily dependent on Spec 2 (Output Validation and Format Enforcement) eliminating the retry bottleneck that the original investigation attributed to ~65% of time on the slowest chapters (an analytic claim -- see Section 2.1/2.4 reproducibility note -- to be re-measured via the timing instrumentation built under this protocol). Without Spec 2, the ~15-minute target for heavy-retry chapters is not achievable.

---

## 8. Reference: Source Specs Absorbed

| Source Spec | Absorbed Into | Role in This Spec |
|-------------|---------------|-------------------|
| `2026-07-17-end-to-end-validation-after-fixes-design.md` | This Spec | Stage definitions, verification checklist, rollback plan |
| `2026-07-17-fix-chapter-size-time-uncorrelated-design.md` | This Spec | Performance baseline (Section 2), timing targets -- NOTE: its findings (r=-0.002, 65%/25% retry share, 79-93 min) are analytic claims, not reproducible from code; Section 2.4 requires building timing instrumentation to re-verify them |

---

## 9. Original Code Mapping

This consolidated spec merges the following original issue codes:

| Original Issue Code | Description | Section in This Spec |
|---------------------|-------------|---------------------|
| `validation` | End-to-end validation protocol after all fixes | 3, 4, 5, 6 |
| `chapter-size-time` | Chapter size and generation time are uncorrelated (performance baseline; analytic prior to be re-verified via Section 2.4 timing instrumentation) | 2 |
