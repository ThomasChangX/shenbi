"""spec #106 T2 接线: shadow 不写 route / armed 写 route+reason /
role-gate armed-only / cap 二次采样两分支 / pending 语义不变。
"""

from pathlib import Path
from types import SimpleNamespace

from shenbi.contracts.enums import RevisionMode
from shenbi.pipeline.chapter_loop import _route_revision_after_resonance
from shenbi.pipeline.state import ChapterState, PipelineConfig, PipelineState

TREND_HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
TREND_SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)
BLOCKED_REPORT = """# 共鸣评审

```verdict
判定: 阻断
共振: 88/100
```
"""


def _make_state(policy: dict[str, object] | None = None) -> PipelineState:
    state = PipelineState(config=PipelineConfig(resonance_policy=policy))
    state.chapter_loop.chapter_states["14"] = ChapterState(resonance_score=42)
    return state


def _seed_project(tmp_path: Path, *, report: str | None, with_trend: bool = True) -> None:
    audits = tmp_path / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    if report is not None:
        (audits / "chapter-14-resonance.md").write_text(report, encoding="utf-8")
    if with_trend:
        truth = tmp_path / "truth"
        truth.mkdir(parents=True, exist_ok=True)
        rows = [
            f"| {c} | 推进 | 21 | 20 | 21 | 15 | {s} | mid |  |"
            for c, s in zip(
                [1, 2, 3, 4, 5, 7, 9, 11, 12, 13],
                [78, 74, 76, 78, 79, 79, 80, 79, 81, 79],
                strict=True,
            )
        ]
        (truth / "resonance_trend.md").write_text(
            "\n".join([TREND_HEADER, TREND_SEP, *rows]) + "\n", encoding="utf-8"
        )


def _no_issues(monkeypatch):
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues", lambda *a, **k: ([], False)
    )


def test_shadow_mode_leaves_route_untouched(tmp_path, monkeypatch, capsys):
    from shenbi.logging import configure_logging

    configure_logging()
    _seed_project(tmp_path, report=None, with_trend=True)  # score=42 < floor 78.0
    state = _make_state(policy=None)  # 缺省 shadow
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == RevisionMode.NO_REVISION.value
    event = cs.audit_results["resonance_would_route"]
    assert event["would_route"] is True and event["reason"] == "resonance"
    assert event["floor"] == 78.0
    assert "resonance_route_reason" not in cs.audit_results
    assert cs.revision_count == 0
    assert "resonance_would_route" in capsys.readouterr().err
    trace = tmp_path / "trace.jsonl"  # TraceWriter 落项目根（trace/writer.py:23 _TRACE_NAME）
    assert trace.exists() and "resonance" in trace.read_text(encoding="utf-8")


def test_armed_mode_routes_spot_fix_with_reason(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == "spot-fix"  # 枚举实值（连字符）
    assert cs.audit_results["resonance_route_reason"] == "resonance"
    assert cs.revision_count == 1


def test_role_gate_blocked_shadow_records_event_only(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=BLOCKED_REPORT, with_trend=True)
    state = _make_state(policy=None)  # shadow：score 88 过 floor，但 verdict 阻断
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == RevisionMode.NO_REVISION.value
    assert cs.audit_results["resonance_would_route"]["reason"] == "role_gate"


def test_role_gate_blocked_armed_routes(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=BLOCKED_REPORT, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["revision_route"] == "spot-fix"
    assert cs.audit_results["resonance_route_reason"] == "role_gate"


def test_negated_block_not_routed(tmp_path, monkeypatch):
    report = BLOCKED_REPORT.replace("判定: 阻断", "判定: 无阻断")
    _seed_project(tmp_path, report=report, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    state.chapter_loop.chapter_states["14"].resonance_score = 85  # 过 floor
    _no_issues(monkeypatch)
    _route_revision_after_resonance(state, tmp_path, 14)
    cs = state.chapter_loop.chapter_states["14"]
    assert cs.audit_results["resonance_would_route"]["would_route"] is False


def test_cap_confirm_pass_restores_no_revision(tmp_path, monkeypatch):
    # armed + 已 2 次修订 + 第 3 次 resonance 路由 → cap 耗尽 → 二次采样复评 85 ≥ floor → pass
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    cs = state.chapter_loop.chapter_states["14"]
    cs.revision_count = 2
    _no_issues(monkeypatch)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        lambda *a, **k: SimpleNamespace(success=True, returncode=0, stderr="", stdout=""),
    )
    (tmp_path / "audits" / "chapter-14-resonance.md").write_text(
        "```verdict\n判定: 通过\n共振: 85/100\n```\n", encoding="utf-8"
    )
    _route_revision_after_resonance(state, tmp_path, 14)
    assert cs.audit_results["revision_route"] == RevisionMode.NO_REVISION.value  # pass 回退
    assert cs.revision_count == 2  # 增量已回退
    assert cs.audit_results["resonance_cap_confirmed"] is True


def test_cap_confirm_both_below_escalates_with_double_report(tmp_path, monkeypatch):
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    cs = state.chapter_loop.chapter_states["14"]
    cs.revision_count = 2
    _no_issues(monkeypatch)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        lambda *a, **k: SimpleNamespace(success=True, returncode=0, stderr="", stdout=""),
    )
    (tmp_path / "audits" / "chapter-14-resonance.md").write_text(
        "```verdict\n判定: 通过\n共振: 40/100\n```\n", encoding="utf-8"
    )
    escalated = []
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.dispatch_escalation",
        lambda *a, **k: escalated.append(1) or True,
    )
    _route_revision_after_resonance(state, tmp_path, 14)
    assert escalated, "两次均 below 必须升级"
    assert (tmp_path / "audits" / "chapter-14-resonance-first.md").exists()  # 双报告保全


def test_cap_confirm_dispatch_failure_conservative_escalation(tmp_path, monkeypatch):
    # confirmed is None（派发失败）→ 保守升级（噪声成本 < 漏放行）
    _seed_project(tmp_path, report=None, with_trend=True)
    state = _make_state(policy={"mode": "armed"})
    state.chapter_loop.chapter_states["14"].revision_count = 2
    _no_issues(monkeypatch)
    monkeypatch.setattr(
        "shenbi.pipeline.dispatch_helper.dispatch_skill",
        lambda *a, **k: SimpleNamespace(success=False, returncode=1, stderr="boom", stdout=""),
    )
    escalated = []
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.dispatch_escalation",
        lambda *a, **k: escalated.append(1) or True,
    )
    _route_revision_after_resonance(state, tmp_path, 14)
    assert escalated  # None → 保守升级


def test_docstring_matches_production():
    from shenbi.pipeline import revision_router

    doc = revision_router.__doc__ or ""
    assert "borderline -> escalation checkpoint" not in doc
    assert "不路由" in doc
