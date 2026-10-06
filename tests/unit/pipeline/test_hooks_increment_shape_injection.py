r"""pending_hooks increment-shape injection: full stable-set ban (phase3 esc#1).

The #26 injection banned only type/trigger_condition/resolve_condition/
depends_on — the phase3 ch1 settle rewrote ``- plant_chapter`` (not banned
in the prompt, banned in the gate) and the retry feedback likewise failed
to name it, so three attempts converged nowhere. The injection and the
IncrementShapeError sanctioned text must render the FULL stable set from
the shared constant, and the cumulative-fields clause must say what
"restate" means (append, not replace).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.exceptions import IncrementShapeError
from shenbi.pipeline.dispatch_helper import (
    _hooks_increment_shape_injection,
    _write_parsed_outputs,
)
from shenbi.pipeline.truth_io import HOOKS_STABLE_FIELDS

_LIVE_HOOKS = """---
type: truth
category: state
---

# 伏笔池

## 详情

### MH05（余孽册的三本册子）

- hook_id: MH05
- plant_chapter: 2
"""


def _write(tmp_path: Path, block: str) -> None:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "pending_hooks.md").write_text(_LIVE_HOOKS, encoding="utf-8")
    _write_parsed_outputs(
        response=f"### FILE: staging/truth/pending_hooks.md\n{block}\n",
        output_paths=["staging/truth/pending_hooks.md"],
        project_dir=tmp_path,
        skill="shenbi-state-settling",
    )


class TestInjectionText:
    def test_every_stable_field_is_banned_by_name(self):
        text = _hooks_increment_shape_injection()
        for field in HOOKS_STABLE_FIELDS:
            assert field in text, f"injection must ban the stable field: {field}"

    def test_cumulative_clause_defines_restate_as_append(self):
        text = _hooks_increment_shape_injection()
        assert "证据/notes" in text
        assert "RESTATE" in text and "APPEND" in text


class TestSanctionedErrorText:
    def test_increment_shape_error_names_stable_fields(self, tmp_path):
        with pytest.raises(IncrementShapeError) as ei:
            _write(
                tmp_path, "## 详情\n\n### MH05（余孽册的三本册子）\n- last_reinforced: 第 1 章\n"
            )
        msg = str(ei.value)
        assert "plant_chapter" in msg
        assert "resolve_chapter" in msg
