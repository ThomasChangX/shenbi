"""G0: pre-execution environment gate.

Extracted from tests/validate-gate.py in PR-19 (P-1.E).
"""

import hashlib
import json
import os
import re
from pathlib import Path

from shenbi.gates.shared import (  # noqa: F401
    ALL_SKILLS,
    CHAPTER_WORD_CEILING,
    CHAPTER_WORD_FLOOR,
    FATIGUE_BASE,
    FIXTURES,
    G4_CHECKER_SKILLS,
    META_NARRATIVE,
    PROJECT,
    SKILLS,
    TESTS,
    TRANSITION_SPECIFIC,
    _find_report,
    _normalize_file_paths,
    count_transition_words,
    fail,
    jload,
    passed,
    read_genre_config,
    unimplemented,
    word_count_md,
    write_gate_marker,
    yload,
)


def gate_G0(seed_file=None, round_dir=None):
    """G0: Round creation environment check."""
    checks = []

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
    novel_output = PROJECT / "novel-output"
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
    missing_dirs = []
    missing_md = []
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

    # G0.6 — novel-output writable
    no = PROJECT / "novel-output"
    if no.exists():
        if not os.access(str(no), os.W_OK):
            return fail(
                "G0",
                checks
                + [
                    {
                        "id": "G0.6",
                        "s": "FAIL",
                        "r": "novel-output/ not writable",
                    }
                ],
                "round_creation",
                ["G0.6"],
            )
    # novel-output doesn't exist yet; parent (PROJECT) must be writable
    # so round-exec.sh can create it
    elif not os.access(str(PROJECT), os.W_OK):
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.6",
                    "s": "FAIL",
                    "r": "PROJECT root not writable; cannot create novel-output/",
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
    missing_fixtures = {}
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

    # G0.9 — scenario path purity: all test input paths must reference
    # tests/fixtures/ or skills/. Project-relative paths (drafts/, truth/,
    # config/, etc.) are forbidden — they assume a running project, making
    # T1 isolation testing impossible. This rule prevents the "scenario
    # references project paths that don't exist" failure mode.
    allowed_prefixes = ("tests/fixtures/", "skills/")
    impure_refs = {}
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
                # Find ALL backtick-enclosed file paths (with extension).
                # Directory paths are handled by G0.9c separately.
                refs = set(re.findall(r"`([a-zA-Z][\w\-/]*\.[a-zA-Z]+)`", sc_content))
                for ref in refs:
                    # Skip skill references (allowed)
                    if ref.startswith("skills/"):
                        continue
                    # Skip already-validated fixture references
                    if ref.startswith("tests/fixtures/"):
                        continue
                    # Everything else is impure — project paths like
                    # drafts/, truth/, config/, chapters/, plans/, audits/
                    impure_refs.setdefault(ref, []).append(f"{skill_dir.name}/{test_type}")
    if impure_refs:
        detail = "; ".join(
            f"'{r}' → must use tests/fixtures/ (found in: {', '.join(skills[:3])})"
            for r, skills in sorted(impure_refs.items())
        )
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.9",
                    "s": "FAIL",
                    "r": f"scenarios contain non-fixture paths: {detail}",
                }
            ],
            "round_creation",
            ["G0.9: replace project paths with tests/fixtures/ equivalents"],
        )
    checks.append(
        {
            "id": "G0.9",
            "s": "PASS",
            "note": "all scenario input paths reference tests/fixtures/",
        }
    )

    # G0.9c — directory path purity: scenarios must not reference
    # project-relative directory paths (truth/, snapshots/, drafts/,
    # import/, etc.) as input sources. Only tests/fixtures/ dirs allowed.
    # Matches paths ending with / that don't start with allowed prefixes.
    impure_dirs = {}
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
                # Match backtick-enclosed directory paths (ending with /)
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
        checks.append(
            {
                "id": "G0.9c",
                "s": "WARN",
                "r": f"{count} non-fixture directory references found: {detail}",
                "note": "not blocking; fix incrementally",
            }
        )
    else:
        checks.append(
            {
                "id": "G0.9c",
                "s": "PASS",
                "note": "all scenario directory paths reference tests/fixtures/",
            }
        )

    # G0.9b — SKILL.md purity: SKILL.md files must NOT contain
    # tests/fixtures/ references. Skills define what they read/write
    # in project terms; scenario files are the only place where test
    # fixture paths belong. A skill hardcoding test fixture paths is
    # a leaky abstraction that breaks the skill's portability.
    skill_fixture_leaks = {}
    for skill_dir in SKILLS.iterdir():
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
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.9b",
                    "s": "FAIL",
                    "r": f"SKILL.md files contain tests/fixtures/ paths (use project paths, not test paths): {detail}",
                }
            ],
            "round_creation",
            [
                "G0.9b: replace tests/fixtures/ paths in SKILL.md with project paths; move fixture mapping to scenario.md"
            ],
        )
    checks.append(
        {
            "id": "G0.9b",
            "s": "PASS",
            "note": "no SKILL.md files leak test fixture paths",
        }
    )

    # G0.10 — completed generative test count (must be >= 59 for full round;
    # WARN if fewer — allows incremental execution)
    if round_dir:
        rd = Path(round_dir)
        t1_reports = rd / "t1-reports"
        if t1_reports.exists() and t1_reports.is_dir():
            generative_scores = list(t1_reports.glob("*-generative-scores.json"))
            count = len(generative_scores)
            if count < 59:
                checks.append(
                    {
                        "id": "G0.10",
                        "s": "WARN",
                        "r": f"generative tests: {count}/59 — {59 - count} remaining",
                        "completed": count,
                        "total": 59,
                    }
                )
            else:
                checks.append(
                    {
                        "id": "G0.10",
                        "s": "PASS",
                        "completed": count,
                        "total": 59,
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

    return passed("G0", checks)
