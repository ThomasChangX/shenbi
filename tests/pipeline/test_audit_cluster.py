"""spec #72 T9: cluster audit dispatch with per-chapter report artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.audit_layer import audit_report_paths
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS
from shenbi.pipeline.state import PipelineState

CW = json.dumps({"chapter_word": {"default": 3200, "min": 2800, "max": 4000}})


@pytest.mark.unit
def test_audit_skills_declare_next_chapter_writes() -> None:
    """Audit skills declare {N+1} brace writes (leader single-resolution)."""
    from shenbi.contracts.loader import load_contract
    from shenbi.pipeline.audit_layer import audit_report_paths

    for s in CHAPTER_STEPS:
        if not s.is_audit:
            continue
        writes = load_contract(s.skill).get("writes", [])
        audit_writes = [w for w in writes if "audits/" in str(w)]
        assert any("{N+1}" in str(w) for w in audit_writes), s.skill
    # leader 单解析覆盖 follower：audit_report_paths(N) 含 N+1 路径
    paths = audit_report_paths(2, "shenbi-review-group-character")
    assert "audits/chapter-3-character.md" in paths
    assert "audits/chapter-2-character.md" in paths


@pytest.mark.unit
def test_no_phantom_paths_beyond_bundle() -> None:
    """Leader resolution yields no paths beyond the bundle (m+1+)."""
    from shenbi.pipeline.audit_layer import audit_report_paths

    paths = audit_report_paths(2, "shenbi-review-group-factual")
    assert not any("chapter-4-" in p for p in paths)  # {N+1} 到 3 为止


@pytest.mark.integration
def test_cluster_savepoint_records_both_chapters(tmp_path: Path) -> None:
    """Cluster savepoint records wave_completed for BOTH bundle chapters
    (a missing N+1 entry is a cascade blind spot).
    """
    import shenbi.pipeline.chapter_loop as cl
    from shenbi.pipeline.dispatch_helper import DispatchResult
    from shenbi.pipeline.parallel_dispatch import ReviewTask

    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第1卷 星火（第 1-4 章）\n", encoding="utf-8"
    )
    state = PipelineState.default(str(tmp_path))
    tasks = [
        ReviewTask(
            skill="shenbi-review-group-factual",
            project_dir=tmp_path,
            prompt="cluster",
            output_path="audits/chapter-1-factual.md",
            output_paths=audit_report_paths(1, "shenbi-review-group-factual"),
        )
    ]
    save_state = lambda *a, **kw: None  # noqa: E731
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cl, "save_state", save_state)
        on_complete = cl._wave_savepoint(state, tmp_path, 1, [1, 2])(tasks)
        on_complete(0, DispatchResult(True, 0, "{}", ""))
    for n in (1, 2):
        cs = state.chapter_loop.chapter_states.get(str(n))
        assert cs is not None, n
        done = cs.audit_results.get("wave_completed") or []
        assert "shenbi-review-group-factual" in done, n
