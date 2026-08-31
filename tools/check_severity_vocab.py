"""AC2 recompute script (spec #34 T903): revision-decisions severity vocab rate.

Replaces the throwaway /tmp/t9x collector from the 2026-08-15 audit. Scans
``novel-output/**/*revision-decisions*.json`` severity values against the
registered RevisionSeverity domain; legacy production values are counted as
in-vocab via the read-side normalization map (docs/framework/status-vocab.md
消费侧容错映射). Exit 1 iff any severity value is out of vocab after mapping.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import get_args

from shenbi.contracts.enums import RevisionSeverity

REPO_ROOT = Path(__file__).resolve().parents[1]

# Keep in sync with g4/chapter_revision._LEGACY_SEVERITY (single registry row).
LEGACY_SEVERITY: dict[str, str] = {
    "blocking": "high",
    "critical": "high",
    "critical_per_audit": "high",
    "warning": "medium",
    "minor": "low",
    "info": "low",
    "none": "low",
    "observation": "low",
}

LEGAL = set(get_args(RevisionSeverity))

_SEVERITY_RE = re.compile(r'"severity":\s*"([^"]+)"')


def _iter_json_docs(text: str) -> list[object]:
    """Yield every concatenated top-level JSON doc in *text*.

    T9 noted some production files carry multiple docs; raw_decode walks them.
    """
    docs: list[object] = []
    dec = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        try:
            obj, end = dec.raw_decode(text, idx)
        except json.JSONDecodeError:
            break
        docs.append(obj)
        idx = end
    return docs


def collect_severities(tree: Path) -> list[str]:
    """Collect every severity value under tree's revision-decisions files."""
    values: list[str] = []
    files = [tree] if tree.is_file() else list(tree.rglob("*revision-decisions*.json"))
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        docs = _iter_json_docs(text)
        if docs:
            for doc in docs:
                if isinstance(doc, dict):
                    values.extend(_walk_severities(doc))
        else:
            # Strict parse failed outright (production files with trailing
            # commas) — regex-side collection, same as the T9 audit.
            values.extend(_SEVERITY_RE.findall(text))
    return values


def _walk_severities(node: object) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "severity" and isinstance(v, str):
                out.append(v)
            else:
                out.extend(_walk_severities(v))
    elif isinstance(node, list):
        for item in node:
            out.extend(_walk_severities(item))
    return out


def main(argv: list[str] | None = None) -> int:
    """Print the out-of-vocab severity rate; exit 1 iff any value escapes."""
    argv = argv if argv is not None else sys.argv[1:]
    tree = Path(argv[0]) if argv else REPO_ROOT / "novel-output"
    values = collect_severities(tree)
    out_of_vocab = [
        v for v in values if v not in LEGAL and LEGACY_SEVERITY.get(v.lower(), v) not in LEGAL
    ]
    rate = (len(out_of_vocab) / len(values) * 100) if values else 0.0
    print(f"severity entries: {len(values)}, out-of-vocab: {len(out_of_vocab)} ({rate:.1f}%)")
    if out_of_vocab:
        for v in sorted(set(out_of_vocab)):
            print(f"  out-of-vocab value: {v!r}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
