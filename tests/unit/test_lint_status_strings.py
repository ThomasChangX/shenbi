"""The bare-status-string lint (spec #34 T3 inversion): only enum members are legal.

Updated from the pre-spec-#34 semantics: the ``s`` key is now enforced (T905
blind spot #1) and ANY bare string constant on the four keys is flagged —
in-vocabulary or not (F447: the old lint let unknown values escape by
construction).
"""

from __future__ import annotations

import ast

import pytest

from tools.lint_status_strings import _Visitor


def _violations_in(source: str, strict: bool = True) -> list[str]:
    v = _Visitor("src/shenbi/x.py", strict, frozenset(), source.splitlines())
    v.visit(ast.parse(source))
    return v.violations


@pytest.mark.unit
def test_bare_pass_dict_value_is_flagged() -> None:
    assert _violations_in('d = {"status": "PASS"}\n')


@pytest.mark.unit
def test_bare_state_and_classification_keys_are_flagged() -> None:
    assert _violations_in('d = {"state": "started"}\n')
    assert _violations_in('d = {"classification": "FAIL"}\n')


@pytest.mark.unit
def test_check_item_s_value_is_now_flagged() -> None:
    """T905: the ``s`` key blind spot is closed — bare values are violations."""
    assert _violations_in('c.append({"id": "G3.1", "s": "PASS"})\n')


@pytest.mark.unit
def test_unknown_value_also_flagged() -> None:
    """F447 inversion: out-of-vocab values no longer escape by construction."""
    assert _violations_in('d = {"s": "HARD_FAIL"}\n')


@pytest.mark.unit
def test_non_status_string_is_not_flagged() -> None:
    assert _violations_in('d = {"name": "chapter-1"}\n') == []


@pytest.mark.unit
def test_ternary_status_value_is_flagged() -> None:
    src = 'd = {"status": "PASS" if ok else "FAIL"}\n'
    vios = _violations_in(src)
    assert any("'PASS'" in v for v in vios)
    assert any("'FAIL'" in v for v in vios)


@pytest.mark.unit
def test_ternary_status_assign_is_flagged() -> None:
    src = 'd["state"] = "started" if x else "scored"\n'
    assert _violations_in(src)


@pytest.mark.unit
def test_read_comparison_is_not_flagged() -> None:
    src = 'if result.get("status") == "FAIL":\n    pass\n'
    assert _violations_in(src) == []


@pytest.mark.unit
def test_lookup_key_inside_value_expr_not_flagged() -> None:
    src = 'd = {"status": rec.get("status")}\n'
    assert _violations_in(src) == []
