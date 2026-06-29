"""Repo lints: body-ban, loader-uniqueness, terminology, section-headers."""

from __future__ import annotations

import pytest

from tools.lint_repo_consistency import (
    find_banned_synonyms,
    find_body_contract_blocks,
    find_extra_contract_key_readers,
    find_section_header_deviants,
)


@pytest.mark.unit
def test_body_reads_block_in_skills_is_flagged() -> None:
    md = "# X\n\n## 数据契约\n\n- **Reads:** `a.md`\n"
    assert find_body_contract_blocks([("skills/x/SKILL.md", md)]) == ["skills/x/SKILL.md"]


@pytest.mark.unit
def test_archived_rounds_are_exempt() -> None:
    md = "# X\n\n- **Reads:** `a.md`\n"
    assert find_body_contract_blocks([("tests/rounds/archived/r1/SKILL.md", md)]) == []


@pytest.mark.unit
def test_auto_generated_body_block_is_exempt() -> None:
    md = (
        "<!-- AUTO-GENERATED from frontmatter — do not edit -->\n\n## 数据契约\n\n"
        "- **Reads:** a.md\n- **Writes:** b.md\n- **Updates:** none\n\n"
        "<!-- END AUTO-GENERATED -->\n\n## 流程\n"
    )
    assert find_body_contract_blocks([("skills/x/SKILL.md", md)]) == []


@pytest.mark.unit
def test_handwritten_block_alongside_auto_gen_is_flagged() -> None:
    """A second, hand-written contract block must not hide behind the banner."""
    md = (
        "<!-- AUTO-GENERATED from frontmatter — do not edit -->\n\n## 数据契约\n\n"
        "- **Reads:** a.md\n\n<!-- END AUTO-GENERATED -->\n\n"
        "## 铁律\n\n- **Writes:** secret.md\n"
    )
    assert find_body_contract_blocks([("skills/x/SKILL.md", md)]) == ["skills/x/SKILL.md"]


@pytest.mark.unit
def test_hook_pool_synonym_flagged() -> None:
    md = "use the hook pool to ...\n"
    assert "hook pool" in find_banned_synonyms([("skills/x/SKILL.md", md)])[0][1]


@pytest.mark.unit
def test_banned_output_header_flagged() -> None:
    md = "# X\n\n## 输出契约\n\nbody\n"
    assert ("skills/x/SKILL.md", "输出契约") in find_section_header_deviants(
        [("skills/x/SKILL.md", md)]
    )


@pytest.mark.unit
def test_legitimate_non_canonical_header_not_flagged() -> None:
    """Skills legitimately have many section titles; only banned ones are drift."""
    md = "# X\n\n## 检查执行\n\n## 缺陷证据格式\n"
    assert find_section_header_deviants([("skills/x/SKILL.md", md)]) == []


@pytest.mark.unit
def test_loader_uniqueness_flags_contract_key_outside_contract_py() -> None:
    py = 'd = yload(p); c = d["contract"]\n'
    assert (
        "src/shenbi/other.py"
        in find_extra_contract_key_readers(
            [("src/shenbi/other.py", py), ("src/shenbi/contract.py", py)]
        )[0]
    )
