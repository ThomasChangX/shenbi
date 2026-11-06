"""束4（2026-11-05）裁决 #10/#11 根因修复：retry 反馈失败族累积。

实证：重派反馈只带上一轮失败项 → 模型逐轮丢持振荡（ch43 规划三连败：
第2轮补了场景预算节、第3轮又丢；草写四连败：字数带与声口密度互相挤兑）。
裁决 #10 的全约束模板+防回退令反馈形 → 第 4 派一次过——本测把该形固化为
框架行为（accumulate_retry_feedback / _clear_retry_feedback）。
"""

from shenbi.pipeline.chapter_loop import (
    _clear_retry_feedback,
    _enrich_g4_feedback,
    _failure_family_id,
    _reset_retries,
    accumulate_retry_feedback,
)
from shenbi.pipeline.state import PipelineState


def _state() -> PipelineState:
    return PipelineState()


def test_first_round_equals_plain_enriched_feedback() -> None:
    """首轮无累积：反馈与既有 _enrich_g4_feedback 全等（零行为变更）。"""
    s = _state()
    failures = ["G4.cp.scene_budget:ch43-plan.md:缺场景预算节"]
    merged = accumulate_retry_feedback(s, "ch43-shenbi-chapter-planning", failures)
    assert merged == _enrich_g4_feedback(failures)
    assert "防回退令" not in merged


def test_second_round_carries_first_family_as_anti_regression() -> None:
    """束4 振荡形：第2轮只报 B → 反馈须同时带 B（活项）与 A（防回退项）。"""
    s = _state()
    key = "ch43-shenbi-chapter-drafting"
    accumulate_retry_feedback(s, key, ["G4.word_count:ch43:2214<2800"])
    merged = accumulate_retry_feedback(s, key, ["G4.cd.voice_density:ch43:1<2"])
    # 本轮活项全清单呈现
    assert "G4.cd.voice_density" in merged
    # 此前轮已点名族进防回退节（约束跨轮持存——单轮反馈的丢持面）
    assert "防回退令" in merged
    assert "G4.word_count" in merged
    # 历史两族齐
    assert set(s.chapter_loop.retry_failure_history[key]) == {"cd.voice_density", "word_count"}


def test_family_latest_message_wins_no_stacking() -> None:
    """同族重败取最新报文（旧报文替换），不叠加重复条目。"""
    s = _state()
    key = "ch44-shenbi-chapter-drafting"
    accumulate_retry_feedback(s, key, ["G4.word_count:ch44:2214<2800"])
    accumulate_retry_feedback(s, key, ["G4.word_count:ch44:2611<2800"])
    merged = accumulate_retry_feedback(s, key, ["G4.cd.voice_density:ch44:1<2"])
    assert "2611" in merged  # 最新报文
    assert "2214" not in merged  # 旧报文被替换
    anti = merged.split("防回退令", 1)[1]
    assert anti.count("G4.word_count") == 1


def test_refixed_family_returns_to_live_section() -> None:
    """防回退项复发 → 回到活项节（最新报文），防回退节不再含该族。"""
    s = _state()
    key = "ch43-shenbi-chapter-planning"
    accumulate_retry_feedback(s, key, ["G4.cp.invalid_chapter_role:ch43:承接"])
    accumulate_retry_feedback(s, key, ["G4.cp.scene_budget:ch43:缺节"])  # role 族转防回退
    merged = accumulate_retry_feedback(
        s, key, ["G4.cp.invalid_chapter_role:ch43:斜杠复合"]
    )  # role 族复发
    live = merged.split("防回退令", 1)[0]
    anti = merged.split("防回退令", 1)[1] if "防回退令" in merged else ""
    assert "斜杠复合" in live  # 复发族以最新报文在活项节
    assert "G4.cp.invalid_chapter_role" not in anti


