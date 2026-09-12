#!/usr/bin/env python3
"""Registry reconciliation lint (spec #60 C22): R1 closure + R2 word list + R3 hashes + R5 globs.

R1 invariants (per-face, bidirectional where stated):
  master.json      == live skill set  AND  master ∩ DEPRECATED = ∅  AND no ghosts
  SHORT_MAP        ⊇ checker-having skills (30)
  G5_CHECKER_GLOBS ⊇ checker-having ∧ t2-prereq skills
  G4_CHECKER_SKILLS == checker keys (30)
  docs/skills/index.md ⊇ live skills (existence)
  t2 seed files    ⊇ per-phase prerequisites (literal token)
  AGENTS.md counts == disk when numeric claims present (transitional face; vacuous
                     once de-numericized — spec acceptance 4 / C23 domain)
  using-shenbi trigger table ⊇ functional live - allow-missing (meta pre-exempted)

R2 invariants (word-list closure):
  every parametric concept (name carries N/NNN/<dim>/SECTION placeholder) is
  glob-resolvable — via its ``patterns:`` entry OR a declared ``globs:`` entry
  (either-or; plan r5 ruling after the yaml's 5-placeholder reality);
  truth-files.index.json concept keys ⊆ yaml concepts (registration closure —
  F1106/F1152 class); hardcoded ``truth/…`` literals in src/shenbi are WARN-only
  when absent from the word list.

R3 invariant: deps.json ``_tool_hashes`` entries are fresh (sha256 envelope per
tests/lock-tool-hashes.sh; entries whose target file is absent from the linted
tree are skipped — temp-copy semantics, plan r3 I3).

R5 invariant: within a t2 phase, no checker glob pattern's file set strictly
contains another same-phase checker's specialized glob (equal patterns and
literal-contained patterns are exempt — plan r2/r3 rulings). The broad-glob-
over-specialized-suffix shape (audits/volume-*.md ⊃ audits/volume-*-score.md)
is the F432 cross-checker false-FAIL carrier.

Reading mechanisms: importable faces go through a temp-src sys.path injection
(SHORT_MAP via cli.py, stdlib-only module level); non-importable faces
(g5/generic/shared/registry/AGENTS/yaml) are read by AST/text parsing so the
lint works on temp repo copies (plan r2 I4 ruling).

Output: one violation line per finding, format ``[Rn] table: direction: entry``.
Exit 1 on any FAIL-level violation. WARN-level notes go to stderr, don't count.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import cast

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from shenbi.skill_utils.deprecated import deprecated_skill_names  # noqa: E402

_META_SKILLS = frozenset({"using-shenbi", "shenbi-writing-skills"})

_WARN: list[str] = []


# ---------------------------------------------------------------- helpers --


def _literal_str_set(source: str, assign_target: str) -> set[str]:
    """Extract string members from ``target = frozenset({...})`` / ``{...}``."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == assign_target for t in node.targets
        ):
            inner = node.value
            if isinstance(inner, ast.Call):  # frozenset({...})
                inner = inner.args[0] if inner.args else None
            if isinstance(inner, (ast.Set, ast.List, ast.Tuple)):
                return {
                    el.value
                    for el in inner.elts
                    if isinstance(el, ast.Constant) and isinstance(el.value, str)
                }
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == assign_target
            and isinstance(node.value, (ast.Dict, ast.Call))
        ):
            inner = node.value
            if isinstance(inner, ast.Call):
                inner = inner.args[0] if inner.args else None
            if isinstance(inner, ast.Dict):
                return {
                    k.value
                    for k in inner.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                }
            if isinstance(inner, (ast.Set, ast.List, ast.Tuple)):
                return {
                    el.value
                    for el in inner.elts
                    if isinstance(el, ast.Constant) and isinstance(el.value, str)
                }
    return set()


def _short_map_keys(repo: Path) -> set[str] | None:
    """SHORT_MAP values via AST extraction of the repo's own cli.py.

    AST (not import): importing a temp-copy cli.py would register the copy's
    module lines in pytest-cov and tank the coverage gate (spec60 execution
    finding); the map is a pure string-literal dict, so AST is exact.
    """
    cli = repo / "src" / "shenbi" / "gates" / "cli.py"
    if not cli.exists():
        return None
    try:
        tree = ast.parse(cli.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(tg, ast.Name) and tg.id == "SHORT_MAP" for tg in node.targets)
            and isinstance(node.value, ast.Dict)
        ):
            return {
                v.value
                for v in node.value.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            }
    return None


