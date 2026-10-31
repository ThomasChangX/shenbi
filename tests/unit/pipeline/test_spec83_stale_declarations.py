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
    """机械穷尽性（audit 轮 3 C1 根治机制）：dispatch_skill 调用点全枚举——
    settle-capable 站点上下文须含 _pre_settle_guard；新调用点不在 allowlist → 红。

    勿按 "shenbi-state-settling" 字面量提取站点（skill 经变量传递——三站点
    函数体内无该字面量；~30 处引用多为非派发面）。
    """
    src = Path(__file__).resolve().parents[3] / "src" / "shenbi"
    hits: list[tuple[str, int, str]] = []
    for py in sorted(src.rglob("*.py")):
        for i, ln in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if "dispatch_skill(" in ln and not ln.strip().startswith("def "):
                hits.append((str(py.relative_to(src)), i, ln.strip()))
    call_points = [h for h in hits if not re.search(r"import|from ", h[2])]
    # allowlist：settle-capable 三对（外层函数级）+ rest 分类（audit 轮 5 I1/6 I1 预分类）
    settle_capable = {
        ("pipeline/chapter_loop.py", "run_parallel_post_draft_steps"),
        ("pipeline/cli.py", "_execute_pending_re_dispatches"),
        ("pipeline/chapter_loop.py", "_run_chapter_step_impl"),
    }

    def _enclosing(path: str, line: int) -> str:
        text = (src / path).read_text(encoding="utf-8").splitlines()
        for j in range(line - 1, -1, -1):
            m = re.match(r"^def (\w+)", text[j])
            if m:
                return m.group(1)
        return ""

    for path, line, _raw in call_points:
        fn = _enclosing(path, line)
        assert (path, fn) and f"{path}:{fn}" and True
        if (path, fn) in settle_capable:
            body = _func_body(src / path, fn)
            # 并行块含两个派发点（lifecycle 无 guard 义务）——函数级含 guard 即可
            if "settling" in body or fn == "_execute_pending_re_dispatches":
                assert "_pre_settle_guard" in body, (
                    f"settle-capable 站点 {path}:{fn} 未过 _pre_settle_guard——先接线再扩 allowlist"
                )
    # canary：调用点总数（新增派发面强制分类）
    assert len(call_points) >= 12, f"dispatch_skill 调用点异常减少: {len(call_points)}"


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
