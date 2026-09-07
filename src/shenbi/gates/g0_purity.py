"""Scenario path purity checks for G0.

Extracted from g0.py to keep file length under 500 lines. These checks
verify that test scenarios reference only tests/fixtures/ paths, not
project-relative paths.
"""

from shenbi.status import GateStatus

import json
import re
from pathlib import Path
from typing import Any

# spec #54 C16 (T0): provenance tri-state literals — single definition point.
PROVENANCE_STATES: frozenset[str] = frozenset({"real-output", "upstream-copy", "synthetic-sample"})
# Whitelist exempts the "real output role" requirement, never the annotation
# itself; entries must exist at merge time (no vacant slots).
PROVENANCE_WHITELIST: frozenset[str] = frozenset({"tests/fixtures/report-example.txt"})
# Staged WARN→FAIL rollout: waves flip to "fail" only after live re-scan
# count reaches zero (spec T0). Promotion is judged by live scan, never by
# reading the static baseline.
ENFORCEMENT_WAVES: dict[str, str] = {"P0": "fail", "P1": "fail", "P2": "fail"}

_CARRIER_SUFFIX = ".provenance.json"
_BASELINE_NAME = "provenance-baseline.json"
_FIXTURE_REF_RE = re.compile(r"tests/fixtures/[\w\-/]+(?:\.\w+)?")


