"""#48/#49 (probe21 genesis whack-a-mole, adjudications #002/#003): a scoped
genesis redo re-dispatched with ONLY the reviewer feedback — the regen
honored explicit bindings but shuffled every unbound layer (canon → anchor
names → 规则五 semantics → 规则1-4 numbering + anchor table; four review
rounds, the $4.10 cost breach). The redo prompt must carry a machine-extracted
STRUCTURE BINDING of the current on-disk baseline (headings, table headers,
first-column key values) so everything the feedback does not explicitly
change is frozen; and the re-raised genesis-complete checkpoint must carry a
binding-drift report so the reviewer sees structural drift without a hand
diff.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline import genesis as genesis_mod
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import (
    CheckpointType,
    GenesisState,
    GenesisStateData,
    PipelineState,
)

RULES_MD = """---
type: truth
---

# 世界铁律

## 规则一：灵脉有竭

灵能源自地脉。

## 规则二：灵能守恒

灵能不可凭空创生。

## 规则五：壁线（天穹之界）

壁线是灵能可存在的最高高度。
"""

PROTAGONIST_MD = """---
type: truth
---

# 主角档案

## 锚点

| 锚点名 | 出场章 | 备注 |
|--------|--------|------|
| 林渡 | 第 1 章 | 灰籍少年 |
| 阿雀 | 第 2 章 | 汤锅姑娘 |

## 成长线

