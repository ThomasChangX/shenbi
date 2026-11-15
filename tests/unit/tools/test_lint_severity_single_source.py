"""Spec #105 T1c: severity-alternation single-source lint (red/green)."""

from __future__ import annotations

import ast

from tools.lint_severity_single_source import check_tree, main

BAD = 'import re\nRE = re.compile(r"BLOCKING|CRITICAL")\n'
BAD_KEY = 'import re\nx = re.search(r"severity: (MAJOR|CRITICAL|MINOR)", s)\n'
GOOD_COMPOSED = 'import re\nfrom shenbi.contracts.severity import AGGREGATE_VOCAB\nRE = re.compile("|".join(AGGREGATE_VOCAB))\n'
GOOD_KEYWORD = 'import re\nRE = re.compile(pattern=r"plain text")\n'
GOOD_SINGLE_WORD = 'import re\nRE = re.compile(r"BLOCKING")\n'
GOOD_NON_RE = 'x = "BLOCKING|CRITICAL"\n'


def _check(source: str) -> list[str]:
    return check_tree(ast.parse(source), "fake.py")


def test_alternation_literal_flags() -> None:
    assert _check(BAD), "两词交替字面量必须违例"
    assert _check(BAD_KEY), "三词交替字面量必须违例"


def test_composed_and_single_word_pass() -> None:
    assert _check(GOOD_COMPOSED) == []
    assert _check(GOOD_KEYWORD) == []
    assert _check(GOOD_SINGLE_WORD) == [], "单词字面量非交替——豁免口设计"
    assert _check(GOOD_NON_RE) == [], "非 re.* 调用不扫"


def test_main_zero_violations_on_current_tree() -> None:
    # 换装后仓库现状：单源外零违例（severity.py 豁免）
    assert main() == 0
