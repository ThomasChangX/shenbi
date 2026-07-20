"""Generic G4 checkers + G4 router + bughunt/clean wrappers."""

from __future__ import annotations
from typing import Any

import json
import re
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_input_path,
)
from shenbi.status import GateStatus


def g4_generic_generative(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Generic G4 for skills without specific checkers. Validates output exists, non-empty, has frontmatter."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp_path in fps or []:
        p = resolve_input_path(fp_path, rd)
        if not p.exists():
            mf.append(f"G4.gen.not_found:{fp_path}")
            continue
        if p.stat().st_size == 0:
            mf.append(f"G4.gen.empty:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.gen.read_error:{fp_path}")
            continue
        if fp_path.endswith(".md"):
            if len(content.strip()) < 50:
                mf.append(f"G4.gen.too_short:{fp_path}")
            else:
                c.append({"id": f"G4.gen.{Path(fp_path).name}", "s": "PASS", "size": len(content)})
        elif fp_path.endswith(".json"):
            try:
                json.loads(content)
                c.append({"id": f"G4.gen.{Path(fp_path).name}", "s": "PASS"})
            except json.JSONDecodeError:
                mf.append(f"G4.gen.invalid_json:{fp_path}")
        else:
            c.append({"id": f"G4.gen.{Path(fp_path).name}", "s": "PASS", "size": len(content)})
    if not fps:
        c.append({"id": "G4.gen", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-generic-gen", c, "scoring", mf)
    return passed("G4-generic-gen", c)


def g4_generic_bughunt(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Generic G4 for bug-hunt reports. Validates report format: detection summary table, file+line citations, rule names, false positive check."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp_path in fps or []:
        p = resolve_input_path(fp_path, rd)
        if not p.exists():
            mf.append(f"G4.bh.not_found:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.bh.read_error:{fp_path}")
            continue
        # Must have Detection Summary or equivalent
        if not re.search(r"## Detection|## 检测|## Defect|缺陷", content):
            mf.append(f"G4.bh.no_detection_section:{fp_path}")
        # Must have file location citations (file path, line number, or both)
        if not re.search(r"(?:L\d+|line\s+\d+|\:\d+|`[^`]+\.[a-z]+`)", content, re.IGNORECASE):
            mf.append(f"G4.bh.no_location_ref:{fp_path}")
        # Must have SKILL.md rule reference (Chinese or English patterns)
        has_rule = bool(
            re.search(
                r"铁律|Iron Rule|Iron Law|Violated Rule|SKILL\.md.*Rule|违反.*规则|SKILL\.md Rule",
                content,
                re.IGNORECASE,
            )
        )
        if not has_rule:
            mf.append(f"G4.bh.no_rule_reference:{fp_path}")
        # Must have false positive check (flexible: markdown bold, colon, dash separators)
        if not re.search(r"False positives?[^0-9]*0|误报[^0-9]*0", content, re.IGNORECASE):
            mf.append(f"G4.bh.no_false_positive_check:{fp_path}")
        if not mf or all(not x.startswith("G4.bh.") for x in mf):
            c.append({"id": f"G4.bh.{Path(fp_path).name}", "s": "PASS"})
    if not fps:
        c.append({"id": "G4.bh", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-bug-hunt", c, "scoring", mf)
    return passed("G4-bug-hunt", c)


def g4_generic_clean(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Generic G4 for clean reports. Validates: per-file confirmation, zero issues assertion, no fabricated suggestions."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp_path in fps or []:
        p = resolve_input_path(fp_path, rd)
        if not p.exists():
            mf.append(f"G4.cl.not_found:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.cl.read_error:{fp_path}")
            continue
        # Must confirm zero issues (digits, Chinese zero, or "Zero" in heading)
        if not re.search(r"\b0\b|零|Zero", content, re.IGNORECASE):
            mf.append(f"G4.cl.no_zero_count:{fp_path}")
        # Must list files checked (various heading formats)
        if not re.search(r"Files Checked|Per-File Confirmation|文件|确认合规", content):
            mf.append(f"G4.cl.no_file_list:{fp_path}")
        # Must not have improvement suggestions (these = hallucinated defects)
        # Exclude negation contexts ("无改进建议", "no improvement suggestions")
        suggestion_matches = re.findall(
            r"(?:改进建议|建议优化|improvement suggestion)", content, re.IGNORECASE
        )
        # Filter out negated mentions
        real_suggestions = []
        for m in suggestion_matches:
            # Check 10 chars before the match for negation
            idx = content.lower().index(m.lower()) if m.lower() in content.lower() else -1
            if idx >= 0:
                before = content[max(0, idx - 15) : idx]
                if not re.search(r"无|不|no\s|not\s|without|没", before, re.IGNORECASE):
                    real_suggestions.append(m)
        if real_suggestions:
            mf.append(f"G4.cl.has_suggestions:{fp_path}:{real_suggestions}")
        if not mf or all(not x.startswith("G4.cl.") for x in mf):
            c.append({"id": f"G4.cl.{Path(fp_path).name}", "s": "PASS"})
    if not fps:
        c.append({"id": "G4.cl", "s": "SKIP", "r": "no files"})
    if mf:
        return fail("G4-clean", c, "scoring", mf)
    return passed("G4-clean", c)


#: Findings that FAIL the gate vs WARN. Everything else defaults to WARN.
_POST_WRITE_FAIL_PREFIXES = (
    "G4.pi.model_leakage",
    "G4.pi.unfinished_ending",
    "G4.ac.",
    "G4.av.",
)


def g4_post_write_integrity(project_dir: Path, *, chapter: int) -> dict[str, Any]:
    """G4 checker: consume persisted post-write integrity findings.

    Reads ``audits/.integrity-findings-<chapter>.jsonl`` (written by
    ``_write_parsed_outputs``) and maps each finding to a G4 check with the
    severity from spec §3.6. Returns a dict ``{"status", "checks"}``.
    """
    findings_path = project_dir / "audits" / f".integrity-findings-{chapter}.jsonl"
    checks: list[dict[str, Any]] = []
    has_fail = False
    has_warn = False
    if findings_path.exists():
        for line in findings_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            finding = str(entry.get("finding", ""))
            is_fail = any(finding.startswith(p) for p in _POST_WRITE_FAIL_PREFIXES)
            # fence_imbalance is the only WARN.
            if finding.startswith("G4.pi.fence_imbalance"):
                is_fail = False
            check_id = finding.split(":", maxsplit=1)[0] if ":" in finding else finding
            checks.append(
                {"id": check_id, "s": GateStatus.FAIL if is_fail else GateStatus.WARN, "r": finding}
            )
            has_fail = has_fail or is_fail
            has_warn = has_warn or (not is_fail)
    status = GateStatus.FAIL if has_fail else (GateStatus.WARN if has_warn else GateStatus.PASS)
    return {"status": status, "checks": checks}


def _chapter_number_from_paths(file_paths: list[str]) -> int | None:
    """Extract chapter number from file paths like ``chapter-NN``."""
    for fp in file_paths:
        m = re.search(r"chapter-(\d+)", fp)
        if m:
            return int(m.group(1))
    return None


def _merge_pwi_into_result(result_str: str, pwi: dict[str, Any]) -> str:
    """Merge post-write integrity findings into an existing G4 result JSON string."""
    try:
        result_data: dict[str, Any] = json.loads(result_str)
    except (json.JSONDecodeError, TypeError):
        result_data = {"status": GateStatus.FAIL, "checks": [], "must_fix": ["unparseable"]}

    result_data.setdefault("checks", [])
    existing_checks: list[dict[str, Any]] = result_data["checks"]
    existing_checks.extend(pwi["checks"])

    # Elevate status: FAIL > WARN > PASS
    current = result_data.get("status", GateStatus.PASS)
    pwi_status = pwi["status"]
    if pwi_status == GateStatus.FAIL or current == GateStatus.FAIL:
        result_data["status"] = GateStatus.FAIL
    elif pwi_status == GateStatus.WARN and current != GateStatus.FAIL:
        result_data["status"] = GateStatus.WARN

    return json.dumps(result_data, indent=2, ensure_ascii=False)


def gate_G4(
    skill_name: str,
    test_type: str,
    file_paths: list[str],
    round_dir: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """G4: Route to the correct per-skill checker."""
    if test_type == "bug-hunt":
        return g4_generic_bughunt(file_paths, round_dir, project_dir, repo_root)
    if test_type == "clean":
        return g4_generic_clean(file_paths, round_dir, project_dir, repo_root)

    # Late imports: per-skill checkers live in sibling modules to avoid
    # circular imports at module load time.
    from shenbi.gates.g4.anti_detect import g4_anti_detect
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting
    from shenbi.gates.g4.chapter_planning import g4_chapter_planning
    from shenbi.gates.g4.character_design import g4_character_design
    from shenbi.gates.g4.context_composing import g4_context_composing
    from shenbi.gates.g4.faction_builder import g4_faction_builder
    from shenbi.gates.g4.foreshadowing_plant import g4_foreshadowing_plant
    from shenbi.gates.g4.foreshadowing_track import g4_foreshadowing_track
    from shenbi.gates.g4.genre_config import g4_genre_config
    from shenbi.gates.g4.length_normalizing import g4_length_normalizing
    from shenbi.gates.g4.location_builder import g4_location_builder
    from shenbi.gates.g4.pacing_design import g4_pacing_design
    from shenbi.gates.g4.plot_thread_weaver import g4_plot_thread_weaver
    from shenbi.gates.g4.power_system import g4_power_system
    from shenbi.gates.g4.relationship_map import g4_relationship_map
    from shenbi.gates.g4.review_arc_payoff import g4_review_arc_payoff
    from shenbi.gates.g4.review_resonance import g4_review_resonance
    from shenbi.gates.g4.state_settling import g4_state_settling
    from shenbi.gates.g4.story_architecture import g4_story_architecture
    from shenbi.gates.g4.style_polishing import g4_style_polishing
    from shenbi.gates.g4.volume_outlining import g4_volume_outlining
    from shenbi.gates.g4.worldbuilding import g4_worldbuilding
    from shenbi.gates.g4.book_spine_init import g4_book_spine_init
    from shenbi.gates.g4.memory_distill import g4_memory_distill
    from shenbi.gates.g4.score_arc import g4_score_arc
    from shenbi.gates.g4.score_volume import g4_score_volume
    from shenbi.gates.g4.score_stratum import g4_score_stratum
    from shenbi.gates.g4.escalation_review import g4_escalation_review
    from shenbi.gates.g4.chapter_revision import g4_chapter_revision
    from shenbi.gates.g4.decisions_validator import g4_decisions, make_composite_checker

    checkers = {
        "shenbi-anti-detect": g4_anti_detect,
        "shenbi-chapter-drafting": make_composite_checker(g4_chapter_drafting, g4_decisions),
        "shenbi-chapter-planning": make_composite_checker(g4_chapter_planning, g4_decisions),
        "shenbi-character-design": g4_character_design,
        "shenbi-context-composing": make_composite_checker(g4_context_composing, g4_decisions),
        "shenbi-faction-builder": g4_faction_builder,
        "shenbi-foreshadowing-plant": g4_foreshadowing_plant,
        "shenbi-foreshadowing-track": g4_foreshadowing_track,
        "shenbi-genre-config": g4_genre_config,
        "shenbi-length-normalizing": g4_length_normalizing,
        "shenbi-location-builder": g4_location_builder,
        "shenbi-pacing-design": g4_pacing_design,
        "shenbi-plot-thread-weaver": g4_plot_thread_weaver,
        "shenbi-power-system": g4_power_system,
        "shenbi-relationship-map": g4_relationship_map,
        "shenbi-review-arc-payoff": g4_review_arc_payoff,
        "shenbi-review-resonance": g4_review_resonance,
        "shenbi-state-settling": make_composite_checker(g4_state_settling, g4_decisions),
        "shenbi-story-architecture": g4_story_architecture,
        "shenbi-style-polishing": g4_style_polishing,
        "shenbi-volume-outlining": g4_volume_outlining,
        "shenbi-worldbuilding": g4_worldbuilding,
        "shenbi-book-spine-init": g4_book_spine_init,
        "shenbi-memory-distill": g4_memory_distill,
        "shenbi-score-arc": g4_score_arc,
        "shenbi-score-volume": g4_score_volume,
        "shenbi-score-stratum": g4_score_stratum,
        "shenbi-escalation-review": g4_escalation_review,
        # New: decisions-only (no existing dedicated checker)
        "shenbi-market-radar": g4_decisions,
        "shenbi-chapter-revision": make_composite_checker(g4_decisions, g4_chapter_revision),
        "shenbi-short-drafting": g4_decisions,
    }
    fn = checkers.get(skill_name)
    if fn:
        result = fn(file_paths, round_dir, project_dir, repo_root)
    else:
        # Generic fallback for skills without dedicated checkers
        result = g4_generic_generative(file_paths, round_dir, project_dir, repo_root)

    # Post-write integrity findings (spec 19 §3.6) — apply to every chapter.
    if project_dir:
        chapter_num = _chapter_number_from_paths(file_paths)
        if chapter_num is not None:
            pwi = g4_post_write_integrity(Path(project_dir), chapter=chapter_num)
            if pwi["checks"]:
                result = _merge_pwi_into_result(result, pwi)

    return result


def gate_G4_bughunt(file_paths: list[str]) -> str:
    """G4.b: Bug-hunt checks (delegates to generic checker)."""
    return g4_generic_bughunt(file_paths)


def gate_G4_clean(file_paths: list[str]) -> str:
    """G4.c: Clean checks (delegates to generic checker)."""
    return g4_generic_clean(file_paths)
