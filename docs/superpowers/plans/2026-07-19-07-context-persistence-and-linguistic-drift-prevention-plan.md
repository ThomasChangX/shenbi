# Spec 4: Context Persistence and Linguistic Drift Prevention — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 43/56 chapters missing L3 context files (77% coverage gap) and close two distinct persistence failures: (a) assembly persistence errors swallowed by try/except with no post-check, and (b) the curated context computed by `_run_context_curation` that is NEVER written to disk. Add text-based linguistic drift detection independent of the contaminated LLM resonance scorer.

**Architecture:** Three-layer defense: (1) Force persistence of `context/chapter-N-context.md` (fix Gap 1) AND persist the curated 9-section context via `safe_write` (fix Gap 2 — currently computed and discarded), (2) Create `linguistic_drift.py` with 5 pragmatic domain-specific alarm metrics — these are NOT industry-standard stylometry (Burrows' Delta/Zeta); they are deliberately cheap, deterministic surface counters tuned to the specific observed failure mode, co-located with `compute_drift.py`, (3) 3-tier intervention (WARN/HARD/ESCALATE) in chapter loop. SYSTEM_TERMS and pattern fingerprints are project-config-driven (read from `genre-config.json -> drift_detection`), not hardcoded, with a generic >3σ frequency-divergence alarm as a second-tier check that catches novel degradation without hardcoding.

**Tech Stack:** Python 3.11+, pathlib, structlog, difflib.SequenceMatcher

## Global Constraints

- `just check` passes with zero failures
- `context/chapter-N-context.md` exists for every chapter (100% coverage)
- `context/chapter-N-curated.md` exists for every chapter (curation output must be persisted, not discarded)
- System term density < 30‰ throughout a 10-chapter smoke test
- Opening similarity < 60% across all adjacent chapters
- Sliding window content overlap < 35%
- Drift detection fires within 5 chapters of deviation onset
- No false-positive interventions on chapters 1-15 (baseline period)
- **Canonical module location:** `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` — co-located with the existing `compute_drift.py`. Spec 6's reference to `src/shenbi/pipeline/linguistic_drift.py` is SUPERSEDED; all drift detection lives under `skill_utils/drift_detection/`.
- **Assembly vs write are separate functions:** `assemble_context(project_dir, chapter_plan_path)` returns a `ContextPackage` and does NOT write; `write_context_file(project_dir, chapter, pkg)` is the separate function that calls `safe_write`. Both must be called. Do not collapse them into one.
- **Linguistic metrics are pragmatic alarm detectors, NOT stylometry:** they are ad hoc surface counters tuned to the observed parametric-prose failure mode — deliberately cheap, deterministic, and independent of LLM scoring. They are a gap-filling first alarm; embedding-novelty / Burrows' Delta are future enhancements (Shout-Out spec).
- **SYSTEM_TERMS are project-config-driven,** read from `genre-config.json -> drift_detection.system_terms` / `.pattern_fingerprints`, with hardcoded values only as a bootstrap fallback when the config is absent. A generic >3σ frequency-divergence alarm from the first-3-chapters baseline is added as a second-tier check that flags ANY term diverging >3σ, catching novel degradation without hardcoding.

---

### Task 1: Force Context File Persistence (Gap 1 — assembly errors swallowed)

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:566-591` (`_run_context_assembly`)
- Test: `tests/unit/pipeline/test_context_persistence.py`

**Interfaces:**
- Consumes: `assemble_context(project_dir, chapter_plan_path: str) -> ContextPackage` and `write_context_file(project_dir, chapter, pkg) -> Path` from `context_assemble.py:209-271` (two SEPARATE functions — assembly returns data, write persists; do not collapse)
- Produces: `_run_context_assembly(project_dir, chapter)` always leaves `context/chapter-N-context.md` on disk, even when assembly throws

**Root cause being fixed (spec §2.2, Gap 1):** the entire `_run_context_assembly` body is wrapped in `try/except Exception` that only does `log.warning(...)` — there is no post-check verifying the file exists and no fallback. If `write_context_file` throws, the pipeline silently continues to chapter-drafting with no context file.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_context_persistence.py
import tempfile
from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.chapter_loop import _run_context_assembly


def test_context_file_written_on_assembly():
    """Context file must exist after assembly, even on partial failure."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "plans").mkdir(parents=True)
        (project_dir / "context").mkdir(parents=True)
        # Write a minimal plan so assemble_context can read it
        (project_dir / "plans" / "chapter-1-plan.md").write_text(
            "# Plan\nrole: opening\n", encoding="utf-8")

        _run_context_assembly(project_dir, 1)

        context_file = project_dir / "context" / "chapter-1-context.md"
        assert context_file.exists(), f"Context file not created at {context_file}"
        content = context_file.read_text(encoding="utf-8")
        assert len(content) > 0, "Context file empty"


def test_context_file_fallback_written_when_assembly_throws():
    """When assemble_context raises, a minimal fallback context MUST still be written."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "plans").mkdir(parents=True)
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "plans" / "chapter-1-plan.md").write_text("# Plan\n")

        # Force assemble_context to raise
        with patch(
            "shenbi.pipeline.context_assemble.assemble_context",
            side_effect=RuntimeError("boom"),
        ):
            _run_context_assembly(project_dir, 1)

        context_file = project_dir / "context" / "chapter-1-context.md"
        assert context_file.exists(), (
            "Fallback context must be written when assembly throws "
            "(spec §3.1 Gap 1: error-swallowing try/except must add post-check + fallback)"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_context_persistence.py -v`
Expected: FAIL (`test_context_file_fallback_written_when_assembly_throws` fails: file not created because the try/except swallows the error with no fallback)

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/chapter_loop.py, REPLACE _run_context_assembly (lines 566-591):

def _run_context_assembly(project_dir: Path, chapter: int) -> None:
    """Materialize the three-route context package for the chapter.

    Calls :func:`assemble_context` + :func:`write_context_file` from
    ``context_assemble``. Closing spec §3.1 Gap 1: the previous body wrapped
    everything in a try/except that only logged a warning, so a throw from
    ``write_context_file`` left NO context file on disk and the pipeline
    silently continued. This version adds a mandatory post-check that verifies
    the file exists and writes a minimal Route-C fallback if it does not.
    """
    plan_path = f"plans/chapter-{chapter}-plan.md"
    context_path = project_dir / "context" / f"chapter-{chapter}-context.md"
    try:
        from shenbi.pipeline.context_assemble import (
            assemble_context,
            write_context_file,
        )

        pkg = assemble_context(project_dir, plan_path)
        out = write_context_file(project_dir, chapter, pkg)
        log.info(
            "context_assembled_for_chapter",
            chapter=chapter,
            sections=len(pkg.sections),
            total_tokens=pkg.total_tokens,
            output=str(out),
        )
    except Exception as e:
        log.warning("context_assembly_failed", chapter=chapter, error=str(e), exc_info=True)

    # HARD VERIFY (Gap 1 fix): output file must exist regardless of the try/except.
    if not context_path.exists():
        log.error("context_assembly_no_output", chapter=chapter)
        _write_minimal_context_fallback(project_dir, chapter)


def _write_minimal_context_fallback(project_dir: Path, chapter: int) -> None:
    """Write a minimal Route-C-only context when full assembly failed.

    Uses :func:`safe_write` (atomic + locked) so the fallback itself cannot be
    half-written.
    """
    from shenbi.pipeline.context_assemble import _route_c
    from shenbi.safe_write import safe_write

    project_dir = Path(project_dir)
    entries = _route_c(project_dir)  # fixed-rule retrieval only
    body = "\n\n".join(str(e.get("text", "")) for e in entries) or (
        "## Context (Minimal Fallback)\n\n"
        "Full context assembly failed; only Route C fixed rules available.\n"
    )
    out = project_dir / "context" / f"chapter-{chapter}-context.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    safe_write(out, body)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_context_persistence.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_context_persistence.py
git commit -m "fix: force context file persistence with post-check + fallback (Gap 1)"
```

---

### Task 2: Persist Curated Context (Gap 2 — computed but never written)

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:594-610` (`_run_context_curation`)
- Test: `tests/unit/pipeline/test_context_persistence.py` (add curation tests)

**Interfaces:**
- Consumes: `curate_context(project_dir, chapter) -> str` from `context_curation.py:81` (returns a curated 9-section string)
- Produces: `_run_context_curation(project_dir, chapter)` writes `context/chapter-N-curated.md` via `safe_write`

**Root cause being fixed (spec §2.2, Gap 2 — newly discovered):** `_run_context_curation` (line 594-610) calls `curate_context()` which returns a curated 9-section string, but the return value is only logged (`log.info("context_curated", chapter=chapter, length=len(curated))`) — the curated string is NEVER written to disk. The curation output is computed and discarded. This is a second, independent persistence failure from Gap 1.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/pipeline/test_context_persistence.py

from unittest.mock import patch


def test_curated_context_written_on_curation():
    """Curated context MUST be written to disk (Gap 2 fix)."""
    from shenbi.pipeline.chapter_loop import _run_context_curation

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "chapters").mkdir(parents=True)

        # curate_context returns a string; ensure it gets persisted
        with patch(
            "shenbi.pipeline.context_curation.curate_context",
            return_value="## Curated\n\nSection body.\n",
        ):
            _run_context_curation(project_dir, 1)

        curated_file = project_dir / "context" / "chapter-1-curated.md"
        assert curated_file.exists(), (
            "Curated context must be written to disk (spec §3.1 Gap 2: "
            "curate_context output was previously computed and discarded)"
        )
        assert "Section body" in curated_file.read_text(encoding="utf-8")