def _checker_keys(repo: Path) -> set[str]:
    """G4_CHECKER_KEYS from generic.py (AST; includes the 3 dynamic score keys)."""
    generic = repo / "src" / "shenbi" / "gates" / "g4" / "generic.py"
    if not generic.exists():
        return set()
    keys = _literal_str_set(generic.read_text(encoding="utf-8"), "G4_CHECKER_KEYS")
    if keys:
        return keys
    # Fallback: static dict keys + score family from scoring_sections.py
    static = _literal_str_set(generic.read_text(encoding="utf-8"), "checkers")
    scoring = repo / "src" / "shenbi" / "gates" / "g4" / "scoring_sections.py"
    if scoring.exists():
        stext = scoring.read_text(encoding="utf-8")
        static |= set(re.findall(r'"(shenbi-score-[a-z-]+)"', stext))
    return static


def _g5_checker_globs(repo: Path) -> dict[str, list[str]]:
    g5 = repo / "src" / "shenbi" / "gates" / "g5.py"
    if not g5.exists():
        return {}
    src = g5.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "G5_CHECKER_GLOBS"
        ):
            if isinstance(node.value, ast.Dict):
                try:
                    return ast.literal_eval(node.value)
                except Exception:  # noqa: BLE001
                    return {}
            return {}
    return {}


def _deps(repo: Path) -> dict[str, object]:
    deps = repo / "tests" / "tiers" / "deps.json"
    if not deps.exists():
        return {}
    data: dict[str, object] = json.loads(deps.read_text(encoding="utf-8"))
    return data


def _t2_prereqs(deps: dict[str, object]) -> set[str]:
    prereqs: set[str] = set()
    phases = cast(dict[str, dict[str, object]], deps.get("t2-phases", {}))
    for info in phases.values():
        for s in cast(list[str], info.get("prerequisites", [])):
            if s.startswith("shenbi-"):
                prereqs.add(s)
    return prereqs


# ------------------------------------------------------------- R1 faces --


def _face_master(repo: Path, live: set[str], all_dirs: set[str], dead: frozenset[str]) -> list[str]:
    """master.json == live ∧ ∩ DEPRECATED = ∅ ∧ no ghosts ∧ version == pyproject."""
    errs: list[str] = []
    master_path = repo / "plugins" / "master.json"
    if not master_path.exists():
        return errs
    m = json.loads(master_path.read_text(encoding="utf-8"))
    entries = {Path(e).parent.name for e in m.get("skills", []) if isinstance(e, str)}
    if dead & entries:
        errs.append(f"[R1] master.json: routes-DEPRECATED: {sorted(dead & entries)}")
    missing = sorted(live - entries)
    if missing:
        errs.append(f"[R1] master.json: missing-live: {missing}")
    ghosts = sorted(entries - all_dirs)
    if ghosts:
        errs.append(f"[R1] master.json: ghost-entries: {ghosts}")
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        ptext = pyproject.read_text(encoding="utf-8")
        pm = re.search(r'^version\s*=\s*"([^"]+)"', ptext, re.M)
        if pm and m.get("version") not in (None, pm.group(1)):
            errs.append(
                f"[R1] master.json: version-drift: master={m.get('version')}"
                f" pyproject={pm.group(1)}"
            )
    return errs


def _face_short_map(repo: Path, checkers: set[str]) -> list[str]:
    """SHORT_MAP ⊇ checker-having skills."""
    short_map = _short_map_keys(repo)
    if short_map is None:
        _WARN.append("[R1] SHORT_MAP: unreadable (cli.py import failed)")
        return []
    gap = sorted(checkers - short_map)
    return [f"[R1] SHORT_MAP: missing-checkers: {gap}"] if gap else []


def _face_g5_globs(repo: Path, checkers: set[str]) -> list[str]:
    """G5_CHECKER_GLOBS ⊇ checker-having ∧ t2-prereq skills."""
    prereqs = _t2_prereqs(_deps(repo))
    globs = _g5_checker_globs(repo)
    gap = sorted((checkers & prereqs) - set(globs))
    return [f"[R1] G5_CHECKER_GLOBS: missing-checker-prereqs: {gap}"] if gap else []


