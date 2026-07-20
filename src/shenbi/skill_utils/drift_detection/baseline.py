"""Establish linguistic baseline from first N chapters (spec §3.5, Task 5a).

The baseline is the reference point for all subsequent drift detection.
It is computed from the first 3 chapters (or caller-specified chapter list),
aggregated, and persisted to ``style/linguistic_baseline.json`` via
:func:`shenbi.safe_write.safe_write`.

Wire-in point: called from ``_run_context_assembly`` or the chapter loop
after chapter 3 completes.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from shenbi.safe_write import safe_write
from shenbi.skill_utils.drift_detection.linguistic_drift import (
    compute_linguistic_metrics,
)


def establish_baseline(project_dir: Path | str, chapters: list[int]) -> dict[str, float]:
    """Compute linguistic baseline from specified chapters.

    Reads chapter prose from ``chapters/chapter-{N}.md``, computes the five
    pragmatic alarm metrics per chapter via :func:`compute_linguistic_metrics`,
    then aggregates by averaging across chapters. Persists the result to
    ``style/linguistic_baseline.json`` via :func:`safe_write`.

    Args:
        project_dir: Root directory of the novel project.
        chapters: List of chapter numbers to use for the baseline (typically
            ``[1, 2, 3]``).

    Returns:
        A dict of averaged metric values keyed by metric name
        (``system_term_density``, ``em_dash_density``, etc.).

    Raises:
        FileNotFoundError: If none of the requested chapter files exist.
    """
    project_dir = Path(project_dir)

    # Collect metrics from each source chapter
    all_metrics: list[dict[str, float]] = []
    for ch in chapters:
        chapter_file = project_dir / "chapters" / f"chapter-{ch}.md"
        if not chapter_file.exists():
            continue
        text = chapter_file.read_text(encoding="utf-8")
        metrics = compute_linguistic_metrics(text, project_dir=project_dir)
        all_metrics.append(metrics)

    if not all_metrics:
        raise FileNotFoundError(
            f"No chapter files found for baseline chapters {chapters} in {project_dir / 'chapters'}"
        )

    # Aggregate: average each numeric metric across chapters
    metric_keys = [
        "system_term_density",
        "em_dash_density",
        "short_sentence_chain_density",
        "pattern_density",
        "dialogue_density",
    ]
    baseline: dict[str, float] = {}
    for key in metric_keys:
        values = [m[key] for m in all_metrics if key in m]
        baseline[key] = round(statistics.mean(values), 4) if values else 0.0

    # Also store total_chars for reference (sum, not average)
    baseline["total_chars"] = sum(m.get("total_chars", 0) for m in all_metrics)

    # Persist to style/linguistic_baseline.json
    baseline_path = project_dir / "style" / "linguistic_baseline.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    safe_write(
        baseline_path,
        json.dumps(baseline, indent=2, ensure_ascii=False),
    )

    return baseline
