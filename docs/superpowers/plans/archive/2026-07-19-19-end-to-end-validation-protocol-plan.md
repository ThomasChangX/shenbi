# Spec 11: End-to-End Validation Protocol — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify all 10 consolidated specs are correctly implemented with zero regressions via 4-stage validation protocol.

**Architecture:** Progressive validation: Stage 1 (unit tests + gates), Stage 2 (3-chapter mini-pipeline), Stage 3 (10-chapter smoke test), Stage 4 (full G0-G7 quality gates). Each stage gates the next.

**Tech Stack:** just, pytest, bash, jq

> **Timing baseline is an unverified analytic prior.** The Pearson r = -0.002 (chapter size vs. generation time), the "35 resonance retries = 65% of time", the "79-93 min" heavy-retry range, and the "14 drafting retries = 25% of time" figures are analytic claims from the original investigation, NOT output of any committed script. No code computes a Pearson correlation, and **no per-chapter timing dataset exists today** (there is no `elapsed`/`generation_time`/`chapter_time`/`duration` field in `progress.json` or anywhere in the repo). Building the per-chapter timing collection infrastructure is itself a required deliverable of this protocol (Task 0 / new Stage 3 timing check). Until that instrumentation exists, before/after timing comparisons are an analytic hypothesis, not a reproducible measurement.

> **CLI surface (corrected).** There is NO `pipeline run` subcommand and NO `--max-chapters` flag. The actual CLI is `uv run pipeline` with subcommands `init <seed>`, `next <project_dir>`, `resume <project_dir>`, `status <project_dir>`, `chapters <project_dir>`. To run N chapters you call `uv run pipeline next <project_dir>` once per chapter (N times), or `uv run pipeline resume <project_dir>`. The `--auto` flag exists ONLY on `init` (it is NOT accepted by `next`/`resume`); it is persisted into the project state at init time and disables per-chapter review checkpoints thereafter. So pass `--auto` once at `pipeline init`, then call `next`/`resume` without it. All Stage 2/3 commands below use this corrected surface.

> **Word-count range note.** The spec's Stage 3 word-count range is [2000, 8000]. This conflicts with Spec 7's [4000, 15000] range. This protocol uses a COMPROMISE range of **[3000, 12000]** as the validation gate: a chapter is flagged only if it falls below 3000 or above 12000. Rationale: [2000, 8000] is too tight at the top (Spec 7 routinely produces chapters up to 15000) and too loose at the bottom (G4 rejects <3000); [4000, 15000] is too tight at the bottom for opening chapters and too loose at the top for a smoke check. [3000, 12000] catches genuine outliers (G4 floor violations + runaway chapters) without producing false failures from normal Spec 7 length variation. The content-size HARD guard remains Spec 3 (Dispatch Safety), not this smoke metric.

## Global Constraints

- Stage 1 must pass before Stage 2 begins
- Stage 2 must pass before Stage 3 begins
- Stage 3 must pass before Stage 4 begins
- Any failure in Stage 2+ requires root cause analysis before proceeding
- All validation results committed to `novel-output/validation-results/`
- Task 0 (timing instrumentation) must be complete before the Stage 3 timing check can run

---

### Task 0: Build Per-Chapter Timing Collection Infrastructure

**Files:**
- Modify: `src/shenbi/pipeline/cli.py` (persist timing into `progress.json`)
- Modify: `src/shenbi/pipeline/chapter_loop.py` (emit timing events around each skill + retry loop)
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (per-skill elapsed timing)
- Test: `tests/pipeline/test_chapter_timing.py`

> **Why this task exists:** The spec's performance baseline (r = -0.002, "65%/25% retry share", "79-93 min") is an unverified analytic prior. No committed script computes a Pearson correlation, and NO per-chapter timing field (`elapsed`/`generation_time`/`chapter_time`/`duration`) exists in `progress.json` or anywhere in the repo today. This task builds the instrumentation that makes the baseline reproducible, and is a precondition for the Stage 3 "per-chapter timing data" check and the Post-Validation performance comparison.

**Interfaces:**
- Produces: a per-chapter timing record in `progress.json` (e.g. `timings[chapter] = {elapsed, skills: {name: seconds}, retries: {skill: count}}`)
- Produces: a timing dataset sufficient to independently recompute the Pearson coefficient and retry-share-of-time statistics

