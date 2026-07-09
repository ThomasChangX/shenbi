"""G5: phase boundary gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import fnmatch
import json
import re
from pathlib import Path
from typing import Any

from shenbi.contracts import ContractError, load_contract, load_registry
from shenbi.contracts.graph import dag_key
from shenbi.gates.shared import (
    PROJECT,
    TESTS,
    find_report,
    fail,
    jload,
    passed,
)
from shenbi.contracts.thresholds import T2_PASS


def gate_G5(
    phase_name: str | None = None, round_dir: str | None = None, project_dir: str | None = None
) -> str:
    """G5: T2 Phase check."""
    c: list[Any] = []
    mf: list[Any] = []
    try:
        deps = jload(TESTS / "tiers" / "deps.json")
    except (json.JSONDecodeError, OSError, ValueError):
        return fail("G5", [], "scoring", ["G5.0:deps.json unreadable or malformed"])
    phase_data = deps.get("t2-phases", {}).get(phase_name)
    if not phase_data:
        return fail("G5", [], "scoring", [f"unknown phase: {phase_name}"])
    try:
        acceptance = jload(TESTS / "tiers" / "acceptance.json")
    except (json.JSONDecodeError, OSError, ValueError):
        return fail("G5", [], "scoring", ["G5.0:acceptance.json unreadable or malformed"])
    threshold = acceptance.get("t2", T2_PASS)
    prereqs = phase_data.get("prerequisites", [])
    rd = Path(round_dir) if round_dir else None

    # G5.1: prereq T1 scores >= threshold (prefer summary.json, fallback to report file)
    summary_data: dict[str, Any] = {}
    if rd:
        sp = rd / "summary.json"
        if sp.exists():
            try:
                summary_data = jload(str(sp)).get("t1_scores", {})
            except (json.JSONDecodeError, OSError):
                pass
    for pr in prereqs:
        score = 0
        if pr in summary_data:
            score = summary_data[pr].get("generative", 0)
        else:
            report = find_report(rd / "t1-reports", pr, "generative") if rd else None
            if report and report.exists():
                rdata = jload(str(report))
                score = rdata.get("final_score", rdata.get("score", 0))
            elif rd:
                mf.append(f"G5.1:{pr}:no_report")
                continue
        if score < threshold:
            mf.append(f"G5.1:{pr}:score={score}<{threshold}")

    # G5.2: handoff integrity — contract Reads vs upstream Writes+Updates.
    # Glob-aware: compare dag_key() of each path so a parametric read
    # (chapters/chapter-N.md) joins a resolved write (chapters/chapter-5.md) or
    # a declared glob (truth/*.md). Non-blocking WARN — the full closure check
    # lives in Layer C (Task 18); this only compares each skill to its
    # immediately preceding prerequisite in the phase list (adjacent-pairs).
    try:
        g52_registry = load_registry()
    except ContractError:
        g52_registry = None  # fall back to literal matching below
    for i in range(1, len(prereqs)):
        up, down = prereqs[i - 1], prereqs[i]
        try:
            up_c = load_contract(up)
            us_outs = {*up_c["writes"], *up_c["updates"]}
        except ContractError:
            us_outs = set()
        try:
            down_c = load_contract(down)
            ds_ins = set(down_c["reads"])
        except ContractError:
            ds_ins = set()
        if g52_registry is not None:
            up_keys = {dag_key(p, g52_registry) for p in us_outs}
            down_keys = {dag_key(p, g52_registry) for p in ds_ins}
        else:  # registry unavailable — literal string compare (old behavior)
            up_keys = us_outs
            down_keys = ds_ins
        missing = down_keys - up_keys
        if missing:
            c.append(
                {
                    "id": "G5.2",
                    "pair": f"{up}->{down}",
                    "s": "WARN",
                    "missing": sorted(missing),
                }
            )

    # G5.3: cross-skill conflict detection (char roles, numerics, terminology)
    if project_dir:
        pd5 = Path(project_dir)
        conflicts: list[Any] = []

        # A. Character name/role conflicts — same name, different role across files
        char_dir = pd5 / "characters"
        if char_dir.exists():
            char_data: dict[str, list[tuple[str, str]]] = {}  # name -> [(file, role)]
            for cf in char_dir.rglob("*.md"):
                try:
                    ct = cf.read_text(encoding="utf-8")
                    nms = re.findall(r"^name:\s*(\S+)", ct, re.MULTILINE)
                    rms = re.findall(r"^role:\s*(\S+)", ct, re.MULTILINE)
                    for nm in nms:
                        if nm not in char_data:
                            char_data[nm] = []
                        role_val = rms[0] if rms else "unknown"
                        char_data[nm].append((cf.name, role_val))
                except Exception:
                    pass
            for name, entries in char_data.items():
                if len(entries) > 1:
                    roles = set(r for _, r in entries)
                    if len(roles) > 1:
                        conflicts.append(f"char_role_conflict:{name}:roles={list(roles)}")

        # B. Numeric consistency — compare numbers with units across output files
        world_dir = pd5 / "world"
        output_files: list[Path] = []
        if world_dir.exists():
            output_files.extend(world_dir.rglob("*.md"))
        # also scan outline files
        outline_dir = pd5 / "outline"
        if outline_dir.exists():
            output_files.extend(list(outline_dir.rglob("*.md"))[:3])
        numeric_registry: dict[
            str, list[tuple[str, int]]
        ] = {}  # canonical_key -> set of (file, value)
        num_pat = re.compile(r"(\d+)\s*(?:个|种|人|章|次|处|条|名|位|倍|%|万|千|百)")
        for wf in output_files[:8]:  # cap at 8 files for speed
            try:
                ct = wf.read_text(encoding="utf-8")[:5000]
                for m in num_pat.finditer(ct):
                    val = int(m.group(1))
                    unit = m.group(2)
                    # extract nearby context as concept key (up to 20 chars before number)
                    start = max(0, m.start() - 20)
                    ctx = ct[start : m.start()]
                    # normalize to a short key
                    key_words = re.findall(r"[一-鿿]{2,}", ctx)
                    ckey = "_".join(key_words[-2:]) if key_words else f"ctx_{abs(hash(ctx)) % 1000}"
                    ckey = f"{ckey}_{unit}"
                    if ckey not in numeric_registry:
                        numeric_registry[ckey] = [(wf.name, val)]
                    else:
                        numeric_registry[ckey].append((wf.name, val))
            except Exception:
                pass
        for key, num_entries in numeric_registry.items():
            unique = {v for _, v in num_entries}
            if len(unique) > 1 and len(num_entries) >= 2:
                conflicts.append(f"numeric:{key}:{dict(num_entries)}")

        # C. Terminology consistency — mixed term variants
        term_pairs = [
            ("灵能", "灵力"),
            ("位面", "次元"),
            ("伏笔", "伏线"),
            ("庶民", "平民"),
            ("庶民", "百姓"),
            ("穿越者", "穿越客"),
        ]
        if char_dir and char_dir.exists():
            sample_text = ""
            for cf in list(char_dir.rglob("*.md"))[:6]:
                try:
                    sample_text += cf.read_text(encoding="utf-8")[:3000]
                except Exception:
                    pass
            for t1, t2 in term_pairs:
                c1 = len(re.findall(t1, sample_text))
                c2 = len(re.findall(t2, sample_text))
                if c1 > 0 and c2 > 0 and c1 + c2 > 3:
                    conflicts.append(f"term_mix:{t1}({c1})/{t2}({c2})")

        if conflicts:
            mf.extend([f"G5.3:{x}" for x in conflicts[:10]])
        else:
            c.append({"id": "G5.3", "s": "PASS", "note": "no cross-skill conflicts detected"})
    else:
        c.append({"id": "G5.3", "s": "SKIP", "r": "need project_dir for this check"})

    # G5.4: expected outputs
    for pattern in phase_data.get("expected_outputs", []):
        if "*" in pattern:
            pd = Path(project_dir) if project_dir else PROJECT
            matches = list(pd.rglob(pattern))
            if not matches:
                mf.append(f"G5.4:{pattern}:no_matches")
            else:
                c.append({"id": "G5.4", "pattern": pattern, "s": "PASS", "matches": len(matches)})
        elif project_dir:
            p = Path(project_dir) / pattern
            if not p.exists():
                mf.append(f"G5.4:{pattern}:not_found")
            else:
                c.append({"id": "G5.4", "pattern": pattern, "s": "PASS"})

    # G5.5 checker → file pattern mapping (each checker only validates semantically relevant files)
    G5_CHECKER_GLOBS = {
        "shenbi-worldbuilding": ["novel.json", "genre-config.json", "world/*.md", "truth/*.md"],
        "shenbi-power-system": ["world/power_system.md"],
        "shenbi-faction-builder": ["world/factions.md", "world/faction-relations.md"],
        "shenbi-location-builder": ["world/locations.md"],
        "shenbi-character-design": ["characters/*.md", "characters/**/*.md"],
        "shenbi-relationship-map": ["characters/relationships.md", "truth/character_matrix.md"],
        "shenbi-story-architecture": [
            "outline/story_frame.md",
            "outline/volume_map.md",
            "outline/rhythm_principles.md",
        ],
        "shenbi-volume-outlining": ["outline/volume_map.md"],
        "shenbi-genre-config": ["genre-config.json"],
        "shenbi-pacing-design": ["outline/rhythm_principles.md"],
        "shenbi-plot-thread-weaver": ["outline/thread_map.md"],
        "shenbi-chapter-planning": ["plans/*.md"],
        "shenbi-chapter-drafting": ["chapters/*.md"],
        "shenbi-foreshadowing-plant": ["truth/pending_hooks.md"],
        "shenbi-foreshadowing-track": ["truth/pending_hooks.md"],
        "shenbi-context-composing": ["context/*.md"],
        "shenbi-state-settling": ["truth/*.md"],
        "shenbi-style-polishing": ["chapters/*.md"],
        "shenbi-anti-detect": ["chapters/*.md"],
        "shenbi-length-normalizing": ["chapters/*.md"],
    }

    def _g5_file_matches_glob(file_path: str, project_dir: str, patterns: list[str]) -> bool:
        """Check if file_path (relative to project_dir) matches any of the given glob patterns."""
        try:
            rel = Path(file_path).relative_to(project_dir)
            rel_str = str(rel)
            return any(fnmatch.fnmatch(rel_str, p) for p in patterns)
        except ValueError:
            return False

    # G5.5: No regression — re-run G4 checks for each prerequisite skill on phase outputs
    phase_outputs = phase_data.get("expected_outputs", [])
    if phase_outputs and project_dir:
        pd = Path(project_dir)
        for pattern in phase_outputs:
            if "*" in pattern:
                for fp in pd.rglob(pattern):
                    if fp.suffix == ".md":
                        # Run G4 check for every prerequisite skill on each output file
                        for pr in prereqs:
                            # Only run checker if file matches its applicable globs
                            globs = G5_CHECKER_GLOBS.get(pr, ["*.md"])
                            if not _g5_file_matches_glob(str(fp), str(pd), globs):
                                continue
                            try:
                                from shenbi.gates.g4 import gate_G4

                                g4_raw = gate_G4(
                                    pr,
                                    "generative",
                                    [str(fp)],
                                    str(project_dir),
                                    project_dir=str(project_dir),
                                    repo_root=str(PROJECT),
                                )
                                g4_data = json.loads(g4_raw)
                                if g4_data.get("status") == "FAIL":
                                    mf.append(f"G5.5:{fp.name}:G4_fail:{pr}")
                            except Exception:
                                c.append(
                                    {
                                        "id": "G5.5",
                                        "file": str(fp),
                                        "s": "WARN",
                                        "r": f"G4-{pr} check unavailable",
                                    }
                                )
        if not any(x.startswith("G5.5:") for x in mf):
            c.append({"id": "G5.5", "s": "PASS", "note": "G4 regression check on outputs"})
    else:
        c.append({"id": "G5.5", "s": "SKIP", "r": "no phase outputs defined"})

    if mf:
        return fail("G5", c, "scoring", mf)
    return passed("G5", c)
