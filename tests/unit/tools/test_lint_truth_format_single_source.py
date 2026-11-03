"""Spec #85 T9 — AST lint for truth-format single source (unit tests)."""

from __future__ import annotations

import ast

import pytest

from tools import lint_truth_format_single_source as lt


def _findings_for(source: str) -> list[str]:
    tree = ast.parse(source)
    out: list[str] = []
    lt.lint_tree("mem://fake.py", tree, out)
    return out


@pytest.mark.unit
def test_bare_hook_literal_regex_position_flagged() -> None:
    src = "import re\n\n_X = re.compile(r'MH\\d+')\n"
    assert any("hook-family" in f for f in _findings_for(src))


@pytest.mark.unit
def test_module_bare_constant_thread_token_flagged() -> None:
    src = "_TOKEN = r'[A-Za-z]+\\d{1,3}'\n"
    assert any("thread-family" in f and "bare" in f for f in _findings_for(src))


@pytest.mark.unit
def test_abc_charset_thread_flagged() -> None:
    src = "import re\n\n_T = re.compile(r'(?<![A-Za-z0-9-])([ABC]\\d{1,3})')\n"
    assert any("thread-family" in f for f in _findings_for(src))


@pytest.mark.unit
def test_composite_with_clean_reference_exempt() -> None:
    src = (
        "import re\n"
        "from shenbi.truth_format import THREAD_ID_RE\n"
        "_H = re.compile(rf'^(#{{2,6}})\\s+({THREAD_ID_RE.pattern})')\n"
    )
    assert _findings_for(src) == []


@pytest.mark.unit
def test_composite_with_dialect_in_constant_segment_flagged() -> None:
    src = (
        "import re\n"
        "from shenbi.truth_format import THREAD_ID_RE\n"
        "_H = re.compile(rf'({THREAD_ID_RE.pattern})|(?:MH\\d+)')\n"
    )
    assert any("hook-family" in f for f in _findings_for(src))


@pytest.mark.unit
def test_cpzone_enum_and_wordlist_not_flagged() -> None:
    # 非 regex 位/值无数字形态——不命中（scan-position 口径）
    src = "X = 'CPZone'\nY = 'MH-'\nZ = '优先级 P0'\n"
    assert _findings_for(src) == []


@pytest.mark.unit
def test_generic_charclass_blind_spot_registered() -> None:
    # 盲区①：泛式不命中（显式接受）
    src = "import re\n\n_G = re.compile(r'[A-Z]{2,4}-\\d+')\n"
    assert _findings_for(src) == []


@pytest.mark.unit
def test_real_tree_zero_violations() -> None:
    rc = lt.main(["--quiet"])
    assert rc == 0, "current tree must be single-source clean (spec acceptance 3)"


# --- audit-T9 C1/I3: per-form parametrized detection (both spellings) ---


@pytest.mark.unit
@pytest.mark.parametrize(
    "dialect_src",
    [
        r"MH\d+",  # 旧方言拼写
        r"MH-?\d{1,4}",  # truth_format 规范族源串逐字拷贝（top recurrence vector）
        r"CP-?\d{1,4}",
        r"H-?\d{1,4}",
        r"P\d*-\d{1,4}",
        r"P\d+-",  # 量词变体（M5）
        r"CP-\d",
        r"[HM]\d",
    ],
)
def test_hook_dialect_forms_detected(dialect_src: str) -> None:
    src = f"import re\n\n_X = re.compile(r'{dialect_src}')\n"
    assert any("hook-family" in f for f in _findings_for(src)), dialect_src


@pytest.mark.unit
@pytest.mark.parametrize(
    "thread_src",
    [r"[ABC]\d{1,3}", r"[A-Za-z]+\d{1,3}", r"[a-zA-Z]+\d"],
)
def test_thread_dialect_forms_detected(thread_src: str) -> None:
    src = f"import re\n\n_T = re.compile(r'{thread_src}')\n"
    assert any("thread-family" in f for f in _findings_for(src)), thread_src
