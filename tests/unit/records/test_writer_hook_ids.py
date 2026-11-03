"""Spec #85 T2 — M6 red test: records/writer second dialect copy swapped."""

from __future__ import annotations

import pytest

from shenbi.records.writer import _HOOK_ID_RE  # pyright: ignore[reportPrivateImportUsage]


@pytest.mark.unit
def test_m6_writer_free_ids_not_mangled() -> None:
    """M6: writer.py kept a verbatim copy of truth_index's mangled pattern
    ("Same pattern as pipeline/truth_index.py"). The swap must yield full
    tokens, not second-character keys.
    """
    ids = [m.group(0) for m in _HOOK_ID_RE.finditer("MH01 与 CP-004")]
    assert ids == ["MH01", "CP-004"]
