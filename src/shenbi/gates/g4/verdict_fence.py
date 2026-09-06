"""Verdict fence envelope — T1201 (spec #45 R1).

The resonance/audit report verdict and resonance score are only adopted from
a machine-written fenced block at report level:

```
```verdict
判定: <token>
共振: <N>/100
```
```

Line-anchored tokenize: the block opens with a line that is exactly
`` ```verdict `` and closes at the next line that is exactly `` ``` ``. When
several fenced blocks exist, the LAST one wins (machine output is appended
last). Verdict/score pattern hits outside the fence are logged as suspected
injection and NOT adopted.

Legacy reports (pre-fence) degrade to the last non-quote (``> ``) match in
the whole document plus a WARN — quote lines are echoes of reviewed (i.e.
untrusted) chapter text, and a report's own verdict line always appears
after the evidence it cites.
"""

from __future__ import annotations

import re

import structlog

log = structlog.get_logger(__name__)

FENCE_RE = re.compile(r"^```verdict$\n(.*?)^```$", re.MULTILINE | re.DOTALL)

_VERDICT_IN_FENCE_RE = re.compile(r"判定\s*[:：]\s*(\S+)")
_SCORE_IN_FENCE_RE = re.compile(r"共振[:：]\s*(\d+)\s*/\s*100")

# Legacy fallback patterns for the resonance score (chapter_loop's former
# four modes), applied with the same last-non-quote strategy.
_LEGACY_SCORE_PATTERNS = (
    re.compile(r"\*\*Resonance\s*Score\*\*:\s*(\d+)", re.IGNORECASE),
    re.compile(r"(?:Score|resonance_score)\s*:\s*(\d+)", re.IGNORECASE),
    re.compile(r"\((\d+)\s*/\s*100\)"),
)

_QUOTE_PREFIX = ">"

# Legacy supplement patterns preserved from the former _GAP_VERDICT_PATTERNS:
# markdown bold (``**判定**: 通过``) and English prefix (``Verdict: 通过``).
_VERDICT_LEGACY_PATTERNS = [
    _VERDICT_IN_FENCE_RE,
    re.compile(r"\*\*判定\*\*\s*[:：]\s*(\S+)"),
    re.compile(r"Verdict\s*[:：]\s*(\S+)"),
]


def extract_fence(text: str) -> str | None:
    """Return the content of the LAST ```verdict fenced block, or None."""
    matches = FENCE_RE.findall(text)
    return matches[-1] if matches else None


def _last_non_quote_match(
    patterns: tuple[re.Pattern[str], ...] | list[re.Pattern[str]], text: str
) -> re.Match[str] | None:
    found: re.Match[str] | None = None
    for line in text.splitlines():
        if not line.lstrip().startswith(_QUOTE_PREFIX):
            for pattern in patterns:
                m = pattern.search(line)
                if m:
                    found = m
    return found


def match_verdict_scoped(text: str) -> str | None:
    """Adopt a verdict token from the fence envelope; legacy fallback otherwise.

    Fence hit outside the envelope (or a legacy non-quote hit) logs a WARN so
    suspected injection is observable, but only the fence/legacy value is
    returned.
    """
    fence = extract_fence(text)
    if fence is not None:
        m = _VERDICT_IN_FENCE_RE.search(fence)
        if m:
            return m.group(1)
        log.warning("verdict_fence_block_missing_verdict_line")
        return None
    m = _last_non_quote_match(_VERDICT_LEGACY_PATTERNS, text)
    if m is None:
        return None
    log.warning("legacy_report_no_envelope", verdict=m.group(1))
    return m.group(1)


def match_score_scoped(text: str) -> int | None:
    """Adopt the resonance score from the fence envelope; legacy fallback."""
    fence = extract_fence(text)
    if fence is not None:
        m = _SCORE_IN_FENCE_RE.search(fence)
        if m:
            return int(m.group(1))
        log.warning("verdict_fence_block_missing_score_line")
        return None
    m = _last_non_quote_match(list(_LEGACY_SCORE_PATTERNS), text)
    if m is None:
        return None
    log.warning("legacy_report_no_envelope_score", score=m.group(1))
    return int(m.group(1))
