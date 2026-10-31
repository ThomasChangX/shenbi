"""spec #83 T5: declarations_stale state chain + ss.stale_declarations gate.

Roundtrip persistence; writer (revision completes -> True); clear point 1
(revalidation-green re-sync); clear point 2 (both settle ingestion sites);
pre-settle guard demotion/hard; three-site mechanical exhaustiveness.
"""

from __future__ import annotations

import re
from pathlib import Path

from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY
from shenbi.pipeline.chapter_loop import _pre_settle_guard
from shenbi.pipeline.state import ChapterState, ChapterStatus, PipelineState


def test_stale_field_persists_roundtrip(tmp_path: Path) -> None:
    st = PipelineState(project_dir=str(tmp_path))
    st.chapter_loop.chapter_states["26"] = ChapterState(
        status=ChapterStatus.COMPLETE, declarations_stale=True
    )
    rt = PipelineState.from_json(st.to_json())
    assert rt.chapter_loop.chapter_states["26"].declarations_stale is True
    # 默认 False 向后兼容（存量 state 无该键）
    st2 = PipelineState(project_dir=str(tmp_path))
    st2.chapter_loop.chapter_states["27"] = ChapterState()
    assert (
        PipelineState.from_json(st2.to_json()).chapter_loop.chapter_states["27"].declarations_stale
        is False
    )


def test_pre_settle_guard_demotes_under_default_shadow(tmp_path: Path) -> None:
    # shadow 键缺席=默认 demote（shadow.py:61-64）——guard 返回 (demoted, hard=[])
    st = PipelineState(project_dir=str(tmp_path))
    st.chapter_loop.chapter_states["26"] = ChapterState(declarations_stale=True)
    demoted, hard = _pre_settle_guard(st, tmp_path, 26)
    assert not hard and demoted and "ss.stale_declarations" in demoted[0]
    # 非 stale 章：零信号
    demoted0, hard0 = _pre_settle_guard(st, tmp_path, 27)
    assert demoted0 == [] and hard0 == []


def test_pre_settle_guard_hard_when_shadow_promoted(tmp_path: Path) -> None:
    # shadow:false（转正后）→ 保持 HARD——apply_shadow 语义
    gc = tmp_path / "genre-config.json"
    gc.write_text('{"market_params": {"stale_declarations": {"shadow": false}}}', encoding="utf-8")
    st = PipelineState(project_dir=str(tmp_path))
    st.chapter_loop.chapter_states["26"] = ChapterState(declarations_stale=True)
    demoted, hard = _pre_settle_guard(st, tmp_path, 26)
    assert demoted == [] and hard and hard[0].startswith("G4.ss.stale_declarations")


def test_shadow_registration_row4() -> None:
    assert GATE_TO_SHADOW_KEY["ss.stale_declarations"] == (
        "market_params",
        "stale_declarations",
    )


def test_settle_dispatch_sites_all_guarded() -> None:
    """Mechanical exhaustiveness over dispatch_skill call points.

    Every call point MUST be classified in one of the two pinned lists below
    (settle-capable -> function body must reference _pre_settle_guard; rest
    -> no settle face). An unclassified point fails with "classify before
    wiring" -- the enforced invariant that ended the r2/r3 C1 falsification
    cycle. Do NOT extract sites by the "shenbi-state-settling" literal (the
    skill travels via variables; the three settle functions carry no such
    literal at their dispatch lines).
    """
    src = Path(__file__).resolve().parents[3] / "src" / "shenbi"
    settle_capable = {  # (path-from-src/shenbi, enclosing function)
        ("pipeline/chapter_loop.py", "run_parallel_post_draft_steps"),
        ("pipeline/cli.py", "_execute_pending_re_dispatches"),
        ("pipeline/chapter_loop.py", "_run_chapter_step_impl"),
    }
    rest = {  # pre-classified non-settle points (audit r5-I1/r6-I1)
        ("pipeline/triggers.py", "run_triggered_skills"),
        ("pipeline/parallel_dispatch.py", "_dispatch_with_retry"),
        ("pipeline/audit_layer.py", "run_audit_layer"),
        ("pipeline/genesis.py", "run_genesis_step"),
        ("pipeline/closure.py", "run_closure_step"),
        ("pipeline/revision_router.py", "dispatch_escalation"),
        ("pipeline/chapter_loop.py", "_run_audit_close_for_chapter"),
        ("pipeline/chapter_loop.py", "_check_conditional_resolve"),
        ("pipeline/cli.py", "cmd_resume"),
    }
    call_points: list[tuple[str, str]] = []
    for py in sorted(src.rglob("*.py")):
        rel = str(py.relative_to(src))
        for i, ln in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if "dispatch_skill(" in ln and not ln.strip().startswith("def ") and "import" not in ln:
                call_points.append((rel, _enclosing(py, i)))
    unclassified = [cp for cp in call_points if cp not in settle_capable and cp not in rest]
    assert not unclassified, (
        f"classify before wiring — 未分类 dispatch_skill 调用点: {unclassified}"
    )
    for path, fn in settle_capable:
        assert "_pre_settle_guard" in _func_body(src / path, fn), (
            f"settle-capable 站点 {path}:{fn} 未过 _pre_settle_guard"
        )
    # canary：调用点总数钉死（增减都红——新增派发面强制重新分类）
    assert len(call_points) == 13, f"dispatch_skill 调用点数变动: {len(call_points)} → 重新分类"


def _enclosing(path: Path, line: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for j in range(line - 1, -1, -1):
        m = re.match(r"^def (\w+)", lines[j])
        if m:
            return m.group(1)
    return ""


def _func_start(path: Path, fn: str) -> int:
    for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if ln.startswith(f"def {fn}("):
            return i
    return 0


def _func_body(path: Path, fn: str) -> str:
    """Whole enclosing-function body (def line to next top-level def)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = _func_start(path, fn)
    out = [lines[start]]
    for ln in lines[start + 1 :]:
        if ln.startswith("def ") or ln.startswith("class "):
            break
        out.append(ln)
    return "\n".join(out)
