"""spec #79 T1: regen-reset — quarantine + chapter-scoped state reset.

Fixtures under tests/fixtures/regen/ are real outputs copied from
novel-xinghuo-vol1 (G0.9: real-skill-output copies, trimmed for the face
under test). The synthetic minimal project mirrors that layout inline.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from shenbi.pipeline.state import PipelineState
from tools.regen_reset import run_reset

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "regen"
PRESERVED_TOP_KEYS = {"genesis", "config", "version", "project_dir", "phase"}


def _make_project(tmp_path: Path) -> Path:
    """Minimal project mirroring the real novel-xinghuo-vol1 layout."""
    p = tmp_path / "proj"
    for d in (
        "chapters",
        "plans",
        "adjudications",
        "audits",
        "gate-markers",
        "cost",
        "context",
        "outline",
        "truth",
        "characters",
    ):
        (p / d).mkdir(parents=True)
    (p / "chapters" / "chapter-1.md").write_text("# 第一章\n\n正文", encoding="utf-8")
    (p / "plans" / "chapter-1-plan.md").write_text("# plan", encoding="utf-8")
    (p / "pipeline-manifest.json").write_text("{}", encoding="utf-8")
    (p / "trace.jsonl").write_text("{}\n", encoding="utf-8")
    shutil.copy(FIXTURES / "pipeline-state.json", p / "pipeline-state.json")
    (p / "progress.json").write_text(
        json.dumps(
            {
                "current_scorer_agent": "chapter-dispatch:shenbi-chapter-drafting",
                "agent_trace": {
                    "shenbi-worldbuilding": "genesis-dispatch:shenbi-worldbuilding",
                    "ch1-key": "chapter-dispatch:shenbi-chapter-drafting",
                },
                "phase": "chapter-loop",
                "genesis_current_step": 17,
                "genesis_completed_skills": ["shenbi-worldbuilding"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (p / "truth" / "pending_hooks.md").write_text(
        "---\ntype: truth\ncategory: hooks\nstatus: active\n---\n# 钩子\n"
        "| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance | 升级曲线 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 红纸包 | PLANTED | 2 | 135 | 物象 | 高 | 8 | 线性 |\n",
        encoding="utf-8",
    )
    shutil.copy(FIXTURES / "character_matrix.md", p / "truth" / "character_matrix.md")
    shutil.copy(FIXTURES / "thread_map.md", p / "outline" / "thread_map.md")
    (p / "truth" / "state-settling-decisions.json").write_text(
        '{"$schema": "shenbi-decisions-v1"}', encoding="utf-8"
    )
    # derived caches
    (p / "truth-embeddings.db").write_bytes(b"stale")
    (p / "truth-index.json").write_text("{}", encoding="utf-8")
    (p / "context" / "ch1.json").write_text("{}", encoding="utf-8")
    (p / "truth" / "pending_hooks.md.lockfile").write_text('{"owner": "x"}', encoding="utf-8")
    # preserved face (byte-for-byte)
    (p / "truth" / "book_spine.md").write_text("spine-bytes", encoding="utf-8")
    (p / "characters" / "deng.md").write_text("card-bytes", encoding="utf-8")
    return p


def test_quarantine_moves_chapter_scoped_artifacts(tmp_path: Path) -> None:
    p = _make_project(tmp_path)
    assert run_reset(p, "pre-regen-test") == 0
    q = p / "_quarantine" / "pre-regen-test"
    assert (q / "chapters" / "chapter-1.md").is_file()
    assert (q / "plans" / "chapter-1-plan.md").is_file()
    assert (q / "pipeline-manifest.json").is_file()
    assert (q / "trace.jsonl").is_file()
    assert not (p / "chapters").exists()
    assert not (p / "pipeline-manifest.json").exists()
    assert (q / "RESET-MANIFEST.txt").is_file()


def test_cursor_reset_preserves_genesis_and_clears_rest(tmp_path: Path) -> None:
    p = _make_project(tmp_path)
    old_state = json.loads((p / "pipeline-state.json").read_text(encoding="utf-8"))
    old_genesis = old_state["genesis"]
    assert run_reset(p, "pre-regen-test") == 0
    new_state = json.loads((p / "pipeline-state.json").read_text(encoding="utf-8"))
    # genesis block carried over byte-equal in content
    assert new_state["genesis"] == old_genesis
    assert new_state["phase"] == "chapter-loop"
    assert new_state["config"] == old_state["config"]
    # chapter_loop is a zero shell: no chapter states, no retry maps
    cl = new_state["chapter_loop"]
    assert cl["chapter_states"] == {}
    assert cl["retry_counts"] == {}
    assert cl["retry_budget_consumed"] == {}
    assert cl["modify_feedback"] in (None, {})
    assert cl["retry_feedback"] in (None, {})
    assert cl["soft_fail_trackers"] == {}
    assert cl["current_chapter"] in (0, 1)
    # non-preserved top keys equal the framework zero state (PipelineState
    # serialization always carries every key — the assertion is "value is
    # zero", not "key vanished")
    fresh = PipelineState.default(project_dir=old_state["project_dir"]).to_dict()
    for key in (
        "closure",
        "closure_step",
        "closure_skills_done",
        "closure_retry_counts",
        "checkpoint_history",
        "pending_checkpoint",
        "pending_re_dispatches",
        "trigger_steps_done",
        "last_trigger_failure",
    ):
        assert new_state[key] == fresh[key], key
    # progress.json regenerated consistent: genesis trace kept, chapter trace dropped
    prog = json.loads((p / "progress.json").read_text(encoding="utf-8"))
    assert prog["phase"] == "chapter-loop"
    assert prog["agent_trace"] == {"shenbi-worldbuilding": "genesis-dispatch:shenbi-worldbuilding"}
    assert prog["current_scorer_agent"] is None
    assert prog["genesis_completed_skills"] == ["shenbi-worldbuilding"]


def test_derived_caches_cleared(tmp_path: Path) -> None:
    p = _make_project(tmp_path)
    assert run_reset(p, "pre-regen-test") == 0
    assert not (p / "truth-embeddings.db").exists()
    assert not (p / "context" / "ch1.json").exists()
    lock = p / "truth" / "pending_hooks.md.lockfile"
    assert json.loads(lock.read_text(encoding="utf-8")) == {}


def test_chapter_scoped_truth_reset_to_header_shells(tmp_path: Path) -> None:
    p = _make_project(tmp_path)
    assert run_reset(p, "pre-regen-test") == 0
    hooks = (p / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
    assert "Hook ID（钩子名）" in hooks
    assert "红纸包" not in hooks
    # dual-table: character_matrix back to template shell (heading + header row),
    # all chapter-increment sections gone
    cm = (p / "truth" / "character_matrix.md").read_text(encoding="utf-8")
    assert "| 角色A | 角色B | 关系性质 | 本章交互 | 变化 |" in cm
    assert "第10章" not in cm
    assert "状态增量" not in cm
    # absent keyed file is NOT created (bootstrap handles first write)
    assert not (p / "truth" / "timeline.md").exists()
    # decisions sidecar emptied
    assert (
        json.loads((p / "truth" / "state-settling-decisions.json").read_text(encoding="utf-8"))
        == {}
    )
    # thread_map: planning layer kept, progress rows normalized to 执行 0%
    tm = (p / "outline" / "thread_map.md").read_text(encoding="utf-8")
    assert "规划 100%／执行 0%" in tm
    assert "### A1: 名录与遗物匣（记忆的物质化）" in tm


def test_preserved_face_untouched_byte_for_byte(tmp_path: Path) -> None:
    p = _make_project(tmp_path)
    spine_before = (p / "truth" / "book_spine.md").read_bytes()
    card_before = (p / "characters" / "deng.md").read_bytes()
    assert run_reset(p, "pre-regen-test") == 0
    assert (p / "truth" / "book_spine.md").read_bytes() == spine_before
    assert (p / "characters" / "deng.md").read_bytes() == card_before


def test_existing_tag_fails_closed(tmp_path: Path) -> None:
    p = _make_project(tmp_path)
    assert run_reset(p, "pre-regen-test") == 0
    assert run_reset(p, "pre-regen-test") == 1


def test_dry_run_leaves_filesystem_unchanged(tmp_path: Path) -> None:
    p = _make_project(tmp_path)
    before = {
        f: f.read_bytes()
        for f in sorted(p.rglob("*"))
        if f.is_file() and "_quarantine" not in f.parts
    }
    assert run_reset(p, "pre-regen-test", dry_run=True) == 0
    after = {
        f: f.read_bytes()
        for f in sorted(p.rglob("*"))
        if f.is_file() and "_quarantine" not in f.parts
    }
    assert before == after
    assert not (p / "_quarantine").exists()


def test_real_layout_fixture_full_run(tmp_path: Path) -> None:
    """Real 15-key pipeline-state.json from novel-xinghuo-vol1 through the reset."""
    p = _make_project(tmp_path)
    old = json.loads((p / "pipeline-state.json").read_text(encoding="utf-8"))
    assert set(old.keys()) >= {
        "genesis",
        "config",
        "phase",
        "chapter_loop",
        "checkpoint_history",
        "closure",
        "pending_checkpoint",
        "last_trigger_failure",
        "trigger_steps_done",
    }
    assert run_reset(p, "pre-regen-test") == 0
    new = json.loads((p / "pipeline-state.json").read_text(encoding="utf-8"))
    # full-state differential against the framework zero state: only the
    # preserved keys may differ from PipelineState.default (phase normalized
    # to chapter-loop, genesis/config/version/project_dir carried over)
    fresh = PipelineState.default(project_dir=old["project_dir"]).to_dict()
    diff = {k for k in set(new) | set(fresh) if new.get(k) != fresh.get(k)}
    assert diff <= PRESERVED_TOP_KEYS, f"unexpected non-zero keys: {diff}"
    assert new["genesis"] == old["genesis"]
    assert new["phase"] == "chapter-loop"
