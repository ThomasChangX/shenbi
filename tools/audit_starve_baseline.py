"""Starvation-marker baseline for audit corpora (spec #109 r3, appendix A).

Single-source arbitration instrument for spec #109 acceptance #2: the
differential replay over a project's historical ``audits/`` corpus must
reproduce THIS script's counts. Prose numbers are not authoritative —
whatever this script prints on the pinned corpus is the baseline.

Corpus rule: dash-form dimension reports ``chapter-<N>-<dim>.md`` EXCLUDING
``review-summary`` files. Side tables (not in headline counts):
``chapter-<N>-review-summary.md`` and ``chapter-<N>.aggregate.md``.

Semantics pinned here (r2 postmortem — two prose-number rewrites died on
adversarial recounts, so the semantics live in executable form only):
  - file_level: starvation family matched anywhere in the file.
  - verdict_line: FIRST line per file matching the line-anchored bold form
    ``^**判定**：`` — only the captured value segment is evaluated (prose
    mentions of family words on other lines never count; the ch9
    world-rules false positive class). Variant no-colon forms (``判定为``)
    are deliberately OUT of the anchor — a design note for T4, not a
    baseline input.
  - verdict_pass: the first verdict value starts with ``通过`` (so
    ``不通过`` never counts) while the file is file-level starved — the
    "fabricated pass" metric.

Usage:
  uv run python tools/audit_starve_baseline.py <project_dir>/audits
  uv run python tools/audit_starve_baseline.py <dir> --manifest   # corpus pin
  uv run python tools/audit_starve_baseline.py <dir> --verify-manifest <sha>

Exit 0 = report printed; exit 1 = corpus manifest mismatch (corpus drifted —
re-baseline required before any acceptance arbitration).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

# spec #109 T4 (I2): the families/anchor live in src (packaged surface); the
# tool imports FROM src (tools→src, the repo-wide direction). Values are
# verbatim — the pinned corpus manifest is unaffected by this migration.
from shenbi.pipeline.audit_starve_family import (  # noqa: E402
    NARROW6,
    VERDICT_LINE_RE,
    WIDE12,
)
from shenbi.pipeline.audit_starve_family import (  # noqa: E402 — re-export
    T4_VARIANTS as T4_VARIANTS,  # noqa: PLC0414 — explicit re-export (spec #90 precedent)
)

DASH_FORM = re.compile(r"chapter-(\d+)-\w[\w-]*\.md$")
SUMMARY_FORM = re.compile(r"chapter-(\d+)-review-summary\.md$")
AGGREGATE_FORM = re.compile(r"chapter-(\d+)\.aggregate\.md$")

FAMILY: dict[str, re.Pattern[str]] = {
    "narrow6": re.compile("|".join(NARROW6)),
    "wide12": re.compile("|".join(WIDE12)),
}

VERDICT_LINE = VERDICT_LINE_RE
VERDICT_PASS = re.compile(r"^\*{0,2}\s*通过")


def _chapter_of(path: Path) -> int:
    m = DASH_FORM.match(path.name) or SUMMARY_FORM.match(path.name)
    m = m or AGGREGATE_FORM.match(path.name)
    if m is None:  # pragma: no cover — corpus filter guarantees a match
        raise ValueError(f"not a corpus file: {path.name}")
    return int(m.group(1))


def load_corpus(audits_dir: Path) -> tuple[list[tuple[int, Path, str]], dict[str, int]]:
    """Return (dash-form corpus [(chapter, path, text)], side-table counts)."""
    corpus: list[tuple[int, Path, str]] = []
    side: dict[str, int] = {"review_summaries": 0, "aggregate_files": 0, "other_md": 0}
    for path in sorted(audits_dir.glob("*.md")):
        if DASH_FORM.match(path.name) and not SUMMARY_FORM.match(path.name):
            corpus.append((_chapter_of(path), path, path.read_text(encoding="utf-8")))
        elif SUMMARY_FORM.match(path.name):
            side["review_summaries"] += 1
        elif AGGREGATE_FORM.match(path.name):
            side["aggregate_files"] += 1
        else:
            side["other_md"] += 1
    return corpus, side


def manifest_sha256(corpus: list[tuple[int, Path, str]]) -> str:
    """Pin the corpus: sha256 over sorted per-file (content-hash, name) lines."""
    lines = sorted(
        f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {path.name}"
        for _ch, path, text in corpus
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def scan(corpus: list[tuple[int, Path, str]]) -> dict[str, dict[str, dict[str, int]]]:
    """Compute the three metrics per family, each split by chapter parity."""
    report: dict[str, dict[str, dict[str, int]]] = {}
    for fam_name, fam_re in FAMILY.items():
        file_level = {"total": 0, "even": 0, "odd": 0}
        verdict_starved = {"total": 0, "even": 0, "odd": 0}
        verdict_pass = {"total": 0, "even": 0, "odd": 0}
        for ch, _path, text in corpus:
            starved = bool(fam_re.search(text))
            verdict_m = VERDICT_LINE.search(text)
            value = verdict_m.group(1).strip() if verdict_m else ""
            v_starved = bool(fam_re.search(value))
            v_pass = bool(VERDICT_PASS.match(value)) and starved
            parity = "even" if ch % 2 == 0 else "odd"
            if starved:
                file_level["total"] += 1
                file_level[parity] += 1
            if v_starved:
                verdict_starved["total"] += 1
                verdict_starved[parity] += 1
            if v_pass:
                verdict_pass["total"] += 1
                verdict_pass[parity] += 1
        report[fam_name] = {
            "file_level_starved": file_level,
            "verdict_line_starved": verdict_starved,
            "verdict_pass_among_starved": verdict_pass,
        }
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry: print the baseline report, or pin/verify the corpus manifest."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audits_dir", type=Path, help="project audits/ directory to measure")
    parser.add_argument("--manifest", action="store_true", help="print corpus manifest sha256 only")
    parser.add_argument(
        "--verify-manifest", metavar="SHA", help="fail (exit 1) on manifest mismatch"
    )
    args = parser.parse_args(argv)

    audits_dir = args.audits_dir
    if not audits_dir.is_dir():
        print(f"not a directory: {audits_dir}", file=sys.stderr)
        return 1
    corpus, side = load_corpus(audits_dir)
    manifest = manifest_sha256(corpus)

    if args.verify_manifest is not None and args.verify_manifest != manifest:
        print(
            f"corpus manifest mismatch: expected {args.verify_manifest}, got {manifest} — "
            "corpus drifted, re-baseline required",
            file=sys.stderr,
        )
        return 1
    if args.manifest:
        print(manifest)
        return 0

    print(
        json.dumps(
            {
                "corpus_dir": str(audits_dir),
                "manifest_sha256": manifest,
                "dash_form_files": len(corpus),
                "side_tables": side,
                "metrics": scan(corpus),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