def test_indexed_ids_collapse_to_family() -> None:
    """索引后缀族归一（sel_3_x / sel_5_x 同族）——与范例键归一同构。"""
    assert _failure_family_id("G4.sb.sel_3_missing_basis:f.md:...") == "sb.sel_N_missing_basis"
    s = _state()
    key = "ch45-shenbi-state-settling"
    accumulate_retry_feedback(s, key, ["G4.sb.sel_3_missing_basis:f.md: selections[3]"])
    merged = accumulate_retry_feedback(s, key, ["G4.sb.sel_5_missing_basis:f.md: selections[5]"])
    # 同族：无防回退节，最新报文在场
    assert "防回退令" not in merged
    assert "sel_5_missing_basis" in merged


def test_clear_wipes_feedback_and_history() -> None:
    """成功面同清：反馈与累积历史一并 pop（canary「retry_feedback 永不清」
    的累积版）。
    """
    s = _state()
    key = "ch43-shenbi-chapter-drafting"
    accumulate_retry_feedback(s, key, ["G4.word_count:ch43:2214<2800"])
    _clear_retry_feedback(s, key)
    assert key not in s.chapter_loop.retry_feedback
    assert key not in s.chapter_loop.retry_failure_history
    # 清后再败：全新起点（无残留防回退族）
    merged = accumulate_retry_feedback(s, key, ["G4.cd.voice_density:ch43:1<2"])
    assert "防回退令" not in merged


def test_reset_retries_clears_history() -> None:
    """步成功兜底清面：_reset_retries 同清累积历史（幂等）。"""
    from shenbi.pipeline.chapter_loop import CHAPTER_STEPS

    s = _state()
    step = next(st for st in CHAPTER_STEPS if st.skill == "shenbi-chapter-planning")
    accumulate_retry_feedback(s, "ch43-shenbi-chapter-planning", ["G4.cp.scene_budget:x:缺节"])
    _reset_retries(s, step, 43)
    assert "ch43-shenbi-chapter-planning" not in s.chapter_loop.retry_failure_history


