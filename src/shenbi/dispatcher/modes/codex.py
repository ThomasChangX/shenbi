"""Codex CLI dispatch mode."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from shenbi.safe_write import locked_transact, safe_write

from shenbi.cli_utils import emit_json
from shenbi.exceptions import ShenbiError, SubAgentProtocolError, SubAgentTimeoutError
from shenbi.logging import get_logger
from shenbi.status import SkillProgressStatus
from shenbi.orchestration.scoring_bridge import check_single_scorer_collapse

log = get_logger(__name__)


def _record_completion(
    round_dir: Path,
    skill: str,
    test_type: str,
    score: float,
    output_files: list[str] | None = None,
) -> None:
    """Record skill completion directly into progress.json.

    Replaces the historical ``shenbi-progress mark-done`` subprocess, which
    invoked an entry point never registered in pyproject.toml. Mirrors how
    gate logic (g_dispatch.py) reads ``completed_skill_names``.

    ``output_files`` (F444) records the skill's produced files at the
    test_type layer so G3.3 can re-run G2 on them.
    """

    def _mutate(progress: dict[str, object]) -> dict[str, object]:
        completed_obj = progress.get("completed_skill_names", [])
        completed = completed_obj if isinstance(completed_obj, list) else []
        if skill not in completed:
            completed.append(skill)
        progress["completed_skill_names"] = completed

        skills_obj = progress.get("skills", {})
        skills = skills_obj if isinstance(skills_obj, dict) else {}
        skill_entry_obj = skills.get(skill, {})
        skill_entry = skill_entry_obj if isinstance(skill_entry_obj, dict) else {}
        entry: dict[str, object] = {"score": score, "status": SkillProgressStatus.DONE}
        if output_files:
            entry["output_files"] = output_files
        skill_entry[test_type] = entry
        skills[skill] = skill_entry
        progress["skills"] = skills
        return progress

    progress_path = round_dir / "progress.json"
    # spec #37 F206: the whole read-modify-write runs under the directory
    # lock — plain safe_write left the read outside the critical section.
    locked_transact(progress_path, _mutate)


def _normalize_scores(scores: dict[Any, Any]) -> tuple[dict[int, float], list[str]]:
    """str→int dimension keys, numeric-only values (bool exempt). Returns (normalized, dropped)."""
    normalized: dict[int, float] = {}
    dropped: list[str] = []
    for k, v in scores.items():
        try:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                normalized[int(k)] = float(v)
            else:
                dropped.append(str(k))
        except (TypeError, ValueError):
            dropped.append(str(k))
    return normalized, dropped


def _record_collapse_check(
    round_dir: Path, skill: str, test_type: str, scores: dict[Any, Any]
) -> dict[str, object]:
    """Persist single-scorer collapse check next to the scores file (spec #31 T2a).

    Separate artifact (NOT a key inside scores-subagent.json): parse_scores_dict
    drops non-numeric keys with a WARN, so embedding would be noise. Scores from
    codex JSON carry str dimension keys — normalized to int here.
    """
    normalized, dropped = _normalize_scores(scores)
    if dropped:
        # Mirrors parse_scores_dict's non_numeric_score_keys_dropped WARN
        # (same severity: data-loss signal, not debug noise).
        log.warning(
            "collapse_check_non_numeric_dropped", skill=skill, test_type=test_type, dropped=dropped
        )
    result = check_single_scorer_collapse(normalized)
    out = round_dir / "t1-reports" / f"{skill}-{test_type}-collapse-check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    safe_write(out, json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("collapse_suspected"):
        log.warning(
            "score_collapse_suspected", skill=skill, test_type=test_type, signals=result["signals"]
        )
    return result


def _codex_exec_scores(round_dir: Path, prompt: str, out_file: Path, skill: str) -> dict[str, Any]:
    """Run one codex exec and extract the first JSON object as scores.

    Shared by the primary scoring dispatch and the opt-in dual-scorer second
    dispatch (spec #31 T2b).
    """
    out_file.parent.mkdir(parents=True, exist_ok=True)
    raw_out = out_file.with_suffix(".raw")

    try:
        result = subprocess.run(
            ["codex", "exec", "-C", str(round_dir), "-o", str(raw_out), prompt],
            timeout=600,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as e:
        raise SubAgentTimeoutError("codex exec timed out after 600s") from e

    if result.returncode != 0:
        log.error("codex_failed", rc=result.returncode, stderr=result.stderr)
        raise SubAgentProtocolError(f"codex exec failed with rc={result.returncode}")

    raw_text = raw_out.read_text(encoding="utf-8")
    try:
        scores: dict[str, Any] = _extract_json_object(raw_text)
    except SubAgentProtocolError:
        log.error("codex_no_json", skill=skill, raw_output_preview=raw_text[:500])
        raise
    return scores


def _extract_json_object(text: str) -> dict[str, Any]:
    r"""Extract the scored JSON object from raw codex output (F203, spec #38).

    Old behavior: ``re.search(r"\{[^{}]*\}")`` grabbed the innermost flat
    object — nested ``{"scores": {...}}`` payloads lost their outer envelope.
    Now every ``{`` position is tried with raw_decode; candidates containing
    nested dict values win over flat ones; multiple equally-flat candidates
    are ambiguous and rejected rather than first-matched.
    """
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            candidates.append(obj)
    if not candidates:
        raise SubAgentProtocolError("no JSON object found in codex output")
    nested = [c for c in candidates if any(isinstance(v, dict) for v in c.values())]
    if nested:
        # Prefer the outermost envelope among nested candidates (longest source
        # span proxy: the one containing the most keys).
        return max(nested, key=len)
    if len(candidates) > 1:
        raise SubAgentProtocolError("ambiguous JSON candidates in codex output")
    return candidates[0]


def _run_dual_scorer_check(
    round_dir: Path, skill: str, test_type: str, prompt: str, scores: dict[str, Any]
) -> dict[str, Any] | None:
    """Opt-in dual-scorer agreement check (spec #31 T2b, F114/F506).

    Second independent codex dispatch → validate_dual_scorer comparison →
    needs_arbitration writes a G3-arb record into the pipeline manifest and
    WARNs. Disputes deliberately do NOT route through escalation_bridge:
    check_escalation is cross-round resonance-slope detection, a different
    mechanism (stage-3 review C2). The second dispatch reuses the identical
    prompt — independence here means a second sampling of the same scoring
    task (agreement probe), not an adversarial second opinion.
    """
    from shenbi.orchestration.scoring_bridge import validate_dual_scorer

    second_file = round_dir / "t1-reports" / f"{skill}-{test_type}-scores-subagent-2.json"
    try:
        scores2 = _codex_exec_scores(round_dir, prompt, second_file, skill)
    except (SubAgentProtocolError, SubAgentTimeoutError) as e:
        # Second scorer is an enhancement, not a gate: log and skip.
        log.warning("dual_scorer_second_dispatch_failed", skill=skill, error=str(e))
        return None
    safe_write(second_file, json.dumps(scores2))

    norm_a, _dropped_a = _normalize_scores(scores)
    norm_b, _dropped_b = _normalize_scores(scores2)

    agreement = validate_dual_scorer(norm_a, norm_b)
    if agreement.get("needs_arbitration"):
        from shenbi.gates.gate_manifest import record_gate_result

        try:
            record_gate_result(
                gate_manifest_dir=round_dir,
                phase="t1",
                chapter=0,
                skill=skill,
                gate="G3-arb",
                result=agreement,
            )
        except ShenbiError:
            # spec #37 F416: manifest corruption is fail-loud — envelope
            # errors propagate; only transient failures are best-effort.
            raise
        except Exception:
            # Manifest write failure must not crash dispatch — the dual check
            # is an enhancement, not a gate (audit-T4 M1).
            log.warning("dual_scorer_manifest_write_failed", skill=skill, exc_info=True)
        log.warning(
            "dual_scorer_dispute",
            skill=skill,
            test_type=test_type,
            disputed_dimensions=agreement.get("disputed_dimensions"),
            max_diff=agreement.get("max_diff"),
        )
    return agreement


def dispatch_codex(
    skill: str,
    test_type: str,
    round_dir: Path,
    prompt: str,
    agent_id: str,
    output_files: list[str] | None = None,
    dual: bool = False,
) -> int:
    """Dispatch via codex CLI."""
    if not prompt:
        raise SubAgentProtocolError("codex mode requires non-empty prompt")

    scores_file = round_dir / "t1-reports" / f"{skill}-{test_type}-scores-subagent.json"
    try:
        scores = _codex_exec_scores(round_dir, prompt, scores_file, skill)
    except SubAgentTimeoutError:
        raise
    except SubAgentProtocolError as e:
        # Historical behavior: codex exec failure logs and returns non-zero
        # (callers treat rc as pass/fail only; the exact rc is not consumed).
        log.error("codex_dispatch_failed", skill=skill, error=str(e))
        return 1

    safe_write(scores_file, json.dumps(scores))

    # spec #31 T2a (F114): deterministic collapse check on every independent
    # scoring dispatch — first production consumer of scoring_bridge.
    _record_collapse_check(round_dir, skill, test_type, scores)

    # Repo-root-relative (the only CWD-dependent path left in the dispatcher).
    # parents[4]: modes -> dispatcher -> shenbi -> src -> <repo root>.
    repo_root = Path(__file__).resolve().parents[4]
    rubric_path = Path(
        os.environ.get("RUBRIC", str(repo_root / f"tests/tiers/t1-skill/{skill}/rubric.md"))
    )
    result = subprocess.run(
        [
            "uv",
            "run",
            "shenbi-score",
            str(rubric_path),
            str(scores_file),
            "--test-type",
            test_type,
            "--round-dir",
            str(round_dir),
            "--subagent",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return result.returncode

    final = json.loads(result.stdout).get("final_score", 0)

    # spec #31 T2b: opt-in dual-scorer agreement check (default OFF).
    env_dual = os.environ.get("SHENBI_DUAL_SCORER") == "1"
    if dual or env_dual:
        log.info(
            "dual_scorer_enabled", skill=skill, source="env" if env_dual and not dual else "config"
        )
        _run_dual_scorer_check(round_dir, skill, test_type, prompt, scores)

    _record_completion(round_dir, skill, test_type, final, output_files=output_files)
    emit_json(json.loads(result.stdout))
    return 0
