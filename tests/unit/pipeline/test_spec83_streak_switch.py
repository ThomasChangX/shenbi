"""spec #83 T4: streak_monitor_rewinds — 口径a 回放基线.

同 key 连击不分族（monitor_rewind/g4_hard 同计）；DISPATCH 交织不断链
（计数器只由 _record_retry 增、章推进清）；loop_id 不作计数器；planning
key 计数但不触发切换（切换面只读 drafting）；复位=仅章推进。
回放锚：ch25×14/ch31×5/ch27/29/33/35×4 全 ≥4 触发零假触发（其余章最长 3）。
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _STREAK_TARGETED_MODE_THRESHOLD,
    _append_feedback_injections,
    _complete_chapter,
    _record_retry,
)
from shenbi.pipeline.state import PipelineState, retry_key


def test_streak_counts_retries_and_persists() -> None:
    st = PipelineState()
    rk = retry_key(25, "shenbi-chapter-drafting")
    _record_retry(st, 25, "shenbi-chapter-drafting")
    _record_retry(st, 25, "shenbi-chapter-drafting")
    assert st.chapter_loop.streak_monitor_rewinds[rk] == 2
    # 序列化 roundtrip（durable——不被 _reset_retries 清除面）
    rt = PipelineState.from_json(st.to_json())
    assert rt.chapter_loop.streak_monitor_rewinds[rk] == 2


def test_switch_fires_at_4_regardless_of_loop_id_resets(tmp_path: Path) -> None:
    # ch25 型：loop_id 序列 [1,2,3,4,1,...] 中途重置仍切换（loop_id 不可作计数器）
    st = PipelineState(project_dir=str(tmp_path))
    for _ in range(_STREAK_TARGETED_MODE_THRESHOLD):
        _record_retry(st, 25, "shenbi-chapter-drafting")
    prompt = _append_feedback_injections("基础 prompt", st, 25, "shenbi-chapter-drafting")
    # 切换面：无既有 retry_feedback 时不注入（注入以 prev_g4_feedback 存在为前提）
    assert "TARGETED-EDIT" not in prompt
    # 有既有反馈 + 连击 ≥4 → 注入定点扩写模式
    st.chapter_loop.retry_feedback[retry_key(25, "shenbi-chapter-drafting")] = (
        "G4.word_count: 差 500"
    )
    prompt2 = _append_feedback_injections("基础 prompt", st, 25, "shenbi-chapter-drafting")
    assert "TARGETED-EDIT MODE" in prompt2 and "定点" in prompt2


def test_switch_not_below_threshold(tmp_path: Path) -> None:
    st = PipelineState(project_dir=str(tmp_path))
    for _ in range(3):  # 其余章最长连击 3——零假触发口径
        _record_retry(st, 24, "shenbi-chapter-drafting")
    st.chapter_loop.retry_feedback[retry_key(24, "shenbi-chapter-drafting")] = (
        "G4.word_count: 差 100"
    )
    prompt = _append_feedback_injections("p", st, 24, "shenbi-chapter-drafting")
    assert "TARGETED-EDIT" not in prompt


def test_planning_key_counts_but_never_switches(tmp_path: Path) -> None:
    # planning key 计数存在；切换消费面只读 drafting key
    st = PipelineState(project_dir=str(tmp_path))
    for _ in range(6):
        _record_retry(st, 25, "shenbi-chapter-planning")
    assert st.chapter_loop.streak_monitor_rewinds[retry_key(25, "shenbi-chapter-planning")] == 6
    st.chapter_loop.retry_feedback[retry_key(25, "shenbi-chapter-planning")] = "G4.cp: x"
    prompt = _append_feedback_injections("p", st, 25, "shenbi-chapter-planning")
    assert "TARGETED-EDIT" not in prompt


def test_reset_only_on_chapter_advance(tmp_path: Path) -> None:
    # _complete_chapter（章推进）复位 bundle 全员 streak；成功重派/升级不复位
    # （复位点只在 _complete_chapter——无其他清除面，durable 对齐 retry_budget_consumed）
    st = PipelineState(project_dir=str(tmp_path))
    _record_retry(st, 2, "shenbi-chapter-drafting")
    _record_retry(st, 3, "shenbi-chapter-drafting")  # 假设 bundle {2,3}
    d = tmp_path
    (d / "outline").mkdir(parents=True, exist_ok=True)
    (d / "outline" / "volume_map.md").write_text("| 第2章 | x |\n", encoding="utf-8")
    _complete_chapter(st, 2)
    keys = [k for k in st.chapter_loop.streak_monitor_rewinds if k.startswith("ch2-")]
    assert keys == []  # ch2 已复位（bundle_chapters 单章态亦复位自身）
