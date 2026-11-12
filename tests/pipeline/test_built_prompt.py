"""Spec #87 T1: BuiltPrompt NamedTuple — tuple-protocol compatibility.

The 63 existing destructure sites must keep working untouched; this pins
the NamedTuple contract (fields, unpacking incl. star, named access).
"""

import pytest

from shenbi.pipeline.dispatch_helper import BuiltPrompt


@pytest.mark.unit
def test_built_prompt_is_namedtuple_with_five_fields() -> None:
    assert issubclass(BuiltPrompt, tuple)
    assert BuiltPrompt._fields == (
        "system",
        "user",
        "output_paths",
        "reads_manifest",
        "raw_disk_reads",
    )


@pytest.mark.unit
def test_built_prompt_unpack_and_named_access() -> None:
    bp = BuiltPrompt("s", "u", ["p"], [{"r": 1}], {"d": "x"})

    a, b, c, d, e = bp  # 5-target destructure (the 63-site pattern)
    assert (a, b, c, d, e) == ("s", "u", ["p"], [{"r": 1}], {"d": "x"})

    *head, tail = bp  # star-unpack (test_dispatch_snapshot.py:55 pattern)
    assert head == ["s", "u", ["p"], [{"r": 1}]] and tail == {"d": "x"}

    assert bp.system == "s" and bp.raw_disk_reads == {"d": "x"}
    assert len(bp) == 5 and bp[0] == "s"