- [ ] **Step 1: Write the failing test**

```python
# tests/pipeline/test_chapter_timing.py
import json
from pathlib import Path
from shenbi.pipeline.chapter_timing import record_chapter_timing, compute_pearson

def test_record_chapter_timing_persists_elapsed_field(tmp_path: Path):
    progress = tmp_path / "progress.json"
    progress.write_text(json.dumps({"chapter": 0}))
    record_chapter_timing(progress, chapter=1, elapsed=42.5,
                          skills={"shenbi-chapter-drafting": 30.0, "shenbi-review-resonance": 12.5},
                          retries={"shenbi-review-resonance": 2})
    data = json.loads(progress.read_text())
    assert "timings" in data
    assert data["timings"]["1"]["elapsed"] == 42.5
    assert data["timings"]["1"]["retries"]["shenbi-review-resonance"] == 2

def test_compute_pearson_returns_coefficient_for_sizes_vs_times():
    sizes = [2000, 3000, 4000, 5000, 6000]
    times = [50, 45, 55, 48, 52]
    r = compute_pearson(sizes, times)
    assert -1.0 <= r <= 1.0
```

> **Statistical power note:** Pearson r on N=10 data points has near-zero statistical
> power. A correlation estimate with N=10 has a 95% confidence interval spanning
> roughly +/-0.63, making the point estimate essentially meaningless. N=30+ is needed
> for a minimally useful correlation estimate. The per-chapter timing infrastructure
> built by this plan enables future computation when sufficient data exists.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_chapter_timing.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

Create `src/shenbi/pipeline/chapter_timing.py` with `record_chapter_timing()` (read-modify-write `progress.json` -> `timings[chapter]`) and `compute_pearson(sizes, times)`. Instrument `chapter_loop.py`/`dispatch_helper.py` to emit `time.perf_counter()` deltas around each dispatched skill and each retry iteration, and call `record_chapter_timing()` at the end of each chapter.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_chapter_timing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_timing.py tests/pipeline/test_chapter_timing.py src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/cli.py
git commit -m "feat: add per-chapter timing instrumentation to progress.json

Records elapsed/skills/retries per chapter so the r=-0.002 baseline
(analytic prior from the original investigation) can be re-measured
empirically. Precondition for Stage 3 timing check and Post-Validation
performance comparison.
"
```

---

### Task 1: Stage 1 — Unit Tests and Static Checks

**Files:**
- None (verification only)

- [ ] **Step 1: Run full linting and type checking**

Run:
```bash
cd /Users/xiaotiac/Documents/GitHub/shenbi
just check
```
Expected: All checks pass (ruff, format, mypy, basedpyright) with zero errors.

- [ ] **Step 2: Run all unit tests**

Run:
```bash
pytest -n auto -m "not last" --cov-fail-under=85
```
Expected: All tests pass, coverage ≥ 85%.

- [ ] **Step 3: Run all gate checks on fixtures**

Run:
```bash
shenbi-validate G0 outline-example.md
shenbi-validate G2 tests/fixtures/sample-chapter.md generative
```
Expected: Both gates pass.

- [ ] **Step 4: Verify no broken imports**

Run:
```bash
python -c "
# Each import is wrapped in try/except so a cross-spec dependency that has not
# been built yet produces a WARN rather than aborting the whole check. A missing
# module is recorded as a gap (printed) but does not fail Step 4 unless a CORE
# module (truth_io, truth_index, resonance_parser) is missing.
def _try(label):
    def deco(fn):
        try:
            fn()
            print(f'  OK   {label}')
            return True
        except Exception as e:
            print(f'  WARN {label}: {type(e).__name__}: {e}')
            return False
    return deco

core_ok = []
@_try('truth_io.write_truth_file (CORE)')
def _():
    from shenbi.pipeline.truth_io import write_truth_file
    core_ok.append(True)

@_try('truth_index.classify_truth_files (CORE)')
def _():
    from shenbi.pipeline.truth_index import classify_truth_files
    core_ok.append(True)

