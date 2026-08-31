"""materialize_progress：progress.json 降级为 trace 派生视图（spec 支柱四）。
重放 INIT/MARK_DONE 重建 progress dict，经 safe_write 落盘。语义对齐
原 update_progress（三个 test_type 均 done/skip → completed）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shenbi.status import SkillProgressStatus
from shenbi.trace.replay import replay

_TEST_TYPES = ("generative", "bug-hunt", "clean")


def _as_int(value: object, default: int) -> int:
    return int(value) if isinstance(value, (int, float, str)) else default


def _as_float(value: object, default: float) -> float:
    return float(value) if isinstance(value, (int, float)) else default


def _empty_skill() -> dict[str, dict[str, Any]]:
    """Match update_progress.cmd_init: every skill starts three-phase pending."""
    return {tt: {"status": SkillProgressStatus.PENDING} for tt in _TEST_TYPES}


def materialize_progress(
    round_dir: Path,
    *,
    total_skills: list[str],
    tier: str = "T1",
    expected_chapters: int = 67,
) -> dict[str, Any]:
    """Reconstruct progress.json from trace (I1/I2 fix: match update_progress semantics).

    Per-phase queues (NOT total - genuinely_done): remaining_generative = skills
    not done on generative specifically. Skills sub-structure defaults to
    three-pending (not empty) for unmarked skills — matches cmd_init.
    """
    events = replay(round_dir)
    skills_state: dict[str, dict[str, dict[str, Any]]] = {}
    trace_known: set[tuple[str, str]] = set()  # (skill, test_type) MARK_DONE-derived
    init_tier, init_chapters = tier, expected_chapters
    for e in events:
        if e.action == "INIT":
            payload = e.payload
            init_tier = str(payload.get("tier", tier))
            init_chapters = _as_int(payload.get("expected_chapters"), expected_chapters)
        elif e.action == "MARK_DONE":
            payload = e.payload
            skill = str(payload.get("skill"))
            tt = str(payload.get("test_type"))
            sd = skills_state.setdefault(skill, _empty_skill())  # I2: default three-pending
            trace_known.add((skill, tt))
            sd[tt] = {
                "status": str(payload.get("status", SkillProgressStatus.DONE)),
                "score": _as_float(payload.get("score"), 0.0),
            }

    all_skills_set = set(total_skills)

    # I1 fix: per-phase pending (mirror cmd_rebuild_queues semantics)
    def _pending(test_type: str) -> set[str]:
        return all_skills_set - {
            sn
            for sn, sd in skills_state.items()
            if sd.get(test_type, {}).get("status")
            in (SkillProgressStatus.DONE, SkillProgressStatus.SKIP)
        }

    genuinely_done = sorted(
        all_skills_set - (_pending("generative") | _pending("bug-hunt") | _pending("clean"))
    )
    # I2 fix: unmarked skills get three-pending structure (not empty)
    skills_full = {skill: skills_state.get(skill, _empty_skill()) for skill in sorted(total_skills)}
    out: dict[str, Any] = {
        "round": Path(round_dir).name.split("-")[1] if "round-" in str(round_dir) else "???",
        "tier": init_tier,
        "completed_skill_names": genuinely_done,
        "skills": skills_full,
        "remaining_generative": sorted(_pending("generative")),
        "remaining_bug_hunt": sorted(_pending("bug-hunt")),
        "remaining_clean": sorted(_pending("clean")),
        "total_framework_skills": len(total_skills),
        "expected_chapters": init_chapters,
    }
    # spec #37 F630: merge into existing progress.json instead of
    # wholesale-replacing it — materialize-owned top-level keys win, foreign
    # top-level keys survive, and skills entries merge per skill/test_type
    # so trace-unknown completions (e.g. dispatcher/G3-written DONE entries)
    # are preserved.
    progress_path = Path(round_dir) / "progress.json"
    owned_top = {
        "round",
        "tier",
        "completed_skill_names",
        "skills",
        "remaining_generative",
        "remaining_bug_hunt",
        "remaining_clean",
        "total_framework_skills",
        "expected_chapters",
    }

    def _merge(existing: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {k: v for k, v in existing.items() if k not in owned_top}
        merged.update(out)
        old_skills = existing.get("skills")
        if isinstance(old_skills, dict):
            for skill, entry in out.get("skills", {}).items():
                old_entry = old_skills.get(skill)
                if not (isinstance(old_entry, dict) and isinstance(entry, dict)):
                    continue
                # Trace-UNKNOWN pairs keep the existing value (e.g. a
                # dispatcher/G3-written DONE); trace-known pairs take the
                # replayed value.
                merged_entry = {
                    tt: (val if (skill, tt) in trace_known else dict(old_entry).get(tt, val))
                    for tt, val in entry.items()
                }
                for tt, old_val in old_entry.items():
                    if tt not in merged_entry:
                        merged_entry[tt] = old_val
                # NOTE: this also mutates out["skills"] in place (same object),
                # so the returned dict matches what landed on disk.
                merged["skills"][skill] = merged_entry
        return merged

    from shenbi.safe_write import locked_transact

    locked_transact(
        progress_path,
        _merge,
        round_dir=Path(round_dir),
        trace_action="MATERIALIZE",
    )
    return out
