"""Codex CLI dispatch mode."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from shenbi.safe_write import safe_write

from shenbi.cli_utils import emit_json
from shenbi.exceptions import SubAgentProtocolError, SubAgentTimeoutError
from shenbi.logging import get_logger

log = get_logger(__name__)


def _record_completion(round_dir: Path, skill: str, test_type: str, score: float) -> None:
    """Record skill completion directly into progress.json.

    Replaces the historical ``shenbi-progress mark-done`` subprocess, which
    invoked an entry point never registered in pyproject.toml. Mirrors how
    gate logic (g_dispatch.py) reads ``completed_skill_names``.
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
    skill_entry[test_type] = {"score": score, "status": "done"}
    skills[skill] = skill_entry
    progress["skills"] = skills

    safe_write(progress_path, json.dumps(progress, indent=2, ensure_ascii=False))


def dispatch_codex(skill: str, test_type: str, round_dir: Path, prompt: str, agent_id: str) -> int:
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
    _record_completion(round_dir, skill, test_type, final)
    emit_json(json.loads(result.stdout))
    return 0
