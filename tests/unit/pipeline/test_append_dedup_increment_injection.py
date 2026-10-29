r"""Generic append_dedup increment-shape injection (phase3 esc#2).

novel-xinghuo-phase3 ch12: triggered ``shenbi-score-arc`` echoed the whole
live ``truth/audit_drift.md`` (frontmatter + H1 + every section) with the
new entries appended — the ingestion guard correctly rejected it pre-write,
but the failure was deterministic: the user prompt never taught the
sanctioned increment form (the state-settling blocks cover only settle's
own targets) and the json_mode output block's "COMPLETE file content" line
is an active contra-instruction for append_dedup targets. Same-day the same
target rejected 4-of-4 first attempts across skills; only the writers with
a corrective-feedback loop converged.

The generic injection renders, for every FILLED append_dedup truth target
of any NON-settle writer, the same sanctioned form the guard enforces.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.dispatch_helper import _build_skill_prompt

GENERIC_MARKER = "append_dedup"

_FILLED_DRIFT = """---
type: truth
category: state
status: active
last_append_chapter: 1
---

# 审计纠偏

### 第1章

- 共鸣短板：开篇钩子可再前置
"""

_SHELL_DRIFT = """---
type: truth
category: state
status: initialized
---

# 审计纠偏

> （待填充——本表由各逐章门 append 短板条目）
"""

_FILLED_HOOKS = """---
type: truth
---

# 伏笔池

### MH05（余孽册的三本册子）

- hook_id: MH05
- plant_chapter: 2
"""


def _project(tmp_path: Path, drift: str = _FILLED_DRIFT, hooks: str | None = None) -> Path:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "audit_drift.md").write_text(drift, encoding="utf-8")
    if hooks is not None:
        (tmp_path / "truth" / "pending_hooks.md").write_text(hooks, encoding="utf-8")
    return tmp_path


def _user_prompt(skill: str, project: Path, json_mode: bool = True) -> str:
    _system, user, _paths, _extras, _ = _build_skill_prompt(
        skill, project, "task", 12, json_mode=json_mode
    )
    return user


class TestGenericFilledContract:
    def test_score_arc_gets_section_increment_form_and_bans(self, tmp_path):
        user = _user_prompt("shenbi-score-arc", _project(tmp_path))
        assert "truth/audit_drift.md" in user
        # sanctioned form: section-block increment along the live layout
        assert "第N章" in user
        # bans the exact forms the guard rejects
        assert ("frontmatter" in user and "# 审计纠偏" in user) or "整档" in user

    def test_settle_writer_keeps_its_own_blocks_only(self, tmp_path):
        user = _user_prompt("shenbi-state-settling", _project(tmp_path))
        assert "APPEND-ONLY HARD CONSTRAINT" in user  # matrix block intact
        assert "pending_hooks.md INCREMENT SHAPE" in user  # hooks block intact

    def test_shell_base_gets_no_filled_contract(self, tmp_path):
        user = _user_prompt("shenbi-score-arc", _project(tmp_path, drift=_SHELL_DRIFT))
        assert GENERIC_MARKER not in user.replace("## 逐目标基座态", "") or ("FILLED" not in user)

    def test_hook_key_writer_gets_hooks_shape_block(self, tmp_path):
        project = _project(tmp_path, hooks=_FILLED_HOOKS)
        user = _user_prompt("shenbi-foreshadowing-resolve", project)
        assert "pending_hooks.md INCREMENT SHAPE" in user


class TestJsonModeCarveOut:
    def test_carve_out_present_for_ad_writer(self, tmp_path):
        user = _user_prompt("shenbi-score-arc", _project(tmp_path))
        assert "EXCEPT" in user and "increment" in user

    def test_carve_out_absent_for_non_ad_writer(self, tmp_path):
        user = _user_prompt("shenbi-worldbuilding", _project(tmp_path))
        assert "EXCEPT" not in user
