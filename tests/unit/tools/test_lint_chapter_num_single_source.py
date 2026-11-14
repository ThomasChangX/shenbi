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
def test_current_tree_is_green() -> None:
    assert lint.main() == 0


@pytest.mark.unit
def test_gates_scope_covers_g4_and_g6() -> None:
    files = {str(p.relative_to(lint.REPO)) for p in lint.GATES.rglob("*.py")}
    assert "src/shenbi/gates/g4/chapter_drafting.py" in files
    assert "src/shenbi/gates/g6.py" in files
    assert "src/shenbi/gates/g6_checks.py" in files
    assert not any("pipeline" in f for f in files)
