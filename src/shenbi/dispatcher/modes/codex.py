"""Codex CLI dispatch mode."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from shenbi.safe_write import safe_write

from shenbi.cli_utils import emit_json
from shenbi.exceptions import SubAgentProtocolError, SubAgentTimeoutError
from shenbi.logging import get_logger
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
    progress_path = round_dir / "progress.json"
    if progress_path.exists():
        loaded = json.loads(progress_path.read_text(encoding="utf-8"))
        progress: dict[str, object] = loaded if isinstance(loaded, dict) else {}
    else:
        progress = {}

    completed_obj = progress.get("completed_skill_names", [])
    completed = completed_obj if isinstance(completed_obj, list) else []
    if skill not in completed:
        completed.append(skill)
    progress["completed_skill_names"] = completed

    skills_obj = progress.get("skills", {})
    skills = skills_obj if isinstance(skills_obj, dict) else {}
    skill_entry_obj = skills.get(skill, {})
    skill_entry = skill_entry_obj if isinstance(skill_entry_obj, dict) else {}
    entry: dict[str, object] = {"score": score, "status": "done"}
    if output_files:
        entry["output_files"] = output_files
    skill_entry[test_type] = entry
    skills[skill] = skill_entry
    progress["skills"] = skills

    safe_write(progress_path, json.dumps(progress, indent=2, ensure_ascii=False))


def _record_collapse_check(
    round_dir: Path, skill: str, test_type: str, scores: dict[Any, Any]
) -> dict[str, object]:
    """Persist single-scorer collapse check next to the scores file (spec #31 T2a).

    Separate artifact (NOT a key inside scores-subagent.json): parse_scores_dict
    drops non-numeric keys with a WARN, so embedding would be noise. Scores from
    codex JSON carry str dimension keys — normalized to int here.
    """
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
    if dropped:
        # Mirrors parse_scores_dict's non_numeric_score_keys_dropped WARN.
        log.info(
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


def dispatch_codex(
    skill: str,
    test_type: str,
    round_dir: Path,
    prompt: str,
    agent_id: str,
    output_files: list[str] | None = None,
) -> int:
    """Dispatch via codex CLI."""
    if not prompt:
        raise SubAgentProtocolError("codex mode requires non-empty prompt")

    scores_file = round_dir / "t1-reports" / f"{skill}-{test_type}-scores-subagent.json"
    scores_file.parent.mkdir(parents=True, exist_ok=True)
    raw_out = scores_file.with_suffix(".raw")

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
        return result.returncode

    raw_text = raw_out.read_text(encoding="utf-8")
    match = re.search(r"\{[^{}]*\}", raw_text, re.DOTALL)
    if not match:
        log.error("codex_no_json", skill=skill, raw_output_preview=raw_text[:500])
        raise SubAgentProtocolError("no JSON object found in codex output")
    try:
        scores = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        log.error(
            "codex_invalid_json", skill=skill, error=str(e), raw_output_preview=raw_text[:500]
        )
        raise SubAgentProtocolError(f"invalid JSON from codex: {e}") from e

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
    _record_completion(round_dir, skill, test_type, final, output_files=output_files)
    emit_json(json.loads(result.stdout))
    return 0
