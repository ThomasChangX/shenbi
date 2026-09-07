"""Bug-hunt expected-evidence content-level closure checker (spec #54 C16, F751/F754/T806).

Evidence-line grammar (spec T1.2): a line in scenario.md or expected/expected-output.md
that references ``tests/fixtures/<file>`` must be resolvable — the referenced file must
exist AND, when the line carries ``L<digits>`` (line pointer) or a CJK anchor text
(>= 4 chars in quotes 「」or ""), that pointer must resolve inside the fixture content.

Scan target: every ``bug-hunt`` dir under tests/tiers/t1-skill/** (including
``_template`` — F751's main battlefield). No ``_``-prefix skip.

Usage:
  uv run python tools/check_bug_hunt_evidence.py [--warn-only]
Exit code: 0 = no violations, 1 = violations found (unless --warn-only).
"""

import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
T1 = PROJECT / "tests" / "tiers" / "t1-skill"
FIXTURES = PROJECT / "tests" / "fixtures"

_FIXTURE_REF_RE = re.compile(r"tests/fixtures/[\w\-/]+(?:\.\w+)?")
_LINE_PTR_RE = re.compile(r"\bL(\d+)\b")
# Anchors: any quote style (「」/""/""/straight ASCII). ASCII quotes are the
# dominant evidence-quoting style in the existing corpus (F751 fabrications
# quoted chapter text in straight quotes); a quoted span with >= 4 non-space
# characters on a fixture-ref line is an evidence anchor and must resolve.
_MIN_ANCHOR_CHARS = 4

_QUOTED_RES = (
    re.compile(r"「([^「」]{4,})」"),
    re.compile(r"“([^“”]{4,})”"),
    re.compile(r"\"([^\"\n]{4,})\""),
)


def _find_anchor(line: str) -> str | None:
    """Longest quoted span on the line with >= _MIN_ANCHOR_CHARS non-space chars."""
    best: str | None = None
    for rx in _QUOTED_RES:
        for m in rx.finditer(line):
            span = m.group(1)
            if len("".join(span.split())) >= _MIN_ANCHOR_CHARS and (
                best is None or len(span) > len(best)
            ):
                best = span
    return best


def parse_evidence_lines(text: str) -> list[tuple[str, str | None, str | None]]:
    """Extract (fixture_rel, lineno_or_None, anchor_or_None) from a scenario/expected text."""
    out: list[tuple[str, str | None, str | None]] = []
    for line in text.splitlines():
        refs = _FIXTURE_REF_RE.findall(line)
        if not refs:
            continue
        lineno_m = _LINE_PTR_RE.search(line)
        anchor = _find_anchor(line)
        for ref in refs:
            out.append(
                (
                    ref,
                    lineno_m.group(1) if lineno_m else None,
                    anchor,
                )
            )
    return out


def verify_scenario(skill_bug_hunt_dir: Path, fixtures_root: Path) -> list[str]:
    """Return violation strings for one skill's bug-hunt dir (empty = clean)."""
    violations: list[str] = []
    targets = [
        skill_bug_hunt_dir / "input" / "scenario.md",
        skill_bug_hunt_dir / "expected" / "expected-output.md",
    ]
    try:
        label = str(skill_bug_hunt_dir.relative_to(PROJECT))
    except ValueError:
        label = str(skill_bug_hunt_dir)
    for doc in targets:
        if not doc.exists():
            continue
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError:
            continue
        for ref, lineno, anchor in parse_evidence_lines(text):
            fixture_path = fixtures_root / ref.removeprefix("tests/fixtures/")
            if not fixture_path.is_file():
                # directory refs are scope pointers, not evidence lines: an
                # existing non-empty dir is fine; empty/missing dirs are F789
                populated = fixture_path.is_dir() and any(
                    ch for ch in fixture_path.iterdir() if ch.name != ".gitkeep"
                )
                if not populated:
                    violations.append(f"{label}: {doc.name} references missing fixture {ref}")
                continue
            try:
                content_lines = fixture_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            if lineno is not None:
                n = int(lineno)
                if n < 1 or n > len(content_lines):
                    violations.append(
                        f"{label}: {doc.name} line pointer L{n} out of range for {ref} "
                        f"({len(content_lines)} lines)"
                    )
            if anchor is not None and anchor not in "\n".join(content_lines):
                violations.append(f"{label}: {doc.name} anchor「{anchor[:20]}」not found in {ref}")
    return violations


def main() -> int:
    """Scan every t1-skill bug-hunt dir and report evidence-closure violations."""
    warn_only = "--warn-only" in sys.argv
    violations: list[str] = []
    if T1.exists():
        for bug_hunt_dir in sorted(T1.rglob("bug-hunt")):
            if bug_hunt_dir.is_dir():
                violations.extend(verify_scenario(bug_hunt_dir, FIXTURES))
    for v in violations:
        print(f"VIOLATION: {v}")
    print(f"{len(violations)} violations")
    if violations and not warn_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