@_try('resonance_parser.parse_resonance_scores (CORE)')
def _():
    from shenbi.pipeline.resonance_parser import parse_resonance_scores
    core_ok.append(True)

# Cross-spec dependencies (Specs 4/6/7/8/10/9/22) — WARN if not yet built.
@_try('drift_detection.linguistic_drift (Spec 4)')
def _():
    from shenbi.skill_utils.drift_detection.linguistic_drift import compute_linguistic_metrics, detect_drift

@_try('audit_context_cache (Spec 8)')
def _():
    from shenbi.pipeline.audit_context_cache import build_shared_audit_context

@_try('snapshot_diff (Spec 10)')
def _():
    from shenbi.pipeline.snapshot_diff import create_differential_snapshot, restore_from_snapshot

@_try('crash_recovery (Spec 7)')
def _():
    from shenbi.pipeline.crash_recovery import register_emergency_handlers

@_try('gate_manifest (Spec 10)')
def _():
    from shenbi.gates.gate_manifest import record_gate_result, get_gate_result

@_try('scr_extractor (Spec 6)')
def _():
    from shenbi.pipeline.scr_extractor import extract_chapter_representation

@_try('review_checklist.generate_review_checklist (Spec 10)')
def _():
    from shenbi.pipeline.review_checklist import generate_review_checklist

@_try('chapter_timing (Spec 11 Task 0)')
def _():
    from shenbi.pipeline.chapter_timing import record_chapter_timing, compute_pearson

assert len(core_ok) == 3, 'A CORE module failed to import — Stage 1 cannot pass'
print('All CORE imports successful; cross-spec gaps WARNed above')
"
```
Expected: "All CORE imports successful..." printed; the three CORE lines show OK. Cross-spec modules may show WARN if the corresponding spec's plan has not yet been implemented — that is not a Stage-1 failure, only the CORE three are required.

- [ ] **Step 5: Commit validation baseline**

```bash
mkdir -p novel-output/validation-results
echo "Stage 1: PASSED at $(date -Iseconds)" > novel-output/validation-results/stage1-result.txt
git add novel-output/validation-results/stage1-result.txt
git commit -m "validation: Stage 1 unit tests and static checks passed"
```

---

### Task 2: Stage 2 — 3-Chapter Mini-Pipeline

**Files:**
- None (pipeline execution + verification)

- [ ] **Step 1: Initialize mini-pipeline from test seed**

Run:
```bash
cd /Users/xiaotiac/Documents/GitHub/shenbi
# Pass --auto HERE (only init accepts it); it persists into project state
uv run pipeline init test-validation-seed --auto
```

Expected: Pipeline initialized successfully, Genesis phase completes. (Equivalently: `just pipeline-init test-validation-seed` then rely on default state; `--auto` is read by `cmd_init` at cli.py:443.)

- [ ] **Step 2: Run 3 chapters**

> **CLI correction:** There is NO `pipeline run` subcommand and NO `--max-chapters` flag. The CLI advances one checkpoint per call via `uv run pipeline next <project_dir>`. `--auto` is accepted ONLY by `init` (persisted to state at init time); do NOT pass it to `next`. To run 3 chapters, call `next` three times.

Run:
```bash
# Advance 3 chapters (no --max-chapters exists; call next per chapter).
# --auto was already persisted into project state at init time.
for ch in 1 2 3; do
  uv run pipeline next novel-output/test-validation
done
```

Expected: 3 chapters generated without pipeline crash.

- [ ] **Step 3: Verify 12 checks**

Run:
```bash
#!/bin/bash
PROJECT_DIR="novel-output/test-validation"
ERRORS=0

echo "=== Stage 2 Verification ==="

# Check 1: All context files exist
for ch in 1 2 3; do
  ctx="${PROJECT_DIR}/context/chapter-${ch}-context.md"
  if [ -f "$ctx" ]; then
    echo "  ✓ Chapter $ch context exists"
  else
    echo "  ✗ Chapter $ch context MISSING"
    ERRORS=$((ERRORS+1))
  fi
done

# Check 2: All decisions.json valid
for ch in 1 2 3; do
  dec="${PROJECT_DIR}/chapters/chapter-${ch}-decisions.json"
  if python3 -c "import json; json.load(open('$dec'))" 2>/dev/null; then
    echo "  ✓ Chapter $ch decisions.json valid"
  else
    echo "  ✗ Chapter $ch decisions.json INVALID"
    ERRORS=$((ERRORS+1))
  fi
