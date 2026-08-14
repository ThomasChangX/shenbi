"""R2: total_chapters := max(read_volume_boundaries()) unified write point (F353).

Mid-book heal acceptance (spec R2-ii): a 56-chapter total=None project heals
before the guard.
"""

import json
import shutil
from pathlib import Path

from shenbi.pipeline._shared import update_total_chapters
from shenbi.pipeline.cli import _read_total_chapters
from shenbi.pipeline.genesis import genesis_finalize_volume_map
from shenbi.pipeline.state import PipelineState
from shenbi.pipeline.triggers import check_triggers

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path, with_total: bool = False) -> Path:
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    data: dict[str, object] = {"title": "星火燃穹"}
    if with_total:
        data["total_chapters"] = 100
    (proj / "novel.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return proj


def test_update_total_chapters_writes_planned_total(tmp_path):
    """Acceptance (i) hook semantics: fixate planned total 100 (max
    boundaries), not the 56 written-so-far count.
    """
    proj = _mk_project(tmp_path)
    assert update_total_chapters(proj) == 100
    assert _read_total_chapters(proj) == 100


def test_genesis_finalize_hook(tmp_path):
    proj = _mk_project(tmp_path)
    assert genesis_finalize_volume_map(proj) == 100


def test_update_idempotent_and_no_boundaries(tmp_path):
    proj = _mk_project(tmp_path, with_total=True)
    assert update_total_chapters(proj) == 100  # idempotent: same value, no rewrite
    empty = tmp_path / "empty"
    (empty / "outline").mkdir(parents=True)
    (empty / "novel.json").write_text("{}", encoding="utf-8")
    assert update_total_chapters(empty) == 0


def test_midbook_heal_unlocks_guard(tmp_path):
    """Acceptance (ii): 56-chapter total=None -> heal -> total==100 -> volume
    boundary trigger reachable.
    """
    proj = _mk_project(tmp_path)
    total = _read_total_chapters(proj)
    assert total == 0
    # Reproduce the cli.py guard sequence (where the heal inserts):
    if total <= 0:
        total = update_total_chapters(proj)
    assert total == 100
    state = PipelineState.default(str(proj))
    result = check_triggers(state, 55, total)
    assert result.volume_boundary is True
    assert result.book_closure is False  # 55 < 100: no premature closure


def test_heal_wired_in_orchestrate(tmp_path, monkeypatch):
    """Wiring: the heal's insertion in _orchestrate_to_checkpoint actually
    feeds total==100 into check_triggers (not just the inline replica).
    """
    from shenbi.pipeline import cli as cli_mod
    from shenbi.pipeline.state import PipelinePhase

    proj = _mk_project(tmp_path)

    state = PipelineState.default(str(proj))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 57
    state.chapter_loop.step_index = 0

    class _Noop:
        book_closure = False

        def any_triggered(self):
            return False

    calls: dict[str, int] = {}

    def fake_run(*a, **k):
        calls["run"] = calls.get("run", 0) + 1
        return True  # True = checkpoint reached; orchestrate returns

    def fake_check(st, ch, total):
        calls["total_seen"] = total
        return _Noop()

    monkeypatch.setattr("shenbi.pipeline.chapter_loop.run_chapter_step", fake_run)
    monkeypatch.setattr("shenbi.pipeline.triggers.check_triggers", fake_check)
    cli_mod._orchestrate_to_checkpoint(state, proj)
    assert calls.get("total_seen") == 100  # heal wrote it before the guard
    assert calls.get("run", 0) >= 1
