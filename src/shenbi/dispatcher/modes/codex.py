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


def dispatch_codex(skill: str, test_type: str, round_dir: Path, prompt: str, agent_id: str) -> int:
    """Dispatch via codex CLI."""
    if not prompt:
        raise SubAgentProtocolError("codex mode requires non-empty prompt")

    scores_file = round_dir / "t1-reports" / f"{skill}-{test_type}-scores-subagent.json"
    scores_file.parent.mkdir(parents=True, exist_ok=True)
    raw_out = scores_file.with_suffix(".raw")

    try:
        result = subprocess.run(
            ["codex", "exec", "-C", str(Path.cwd()), "-o", str(raw_out), prompt],
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

    rubric_path = Path(os.environ.get("RUBRIC", f"tests/tiers/t1-skill/{skill}/rubric.md"))
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
    subprocess.run(
        ["uv", "run", "shenbi-progress", "mark-done", str(round_dir), skill, test_type, str(final)],
        check=True,
    )
    emit_json(json.loads(result.stdout))
    return 0