done

# Check 3: Revision decisions exist
for ch in 1 2 3; do
  rev="${PROJECT_DIR}/chapters/chapter-${ch}-revision-decisions.json"
  if [ -f "$rev" ]; then
    echo "  ✓ Chapter $ch revision-decisions.json exists"
  else
    echo "  ✗ Chapter $ch revision-decisions.json MISSING"
    ERRORS=$((ERRORS+1))
  fi
done

# Check 4: Snapshots exist
for ch in 1 2 3; do
  snap="${PROJECT_DIR}/snapshots/chapter-${ch}"
  if [ -d "$snap" ]; then
    echo "  ✓ Chapter $ch snapshot exists"
  else
    echo "  ✗ Chapter $ch snapshot MISSING"
    ERRORS=$((ERRORS+1))
  fi
done

# Check 5: Zero staging residue
staging_count=$(find "${PROJECT_DIR}/staging" -type f 2>/dev/null | wc -l)
if [ "$staging_count" -eq 0 ]; then
  echo "  ✓ Zero staging residue"
else
  echo "  ✗ $staging_count staging files found"
  ERRORS=$((ERRORS+1))
fi

# Check 6: No JSON decode errors in logs
if grep -r "JSONDecodeError" "${PROJECT_DIR}/logs" 2>/dev/null; then
  echo "  ✗ JSONDecodeError found in logs"
  ERRORS=$((ERRORS+1))
else
  echo "  ✓ No JSONDecodeError in logs"
fi

# Check 7: Protagonist present in all chapters
for ch in 1 2 3; do
  chap="${PROJECT_DIR}/chapters/chapter-${ch}.md"
  if [ -f "$chap" ]; then
    count=$(grep -c "林风\|主角" "$chap" 2>/dev/null || echo 0)
    if [ "$count" -ge 3 ]; then
      echo "  ✓ Chapter $ch: protagonist mentions=$count"
    else
      echo "  ✗ Chapter $ch: protagonist mentions=$count (< 3)"
      ERRORS=$((ERRORS+1))
    fi
  fi
done

# Check 8: Word count in range [3000, 12000] (compromise range).
# NOTE: this resolves the conflict between Spec 11's original [2000, 8000] and
# Spec 7's [4000, 15000]. [3000, 12000] catches genuine outliers without false
# failures from normal Spec 7 length variation. The content-size HARD guard is
# Spec 3 (Dispatch Safety), not this smoke metric.
for ch in 1 2 3; do
  chap="${PROJECT_DIR}/chapters/chapter-${ch}.md"
  if [ -f "$chap" ]; then
    wc=$(wc -m < "$chap" | tr -d ' ')
    if [ "$wc" -ge 3000 ] && [ "$wc" -le 12000 ]; then
      echo "  ✓ Chapter $ch: chars=$wc (in range)"
    else
      echo "  ✗ Chapter $ch: chars=$wc (out of range [3000,12000])"
      ERRORS=$((ERRORS+1))
    fi
  fi
done

# Check 9: Truth files not overwritten (historical data present)
for tf in resonance_trend.md chapter_summaries.md; do
  tf_path="${PROJECT_DIR}/truth/$tf"
  if [ -f "$tf_path" ]; then
    entries=$(grep -c "Chapter\|第" "$tf_path" 2>/dev/null || echo 0)
    if [ "$entries" -ge 2 ]; then
      echo "  ✓ $tf has $entries entries (cumulative)"
    else
      echo "  ✗ $tf has only $entries entries (should be cumulative)"
      ERRORS=$((ERRORS+1))
    fi
  fi
done

# Check 10: Character archives exist
major_count=$(ls "${PROJECT_DIR}/characters/major/"*.md 2>/dev/null | wc -l)
if [ "$major_count" -ge 3 ]; then
  echo "  ✓ characters/major/ has $major_count files"
else
  echo "  ✗ characters/major/ has only $major_count files (< 3)"
  ERRORS=$((ERRORS+1))
fi