def _face_g4_checker_skills(repo: Path, checkers: set[str]) -> list[str]:
    """G4_CHECKER_SKILLS == checker keys."""
    shared = repo / "src" / "shenbi" / "gates" / "shared.py"
    if not shared.exists():
        return []
    g4cs = _literal_str_set(shared.read_text(encoding="utf-8"), "G4_CHECKER_SKILLS")
    if g4cs == checkers:
        return []
    return [
        f"[R1] G4_CHECKER_SKILLS: !=checkers: only-in-shared={sorted(g4cs - checkers)} "
        f"missing-from-shared={sorted(checkers - g4cs)}"
    ]


def _face_index_md(repo: Path, live: set[str]) -> list[str]:
    """docs/skills/index.md ⊇ live skills (existence)."""
    index_md = repo / "docs" / "skills" / "index.md"
    if not index_md.exists():
        return []
    text = index_md.read_text(encoding="utf-8")
    missing = sorted(s for s in live if s not in text)
    return [f"[R1] docs/skills/index.md: missing-live: {missing}"] if missing else []


def _face_t2_seeds(repo: Path) -> list[str]:
    """t2 seed ⊇ per-phase prerequisites (literal token; absent seeds skipped)."""
    errs: list[str] = []
    phases = cast(dict[str, dict[str, object]], _deps(repo).get("t2-phases", {}))
    for phase, info in phases.items():
        seed = repo / "tests" / "tiers" / "t2-phase" / phase / "input" / "seed.md"
        if not seed.exists():
            continue
        stext = seed.read_text(encoding="utf-8")
        phase_prereqs = [
            s for s in cast(list[str], info.get("prerequisites", [])) if s.startswith("shenbi-")
        ]
        gap = [s for s in phase_prereqs if s not in stext]
        if gap:
            errs.append(f"[R1] t2-seed[{phase}]: missing-prereqs: {gap}")
    return errs


def _face_agents_counts(repo: Path, all_dirs: set[str]) -> list[str]:
    """AGENTS.md numeric skill counts (transitional; vacuous once de-numericized)."""
    agents = repo / "AGENTS.md"
    if not agents.exists():
        return []
    atext = agents.read_text(encoding="utf-8")
    for n in re.findall(r"(\d+)\s+(?:functional|meta|skills|total)", atext):
        if int(n) != len(all_dirs):
            return [f"[R1] AGENTS.md: count-drift: claims={n} disk={len(all_dirs)}"]
    return []


def _face_trigger_table(repo: Path, live: set[str], allow_missing: frozenset[str]) -> list[str]:
    """using-shenbi trigger table ⊇ functional live - allow_missing (meta exempt)."""
    table = repo / "skills" / "using-shenbi" / "SKILL.md"
    if not table.exists():
        return []
    ttext = table.read_text(encoding="utf-8")
    expected = sorted(s for s in (live - _META_SKILLS - allow_missing) if s.startswith("shenbi-"))
    gap = [s for s in expected if s not in ttext]
    return [f"[R1] using-shenbi: unmentioned-functional-live: {gap}"] if gap else []


def _face_deps_dead(repo: Path, dead: frozenset[str]) -> list[str]:
    """DEPRECATED skills must not be registered in deps.json (C21 forbid-register)."""
    deps_names = _collect_deps_names(_deps(repo))
    if dead & deps_names:
        return [f"[R1] deps.json: routes-DEPRECATED: {sorted(dead & deps_names)}"]
    return []


def _r1_skill_closure(repo: Path, allow_missing: frozenset[str]) -> list[str]:
    skills_dir = repo / "skills"
    all_dirs = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    dead = deprecated_skill_names(skills_dir)
    live = all_dirs - dead
    checkers = _checker_keys(repo)
    errs: list[str] = []
    errs += _face_master(repo, live, all_dirs, dead)
    errs += _face_short_map(repo, checkers)
    errs += _face_g5_globs(repo, checkers)
    errs += _face_g4_checker_skills(repo, checkers)
    errs += _face_index_md(repo, live)
    errs += _face_t2_seeds(repo)
    errs += _face_agents_counts(repo, all_dirs)
    errs += _face_trigger_table(repo, live, allow_missing)
    errs += _face_deps_dead(repo, dead)
    return errs


def _collect_deps_names(node: object) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        for v in node.values():
            names |= _collect_deps_names(v)
    elif isinstance(node, list):
        for v in node:
            if isinstance(v, str) and v.startswith("shenbi-"):
                names.add(v)
            else:
                names |= _collect_deps_names(v)
    return names


# ------------------------------------------------------------- R2 faces --