def _iter_scenarios(
    t1_skill_dir: Path,
) -> list[tuple[str, str, Path, str]]:
    """All (skill, test_type, scenario, content) triples under t1_skill_dir.

    Unlike the legacy purity scans, ``_``-prefixed dirs (``_template``) are
    IN scope — F751's planted-defect breakage lives in the template scenarios.
    """
    out: list[tuple[str, str, Path, str]] = []
    if not t1_skill_dir.exists():
        return out
    for skill_dir in sorted(t1_skill_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        for test_type in ("generative", "bug-hunt", "clean"):
            scenario = skill_dir / test_type / "input" / "scenario.md"
            if not scenario.exists():
                continue
            try:
                content = scenario.read_text(encoding="utf-8")
            except Exception:
                continue
            out.append((skill_dir.name, test_type, scenario, content))
    return out


def _consumed_fixtures(t1_skill_dir: Path) -> dict[str, list[str]]:
    """Map fixture rel-path → consuming scenario labels (dedup)."""
    consumed: dict[str, list[str]] = {}
    for skill, test_type, _sc, content in _iter_scenarios(t1_skill_dir):
        for ref in set(_FIXTURE_REF_RE.findall(content)):
            consumed.setdefault(ref, []).append(f"{skill}/{test_type}")
    return consumed


def load_provenance(fixture_path: Path) -> str | None:
    """Resolve a fixture's provenance state, or None if missing/illegal.

    Carriers: ``.md`` YAML frontmatter ``provenance:`` field; anything else
    reads the sibling ``<name>.provenance.json`` sidecar. A value outside
    PROVENANCE_STATES (including self-exemption notes) returns None so the
    caller counts it as a violation.
    """
    try:
        if fixture_path.suffix == ".md":
            text = fixture_path.read_text(encoding="utf-8")
            m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
            if not m:
                return None
            pm = re.search(r"^provenance:\s*(\S+)\s*$", m.group(1), re.MULTILINE)
            if not pm:
                return None
            value = pm.group(1).strip("\"'")
        else:
            sidecar = fixture_path.parent / (fixture_path.name + ".provenance.json")
            if not sidecar.exists():
                return None
            value = str(json.loads(sidecar.read_text(encoding="utf-8"))["provenance"])
    except Exception:
        return None
    return value if value in PROVENANCE_STATES else None


def _wave_status(wave: str, violations: int) -> GateStatus:
    if violations == 0:
        return GateStatus.PASS
    return GateStatus.FAIL if ENFORCEMENT_WAVES[wave] == "fail" else GateStatus.WARN


def baseline_delta_note(check_id: str, current_violations: list[str]) -> str | None:
    """Read-only new-since-baseline delta for reporting (spec T0).

    The baseline never drives WARN/FAIL judgement (that is live-scan only);
    a missing baseline file yields None ("no baseline") and never errors.
    """
    baseline_path = Path(__file__).resolve().parents[3] / "tests/fixtures/provenance-baseline.json"
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "no baseline"
    known = baseline.get("violations", {}).get(check_id, [])
    new = [v for v in current_violations if not any(v in tok for tok in known)]
    return f"new-since-baseline: +{len(new)}" if new else "no new violations since baseline"


def check_scenario_reference_closure(
    t1_skill_dir: Path, project_root: Path
) -> list[dict[str, Any]]:
    """G0.17: every scenario-referenced tests/fixtures/ path must resolve.

    A populated directory is a legitimate scope pointer; an EMPTY directory
    referenced as if content exists is the F789 violation, same class as a
    missing path.
    """
    missing: dict[str, list[str]] = {}
    for ref, consumers in _consumed_fixtures(t1_skill_dir).items():
        p = project_root / ref
        populated = p.is_dir() and any(ch for ch in p.iterdir() if ch.name != ".gitkeep")
        ok = p.is_file() or populated
        if not ok:
            missing.setdefault(ref, []).extend(consumers[:3])
    violations = len(missing)
    if violations:
        detail = "; ".join(f"{r} (needed by: {', '.join(c)})" for r, c in sorted(missing.items()))
        status = _wave_status("P0", violations)
        return [
            {
                "id": "G0.17",
                "s": status,
                "r": f"{violations} referenced fixtures missing: {detail}",
                "note": baseline_delta_note("G0.17", sorted(missing)),
                "violations": sorted(missing),
            }
        ]
    return [{"id": "G0.17", "s": GateStatus.PASS, "note": "all referenced fixtures exist"}]


def check_fixture_provenance(t1_skill_dir: Path, fixtures_dir: Path) -> list[dict[str, Any]]:
    """G0.18: consumed fixtures carry a legal tri-state provenance carrier.

    Whitelist entries waive the real-output ROLE requirement but never the
    annotation itself (spec T0): a whitelisted fixture without a legal
    carrier is still a violation.
    """
    offenders: list[str] = []
    for ref in _consumed_fixtures(t1_skill_dir):
        fixture_path = fixtures_dir / ref.removeprefix("tests/fixtures/")
        if not fixture_path.is_file():
            continue  # existence is G0.17's wave
        if load_provenance(fixture_path) is None:
            offenders.append(ref)
    violations = len(offenders)
    if violations:
        status = _wave_status("P1", violations)
        return [
            {
                "id": "G0.18",
                "s": status,
                "r": f"{violations} consumed fixtures lack legal provenance: "
                f"{'; '.join(sorted(offenders)[:10])}"
                f"{'...' if violations > 10 else ''}",
                "note": baseline_delta_note("G0.18", sorted(offenders)),
                "violations": sorted(offenders),
            }
        ]
    return [{"id": "G0.18", "s": GateStatus.PASS, "note": "all consumed fixtures carry provenance"}]


def _stem_segments(name: str) -> tuple[str, ...]:
    return tuple(name.rsplit(".", 1)[0].split("-"))


def check_variant_bypass(t1_skill_dir: Path, fixtures_dir: Path) -> list[dict[str, Any]]:
    """G0.19: unreferenced variant-sibling files are not exempt from provenance.

    Variant criterion (fixed): shares the first two ``-`` stem segments with
    any scenario-referenced fixture (e.g. ``foo-example`` vs
    ``foo-example-variant``). Carrier files are never scan targets.
    """
    consumed = _consumed_fixtures(t1_skill_dir)
    referenced = {_stem_segments(ref.rsplit("/", 1)[-1])[:2] for ref in consumed}
    offenders: list[str] = []
    if fixtures_dir.exists():
        for p in sorted(fixtures_dir.rglob("*")):
            if not p.is_file():
                continue
            if p.name.endswith(_CARRIER_SUFFIX) or p.name == _BASELINE_NAME or p.name == ".gitkeep":
                continue
            rel = "tests/fixtures/" + p.relative_to(fixtures_dir).as_posix()
            if rel in consumed or rel in PROVENANCE_WHITELIST:
                continue
            if _stem_segments(p.name)[:2] in referenced and load_provenance(p) is None:
                offenders.append(rel)
    violations = len(offenders)
    if violations:
        status = _wave_status("P2", violations)
        return [
            {
                "id": "G0.19",
                "s": status,
                "r": f"{violations} unreferenced variant files lack provenance: "
                f"{'; '.join(sorted(offenders)[:10])}"
                f"{'...' if violations > 10 else ''}",
                "note": baseline_delta_note("G0.19", sorted(offenders)),
                "violations": sorted(offenders),
            }
        ]
    return [{"id": "G0.19", "s": GateStatus.PASS, "note": "variant bypass files annotated"}]


def check_scenario_file_purity(
    t1_skill_dir: Path,
) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """G0.9: scenario file paths must reference tests/fixtures/ or skills/.

    Returns (checks, fail_reason_or_None, must_fix).
    """
    impure_refs: dict[str, list[str]] = {}
    if t1_skill_dir.exists():
        for skill_dir in sorted(t1_skill_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            for test_type in ("generative", "bug-hunt", "clean"):
                scenario = skill_dir / test_type / "input" / "scenario.md"
                if not scenario.exists():
                    continue
                try:
                    sc_content = scenario.read_text(encoding="utf-8")
                except Exception:
                    continue
                refs = set(re.findall(r"`([a-zA-Z][\w\-/]*\.[a-zA-Z]+)`", sc_content))
                for ref in refs:
                    if ref.startswith("skills/"):
                        continue
                    if ref.startswith("tests/fixtures/"):
                        continue
                    impure_refs.setdefault(ref, []).append(f"{skill_dir.name}/{test_type}")

    if impure_refs:
        detail = "; ".join(
            f"'{r}' → must use tests/fixtures/ (found in: {', '.join(skills[:3])})"
            for r, skills in sorted(impure_refs.items())
        )
        return (
            [
                {
                    "id": "G0.9",
                    "s": GateStatus.FAIL,
                    "r": f"scenarios contain non-fixture paths: {detail}",
                }
            ],
            "scenarios contain non-fixture paths",
            ["G0.9: replace project paths with tests/fixtures/ equivalents"],
        )
    return (
        [
            {
                "id": "G0.9",
                "s": GateStatus.PASS,
                "note": "all scenario input paths reference tests/fixtures/",
            }
        ],
        None,
        [],
    )


def check_scenario_dir_purity(t1_skill_dir: Path) -> list[dict[str, Any]]:
    """G0.9c: scenario directory paths must reference tests/fixtures/ or skills/."""
    impure_dirs: dict[str, list[str]] = {}
    if t1_skill_dir.exists():
        for skill_dir in sorted(t1_skill_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            for test_type in ("generative", "bug-hunt", "clean"):
                scenario = skill_dir / test_type / "input" / "scenario.md"
                if not scenario.exists():
                    continue
                try:
                    sc_content = scenario.read_text(encoding="utf-8")
                except Exception:
                    continue
                dirs = set(re.findall(r"`([a-zA-Z][\w\-/]+/)`?", sc_content))
                dirs = {d.rstrip("`") for d in dirs}
                for d in dirs:
                    if d.startswith("tests/fixtures/") or d.startswith("skills/"):
                        continue
                    impure_dirs.setdefault(d, []).append(f"{skill_dir.name}/{test_type}")

    if impure_dirs:
        count = sum(len(v) for v in impure_dirs.values())
        detail = "; ".join(
            f"'{d}' → (found in: {', '.join(skills[:3])})"
            for d, skills in sorted(impure_dirs.items())
        )
        return [
            {
                "id": "G0.9c",
                "s": GateStatus.WARN,
                "r": f"{count} non-fixture directory references found: {detail}",
                "note": "not blocking; fix incrementally",
            }
        ]
    return [
        {
            "id": "G0.9c",
            "s": GateStatus.PASS,
            "note": "all scenario directory paths reference tests/fixtures/",
        }
    ]


def check_skill_md_purity(
    skills_dir: Path,
) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """G0.9b: SKILL.md files must NOT contain tests/fixtures/ references."""
    skill_fixture_leaks: dict[str, list[str]] = {}
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            sk_content = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue
        leaked = re.findall(r"tests/fixtures/[\w\-/]+", sk_content)
        if leaked:
            skill_fixture_leaks[skill_dir.name] = leaked

    if skill_fixture_leaks:
        detail = "; ".join(
            f"{skill}: {', '.join(paths)}" for skill, paths in sorted(skill_fixture_leaks.items())
        )
        return (
            [
                {
                    "id": "G0.9b",
                    "s": GateStatus.FAIL,
                    "r": f"SKILL.md files contain tests/fixtures/ paths (use project paths, not test paths): {detail}",
                }
            ],
            "SKILL.md files contain tests/fixtures/ paths",
            [
                "G0.9b: replace tests/fixtures/ paths in SKILL.md with project paths; move fixture mapping to scenario.md"
            ],
        )
    return (
        [
            {
                "id": "G0.9b",
                "s": GateStatus.PASS,
                "note": "no SKILL.md files leak test fixture paths",
            }
        ],
        None,
        [],
    )
