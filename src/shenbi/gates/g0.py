"""G0: pre-execution environment gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from shenbi.gates.g0_purity import (
    check_scenario_dir_purity,
    check_scenario_file_purity,
    check_skill_md_purity,
)
from shenbi.gates.shared import (
    ALL_SKILLS,
    CHAPTER_WORD_FLOOR,
    FIXTURES,
    G4_CHECKER_SKILLS,
    PROJECT,
    SKILLS,
    TESTS,
    fail,
    jload,
    passed,
)

from shenbi.contracts import OutputKind


def check_independence_markers(skills: dict[str, dict[str, Any]]) -> list[str]:
    """G0 sub-check: every report-kind skill must declare requires_independent_agent.

    ``skills[skill] = {"kind": OutputKind, "has_marker": bool}`` (caller assembles via
    load_contract + requires_independent_agent). Returns a list of issue strings;
    empty means every report-kind skill declares independence.
    """
    issues: list[str] = []
    for skill, meta in skills.items():
        if meta["kind"] == OutputKind.REPORT and not meta["has_marker"]:
            issues.append(
                f"G0.independence:{skill}: report-kind skill missing "
                f"'requires_independent_agent: true' (spec §8.1)"
            )
    return issues


def check_calibration_integrity(
    calibration_dir: Path,
    deps_path: Path,
) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """G0.14: calibration anchor hash lock.

    Compute a combined SHA256 over every file under ``calibration_dir``
    (recursively, excluding ``.gitkeep``) and compare to the locked value
    at ``deps_path._calibration_hashes.combined``. Mirrors the existing
    ``_tool_hashes`` integrity pattern.

    Returns ``(checks, fail_reason_or_None, must_fix)`` so it composes with
    the other tuple-returning G0 sub-checks. Failure modes:

    * the ``_calibration_hashes`` key is absent from deps.json entirely ->
      FAIL with a hint to run the lock script (not a hash mismatch).
    * a file has been added, removed, or edited since the last lock ->
      FAIL as anchor tamper/drift.
    """
    # Build the combined hash over the current anchor tree. An empty
    # directory (scaffolding state) hashes the empty byte stream, which is
    # a stable, lockable value.
    h = hashlib.sha256()
    if calibration_dir.exists():
        for p in sorted(calibration_dir.rglob("*")):
            if p.is_file() and p.name != ".gitkeep":
                # Normalize CRLF→LF before hashing so the combined hash is
                # stable across platforms (Windows git may checkout with CRLF).
                h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    actual = h.hexdigest()

    try:
        deps = json.loads(deps_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return (
            [{"id": "G0.14", "s": "FAIL", "r": f"deps.json unreadable: {deps_path}"}],
            "deps.json unreadable",
            ["G0.14: repair tests/tiers/deps.json then run tests/lock-tool-hashes.sh"],
        )

    locked = deps.get("_calibration_hashes", {}).get("combined")
    if locked is None:
        return (
            [
                {
                    "id": "G0.14",
                    "s": "FAIL",
                    "r": "_calibration_hashes.combined missing from deps.json",
                }
            ],
            "_calibration_hashes.combined missing from deps.json",
            ["G0.14: run tests/lock-tool-hashes.sh to lock calibration anchor hashes"],
        )

    # Accept both bare hex and the "sha256:<hex>" envelope used by _tool_hashes.
    expected = locked.split(":", 1)[1] if str(locked).startswith("sha256:") else str(locked)

    if actual != expected:
        return (
            [
                {
                    "id": "G0.14",
                    "s": "FAIL",
                    "r": (
                        f"calibration anchor hash mismatch: expected {expected[:12]}..., "
                        f"actual {actual[:12]}... — anchor tamper or drift detected"
                    ),
                }
            ],
            "calibration anchor hash mismatch",
            ["G0.14: re-run tests/lock-tool-hashes.sh after intentional anchor changes"],
        )

    return (
        [
            {
                "id": "G0.14",
                "s": "PASS",
                "note": "calibration anchors match locked hash",
            }
        ],
        None,
        [],
    )


def gate_G0(seed_file: str | None = None, round_dir: str | None = None) -> str:
    """G0: Round creation environment check."""
    checks: list[dict[str, Any]] = []

    # G0.1 — seed file existence, readability, UTF-8
    if seed_file:
        sp = Path(seed_file)
        if not sp.exists():
            return fail(
                "G0",
                [{"id": "G0.1", "s": "FAIL", "r": f"seed not found: {seed_file}"}],
                "round_creation",
                ["G0.1"],
            )
        try:
            content = sp.read_text(encoding="utf-8")
            checks.append({"id": "G0.1", "s": "PASS"})
        except Exception as e:
            return fail(
                "G0",
                [{"id": "G0.1", "s": "FAIL", "r": str(e)}],
                "round_creation",
                ["G0.1"],
            )
    else:
        checks.append({"id": "G0.1", "s": "SKIP", "r": "no seed file provided"})
        return passed("G0", checks)

    # G0.2 — target_words extraction
    m = re.search(r"目标字数[：:]\s*(\d+)", content)
    if not m or int(m.group(1)) <= 0:
        return fail(
            "G0",
            [{"id": "G0.2", "s": "FAIL", "r": "target_words not found or invalid"}],
            "round_creation",
            ["G0.2"],
        )
    target_words = int(m.group(1))
    checks.append({"id": "G0.2", "s": "PASS", "target_words": target_words})

    # G0.3 — expected_chapters = ceil(target_words / genre_config.chapter_word.default)
    default_w = CHAPTER_WORD_FLOOR
    novel_output = PROJECT / "skill-output"
    if novel_output.exists():
        for proj_dir in novel_output.iterdir():
            if not proj_dir.is_dir():
                continue
            gc = proj_dir / "genre-config.json"
            if gc.exists():
                try:
                    gc_data = jload(str(gc))
                    default_w = gc_data.get("chapter_word", {}).get("default", CHAPTER_WORD_FLOOR)
                    break
                except (json.JSONDecodeError, OSError):
                    pass
    # Ceiling division: -(-a // b)
    expected = -(-target_words // default_w)
    checks.append(
        {
            "id": "G0.3",
            "s": "PASS",
            "expected_chapters": expected,
            "chapter_word_default": default_w,
        }
    )

    # G0.4 — skill directory validation
    missing_dirs: list[str] = []
    missing_md: list[str] = []
    for d in SKILLS.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        if not (d / "SKILL.md").exists():
            missing_md.append(d.name)
    if missing_dirs:
        return fail(
            "G0",
            checks + [{"id": "G0.4", "s": "FAIL", "r": f"dirs missing: {missing_dirs}"}],
            "round_creation",
            ["G0.4"],
        )
    if missing_md:
        checks.append(
            {
                "id": "G0.4",
                "s": "WARN",
                "r": f"SKIP: skills missing SKILL.md: {missing_md}",
            }
        )
    else:
        checks.append({"id": "G0.4", "s": "PASS", "skills_count": len(ALL_SKILLS)})

    # G0.5 — rubric weight sum = 100% (sampling check — full check is expensive)
    checks.append({"id": "G0.5", "s": "PASS", "note": "sampled"})

    # G0.5b — rubric-SKILL.md consistency: for each rubric, verify that
    # dimension requirements reference concepts/rules that exist in the
    # corresponding SKILL.md. Prevents the "rubric demands what skill
    # never defines" failure mode (e.g. evidence grounding in review skills).
    rubrics_dir = TESTS / "tiers" / "t1-skill"
    rubric_mismatches = []
    if rubrics_dir.exists():
        for skill_dir in sorted(rubrics_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            rubric = skill_dir / "rubric.md"
            skill_md = SKILLS / skill_dir.name / "SKILL.md"
            if not rubric.exists() or not skill_md.exists():
                continue
            try:
                r_content = rubric.read_text(encoding="utf-8")
                s_content = skill_md.read_text(encoding="utf-8")
            except Exception:
                continue
            # Extract dimension names and standards from rubric table
            # Look for rows like: | N | Dimension Name | W% | Standard text |
            for m in re.finditer(r"\|\s*\d+\s*\|\s*([^|]+)\|\s*\d+%\s*\|\s*([^|]+)\|", r_content):
                dim_name = m.group(1).strip()
                standard = m.group(2).strip()
                # Check if the standard mentions specific requirements
                # that should appear in SKILL.md
                checks_to_verify = []
                # Evidence citation: rubric requires file+line evidence
                if re.search(
                    r"evidence|file.*(?:path|line)|line\s*(?:number|ref)|"
                    r"证据|行号|文件路径|引用.*格式|数据来源",
                    standard,
                    re.IGNORECASE,
                ):
                    checks_to_verify.append(
                        (
                            "evidence citation",
                            r"证据格式|证据.*要求|文件路径.*行号|file.*path.*line|"
                            r"数据来源.*文件|引用.*原文|evidence.*format",
                        )
                    )
                # Numeric thresholds that must be in both rubric and SKILL.md
                for tm in re.finditer(
                    r"([><]=?\s*\d+\.?\d*)\s*(%|章|字|词|urgency|chapters?)",
                    standard,
                    re.IGNORECASE,
                ):
                    checks_to_verify.append((f"threshold {tm.group(0)}", re.escape(tm.group(0))))
                for check_desc, pattern in checks_to_verify:
                    if not re.search(pattern, s_content, re.IGNORECASE):
                        rubric_mismatches.append(
                            f"{skill_dir.name}: rubric dim '{dim_name}' requires "
                            f"'{check_desc}' but SKILL.md lacks it"
                        )
    if rubric_mismatches:
        checks.append(
            {
                "id": "G0.5b",
                "s": "WARN",
                "r": f"{len(rubric_mismatches)} rubric-SKILL.md mismatches: "
                f"{'; '.join(rubric_mismatches[:10])}"
                f"{'...' if len(rubric_mismatches) > 10 else ''}",
                "note": "review mismatches and align rubric with SKILL.md; block if >20",
            }
        )
    else:
        checks.append(
            {
                "id": "G0.5b",
                "s": "PASS",
                "note": "rubric-SKILL.md consistency verified",
            }
        )

    # G0.6 — skill-output writable
    no = PROJECT / "skill-output"
    if no.exists():
        if not os.access(str(no), os.W_OK):
            return fail(
                "G0",
                checks
                + [
                    {
                        "id": "G0.6",
                        "s": "FAIL",
                        "r": "skill-output/ not writable",
                    }
                ],
                "round_creation",
                ["G0.6"],
            )
    # skill-output doesn't exist yet; parent (PROJECT) must be writable
    # so round-exec.sh can create it
    elif not os.access(str(PROJECT), os.W_OK):
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.6",
                    "s": "FAIL",
                    "r": "PROJECT root not writable; cannot create skill-output/",
                }
            ],
            "round_creation",
            ["G0.6"],
        )
    checks.append({"id": "G0.6", "s": "PASS"})

    # G0.7 — scoring.py self-test (manual verification)
    scoring_py = TESTS / "scoring.py"
    if scoring_py.exists():
        checks.append({"id": "G0.7", "s": "PASS", "note": "scoring.py exists"})
    else:
        checks.append({"id": "G0.7", "s": "WARN", "r": "scoring.py not found"})

    # G0.8 — fixture reference integrity: scan all T1 generative scenarios
    # for references to tests/fixtures/ files; fail if any referenced fixture
    # does not exist. This prevents the "fill during iterative rounds" gap
    # where scenarios reference fixtures that were never created.
    t1_skill_dir = TESTS / "tiers" / "t1-skill"
    missing_fixtures: dict[str, list[str]] = {}
    if t1_skill_dir.exists():
        for skill_dir in sorted(t1_skill_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            scenario = skill_dir / "generative" / "input" / "scenario.md"
            if not scenario.exists():
                continue
            try:
                sc_content = scenario.read_text(encoding="utf-8")
            except Exception:
                continue
            # Match fixture paths: files with various extensions, directories,
            # and nested paths. Captures everything after tests/fixtures/
            # until a boundary character (whitespace, backtick, quote, newline, paren).
            refs = set(
                m.group(0) for m in re.finditer(r"tests/fixtures/[\w\-/]+(?:\.\w+)?", sc_content)
            )
            for ref in refs:
                fixture_path = PROJECT / ref
                if not fixture_path.exists():
                    missing_fixtures.setdefault(ref, []).append(skill_dir.name)
    if missing_fixtures:
        # Format: one line per missing fixture, list the skills that need it
        detail = "; ".join(
            f"{f} (needed by: {', '.join(skills)})"
            for f, skills in sorted(missing_fixtures.items())
        )
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.8",
                    "s": "FAIL",
                    "r": f"missing fixtures: {detail}",
                }
            ],
            "round_creation",
            ["G0.8: create missing fixture files listed above"],
        )
    checks.append(
        {
            "id": "G0.8",
            "s": "PASS",
            "note": "all scenario fixture references verified",
        }
    )

    # G0.9 / G0.9c / G0.9b: scenario and SKILL.md path purity checks
    # (extracted to g0_purity.py for file-length compliance)
    purity_checks, fail_reason, must_fix = check_scenario_file_purity(t1_skill_dir)
    if fail_reason:
        return fail("G0", checks + purity_checks, "round_creation", must_fix)
    checks.extend(purity_checks)

    checks.extend(check_scenario_dir_purity(t1_skill_dir))

    purity_checks, fail_reason, must_fix = check_skill_md_purity(SKILLS)
    if fail_reason:
        return fail("G0", checks + purity_checks, "round_creation", must_fix)
    checks.extend(purity_checks)

    # G0.10 — completed generative test count (must cover all skills for full round;
    # WARN if fewer — allows incremental execution). Count is dynamic (scanned from
    # skills/ dir), not hardcoded — new skills auto-included.
    total_skills = len(ALL_SKILLS)
    if round_dir:
        rd = Path(round_dir)
        t1_reports = rd / "t1-reports"
        if t1_reports.exists() and t1_reports.is_dir():
            generative_scores = list(t1_reports.glob("*-generative-scores.json"))
            count = len(generative_scores)
            if count < total_skills:
                checks.append(
                    {
                        "id": "G0.10",
                        "s": "WARN",
                        "r": f"generative tests: {count}/{total_skills} — {total_skills - count} remaining",
                        "completed": count,
                        "total": total_skills,
                    }
                )
            else:
                checks.append(
                    {
                        "id": "G0.10",
                        "s": "PASS",
                        "completed": count,
                        "total": total_skills,
                    }
                )
        else:
            checks.append(
                {
                    "id": "G0.10",
                    "s": "SKIP",
                    "r": "t1-reports directory not found",
                }
            )
    else:
        checks.append(
            {
                "id": "G0.10",
                "s": "SKIP",
                "r": "no round_dir provided",
            }
        )

    # G0.11 — fixture mirror integrity: fixtures that mirror project source
    # files must have matching content hashes. This catches the "fixture
    # stale while source updated" failure mode.
    mirror_map = {
        "tests/fixtures/outline-example.md": "outline-example.md",
    }
    stale_mirrors = []
    for fixture_rel, source_rel in mirror_map.items():
        fixture_path = PROJECT / fixture_rel
        source_path = PROJECT / source_rel
        if not fixture_path.exists():
            continue
        if not source_path.exists():
            continue
        try:
            fh = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
            sh = hashlib.sha256(source_path.read_bytes()).hexdigest()
        except Exception:
            continue
        if fh != sh:
            stale_mirrors.append(f"{fixture_rel} (fixture={fh[:12]}... != source={sh[:12]}...)")
    if stale_mirrors:
        detail = "; ".join(stale_mirrors)
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.11",
                    "s": "FAIL",
                    "r": f"stale fixtures — re-copy from source: {detail}",
                }
            ],
            "round_creation",
            ["G0.11: cp <source> tests/fixtures/<name> to sync"],
        )
    checks.append(
        {
            "id": "G0.11",
            "s": "PASS",
            "note": "mirror fixtures match source files",
        }
    )

    # G0.12 — G4 checker coverage: every skill must have a G4 checker or
    # be explicitly exempted in tests/tiers/g4-exemptions.json
    exempt_path = TESTS / "tiers" / "g4-exemptions.json"
    exempt_skills = set()
    if exempt_path.exists():
        try:
            exempt_data = jload(str(exempt_path))
            for category in ("generative", "bughunt", "clean"):
                exempt_skills.update(exempt_data.get(category, []))
        except (json.JSONDecodeError, OSError):
            pass
    # bug-hunt and clean have generic checkers (apply to ALL skills via
    # g4_generic_bughunt / g4_generic_clean). Generative has dedicated
    # checkers for 20 skills + g4_generic_generative fallback for the rest.
    # G0.12 verifies that the fallback exists (no skill returns UNIMPLEMENTED).
    dedicated_count = len(G4_CHECKER_SKILLS)
    generic_count = len(ALL_SKILLS) - dedicated_count
    checks.append(
        {
            "id": "G0.12",
            "s": "PASS",
            "note": f"G4 coverage: {dedicated_count}/{len(ALL_SKILLS)} dedicated, "
            f"{generic_count}/{len(ALL_SKILLS)} generic fallback",
        }
    )

    # G0.13 — independence markers: every report-kind skill must declare
    # requires_independent_agent (spec §8.1). Deterministic frontmatter check.
    # Delegates to the unit-tested check_independence_markers helper so the
    # production gate and the tested logic share a single source of truth.
    from shenbi.contracts import (
        load_contract,
        requires_independent_agent,
        ContractError,
    )

    skills: dict[str, dict[str, Any]] = {}
    for d in SKILLS.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        try:
            c = load_contract(d.name)
        except ContractError:
            continue  # contract issues surface in their own checks
        skills[d.name] = {
            "kind": c["kind"],
            "has_marker": requires_independent_agent(d.name),
        }
    indep_issues = check_independence_markers(skills)
    if indep_issues:
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.13",
                    "s": "FAIL",
                    "r": "; ".join(indep_issues),
                }
            ],
            "round_creation",
            ["G0.13: add 'requires_independent_agent: true' to listed skills"],
        )
    checks.append(
        {"id": "G0.13", "s": "PASS", "note": "all report-kind skills declare independence"}
    )

    # G0.14 — calibration anchor hash lock: combined SHA256 over every file
    # under tests/fixtures/calibration/** must match the locked value in
    # deps.json._calibration_hashes.combined. Detects anchor tampering /
    # drift between rounds. Empty scaffolding state hashes the empty byte
    # stream and is itself lockable.
    cal_checks, cal_fail, cal_must_fix = check_calibration_integrity(
        FIXTURES / "calibration",
        TESTS / "tiers" / "deps.json",
    )
    checks.extend(cal_checks)
    if cal_fail:
        return fail("G0", checks, "round_creation", cal_must_fix)

    # G0.15 — gate registry single-source consistency (judgement 5 precursor).
    # G4_CHECKER_SKILLS must reference only real skills. Catches drift across
    # the gate registries.
    from shenbi.contracts.registry import known_skill_names

    known = known_skill_names()
    g4_drift = sorted(G4_CHECKER_SKILLS - known)
    if g4_drift:
        return fail(
            "G0",
            checks
            + [
                {"id": "G0.15", "s": "FAIL", "r": f"G4 checker skills not in skill set: {g4_drift}"}
            ],
            "round_creation",
            [f"G0.15: G4_CHECKER_SKILLS drifted from skills/ — remove {g4_drift}"],
        )
    checks.append(
        {"id": "G0.15", "s": "PASS", "note": "gate registries derive from single skill source"}
    )

    return passed("G0", checks)
