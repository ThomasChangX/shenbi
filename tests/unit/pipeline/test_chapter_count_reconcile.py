"""Chapter-count reconciliation across the five derivation sources.

Fixcheck P1: ceil(200000/2000)=100 (genre-config math) silently coexisted
with novel.json/volume_map/book_spine/rhythm_principles all saying 50 —
G0.3 emits its expected-chapters as metadata only and nothing in the
pipeline ever cross-checked the sources; the contradiction surfaced only
because the foundation-review LLM happened to catch it.
"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline._shared import reconcile_chapter_counts


def _project(tmp_path: Path, *, default: int = 4000, total: int = 50, spine: int = 50) -> Path:
    (tmp_path / "outline").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "novel.json").write_text(
        json.dumps({"target_word_count": 200000, "total_chapters": total}), encoding="utf-8"
    )
    (tmp_path / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": default}}), encoding="utf-8"
    )
    (tmp_path / "outline" / "volume_map.md").write_text(
        f"---\ntotal_chapters: {total}\n---\n## 第一卷\n", encoding="utf-8"
    )
    (tmp_path / "outline" / "rhythm_principles.md").write_text(
        f"---\ntotal_chapters: {total}\nchapter_word_target: {default}\n---\n", encoding="utf-8"
    )
    (tmp_path / "truth" / "book_spine.md").write_text(
        f"---\ntotal_chapters: {spine}\n---\n", encoding="utf-8"
    )
    return tmp_path


def test_consistent_five_way_passes(tmp_path: Path) -> None:
    assert reconcile_chapter_counts(_project(tmp_path)) == []


def test_genre_config_math_mismatch_is_reported(tmp_path: Path) -> None:
    issues = reconcile_chapter_counts(_project(tmp_path, default=2000))
    assert any("ceil(200000/2000)=100" in i and "novel.json=50" in i for i in issues), issues


def test_frontmatter_drift_is_reported(tmp_path: Path) -> None:
    issues = reconcile_chapter_counts(_project(tmp_path, spine=51))
    assert any("book_spine.md" in i and "51" in i for i in issues), issues


def test_missing_files_are_tolerated(tmp_path: Path) -> None:
    (tmp_path / "novel.json").write_text(
        json.dumps({"target_word_count": 200000, "total_chapters": 50}), encoding="utf-8"
    )
    assert reconcile_chapter_counts(tmp_path) == []


def test_missing_novel_json_is_tolerated(tmp_path: Path) -> None:
    assert reconcile_chapter_counts(tmp_path) == []


def test_advance_leads_checkpoint_context_with_reconcile_issues(tmp_path: Path) -> None:
    """Wiring: genesis completion puts the reconciliation diff into the
    GENESIS_COMPLETE checkpoint context as MUST-FIX (the checkpoint already
    gates entry to the chapter loop; the reviewer gets machine evidence).
    """
    from shenbi.pipeline.genesis import GENESIS_STEPS, _advance
    from shenbi.pipeline.state import CheckpointType, GenesisState, PipelineState

    state = PipelineState.default(str(tmp_path))
    state.genesis.state = GenesisState.IN_PROGRESS

    # divergent project: genre-config math says 100, novel.json says 50
    _project(tmp_path, default=2000)

    done = _advance(state, len(GENESIS_STEPS) - 1, tmp_path)

    assert done is True
    assert state.pending_checkpoint.type == CheckpointType.GENESIS_COMPLETE
    ctx = state.pending_checkpoint.context or ""
    assert ctx.startswith("MUST-FIX 章数对账不一致"), ctx
    assert "ceil(200000/2000)=100" in ctx, ctx
