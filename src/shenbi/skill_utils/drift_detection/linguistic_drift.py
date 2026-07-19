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

    system_terms: list[str] = field(
        default_factory=lambda: [
            # Bootstrap fallback only; overridden by genre-config.json in real runs.
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


@dataclass
class DriftResult:
    is_drift: bool
    severity: Literal["NONE", "WARN", "HARD", "ESCALATE"]
    metrics: dict[str, float]
    deviations: dict[str, float]
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
            dd.get("pattern_fingerprints", DriftConfig().pattern_fingerprints)
        ),
    )


def _short_chain_chars(text: str) -> int:
    """Count characters in chains of 3+ consecutive short sentences (<=15 chars)."""
    short_sents = re.findall(r"(?:[^。！？\n]{1,15}[。！？\n]){3,}", text)
    return sum(len(s) for s in short_sents)


def compute_linguistic_metrics(
    text: str, project_dir: Path | str | None = None
) -> dict[str, float]:
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

    Threshold: any of the density metrics deviates >500% from baseline, or the
    dialogue density collapses to <20% of baseline. Severity is driven by the
    absolute system_term_density (per mille): 30-50 -> WARN, 50-100 -> HARD,
    >100 -> ESCALATE.
    """
    deviations: dict[str, float] = {}
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
    severity: Literal["NONE", "WARN", "HARD", "ESCALATE"]
    if stm_density > 100:
        severity = "ESCALATE"
    elif stm_density > 50:
        severity = "HARD"
    elif stm_density > 30 or is_drift:
        severity = "WARN"
    else:
        severity = "NONE"

    message = (
        (
            f"Drift detected: {trigger_metric} deviated {max_deviation_ratio:.1f}x "
            f"from baseline. System term density: {stm_density:.1f} per mille."
        )
        if is_drift
        else "No linguistic drift detected."
    )

    return DriftResult(
        is_drift=is_drift,
        severity=severity,
        metrics=current,
        deviations=deviations,
        message=message,
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


# ---------------------------------------------------------------------------
# Pipeline-facing deterministic drift check (ADD-3, per Spec 4 §3.2)
# ---------------------------------------------------------------------------


def _load_baseline(project_dir: Path) -> dict[str, float]:
    """Load or create linguistic baseline from early chapters."""
    baseline_path = project_dir / "context" / "linguistic_baseline.json"
    if baseline_path.exists():
        loaded: dict[str, float] = json.loads(baseline_path.read_text(encoding="utf-8"))
        return loaded

    # Create baseline from early chapters
    baseline: dict[str, float] = {
        "system_term_density": 0.0,
        "em_dash_density": 0.0,
        "dialogue_ratio": 0.0,
    }
    chapters_read = 0

    for ch in range(1, 6):
        ch_path = project_dir / "chapters" / f"chapter-{ch}.md"
        if ch_path.exists():
            text = ch_path.read_text(encoding="utf-8")
            total_chars = len(text)
            system_terms = len(re.findall(r"系统|面板|等级|技能|属性|经验", text))
            em_dashes = text.count("——") + text.count("--")
            dialogue_chars = sum(len(m.group()) for m in re.finditer(r'["""].+?["»"]', text))
            baseline["system_term_density"] += system_terms / max(total_chars, 1)
            baseline["em_dash_density"] += em_dashes / max(total_chars, 1)
            baseline["dialogue_ratio"] += dialogue_chars / max(total_chars, 1)
            chapters_read += 1

    if chapters_read > 0:
        for k in baseline:
            baseline[k] /= chapters_read

    from shenbi.safe_write import safe_write

    safe_write(baseline_path, json.dumps(baseline, indent=2))
    return baseline


def check_linguistic_drift(project_dir: Path, chapter: int) -> list[str]:
    """Run linguistic drift detection. Returns WARN alerts.

    Args:
        project_dir: Root directory of the novel project.
        chapter: Chapter number to check.

    Returns:
        List of warning strings (empty if no drift detected).
    """
    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_path.exists():
        return []

    text = chapter_path.read_text(encoding="utf-8")
    total_chars = max(len(text), 1)
    baseline = _load_baseline(project_dir)

    alerts = []

    # System term density (per mille)
    system_terms = len(re.findall(r"系统|面板|等级|技能|属性|经验", text))
    system_density = (system_terms / total_chars) * 1000
    if system_density > 30:
        alerts.append(
            f"System term density {system_density:.0f}‰ "
            f"(baseline: {baseline.get('system_term_density', 0) * 1000:.0f}‰)"
        )

    # Em-dash density (per mille)
    em_dashes = text.count("——") + text.count("--")
    em_density = (em_dashes / total_chars) * 1000
    if em_density > 20:
        alerts.append(
            f"Em-dash density {em_density:.0f}‰ "
            f"(baseline: {baseline.get('em_dash_density', 0) * 1000:.0f}‰)"
        )

    # Dialogue density check (>chapter 10, near zero dialogue)
    if chapter > 10:
        dialogue_chars = sum(len(m.group()) for m in re.finditer(r'["""].+?["»"]', text))
        dialogue_ratio = dialogue_chars / total_chars
        if dialogue_ratio < 0.01:
            alerts.append("Dialogue density near zero -- possible character disappearance")

    return alerts