def _load_yaml_registry(repo: Path) -> dict[str, list[dict[str, str]]] | None:
    """Parse truth-files.yaml into {concepts, patterns, globs} string dicts."""
    yaml_path = repo / "docs" / "framework" / "truth-files.yaml"
    if not yaml_path.exists():
        return None
    try:
        import yaml  # noqa: PLC0415 (deferred: keep lint startup cheap)
    except ImportError:
        return None
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    out: dict[str, list[dict[str, str]]] = {}
    for section in ("concepts", "patterns", "globs"):
        entries = data.get(section) or []
        out[section] = [{k: str(v) for k, v in e.items() if isinstance(v, str)} for e in entries]
    return out


_PARAMETRIC_RE = re.compile(r"N(?![A-Za-z0-9])|NNN(?![A-Za-z0-9])|<dim>|SECTION")


def _is_parametric(name: str) -> bool:
    """Parametric = carries an N/NNN/<dim>/SECTION placeholder (spec R2 note)."""
    return bool(_PARAMETRIC_RE.search(name))


def _r2_unregistered_index_keys(
    repo: Path,
    concept_set: set[str],
    pattern_parametrics: set[str],
    pattern_globs: set[str],
    glob_patterns: list[str],
) -> list[str]:
    """index.json keys not registered in any yaml form (F1106/F1152 closure).

    Glob-shaped keys (with *) must equal a declared pattern/glob; concrete keys
    must be concept-registered OR an instance of a registered parametric (a
    broad declared glob covering a concrete file is NOT registration — F1152).
    """
    index_json = repo / "docs" / "framework" / "truth-files.index.json"
    if not index_json.exists():
        return []
    idx = json.loads(index_json.read_text(encoding="utf-8"))
    parametric_as_globs = [
        c.replace("NNN", "*").replace("N", "*").replace("<dim>", "*")
        for c in (concept_set | pattern_parametrics)
    ]
    unregistered: list[str] = []
    for k in idx:
        if "*" in k:
            ok = k in pattern_globs or k in set(glob_patterns)
        else:
            ok = (
                k in concept_set
                or k in pattern_parametrics
                or any(fnmatch(k, pg) for pg in parametric_as_globs)
            )
        if not ok:
            unregistered.append(k)
    return sorted(unregistered)


def _r2_word_list(repo: Path) -> list[str]:
    errs: list[str] = []
    reg = _load_yaml_registry(repo)
    if reg is None:
        _WARN.append("[R2] truth-files.yaml: unreadable (missing or yaml unavailable)")
        return errs
    concepts = [c.get("name", "") for c in reg["concepts"]]
    concept_set = set(concepts)
    pattern_parametrics = {p.get("parametric", "") for p in reg["patterns"]}
    pattern_globs = {p.get("glob", "") for p in reg["patterns"]}
    glob_patterns = [g.get("pattern", "") for g in reg["globs"]]

    # parametric concepts must be glob-resolvable (patterns OR globs — either-or)
    for name in concepts:
        if not _is_parametric(name):
            continue
        if name in pattern_parametrics:
            continue
        if any(fnmatch(name, g) for g in glob_patterns):
            continue
        errs.append(f"[R2] truth-files.yaml: parametric-unresolvable: {name}")

    unregistered = _r2_unregistered_index_keys(
        repo, concept_set, pattern_parametrics, pattern_globs, glob_patterns
    )
    if unregistered:
        errs.append(f"[R2] truth-files.index.json: not-in-yaml: {unregistered}")

    _r2_orphan_warn(repo, reg["concepts"])

    # hardcoded truth/ literals in src not in the word list -> WARN only
    src_dir = repo / "src" / "shenbi"
    if src_dir.exists():
        known = concept_set | set(glob_patterns) | set(pattern_parametrics)
        seen: set[str] = set()
        literal_re = re.compile(r"[\"']((?:truth|audits|context)/[a-z0-9_*./-]+)[\"']")
        for py in src_dir.rglob("*.py"):
            for m in literal_re.finditer(py.read_text(encoding="utf-8")):
                lit = m.group(1)
                if lit not in seen and lit not in known:
                    seen.add(lit)
        # WARN-only face: noise-prone (dynamic paths); never FAILs
        _WARN.extend(f"[R2] src-literal-unregistered: {lit}" for lit in sorted(seen)[:20])
    return errs