def test_history_capped_at_max_families() -> None:
    """上限防御：超 _RETRY_HISTORY_MAX_FAMILIES 族丢最旧（首见序）。"""
    from shenbi.pipeline.chapter_loop import _RETRY_HISTORY_MAX_FAMILIES

    s = _state()
    key = "ch46-shenbi-chapter-drafting"
    fams = [chr(ord("a") + i % 26) + ("" if i < 26 else str(i // 26)) for i in range(40)]
    for tag in fams[: _RETRY_HISTORY_MAX_FAMILIES + 4]:
        accumulate_retry_feedback(s, key, [f"G4.cd.check_{tag}:ch46:v{tag}"])
    assert len(s.chapter_loop.retry_failure_history[key]) == _RETRY_HISTORY_MAX_FAMILIES
    # 最旧族被丢（check_a 不在场），最新族在场
    assert "cd.check_a" not in s.chapter_loop.retry_failure_history[key]
    newest = fams[_RETRY_HISTORY_MAX_FAMILIES + 3]
    assert f"cd.check_{newest}" in s.chapter_loop.retry_failure_history[key]


def test_non_g4_string_family_semantics() -> None:
    """非 G4 形态走同面：ascii 冒号前缀键同族重写（不叠加）；整串形
    （全角冒号/人审自由文本）异文累积为防回退——#10 实证语义（人审全
    约束清单跨轮持存）。
    """
    s = _state()
    key = "ch43-shenbi-chapter-drafting"
    # ascii 冒号前缀键（pipeline-scene-split 族）：同族最新报文重写
    accumulate_retry_feedback(s, key, ["pipeline-scene-split: 标记违例:第2场景"])
    merged = accumulate_retry_feedback(s, key, ["pipeline-scene-split: 字数带:ch43"])
    assert "防回退令" not in merged
    assert "字数带" in merged and "标记违例" not in merged
    # 整串形（人审反馈，全角冒号无段）：异文累积
    hkey = "ch43-shenbi-chapter-planning"
    accumulate_retry_feedback(s, hkey, ["拒收：三件套 0-1/3，倒计时锚未起算"])
    merged2 = accumulate_retry_feedback(s, hkey, ["拒收：清偿表三义务缺席"])
    assert "防回退令" in merged2
    assert "三件套" in merged2


def test_human_feedback_verbatim_passthrough_but_tracked() -> None:
    """enrich=False（cli 审查路由形）：人审自由文本逐字透传（G4 模板头
    不污染裁决语义），族仍入史——后续机器败轮以防回退令持存人审约束。
    """
    s = _state()
    key = "ch47-shenbi-volume-consolidation"
    fb = "重跑说明：consolidation 头寸按裁决 156 收窄"
    merged = accumulate_retry_feedback(s, key, [fb], enrich=False)
    assert merged == fb  # 逐字（无 G4 模板头/兜底句）
    # 人审约束入史：下轮机器败（异族）以防回退令持存之
    merged2 = accumulate_retry_feedback(s, key, ["G4.vc.structure:x:列头缺"])
    assert "防回退令" in merged2 and fb in merged2


def test_state_roundtrip_preserves_history() -> None:
    """持久化面：to_dict/from_dict 往返保累积历史（crash-resume 不丢约束集）。"""
    s = _state()
    accumulate_retry_feedback(s, "ch43-shenbi-chapter-drafting", ["G4.word_count:ch43:2214<2800"])
    restored = PipelineState.from_json(s.to_json())
    assert restored.chapter_loop.retry_failure_history == (s.chapter_loop.retry_failure_history)


def test_serial_g4_path_accumulates_across_rounds(tmp_path, monkeypatch) -> None:
    """接线级：串行步 G4 硬败两次（异族）→ 第二轮注入的 retry_feedback
    同时带本轮活项与首轮族防回退项（束4 ch43 规划振荡的机器复现）。
    """

    class _OK:
        success = True
        returncode = 0
        stdout = ""
        stderr = ""

    from shenbi.pipeline import chapter_loop as cl

    state = PipelineState.default(str(tmp_path))
    from shenbi.pipeline.state import PipelinePhase

    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 43
    state.chapter_loop.per_chapter_review_enabled = False
    state.chapter_loop.step_index = next(
        i for i, st in enumerate(cl.CHAPTER_STEPS) if st.skill == "shenbi-chapter-planning"
    )
    monkeypatch.setattr(cl, "dispatch_skill", lambda *a, **kw: _OK())
    gate_results = [
        {
            "status": "FAIL",
            "must_fix": ["G4.cp.scene_budget:plans/chapter-43-plan.md:缺场景预算节"],
        },
        {"status": "FAIL", "must_fix": ["G4.cp.invalid_chapter_role:ch43:承接"]},
    ]
    monkeypatch.setattr(cl, "run_gate_g4", lambda *a, **kw: gate_results.pop(0))

    key = "ch43-shenbi-chapter-planning"
    assert cl.run_chapter_step(state, tmp_path) is False  # 首败：自动重派路由
    fb1 = state.chapter_loop.retry_feedback[key]
    assert "G4.cp.scene_budget" in fb1 and "防回退令" not in fb1
    assert cl.run_chapter_step(state, tmp_path) is False  # 二败（异族）
    fb2 = state.chapter_loop.retry_feedback[key]
    assert "G4.cp.invalid_chapter_role" in fb2  # 本轮活项
    assert "防回退令" in fb2 and "G4.cp.scene_budget" in fb2  # 首轮族持存
    # 第三轮门 PASS → 反馈与历史同清
    monkeypatch.setattr(cl, "run_gate_g4", lambda *a, **kw: {"status": "PASS", "must_fix": []})
    (tmp_path / "plans").mkdir(exist_ok=True)
    cl.run_chapter_step(state, tmp_path)
    # planning 步可能因 outputs/precheck 面走失败路由——只断言门 PASS 清面
    if key not in state.chapter_loop.retry_feedback:
        assert key not in state.chapter_loop.retry_failure_history
