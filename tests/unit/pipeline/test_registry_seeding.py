"""Spec #75 registry seeding: deterministic name_registry bootstrap.

Seeding is a one-shot 卷层初值 (pipeline producer); rolling updates belong
to state-settling. Idempotence rule: an existing registry is NEVER
overwritten by the seeder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.registry_seeding import main, seed_name_registry


@pytest.mark.unit
def test_seed_creates_registry_with_core_rows(tmp_path: Path) -> None:
    target = seed_name_registry(tmp_path)
    assert target == tmp_path / "truth" / "name_registry.md"
    text = target.read_text(encoding="utf-8")
    # The three invariant rows the #75/#74 contract depends on.
    assert "| 登记名 | 临 |" in text
    assert "| 代词白名单 | 他 |" in text
    assert "| 禁用名 | 灯 |" in text


@pytest.mark.unit
def test_seed_is_idempotent_existing_registry_untouched(tmp_path: Path) -> None:
    seed_name_registry(tmp_path)
    target = tmp_path / "truth" / "name_registry.md"
    target.write_text("# 已由 settling 演进的字典\n", encoding="utf-8")
    seed_name_registry(tmp_path)
    assert "已由 settling 演进的字典" in target.read_text(encoding="utf-8")


@pytest.mark.unit
def test_cli_main_returns_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "truth" / "name_registry.md").is_file()
