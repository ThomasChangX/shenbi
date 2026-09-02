"""Dispatcher executor: orchestrates gate checks + sub-agent dispatch.

PR-20 (P-1.E): Python translation of tests/dispatch-subagent.sh (203 lines).
Replaces shell script with typed, loggable Python.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from shenbi.audit._shared import derive_output_files
from shenbi.contracts import ContractError, load_contract
from shenbi.contracts import OutputKind
from shenbi.contracts.paths import (
    AmbiguousChapterError,
    PathContext,
    extract_chapter,
    parse_path_context,
    resolve_or_skip_ctx,
)
from shenbi.contracts.registry import bootstrap_registry
from shenbi.logging import get_logger
from shenbi.process_guard import run_subprocess_json

log = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = REPO_ROOT

# Cached set of truth files; lazily built from truth-files.yaml concepts.
_truth_files_cache: set[str] | None = None


def _truth_file_set() -> set[str]:
    """Files listed as kind='truth' in truth-files.yaml concepts.

    Both truth and chapter edits have OutputKind.ARTIFACT, so OutputKind cannot
    distinguish them; the distinction lives in truth-files.yaml (spec New-I).
    """
    global _truth_files_cache
    if _truth_files_cache is None:
        _truth_files_cache = {
            name for name, kind in bootstrap_registry().items() if kind == "truth"
        }
    return _truth_files_cache


_decisions_files_cache: set[str] | None = None


def _decisions_file_set() -> set[str]:
    """Files listed as kind='decisions' in truth-files.yaml concepts."""
    global _decisions_files_cache
    if _decisions_files_cache is None:
        _decisions_files_cache = {
            name for name, kind in bootstrap_registry().items() if kind == "decisions"
        }
    return _decisions_files_cache


def generate_agent_id(round_dir: Path, skill: str, test_type: str) -> str:
    """Generate unique agent ID for this dispatch."""
    return f"{round_dir.name}-{skill}-{test_type}-{uuid.uuid4().hex[:8]}"


def derive_file_type(skill: str) -> str:
    """Derive G2 FILE_TYPE from the contract layer (spec New-I).

    Join rule: load contract kind. REPORT -> report. ARTIFACT -> truth iff the
    skill writes/updates a file that truth-files.yaml lists as kind=truth, else
    chapter. EPHEMERAL (no persisted output) -> chapter default. This replaces
    the hardcoded skill-name sets that missed shenbi-foreshadowing-resolve.
    """
    try:
        c = load_contract(skill)
    except ContractError:
        return "chapter"
    kind = c["kind"]
    if kind == OutputKind.REPORT:
        return "report"
    if kind == OutputKind.EPHEMERAL:
        return "chapter"
    outputs = {*c["writes"], *c["updates"]}
    if outputs & _truth_file_set():
        return "truth"
    if outputs & _decisions_file_set():
        return "decisions"
    return "chapter"


def derive_input_files(
    skill: str,
    chapter: int | None = None,
    round_dir: Path | None = None,
    ctx: PathContext | None = None,
) -> list[str]:
    """Return the skill's contract reads, resolving placeholders (chapter or PathContext).
    When *chapter* is provided, N/NNN placeholders are resolved.
    Paths with unresolvable placeholders (genesis mode) are skipped via
    resolve_or_skip → None → filtered. When *round_dir* is provided,
    relative paths are made absolute.
    """
    try:
        paths = [
            rp
            for p in load_contract(skill)["reads"]
            if (rp := resolve_or_skip_ctx(p, chapter, ctx)) is not None
        ]
        if round_dir is not None:
            paths = [str((round_dir / p).resolve()) for p in paths]
        return paths
    except ContractError:
        return []


def run_g1(skill: str, inputs: list[str], round_dir: Path) -> dict[str, Any]:
    """Run G1 gate via shenbi-validate entry point."""
    inputs_json = json.dumps(inputs)
    # T1a/T6 (spec #38 F125 residual): guarded subprocess boundary.
    return run_subprocess_json(
        ["uv", "run", "shenbi-validate", "G1", skill, inputs_json, str(round_dir)]
    )


def run_g2(outputs: list[str], file_type: str, round_dir: Path) -> dict[str, Any]:
    """Run G2 gate via shenbi-validate entry point."""
    output_files = ",".join(outputs)
    # T1a/T6 (spec #38 F125 residual): guarded subprocess boundary.
    return run_subprocess_json(
        [
            "uv",
            "run",
            "shenbi-validate",
            "G2",
            output_files,
            file_type,
            str(round_dir),
            str(PROJECT_DIR),
        ]
    )


def detect_mode() -> str:
    """Detect available dispatch mode.

    Prefers codex CLI when available (for LLM-backed skill execution),
    falls back to internal mode for development/debugging.
    """
    import shutil

    if shutil.which("codex"):
        return "codex"
    return "internal"


def dispatch(skill: str, test_type: str, round_dir: Path, prompt: str) -> int:
    """Main dispatch entry point."""
    agent_id = generate_agent_id(round_dir, skill, test_type)
    log.info("dispatch_start", agent_id=agent_id, skill=skill, test_type=test_type)
    path_ctx = parse_path_context(prompt)
    # F257: the former `chapter=` kwarg had zero external callers; derive from prompt.
    chapter = (
        path_ctx.chapter if path_ctx is not None and isinstance(path_ctx.chapter, int) else None
    )
    if chapter is None:
        # F234 (spec #38): ambiguous multi-chapter prompts must not silently
        # route to the first match — fall back to no chapter + warn.
        try:
            chapter = extract_chapter(prompt, strict=True)
        except AmbiguousChapterError:
            log.warning("chapter_ambiguous_in_prompt", skill=skill)
            chapter = None
    file_type = derive_file_type(skill)
    input_files = derive_input_files(skill, chapter, round_dir, ctx=path_ctx)

    # Optionally skip reads marked as optional (ramp-up / late-produced files).
    skip_raw = os.environ.get("SHENBI_G1_SKIP_READS", "")
    if skip_raw:
        skip_patterns = [p.strip() for p in skip_raw.split(",") if p.strip()]
        if skip_patterns:
            from fnmatch import fnmatch

            filtered: list[str] = []
            for f in input_files:
                name = Path(f).name
                if any(fnmatch(name, pat) for pat in skip_patterns):
                    if not Path(f).exists():
                        matching = [p for p in skip_patterns if fnmatch(name, p)]
                        log.debug(
                            "g1_skip_optional_read",
                            file=f,
                            pattern=matching[0] if matching else "unknown",
                        )
                        continue  # skip: optional file not yet produced
                filtered.append(f)
            original_count = len(input_files)
            input_files = filtered
            log.info("g1_optional_reads_filtered", original=original_count, kept=len(input_files))

    g1 = run_g1(skill, input_files, round_dir)
    if g1.get("status") != "PASS":
        log.error("g1_failed", gate="G1", result=g1)
        return 1
    log.info("gate_passed", gate="G1")

    output_files = derive_output_files(skill, chapter, round_dir, ctx=path_ctx)
    is_pipeline = (round_dir / "pipeline-state.json").exists()

    mode = detect_mode()
    log.info("dispatch_mode", mode=mode)

    if mode == "codex":
        from shenbi.dispatcher.modes.codex import dispatch_codex

        # spec #31 T2b: pipeline rounds opt into dual scoring via
        # pipeline-state.json config.dual_scorer (default False, fail-open).
        dual = False
        if is_pipeline:
            try:
                state_data = json.loads((round_dir / "pipeline-state.json").read_text("utf-8"))
                dual = bool(state_data.get("config", {}).get("dual_scorer", False))
            except (json.JSONDecodeError, OSError):
                log.warning("dual_scorer_config_unreadable", round_dir=str(round_dir))
        rc = dispatch_codex(skill, test_type, round_dir, prompt, agent_id, output_files, dual=dual)
    else:
        from shenbi.dispatcher.modes.internal import dispatch_internal

        rc = dispatch_internal(skill, test_type, round_dir, prompt, agent_id)

    # F227: G2 runs AFTER execution. Validating outputs before the skill runs
    # failed every fresh round (the outputs did not exist yet). Pipeline mode
    # keeps skipping G2 here — outputs are validated by G4/G6 instead.
    if not is_pipeline and rc == 0 and output_files:
        g2 = run_g2(output_files, file_type, round_dir)
        if g2.get("status") != "PASS":
            log.error("g2_failed", gate="G2", result=g2)
            return 1
        log.info("gate_passed", gate="G2")
    elif is_pipeline:
        log.info("g2_skipped_pipeline", reason="pipeline mode — output validated by G4/G6")
    return rc


def _audit_watch_paths(
    skill: str, chapter: int | None = None, ctx: PathContext | None = None
) -> list[str]:
    """Audit watch surface: the skill contract writes+updates (project-relative)."""
    try:
        return derive_output_files(skill, chapter, ctx=ctx)
    except ContractError:
        return []


def dispatch_with_write_audit(skill: str, test_type: str, round_dir: Path, prompt: str) -> int:
    """Audited dispatch (pillar 4 Tier B topology) — legacy CLI route only.

    Covers ONLY dispatches that go through :func:`dispatch` above, i.e. the
    ``shenbi-dispatch`` CLI subprocess (T1 testing / legacy fallback). The
    production API/IDE routes live in ``pipeline.dispatch_helper`` and get
    the identical audit via its ``_with_write_audit`` wrapper (C32 R3/F518).

    pre snapshot(declared write surface) -> dispatch -> post snapshot -> audit ->
    record. Returns 0 = shippable; 2 = GATE_FAIL (write overreach or drift),
    blocked before tier advance. The write side uses FS snapshot diff, feasible
    for all dispatch modes incl. codex subprocesses; read provenance in a
    subprocess is a known blind spot. Snapshot root is PROJECT_DIR (framework
    repo root — F519); the API/IDE wrapper roots at the pipeline project dir
    where those routes actually write.
    """
    from shenbi.audit.record import record_audit_outcome
    from shenbi.audit.snapshot import snapshot_tree

    from shenbi.audit.write_audit import audit_writes

    path_ctx = parse_path_context(prompt)
    chapter = (
        path_ctx.chapter if path_ctx is not None and isinstance(path_ctx.chapter, int) else None
    )
    if chapter is None:
        # F234 (spec #38): ambiguous multi-chapter prompts must not silently
        # route to the first match — fall back to no chapter + warn.
        try:
            chapter = extract_chapter(prompt, strict=True)
        except AmbiguousChapterError:
            log.warning("chapter_ambiguous_in_prompt", skill=skill)
            chapter = None
    watch = _audit_watch_paths(skill, chapter, ctx=path_ctx)
    pre = snapshot_tree(PROJECT_DIR, watch)
    # Franklin Important: if dispatch() crashes mid-write, still run the post-snapshot
    # + audit so write overreach is caught even on failure paths.
    rc: int = -1
    dispatch_exc: BaseException | None = None
    try:
        rc = dispatch(skill, test_type, round_dir, prompt)
    except Exception as exc:
        # CRITICAL: log every exception from dispatch() before re-raising
        log.error(
            "dispatch_exception",
            skill=skill,
            test_type=test_type,
            exc_type=type(exc).__name__,
            exc_msg=str(exc),
            round_dir=str(round_dir),
        )
        dispatch_exc = exc
        rc = -1
    finally:
        # F517 (spec #38): the audit chain itself (snapshot/diff/record) must
        # not mask the original dispatch exception or crash the caller — a
        # broken chain is an infra error that fails the dispatch (rc=2) while
        # the original exception still propagates.
        try:
            post = snapshot_tree(PROJECT_DIR, watch)
            result = audit_writes(skill, pre, post, chapter=chapter, ctx=path_ctx)
            audit_ok = record_audit_outcome(round_dir, skill, result)
        except Exception as audit_exc:
            log.error(
                "write_audit_infra_error",
                skill=skill,
                exc_type=type(audit_exc).__name__,
                exc_msg=str(audit_exc),
            )
            rc = 2
            # Chain the audit failure to any earlier dispatch exception so the
            # original cause survives the double-crash path (audit-T6 I1).
            raise audit_exc from dispatch_exc
        if not audit_ok and rc == 0:
            rc = 2  # GATE_FAIL: write overreach or drift
    if dispatch_exc is not None:
        raise dispatch_exc
    return rc