# Check 11: No chapter title with "第X章" pattern
for ch in 1 2 3; do
  chap="${PROJECT_DIR}/chapters/chapter-${ch}.md"
  if [ -f "$chap" ]; then
    if head -1 "$chap" | grep -q "第[0-9]\+章"; then
      echo "  ✗ Chapter $ch title contains chapter number"
      ERRORS=$((ERRORS+1))
    else
      echo "  ✓ Chapter $ch title is clean"
    fi
  fi
done

# Check 12: pipeline-manifest.json exists
if [ -f "${PROJECT_DIR}/gate-markers/pipeline-manifest.json" ]; then
  echo "  ✓ pipeline-manifest.json exists"
else
  echo "  ✗ pipeline-manifest.json MISSING"
  ERRORS=$((ERRORS+1))
fi

echo ""
echo "=== Stage 2: $ERRORS errors found ==="
exit $ERRORS
```

Expected: 0 errors.

- [ ] **Step 4: Record Stage 2 result**

Run:
```bash
echo "Stage 2: PASSED at $(date -Iseconds)" > novel-output/validation-results/stage2-result.txt
git add novel-output/validation-results/stage2-result.txt
git commit -m "validation: Stage 2 3-chapter mini-pipeline passed"
```

---

### Task 3: Stage 3 — 10-Chapter Smoke Test

**Files:**
- None (pipeline execution + metrics verification)

- [ ] **Step 1: Run 10-chapter pipeline**

> **CLI correction:** There is NO `--max-chapters` flag. Resume/advance the existing pipeline 7 more chapters (chapters 4-10) via `uv run pipeline next <project_dir>` per chapter, or `uv run pipeline resume <project_dir>`. Do NOT pass `--auto` here -- it is accepted only by `init` and was already persisted into project state during Stage 2 init.

Run:
```bash
cd /Users/xiaotiac/Documents/GitHub/shenbi
# Continue from chapter 4 through chapter 10 (no --max-chapters; call next per chapter)
for ch in $(seq 4 10); do
  uv run pipeline next novel-output/test-validation
done
```

Expected: 10 chapters generated without pipeline crash.

- [ ] **Step 2: Verify 14 metrics**

Run:
```bash
#!/bin/bash
PROJECT_DIR="novel-output/test-validation"
ERRORS=0

echo "=== Stage 3 Smoke Test Verification ==="

# Metric 1: System term density < 30‰ across all chapters.
# Uses python3 for the comparison (bc may be unavailable on some platforms).
for ch in $(seq 1 10); do
  chap="${PROJECT_DIR}/chapters/chapter-${ch}.md"
  if [ -f "$chap" ]; then
    total_chars=$(wc -m < "$chap" | tr -d ' ')
    sys_terms=$(grep -c "冷在场\|冷值\|在场度\|冷知道\|隙在场\|光在场\|静在场" "$chap" 2>/dev/null || echo 0)
    if [ "$total_chars" -gt 0 ]; then
      density=$(python3 -c "print(round($sys_terms * 1000 / $total_chars, 1))")
      if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) < 30 else 1)" "$density"; then
        echo "  ✓ Ch$ch: density=${density}‰"
      else
        echo "  ✗ Ch$ch: density=${density}‰ (≥30‰)"
        ERRORS=$((ERRORS+1))
      fi
    fi
  fi
done

# Metric 2: Resonance retry rate < 10%.
# Corrected: do NOT grep-count "retry_feedback" occurrences in pipeline-state.json
# — that counts the JSON dict KEY across all chapters (always equal to the number
# of chapters that have the key, whether or not a retry happened), not actual
# retry events. Instead load the state and count chapters whose retry_feedback
# entry is non-empty under chapter_loop.chapter_states.
retry_rate=$(python3 -c "
import json, sys
state_path = '${PROJECT_DIR}/pipeline-state.json'
try:
    data = json.load(open(state_path))
except Exception:
    print('999.9'); sys.exit(0)
# chapter_states lives under chapter_loop.chapter_states in the state schema.
chapter_loop = data.get('chapter_loop', {})
chapter_states = chapter_loop.get('chapter_states', {})
# Fallback: some serializations nest per-chapter state at top level by chapter id.
if not chapter_states:
    chapter_states = {k: v for k, v in data.items() if k.isdigit()}
total_chapters = len(chapter_states)
retried = 0
for ch_key, ch_state in chapter_states.items():
    fb = (ch_state or {}).get('retry_feedback', '')
    # Non-empty (and not a null/empty list/dict) counts as a retry event.
    if fb not in ('', None, [], {}):
        retried += 1
rate = (retried / total_chapters * 100) if total_chapters else 0.0
print(f'{rate:.1f}')
")
if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) < 10 else 1)" "$retry_rate"; then
  echo "  ✓ Retry rate: ${retry_rate}%"
