#!/usr/bin/env python
"""One-off staging residue cleanup (SDD #21 R3.4).

Decision rules (three branches, spec #21):

1. ``staging/plans/chapter-N-plan.md`` — deleted only when the committed
   ``plans/chapter-N-plan.md`` already exists (the staged draft is stale).
2. ``staging/truth/<file>`` WITH a keyed-upsert entry in the
   ``.staging-meta.json`` sidecar — staged rows whose key is MISSING from
   the live ``truth/<file>`` are replayed into live (via truth_io upsert)
   BEFORE the staged file is deleted; rows whose key exists in live keep the
   live version (live is the authority — deleting data or blindly committing
   the staged snapshot would both lose information).
3. ``staging/truth/<file>`` WITHOUT a sidecar entry (free-text truth files,
   no key semantics) — NOT auto-replayed; reported as "manual diff needed".
   Never silently whole-file committed (that is the last-writer-wins bug
   this spec fixes).

Default is DRY-RUN (prints the plan); pass ``--apply`` to execute.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.truth_io import (
    has_markdown_row,
    is_separator_row,
    split_table_cells,
    upsert_markdown_row,
)
from shenbi.safe_write import safe_write

log = get_logger(__name__)


def _plan_actions(project_dir: Path) -> list[tuple[str, str]]:
    """(staged file, action) pairs for staging/plans/."""
    out: list[tuple[str, str]] = []
    staged_plans = project_dir / "staging" / "plans"
    if not staged_plans.is_dir():
        return out
    for f in sorted(staged_plans.iterdir()):
        committed = project_dir / "plans" / f.name
        if f.name.endswith("-decisions.json"):
            # Layer-A decisions sidecars staged next to their plan; the
            # contract commits only the .md. Preserve the data: move the
            # sidecar next to the committed plan once the plan exists.
            plan_md = committed.with_name(committed.name.replace("-decisions.json", ".md"))
            if plan_md.exists() and not committed.exists():
                out.append((str(f), "move to plans/ (preserve decisions data)"))
            else:
                out.append((str(f), "keep (plan not committed or already moved)"))
        elif f.suffix == ".md":
            if committed.exists():
                out.append((str(f), "delete (committed version exists)"))
            else:
                out.append((str(f), "keep (no committed version)"))
    return out


def _replay_rows(staged_text: str, live_text: str, key_field: str) -> tuple[str, int]:
    """Live-priority replay: return (merged live text, replayed row count)."""
    merged = live_text
    replayed = 0
    for line in staged_text.split("\n"):
        cells = split_table_cells(line)
        if cells is None or is_separator_row(cells):
            continue
        if not has_markdown_row(merged, line, key_field):
            merged = upsert_markdown_row(merged, line, key_field)
            replayed += 1
    return merged, replayed


def _truth_actions(project_dir: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    staged_truth = project_dir / "staging" / "truth"
    if not staged_truth.is_dir():
        return out
    meta: dict[str, dict[str, str]] = {}
    meta_path = project_dir / "staging" / ".staging-meta.json"
    if meta_path.exists():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                meta = loaded
        except (OSError, ValueError):
            log.warning("staging_meta_unreadable", path=str(meta_path))
    for f in sorted(staged_truth.glob("*.md")):
        target = f"truth/{f.name}"
        entry = meta.get(target)
        live = project_dir / "truth" / f.name
        if entry and entry.get("key_field"):
            live_text = live.read_text(encoding="utf-8") if live.exists() else ""
            _, replayed = _replay_rows(
                f.read_text(encoding="utf-8"), live_text, str(entry["key_field"])
            )
            out.append(
                {
                    "staged": str(f),
                    "action": f"replay {replayed} missing-key row(s) into live, then delete",
                }
            )
        else:
            out.append({"staged": str(f), "action": "MANUAL DIFF NEEDED (no key semantics)"})
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry: report (and with --apply, execute) the staging cleanup."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="execute (default: dry-run)")
    args = parser.parse_args(argv)
    project_dir = args.project_dir
    staging = project_dir / "staging"
    if not staging.is_dir():
        print("no staging directory; nothing to do")
        return 0

    plan_actions = _plan_actions(project_dir)
    truth_actions = _truth_actions(project_dir)

    print("== staging/plans ==")
    for path, action in plan_actions:
        print(f"  {action}: {path}")
    print("== staging/truth ==")
    for rec in truth_actions:
        print(f"  {rec['action']}: {rec['staged']}")

    if not args.apply:
        print("dry-run; pass --apply to execute")
        return 0

    for path_str, action in plan_actions:
        src = Path(path_str)
        if action.startswith("delete"):
            src.unlink()
        elif action.startswith("move"):
            dest = project_dir / "plans" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            src.unlink()
            print(f"moved {src} -> {dest}")

    for rec in truth_actions:
        action = str(rec["action"])
        staged_path = Path(str(rec["staged"]))
        if action.startswith("replay"):
            target = f"truth/{staged_path.name}"
            entry_key = _entry_key(project_dir, target)
            if entry_key is None:
                print(f"SKIP (meta lost): {staged_path}")
                continue
            live = project_dir / "truth" / staged_path.name
            live_text = live.read_text(encoding="utf-8") if live.exists() else ""
            merged, replayed = _replay_rows(
                staged_path.read_text(encoding="utf-8"), live_text, entry_key
            )
            safe_write(live, merged.encode("utf-8"))
            print(f"replayed {replayed} row(s) into {live}; deleted {staged_path}")
            staged_path.unlink()
        else:
            print(f"KEPT for manual diff: {staged_path}")
    return 0


def _entry_key(project_dir: Path, target: str) -> str | None:
    """Re-read the sidecar for *target*'s key_field."""
    meta_path = project_dir / "staging" / ".staging-meta.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = meta.get(target) if isinstance(meta, dict) else None
    return str(entry.get("key_field")) if entry and entry.get("key_field") else None


if __name__ == "__main__":
    sys.exit(main())
