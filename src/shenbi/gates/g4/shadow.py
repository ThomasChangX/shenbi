"""spec #82 shadow gate demotion (gates-side pure helper).

New FAIL gates default to ``shadow: true`` in genre-config: a shadow gate's
FAIL is demoted to WARN at the *consumption* sites (chapter_loop / cli), never
inside the gate checkers — those stay pure and idempotent. The call site then
emits the trace WARN event (action="WARN", the #81 trace face) and routes the
demoted item into the WARN channel instead of the hard-fail classifier.

Routing contract (plan R3/I1, pinned):
  - demoted items are REMOVED from the must_fix list before classification;
  - if every must_fix item was demoted (single-gate FAIL — the common first-
    bundle case) the step is treated as PASS-with-warnings: the caller
    replicates the :4207 retry_feedback cleanup and must NOT fall into the
    ``G4.generic_failure`` synthetic-HARD fallback (:4212-4215).
"""

from __future__ import annotations

import re
from pathlib import Path

from shenbi.gates.shared import read_genre_config

# Keys are prefixed check ids as emitted by must_fix strings (the
# `_extract_check_id` shape); values are (config_block, config_key).
# An unmapped id maps to None → NO demotion (fail-safe direction: unlisted
# gates stay HARD-visible; silent demotion is the accident we guard against).
GATE_TO_SHADOW_KEY: dict[str, tuple[str, str]] = {
    "cp.cold_streak_window": ("market_params", "cold_streak_cap"),
    "cp.hot_hook_window": ("market_params", "hot_hook_floor"),
    "cp.payoff_magnitude": ("market_params", "payoff_magnitude_floor"),
    "cp.hook_age": ("market_params", "hook_max_age"),
    "cd.hook_type_rotation": ("market_params", "hook_rotation"),
    # 阶段8/N1: cp 钩型存在性/词表门与 rotation 同七型执法族（同一 shadow 键族管辖）
    "cp.missing_hook_type": ("market_params", "hook_rotation"),
    "cp.hook_type_wordlist": ("market_params", "hook_rotation"),
    "cd.quote_verbatim": ("market_params", "quote_anchor"),
    "cp.missing_retention_anchor": ("market_params", "retention_anchor"),
    "cp.core_motif_touch": ("pacing", "core_motif_touch"),
    # spec #83 §10 行 1：POST 引句两臂 FAIL 臂（勿与 #82 既有 G4.cd.quote_verbatim
    # 混同——彼门为 v4 备忘张力拍锚，两语义不同的门不可连带转正）
    "cd.post_quote_verbatim": ("market_params", "post_quote_verbatim"),
    # spec #83 §10 行 2：POST 转折词交叉门（前置=count_transition_words 补语形去重）
    "cd.post_transition_cross": ("market_params", "post_transition_cross"),
    # spec #83 §10 行 3：修订删物象相对谓词（复验面——消费点 :4487 显式 demote）
    "rev.prop_purged": ("market_params", "prop_purge_guard"),
}


def check_id(item: str) -> str:
    """Extract the prefixed G4 check id from a must_fix string."""
    m = re.match(r"G4\.([a-z_.]+)", item)
    return m.group(1) if m else item.split(":", maxsplit=1)[0].replace("G4.", "")


def apply_shadow(project_dir: Path, item: str) -> str | None:
    """Return the demoted WARN text for *item*, or None when it stays HARD.

    Pure read (genre-config only); the trace WARN event is the caller's to
    emit once demotion is confirmed.
    """
    cfg = read_genre_config(str(project_dir)) or {}
    loc = GATE_TO_SHADOW_KEY.get(check_id(item))
    if loc is None:
        return None  # unlisted gate: stays HARD (fail-safe)
    block, key = loc
    entry = (cfg.get(block) or {}).get(key, {})
    if not (isinstance(entry, dict) and entry.get("shadow", True) is True):
        # shadow:false = promoted → stays HARD. Key absent → default shadow
        # (spec L-D: 新 FAIL 门默认 shadow:true) → demote.
        return None
    return f"[shadow] {item}（shadow 试运行——零误伤后转正）"


def demote_must_fix(project_dir: Path, must_fix: list[str]) -> tuple[list[str], list[str]]:
    """Split a must_fix list into (demoted WARN texts, remaining HARD items).

    The common single-gate case (all items demoted → remaining empty) tells
    the caller to route PASS-with-warnings instead of the synthetic-HARD
    fallback.
    """
    demoted: list[str] = []
    remaining: list[str] = []
    for item in must_fix:
        text = apply_shadow(project_dir, item)
        if text is None:
            remaining.append(item)
        else:
            demoted.append(text)
    return demoted, remaining


def emit_shadow_warn_trace(project_dir: Path | str, chapter: int, item: str) -> None:
    """Append-only trace WARN event for demoted shadow gates (spec #82 T3).

    Fire-and-forget via the #81 trace face: a trace-side failure must never
    block the loop. Shared by all four demotion sites (chapter_loop + cli).
    """
    import structlog

    log = structlog.get_logger("shenbi.gates.g4.shadow")
    try:
        from shenbi.trace.writer import TraceWriter

        TraceWriter(Path(project_dir)).append(
            actor="chapter-loop",
            actor_role="SYSTEM",
            action="WARN",
            target=f"ch{chapter}",
            gate="shadow",
            payload={"chapter": chapter, "item": item[:200]},
        )
    except Exception:  # noqa: BLE001 -- observability must not break the loop
        log.warning("shadow_trace_emit_failed", chapter=chapter)
