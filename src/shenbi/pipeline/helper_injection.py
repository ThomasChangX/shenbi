"""Pre-dispatch helper precompute injection (spec #33 T1a).

Deterministic statistics helpers (compute_stats etc.) are wired so the
LLM receives precomputed values instead of recomputing them by hand —
or, on the API dispatch route, instead of receiving a dead ``python -m``
instruction it cannot execute at all.

Injection happens at the ``_build_skill_prompt`` seam (same layer as
plan_skeleton / review_checklist injection). Per-skill rollback: list a
skill under the top-level ``helper_injection_disabled`` key in
executor_config.toml to fall back to the pure-prompt path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from shenbi.pipeline.dispatch_helper import load_executor_config
from shenbi.skill_utils.style_learning.compute_stats import compute_all_stats

log = structlog.get_logger(__name__)

#: Hard cap for the injected JSON block. The block is prepended after the
#: dispatcher's total input budget is applied, so it must guard its own size
#: (spec #33 plan: injected block is NOT covered by _INPUT_MAX_CHARS_TOTAL).
_MAX_BLOCK_CHARS = 8 * 1024

#: Upper bound on chapter files read per dispatch (cost containment, spec risk).
_MAX_CHAPTERS = 10


def _helper_injection_disabled() -> frozenset[str]:
    """Skills opted out of helper injection via executor_config.toml."""
    raw = load_executor_config().get("helper_injection_disabled", [])
    if isinstance(raw, list):
        return frozenset(str(item) for item in raw)
    log.warning("helper_injection_disabled_malformed", value=raw)
    return frozenset()


def _chapter_number(path: Path) -> int:
    match = re.search(r"chapter-(\d+)\.md", path.name)
    return int(match.group(1)) if match else 0


def _style_stats_block(project_dir: Path) -> str | None:
    chapter_files = sorted((project_dir / "chapters").glob("chapter-*.md"), key=_chapter_number)
    if not chapter_files:
        log.info("helper_injection_no_chapters", skill="shenbi-style-learning")
        return None
    window = chapter_files[-_MAX_CHAPTERS:]
    texts = {p.name: p.read_text(encoding="utf-8") for p in window}
    stats: dict[str, Any] = compute_all_stats(texts)
    block = (
        "## Helper Precompute (style stats, deterministic)\n\n"
        "```json\n" + json.dumps(stats, ensure_ascii=False, indent=2) + "\n```\n\n"
        f"以上统计已由框架预计算（compute_all_stats，窗口=最近 {len(window)} 章），"
        "直接引用，不要重算。\n\n"
    )
    if len(block) > _MAX_BLOCK_CHARS:
        # Truncating mid-JSON would leave a malformed block; skip entirely.
        log.warning(
            "helper_block_skipped_oversize",
            skill="shenbi-style-learning",
            size=len(block),
            limit=_MAX_BLOCK_CHARS,
        )
        return None
    return block


def inject_helper_precompute(skill: str, project_dir: Path, user_prompt: str) -> str:
    """Prepend a deterministic helper precompute block for ``skill``.

    Returns ``user_prompt`` unchanged when the skill has no wired helper,
    has no data, or is opted out via executor_config.toml.
    """
    if skill in _helper_injection_disabled():
        return user_prompt
    if skill == "shenbi-style-learning":
        block = _style_stats_block(project_dir)
        if block is not None:
            return block + user_prompt
    return user_prompt