def test_curated_context_uses_safe_write():
    """Curation persistence must go through safe_write (atomic + locked)."""
    from shenbi.pipeline.chapter_loop import _run_context_curation

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "context").mkdir(parents=True)
        (project_dir / "chapters").mkdir(parents=True)

        with patch(
            "shenbi.pipeline.context_curation.curate_context",
            return_value="curated body",
        ), patch("shenbi.safe_write.safe_write") as mock_sw:
            _run_context_curation(project_dir, 2)
            assert mock_sw.called, "safe_write must be used to persist curated context"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_context_persistence.py::test_curated_context_written_on_curation -v`
Expected: FAIL (curated file does not exist — currently discarded)

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/chapter_loop.py, REPLACE _run_context_curation (lines 594-610):

def _run_context_curation(project_dir: Path, chapter: int) -> None:
    """Run deterministic context curation and PERSIST it (Gap 2 fix).

    Replaces the ``shenbi-context-composing`` LLM call (step 5) with
    deterministic Python operations: 9-section structuring, ending diversity
    check, and hook debt briefing generation.

    Closing spec §3.1 Gap 2: the previous body called ``curate_context`` and
    only logged the result length — the curated string was computed and then
    DISCARDED, never written to disk. This version persists the curated
    9-section document via :func:`safe_write` and post-checks the file.
    """
    from shenbi.pipeline.context_curation import curate_context
    from shenbi.safe_write import safe_write

    curated_path = project_dir / "context" / f"chapter-{chapter}-curated.md"
    try:
        curated = curate_context(project_dir, chapter)
        curated_path.parent.mkdir(parents=True, exist_ok=True)
        safe_write(curated_path, curated)  # FIX: actually persist (was discarded)
        log.info("context_curated", chapter=chapter, length=len(curated),
                 output=str(curated_path))
    except Exception as e:
        log.warning("context_curation_failed", chapter=chapter, error=str(e), exc_info=True)

    # Post-check: curation failures are non-fatal, but surface a hard error if
    # the output is unexpectedly absent after a non-throwing run.
    if not curated_path.exists():
        log.error("context_curation_no_output", chapter=chapter)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_context_persistence.py -v`
