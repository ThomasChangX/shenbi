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

import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Final, Literal

from shenbi.config.thresholds import DEFAULT_THRESHOLDS
from shenbi.gates.shared import META_BLOCK_RE  # 单源别名（z11 F1301）

# R2 (F601): single source for the drift threshold. Dialogue collapse sets the
# deviation ratio to exactly this value, so the trigger test must be >=.
_DEVIATION_DRIFT_THRESHOLD: Final[float] = 5.0


@dataclass
class DriftConfig:
    """Bootstrap drift vocabulary.

    Spec #32 F644 adjudication: the ``genre-config.json -> drift_detection``
    key has NO writer anywhere in the framework or skills, so reading it
    carried zero information. The reader (``load_drift_config``) was removed;
    the bootstrap vocabulary below is the single deterministic source until a
    writer is added (explicitly out of scope for spec #32 — that would be a
    feature, not a fix). Absolute severity thresholds live in
    ``shenbi.config.thresholds`` (single source).
    """

    system_terms: list[str] = field(
        default_factory=lambda: [
            # Bootstrap vocabulary (single source after the F644 reader removal).
            "参数",
            "系统",
            "格式串",
            "历法",
            "槽位",
            "帧序列",
            "阈值",
            "在场于",
            "Phase",
            "MH-",
            "冷在场",
            "冷值",
            "在场度",
            "冷知道",
        ]
    )
    pattern_fingerprints: list[str] = field(default_factory=lambda: ["冷在", "冷知道"])


_BOOTSTRAP_DRIFT_CONFIG: Final[DriftConfig] = DriftConfig()


@dataclass
class DriftResult:
    is_drift: bool
    severity: Literal["NONE", "WARN", "HARD", "ESCALATE"]
    metrics: dict[str, float]
    deviations: dict[str, float]
    message: str
    # F618 (spec #32): metrics whose baseline is 0 while current > 0 — the
    # ratio is undefined (insufficient baseline), not fabricated drift.
    insufficient_baseline: list[str] = field(default_factory=list)


_SENTENCE_END_RE: Final = re.compile(r"[^。！？\n]*[。！？\n]")
_SHORT_SENTENCE_MAX: Final = 15


def _short_chain_chars(text: str) -> int:
    """Count characters in chains of 3+ consecutive short sentences (<=15 chars).

    F653 (spec #32): split on sentence terminators first, then measure each
    sentence's full length. The previous unanchored regex could backtrack a
    <=15-char tail out of a long sentence and absorb it into a chain; a
    sentence counts as short only if its ENTIRE body (terminator excluded)
    is <=15 chars.
    """
    total = 0
    chain: list[str] = []
    for sent in _SENTENCE_END_RE.findall(text):
        if len(sent) - 1 <= _SHORT_SENTENCE_MAX:
            chain.append(sent)
            if len(chain) == 3:
                # chain just completed — count all three founding sentences
                total += sum(len(s) for s in chain)
            elif len(chain) > 3:
                total += len(sent)
        else:
            chain = []
    return total


def compute_linguistic_metrics(
    text: str, project_dir: Path | str | None = None
) -> dict[str, float]:
    """Compute 5 linguistic drift metrics, each normalized per mille.

    Args:
        text: The chapter prose to analyze.
        project_dir: Kept for call-site compatibility only. The
            ``genre-config.json -> drift_detection`` reader was removed (spec
            #32 F644: zero writers → zero information); the bootstrap
            DriftConfig vocabulary is always used.
    """
    cfg = _BOOTSTRAP_DRIFT_CONFIG
    # F634: META blocks are bookkeeping, not prose — strip before any metric.
    text = META_BLOCK_RE.sub("", text)
    text_len = max(len(text), 1)

    # M1: System term density — parametric language indicator
    # F605: empty vocabulary must skip the regex — re.compile("") matches at
    # every position and inflates the density to ~1000‰.
    if cfg.system_terms:
        system_term_re = re.compile("|".join(re.escape(t) for t in cfg.system_terms))
        system_term_density = len(system_term_re.findall(text)) / text_len * 1000
    else:
        system_term_density = 0.0

    # M2: Em-dash density — enumeration separator in degraded prose
    em_dash_density = text.count("——") / text_len * 1000

    # M3: Short-sentence chain density — consecutive <=15 char sentences
    short_sentence_chain_density = _short_chain_chars(text) / text_len * 1000

    # M4: Pattern density — project fingerprint of degradation (config-driven)
    pattern_density = sum(text.count(p) for p in cfg.pattern_fingerprints) / text_len * 1000

    # M5: Dialogue density — quotation-mark frequency, proxy for natural talk
    dialogue_density = text.count("\u201c") / text_len * 1000  # left double quote
    dialogue_density += text.count("\u201d") / text_len * 1000  # right double quote
    dialogue_density += text.count('"') / text_len * 1000  # ASCII double quote

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

    def _term_freqs(text: str) -> Counter[str]:
        # CJK word sequences — contiguous CJK chars form surface tokens
        words = re.findall(r"[\u4e00-\u9fff]+", text)
        return Counter(words)

    base = _term_freqs(baseline_text)
    curr = _term_freqs(current_text)
    base_total = sum(base.values()) or 1

    alarms: list[str] = []
    for term, c in curr.items():
        if c < min_count:
            continue
        baseline_count = base.get(term, 0)
        baseline_rate = baseline_count / base_total
        current_rate = c / (sum(curr.values()) or 1)
        # Novel term: absent from baseline, present in current
        if baseline_rate == 0 and current_rate > 0:
            alarms.append(term)
            continue
        # Existing term: check for significant frequency surge
        if baseline_count >= min_count and current_rate > baseline_rate * (1 + sigma_threshold):
            alarms.append(term)
    return alarms


