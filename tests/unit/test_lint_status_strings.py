"""The bare-status-string lint flags status-vocab dict values outside status.py."""

from __future__ import annotations

import ast

import pytest

from tools.lint_status_strings import find_violations


def _violations_in(source: str, filename: str = "x.py") -> list[str]:
    return find_violations(filename, ast.parse(source))


@pytest.mark.unit
def test_bare_pass_dict_value_outside_status_py_is_flagged() -> None:
    src = 'd = {"status": "PASS"}\n'
    assert any("PASS" in v for v in _violations_in(src, "src/shenbi/gates/g1.py"))


@pytest.mark.unit
def test_bare_state_and_classification_keys_are_flagged() -> None:
    """The three overloaded keys (status/state/classification) are all enforced."""
    assert _violations_in('d = {"state": "started"}\n', "src/shenbi/phase_runner.py")
    assert _violations_in('d = {"classification": "FAIL"}\n', "src/shenbi/scoring.py")


@pytest.mark.unit
def test_status_py_is_exempt() -> None:
    src = 'x = {"status": "PASS"}\n'
    assert _violations_in(src, "src/shenbi/status.py") == []


@pytest.mark.unit
def test_read_comparison_is_not_flagged() -> None:
    """Comparisons read external JSON; only the 'status' dict key is an emit site."""
    src = 'if result.get("status") == "FAIL":\n    pass\n'
    assert _violations_in(src, "src/shenbi/gates/g3.py") == []


@pytest.mark.unit
def test_check_item_s_value_is_not_flagged() -> None:
    """Gate check-item dicts use key 's' with status-like values by the
    thousand (e.g. {"id":"G3.1","s":"PASS"}). Only the 'status' key is flagged.
    """
    src = 'c.append({"id": "G3.1", "s": "PASS"})\n'
    assert _violations_in(src, "src/shenbi/gates/g3.py") == []


@pytest.mark.unit
def test_non_status_string_is_not_flagged() -> None:
    src = 'd = {"name": "chapter-1"}\n'
    assert _violations_in(src, "src/shenbi/gates/g1.py") == []


@pytest.mark.unit
def test_ternary_status_value_is_flagged() -> None:
    """Bare status literals inside a ternary value are emit sites too.

    Regression for the Copilot review on PR #6: the lint previously only matched
    ``ast.Constant`` values, so ``{"status": "PASS" if ok else "FAIL"}`` slipped
    through. Both branches must be caught.
    """
    src = 'd = {"status": "PASS" if ok else "FAIL"}\n'
    vios = _violations_in(src, "src/shenbi/gates/g1.py")
    assert any("'PASS'" in v for v in vios)
    assert any("'FAIL'" in v for v in vios)


@pytest.mark.unit
def test_ternary_status_assign_is_flagged() -> None:
    """Same gap for ``d["state"] = ...`` assignments with a ternary RHS."""
    src = 'd["state"] = "started" if x else "scored"\n'
    assert _violations_in(src, "src/shenbi/phase_runner.py")
