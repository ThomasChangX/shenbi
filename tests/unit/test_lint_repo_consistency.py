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


@pytest.mark.unit
def test_dead_decisions_sidecar_clean_tree() -> None:
    """On the real repo (after T4), 0 dead decisions sidecars remain.

    Negative control: confirms the lint runs without error on a clean tree.
    """
    from tools.lint_repo_consistency import find_dead_decisions_sidecars

    dead = find_dead_decisions_sidecars()
    assert dead == [], f"expected 0 dead decisions sidecars after T4, got {dead}"


@pytest.mark.unit
def test_dead_decisions_sidecar_flags_synthetic_dead() -> None:
    """Positive control: a decisions.json write with no consumer IS flagged.

    Without this, a broken lint (e.g. isinstance(w, str) on dict-form writes)
    would pass the negative control via vacuous truth — exactly the dead-wire
    pattern spec §8.1 iron law forbids.
    """
    from tools.lint_repo_consistency import _is_dead_decisions_sidecar

    # A dict-form write (the actual repo form: {file: ..., mode: ...}).
    synthetic_write = {
        "file": "plans/chapter-N-totally-dead-decisions.json",
        "mode": "create_or_overwrite",
    }
    all_reads: set[str] = set()  # no skill reads it
    g4_skills: set[str] = set()  # not G4-validated
    code_blob: str = ""  # no code references (param type is str, not set — basedpyright strict)
    assert (
        _is_dead_decisions_sidecar(synthetic_write, "shenbi-fake", all_reads, g4_skills, code_blob)
        is True
    )


@pytest.mark.unit
def test_dead_decisions_sidecar_spares_g4_validated() -> None:
    """A decisions.json write consumed by G4 is NOT flagged (Task 4 disposition)."""
    from tools.lint_repo_consistency import _is_dead_decisions_sidecar

    write = {"file": "chapters/chapter-N-revision-decisions.json", "mode": "create_or_overwrite"}
    all_reads: set[str] = set()
    g4_skills = {"shenbi-chapter-revision"}  # G4 g4_decisions validates it
    code_blob: str = ""  # param type is str (basedpyright strict)
    assert (
        _is_dead_decisions_sidecar(
            write, "shenbi-chapter-revision", all_reads, g4_skills, code_blob
        )
        is False
    )
