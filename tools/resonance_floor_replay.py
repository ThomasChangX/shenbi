#!/usr/bin/env python3
"""Offline resonance-floor replay tool (spec #106 AC2/AC3 evidence).

--replay: recompute the dynamic floor per scored chapter against the real
trend file and print ch | score | floor | source | would_route plus the
ignition rate (calibration reproducibility, NOT validity proof — validity
belongs to #115's external anchors).

--diff-route: SAME-SNAPSHOT code-level differential — for every evaluable
chapter compute the route twice: (a) the pre-#106 expression
``route_chapter_revision(*collect_audit_issues(...))`` and (b) the same
expression under the new wiring with mode=shadow (shadow never changes the
route). Starved audit artifacts (#109 bundle follower reports) are the SAME
input on both sides, so they can only affect would_route event fields, never
the diff. We deliberately do NOT reconcile against pipeline-state.json's
historical route values: re-review overwrites and starved-report noise make
that diff non-zero for reasons unrelated to #106.

tools/ scripts may print (report_longitudinal.py precedent); this is not
src/shenbi/ framework code.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shenbi.pipeline.resonance_policy import effective_resonance_floor, trend_rows_full
from shenbi.pipeline.state import PipelineConfig


def replay_floors(project_dir: Path | str) -> list[dict[str, object]]:
    """Per scored chapter: dynamic floor + would_route (read-only)."""
    project_dir = Path(project_dir)
    trend = project_dir / "truth" / "resonance_trend.md"
    config = PipelineConfig()
    rows = trend_rows_full(trend) if trend.exists() else []
    out: list[dict[str, object]] = []
    cold_min = 8
    prior_scored = 0
    for ch, overall, _ov in rows:
        if overall is None:
            continue
        fc = effective_resonance_floor(project_dir, ch, config)
        if prior_scored >= cold_min or fc.source == "p25":
            pass  # evaluable: floor computation itself carries the semantics
        out.append(
            {
                "chapter": ch,
                "score": overall,
                "floor": fc.floor,
                "source": fc.source,
                "would_route": overall < fc.floor,
            }
        )
        prior_scored += 1
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --replay / --diff-route (read-only)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=str)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--replay", action="store_true", help="per-chapter floor replay")
    mode.add_argument("--diff-route", action="store_true", help="same-snapshot route differential")
    args = parser.parse_args(argv)
    project_dir = Path(args.project_dir)

    if args.replay:
        rows = replay_floors(project_dir)
        evaluable = [r for r in rows if r["source"] == "p25"]
        ignited = [r for r in rows if r["would_route"]]
        for r in rows:
            print(
                f"ch{r['chapter']:>3} | score={r['score']:>5} | floor={r['floor']:>6.2f} "
                f"| source={r['source']:<15} | would_route={r['would_route']}"
            )
        cold = len(rows) - len(evaluable)
        rate = (
            f"{len(ignited)}/{len(evaluable)}={len(ignited) / len(evaluable):.1%}"
            if evaluable
            else "n/a"
        )
        print(f"\ncold-start chapters: {cold}; ignition rate: {rate}")
        print(f"ignited: {[r['chapter'] for r in ignited]}")
        return 0

    # --diff-route: same-snapshot code-level differential (see module docstring
    # for why we never reconcile against historical state.json routes). The
    # wired side runs the REAL _route_revision_after_resonance on a scratch
    # in-memory state with mode=shadow and reads the persisted route key —
    # not a re-derivation of the baseline expression.
    from shenbi.pipeline.chapter_loop import (  # noqa: PLC0415 -- lazy: keeps --replay import-light
        _route_revision_after_resonance,
        collect_audit_issues,
        route_chapter_revision,
    )
    from shenbi.pipeline.state import (  # noqa: PLC0415 -- lazy: keeps --replay import-light
        ChapterState,
        PipelineConfig,
        PipelineState,
    )

    rows = replay_floors(project_dir)
    diff = 0
    checked = 0
    for r in rows:
        ch = int(r["chapter"])  # type: ignore[arg-type]
        baseline = route_chapter_revision(*collect_audit_issues(project_dir, ch)).value
        scratch = PipelineState(config=PipelineConfig(resonance_policy={"mode": "shadow"}))
        scratch.chapter_loop.chapter_states[str(ch)] = ChapterState(
            resonance_score=int(r["score"])  # type: ignore[arg-type]
        )
        _route_revision_after_resonance(scratch, project_dir, ch)
        wired = scratch.chapter_loop.chapter_states[str(ch)].audit_results["revision_route"]
        checked += 1
        if baseline != wired:
            diff += 1
            print(f"ch{ch}: route diff {baseline} != {wired}")
    print(f"route-diff: {diff} (checked {checked} chapters, shadow wiring vs baseline expression)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
