"""spec #82 T0: completion-time declared-label snapshot (sequence-gate data base).

Snapshot freezes the labels that passed the gate at completion time; post-gate
plan rewrites (the _REDO_RE_DISPATCH path) must not rewrite history. Leader +
follower both snapshot at the leader's completion moment (bundle-atomic).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.chapter_loop import DECLARED_WORDLISTS, _snapshot_declared
from shenbi.pipeline.state import ChapterState

FIX = (
    Path(__file__).resolve().parents[2] / "fixtures" / "spec82"
)  # 规范布局：plans/ + outline/ 平铺节选

V4_PLAN = """plan_format: v4
emotion_tone: 悲
**payoff 拍**: 类型｜轴(债)｜中兑现
章尾张力拍: 章｜『他数到第三遍，门被推开一半。』
章尾钩型: 悬念钩
金句位: 燃｜章首复述｜一页眉批
"""


def _mk_project(tmp_path: Path, plan: str = V4_PLAN, *, ch: int = 37) -> Path:
    (tmp_path / "plans").mkdir(exist_ok=True)
    (tmp_path / "plans" / f"chapter-{ch}-plan.md").write_text(plan, encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_snapshot_captures_six_keys_real_fixture() -> None:
    """Real-fixture six-key capture (plan C1 green test): ch36 plan copy.

    Asserts emotion_tone==悲, 張力拍档位==章, payoff档==中, 金句位燃 truthy,
    章尾钩型 absent (v3 plan has no such line).
    """
    snap = _snapshot_declared(FIX, 36)  # fixture 既有真实 plan——勿写
    assert snap["emotion_tone"] == "悲"
    assert snap["张力拍档位"] == "章"
    assert snap["payoff档"] == "中"
    assert snap["金句位燃"] is True
    assert "章尾钩型" not in snap  # v3 plan: no hook-type line


@pytest.mark.unit
def test_wordlist_external_tone_warns_and_kept_raw(tmp_path: Path, caplog) -> None:
    import logging as _logging

    with caplog.at_level(_logging.WARNING, logger="shenbi.pipeline.chapter_loop"):
        _mk_project(tmp_path, plan=V4_PLAN.replace("emotion_tone: 悲", "emotion_tone: 安"))
        snap = _snapshot_declared(tmp_path, 37)
    assert snap["emotion_tone"] == "安"  # raw kept; consumers apply cold predicate
    assert "安" not in DECLARED_WORDLISTS["emotion_tone"]
    assert any("snapshot_wordlist_external" in r.message for r in caplog.records)  # audit-T2/I2


@pytest.mark.unit
def test_node_markers_ingested_from_volume_map(tmp_path: Path) -> None:
    # 规范布局：outline/volume_map.md（fixture 真实节选拷贝进 tmp 项目）
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        (FIX / "volume_map-vol1-excerpt.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    snap8 = _snapshot_declared(tmp_path, 8)
    snap22 = _snapshot_declared(tmp_path, 22)
    assert "轮回触点◆" in snap8["节点标记集"]
    assert "萤回触◆" in snap22["节点标记集"]


@pytest.mark.unit
def test_chapter_state_has_declared_field() -> None:
    cs = ChapterState()
    assert cs.declared == {}
    cs.declared = {"emotion_tone": "悲"}
    assert json.loads(json.dumps(cs.declared))["emotion_tone"] == "悲"


@pytest.mark.unit
def test_declared_survives_state_roundtrip(tmp_path: Path) -> None:
    """audit-T2/C1: declared must persist through to_dict/from_dict —
    sequence gates (T4) read the snapshot from pipeline-state.json.
    """
    from shenbi.pipeline.state import PipelineState

    state = PipelineState.default(str(tmp_path))
    state.chapter_loop.chapter_states["37"] = ChapterState(
        declared={"emotion_tone": "悲", "节点标记集": ["轮回触点◆"]}
    )
    data = state.to_dict()
    restored = PipelineState.from_dict(data)
    assert restored.chapter_loop.chapter_states["37"].declared == {
        "emotion_tone": "悲",
        "节点标记集": ["轮回触点◆"],
    }
    import json

    json.loads(json.dumps(data, ensure_ascii=False))["chapter_loop"]["chapter_states"]["37"][
        "declared"
    ]


@pytest.mark.unit
def test_ch2_fixture_big_hook_snapshot() -> None:
    """audit-T2/M2: ch2 fixture consumption — ch2 declares 大 (S1 evidence)."""
    snap = _snapshot_declared(FIX, 2)
    assert snap["张力拍档位"] == "大"


@pytest.mark.unit
def test_follower_snapshot_written_and_frozen(tmp_path: Path, monkeypatch) -> None:
    """audit-T2/I1: bundle wiring + freeze semantics against _complete_chapter.

    Bundle [37, 38]: completing the leader snapshots BOTH members; rewriting
    the plans afterwards must not change the frozen snapshot (T0 red test).
    """
    import shenbi.pipeline.chapter_loop as cl
    from shenbi.pipeline.state import PipelineState

    (tmp_path / "plans").mkdir()
    (tmp_path / "plans" / "chapter-37-plan.md").write_text(V4_PLAN, encoding="utf-8")
    (tmp_path / "plans" / "chapter-38-plan.md").write_text(
        V4_PLAN.replace("emotion_tone: 悲", "emotion_tone: 惧"), encoding="utf-8"
    )
    # bundle_chapters on a project without volume_map -> singleton; force a
    # 2-chapter bundle by stubbing to the documented [n, n+1] shape.
    monkeypatch.setattr(cl, "bundle_chapters", lambda pd, ch: [ch, ch + 1])
    for heavy in (
        "check_product_contracts",
        "_check_world_file_freshness",
        "_print_timing_summary",
        "print_token_summary",
    ):
        monkeypatch.setattr(cl, heavy, lambda *a, **k: None, raising=False)
    monkeypatch.setattr("shenbi.cost.report.write_report", lambda *a, **k: None)

    state = PipelineState.default(str(tmp_path))
    cl._complete_chapter(state, 37)

    cs37 = state.chapter_loop.chapter_states["37"]
    cs38 = state.chapter_loop.chapter_states["38"]
    assert cs37.declared["emotion_tone"] == "悲"
    assert cs38.declared["emotion_tone"] == "惧"  # follower snapshotted too

    # freeze: post-completion plan rewrite must not rewrite history
    (tmp_path / "plans" / "chapter-37-plan.md").write_text(
        V4_PLAN.replace("emotion_tone: 悲", "emotion_tone: 喜"), encoding="utf-8"
    )
    assert cl._snapshot_declared(tmp_path, 37)["emotion_tone"] == "喜"  # read reflects file
    assert cs37.declared["emotion_tone"] == "悲"  # frozen snapshot unchanged