Expected: PASS (all tests, including the two new curation tests)

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_context_persistence.py
git commit -m "fix: persist curated context via safe_write (Gap 2 — was computed and discarded)"
```

---

### Task 3: Create Linguistic Drift Detector

**Files:**
- Create: `src/shenbi/skill_utils/drift_detection/linguistic_drift.py`
- Test: `tests/unit/skill_utils/drift_detection/test_linguistic_drift.py`

**Module location (canonical):** `src/shenbi/skill_utils/drift_detection/linguistic_drift.py` — co-located with the existing `compute_drift.py`. Spec 6's reference to `src/shenbi/pipeline/linguistic_drift.py` is SUPERSEDED; all drift detection lives under `skill_utils/drift_detection/`.

**Design rationale:** these are pragmatic domain-specific alarm detectors, NOT industry-standard stylometry. Classical stylometry (Burrows' Delta, Zeta, n-gram authorship attribution) uses function-word frequencies, type-token ratio, Yule's K lexical diversity. The 5 metrics here are ad hoc surface counters tuned to the specific observed failure mode (system-term leakage, em-dash enumeration, pattern fingerprinting). They are deliberately cheap, deterministic, and independent of LLM scoring — which is the actual goal (an alarm system that works even when the resonance LLM scorer is contaminated). Embedding-novelty / Burrows' Delta on sliding windows are future enhancements (Shout-Out spec), not this task.

**Interfaces:**
- Produces: `compute_linguistic_metrics(text: str, project_dir: Path | None = None) -> dict` — returns 5 metric values (all per-mille)
- Produces: `detect_drift(metrics: dict, baseline: dict) -> DriftResult` — compares against baseline
- Produces: `load_drift_config(project_dir) -> DriftConfig` — reads `genre-config.json -> drift_detection`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/skill_utils/drift_detection/test_linguistic_drift.py
from pathlib import Path

from shenbi.skill_utils.drift_detection.linguistic_drift import (
    DriftResult,
    compute_linguistic_metrics,
    detect_drift,
    frequency_divergence_alarms,
)

NORMAL_PROSE = """
林风站在废料场边缘，望着远处燃烧的天际线。他的手指无意识地摩挲着口袋里的金属碎片。
"你确定要这么做？"陈维民的声音从身后传来，带着一丝不易察觉的颤抖。
林风没有回头。"没有别的路了。"
"""

DEGRADED_PROSE = """
冷在场于第七层深度。系统参数确认：冷值 7.3，在场度 0.89。
冷知道深度在第八层。参数更新：冷值 8.1，在场度 0.92。
冷在场于第九层深度。系统确认：冷值 9.0，在场度 0.95。
静在场。光冷。隙在场。
"""


def test_compute_metrics_normal_prose():
    metrics = compute_linguistic_metrics(NORMAL_PROSE)
    assert metrics["system_term_density"] < 10.0  # < 10 per mille
    assert metrics["dialogue_density"] > 0.0  # has dialogue
    assert metrics["em_dash_density"] < 10.0


def test_compute_metrics_degraded_prose():
    metrics = compute_linguistic_metrics(DEGRADED_PROSE)
    assert metrics["system_term_density"] > 50.0  # > 50 per mille
    assert metrics["short_sentence_chain_density"] > 0.0


def test_detect_drift_triggers_on_large_deviation():
    baseline = compute_linguistic_metrics(NORMAL_PROSE)
    current = compute_linguistic_metrics(DEGRADED_PROSE)
    result = detect_drift(current, baseline)
    assert result.is_drift
    assert result.severity in ("WARN", "HARD", "ESCALATE")


def test_detect_drift_no_false_positive():
    baseline = compute_linguistic_metrics(NORMAL_PROSE)
    similar = NORMAL_PROSE + "\n风起了。\n"
    current = compute_linguistic_metrics(similar)
    result = detect_drift(current, baseline)
    assert not result.is_drift


def test_system_terms_loaded_from_genre_config(tmp_path):
    """SYSTEM_TERMS come from genre-config.json when present (not hardcoded)."""
    import json
    from shenbi.skill_utils.drift_detection.linguistic_drift import load_drift_config

    (tmp_path / "genre-config.json").write_text(json.dumps({
        "drift_detection": {
            "system_terms": ["自定义甲", "自定义乙"],
            "pattern_fingerprints": ["自定义句式"],
        }
    }), encoding="utf-8")

    cfg = load_drift_config(tmp_path)
    assert "自定义甲" in cfg.system_terms
    assert "自定义句式" in cfg.pattern_fingerprints


def test_frequency_divergence_flags_outlier_terms():
    """Generic >3 sigma frequency-divergence alarm catches novel degradation."""
    baseline_text = "林风看着远处的山。" * 50  # normal vocabulary
    # '在场度' is a new outlier term absent from baseline
    degraded = baseline_text + ("在场度 0.89。" * 30)
    current_metrics = compute_linguistic_metrics(degraded)
    baseline_metrics = compute_linguistic_metrics(baseline_text)

    alarms = frequency_divergence_alarms(
        degraded, baseline_text, sigma_threshold=3.0)
    # The novel outlier term must be flagged without being in SYSTEM_TERMS
    assert any("在场度" in a for a in alarms), (
        "Generic >3 sigma alarm must catch novel degradation terms not in SYSTEM_TERMS")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py -v`
