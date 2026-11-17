"""Resonance backfill maintenance command (spec #106 T3b).

Re-dispatches ``shenbi-review-resonance`` for pending trend rows with a
double guard: (1) the target chapter's text must be on disk AND the skill's
required contract reads must resolve (``missing_audit_reads`` — the #105
audit readiness precheck); (2) the product must carry a parseable non-pending
score and none of the #109 T4 starved-form markers (待补/不适用/附条件 —
the skill scores even without text, 63/81/63 anchor). A chapter failing
either guard is REFUSED and its trend row is left untouched.

Real dispatches are paid maintenance actions — run on user command only
(``just resonance-backfill <dir>``); tests monkeypatch
``shenbi.pipeline.dispatch_helper.dispatch_skill`` (consumed via
function-local import).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)

#: #109 T4 饿死词族子集（产物侧判据）——命中即拒绝写 trend 行。
#: spec #109 audit-T4 🟡1 裁定（2026-11-18）：**有意收窄**——本判据是 #106 的
#: trend 行产物过滤（resonance 回放域），非 T4 判定行生产门；不 import
#: audit_starve_family.PRODUCTION_FAMILY（扩词族=改 #106 行为，越权本批）。
#: 词族漂移监督：tests/unit/tools/test_audit_starve_baseline.py 单源断言守
#: 生产门侧；本子集变动须同步本注释。
_STARVED_FORM_RE = re.compile(r"待补|不适用|附条件")


def _pending_chapters(project_dir: Path) -> list[int]:
    from shenbi.pipeline.resonance_policy import trend_rows_full

    trend = project_dir / "truth" / "resonance_trend.md"
    if not trend.exists():
        return []
    rows = trend_rows_full(trend)
    return sorted(ch for ch, overall, _ov in rows if overall is None)


def backfill_resonance(project_dir: Path | str, chapters: list[int] | None) -> dict[str, list[int]]:
    """Backfill pending resonance rows with the double guard (spec #106 T3b).

    Returns ``{"filled": [...], "refused_missing_text": [...],
    "refused_bad_product": [...]}``.
    """
    project_dir = Path(project_dir)
    targets = list(chapters) if chapters is not None else _pending_chapters(project_dir)
    result: dict[str, list[int]] = {
        "filled": [],
        "refused_missing_text": [],
        "refused_bad_product": [],
    }
    for ch in targets:
        # Guard 1: chapter text on disk + required contract reads resolvable.
        chapter_file = project_dir / "chapters" / f"chapter-{ch}.md"
        if not chapter_file.exists():
            result["refused_missing_text"].append(ch)
            log.warning("backfill_missing_chapter_text", chapter=ch)
            continue
        from shenbi.pipeline.audit_layer import missing_audit_reads

        missing = missing_audit_reads(project_dir, "shenbi-review-resonance", ch)
        if missing:
            result["refused_missing_text"].append(ch)
            log.warning("backfill_missing_contract_reads", chapter=ch, missing=missing)
            continue
        # Guard 2 (dispatch side): paid maintenance dispatch, user-command only.
        # 函数级局部 import（F947：monkeypatch 源模块属性即生效）
        from shenbi.pipeline.dispatch_helper import dispatch_skill

        dispatch_result = dispatch_skill(
            "shenbi-review-resonance",
            project_dir,
            f"Backfill resonance review for chapter {ch} (pending trend row).",
        )
        report = project_dir / "audits" / f"chapter-{ch}-resonance.md"
        if not dispatch_result.success or not report.exists():
            result["refused_bad_product"].append(ch)  # 派发失败不熔断，继续下一章
            log.warning("backfill_dispatch_failed", chapter=ch)
            continue
        # Guard 3 (product side): parseable non-pending score, no starved forms.
        from shenbi.gates.g4.verdict_fence import extract_fence, match_score_scoped

        text = report.read_text(encoding="utf-8")
        score = match_score_scoped(text)
        fence = extract_fence(text)
        fence_text = fence if fence is not None else ""
        from shenbi.pipeline.chapter_loop import RESONANCE_PENDING_RE

        if (
            score is None
            or RESONANCE_PENDING_RE.search(fence_text)  # audit-T4 M2 单源
            or _STARVED_FORM_RE.search(fence_text or text)
        ):
            result["refused_bad_product"].append(ch)
            log.warning("backfill_starved_product", chapter=ch, score=score)
            continue
        # Fill the trend row ONLY if it is still pending/absent: a real
        # dispatch has the skill write its own rich row (SDD #21 R1 — the
        # framework placeholder must never clobber it). With the row still
        # pending (mocked dispatch in tests / skill skipped its write), the
        # placeholder row upserts in its place.
        from shenbi.pipeline.chapter_loop import build_resonance_trend_row
        from shenbi.pipeline.resonance_policy import trend_rows_full
        from shenbi.pipeline.truth_io import write_truth_file

        current = {
            ch2: overall
            for ch2, overall, _ov in trend_rows_full(project_dir / "truth" / "resonance_trend.md")
        }
        if current.get(ch) is None:
            write_truth_file(
                project_dir,
                "resonance_trend.md",
                build_resonance_trend_row(ch, score),
                mode="upsert_markdown_row",
                key_field="chapter",
            )
        result["filled"].append(ch)
        log.info("backfill_filled", chapter=ch, score=score)
    return result


def _parse_chapters(spec: str) -> list[int]:
    chapters: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            chapters.extend(range(int(lo), int(hi) + 1))
        else:
            chapters.append(int(part))
    return chapters


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="resonance-backfill",
        description="Re-dispatch review-resonance for pending trend rows (spec #106 T3b, 维护命令)",
    )
    parser.add_argument("project_dir", type=str)
    parser.add_argument(
        "--chapters",
        type=str,
        default=None,
        help="a-b or c,d form; default = pending trend rows",
    )
    args = parser.parse_args(argv)
    chapters = _parse_chapters(args.chapters) if args.chapters else None
    result = backfill_resonance(args.project_dir, chapters)
    from shenbi.cli_utils import echo

    echo(f"filled: {result['filled']}")
    echo(f"refused_missing_text: {result['refused_missing_text']}", err=True)
    echo(f"refused_bad_product: {result['refused_bad_product']}", err=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
