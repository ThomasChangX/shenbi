"""spec #80 T12: lint_invariant_coverage 谓词测试。

tmp invariants.md/INDEX 喂正反例（F947 离线——零真实项目文件写入）；
repo 真实文档的 check() 必须零违规（just check 面的镜像断言）。
"""

from __future__ import annotations

from pathlib import Path

from tools.lint_invariant_coverage import (
    CURRENT_PHASE,
    check,
    mutant_test_name,
    parse_census,
)

GOOD_DOC = """# 不变量普查

| # | 维度 | 载体 | 声明 | 门检 | 审计 | 期相 | mutant 义务 |
|---|------|------|------|------|------|------|-------------|
| 1 | 恒等 identity | a.json | 备忘行 | XC.x | review-x | P1 | Yes（name-swap） |
| 2 | 持有与经手 props | b.json | 备忘行 | cp.x | review-y | P1 | Yes（prop-chain-break） |
| 3 | 枚举计数 counters | c.json | 备忘行 | cd.x | review-z | P1 | Yes（counter-dup） |
| 4 | 知识态 | — | — | — | — | P3 | No |
"""


def _full13(doc: str) -> str:
    """Pad a tmp census to the 13-row shape with not-yet-due P3 filler rows."""
    filler = "".join(f"| {n} | 补行{n} | — | — | — | — | P3 | No |\n" for n in range(5, 14))
    return doc + filler


GOOD_INDEX = """# Spec 执行索引

## 执行队列

### #80 · 某spec
- **文件**：a.md ｜ **状态**：Active
- **触及的不变量维度**：恒等 identity／持有与经手 props

### #81 · 另一spec
- **文件**：b.md ｜ **状态**：Active
- **触及的不变量维度**：无（观测域）
"""

GOOD_MUTANTS = (
    "def test_mutant_name_swap_killed_by_f15():\n    pass\n"
    "def test_mutant_prop_chain_break_killed_by_f16():\n    pass\n"
    "def test_mutant_counter_dup_killed_by_f17():\n    pass\n"
)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_current_phase_is_p1() -> None:
    assert CURRENT_PHASE == "P1"


def test_repo_real_docs_pass(tmp_path: Path) -> None:
    # 真实仓库三件套镜像 just check 面：零违规
    problems = check()  # 默认三件套=真实仓库文件
    assert problems == [], "\n".join(problems)


def test_good_tmp_corpus_passes(tmp_path: Path) -> None:
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(GOOD_DOC)),
        index=_write(tmp_path, "INDEX.md", GOOD_INDEX),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert problems == []


def test_p1_row_with_hole_fails(tmp_path: Path) -> None:
    bad = GOOD_DOC.replace("| a.json | 备忘行 | XC.x |", "| — | 备忘行 | XC.x |")
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(bad)),
        index=_write(tmp_path, "INDEX.md", GOOD_INDEX),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert any("载体" in p and "恒等" in p for p in problems)


def test_bad_phase_value_fails(tmp_path: Path) -> None:
    bad = GOOD_DOC.replace("| P3 | No |", "| P4 | No |", 1)
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(bad)),
        index=_write(tmp_path, "INDEX.md", GOOD_INDEX),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert any("期相" in p for p in problems)


def test_obligation_without_matching_test_fails(tmp_path: Path) -> None:
    mutants = GOOD_MUTANTS.replace("test_mutant_name_swap_killed_by_f15", "test_other")
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(GOOD_DOC)),
        index=_write(tmp_path, "INDEX.md", GOOD_INDEX),
        mutant_tests=_write(tmp_path, "m.py", mutants),
    )
    assert any("name-swap" in p for p in problems)


def test_p2_deferred_mutant_not_required_at_p1(tmp_path: Path) -> None:
    # P2 标记的补充 mutant（settle-illegal-op）在 CURRENT_PHASE=P1 不要求
    doc = GOOD_DOC.replace(
        "Yes（prop-chain-break）", "Yes（prop-chain-break；P2 增 settle-illegal-op）"
    )
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(doc)),
        index=_write(tmp_path, "INDEX.md", GOOD_INDEX),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert problems == []


def test_index_active_entry_missing_section_fails(tmp_path: Path) -> None:
    idx = GOOD_INDEX.replace("- **触及的不变量维度**：无（观测域）\n", "")
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(GOOD_DOC)),
        index=_write(tmp_path, "INDEX.md", idx),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert any("#81" in p and "触及的不变量维度" in p for p in problems)


def test_index_block_terminates_at_section_heading(tmp_path: Path) -> None:
    # audit-T12 I-1 回归钉：末条目节线被删 + 无 --- 分隔——块不得落穿 EOF
    # 吞掉登记约定段（该段自身含「触及的不变量维度」字面量，会掩盖缺节）
    idx = GOOD_INDEX.replace("- **触及的不变量维度**：无（观测域）\n", "")
    idx += "\n## 登记与编号约定\n\n- 活跃 spec 须含「触及的不变量维度」节\n"
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(GOOD_DOC)),
        index=_write(tmp_path, "INDEX.md", idx),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert any("#81" in p and "触及的不变量维度" in p for p in problems)


def test_section_listing_no_census_dim_fails(tmp_path: Path) -> None:
    idx = GOOD_INDEX.replace("恒等 identity／持有与经手 props", "不存在的维度甲／不存在的维度乙")
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(GOOD_DOC)),
        index=_write(tmp_path, "INDEX.md", idx),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert any("#80" in p and "普查表维度名" in p for p in problems)


def test_definition_leak_fails(tmp_path: Path) -> None:
    doc = GOOD_DOC + '\nop 集私定义 = "transfer"\n'
    problems = check(
        doc=_write(tmp_path, "inv.md", _full13(doc)),
        index=_write(tmp_path, "INDEX.md", GOOD_INDEX),
        mutant_tests=_write(tmp_path, "m.py", GOOD_MUTANTS),
    )
    assert any("只引用不定义" in p for p in problems)


def test_mutant_test_name_normalization() -> None:
    # R1-M13: census hyphen 形 ↔ 测试 underscore 形
    assert mutant_test_name("name-swap") == "test_mutant_name_swap_killed_by_"
    assert mutant_test_name("counter-dup") == "test_mutant_counter_dup_killed_by_"


def test_parse_census_shape() -> None:
    header, rows = parse_census()
    assert header[:2] == ["#", "维度"]
    assert len(rows) == 13
