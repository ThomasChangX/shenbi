from __future__ import annotations

from pathlib import Path

from tools.generate_autocheck_docs import BANNER, ENDER, inject_block, render_autocheck


def test_render_includes_thresholds() -> None:
    from shenbi.contracts.skills._scoring_base import ScoreReport

    md = render_autocheck(ScoreReport)
    assert BANNER in md
    assert ENDER in md
    assert "PASS_THRESHOLD" in md
    assert "90" in md


def test_render_includes_computed_fields() -> None:
    from shenbi.contracts.skills._scoring_base import ScoreReport

    md = render_autocheck(ScoreReport)
    assert "passed" in md


def test_render_includes_formula() -> None:
    from shenbi.contracts.skills._scoring_base import ScoreReport

    md = render_autocheck(ScoreReport)
    assert "ROUTE_C_SOFT_WEIGHT" in md or "AGGREGATION_FORMULA" in md


def test_inject_creates_block(tmp_path: Path) -> None:
    from shenbi.contracts.skills._scoring_base import ScoreReport

    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: x\n---\n# Title\n", encoding="utf-8")
    block = render_autocheck(ScoreReport)
    assert inject_block(f, block) is True
    content = f.read_text(encoding="utf-8")
    assert BANNER in content
    assert ENDER in content


def test_inject_idempotent(tmp_path: Path) -> None:
    """Second inject with the same block -> no change."""
    from shenbi.contracts.skills._scoring_base import ScoreReport

    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: x\n---\n# Title\n", encoding="utf-8")
    block = render_autocheck(ScoreReport)
    inject_block(f, block)
    assert inject_block(f, block) is False


def test_tampered_block_overwritten_on_regen(tmp_path: Path) -> None:
    """Manual edit inside the sentinel block -> regeneration overwrites it."""
    from shenbi.contracts.skills._scoring_base import ScoreReport

    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: x\n---\n# Title\n", encoding="utf-8")
    block = render_autocheck(ScoreReport)
    inject_block(f, block)

    # Tamper: inject manual text inside the block
    content = f.read_text(encoding="utf-8")
    tampered = content.replace("PASS_THRESHOLD", "HACKED_THRESHOLD")
    f.write_text(tampered, encoding="utf-8")

    # Regenerate -- must detect change and overwrite
    assert inject_block(f, block) is True
    final = f.read_text(encoding="utf-8")
    assert "HACKED" not in final
    assert "PASS_THRESHOLD" in final