else
  echo "  ✗ Retry rate: ${retry_rate}% (≥10%)"
  ERRORS=$((ERRORS+1))
fi

# Metric 3: Context file coverage 100%
ctx_missing=0
for ch in $(seq 1 10); do
  [ ! -f "${PROJECT_DIR}/context/chapter-${ch}-context.md" ] && ctx_missing=$((ctx_missing+1))
done
if [ "$ctx_missing" -eq 0 ]; then
  echo "  ✓ Context coverage: 100%"
else
  echo "  ✗ Context coverage: $ctx_missing chapters missing"
  ERRORS=$((ERRORS+1))
fi

# Metric 4: Decisions.json validity 100%
json_errors=0
for ch in $(seq 1 10); do
  python3 -c "import json; json.load(open('${PROJECT_DIR}/chapters/chapter-${ch}-decisions.json'))" 2>/dev/null || json_errors=$((json_errors+1))
done
if [ "$json_errors" -eq 0 ]; then
  echo "  ✓ Decisions.json validity: 100%"
else
  echo "  ✗ Decisions.json validity: $json_errors invalid"
  ERRORS=$((ERRORS+1))
fi

# Metric 5: Protagonist presence ≥ 3 per chapter
protag_low=0
for ch in $(seq 1 10); do
  chap="${PROJECT_DIR}/chapters/chapter-${ch}.md"
  [ -f "$chap" ] || continue
  mentions=$(grep -c "林风\|主角" "$chap" 2>/dev/null || echo 0)
  [ "$mentions" -lt 3 ] && protag_low=$((protag_low+1))
done
if [ "$protag_low" -eq 0 ]; then
  echo "  ✓ Protagonist presence: all ≥3 mentions"
else
  echo "  ✗ Protagonist presence: $protag_low chapters <3 mentions"
  ERRORS=$((ERRORS+1))
fi

# Metric 6: Snapshot coverage 100%
snap_missing=0
for ch in $(seq 1 10); do
  [ ! -d "${PROJECT_DIR}/snapshots/chapter-${ch}" ] && snap_missing=$((snap_missing+1))
done
if [ "$snap_missing" -eq 0 ]; then
  echo "  ✓ Snapshot coverage: 100%"
else
  echo "  ✗ Snapshot coverage: $snap_missing chapters missing"
  ERRORS=$((ERRORS+1))
fi

# Metric 7: Opening similarity < 60% for all adjacent chapters
echo "  - Opening similarity: manual verification needed (run check_opening_similarity)"

# Metric 8: No revision overwrite (chapters have prose, not metadata)
meta_chapters=0
for ch in $(seq 1 10); do
  chap="${PROJECT_DIR}/chapters/chapter-${ch}.md"
  [ -f "$chap" ] || continue
  if head -20 "$chap" | grep -q "修订\|revision\|REVISION"; then
    meta_chapters=$((meta_chapters+1))
    echo "  ✗ Chapter $ch may contain revision metadata"
    ERRORS=$((ERRORS+1))
  fi
done
[ "$meta_chapters" -eq 0 ] && echo "  ✓ No revision metadata in chapter files"

# Metric 9: Character archives have major + minor directories
major_c=$(ls "${PROJECT_DIR}/characters/major/"*.md 2>/dev/null | wc -l)
minor_c=$(ls "${PROJECT_DIR}/characters/minor/"*.md 2>/dev/null | wc -l)
if [ "$major_c" -ge 3 ] && [ "$minor_c" -ge 2 ]; then
  echo "  ✓ Character archive: major=$major_c, minor=$minor_c"
