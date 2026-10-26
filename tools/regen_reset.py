"""spec #79 regen-reset: quarantine the old chapter run, reset chapter-scoped state.

One-shot per-tag tool (fail-closed: an existing tag never gets overwritten —
_quarantine already holds ad-hoc drafting dumps). Moves chapter-scoped
artifacts into ``_quarantine/<tag>/`` (relative layout kept), resets
pipeline-state/progress to a post-genesis zero state (genesis block preserved
— paid genesis is never re-run), rewrites chapter-scoped truth tables as
header shells keyed off ``truth_io._TABLE_HEADER_BOOTSTRAP``, and clears the
derived caches (embeddings / index / context) whose stale chapter chunks
would poison regeneration context. World/character/volume truth is preserved
byte-for-byte; thread_map's #74 planning layer is normalized (「当前进度」
rows back to 执行 0%), never wiped. Zero LLM, zero dispatch, zero
src/shenbi mutation. Exit codes: 0 ok / 1 fail / 2 usage.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.pipeline.state import PipelineState
from shenbi.pipeline.truth_index import build_index
from shenbi.pipeline.truth_io import _TABLE_HEADER_BOOTSTRAP

# Chapter-scoped artifacts moved into _quarantine/<tag>/ (relative layout kept).
# The manifest/trace ride along because a stale manifest would let
# release_split pack quarantined chapters (spec #79 §1).
_QUARANTINE_DIRS = ("chapters", "plans", "adjudications", "audits", "gate-markers", "cost")
_QUARANTINE_FILES = (
    "pipeline-manifest.json",
    "pipeline-manifest.json.lockfile",
    "trace.jsonl",
    "trace.jsonl.lockfile",
)

# pipeline-state top keys carried over from the old run; phase is normalized
# to chapter-loop (genesis already done — chapters existed to quarantine).
_PRESERVED_STATE_KEYS = ("genesis", "config", "version", "project_dir")

# Keyed table files reset to a header shell. arc_payoff_trend stays out
# (volume-keyed). character_matrix is dual-table: its whole body is chapter
# run data (main 交互表 + per-chapter 状态增量 sections) — reset is a full
# template shell, the "信息边界" face is the file's settle-managed skeleton.
_TABLE_SHELL_FILES = (
    "pending_hooks.md",
    "current_state.md",
    "character_matrix.md",
    "chapter_summaries.md",
    "emotional_arcs.md",
    "subplot_board.md",
    "bridge_tracker.md",
    "particle_ledger.md",
    "resonance_anchors.md",
    "resonance_trend.md",
    "timeline.md",
    "prop_registry.md",
)

# Non-table chapter-scoped truth files reset to their init-template shell
# (frontmatter + heading + guidance line — the state-settling first-run shape).
_TEMPLATE_SHELLS: dict[str, tuple[str, str]] = {
    "current_focus.md": ("intent", "# 当前关注点"),
    "drift_guidance.md": ("state", "# 纠偏指导"),
    "audit_drift.md": ("state", "# 审计纠偏"),
}

_GUIDANCE_LINE = "> 此文件由 state-settling 首次运行时填充实际数据。"

_PROGRESS_RE = re.compile(r"- \*\*当前进度\*\*: 规划 100%／执行 \d+%")  # noqa: RUF001

#: Derived caches deleted outright: the index is rebuilt inline (build_index
#: tolerates the reset truth shells), embeddings rebuild lazily on the next
#: chapter's context assembly — a stale copy is precisely the poison the
#: reset exists to remove (spec #79 §1).
_DERIVED_CACHE_FILES = ("truth-embeddings.db", "truth-index.json")
_DERIVED_CACHE_DIRS = ("context",)


def _shell_frontmatter(category: str) -> str:
    return f"---\ntype: truth\ncategory: {category}\nstatus: initialized\n---\n"


def _table_shell(name: str, old_category: str | None) -> str:
    header = _TABLE_HEADER_BOOTSTRAP[name]
    cols = header.count("|") - 1
    sep = "|" + "---|" * cols
    fm = _shell_frontmatter(old_category or "state")
    return f"{fm}\n{header}\n{sep}\n"


def _old_frontmatter_category(text: str) -> str | None:
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return None
    cm = re.search(r"^category:\s*(\S+)", m.group(1), flags=re.M)
    return cm.group(1) if cm else None


def _reset_state(pipeline_state: Path) -> None:
    old = json.loads(pipeline_state.read_text(encoding="utf-8"))
    fresh = PipelineState.default(project_dir=old.get("project_dir", "")).to_dict()
    for key in _PRESERVED_STATE_KEYS:
        if key in old:
            fresh[key] = old[key]
    fresh["phase"] = "chapter-loop"
    pipeline_state.write_text(
        json.dumps(fresh, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _reset_progress(progress: Path, phase: str) -> None:
    old: dict[str, Any] = {}
    if progress.is_file():
        old = json.loads(progress.read_text(encoding="utf-8"))
    genesis_trace = {
        k: v for k, v in old.get("agent_trace", {}).items() if str(v).startswith("genesis")
    }
    fresh = {
        "current_scorer_agent": None,
        "agent_trace": genesis_trace,
        "phase": phase,
        "genesis_current_step": old.get("genesis_current_step"),
        "genesis_completed_skills": old.get("genesis_completed_skills", []),
    }
    progress.write_text(json.dumps(fresh, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalize_thread_map(thread_map: Path) -> None:
    """Normalize the #74 planning layer: progress rows back to 执行 0%.

    The planning rows (spans, 推进形态, 高潮窗口) are spec-#74 data and stay;
    only the run-progress markers reset. Overview rows reconcile from the
    detail sections (truth_io), so no separate table surgery here.
    """
    if not thread_map.is_file():
        return
    text = thread_map.read_text(encoding="utf-8")
    normalized = _PROGRESS_RE.sub("- **当前进度**: 规划 100%／执行 0%", text)  # noqa: RUF001
    if normalized != text:
        thread_map.write_text(normalized, encoding="utf-8")


def _clear_snapshots_key(project_dir: Path) -> None:
    """Drop last_drift_chapter from snapshots/manifest.json (absent dir is fine)."""
    snaps = project_dir / "snapshots" / "manifest.json"
    if not snaps.is_file():
        return
    data = json.loads(snaps.read_text(encoding="utf-8"))
    data.pop("last_drift_chapter", None)
    snaps.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _clear_derived_caches(project_dir: Path) -> None:
    """Delete embeddings/index/context — stale chapter chunks poison regeneration."""
    for f in _DERIVED_CACHE_FILES:
        target = project_dir / f
        if target.exists():
            target.unlink()
    for d in _DERIVED_CACHE_DIRS:
        target = project_dir / d
        if target.is_dir():
            shutil.rmtree(target)


def _plan_actions(project_dir: Path, tag: str) -> list[str]:
    """Collect the ordered action list (also the dry-run face)."""
    truth = project_dir / "truth"
    actions = [
        f"move dir  {d}/ -> _quarantine/{tag}/{d}/"
        for d in _QUARANTINE_DIRS
        if (project_dir / d).is_dir()
    ]
    actions += [
        f"move file {f} -> _quarantine/{tag}/{f}"
        for f in _QUARANTINE_FILES
        if (project_dir / f).is_file()
    ]
    actions.append("reset      pipeline-state.json (genesis/config/version/project_dir kept)")
    actions.append("regen      progress.json (genesis trace kept)")
    actions.append("clear      snapshots/manifest.json last_drift_chapter")
    actions += [
        f"delete     {f} (stale chapter chunks would poison context)"
        for f in _DERIVED_CACHE_FILES
        if (project_dir / f).exists()
    ]
    actions += [f"delete dir {d}/" for d in _DERIVED_CACHE_DIRS if (project_dir / d).is_dir()]
    actions.append("zero       remaining *.lockfile")
    actions += [
        f"shell      truth/{n} -> bootstrap header"
        for n in _TABLE_SHELL_FILES
        if (truth / n).is_file()
    ]
    actions += [
        f"shell      truth/{n} -> init template" for n in _TEMPLATE_SHELLS if (truth / n).is_file()
    ]
    if (truth / "state-settling-decisions.json").is_file():
        actions.append("empty      truth/state-settling-decisions.json")
    if (truth / "state_snapshot-pre-rev.md").is_file():
        actions.append(f"move file truth/state_snapshot-pre-rev.md -> _quarantine/{tag}/truth/")
    actions.append("normalize  outline/thread_map.md 当前进度 -> 执行 0%")
    return actions


def _execute_reset(project_dir: Path, tag: str, actions: list[str]) -> None:
    """Apply the planned actions (guard checks already passed)."""
    quarantine = project_dir / "_quarantine" / tag
    quarantine.mkdir(parents=True)
    for d in _QUARANTINE_DIRS:
        src = project_dir / d
        if src.is_dir():
            shutil.move(str(src), str(quarantine / d))
    for f in _QUARANTINE_FILES:
        src = project_dir / f
        if src.is_file():
            shutil.move(str(src), str(quarantine / f))

    state_path = project_dir / "pipeline-state.json"
    if state_path.is_file():
        _reset_state(state_path)
    _reset_progress(project_dir / "progress.json", "chapter-loop")

    _clear_snapshots_key(project_dir)
    _clear_derived_caches(project_dir)

    for lock in project_dir.rglob("*.lockfile"):
        if "_quarantine" not in lock.parts:
            lock.write_text("{}", encoding="utf-8")

    _reset_truth_shells(project_dir, tag)
    _normalize_thread_map(project_dir / "outline" / "thread_map.md")

    # rebuild the truth index inline over the reset shells (deterministic,
    # local — zero LLM); embeddings rebuild lazily on next context assembly
    try:
        build_index(project_dir)
    except Exception as exc:  # noqa: BLE001 — index rebuild is best-effort, logged
        print(f"regen-reset: truth-index rebuild deferred ({exc})", file=sys.stderr)

    stamp = datetime.now(UTC).isoformat()
    (quarantine / "RESET-MANIFEST.txt").write_text(
        f"regen-reset {tag} @ {stamp}\nproject: {project_dir}\n\n" + "\n".join(actions) + "\n",
        encoding="utf-8",
    )


def _reset_truth_shells(project_dir: Path, tag: str) -> None:
    """Rewrite chapter-scoped truth files to shell state (present files only)."""
    truth = project_dir / "truth"
    for name in _TABLE_SHELL_FILES:
        target = truth / name
        if target.is_file():
            cat = _old_frontmatter_category(target.read_text(encoding="utf-8"))
            target.write_text(_table_shell(name, cat), encoding="utf-8")
    for name, (cat, heading) in _TEMPLATE_SHELLS.items():
        target = truth / name
        if target.is_file():
            target.write_text(
                f"{_shell_frontmatter(cat)}\n{heading}\n\n{_GUIDANCE_LINE}\n",
                encoding="utf-8",
            )
    decisions = truth / "state-settling-decisions.json"
    if decisions.is_file():
        decisions.write_text("{}", encoding="utf-8")
    snapshot = truth / "state_snapshot-pre-rev.md"
    if snapshot.is_file():
        q_truth = project_dir / "_quarantine" / tag / "truth"
        q_truth.mkdir(parents=True, exist_ok=True)
        shutil.move(str(snapshot), str(q_truth / snapshot.name))


def run_reset(project_dir: Path, tag: str, dry_run: bool = False) -> int:
    """Execute the reset; returns the process exit code (0 ok / 1 fail)."""
    if not project_dir.is_dir():
        print(f"regen-reset: project dir not found: {project_dir}", file=sys.stderr)
        return 2
    quarantine = project_dir / "_quarantine" / tag
    if quarantine.exists():
        print(
            f"regen-reset: tag already exists, refusing to overwrite: {quarantine}",
            file=sys.stderr,
        )
        return 1
    chapters = project_dir / "chapters"
    if not chapters.is_dir() or not any(chapters.glob("chapter-*.md")):
        print("regen-reset: no chapters to quarantine (nothing to reset)", file=sys.stderr)
        return 1

    actions = _plan_actions(project_dir, tag)
    if dry_run:
        print(f"regen-reset DRY-RUN plan for {project_dir} (tag={tag}):")
        for a in actions:
            print(f"  {a}")
        return 0

    _execute_reset(project_dir, tag, actions)
    print(f"regen-reset: quarantined under _quarantine/{tag} ({len(actions)} actions)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: regen-reset <dir> --tag T [--dry-run]."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--tag", required=True, help="quarantine tag, e.g. pre-regen-2026-10")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, touch nothing")
    args = parser.parse_args(argv)
    return run_reset(args.project_dir, args.tag, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
