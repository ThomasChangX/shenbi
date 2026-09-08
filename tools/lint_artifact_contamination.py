#!/usr/bin/env python3
"""Lint: production-artifact contamination checks (spec #56 C18 T2).

Four checks over the novel-output tree (default) or ``--tree DIR``:

(a) ``meta_narration`` — the 7-pattern meta-narration family leaked from
    the manual-era read-only sandbox workflow (F1171).
(b) ``manual_calc`` — manual-score self-certification: a "手动计算/手算"
    pattern co-occurring with a number in the same file (F1162/F1172).
(c) ``timestamp`` — same-file ISO-timestamp non-monotonicity, plus a
    cross-file fabricated-signature check: >=2 files sharing the *same
    full* ISO timestamp string that lands exactly on the hour
    (``HH:00:00``) — the framework writes ``datetime.now(UTC)`` real
    times, so duplicated on-the-hour stamps are the manual-era
    fabricated-batch family (F1163). Cross-file *disorder* alone is
    legal (revisions/re-runs) and is not flagged.
(d) ``state_reconcile`` — ``pipeline-state.json``
    ``chapter_loop.chapter_states.<N>.audit_results.audit_reports``
    (list of relative paths) reconciled against on-disk
    ``audits/chapter-<N>-*.md``; both the missing-path and the
    empty-container/missing-key branches are flagged (F1165).

Exemptions: ``tools/artifact-lint-exemptions.json`` maps check name to a
list of ``{"path": ..., "reason": ...}`` entries (paths relative to the
linted tree). Exempted findings are skipped and do not count as hits.

Exit codes: 0 when no non-exempt findings; 1 when there are; 2 on usage
errors (missing tree, malformed exemption entries).
``--baseline-out FILE`` writes the full finding list *including*
exempt-marked entries (``"exempt": true``) as JSON for before/after
comparison and exemption-bookkeeping reconciliation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TREE = REPO_ROOT / "novel-output"

#: F1171 7-pattern family — keep byte-identical with the spec.
META_NARRATION_PATTERNS: tuple[str, ...] = (
    "手动复制",
    "只读沙箱",
    "无法写入",
    "请手动",
    "manually copy",
    "read-only sandbox",
    "cannot write",
)

MANUAL_CALC_PATTERNS: tuple[str, ...] = ("手动计算", "手算")

Finding = dict[str, object]
ExemptionEntry = dict[str, str]
Exemptions = dict[str, list[ExemptionEntry]]

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_ON_THE_HOUR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:00:00Z$")
_NUMBER_RE = re.compile(r"\d")

#: A fabricated-signature group needs at least this many files sharing the stamp.
_SIGNATURE_MIN_FILES = 2

#: Binary/asset suffixes never scanned as text.
SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".db"}


def load_exemptions(repo_root: Path) -> Exemptions:
    """Load the per-check exemption list from ``tools/artifact-lint-exemptions.json``.

    Raises ``SystemExit(2)`` on malformed entries (missing ``path``/``reason``).
    """
    exemptions_file = repo_root / "tools" / "artifact-lint-exemptions.json"
    if not exemptions_file.exists():
        return {}
    try:
        data = json.loads(exemptions_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: malformed exemption JSON: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    out: Exemptions = {}
    for check, entries in data.items():
        checked: list[ExemptionEntry] = []
        for e in entries:
            if not isinstance(e, dict) or "path" not in e or "reason" not in e:
                print(
                    f"malformed exemption entry for check {check!r}: {e!r} "
                    "(needs 'path' and 'reason')",
                    file=sys.stderr,
                )
                raise SystemExit(2)
            checked.append({"path": str(e["path"]), "reason": str(e["reason"])})
        out[check] = checked
    return out


def _exempt_paths(exemptions: Exemptions) -> dict[str, set[str]]:
    return {check: {e["path"] for e in entries} for check, entries in exemptions.items()}


def _iter_text_files(root: Path) -> list[tuple[Path, str]]:
    pairs: list[tuple[Path, str]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix in SKIP_SUFFIXES:
            continue
        try:
            pairs.append((p, p.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, OSError):
            continue
    return pairs


def lint_tree(root: Path, *, exemptions: Exemptions | None = None) -> list[Finding]:
    """Return the non-exempt findings for ``root`` (paths relative to root)."""
    return [f for f in lint_tree_all(root, exemptions=exemptions) if not f["exempt"]]


def lint_tree_all(root: Path, *, exemptions: Exemptions | None = None) -> list[Finding]:
    """Return ALL findings for ``root``, exempt entries marked ``"exempt": True``."""
    exemptions = exemptions or {}
    exempt = _exempt_paths(exemptions)
    findings: list[Finding] = []
    ts_occurrences: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for path_obj, text in _iter_text_files(root):
        findings.extend(_scan_file(path_obj, root, text, ts_occurrences))

    for ts, occ in ts_occurrences.items():
        files = {rel for rel, _ in occ}
        if len(files) < _SIGNATURE_MIN_FILES or not _ON_THE_HOUR_RE.match(ts):
            continue
        detail = f"fabricated on-the-hour signature {ts} shared by {len(files)} files"
        for rel, line in occ:
            findings.append(
                {"check": "timestamp", "path": rel, "line": line, "detail": detail, "exempt": False}
            )

    # A linted tree may host several project trees (novel-output/xinghuo-ranqiong,
    # test-validation): reconcile every pipeline-state.json found at depth <= 1.
    state_roots: list[Path] = [root]
    if root.is_dir():
        state_roots += [d for d in sorted(root.iterdir()) if d.is_dir()]
    for state_root in state_roots:
        findings.extend(_lint_state_reconcile(state_root, root))

    for f in findings:
        if f["path"] in exempt.get(str(f["check"]), set()):
            f["exempt"] = True
    return findings


def _scan_file(
    path_obj: Path,
    root: Path,
    text: str,
    ts_occurrences: dict[str, list[tuple[str, int]]],
) -> list[Finding]:
    """Per-file checks: meta-narration (a), manual-calc (b), monotonicity (c).

    The spec counts files, not lines — one finding per file per check.
    """
    out: list[Finding] = []
    rel = str(path_obj.relative_to(root))
    lines = text.splitlines()
    meta_line = next(
        (i for i, ln in enumerate(lines, 1) if any(p in ln for p in META_NARRATION_PATTERNS)),
        None,
    )
    if meta_line is not None:
        out.append(
            {
                "check": "meta_narration",
                "path": rel,
                "line": meta_line,
                "detail": "meta-narration pattern present",
                "exempt": False,
            }
        )
    # Same-file co-occurrence: the pattern anywhere plus a digit anywhere.
    manual_line = next(
        (i for i, ln in enumerate(lines, 1) if any(p in ln for p in MANUAL_CALC_PATTERNS)),
        None,
    )
    if manual_line is not None and _NUMBER_RE.search(text):
        out.append(
            {
                "check": "manual_calc",
                "path": rel,
                "line": manual_line,
                "detail": "manual-calc self-certification",
                "exempt": False,
            }
        )
    for i, line in enumerate(lines, start=1):
        for m in _TS_RE.finditer(line):
            ts_occurrences[m.group(0)].append((rel, i))
    stamps = [m.group(0) for m in _TS_RE.finditer(text)]
    if stamps != sorted(stamps):
        line_no = _first_inversion_line(lines)
        out.append(
            {
                "check": "timestamp",
                "path": rel,
                "line": line_no,
                "detail": "same-file timestamps non-monotonic",
                "exempt": False,
            }
        )
    return out


def _first_inversion_line(lines: list[str]) -> int:
    """Line number of the first timestamp that breaks monotonic order."""
    prev: str | None = None
    for i, line in enumerate(lines, start=1):
        for m in _TS_RE.finditer(line):
            if prev is not None and m.group(0) < prev:
                return i
            prev = m.group(0)
    return 1


def _lint_state_reconcile(state_root: Path, tree_root: Path) -> list[Finding]:
    state_file = state_root / "pipeline-state.json"
    if not state_file.exists():
        return []
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    chapter_states: dict[str, dict[str, object]] = (state.get("chapter_loop") or {}).get(
        "chapter_states"
    ) or {}

    on_disk: dict[str, set[str]] = defaultdict(set)
    audits_dir = state_root / "audits"
    if audits_dir.is_dir():
        for p in audits_dir.glob("chapter-*.md"):
            m = re.match(r"chapter-(\d+)-", p.name)
            if m:
                on_disk[m.group(1)].add(str(p.relative_to(state_root)))

    findings: list[Finding] = []
    for ch, disk_paths in sorted(on_disk.items()):
        ch_state = chapter_states.get(ch) or {}
        audit_results = ch_state.get("audit_results") if isinstance(ch_state, dict) else None
        reported = set(
            (audit_results or {}).get("audit_reports") or []  # type: ignore[union-attr]
        )
        prefix = str(state_root.relative_to(tree_root))
        for missing in sorted(disk_paths - reported):
            findings.append(
                {
                    "check": "state_reconcile",
                    "path": f"{prefix}/{missing}" if prefix != "." else missing,
                    "line": 0,
                    "detail": (
                        f"on disk but not in chapter_states[{ch}].audit_results.audit_reports"
                    ),
                    "exempt": False,
                }
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry: lint a tree, optionally write a baseline JSON report."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.splitlines()[0] if doc else None)
    parser.add_argument(
        "--tree", type=Path, default=DEFAULT_TREE, help="tree to lint (default novel-output)"
    )
    parser.add_argument(
        "--baseline-out", type=Path, default=None, help="write full findings JSON here"
    )
    args = parser.parse_args(argv)

    if not args.tree.is_dir():
        print(f"error: tree does not exist: {args.tree}", file=sys.stderr)
        return 2

    exemptions = load_exemptions(REPO_ROOT)
    all_findings = lint_tree_all(args.tree, exemptions=exemptions)
    hits = [f for f in all_findings if not f["exempt"]]

    if args.baseline_out:
        args.baseline_out.parent.mkdir(parents=True, exist_ok=True)
        args.baseline_out.write_text(
            json.dumps(
                {
                    "tree": str(args.tree),
                    "exemptions_registered": {k: len(v) for k, v in exemptions.items()},
                    "total": len(hits),
                    "by_check": dict(Counter(str(f["check"]) for f in hits)),
                    "findings": all_findings,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {"total": len(hits), "by_check": dict(Counter(str(f["check"]) for f in hits))},
            ensure_ascii=False,
        )
    )
    for f in hits:
        print(f"{f['check']}: {f['path']}:{f['line']} {f['detail']}", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
