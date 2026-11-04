"""Spec #95 T3: 00189 blob replay — fixture integrity + assembly baseline.

Task 6 (freeze): hash-pin the frozen 00189 read blobs (real captured
artifacts, G0.9/G0.11) and record the CURRENT assembly baseline numbers.
Tasks 7-9 update expected fields as matrix/hooks/budget windows land —
every task keeps ``just test`` green (no cross-task red window).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parents[3] / "tests/fixtures/spec95/00189-reads"
MANIFEST = FIXTURES / "manifest.json"

# spec #95 r1.4: chars×0.80 ≈ tokens（01/02 实测 95,835/119,928）——估算规则钉死
TOKEN_RATIO = 0.80


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_fixture_manifest_present() -> None:
    m = _manifest()
    assert m["src_dispatch"].endswith("00189-shenbi-state-settling-ch041-a1.json")
    assert len(m["reads"]) == 15  # type: ignore[arg-type]


@pytest.mark.unit
def test_frozen_blobs_hash_pinned() -> None:
    """G0.11: fixture payloads byte-match the recorded sha256 (header excluded)."""
    m = _manifest()
    for entry in m["reads"]:  # type: ignore[union-attr]
        raw = (FIXTURES / entry["file"]).read_bytes()
        payload = raw.split(b"-->" + b"\n", 1)[1] if raw.startswith(b"<!--") else raw
        assert hashlib.sha256(payload).hexdigest() == entry["sha256_payload"], entry["file"]
    up = m["user_prompt"]  # type: ignore[index]
    raw = (FIXTURES / str(up["file"])).read_bytes()
    payload = raw.split(b"-->" + b"\n", 1)[1] if raw.startswith(b"<!--") else raw
    assert hashlib.sha256(payload).hexdigest() == up["sha256_payload"]


@pytest.mark.unit
def test_baseline_assembly_numbers_recorded() -> None:
    """r1.2/r1.4 anchor numbers, re-recorded at freeze time (Step 2 authority).

    user_prompt chars 119,928 / token estimate 95,835 (ratio 0.80) / two
    [TRUNCATED sentinels / hooks extractor kept 14/14 (zero narrowing).
    Tasks 7-9 will shift these — each task updates its own expected field.
    """
    m = _manifest()
    up = m["user_prompt"]  # type: ignore[index]
    assert up["chars"] == 119_928
    user_text = (FIXTURES / str(up["file"])).read_text(encoding="utf-8")
    est_tokens = int(up["chars"] * TOKEN_RATIO)  # type: ignore[operator]
    assert est_tokens == 95_942  # 119,928 × 0.80 ≈ recorded usage 95,835 (±0.1%)
    assert user_text.count("[TRUNCATED") == 2
    assert (
        "extractor:hooks_audit_scoped] 详情已按本章 plan/audit 点名裁剪：保留 14 段，省略 0 段"
        in user_text
    )
