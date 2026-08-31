"""Tests for chapter-pattern structured accumulation + historical-half injection (spec #33 T1a-2)."""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.helper_injection import (
    accumulate_pattern_classification,
    inject_helper_precompute,
)


def _write_input(project_dir: Path, chapter: int, payload: list[dict[str, str]]) -> None:
    ctx = project_dir / "context"
    ctx.mkdir(exist_ok=True)
    (ctx / f"chapter-pattern-input-{chapter}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def test_accumulate_appends_keyed_row(tmp_path: Path) -> None:
    # Pattern strings follow the test_compute_pattern inline-input precedent.
    payload = [{"num": 1, "pattern": "引入"}, {"num": 2, "pattern": "转折"}]
    accumulate_pattern_classification(tmp_path, 1, payload)
    text = (tmp_path / "truth" / "chapter_patterns.md").read_text(encoding="utf-8")
    assert "| 1 | 引入 |" in text


def test_accumulate_dedups_same_chapter(tmp_path: Path) -> None:
    accumulate_pattern_classification(tmp_path, 1, [{"num": 1, "pattern": "引入"}])
    accumulate_pattern_classification(tmp_path, 1, [{"num": 1, "pattern": "转折"}])
    text = (tmp_path / "truth" / "chapter_patterns.md").read_text(encoding="utf-8")
    assert text.count("| 1 |") == 1


def test_injection_includes_entropy(tmp_path: Path) -> None:
    for n, pat in enumerate(["引入", "转折", "揭示", "升级", "决战", "收束"], start=1):
        accumulate_pattern_classification(tmp_path, n, [{"num": n, "pattern": pat}])
    user = inject_helper_precompute("shenbi-chapter-pattern", tmp_path, "PROMPT")
    assert "## Helper Precompute (chapter pattern history, deterministic)" in user
    assert "entropy" in user
    assert "PROMPT" in user  # original prompt preserved after block


def test_injection_empty_history_returns_unchanged(tmp_path: Path) -> None:
    user = inject_helper_precompute("shenbi-chapter-pattern", tmp_path, "PROMPT")
    assert user == "PROMPT"
