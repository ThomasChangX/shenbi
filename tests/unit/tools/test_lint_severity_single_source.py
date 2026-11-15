"""Spec #105 T1c: severity-alternation single-source lint (red/green)."""

from __future__ import annotations

import ast

from tools.lint_severity_single_source import check_tree, main

BAD = 'import re\nRE = re.compile(r"BLOCKING|CRITICAL")\n'
BAD_KEY = 'import re\nx = re.search(r"severity: (MAJOR|CRITICAL|MINOR)", s)\n'
GOOD_COMPOSED = 'import re\nfrom shenbi.contracts.severity import AGGREGATE_VOCAB\nRE = re.compile("|".join(AGGREGATE_VOCAB))\n'
GOOD_KEYWORD = 'import re\nRE = re.compile(pattern=r"plain text")\n'
BAD_KEYWORD = 'import re\nRE = re.compile(pattern=r"BLOCKING|CRITICAL")\n'  # M-2: keyword 形红钉
BAD_NONADJACENT = (
    'import re\nRE = re.compile(r"(?:BLOCKING|FAIL|CRITICAL)")\n'  # M-1: 非相邻交替红钉
)
BAD_ALIAS = 'import re as _re\nRE = _re.compile(r"BLOCKING|CRITICAL")\n'  # S8 I-2 alias red pin
BAD_FROM_IMPORT = (
    'from re import compile as _c\nRE = _c(r"BLOCKING|CRITICAL")\n'  # S8 r2 from-import
)
GOOD_SINGLE_WORD = 'import re\nRE = re.compile(r"BLOCKING")\n'
GOOD_NON_RE = 'x = "BLOCKING|CRITICAL"\n'


def _check(source: str) -> list[str]:
    return check_tree(ast.parse(source), "fake.py")


def test_alternation_literal_flags() -> None:
    assert _check(BAD), "两词交替字面量必须违例"
    assert _check(BAD_KEY), "三词交替字面量必须违例"
    assert _check(BAD_KEYWORD), "keyword 形必须违例（M-2 红钉）"
    assert _check(BAD_NONADJACENT), "非相邻交替必须违例（M-1 段计数）"
    assert _check(BAD_ALIAS), "import re as _re 别名必须违例（S8 I-2）"
    assert _check(BAD_FROM_IMPORT), "from re import compile as _c 必须违例（S8 r2）"


def test_composed_and_single_word_pass() -> None:
    assert _check(GOOD_COMPOSED) == []
    assert _check(GOOD_KEYWORD) == []
    assert _check(GOOD_SINGLE_WORD) == [], "单词字面量非交替——豁免口设计"
    assert _check(GOOD_NON_RE) == [], "非 re.* 调用不扫"


def test_main_zero_violations_on_current_tree() -> None:
    # 换装后仓库现状：单源外零违例（severity.py 豁免）
    assert main() == 0
