"""Unit test for G0.10 dynamic skill count (spec §9.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates import shared
from shenbi.gates.shared import all_skills


@pytest.mark.unit
def test_all_skills_is_dynamic_not_hardcoded(tmp_path: Path) -> None:
    """all_skills() is lazily scanned, cached, and directory-perceptive (spec #89 T4)."""
    first = all_skills()
    assert isinstance(first, list)
    assert first == all_skills()  # lru_cache: stable across calls
    assert len(first) >= 61  # current count, grows with new skills
    # 新目录可感知：monkeypatch SKILLS → cache_clear → 感知新技能；finally 恢复+再清

    fake = tmp_path / "skills"  # 真树外（audit-T4 🟡：xdist 共享真树有竞争）
    fake.mkdir(parents=True, exist_ok=True)
    (fake / "shenbi-probe-skill").mkdir(exist_ok=True)
    (fake / "shenbi-probe-skill" / "SKILL.md").write_text("x", encoding="utf-8")
    real_skills = shared.SKILLS
    shared.SKILLS = fake
    try:
        all_skills.cache_clear()
        assert "shenbi-probe-skill" in all_skills()
    finally:
        shared.SKILLS = real_skills
        all_skills.cache_clear()
        import shutil

        shutil.rmtree(fake, ignore_errors=True)
    assert "shenbi-probe-skill" not in all_skills()
