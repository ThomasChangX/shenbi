"""Unrecoverable decisions JSON must classify as a retryable write failure.

probe3 (genre-config first run): ``_validate_json_output`` raised a bare
ValueError from ``_write_one``; the dispatch boundary catches
DispatchWriteFailureError/TruthFileParseError — a plain ValueError pierced
both, crashed the process (exit 1) and left the retry budget's attempt3
unconsumed. The corrupt content was never written (fail-loud intent), but
the failure must route through the retry classifier, not the process
boundary.
"""

from __future__ import annotations

import pytest

from shenbi.exceptions import DispatchWriteFailureError
from shenbi.pipeline.dispatch_helper import _write_parsed_outputs


@pytest.mark.unit
def test_unrecoverable_decisions_json_raises_dispatch_write_failure(tmp_path):
    parsed = {"genre-config-decisions.json": "NOT JSON AT ALL"}
    with pytest.raises(DispatchWriteFailureError) as exc_info:
        _write_parsed_outputs(
            "",
            ["genre-config-decisions.json"],
            tmp_path,
            skill="shenbi-genre-config",
            parsed=parsed,
        )
    assert exc_info.value.signature == "decisions_json_unrecoverable"
    # nothing persisted
    assert not (tmp_path / "genre-config-decisions.json").exists()


@pytest.mark.unit
def test_schema_incomplete_decisions_json_also_classified(tmp_path):
    """A recovered-but-schema-incomplete decisions object is the same
    failure class (ValueError from the validator) — same routing.
    """
    bad = '{"$schema": "shenbi-decisions-v1", "selections": "not-an-array"} trailing'
    parsed = {"genre-config-decisions.json": bad}
    with pytest.raises(DispatchWriteFailureError) as exc_info:
        _write_parsed_outputs(
            "",
            ["genre-config-decisions.json"],
            tmp_path,
            skill="shenbi-genre-config",
            parsed=parsed,
        )
    assert exc_info.value.signature == "decisions_json_unrecoverable"
