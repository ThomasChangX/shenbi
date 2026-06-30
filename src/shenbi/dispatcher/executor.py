"""Dispatcher executor: orchestrates gate checks + sub-agent dispatch.

PR-20 (P-1.E): Python translation of tests/dispatch-subagent.sh (203 lines).
Replaces shell script with typed, loggable Python.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from shenbi.contracts import ContractError, load_contract
from shenbi.contracts import OutputKind
from shenbi.contracts.registry import bootstrap_registry
from shenbi.logging import get_logger

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
    return "chapter"


def derive_input_files(skill: str) -> list[str]:
    """Return the skill's contract reads via the single loader."""
    try:
        return list(load_contract(skill)["reads"])
    except ContractError:
        # A skill outside the contract system (e.g. a meta skill) has no inputs.
        return []


def derive_output_files(skill: str) -> list[str]:
    """Return the skill's contract writes + updates via the single loader."""
    try:
        c = load_contract(skill)
        return [*c["writes"], *c["updates"]]
    except ContractError:
        return []


def run_g1(skill: str, inputs: list[str], round_dir: Path) -> dict[str, Any]:
    """Run G1 gate via shenbi-validate entry point."""
    inputs_json = json.dumps(inputs)
    result = subprocess.run(
        ["uv", "run", "shenbi-validate", "G1", skill, inputs_json, str(round_dir)],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def run_g2(outputs: list[str], file_type: str, round_dir: Path) -> dict[str, Any]:
    """Run G2 gate via shenbi-validate entry point."""
    output_files = ",".join(outputs)
    result = subprocess.run(
        [
            "uv",
            "run",
            "shenbi-validate",
            "G2",
            output_files,
            file_type,
            str(round_dir),
            str(PROJECT_DIR),
        ],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def detect_mode() -> str:
    """Detect dispatch mode (codex, codex-api, or internal)."""
    if shutil.which("codex"):
        return "codex"
    if os.environ.get("CODEX_API_KEY"):
        return "codex-api"
    return "internal"


def dispatch(skill: str, test_type: str, round_dir: Path, prompt: str) -> int:
    """Main dispatch entry point."""
    agent_id = generate_agent_id(round_dir, skill, test_type)
    log.info("dispatch_start", agent_id=agent_id, skill=skill, test_type=test_type)

    file_type = derive_file_type(skill)
    input_files = derive_input_files(skill)

    g1 = run_g1(skill, input_files, round_dir)
    if g1.get("status") != "PASS":
        log.error("g1_failed", gate="G1", result=g1)
        return 1
    log.info("gate_passed", gate="G1")

    output_files = derive_output_files(skill)
    if output_files:
        g2 = run_g2(output_files, file_type, round_dir)
        if g2.get("status") != "PASS":
            log.error("g2_failed", gate="G2", result=g2)
            return 1
        log.info("gate_passed", gate="G2")

    mode = detect_mode()
    log.info("dispatch_mode", mode=mode)

    if mode == "codex":
        from shenbi.dispatcher.modes.codex import dispatch_codex

        return dispatch_codex(skill, test_type, round_dir, prompt, agent_id)
    if mode == "codex-api":
        from shenbi.dispatcher.modes.codex_api import dispatch_codex_api

        return dispatch_codex_api(skill, test_type, round_dir, prompt, agent_id)
    from shenbi.dispatcher.modes.internal import dispatch_internal

    return dispatch_internal(skill, test_type, round_dir, prompt, agent_id)


def _audit_watch_paths(skill: str) -> list[str]:
    """Audit watch surface: the skill contract writes+updates (project-relative)."""
    try:
        return derive_output_files(skill)
    except ContractError:
        return []


def dispatch_with_write_audit(skill: str, test_type: str, round_dir: Path, prompt: str) -> int:
    """Audited dispatch (pillar 4 Tier B topology).

    pre snapshot(declared write surface) -> dispatch -> post snapshot -> audit ->
    record. Returns 0 = shippable; 2 = GATE_FAIL (write overreach or drift),
    blocked before tier advance. The write side uses FS snapshot diff, feasible
    for all dispatch modes incl. codex subprocesses; read provenance in a
    subprocess is a known blind spot.
    """
    from shenbi.audit.record import record_audit_outcome
    from shenbi.audit.snapshot import snapshot_tree
    from shenbi.audit.write_audit import audit_writes

    watch = _audit_watch_paths(skill)
    pre = snapshot_tree(PROJECT_DIR, watch)
    # Franklin Important: if dispatch() crashes mid-write, still run the post-snapshot
    # + audit so write overreach is caught even on failure paths.
    rc: int
    dispatch_exc: BaseException | None = None
    try:
        rc = dispatch(skill, test_type, round_dir, prompt)
    except Exception as exc:
        dispatch_exc = exc
        rc = -1
    finally:
        post = snapshot_tree(PROJECT_DIR, watch)
        result = audit_writes(skill, pre, post)
        ok = record_audit_outcome(round_dir, skill, result)
    if dispatch_exc is not None:
        raise dispatch_exc
    return rc if ok else 2
