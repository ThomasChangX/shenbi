"""Unit tests for tools/lint_chapter_num_single_source.py (spec #89 T2)."""

from __future__ import annotations

import ast

import pytest

import tools.lint_chapter_num_single_source as lint


@pytest.mark.unit
def test_inline_literal_hits() -> None:
    tree = ast.parse('m = re.search(r"chapter-(\\d+)", p.name)')
    hits: list[tuple[str, int]] = []
    lint.lint_tree(tree, "x.py", hits, allow_definition=False)
    assert hits == [("x.py", 1)]


@pytest.mark.unit
def test_constant_reference_and_fstring_are_clean() -> None:
    tree = ast.parse(
        "n = CHAPTER_NUM_RE.search(p.name)\n"
        'ok = f"chapter-{n}-decisions.json" in fp\n'
        'm = re.search(r"chapter-\\d+", s)\n'
    )
    hits: list[tuple[str, int]] = []
    lint.lint_tree(tree, "x.py", hits, allow_definition=False)
    assert hits == []  # 常量引用/f-string/无捕获组形态均不命中


@pytest.mark.unit
def test_definition_allowed_only_for_shared() -> None:
    tree = ast.parse('CHAPTER_NUM_RE = re.compile(r"chapter-(\\d+)")')
    hits: list[tuple[str, int]] = []
    lint.lint_tree(tree, "shared.py", hits, allow_definition=True)
    assert hits == []
    lint.lint_tree(tree, "g6.py", hits, allow_definition=False)
    assert hits == [("g6.py", 1)]


@pytest.mark.unit
def test_second_compile_and_embedded_compile_still_red_in_shared() -> None:
    # audit-T2 I4：放行仅限精确等值 re.compile——第二/内嵌形态仍红
    tree = ast.parse(
        'CHAPTER_NUM_RE = re.compile(r"chapter-(\\d+)")\n'
        'X = re.compile(r"chapter-(\\d+)-decisions\\.json")\n'
        'Y = foo.compile(r"chapter-(\\d+)")\n'
    )
    hits: list[tuple[str, int]] = []
    lint.lint_tree(tree, "shared.py", hits, allow_definition=True)
    assert hits == [("shared.py", 2), ("shared.py", 3)]


@pytest.mark.unit
def test_split_subn_and_keyword_pattern_hit() -> None:
    tree = ast.parse(
        'a = re.split(r"chapter-(\\d+)", s)\n'
        'b = re.subn(r"chapter-(\\d+)", "x", s)\n'
        'c = re.search(pattern=r"chapter-(\\d+)", string=s)\n'
    )
    hits: list[tuple[str, int]] = []
    lint.lint_tree(tree, "x.py", hits, allow_definition=False)
    assert hits == [("x.py", 1), ("x.py", 2), ("x.py", 3)]


@pytest.mark.unit
def test_current_tree_is_green() -> None:
    assert lint.main() == 0


@pytest.mark.unit
def test_gates_scope_covers_g4_and_g6() -> None:
    files = {str(p.relative_to(lint.REPO)) for p in lint.GATES.rglob("*.py")}
    assert "src/shenbi/gates/g4/chapter_drafting.py" in files
    assert "src/shenbi/gates/g6.py" in files
    assert "src/shenbi/gates/g6_checks.py" in files
    assert not any("pipeline" in f for f in files)
