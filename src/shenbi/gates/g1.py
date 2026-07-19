"""G1: input validation gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import fnmatch
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.contracts.legacy import load_registry
from shenbi.gates.shared import (
    SKILLS,
    bak_path,
    normalize_file_paths,
    fail,
    jload,
    passed,
    yload,
)
from shenbi.safe_write import safe_write


def derive_backup_skills() -> frozenset[str]:
    """Auto-derive skills needing a ``.bak``: ``updates:`` intersects truth-kind concepts.

    Replaces the former hardcoded frozenset of 9, which silently missed
    several truth-updaters (e.g. review-resonance, memory-distill) and
    caused G2.11's truth-diff to no-op for them. The derived set covers
    every skill whose contract ``updates`` a truth-kind concept (matched
    verbatim or via a declared registry glob like ``truth/*.md``), so a new
    truth-updater is covered automatically with no gate edit.

    Non-truth updaters (world/, outline/, config files) are excluded: their
    ``.bak`` files were never read by G2.11 (which only fires for
    ``file_type == "truth"``), so backing them up was dead work.

    Optimization: load the registry ONCE (not per-skill) and read raw
    frontmatter directly (``read_frontmatter_contract``), avoiding the
    O(#skills) registry reloads that ``load_contract`` would trigger.
    """
    from shenbi.contracts.legacy import read_frontmatter_contract

    reg = load_registry()
    truth_names = {c.name for c in reg.concepts if c.kind == "truth"}
    result: set[str] = set()
    for skill_dir in SKILLS.iterdir():
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        skill = skill_dir.name
        try:
            raw = read_frontmatter_contract(skill, skill_md)
            updates = raw.get("updates", [])
        except Exception:
            # Skills without a contract block (e.g. writing-skills) cannot
            # be truth-updaters; skip them rather than aborting import.
            continue
        if not updates:
            continue  # fast-skip non-updaters
        for f in updates:
            # Normalize dict-form writes/updates (spec §3.2): {file, mode?, ...}
            if isinstance(f, dict) and "file" in f:
                f = str(f["file"])
            if not isinstance(f, str):
                continue  # skip malformed entries gracefully
            # Match both directions: a declared glob like ``truth/*.md`` (f is
            # the pattern, t is the literal concept) and a literal update
            # against a registry glob concept. ``f == t`` covers exact hits.
            if any(f == t or fnmatch.fnmatch(f, t) or fnmatch.fnmatch(t, f) for t in truth_names):
                result.add(skill)
                break
    return frozenset(result)


BACKUP_SKILLS: frozenset[str] = (
    derive_backup_skills()
)  # computed at import; covers all truth-updaters


def compute_backup_targets(
    skill_name: str | None, file_paths: list[str], round_dir: str | None
) -> list[tuple[str, str]]:
    """Pure decision: which (src_path, bak_path) pairs to create for an in-place skill.

    Extracted from G1.4 so the backup decision is testable without I/O. The
    gate still performs the copy (G2.11 truth-diff depends on the .bak
    existing pre-dispatch); moving the write fully to the dispatcher is a
    follow-up orchestration refactor (out of scope here).
    """
    if not skill_name or skill_name not in BACKUP_SKILLS or not round_dir:
        return []
    return [(fp, bak_path(fp)) for fp in file_paths]


def check_fields_exist(
    skill: str, inputs: list[str], fields_map: dict[str, list[str]]
) -> list[str]:
    """WARN (not FAIL) if declared fields are not found in input files.

    Runs before _build_skill_prompt's filtering, so skill authors see
    field-name drift warnings before the LLM sees filtered content.
    Non-blocking — returns warning strings only.

    Markdown files: declared field names are matched against the literal
    text of ``## H2`` headings (e.g. ``## Foo Bar`` is matched as
    ``"Foo Bar"``). JSON files: matched against top-level keys of an
    object. Files not present on disk, or of other extensions, are skipped
    silently (existence is G1.1's concern).
    """
    warnings: list[str] = []
    for fp in inputs:
        fields = fields_map.get(fp) or fields_map.get(Path(fp).name)
        if not fields:
            continue
        p = Path(fp)
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")
        if fp.endswith(".md"):
            # Collect literal H2 heading text (no snake_case normalization).
            actual: set[str] = set()
            for line in content.splitlines():
                if line.startswith("## "):
                    actual.add(line[3:].strip())
            missing = set(fields) - actual
            if missing:
                warnings.append(f"{fp}: declared fields {missing} not found in file")
        elif fp.endswith(".json"):
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                continue  # G1.2 already handles JSON parse errors
            if isinstance(data, dict):
                missing = set(fields) - set(data.keys())
                if missing:
                    warnings.append(f"{fp}: declared keys {missing} not found in file")
    return warnings


def gate_G1(
    skill_name: str | None = None,
    input_files: str | list[str] | None = None,
    round_dir: str | None = None,
) -> str:
    """G1: Pre-dispatch input validation."""
    c: list[Any] = []
    mf: list[Any] = []

    # Normalize input_files (accept JSON string, list, or comma-separated string)
    if isinstance(input_files, str):
        try:
            input_files = json.loads(input_files)
        except (json.JSONDecodeError, ValueError):
            pass
    fps = normalize_file_paths(input_files)
    rd = Path(round_dir) if round_dir else None
    targets = compute_backup_targets(skill_name, fps, str(rd) if rd else None)

    # Expand glob patterns before validation.
    # Genesis-mode: unmatched globs that match SHENBI_G1_SKIP_READS are silently
    # dropped (the files don't exist yet). All other unmatched globs are kept as
    # literal paths so G1.1 fails clearly on missing required inputs.
    import glob as _glob
    import os as _os
    from fnmatch import fnmatch as _fnmatch

    skip_raw = _os.environ.get("SHENBI_G1_SKIP_READS", "")
    skip_patterns = [p.strip() for p in skip_raw.split(",") if p.strip()] if skip_raw else []

    expanded_fps: list[str] = []
    for fp in fps:
        if fp != _glob.escape(fp):  # glob.escape covers *, ?, [...], [!...]
            matches = _glob.glob(fp, recursive=True)
            if matches:
                for m in matches:
                    if m not in expanded_fps:
                        expanded_fps.append(m)
            elif skip_patterns and any(_fnmatch(Path(fp).name, pat) for pat in skip_patterns):
                # Unmatched optional glob in genesis mode; silently skip
                pass
            # Unmatched required glob; keep literal path so G1.1 fails
            elif fp not in expanded_fps:
                expanded_fps.append(fp)
        elif fp not in expanded_fps:
            expanded_fps.append(fp)
    fps = expanded_fps

    for fp in fps:
        p = Path(fp)

        # G1.1 — file exists and non-empty
        if not p.exists():
            mf.append({"id": "G1.1", "file": fp, "s": "FAIL", "r": "not found"})
            continue
        if p.stat().st_size == 0:
            mf.append({"id": "G1.1", "file": fp, "s": "FAIL", "r": "empty"})
            continue
        c.append({"id": "G1.1", "file": fp, "s": "PASS"})

        # G1.2 — JSON files parse successfully
        if fp.endswith(".json"):
            try:
                jload(fp)
                c.append({"id": "G1.2", "file": fp, "s": "PASS"})
            except (json.JSONDecodeError, OSError):
                mf.append({"id": "G1.2", "file": fp, "s": "FAIL", "r": "JSON parse error"})

        # G1.3 — YAML frontmatter parses successfully
        if fp.endswith(".md"):
            try:
                fm = yload(fp)
                c.append({"id": "G1.3", "file": fp, "s": "PASS", "has_fm": bool(fm)})
            except Exception:
                mf.append({"id": "G1.3", "file": fp, "s": "FAIL", "r": "YAML parse error"})

        # G1.4 — create .bak for in-place modifying skills (decision via pure helper)
        target_dict = dict(targets)
        if fp in target_dict:
            bak = Path(bak_path(fp))
            if not bak.exists():
                try:
                    safe_write(bak, Path(fp).read_bytes())
                    c.append({"id": "G1.4", "file": fp, "s": "PASS", "r": ".bak created"})
                except OSError:
                    mf.append({"id": "G1.4", "file": fp, "s": "FAIL", "r": "cannot create .bak"})
            else:
                c.append({"id": "G1.4", "file": fp, "s": "PASS", "r": ".bak exists"})
        elif skill_name and skill_name in BACKUP_SKILLS and not rd:
            # Skill is in-place but backups are impossible without round_dir.
            c.append(
                {"id": "G1.4", "file": fp, "s": "SKIP", "r": "no round_dir — cannot create .bak"}
            )
        else:
            c.append({"id": "G1.4", "file": fp, "s": "SKIP", "r": "not in-place skill"})

    # G1.5 — file lock check (round-level .gate-lock file)
    if rd:
        lock_path = rd / ".gate-lock"
        if lock_path.exists():
            age = datetime.now(UTC).timestamp() - lock_path.stat().st_mtime
            if age <= 300:
                mf.append({"id": "G1.5", "s": "FAIL", "r": f"lock active ({age:.0f}s old)"})
            else:
                c.append({"id": "G1.5", "s": "PASS", "r": f"stale lock ({age:.0f}s, >300s)"})
        else:
            c.append({"id": "G1.5", "s": "PASS", "r": "no lock file"})
    else:
        c.append({"id": "G1.5", "s": "SKIP", "r": "no round_dir"})

    # G1.6 — scoring_history check for scorer agent_id
    if rd:
        pp = rd / "progress.json"
        if pp.exists():
            try:
                progress = jload(str(pp))
                scoring_history = progress.get("scoring_history", [])
                if isinstance(scoring_history, list):
                    c.append(
                        {
                            "id": "G1.6",
                            "s": "PASS",
                            "note": f"scoring_history: {len(scoring_history)} entries",
                        }
                    )
                else:
                    c.append({"id": "G1.6", "s": "WARN", "r": "scoring_history not a list"})
            except (json.JSONDecodeError, OSError):
                c.append({"id": "G1.6", "s": "SKIP", "r": "progress.json unreadable"})
        else:
            c.append({"id": "G1.6", "s": "SKIP", "r": "no progress.json"})
    else:
        c.append({"id": "G1.6", "s": "SKIP", "r": "no round_dir"})

    if not fps:
        c.append({"id": "G1.0", "s": "SKIP", "r": "no input files"})

    if mf:
        return fail(
            "G1",
            c,
            "subagent_dispatch",
            [x["id"] + ":" + x.get("file", x.get("r", "")) for x in mf],
        )
    return passed("G1", c)