从南仓工账开始。
"""


def _proj(tmp_path: Path) -> Path:
    (tmp_path / "world").mkdir(exist_ok=True)
    (tmp_path / "characters").mkdir(exist_ok=True)
    (tmp_path / "world" / "rules.md").write_text(RULES_MD, encoding="utf-8")
    (tmp_path / "characters" / "protagonist.md").write_text(PROTAGONIST_MD, encoding="utf-8")
    return tmp_path


def _state_with_project(proj: Path) -> PipelineState:
    state = PipelineState.default(str(proj))
    state.genesis = GenesisStateData(
        state=GenesisState.PENDING,
        current_step=17,
        skills_done=["shenbi-worldbuilding", "shenbi-character-design"],
    )
    return state


def test_extract_structure_bindings_covers_headings_headers_and_keys(tmp_path):
    bindings = genesis_mod.extract_structure_bindings(_proj(tmp_path), "shenbi-character-design")
    assert "## 锚点" in bindings
    assert "| 锚点名 | 出场章 | 备注 |" in bindings  # table header frozen verbatim
    assert "林渡" in bindings and "阿雀" in bindings  # first-column key values
    assert "# 主角档案" in bindings
    assert "从南仓工账开始" not in bindings  # prose is NOT bound (structure only)
    assert "type: truth" not in bindings  # frontmatter excluded


def test_rollback_injects_binding_freeze_into_retry_feedback(tmp_path):
    from shenbi.pipeline.cli import _rollback_genesis_to_steps

    proj = _proj(tmp_path)
    state = _state_with_project(proj)
    _rollback_genesis_to_steps(state, [1], feedback="术语表与正文混用，需修")

    fb = state.genesis.retry_feedback["shenbi-worldbuilding"]
    assert "术语表与正文混用，需修" in fb
    assert "## 规则五：壁线（天穹之界）" in fb  # baseline rule headings ride along
    assert "逐字保留" in fb  # freeze instruction present
    # the binding snapshot persists for the post-regen drift report
    assert "## 规则五" in state.genesis.frozen_bindings["shenbi-worldbuilding"]


def test_rollback_without_feedback_still_freezes_structure(tmp_path):
    """A feedback-less reject still means redo — the binding injection alone
    must ride along (the shuffle vector is the prompt, not the feedback).
    """
    from shenbi.pipeline.cli import _rollback_genesis_to_steps

    proj = _proj(tmp_path)
    state = _state_with_project(proj)
    _rollback_genesis_to_steps(state, [3])

    fb = state.genesis.retry_feedback.get("shenbi-character-design", "")
    assert "林渡" in fb and "逐字保留" in fb


def test_binding_drift_report_names_renamed_and_added_lines(tmp_path):
    proj = _proj(tmp_path)
    state = _state_with_project(proj)
    state.genesis.frozen_bindings["shenbi-worldbuilding"] = genesis_mod.extract_structure_bindings(
        proj, "shenbi-worldbuilding"
    )
    # regen shuffled: renamed 规则五, renumbered, added a new rule
    shuffled = RULES_MD.replace("## 规则五：壁线（天穹之界）", "## 规则五：天界壁障").replace(
        "# 世界铁律\n", "# 世界铁律\n\n## 规则零：额外律\n"
    )
    (proj / "world" / "rules.md").write_text(shuffled, encoding="utf-8")

    drift = genesis_mod.binding_drift_report(state, proj)
    assert "规则五" in drift and "天界壁障" in drift
    assert "规则零" in drift  # additions reported too


def test_binding_drift_silent_when_structure_held(tmp_path):
    proj = _proj(tmp_path)
    state = _state_with_project(proj)
    state.genesis.frozen_bindings["shenbi-worldbuilding"] = genesis_mod.extract_structure_bindings(
        proj, "shenbi-worldbuilding"
    )
    # prose changed, structure intact — the semantic layer is the feedback's
    # job, not the drift gate's
    held = RULES_MD.replace("灵能源自地脉。", "灵能源自地脉，取之过度则枯。")
    (proj / "world" / "rules.md").write_text(held, encoding="utf-8")

    assert genesis_mod.binding_drift_report(state, proj) == ""


def test_genesis_complete_context_carries_drift_and_consumes_bindings(tmp_path, monkeypatch):
    proj = _proj(tmp_path)
    state = _state_with_project(proj)
    state.genesis.frozen_bindings["shenbi-worldbuilding"] = genesis_mod.extract_structure_bindings(
        proj, "shenbi-worldbuilding"
    )
    (proj / "world" / "rules.md").write_text(
        RULES_MD.replace("## 规则二：灵能守恒", "## 规则二：灵量守恒"), encoding="utf-8"
    )
    state.genesis.current_step = 16  # _advance(16) -> 17 -> genesis-complete raises

    raised: list[CheckpointType] = []

    def _fake_set(st, cp_type, **kw):
        raised.append(cp_type)
        set_checkpoint(st, cp_type, **kw)

    monkeypatch.setattr(genesis_mod, "set_checkpoint", _fake_set)
    genesis_mod._advance(state, 16, proj)

    assert raised == [CheckpointType.GENESIS_COMPLETE]
    assert "灵量守恒" in (state.pending_checkpoint.context or "")
    assert state.genesis.frozen_bindings == {}  # consumed at raise


def test_frozen_bindings_serialize_round_trip(tmp_path):
    import json

    proj = _proj(tmp_path)
    state = _state_with_project(proj)
    state.genesis.frozen_bindings["shenbi-worldbuilding"] = "## 规则一"
    state.genesis.frozen_bindings["shenbi-character-design"] = "林渡"

    payload = json.loads(json.dumps(state.to_dict()))
    restored = PipelineState.from_dict(payload)
    assert restored.genesis.frozen_bindings == {
        "shenbi-worldbuilding": "## 规则一",
        "shenbi-character-design": "林渡",
    }


#: Write-side drift guard (probe22 adjudication #002 P0-1 / #003 P3-4): the
#: prompt-side binding freeze was IGNORED by a full rewrite — the unsanctioned
#: canon swap landed at step 1 and steps 2-17 all dispatched on the wrong
#: base, the drift surfacing only at genesis-complete after a false
#: foundation-review verification. The machine cannot judge sanctioned vs
#: unsanctioned renames, so the guard must STOP, not verdict: raise the
#: genesis-complete checkpoint immediately with the drift leading the context,
#: frozen bindings intact.
def _redo_state(proj: Path) -> PipelineState:
    state = PipelineState.default(str(proj))
    state.genesis = GenesisStateData(
        state=GenesisState.PENDING,
        current_step=0,
        skills_done=[],
    )
    state.genesis.frozen_bindings["shenbi-worldbuilding"] = genesis_mod.extract_structure_bindings(
        proj, "shenbi-worldbuilding"
    )
    return state


def _mock_genesis_dispatch(monkeypatch, rules_text: str):
    from types import SimpleNamespace

    def _fake_dispatch(skill, project_dir, prompt, **kw):
        if skill == "shenbi-worldbuilding":
            (Path(project_dir) / "world" / "rules.md").write_text(rules_text, encoding="utf-8")
        return SimpleNamespace(success=True, stderr="", returncode=0)

    monkeypatch.setattr(genesis_mod, "dispatch_skill", _fake_dispatch)
    monkeypatch.setattr(
        genesis_mod,
        "run_gate_g4",
        lambda *a, **k: {"status": "PASS", "must_fix": [], "warnings": []},
    )


def test_redo_step_drift_stops_cycle_with_checkpoint(tmp_path, monkeypatch):
    proj = _proj(tmp_path)
    state = _redo_state(proj)
    _mock_genesis_dispatch(
        monkeypatch, RULES_MD.replace("## 规则二：灵能守恒", "## 规则二：灵量守恒")
    )

    stopped = genesis_mod.run_genesis_step(state, proj)

    assert stopped is True  # checkpoint reached — remaining steps NOT dispatched
    assert state.pending_checkpoint.type == CheckpointType.GENESIS_COMPLETE
    ctx = state.pending_checkpoint.context or ""
    assert "灵量守恒" in ctx and "漂移" in ctx
    assert "shenbi-worldbuilding" in state.genesis.frozen_bindings  # freeze NOT consumed
    assert "shenbi-worldbuilding" in state.genesis.skills_done
    assert state.genesis.current_step == len(genesis_mod.GENESIS_STEPS)


def test_redo_step_structure_held_advances_silently(tmp_path, monkeypatch):
    proj = _proj(tmp_path)
    state = _redo_state(proj)
    _mock_genesis_dispatch(monkeypatch, RULES_MD)  # structure held

    stopped = genesis_mod.run_genesis_step(state, proj)

    assert stopped is False
    assert state.genesis.current_step == 1
    assert state.pending_checkpoint.type == CheckpointType.NONE
    assert "shenbi-worldbuilding" in state.genesis.skills_done


def test_rollback_retains_original_freeze_and_drops_uncontested(tmp_path):
    """Rejecting the drift checkpoint with a redo list is the reviewer's
    verdict vocabulary: listed steps are re-dispatched against the ORIGINAL
    freeze (first-freeze-wins — the drifted output on disk must not crown
    itself the new baseline); UNLISTED frozen skills are uncontested and
    their freezes are consumed.
    """
    from shenbi.pipeline.cli import _rollback_genesis_to_steps

    proj = _proj(tmp_path)
    state = _state_with_project(proj)
    state.genesis.frozen_bindings = {
        "shenbi-worldbuilding": genesis_mod.extract_structure_bindings(
            proj, "shenbi-worldbuilding"
        ),
        "shenbi-character-design": genesis_mod.extract_structure_bindings(
            proj, "shenbi-character-design"
        ),
    }
    (proj / "world" / "rules.md").write_text(
        RULES_MD.replace("## 规则一：灵脉有竭", "## 规则一：灵潮有竭"), encoding="utf-8"
    )

    _rollback_genesis_to_steps(state, [1], feedback="修正")

    frozen = state.genesis.frozen_bindings["shenbi-worldbuilding"]
    assert "灵潮有竭" not in frozen  # original freeze retained, drifted disk NOT crowned
    assert "灵潮有竭" not in state.genesis.retry_feedback["shenbi-worldbuilding"]
    assert "shenbi-character-design" not in state.genesis.frozen_bindings  # uncontested → dropped