def _r2_orphan_warn(repo: Path, concepts: list[dict[str, str]]) -> None:
    """Orphan concepts (F888/F823): absent from index.json keys entirely.

    index.json maps concept -> {reads/writes/updates: [skill names]}, so its
    KEY set is exactly the concepts with a producer or consumer. WARN only;
    producer: pipeline/shared concepts are infrastructure outputs and exempt.
    """
    index_json = repo / "docs" / "framework" / "truth-files.index.json"
    if not index_json.exists():
        return
    idx_keys = set(json.loads(index_json.read_text(encoding="utf-8")))
    for c in concepts:
        name = c.get("name", "")
        if c.get("producer") in ("pipeline", "shared") or not name:
            continue
        if name in idx_keys:
            continue
        # index keys are normalized globs; match the concept against them
        # either way, treating N/NNN/<dim> placeholders as wildcards
        name_as_glob = name.replace("NNN", "*").replace("N", "*").replace("<dim>", "*")
        if any(fnmatch(name, k) or fnmatch(k, name_as_glob) for k in idx_keys):
            continue
        _WARN.append(f"[R2] orphan-concept: {name}")


# ------------------------------------------------------------- R3 face --


def _r3_hash_freshness(repo: Path) -> list[str]:
    """_tool_hashes entries fresh (sha256 envelope; absent targets skipped)."""
    deps = _deps(repo)
    hashes = deps.get("_tool_hashes")
    if not isinstance(hashes, dict):
        return []
    errs: list[str] = []
    stale: list[str] = []
    for rel, expected in hashes.items():
        target = repo / str(rel)
        if not target.exists():
            continue  # temp-copy semantics (plan r3 I3)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if expected != f"sha256:{digest}":
            stale.append(str(rel))
    if stale:
        errs.append(f"[R3] _tool_hashes: stale[{len(stale)}]: {stale[:10]}")
    return errs


# -------------------------------------------------------------- R5 face --


def _instantiate(pattern: str, tag: str) -> str:
    """Replace each wildcard run with a distinct marker token."""
    parts = pattern.split("*")
    return "".join(part if k == 0 else f"{tag}{k}{part}" for k, part in enumerate(parts))


def _r5_glob_validity(repo: Path) -> list[str]:
    """Same-phase strict-containment among wildcard globs (F432 carrier)."""
    errs: list[str] = []
    deps = _deps(repo)
    globs = _g5_checker_globs(repo)
    checkers = _checker_keys(repo)
    phases = cast(dict[str, dict[str, object]], deps.get("t2-phases", {}))
    for phase, info in phases.items():
        plist = cast(list[str], info.get("prerequisites", []))
        phase_checkers = [s for s in plist if s in checkers and s in globs]
        for a in phase_checkers:
            for b in phase_checkers:
                if a == b:
                    continue
                for pa in globs[a]:
                    for pb in globs[b]:
                        if "*" not in pa or "*" not in pb or pa == pb:
                            continue  # literal pairs / equal strings exempt
                        # pb's domain strictly inside pa's? instantiate pb's
                        # wildcards with markers and check pa matches them all.
                        inst = _instantiate(pb, "wqz")
                        if fnmatch(inst, pa):
                            errs.append(
                                f"[R5] G5_CHECKER_GLOBS[{phase}]: strict-containment: "
                                f"{pa} ({a}) strictly contains {pb} ({b})"
                            )
    return errs


# ----------------------------------------------------------------- main --


def lint_registry_reconcile(repo: Path, allow_missing: frozenset[str] = frozenset()) -> list[str]:
    """Run all reconciliation faces; return FAIL-level violation lines."""
    _WARN.clear()
    errs: list[str] = []
    errs += _r1_skill_closure(repo, allow_missing)
    errs += _r2_word_list(repo)
    errs += _r3_hash_freshness(repo)
    errs += _r5_glob_validity(repo)
    return errs


def main() -> int:
    """CLI entry: print violations, exit 1 on any FAIL-level finding."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=_REPO_ROOT)
    parser.add_argument(
        "--allow-missing",
        default="",
        help="comma-separated skills exempt from the using-shenbi trigger-table face",
    )
    args = parser.parse_args()
    allow = frozenset(s for s in args.allow_missing.split(",") if s)
    vios = lint_registry_reconcile(args.repo, allow)
    for v in vios:
        print(v)
    for w in _WARN:
        print(f"WARN {w}", file=sys.stderr)
    print(f"{'0' if not vios else len(vios)} violations", file=sys.stderr)
    return 1 if vios else 0


if __name__ == "__main__":
    sys.exit(main())
