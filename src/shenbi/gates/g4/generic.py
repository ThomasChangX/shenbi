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
        if p.is_dir():
            # Directory outputs (spec #6 R3): snapshot-family dirs require a
            # manifest-named entry (filename authority: snapshot-manage SKILL
            # contract); non-snapshot dirs (characters/) check existence +
            # content only. Pure read-only validation.
            try:
                entries = [e for e in p.iterdir() if e.is_file()]
            except OSError:
                mf.append(f"G4.gen.read_error:{fp_path}")
                continue
            if not entries:
                mf.append(f"G4.gen.dir_empty:{fp_path}")
                continue
            if "snapshot" in fp_path.replace("\\", "/").lower() and not any(
                "manifest" in e.name.lower() for e in entries
            ):
                mf.append(f"G4.gen.manifest_missing:{fp_path}")
                continue
            c.append(
                {
                    "id": f"G4.gen.dir.{Path(fp_path).name}",
                    "s": GateStatus.PASS,
                    "files": len(entries),
                }
            )
            continue
        if p.stat().st_size == 0:
            mf.append(f"G4.gen.empty:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
            mf.append(f"G4.gen.read_error:{fp_path}")
            continue
        if fp_path.endswith(".md"):
            if len(content.strip()) < 50:
                mf.append(f"G4.gen.too_short:{fp_path}")
            else:
                c.append(
                    {
                        "id": f"G4.gen.{Path(fp_path).name}",
                        "s": GateStatus.PASS,
                        "size": len(content),
                    }
                )
        elif fp_path.endswith(".json"):
            try:
                json.loads(content)
                c.append({"id": f"G4.gen.{Path(fp_path).name}", "s": GateStatus.PASS})
            except json.JSONDecodeError:
                mf.append(f"G4.gen.invalid_json:{fp_path}")
        else:
            c.append(
                {"id": f"G4.gen.{Path(fp_path).name}", "s": GateStatus.PASS, "size": len(content)}
            )
    if not fps:
        c.append({"id": "G4.gen", "s": GateStatus.SKIP, "r": "no files"})
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
        mf_before = len(mf)  # per-file PASS scoping (Copilot PR#103 review)
        p = resolve_input_path(fp_path, rd)
        if not p.exists():
            mf.append(f"G4.bh.not_found:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
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
        if len(mf) == mf_before:
            c.append({"id": f"G4.bh.{Path(fp_path).name}", "s": GateStatus.PASS})
    if not fps:
        c.append({"id": "G4.bh", "s": GateStatus.SKIP, "r": "no files"})
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
        mf_before = len(mf)  # per-file PASS scoping (Copilot PR#103 review)
        p = resolve_input_path(fp_path, rd)
        if not p.exists():
            mf.append(f"G4.cl.not_found:{fp_path}")
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 (C13 allowlist: intentional broad catch, structured handling per spec #39 T5)
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
            # F405 (spec #39 T10): check EVERY occurrence — the old
            # first-index lookup mis-judged texts whose first mention was
            # negated but a later one was not (and vice versa). An
            # unnegated occurrence anywhere makes it a real suggestion.
            pat = re.compile(re.escape(m), re.IGNORECASE)
            for occ in pat.finditer(content):
                before = content[max(0, occ.start() - 15) : occ.start()]
                if not re.search(r"无|不|no\s|not\s|without|没", before, re.IGNORECASE):
                    real_suggestions.append(m)
                    break
        if real_suggestions:
            mf.append(f"G4.cl.has_suggestions:{fp_path}:{real_suggestions}")
        if len(mf) == mf_before:
            c.append({"id": f"G4.cl.{Path(fp_path).name}", "s": GateStatus.PASS})
    if not fps:
        c.append({"id": "G4.cl", "s": GateStatus.SKIP, "r": "no files"})
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


def _revalidate_finding(project_dir: Path, file_field: str, finding: str) -> bool:
    """Check a persisted post-write finding against current disk state.

    Probe2 escalation-1 (2026-09-30): findings are append-only and were
    consumed verbatim — a transient finding from a truncated staging write
    (later rewritten complete and settled) permanently poisoned every later
    G4 composite for that chapter. Revalidation locates the file (raw path,
    then the de-staged twin for settled staging writes) and re-runs the
    mapped check; a finding survives only when it still reproduces. Read-side
    only — the findings file keeps its append-only log semantics.

    Unknown finding prefixes cannot be re-mapped; they are kept
    conservatively (fail-closed rather than pardoning a future class).
    """
    target: Path | None = None
    raw = project_dir / file_field
    if raw.exists():
        target = raw
    elif file_field.startswith("staging/"):
        destaged = project_dir / file_field[len("staging/") :]
        if destaged.exists():
            target = destaged
    if target is None:
        log.warning("pwi_finding_stale_file_gone", finding=finding, file=file_field)
        return False

    from shenbi.pipeline.llm_output_integrity import (
        check_audit_completeness,
        check_audit_line_refs,
        check_markdown_fence_balance,
        check_prose_leakage,
    )

    if finding.startswith("G4.ac."):
        emitted = check_audit_completeness(target)
    elif finding.startswith(("G4.pi.model_leakage", "G4.pi.unfinished_ending")):
        emitted = check_prose_leakage(target)
    elif finding.startswith("G4.pi.fence_imbalance"):
        emitted = check_markdown_fence_balance(target)
    elif finding.startswith("G4.av."):
        m = re.search(r"chapter-(\d+)", target.name)
        chapter_path = project_dir / "chapters" / f"chapter-{m.group(1)}.md" if m else None
        if chapter_path is None or not chapter_path.exists():
            log.warning("pwi_finding_stale_chapter_gone", finding=finding, file=file_field)
            return False
        emitted = check_audit_line_refs(target, chapter_path)
    else:
        return True

    token = finding.split(" — ", maxsplit=1)[0]
    if any(e.split(" — ", maxsplit=1)[0] == token for e in emitted):
        return True
    log.warning("pwi_finding_stale_not_reproduced", finding=finding, file=file_field)
    return False


def g4_post_write_integrity(project_dir: Path, *, chapter: int) -> dict[str, Any]:
    """G4 checker: consume persisted post-write integrity findings.

    Reads ``audits/.integrity-findings-<chapter>.jsonl`` (written by
    ``_write_parsed_outputs``) and maps each finding to a G4 check with the
    severity from spec §3.6. Findings that no longer reproduce against
    current disk state are dropped (see :func:`_revalidate_finding`). Returns
    a dict ``{"status", "checks", "must_fix"}`` — reproduced FAIL-class
    findings ride ``must_fix`` so retry feedback can cite them (probe2
    escalation-1: an FAIL-with-empty-must_fix composite degrades into the
    ``G4.generic_failure`` conservative default, which no retry can fix).
    """
    findings_path = project_dir / "audits" / f".integrity-findings-{chapter}.jsonl"
    checks: list[dict[str, Any]] = []
    must_fix: list[str] = []
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
            file_field = str(entry.get("file", ""))
            if not _revalidate_finding(project_dir, file_field, finding):
                continue
            is_fail = any(finding.startswith(p) for p in _POST_WRITE_FAIL_PREFIXES)
            # fence_imbalance is the only WARN.
            if finding.startswith("G4.pi.fence_imbalance"):
                is_fail = False
            check_id = finding.split(":", maxsplit=1)[0] if ":" in finding else finding
            checks.append(
                {"id": check_id, "s": GateStatus.FAIL if is_fail else GateStatus.WARN, "r": finding}
            )
            if is_fail:
                must_fix.append(finding)
            has_fail = has_fail or is_fail
            has_warn = has_warn or (not is_fail)
    status = GateStatus.FAIL if has_fail else (GateStatus.WARN if has_warn else GateStatus.PASS)
    return {"status": status, "checks": checks, "must_fix": must_fix}


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

    # Reproduced FAIL-class findings must ride must_fix (probe2 escalation-1):
    # an FAIL composite with empty must_fix degrades into the
    # G4.generic_failure conservative default, which no retry can target.
    result_data.setdefault("must_fix", [])
    if isinstance(result_data["must_fix"], list):
        result_data["must_fix"].extend(pwi.get("must_fix", []))

    # Elevate status: FAIL > WARN > PASS
    current = result_data.get("status", GateStatus.PASS)
    pwi_status = pwi["status"]
    if pwi_status == GateStatus.FAIL or current == GateStatus.FAIL:
        result_data["status"] = GateStatus.FAIL
    elif pwi_status == GateStatus.WARN and current != GateStatus.FAIL:
        result_data["status"] = GateStatus.WARN

    return json.dumps(result_data, indent=2, ensure_ascii=False)


# Declarative wiring facts (spec #60 T0a-2 / F1017): make_composite_checker
# closures are not introspectable, so the decisions-wired roster is declared here
# and asserted against actual construction inside build_checkers().
G4_DECISIONS_WIRED: frozenset[str] = frozenset(
    {
        "shenbi-chapter-drafting",
        "shenbi-chapter-planning",
        "shenbi-context-composing",
        "shenbi-genre-config",
        "shenbi-chapter-revision",
        "shenbi-short-drafting",
        "shenbi-state-settling",
        "shenbi-market-radar",
    }
)

# The full checker roster: 27 static keys below + 3 score-* keys registered
# dynamically by register_score_checkers(). String-only so lint tooling (and
# g5) can import it without pulling the per-skill checker modules.
G4_CHECKER_KEYS: frozenset[str] = frozenset(
    {
        "shenbi-anti-detect",
        "shenbi-chapter-drafting",
        "shenbi-chapter-planning",
        "shenbi-character-design",
        "shenbi-context-composing",
        "shenbi-faction-builder",
        "shenbi-foreshadowing-lifecycle",
        "shenbi-genre-config",
        "shenbi-length-normalizing",
        "shenbi-location-builder",
        "shenbi-pacing-design",
        "shenbi-plot-thread-weaver",
        "shenbi-power-system",
        "shenbi-relationship-map",
        "shenbi-review-arc-payoff",
        "shenbi-review-resonance",
        "shenbi-state-settling",
        "shenbi-story-architecture",
        "shenbi-style-polishing",
        "shenbi-volume-outlining",
        "shenbi-worldbuilding",
        "shenbi-book-spine-init",
        "shenbi-memory-distill",
        "shenbi-escalation-review",
        "shenbi-market-radar",
        "shenbi-chapter-revision",
        "shenbi-short-drafting",
        "shenbi-score-arc",
        "shenbi-score-stratum",
        "shenbi-score-volume",
    }
)


def build_checkers() -> dict[str, Any]:
    """Construct the per-skill G4 checker registry.

    Late imports are deliberate (circular-import avoidance at module load;
    see cli.py T1604 note) and stay inside this factory. The declarative
    G4_DECISIONS_WIRED / G4_CHECKER_KEYS frozensets are asserted against the
    actual construction so they cannot silently drift (F1017 recurrence guard).
    """
    from shenbi.gates.g4.anti_detect import g4_anti_detect
    from shenbi.gates.g4.book_spine_init import g4_book_spine_init
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting
    from shenbi.gates.g4.chapter_planning import g4_chapter_planning
    from shenbi.gates.g4.chapter_revision import g4_chapter_revision
    from shenbi.gates.g4.character_design import g4_character_design
    from shenbi.gates.g4.context_composing import g4_context_composing
    from shenbi.gates.g4.decisions_validator import g4_decisions, make_composite_checker
    from shenbi.gates.g4.escalation_review import g4_escalation_review
    from shenbi.gates.g4.faction_builder import g4_faction_builder
    from shenbi.gates.g4.foreshadowing_lifecycle import g4_foreshadowing_lifecycle
    from shenbi.gates.g4.genre_config import g4_genre_config
    from shenbi.gates.g4.length_normalizing import g4_length_normalizing
    from shenbi.gates.g4.location_builder import g4_location_builder
    from shenbi.gates.g4.memory_distill import g4_memory_distill
    from shenbi.gates.g4.pacing_design import g4_pacing_design
    from shenbi.gates.g4.plot_thread_weaver import g4_plot_thread_weaver
    from shenbi.gates.g4.power_system import g4_power_system
    from shenbi.gates.g4.relationship_map import g4_relationship_map
    from shenbi.gates.g4.review_arc_payoff import g4_review_arc_payoff
    from shenbi.gates.g4.review_resonance import g4_review_resonance
    from shenbi.gates.g4.scoring_sections import register_score_checkers
    from shenbi.gates.g4.state_settling import g4_state_settling
    from shenbi.gates.g4.story_architecture import g4_story_architecture
    from shenbi.gates.g4.style_polishing import g4_style_polishing
    from shenbi.gates.g4.volume_outlining import g4_volume_outlining
    from shenbi.gates.g4.worldbuilding import g4_worldbuilding

    wired: set[str] = set()

    def comp(base: Any, name: str, pred: Any = None) -> Any:
        wired.add(name)
        if pred is None:
            return make_composite_checker(base, g4_decisions)
        return make_composite_checker(base, g4_decisions, pred)

    checkers: dict[str, Any] = {
        "shenbi-anti-detect": g4_anti_detect,
        "shenbi-chapter-drafting": comp(g4_chapter_drafting, "shenbi-chapter-drafting"),
        "shenbi-chapter-planning": comp(g4_chapter_planning, "shenbi-chapter-planning"),
        "shenbi-character-design": g4_character_design,
        "shenbi-context-composing": comp(g4_context_composing, "shenbi-context-composing"),
        "shenbi-faction-builder": g4_faction_builder,
        "shenbi-foreshadowing-lifecycle": g4_foreshadowing_lifecycle,
        "shenbi-genre-config": comp(g4_genre_config, "shenbi-genre-config"),
        "shenbi-length-normalizing": g4_length_normalizing,
        "shenbi-location-builder": g4_location_builder,
        "shenbi-pacing-design": g4_pacing_design,
        "shenbi-plot-thread-weaver": g4_plot_thread_weaver,
        "shenbi-power-system": g4_power_system,
        "shenbi-relationship-map": g4_relationship_map,
        "shenbi-review-arc-payoff": g4_review_arc_payoff,
        "shenbi-review-resonance": g4_review_resonance,
        "shenbi-state-settling": comp(g4_state_settling, "shenbi-state-settling"),
        "shenbi-story-architecture": g4_story_architecture,
        "shenbi-style-polishing": g4_style_polishing,
        "shenbi-volume-outlining": g4_volume_outlining,
        "shenbi-worldbuilding": g4_worldbuilding,
        "shenbi-book-spine-init": g4_book_spine_init,
        "shenbi-memory-distill": g4_memory_distill,
        "shenbi-escalation-review": g4_escalation_review,
        # New: decisions-only (no existing dedicated checker)
        "shenbi-market-radar": g4_decisions,
        "shenbi-chapter-revision": comp(
            g4_chapter_revision,
            "shenbi-chapter-revision",
            # revision sidecars carry stricter G4.rev semantics than DecisionsDoc
            # (empty_adjustments_no_skip / >=20-char rationale) — route them to
            # the dedicated checker, not the generic decisions slot.
            lambda fp: fp.endswith("-decisions.json") and "revision" not in Path(fp).name,
        ),
        "shenbi-short-drafting": g4_decisions,
    }
    wired.add("shenbi-market-radar")  # bare g4_decisions assignment — wired too
    wired.add("shenbi-short-drafting")  # bare g4_decisions assignment — wired too
    # C37 F427: three copy-paste score checkers unified
    register_score_checkers(checkers)
    assert wired == set(G4_DECISIONS_WIRED), (
        f"G4_DECISIONS_WIRED drifted from construction: {wired ^ set(G4_DECISIONS_WIRED)}"
    )
    assert set(checkers) == set(G4_CHECKER_KEYS), (
        f"G4_CHECKER_KEYS drifted from construction: {set(checkers) ^ set(G4_CHECKER_KEYS)}"
    )
    return checkers


#: batch #15 #33: genesis content producers whose outputs must reference
#: years via world/story_bible.md 世界史时间线 anchor NAMES (or relative
#: phrasing), never raw absolute years. Derived from GENESIS_STEPS minus the
#: non-narrative steps (genre-config / style-learning / anchor-curate /
#: foundation-review). Kept as a literal frozenset so the lint face stays
#: import-cheap; tests reconcile it against GENESIS_STEPS.
_YEAR_ANCHOR_SKILLS: frozenset[str] = frozenset(
    {
        "shenbi-worldbuilding",
        "shenbi-character-design",
        "shenbi-story-architecture",
        "shenbi-faction-builder",
        "shenbi-volume-outlining",
        "shenbi-pacing-design",
        "shenbi-plot-thread-weaver",
        "shenbi-foreshadowing-lifecycle",
        "shenbi-power-system",
        "shenbi-location-builder",
        "shenbi-relationship-map",
        "shenbi-book-spine-init",
        "shenbi-intent-management",
    }
)


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

    checkers = build_checkers()

    fn = checkers.get(skill_name)
    result: str
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

    # batch #15 #33: year-anchor single-source scan for the 13 genesis
    # producers. Outline files' projections are FLAGGED (WARN); every other
    # producer output with a raw absolute year FAILS — probe15's four-layer
    # mutually-exclusive year numbers must never re-form.
    if skill_name in _YEAR_ANCHOR_SKILLS:
        must_fix: list[str] = []
        warns: list[dict[str, Any]] = []
        for fp in file_paths:
            p = Path(fp)
            if not p.exists():
                continue
            from shenbi.pipeline.llm_output_integrity import check_year_anchors

            for finding in check_year_anchors(p):
                if "outline" in p.parts or (p.suffix == ".md" and "outline" in str(p)):
                    warns.append(
                        {"id": "G4.ys.outline_projection", "s": GateStatus.WARN, "f": finding}
                    )
                else:
                    must_fix.append(finding)
        if must_fix or warns:
            ys = {
                "status": GateStatus.FAIL if must_fix else GateStatus.WARN,
                "checks": warns,
                "must_fix": must_fix,
            }
            result = _merge_pwi_into_result(result, ys)

    return result


def gate_G4_bughunt(
    file_paths: list[str],
    round_dir: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """G4.b: Bug-hunt checks (delegates to generic checker)."""
    # spec #48 C34 (F457): rd threaded so relative paths resolve instead of
    # raising bare ValueError.
    return g4_generic_bughunt(file_paths, round_dir, project_dir, repo_root)


def gate_G4_clean(
    file_paths: list[str],
    round_dir: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """G4.c: Clean checks (delegates to generic checker)."""
    return g4_generic_clean(file_paths, round_dir, project_dir, repo_root)