def detect_drift(current: dict[str, float], baseline: dict[str, float]) -> DriftResult:
    """Detect linguistic drift by comparing current metrics against baseline.

    Threshold: any of the density metrics deviates >=500% (>= 5.0x, see
    _DEVIATION_DRIFT_THRESHOLD — inclusive so the dialogue-collapse set-point
    is reachable) from baseline, or the dialogue density collapses to <20% of
    baseline. Severity is driven by the absolute system_term_density (per
    mille): warn..hard -> WARN, hard..escalate -> HARD, >escalate -> ESCALATE
    (single source: ``shenbi.config.thresholds.DEFAULT_THRESHOLDS``).
    """
    deviations: dict[str, float] = {}
    insufficient_baseline: list[str] = []
    max_deviation_ratio = 1.0
    trigger_metric: str | None = None

    for metric in [
        "system_term_density",
        "em_dash_density",
        "pattern_density",
        "short_sentence_chain_density",
    ]:
        base_val = baseline.get(metric, 0.0)
        curr_val = current.get(metric, 0.0)
        if base_val <= 0:
            # F618 (spec #32): zero baseline — ratio undefined, first sighting
            # must not fabricate drift (previously a 6.0 sentinel forced WARN).
            deviations[metric] = 1.0
            if curr_val > 0:
                insufficient_baseline.append(metric)
            continue
        ratio = curr_val / base_val
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
            max_deviation_ratio = max(max_deviation_ratio, _DEVIATION_DRIFT_THRESHOLD)
            trigger_metric = trigger_metric or "dialogue_density"

    is_drift = max_deviation_ratio >= _DEVIATION_DRIFT_THRESHOLD  # >=500% deviation

    stm_density = current.get("system_term_density", 0.0)  # already per mille
    severity: Literal["NONE", "WARN", "HARD", "ESCALATE"]
    if stm_density > DEFAULT_THRESHOLDS.system_term_density_escalate:
        severity = "ESCALATE"
    elif stm_density > DEFAULT_THRESHOLDS.system_term_density_hard:
        severity = "HARD"
    elif stm_density > DEFAULT_THRESHOLDS.system_term_density_warn or is_drift:
        severity = "WARN"
    else:
        severity = "NONE"

    if is_drift:
        message = (
            f"Drift detected: {trigger_metric} deviated {max_deviation_ratio:.1f}x "
            f"from baseline. System term density: {stm_density:.1f} per mille."
        )
    elif severity != "NONE":
        # R3 (F612): absolute-threshold breach without ratio drift — must not
        # read as "no drift" to the reviewer the ESCALATE pause hands it to.
        message = (
            f"Severity {severity}: system term density {stm_density:.1f} per mille "
            f"(absolute threshold breach; ratio metrics within bounds)."
        )
    else:
        message = "No linguistic drift detected."

    if insufficient_baseline and not is_drift:
        message += f" Insufficient baseline (zero) for: {', '.join(insufficient_baseline)}."

    return DriftResult(
        is_drift=is_drift,
        severity=severity,
        metrics=current,
        deviations=deviations,
        message=message,
        insufficient_baseline=insufficient_baseline,
    )


def check_opening_similarity(chapter_text: str, prev_chapter_text: str) -> float:
    """Compare first 300 characters of consecutive chapters using SequenceMatcher."""
    opening1 = chapter_text[:300]
    opening2 = prev_chapter_text[:300]
    return SequenceMatcher(None, opening1, opening2).ratio()


def check_window_redundancy(chapters: list[str], window_size: int = 4) -> float:
    """Compute pairwise similarity of all chapter pairs within a sliding window.
    Returns the maximum similarity found. Threshold: >0.35 flags content looping.
    """
    if len(chapters) < 2:
        return 0.0
    max_similarity = 0.0
    window = chapters[-window_size:] if len(chapters) >= window_size else chapters
    for i in range(len(window)):
        for j in range(i + 1, len(window)):
            sim = SequenceMatcher(None, window[i][:500], window[j][:500]).ratio()
            max_similarity = max(max_similarity, sim)
    return max_similarity
