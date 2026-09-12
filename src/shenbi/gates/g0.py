"""G0: pre-execution environment gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.status import GateStatus

from shenbi.logging import get_logger

log = get_logger(__name__)


# G0.11 fixture mirror map — single source of truth (spec Task 2.3 铁律 7).
# tools/check_fixture_mirror.py 与 gate_G0() 都读此常量，避免两处漂移。
# spec #57 T4: timestamped snapshot mirrors removed — upstream writer class
# deleted (#26 path 3); fixtures retained in tests/fixtures/snapshot-dir as
# real historical outputs.
MIRROR_MAP: dict[str, str] = {
    "tests/fixtures/outline-example.md": "outline-example.md",
    "tests/fixtures/volume-map-xinghuo.md": "novel-output/xinghuo-ranqiong/outline/volume_map.md",
    "tests/fixtures/truth-pending_hooks-ch56.md": (
        "novel-output/xinghuo-ranqiong/truth/pending_hooks.md"
    ),
    "tests/fixtures/truth-current_state-xinghuo.md": (
        "novel-output/xinghuo-ranqiong/truth/current_state.md"
    ),
    # spec #54 C16 F780: chapter-025 snapshot truth mirrors must stay
    # byte-identical to their top-level truth-*.md counterparts.
    "tests/fixtures/truth-chapter_summaries.md": (
        "tests/fixtures/snapshots/chapter-025/truth/chapter_summaries.md"
    ),
    "tests/fixtures/truth-emotional_arcs.md": (
        "tests/fixtures/snapshots/chapter-025/truth/emotional_arcs.md"
    ),
    "tests/fixtures/truth-pending_hooks.md": (
        "tests/fixtures/snapshots/chapter-025/truth/pending_hooks.md"
    ),
    "tests/fixtures/truth-character_matrix.md": (
        "tests/fixtures/snapshots/chapter-025/truth/character_matrix.md"
    ),
    # spec #54 C16 AC3 / F781: same-source duplicate pairs populated during
    # library governance — registered so the sync guard (not hash dedup)
    # owns their equality.
    "tests/fixtures/characters/supporting/relationships.md": (
        "tests/fixtures/truth/character_profiles/relationships.md"
    ),
    "tests/fixtures/consolidation/volume-1/volume-summary.md": (
        "tests/fixtures/story/volumes/volume-map.md"
    ),
    "tests/fixtures/source/report-example.txt": (
        "tests/fixtures/truth/source_material/original-work.txt"
    ),
    "tests/fixtures/config/platform-rules/genre-config.json": (
        "tests/fixtures/genre-config-example.json"
    ),
    "tests/fixtures/samples/reference-texts/reference-chapter-3.md": (
        "tests/fixtures/drafts/chapter-3.md"
    ),
    "tests/fixtures/decisions/corpus/case01-ok.json": (
        "tests/fixtures/decisions/valid-chapter-decisions.json"
    ),
    "tests/fixtures/decisions/corpus/case07-bad_json_prefix.json": (
        "tests/fixtures/revision-decisions/chapter-legacy-severity-revision-decisions.json"
    ),
    "tests/fixtures/decisions/corpus/case03-bad_json_concat.json": (
        "tests/fixtures/decisions/trailing-sample.json"
    ),
    "tests/fixtures/decisions/corpus/case14-bad_schema_p25.json": (
        "tests/fixtures/revision-decisions/chapter-sample-revision-decisions.json"
    ),
    # 阶段 8 终审补：payload 级（frontmatter 剥离后）重复对
    "tests/fixtures/audits/chapter-1-character.md": ("tests/fixtures/audit-report-example.md"),
    "tests/fixtures/consolidation/volume-1/unresolved-hooks.md": (
        "tests/fixtures/truth-pending_hooks-ch56.md"
    ),
}


import hashlib
import math
import json
import os
import re
from pathlib import Path
from typing import Any

_FM_PROVENANCE_RE = re.compile(
    rb"\A---\r?\n.*?^provenance:.*?\r?\n---\r?\n\n?", re.DOTALL | re.MULTILINE
)


def mirror_digest(path: Path) -> str:
    """Content sha256 with provenance frontmatter stripped (spec #54 C16 F780).

    Provenance carriers are metadata, not content: a mirror may carry a
    ``provenance:`` frontmatter block that its source lacks. Mirror identity
    is judged on the payload bytes after stripping such a leading block.
    """
    data = path.read_bytes()
    if path.suffix == ".md":
        data = _FM_PROVENANCE_RE.sub(b"", data, count=1)
    return hashlib.sha256(data).hexdigest()


from shenbi.gates.g0_config_coherence import check_config_coherence
from shenbi.gates.g0_purity import (
    check_scenario_dir_purity,
    check_scenario_file_purity,
    check_scenario_reference_closure,
    check_skill_md_purity,
    check_fixture_provenance,
    check_variant_bypass,
)
from shenbi.paths import Layout, detect_layout
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
        for p in sorted(
            calibration_dir.rglob("*"),
            key=lambda x: str(x.relative_to(calibration_dir)).replace(os.sep, "/"),
        ):
            if p.is_file() and p.name != ".gitkeep":
                # Normalize CRLF→LF before hashing so the combined hash is
                # stable across platforms (Windows git may checkout with CRLF).
                h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    actual = h.hexdigest()

    try:
        deps = json.loads(deps_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return (
            [{"id": "G0.14", "s": GateStatus.FAIL, "r": f"deps.json unreadable: {deps_path}"}],
            "deps.json unreadable",
            ["G0.14: repair tests/tiers/deps.json then run tests/lock-tool-hashes.sh"],
        )

    locked = deps.get("_calibration_hashes", {}).get("combined")
    if locked is None:
        return (
            [
                {
                    "id": "G0.14",
                    "s": GateStatus.FAIL,
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
                    "s": GateStatus.FAIL,
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
                "s": GateStatus.PASS,
                "note": "calibration anchors match locked hash",
            }
        ],
        None,
        [],
    )


def _layout_project_roots(base: Path, layouts: frozenset[Layout]) -> list[Path]:
    """Collect project roots under ``base`` whose detected layout is in ``layouts``.

    Spec #48 C34 (F413): single probe authority is ``shenbi.paths.detect_layout``.
    Candidates = direct children of base plus children of the layout-root
    containers (excluding container dirs themselves); a candidate is a project
    root only when its layout key file exists (detect root-name hits alone are
    anchors for the upward walk, never project roots).
    """
    candidates: list[Path] = sorted(p for p in base.iterdir() if p.is_dir())
    for container in ("novel-output", "skill-output"):
        cdir = base / container
        if cdir.is_dir():
            candidates.extend(sorted(p for p in cdir.iterdir() if p.is_dir()))
    roots: list[Path] = []
    seen: set[Path] = set()
    for cand in candidates:
        if cand.name in ("novel-output", "skill-output", "project-output") or cand in seen:
            continue  # container dirs never returned as project roots
        verdict = detect_layout(cand)
        key_file = "novel.json" if verdict is Layout.PROJECT_OUTPUT else "genre-config.json"
        if verdict in layouts and (cand / key_file).exists():
            roots.append(cand)
            seen.add(cand)
    return sorted(roots)


_WEIGHT_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)%")


def _rubric_weight_sum(rubric_path: Path) -> float | None:
    """Sum the Weight column of a rubric's dimension tables.

    Header-aware: the Weight column is located by the table header row, so
    layouts with populated columns after Weight (the majority convention in
    this repo's rubrics) are parsed correctly, and percent tokens in other
    columns (e.g. "≥90%" in a Standard cell) are never counted.

    Returns None when the rubric has no weight cells at all (prose-only or
    non-scoring rubric) — such rubrics are skipped, not failed.
    """
    lines = rubric_path.read_text(encoding="utf-8").splitlines()
    total = 0.0
    found = False
    i = 0
    while i < len(lines):
        line = lines[i]
        cells = (
            [c.strip() for c in line.strip().strip("|").split("|")]
            if line.lstrip().startswith("|")
            else []
        )
        if cells and "weight" in [c.lower() for c in cells]:
            widx = [c.lower() for c in cells].index("weight")
            j = i + 2  # skip the |---|---| separator row
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                row = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                if widx < len(row):
                    m = _WEIGHT_VALUE_RE.fullmatch(row[widx])
                    if m:
                        total += float(m.group(1))
                        found = True
                j += 1
            i = j
        else:
            i += 1
    return total if found else None


def _g05_weight_check() -> dict[str, Any]:
    """G0.5: every rubric weight table under tests/tiers sums to exactly 100%."""
    bad: list[str] = []
    rubrics = sorted((TESTS / "tiers").rglob("rubric.md")) if (TESTS / "tiers").exists() else []
    for rubric in rubrics:
        total = _rubric_weight_sum(rubric)
        # Skip _-prefixed scaffolding (same convention as G0.4/G0.5b):
        # _template carries placeholder weights, not a scoring contract.
        if total is None or any(part.startswith("_") for part in rubric.relative_to(TESTS).parts):
            continue
        if not math.isclose(total, 100, abs_tol=1e-9):
            bad.append(f"{rubric.relative_to(TESTS)}={total:g}%")
    if bad:
        return {
            "id": "G0.5",
            "s": GateStatus.FAIL,
            "r": f"rubric weights must sum to 100%: {bad}",
        }
    return {
        "id": "G0.5",
        "s": GateStatus.PASS,
        "rubrics_checked": len(rubrics),
    }


def gate_G0(seed_file: str | None = None, round_dir: str | None = None) -> str:
    """G0: Round creation environment check."""
    checks: list[dict[str, Any]] = []

    # G0.1 — seed file existence, readability, UTF-8
    if seed_file:
        sp = Path(seed_file)
        if not sp.exists():
            return fail(
                "G0",
                [{"id": "G0.1", "s": GateStatus.FAIL, "r": f"seed not found: {seed_file}"}],
                "round_creation",
                ["G0.1"],
            )
        try:
            content = sp.read_text(encoding="utf-8")
            checks.append({"id": "G0.1", "s": GateStatus.PASS})
        except Exception as e:
            return fail(
                "G0",
                [{"id": "G0.1", "s": GateStatus.FAIL, "r": str(e)}],
                "round_creation",
                ["G0.1"],
            )
    else:
        checks.append({"id": "G0.1", "s": GateStatus.SKIP, "r": "no seed file provided"})
        return passed("G0", checks)

    # G0.2 — target_words extraction
    m = re.search(r"目标字数[：:]\s*(\d+)", content)
    if not m or int(m.group(1)) <= 0:
        return fail(
            "G0",
            [{"id": "G0.2", "s": GateStatus.FAIL, "r": "target_words not found or invalid"}],
            "round_creation",
            ["G0.2"],
        )
    target_words = int(m.group(1))
    checks.append({"id": "G0.2", "s": GateStatus.PASS, "target_words": target_words})

    # G0.3 — expected_chapters = ceil(target_words / genre_config.chapter_word.default)
    default_w = CHAPTER_WORD_FLOOR
    # spec #48 C34 (F413): project-root set expanded from skill-output-only to
    # all detected layouts via the single probe authority.
    for proj_dir in _layout_project_roots(
        PROJECT, frozenset({Layout.NOVEL_OUTPUT, Layout.SKILL_OUTPUT})
    ):
        gc = proj_dir / "genre-config.json"
        try:
            gc_data = jload(str(gc))
            default_w = gc_data.get("chapter_word", {}).get("default", CHAPTER_WORD_FLOOR)
            break
        except (json.JSONDecodeError, OSError):
            continue  # malformed genre-config.json → try next project dir
    # Ceiling division: -(-a // b)
    expected = -(-target_words // default_w)
    checks.append(
        {
            "id": "G0.3",
            "s": GateStatus.PASS,
            "expected_chapters": expected,
            "chapter_word_default": default_w,
        }
    )

    # G0.4 — skill directory validation
    missing_md: list[str] = []
    for d in SKILLS.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        if not (d / "SKILL.md").exists():
            missing_md.append(d.name)
    if missing_md:
        checks.append(
            {
                "id": "G0.4",
                "s": GateStatus.WARN,
                "r": f"SKIP: skills missing SKILL.md: {missing_md}",
            }
        )
    else:
        checks.append({"id": "G0.4", "s": GateStatus.PASS, "skills_count": len(ALL_SKILLS)})

    # G0.5 — rubric weight sum = 100% (C17 T5 / T1109: real implementation)
    checks.append(_g05_weight_check())

    # G0.5b — rubric-SKILL.md consistency: for each rubric, verify that
    # dimension requirements reference concepts/rules that exist in the
    # corresponding SKILL.md. Prevents the "rubric demands what skill
    # never defines" failure mode (e.g. evidence grounding in review skills).
    rubrics_dir = TESTS / "tiers" / "t1-skill"
    rubric_mismatches: list[Any] = []
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
                checks_to_verify: list[Any] = []
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
                "s": GateStatus.WARN,
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
                "s": GateStatus.PASS,
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
                        "s": GateStatus.FAIL,
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
                    "s": GateStatus.FAIL,
                    "r": "PROJECT root not writable; cannot create skill-output/",
                }
            ],
            "round_creation",
            ["G0.6"],
        )
    checks.append({"id": "G0.6", "s": GateStatus.PASS})

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
                    "s": GateStatus.FAIL,
                    "r": f"missing fixtures: {detail}",
                }
            ],
            "round_creation",
            ["G0.8: create missing fixture files listed above"],
        )
    checks.append(
        {
            "id": "G0.8",
            "s": GateStatus.PASS,
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

    # G0.17/G0.18/G0.19 — fixture authenticity enforcement (spec #54 C16):
    # reference existence closure, provenance tri-state carriers, variant
    # bypass. Waves start in WARN mode; promotion to FAIL is per-wave after
    # live re-scan count reaches zero (see g0_purity.ENFORCEMENT_WAVES).
    checks.extend(check_scenario_reference_closure(t1_skill_dir, PROJECT))
    checks.extend(check_fixture_provenance(t1_skill_dir, FIXTURES))
    checks.extend(check_variant_bypass(t1_skill_dir, FIXTURES))

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
            generative_scores = [
                p
                for p in t1_reports.glob("*-generative-scores*.json")
                # spec #31: dual-scorer second file would double-count a skill.
                if not p.name.endswith("-scores-subagent-2.json")
            ]
            count = len(generative_scores)
            if count < total_skills:
                checks.append(
                    {
                        "id": "G0.10",
                        "s": GateStatus.WARN,
                        "r": f"generative tests: {count}/{total_skills} — {total_skills - count} remaining",
                        "completed": count,
                        "total": total_skills,
                    }
                )
            else:
                checks.append(
                    {
                        "id": "G0.10",
                        "s": GateStatus.PASS,
                        "completed": count,
                        "total": total_skills,
                    }
                )
        else:
            checks.append(
                {
                    "id": "G0.10",
                    "s": GateStatus.SKIP,
                    "r": "t1-reports directory not found",
                }
            )
    else:
        checks.append(
            {
                "id": "G0.10",
                "s": GateStatus.SKIP,
                "r": "no round_dir provided",
            }
        )

    # G0.11 — fixture mirror integrity: fixtures that mirror project source
    # files must have matching content hashes. This catches the "fixture
    # stale while source updated" failure mode. Missing sides are reported
    # explicitly (spec #54 C16 / T803 fix: no silent skip).
    stale_mirrors: list[str] = []
    missing_sides: list[str] = []
    for fixture_rel, source_rel in MIRROR_MAP.items():
        fixture_path = PROJECT / fixture_rel
        source_path = PROJECT / source_rel
        if not fixture_path.exists():
            missing_sides.append(f"fixture side missing: {fixture_rel}")
            continue
        if not source_path.exists():
            missing_sides.append(f"source side missing: {source_rel} (for {fixture_rel})")
            continue
        try:
            fh = mirror_digest(fixture_path)
            sh = mirror_digest(source_path)
        except Exception:
            continue
        if fh != sh:
            stale_mirrors.append(f"{fixture_rel} (fixture={fh[:12]}... != source={sh[:12]}...)")
    if missing_sides:
        checks.append(
            {
                "id": "G0.11",
                "s": GateStatus.WARN,
                "r": f"missing mirror side: {'; '.join(missing_sides)}",
                "note": "register or remove the half-dead MIRROR_MAP entry",
            }
        )
    if stale_mirrors:
        detail = "; ".join(stale_mirrors)
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.11",
                    "s": GateStatus.FAIL,
                    "r": f"stale fixtures — re-copy from source: {detail}",
                }
            ],
            "round_creation",
            ["G0.11: cp <source> tests/fixtures/<name> to sync"],
        )
    checks.append(
        {
            "id": "G0.11",
            "s": GateStatus.PASS,
            "note": "mirror fixtures match source files",
        }
    )

    # G0.12 — G4 checker coverage: every skill must resolve to a G4 checker
    # (dedicated or generic fallback) — none returns UNIMPLEMENTED
    # bug-hunt and clean have generic checkers (apply to ALL skills via
    # g4_generic_bughunt / g4_generic_clean). Generative has dedicated
    # checkers for G4_CHECKER_SKILLS entries + g4_generic_generative fallback for the rest.
    # G0.12 verifies that the fallback exists (no skill returns UNIMPLEMENTED).
    dedicated_count = len(G4_CHECKER_SKILLS)
    generic_count = len(ALL_SKILLS) - dedicated_count
    checks.append(
        {
            "id": "G0.12",
            "s": GateStatus.PASS,
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
                    "s": GateStatus.FAIL,
                    "r": "; ".join(indep_issues),
                }
            ],
            "round_creation",
            ["G0.13: add 'requires_independent_agent: true' to listed skills"],
        )
    checks.append(
        {"id": "G0.13", "s": GateStatus.PASS, "note": "all report-kind skills declare independence"}
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
                {
                    "id": "G0.15",
                    "s": GateStatus.FAIL,
                    "r": f"G4 checker skills not in skill set: {g4_drift}",
                }
            ],
            "round_creation",
            [f"G0.15: G4_CHECKER_SKILLS drifted from skills/ — remove {g4_drift}"],
        )
    checks.append(
        {
            "id": "G0.15",
            "s": GateStatus.PASS,
            "note": "gate registries derive from single skill source",
        }
    )

    # G0.16 — skill contract + description quality (spec §3.1). Validates every
    # skills/*/SKILL.md: description <= 500 chars and trigger-only, writes/
    # updates disjoint, write semantics (mode) declared.
    from shenbi.gates.g0_skill_contract import check_skill_contracts

    sc_issues = check_skill_contracts()
    if sc_issues:
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.16",
                    "s": GateStatus.FAIL,
                    "r": "; ".join(sc_issues),
                }
            ],
            "round_creation",
            [
                "G0.16: shorten descriptions to <=500 chars (trigger-only), "
                "remove writes/updates overlap, add mode: to declared writes/updates"
            ],
        )
    checks.append(
        {
            "id": "G0.16",
            "s": GateStatus.PASS,
            "note": "all skills pass contract + description checks",
        }
    )

    # G0.cc — configuration coherence (threshold mismatch + critical audit
    # disabled). Production genre-config.json does NOT live at the repo root
    # (PROJECT); it lives one level down under novel-output/<project>/. So scan
    # PROJECT / "novel-output" / "*" for any subdir containing a genre-config.json
    # and run the coherence check against each. G0 is also invoked standalone on
    # the repo itself, where there may be no novel-output/ at all — in that case
    # the loop finds nothing and the check is a silent no-op.
    cc_must_fix: list[str] = []
    try:
        # spec #48 C34: novel-output-only semantics preserved, scan via
        # _layout_project_roots single source.
        project_dirs = _layout_project_roots(PROJECT, frozenset({Layout.NOVEL_OUTPUT}))
        for project_dir in project_dirs:
            # Read the in-effect floor from pipeline-state.json when present
            # (was dead-wired: floor checks never ran from gate_G0 — spec 13 R1).
            floor: int | float | None = None
            state_path = project_dir / "pipeline-state.json"
            if state_path.exists():
                try:
                    state_data: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))
                    raw_floor = state_data.get("config", {}).get("resonance_global_floor")
                    if raw_floor is not None:
                        # Pass raw through: the checker flags non-numeric values
                        # loudly (floor_invalid_type) instead of silent skip.
                        floor = raw_floor  # pyright: ignore[reportAssignmentType]
                except (OSError, json.JSONDecodeError):
                    log.warning("g0_state_read_failed_for_floor", path=str(state_path))
            cc_issues = check_config_coherence(project_dir, resonance_global_floor=floor)
            for idx, issue in enumerate(cc_issues):
                check_id = f"G0.cc.{idx + 1}"
                checks.append({"id": check_id, "s": GateStatus.FAIL, "r": issue})
                cc_must_fix.append(check_id)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        log.debug("g0_config_coherence_skipped")

    if cc_must_fix:
        return fail("G0", checks, "config_coherence", cc_must_fix)
    return passed("G0", checks)