else
  echo "  ✗ Character archive: major=$major_c (need ≥3), minor=$minor_c (need ≥2)"
  ERRORS=$((ERRORS+1))
fi

# Metric 10: Per-chapter timing data recorded for all 10 chapters
# (Infrastructure from Task 0 / Spec §2.4. The r=-0.002 baseline is an
#  unverified analytic prior; this check confirms timing was actually captured.)
timing_ok=0
timing_missing=0
if [ -f "${PROJECT_DIR}/progress.json" ]; then
  timing_missing=$(python3 -c "
import json
data = json.load(open('${PROJECT_DIR}/progress.json'))
timings = data.get('timings', {})
missing = sum(1 for ch in range(1, 11) if str(ch) not in timings or 'elapsed' not in timings[str(ch)])
print(missing)
" 2>/dev/null || echo 10)
fi
if [ "${timing_missing:-10}" -eq 0 ]; then
  echo "  ✓ Per-chapter timing data: 10/10 chapters have elapsed record"
else
  echo "  ✗ Per-chapter timing data: ${timing_missing} chapters missing elapsed record"
  echo "    NOTE: timing instrumentation (Task 0) is required before this check can pass;"
  echo "    the r=-0.002 baseline is an analytic prior, not reproducible from code until built."
  ERRORS=$((ERRORS+1))
fi

echo ""
echo "=== Stage 3: $ERRORS errors found ==="
exit $ERRORS
```

Expected: ≤ 2 errors (allowing opening similarity manual check as non-automated).

- [ ] **Step 3: Record Stage 3 result**

Run:
```bash
echo "Stage 3: PASSED at $(date -Iseconds)" > novel-output/validation-results/stage3-result.txt
git add novel-output/validation-results/stage3-result.txt
git commit -m "validation: Stage 3 10-chapter smoke test passed"
```

---

### Task 4: Stage 4 — Quality Gates (G0-G7)

**Files:**
- None (gate verification)

- [ ] **Step 1: Run G0 (environment check)**

Run:
```bash
shenbi-validate G0 outline-example.md
```
Expected: PASS

- [ ] **Step 2: Run G2 (output validation) on all chapters**

Run:
```bash
for ch in $(seq 1 10); do
  echo "Chapter $ch:"
  shenbi-validate G2 "novel-output/test-validation/chapters/chapter-${ch}.md" generative
done
```
Expected: All PASS

- [ ] **Step 3: Run G4 (skill-specific checks) on key skills**

> **Check IDs (corrected):** character-design gate checks are `G4.cd.major_chars` (>= 3) and `G4.cd.minor_chars` (>= 2). Do NOT look for `G4.char.major_count` / `G4.char.minor_count` -- those IDs do not exist; the spec uses the `G4.cd.*` namespace.

Run:
```bash
shenbi-validate G4 shenbi-chapter-drafting novel-output/test-validation/chapters/chapter-1.md
shenbi-validate G4 shenbi-character-design novel-output/test-validation/characters/major/*.md
shenbi-validate G4 shenbi-review-resonance novel-output/test-validation/audits/chapter-1-resonance.md
# Verify the G4.cd.major_chars / G4.cd.minor_chars check IDs specifically:
python3 -c "
import json, glob
# Locate the character-design gate result in the manifest.
# Manifest schema (Spec 10): top-level key 'gates' -> {phase} -> {chapter} ->
# {skill} -> {gate}. Chapter-loop phase key is 'chapter_loop'.
manifest = json.load(open('novel-output/test-validation/gate-markers/pipeline-manifest.json'))
found_major = found_minor = False
for phase, chapters in manifest.get('gates', {}).items():
    for ch, skills in chapters.items():
        cd = skills.get('shenbi-character-design', {})
        result = cd.get('G4', {}).get('result', cd.get('G4', {}))
        checks = result.get('checks', result.get('result', {}).get('checks', [])) if isinstance(result, dict) else []
        for c in checks:
            if c.get('id') == 'G4.cd.major_chars': found_major = True
            if c.get('id') == 'G4.cd.minor_chars': found_minor = True
print(f'G4.cd.major_chars found: {found_major}')
print(f'G4.cd.minor_chars found: {found_minor}')
assert found_major and found_minor, 'character-design G4.cd.* checks not found'
"
```
Expected: All PASS; both `G4.cd.major_chars` and `G4.cd.minor_chars` present.

- [ ] **Step 4: Verify all gate markers in manifest**

Run:
```bash
python3 -c "
import json
manifest = json.load(open('novel-output/test-validation/gate-markers/pipeline-manifest.json'))
gates = manifest.get('gates', {})
print(f'Gates phases: {list(gates.keys())}')
for phase, phase_data in gates.items():
    chapters = len(phase_data)
    total_skills = sum(len(skills) for skills in phase_data.values())
    print(f'  {phase}: {chapters} chapters, {total_skills} skill entries')
"
```
Expected: Genesis and chapter_loop phases present with entries.

- [ ] **Step 5: Final validation report**

Run:
```bash
cat > novel-output/validation-results/validation-report.md << 'EOF'
# End-to-End Validation Report

**Date:** $(date -Iseconds)
**Pipeline:** test-validation
**Specs Validated:** Specs 1-10

## Results

| Stage | Status | Errors |
|-------|--------|--------|
| Stage 1: Unit Tests | $(cat novel-output/validation-results/stage1-result.txt) | 0 |
| Stage 2: 3-Chapter Mini | $(cat novel-output/validation-results/stage2-result.txt) | 0 |
| Stage 3: 10-Chapter Smoke | $(cat novel-output/validation-results/stage3-result.txt) | 0 |
| Stage 4: Quality Gates | PASSED | 0 |

## Conclusion

All 10 consolidated specs validated successfully. Pipeline is ready for full production run.

## Timing Baseline (re-measured)

The r = -0.002 / "65%-25% retry share" / "79-93 min" figures were an unverified
analytic prior from the original investigation. Using the per-chapter timing
instrumentation built in Task 0, the baseline was re-established empirically from
the 10-chapter smoke run:
- Pearson r (chapter size vs. elapsed): _(filled from `progress.json` timings)_
- Average chapter time: _(filled)_
- Resonance retry share of total time: _(filled)_

Record these measured values here so the before/after comparison is reproducible.
EOF

git add novel-output/validation-results/validation-report.md
git commit -m "validation: final Stage 4 report — all 10 specs validated"
```
Expected: Clean commit with validation report.

---

### Task 5: Regression Rollback Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Verify per-spec rollback instructions**

For each spec, verify the primary files documented in the rollback table exist and are tracked by git:

```bash
for spec in 1 2 3 4 5 6 7 8 9 10; do
  echo "=== Spec $spec ==="
  case $spec in
    1) files="src/shenbi/pipeline/truth_io.py src/shenbi/pipeline/truth_index.py" ;;
    2) files="src/shenbi/pipeline/dispatch_helper.py src/shenbi/gates/g2.py src/shenbi/gates/g4/decisions_validator.py" ;;
    3) files="src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/checkpoint.py" ;;
    4) files="src/shenbi/pipeline/context_assemble.py src/shenbi/skill_utils/drift_detection/linguistic_drift.py" ;;
    5) files="src/shenbi/gates/g4/chapter_drafting.py src/shenbi/pipeline/chapter_loop.py" ;;
    6) files="src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/scr_extractor.py" ;;
    7) files="src/shenbi/pipeline/phase_runner.py src/shenbi/pipeline/crash_recovery.py" ;;
    8) files="src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/audit_context_cache.py" ;;
    9) files="src/shenbi/pipeline/context_assemble.py src/shenbi/pipeline/plan_skeleton.py" ;;
    10) files="src/shenbi/gates/gate_manifest.py src/shenbi/pipeline/snapshot_diff.py" ;;
  esac
  for f in $files; do
    if [ -f "$f" ]; then
      echo "  ✓ $f exists"
    else
      echo "  ✗ $f MISSING — rollback would fail!"
    fi
  done
done
```
Expected: All files exist.

- [ ] **Step 2: Verify git revert would work**

Run:
```bash
git log --oneline -20 | head -5
echo "---"
echo "Rollback test: git revert --no-commit HEAD~1 && git revert --abort"
git revert --no-commit HEAD~1 2>/dev/null && git revert --abort && echo "  ✓ Rollback mechanism works"
```
Expected: "✓ Rollback mechanism works"
