"""match_tropes.py — Deterministic trope-matching helpers for trope detection.

Reads the ``tropeInventory`` schema from a genre-config fixture and counts how
many story beats match each trope's signatures via keyword substring match.

NOTE: production uses LLM semantic matching in the scoring agent; this
deterministic helper supports the trope-detection unit test (spec §10) and
fixture validation. Keyword match is the testable proxy.

Usage:
  python -m shenbi.skill_utils.trope_detection \
      --config tests/fixtures/genre-config-example.json --beats-file beats.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


@dataclass(frozen=True)
class Trope:
    trope: str
    signatures: list[str]
    overuse_threshold: int
    rewrite_hint: str


class TropeMatch(TypedDict):
    trope: str
    hits: int
    overuse: bool
    overuse_threshold: int
    rewrite_hint: str


def count_trope_hits(beats: list[str], trope: Trope) -> int:
    """Count story beats that match any signature (keyword substring match).

    A beat is counted at most once even if it matches multiple signatures.
    """
    hits = 0
    for beat in beats:
        if any(sig in beat for sig in trope.signatures):
            hits += 1
    return hits


def trope_overuse(hit_count: int, trope: Trope) -> bool:
    """True when the trope appears more often than its overuse_threshold."""
    return hit_count > trope.overuse_threshold


def load_trope_inventory(config_path: str | Path) -> list[Trope]:
    """Load the ``tropeInventory`` array from a genre-config JSON file."""
    data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    raw = data.get("tropeInventory", [])
    return [
        Trope(
            trope=item["trope"],
            signatures=item["signatures"],
            overuse_threshold=item["overuse_threshold"],
            rewrite_hint=item.get("rewrite_hint", ""),
        )
        for item in raw
    ]


def match_all(beats: list[str], tropes: list[Trope]) -> list[TropeMatch]:
    """Run every trope against the beats, returning per-trope result dicts."""
    results: list[TropeMatch] = []
    for t in tropes:
        hits = count_trope_hits(beats, t)
        results.append(
            {
                "trope": t.trope,
                "hits": hits,
                "overuse": trope_overuse(hits, t),
                "overuse_threshold": t.overuse_threshold,
                "rewrite_hint": t.rewrite_hint,
            }
        )
    return results


def _read_beats(beats_path: str | Path) -> list[str]:
    """Read beats from a file, one non-empty beat per line."""
    text = Path(beats_path).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="match_tropes",
        description="Count trope signature hits in a list of story beats.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Genre-config JSON file containing a 'tropeInventory' array.",
    )
    parser.add_argument(
        "--beats-file",
        required=True,
        help="Text file of story beats, one beat per line.",
    )
    args = parser.parse_args()

    tropes = load_trope_inventory(args.config)
    beats = _read_beats(args.beats_file)
    results = match_all(beats, tropes)

    output = {
        "sample": {"beats": len(beats), "tropes": len(tropes)},
        "results": results,
    }
    sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