Expected: FAIL (module not found — `skill_utils/drift_detection/linguistic_drift.py` does not exist yet)

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/skill_utils/drift_detection/linguistic_drift.py
"""Pragmatic linguistic-drift alarm detectors.

These are NOT industry-standard stylometry (Burrows' Delta, Zeta, n-gram
authorship attribution). They are deliberately cheap, deterministic surface
counters tuned to the specific observed failure mode: parametric prose
collapse (system-term leakage, em-dash enumeration, pattern fingerprinting).
The goal is an alarm system that works even when the resonance LLM scorer is
contaminated by the same degraded context it scores. Embedding-novelty /
Burrows' Delta are future enhancements (Shout-Out spec), not this module.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal


@dataclass
class DriftConfig:
    """Project-specific drift terms, loaded from genre-config.json.

    Falls back to a conservative bootstrap set when the config is absent so
    detection still works on fresh projects.
    """
    system_terms: list[str] = field(default_factory=lambda: [
        # Bootstrap fallback only; overridden by genre-config.json in real runs.
        "参数", "系统", "格式串", "历法", "槽位", "帧序列", "阈值", "在场于",
        "Phase", "MH-", "冷在场", "冷值", "在场度", "冷知道",
    ])
    pattern_fingerprints: list[str] = field(default_factory=lambda: ["冷在", "冷知道"])


@dataclass
class DriftResult:
    is_drift: bool
    severity: Literal["NONE", "WARN", "HARD", "ESCALATE"]
    metrics: dict
    deviations: dict
    message: str


def load_drift_config(project_dir: Path | str | None) -> DriftConfig:
    """Load drift terms from ``genre-config.json -> drift_detection``.

    SYSTEM_TERMS and pattern fingerprints are project-specific (they describe
    THIS novel's parametric failure vocabulary) and MUST be config-driven
    rather than hardcoded. Returns a bootstrap DriftConfig if the file or key
    is absent.
    """
    if project_dir is None:
        return DriftConfig()
    config_path = Path(project_dir) / "genre-config.json"
    if not config_path.exists():
        return DriftConfig()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DriftConfig()
    dd = raw.get("drift_detection", {}) if isinstance(raw, dict) else {}
    return DriftConfig(
        system_terms=list(dd.get("system_terms", DriftConfig().system_terms)),
        pattern_fingerprints=list(
            dd.get("pattern_fingerprints", DriftConfig().pattern_fingerprints)),
    )


def _short_chain_chars(text: str) -> int:
    """Count characters in chains of 5+ consecutive short sentences (<=15 chars)."""
    short_sents = re.findall(r"(?:[^。！？\n]{1,15}[。！？\n]){5,}", text)
    return sum(len(s) for s in short_sents)


def compute_linguistic_metrics(
    text: str, project_dir: Path | str | None = None
) -> dict:
    """Compute 5 linguistic drift metrics, each normalized per mille.

    Args:
        text: The chapter prose to analyze.
        project_dir: Project root (used to load config-driven SYSTEM_TERMS).
    """
    cfg = load_drift_config(project_dir)
    text_len = max(len(text), 1)

    # M1: System term density — parametric language indicator
    system_term_re = re.compile("|".join(re.escape(t) for t in cfg.system_terms))
    system_term_density = len(system_term_re.findall(text)) / text_len * 1000

    # M2: Em-dash density — enumeration separator in degraded prose
    em_dash_density = text.count("——") / text_len * 1000

    # M3: Short-sentence chain density — consecutive <=15 char sentences
    short_sentence_chain_density = _short_chain_chars(text) / text_len * 1000

    # M4: Pattern density — project fingerprint of degradation (config-driven)
    pattern_density = sum(text.count(p) for p in cfg.pattern_fingerprints) / text_len * 1000

    # M5: Dialogue density — quotation-mark frequency, proxy for natural talk
    dialogue_density = text.count("\u201c") / text_len * 1000  # Chinese left double quote

    return {
        "system_term_density": round(system_term_density, 4),
        "em_dash_density": round(em_dash_density, 4),
        "short_sentence_chain_density": round(short_sentence_chain_density, 4),
        "pattern_density": round(pattern_density, 4),
        "dialogue_density": round(dialogue_density, 4),
        "total_chars": text_len,
    }


def frequency_divergence_alarms(
    current_text: str,
    baseline_text: str,
    sigma_threshold: float = 3.0,
    min_count: int = 2,
) -> list[str]:
    """Generic second-tier alarm: flag ANY term whose frequency diverges >3 sigma.

    This catches novel degradation patterns WITHOUT hardcoding them into
    SYSTEM_TERMS. Computes a per-term frequency distribution from the baseline
    (first chapters) and flags current terms whose count exceeds the baseline
    mean + ``sigma_threshold`` standard deviations, requiring at least
    ``min_count`` occurrences to avoid noise.

    > **CJK caution:** CJK bigram frequency distributions are fat-tailed.
    > Sigma-threshold outlier detection on raw bigram counts will be unreliable
    > for N < 100 chapters. Use TF-IDF weighting or relative frequency ratio
    > (current chapter vs. baseline) instead of absolute sigma thresholds.
    > Until sufficient data is accumulated, treat frequency_alarms as
    > informational (WARN) rather than blocking (HARD).
    """
    def _term_freqs(text: str) -> Counter:
        # Bigrams of CJK chars — cheap surface units that capture novel phrases
        cjk = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        return Counter(cjk[i:i + 2] for i in range(len(cjk) - 1))

    base = _term_freqs(baseline_text)
    curr = _term_freqs(current_text)
    base_total = sum(base.values()) or 1
    counts = list(base.values())
    mean = sum(counts) / len(counts) if counts else 0.0
    variance = sum((c - mean) ** 2 for c in counts) / len(counts) if counts else 0.0
    stddev = math.sqrt(variance) or 1.0
    cutoff = mean + sigma_threshold * stddev

    alarms: list[str] = []
    for term, c in curr.items():
        if c < min_count:
            continue
        if base.get(term, 0) < cutoff:
            continue
        # Flag only terms far ABOVE their baseline presence (novel burst)
        baseline_rate = base.get(term, 0) / base_total
        current_rate = c / (sum(curr.values()) or 1)
        if baseline_rate == 0 and current_rate > 0:
            alarms.append(term)
    return alarms


def detect_drift(current: dict, baseline: dict) -> DriftResult:
    """Detect linguistic drift by comparing current metrics against baseline.

    Threshold: any of the density metrics deviates >500% from baseline, or the
    dialogue density collapses to <20% of baseline. Severity is driven by the
    absolute system_term_density (per mille): 30-50 -> WARN, 50-100 -> HARD,
    >100 -> ESCALATE.
    """
    deviations: dict[str, float] = {}
    max_deviation_ratio = 1.0
    trigger_metric: str | None = None

    for metric in ["system_term_density", "em_dash_density", "pattern_density",
                   "short_sentence_chain_density"]:
        base_val = baseline.get(metric, 0.0)
        curr_val = current.get(metric, 0.0)
        ratio = (curr_val / base_val) if base_val > 0 else (6.0 if curr_val > 0 else 1.0)
        deviations[metric] = round(ratio, 2)
        if ratio > max_deviation_ratio:
            max_deviation_ratio = ratio
            trigger_metric = metric

    # Dialogue density: trigger when it drops below 20% of baseline
    base_dialogue = baseline.get("dialogue_density", 0.0)
    curr_dialogue = current.get("dialogue_density", 0.0)
    if base_dialogue > 0:
        dialogue_ratio = curr_dialogue / base_dialogue
        deviations["dialogue_density"] = round(dialogue_ratio, 2)
        if dialogue_ratio < 0.2:
            max_deviation_ratio = max(max_deviation_ratio, 5.0)
            trigger_metric = trigger_metric or "dialogue_density"

    is_drift = max_deviation_ratio > 5.0  # >500% deviation threshold

    stm_density = current.get("system_term_density", 0.0)  # already per mille
    if stm_density > 100:
        severity = "ESCALATE"
    elif stm_density > 50:
        severity = "HARD"
    elif stm_density > 30 or is_drift:
        severity = "WARN"
    else:
        severity = "NONE"

    message = (
        f"Drift detected: {trigger_metric} deviated {max_deviation_ratio:.1f}x "
        f"from baseline. System term density: {stm_density:.1f} per mille."
    ) if is_drift else "No linguistic drift detected."

    return DriftResult(
        is_drift=is_drift,
        severity=severity,
        metrics=current,
        deviations=deviations,
        message=message,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/skill_utils/drift_detection/linguistic_drift.py tests/unit/skill_utils/drift_detection/test_linguistic_drift.py
git commit -m "feat: add pragmatic linguistic-drift alarm detectors (config-driven + 3-sigma)"
```

---

### Task 4: Add Opening Similarity and Content Looping Detection

**Files:**
- Modify: `src/shenbi/skill_utils/drift_detection/linguistic_drift.py`
- Test: `tests/unit/skill_utils/drift_detection/test_linguistic_drift.py` (add tests)

**Interfaces:**
- Produces: `check_opening_similarity(chapter_text: str, prev_chapter_text: str) -> float`
- Produces: `check_window_redundancy(chapters: list[str], window_size: int = 4) -> float`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/skill_utils/drift_detection/test_linguistic_drift.py:

def test_check_opening_similarity_identical():
    from shenbi.skill_utils.drift_detection.linguistic_drift import check_opening_similarity
    ch1 = "冷在场于第七层深度。冷知道深度在第八层。" + "x" * 300
    ch2 = "冷在场于第七层深度。冷知道深度在第八层。" + "y" * 300
    similarity = check_opening_similarity(ch1, ch2)
    assert similarity > 0.6, f"Expected >0.6, got {similarity}"


def test_check_opening_similarity_different():
    from shenbi.skill_utils.drift_detection.linguistic_drift import check_opening_similarity
    ch1 = "林风站在山顶，望着远方的云海翻涌。" + "x" * 300
    ch2 = "陈维民推开实验室的门，灯光自动亮起。" + "y" * 300
    similarity = check_opening_similarity(ch1, ch2)
    assert similarity < 0.6, f"Expected <0.6, got {similarity}"


def test_check_window_redundancy_detects_looping():
    from shenbi.skill_utils.drift_detection.linguistic_drift import check_window_redundancy
    chapters = [
        "冷在场于第七层深度。" * 50,
        "冷在场于第八层深度。" * 50,
        "冷在场于第九层深度。" * 50,
        "冷在场于第十层深度。" * 50,
    ]
    max_sim = check_window_redundancy(chapters, window_size=4)
    assert max_sim > 0.35, f"Expected >0.35, got {max_sim}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py::test_check_opening_similarity_identical -v`
Expected: FAIL (function not defined)

- [ ] **Step 3: Write minimal implementation**

```python
# Add to src/shenbi/skill_utils/drift_detection/linguistic_drift.py:
from difflib import SequenceMatcher


def check_opening_similarity(chapter_text: str, prev_chapter_text: str) -> float:
    """Compare first 300 characters of consecutive chapters using SequenceMatcher."""
    opening1 = chapter_text[:300]
    opening2 = prev_chapter_text[:300]
    return SequenceMatcher(None, opening1, opening2).ratio()


def check_window_redundancy(chapters: list[str], window_size: int = 4) -> float:
    """Compute pairwise similarity of all chapter pairs within a sliding window.
    Returns the maximum similarity found. Threshold: >0.35 flags content looping."""
    if len(chapters) < 2:
        return 0.0
    max_similarity = 0.0
    window = chapters[-window_size:] if len(chapters) >= window_size else chapters
    for i in range(len(window)):
        for j in range(i + 1, len(window)):
            sim = SequenceMatcher(None, window[i][:500], window[j][:500]).ratio()
            max_similarity = max(max_similarity, sim)
    return max_similarity
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/skill_utils/drift_detection/test_linguistic_drift.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/skill_utils/drift_detection/linguistic_drift.py tests/unit/skill_utils/drift_detection/test_linguistic_drift.py
git commit -m "feat: add opening similarity and content looping detection"
```

---

### Task 5: Integrate 3-Tier Intervention in Chapter Loop

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add drift check after snapshot step)
- Modify: `src/shenbi/skill_utils/drift_detection/compute_drift.py:147` (add 4th trigger after `detect_volume_drift`)

**Interfaces:**
- Consumes: `compute_linguistic_metrics()` from `src/shenbi/skill_utils/drift_detection/linguistic_drift.py`
- Consumes: `detect_drift()` from the same module
- Produces: `_check_linguistic_drift(project_dir, chapter) -> DriftResult | None`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_drift_intervention.py
from pathlib import Path

from shenbi.skill_utils.drift_detection.linguistic_drift import (
    DriftResult,
    compute_linguistic_metrics,
    detect_drift,
)

def test_intervention_triggers_on_degraded_text():
    """3-tier intervention should fire when system term density exceeds thresholds."""
    normal = "林风站在山顶，望着远方。" * 20
    degraded = "冷在场于第七层深度。冷值7.3，在场度0.89。" * 20

    baseline = compute_linguistic_metrics(normal)
    current = compute_linguistic_metrics(degraded)
    result = detect_drift(current, baseline)

    assert result.is_drift
    assert result.severity in ("WARN", "HARD", "ESCALATE")
    assert len(result.message) > 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_drift_intervention.py -v`
Expected: FAIL (test file not found → create it) then PASS

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/chapter_loop.py, add after the snapshot step:

def _check_linguistic_drift(project_dir: Path, chapter: int) -> DriftResult | None:
    """Check chapter text for linguistic drift and apply tiered intervention.

    Reads the just-written ``chapters/chapter-{chapter}.md`` (no zero-padding),
    compares its pragmatic alarm metrics (Task 3) against the established
    baseline, and applies WARN/HARD/ESCALATE intervention per spec §3.4.
    """
    from shenbi.skill_utils.drift_detection.linguistic_drift import (
        check_opening_similarity,
        compute_linguistic_metrics,
        detect_drift,
    )

    chapter_file = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_file.exists():
        return None

    chapter_text = chapter_file.read_text(encoding="utf-8")

    # Load baseline (established from first 3 chapters — see Task 6 / spec §3.5)
    baseline_file = project_dir / "style" / "linguistic_baseline.json"
    import json
    if baseline_file.exists():
        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    else:
        log.warning("no_linguistic_baseline", chapter=chapter)
        return None

    current = compute_linguistic_metrics(chapter_text, project_dir=project_dir)
    result = detect_drift(current, baseline)

    if result.is_drift:
        log.warning("linguistic_drift_detected",
                     chapter=chapter,
                     severity=result.severity,
                     metrics=result.metrics)

        if result.severity == "ESCALATE":
            log.error("drift_escalate_pause_for_review", chapter=chapter)
            raise DriftEscalationError(
                f"Chapter {chapter}: system term density "
                f"{result.metrics.get('system_term_density', 0):.1f} per mille. "
                "Pipeline paused for human review."
            )
        elif result.severity == "HARD":
            _inject_drift_correction(project_dir, chapter, result)
        elif result.severity == "WARN":
            _inject_drift_warning(project_dir, chapter, result)

    # Check opening similarity against the previous chapter
    if chapter > 1:
        prev_file = project_dir / "chapters" / f"chapter-{chapter - 1}.md"
        if prev_file.exists():
            prev_text = prev_file.read_text(encoding="utf-8")
            opening_sim = check_opening_similarity(chapter_text, prev_text)
            if opening_sim > 0.6:
                log.warning("opening_similarity_high",
                            chapter=chapter, similarity=round(opening_sim, 2))
                _inject_opening_variation_directive(project_dir, chapter, opening_sim)

    return result


def _inject_drift_correction(project_dir: Path, chapter: int, result: DriftResult) -> None:
    """Write a PRE_WRITE_CHECK directive for the next chapter to correct drift."""
    from shenbi.safe_write import safe_write
    directive = f"""## PRE_WRITE_CHECK (AUTO-GENERATED - DRIFT DETECTED)

CRITICAL: Chapter {chapter} has system term density of {result.metrics.get('system_term_density', 0):.1f} per mille (baseline: <5).
The next chapter MUST:
1. Use natural Chinese narrative prose — NO system parameter language (冷在场, 冷值, 在场度)
2. Include at least 3 dialogue exchanges with human characters
3. Include at least 2 physical actions or sensory descriptions
4. Use varied sentence structures — no repeated sentence templates
"""
    directive_file = project_dir / "context" / f"drift-correction-{chapter + 1}.md"
    safe_write(directive_file, directive)


def _inject_drift_warning(project_dir: Path, chapter: int, result: DriftResult) -> None:
    """Write a gentle warning for the next chapter."""
    from shenbi.safe_write import safe_write
    warning = f"""## PRE_WRITE_CHECK (AUTO-GENERATED - STYLE WARNING)

Note: Chapter {chapter} shows early signs of parametric language.
Please prioritize natural prose and human character dialogue in the next chapter.
"""
    warning_file = project_dir / "context" / f"drift-warning-{chapter + 1}.md"
    safe_write(warning_file, warning)


def _inject_opening_variation_directive(project_dir: Path, chapter: int, similarity: float) -> None:
    """Warn about high opening similarity."""
    from shenbi.safe_write import safe_write
    directive = f"""## PRE_WRITE_CHECK (OPENING VARIATION)

The opening of Chapter {chapter} is {similarity*100:.0f}% similar to Chapter {chapter-1}.
Next chapter MUST use a different opening approach.
Forbidden openings: "冷知道/冷在/冷在场于" sentence patterns.
"""
    directive_file = project_dir / "context" / f"opening-variation-{chapter + 1}.md"
    safe_write(directive_file, directive)


class DriftEscalationError(Exception):
    """Raised when linguistic drift reaches ESCALATE severity."""
    pass
```

```python
# In src/shenbi/skill_utils/drift_detection/compute_drift.py, add a 4th trigger:

# After detect_volume_drift (ends ~line 146), alongside the three score-based
# conditions, add:
def check_linguistic_drift_trigger(linguistic_result) -> bool:
    """4th trigger: linguistic alarm metrics exceed thresholds.

    Independent of resonance scores (which are contaminated by the degraded
    LLM context). Fires on HARD/ESCALATE linguistic drift only.
    """
    if linguistic_result is None:
        return False
    return linguistic_result.is_drift and linguistic_result.severity in ("HARD", "ESCALATE")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_drift_intervention.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/skill_utils/drift_detection/compute_drift.py tests/unit/pipeline/test_drift_intervention.py
git commit -m "feat: integrate 3-tier linguistic drift intervention in chapter loop"
```

---

### Task 5a: Establish Linguistic Baseline (NEW)

**Files:**
- New: `src/shenbi/skill_utils/drift_detection/baseline.py`

**Purpose:** Compute and persist the linguistic baseline from the first 3 chapters
so that subsequent drift detection has a reference point.

```python
# baseline.py
def establish_baseline(project_dir: Path, chapters: list[int]) -> dict:
    """Compute linguistic baseline from specified chapters.

    Reads chapter prose, computes system-term density, bigram frequencies,
    opening similarity, and window redundancy. Persists to
    style/linguistic_baseline.json via safe_write.
    """
    ...
```
Wire this into `_run_context_assembly` or chapter_loop so it runs once
after chapter 3 completes.

---

### Task 6: Add Context Audit and Backfill CLI

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py` (add `_audit_context_coverage`)
- Modify: `src/shenbi/pipeline/cli.py` (add `backfill-context` command)

**Interfaces:**
- Produces: `_audit_context_coverage(project_dir, current_chapter) -> list[int]` — returns missing chapter numbers
- Produces: `pipeline backfill-context --chapters 13-54` CLI command

**Note on signatures (verified against code):** `assemble_context(project_dir, chapter_plan_path: str)` takes a PLAN PATH string (not a chapter int) and returns a `ContextPackage`; `write_context_file(project_dir, chapter, pkg)` is the separate function that persists via `safe_write`; `curate_context(project_dir, chapter)` returns the curated string directly (it re-reads what assembly wrote). The backfill must call these with the correct arguments and must NOT pass `assemble_context`'s return value into `curate_context`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_context_audit.py
import tempfile
from pathlib import Path

def test_audit_context_coverage_finds_gaps():
    from shenbi.pipeline.chapter_loop import _audit_context_coverage
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        context_dir = project_dir / "context"
        context_dir.mkdir(parents=True)
        # Create context for chapters 1, 2, 5 only — gaps at 3, 4
        # (real naming: chapter-{ch}-context.md, no zero-padding)
        for ch in [1, 2, 5]:
            (context_dir / f"chapter-{ch}-context.md").write_text("test", encoding="utf-8")

        missing = _audit_context_coverage(project_dir, current_chapter=5)
        assert 3 in missing, f"Chapter 3 should be missing, got {missing}"
        assert 4 in missing, f"Chapter 4 should be missing, got {missing}"
        assert 1 not in missing, f"Chapter 1 should not be missing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/pipeline/test_context_audit.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# In src/shenbi/pipeline/chapter_loop.py:

def _audit_context_coverage(project_dir: Path, current_chapter: int) -> list[int]:
    """Scan all chapters up to current_chapter and return list of missing context files.

    Uses the real (non-padded) ``chapter-{ch}-context.md`` naming. Called at
    pipeline resume initialization to surface the 77% coverage gap (spec §3.1).
    """
    import structlog
    log = structlog.get_logger()
    context_dir = project_dir / "context"
    missing = []
    for ch in range(1, current_chapter + 1):
        context_file = context_dir / f"chapter-{ch}-context.md"
        if not context_file.exists():
            missing.append(ch)
    if missing:
        log.warning("context_coverage_gap", missing_chapters=missing,
                    gap_ratio=f"{len(missing)}/{current_chapter}")
    return missing
```

```python
# In src/shenbi/pipeline/cli.py, add a backfill-context command:
@pipeline.command("backfill-context")
@click.option("--chapters", help="Chapter range, e.g. '13-54'")
@click.option("--project-dir", default=".", type=click.Path(exists=True))
def backfill_context(chapters: str, project_dir: str):
    """Re-run deterministic context assembly + curation for a chapter range.

    These are deterministic Python functions and can be re-executed safely to
    close coverage gaps for already-generated chapters. Uses the real
    assemble_context(project_dir, plan_path) / write_context_file / curate_context
    signatures (spec §3.1 backfill).
    """
    from shenbi.pipeline.context_assemble import assemble_context, write_context_file
    from shenbi.pipeline.context_curation import curate_context
    from shenbi.safe_write import safe_write
    project_path = Path(project_dir)

    if "-" in chapters:
        start, end = chapters.split("-")
        chapter_range = range(int(start), int(end) + 1)
    else:
        chapter_range = [int(chapters)]

    for ch in chapter_range:
        try:
            plan_path = f"plans/chapter-{ch}-plan.md"
            pkg = assemble_context(project_path, plan_path)
            write_context_file(project_path, ch, pkg)  # safe_write inside
            curated = curate_context(project_path, ch)
            curated_path = project_path / "context" / f"chapter-{ch}-curated.md"
            curated_path.parent.mkdir(parents=True, exist_ok=True)
            safe_write(curated_path, curated)
            click.echo(f"  Backfilled context for chapter {ch}")
        except Exception as e:
            click.echo(f"  FAILED chapter {ch}: {e}", err=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/pipeline/test_context_audit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/cli.py tests/unit/pipeline/test_context_audit.py
git commit -m "feat: add context coverage audit and backfill-context CLI command"
```
