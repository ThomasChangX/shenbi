"""C 批: volume budget guardrails — 卷界锚规则、骨架序言派生、再预算检视.

The 千万字 route grows the book by appending volumes at boundaries. Three
disciplines keep that growth honest, all deterministic code (no LLM writer
discipline load-bearing — the GO① pattern):

- **卷界锚规则** (:func:`check_new_volume_anchor`): a NEW ``## 第N卷`` section
  must start at live max chapter boundary + 1, with a machine-readable
  ``(第 a-b 章)`` range — enforced BEFORE the merge write, with the same
  pointed-rejection discipline as the increment shape guard.
- **骨架序言派生** (:func:`sync_volume_skeleton`): frontmatter
  ``total_chapters`` and the preamble ``> **卷界**:`` line are DERIVED from
  the volume sections whenever a volume increment lands (the writer is
  contract-forbidden from emitting either; a hand-maintained 最大章界 went
  stale the moment re-budget added a volume).
- **再预算检视** (:func:`budget_verdict`): the boundary chain's single
  consultation — novel.json ``target_word_count`` edits surface as a
  re-budget PENDING (the human's re-budget entry), per-volume planned-vs-
  actual drift is checked against the ±3 tolerance with consecutive-
  overshoot escalation, and the per-chapter 保量 floor reuses the G0.3
  口径 (:func:`shenbi.gates.shared.chapter_word_floor` /
  :func:`total_chars_md_text`). ``--apply`` performs the deterministic
  writeback (:func:`update_total_chapters` + skeleton sync) once the new
  volumes have landed.

CLI::

    python -m shenbi.pipeline.volume_budget <project_dir> [--apply]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from shenbi.pipeline._shared import read_volume_boundaries, update_total_chapters
from shenbi.safe_write import safe_write

#: A volume heading with its machine-readable chapter span:
#: ``## 第一卷：哑脉藏火（第 1-23 章）`` — token in group(1), arabic span in
#: groups (2, 3). The paren span is the genesis contract shape; without it
#: neither the anchor rule nor the five-way reconciliation can read the
#: section.
_VOL_SPAN_HEADING_RE = re.compile(
    r"^##\s*(第[一二三四五六七八九十百千\d]+卷)[^\n（(]*[（(]第\s*(\d+)\s*[-–—~～]\s*第?\s*(\d+)\s*章[）)]",
    re.MULTILINE,
)

#: The preamble line the skeleton derivation maintains.
_BOUNDARY_LINE_RE = re.compile(r"^>\s*\*\*卷界\*\*[:：].*$", re.MULTILINE)

#: Per-volume drift tolerance (planned span vs actual consumption): within
#: ±3 chapters the boundary chain tolerates without escalation — a volume
#: running hot by a chapter or two is pacing, not a budget event.
_DRIFT_TOLERANCE = 3

#: Consecutive overshooting volumes before the check demands re-budget
#: (two in a row is a systematic underestimate, not noise).
_CONSECUTIVE_ESCALATION = 2


@dataclass(frozen=True)
class VolumeSpan:
    token: str  # 第N卷 heading token, as written
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def parse_volume_spans(text: str) -> list[VolumeSpan]:
    """Ordered volume spans from ``(第 a-b 章)`` headings ([] when none)."""
    return [
        VolumeSpan(m.group(1), int(m.group(2)), int(m.group(3)))
        for m in _VOL_SPAN_HEADING_RE.finditer(text)
    ]


def check_new_volume_anchor(base_text: str, increment_text: str) -> str | None:
    """Anchor-rule verdict for a volume_map increment; None = passes.

    Every NEW volume section (token absent from the base) must carry a
    machine-readable span and CHAIN: the first at the effective max
    boundary + 1, each next at its predecessor's end + 1. The effective
    max counts base spans with same-token spans OVERRIDDEN by the increment
    (a re-spanned tail volume legitimately moves the boundary), so a
    multi-volume re-budget lands in ONE dispatch. REPLACED volumes are
    otherwise unconstrained here — mid-book span adjustments are the drift
    guardrails' concern, not the merge's.
    """
    base_spans = parse_volume_spans(base_text)
    base_tokens = {s.token for s in base_spans}
    inc_spans = parse_volume_spans(increment_text)

    effective: dict[str, VolumeSpan] = {s.token: s for s in base_spans}
    for s in inc_spans:
        if s.token in effective:
            effective[s.token] = s
    eff_max = max((s.end for s in effective.values()), default=0)

    new_spans = sorted((s for s in inc_spans if s.token not in base_tokens), key=lambda s: s.start)
    # New heading tokens WITHOUT a machine-readable span are unauditable
    # (five-way reconciliation + this rule both read the paren range).
    all_tokens = {
        m.group(1)
        for m in re.finditer(
            r"^##\s*(第[一二三四五六七八九十百千\d]+卷)[：:（(\s]", increment_text, re.MULTILINE
        )
    }
    spanned_new = {s.token for s in new_spans}
    unspanned = [t for t in sorted(all_tokens - base_tokens - spanned_new)]
    if unspanned:
        return (
            f"输出未落盘——新卷 {unspanned[0]} 的标题缺少机器可读章界"
            "「(第 a-b 章)」，锚规则与五方对账均无法读取。"
            "合法形态：`## 第N卷：<标题>(第 a-b 章)`。"
        )
    expected_start = eff_max + 1
    for s in new_spans:
        if s.start != expected_start:
            return (
                f"输出未落盘——卷界锚规则：新卷 {s.token} 起始为第 {s.start} 章，"
                f"须从第 {expected_start} 章起卷（有效最大章界为第 {eff_max} 章）。"
            )
        expected_start = s.end + 1
    return None


def sync_volume_skeleton(text: str) -> str:
    """Derive frontmatter ``total_chapters`` + the ``> **卷界**:`` preamble
    line from the volume sections (GO① discipline: the skeleton is a
    derived mirror, never writer-maintained).

    No-op without parseable volumes; never invents a missing frontmatter key
    or preamble line (only REWRITES existing ones).
    """
    spans = parse_volume_spans(text)
    if not spans:
        return text
    max_end = max(s.end for s in spans)
    out = text

    m_fm = re.match(r"^---\n(.*?)\n---\n", out, re.DOTALL)
    if m_fm is not None and re.search(r"^total_chapters\s*[:：]", m_fm.group(1), re.MULTILINE):
        fm = re.sub(
            r"^(total_chapters\s*[:：]\s*).*$",
            rf"\g<1>{max_end}",
            m_fm.group(1),
            count=1,
            flags=re.MULTILINE,
        )
        out = f"---\n{fm}\n---\n" + out[m_fm.end() :]

    if _BOUNDARY_LINE_RE.search(out) is not None:
        lens = " / ".join(str(s.length) for s in spans)
        line = f"> **卷界**：{lens} = {max_end}；最大章界为第 {max_end} 章。"
        existing = _BOUNDARY_LINE_RE.search(out)
        assert existing is not None
        existing_nums = [int(n) for n in re.findall(r"\d+", existing.group(0))]
        derived_nums = [s.length for s in spans] + [max_end, max_end]
        if existing_nums != derived_nums:
            # numbers disagree (or list length changed) — rewrite; when the
            # numbers already match, the line stays byte-identical (a genesis
            # emphasis variant like **第 118 章** survives re-derivation).
            out = _BOUNDARY_LINE_RE.sub(lambda _: line, out, count=1)
    return out


@dataclass(frozen=True)
class BudgetVerdict:
    """The boundary chain's one-stop budget consultation result."""

    planned_total: int
    implied_total: int  # ceil(target_word_count / chapter_word.default); 0 unknown
    re_budget_pending: bool
    drifts: dict[str, int] = field(default_factory=dict)  # token → actual - planned
    findings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings and not self.re_budget_pending


def _implied_total(project_dir: Path) -> tuple[int, int]:
    """(implied chapter total, chapter_word default) — (0, 0) when unknown."""
    try:
        novel = json.loads((project_dir / "novel.json").read_text(encoding="utf-8"))
        gc = json.loads((project_dir / "genre-config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return 0, 0
    target = novel.get("target_word_count")
    default = gc.get("chapter_word", {}).get("default")
    if (
        not isinstance(target, (int, float))
        or not isinstance(default, (int, float))
        or default <= 0
    ):
        return 0, 0
    return -(-int(target) // int(default)), int(default)


def _actual_spans(project_dir: Path) -> dict[str, tuple[int, int]]:
    """Token → actual span from volume_summaries headings (written at each
    boundary with the REAL consumed span) — the drift source of truth.
    """
    path = project_dir / "truth" / "volume_summaries.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    spans: dict[str, tuple[int, int]] = {}
    for m in re.finditer(
        r"^##\s*(第\d+卷)[:：][^\n（(]*[（(]第\s*(\d+)\s*[-–—~～]\s*第?\s*(\d+)\s*章[）)]",
        text,
        re.MULTILINE,
    ):
        spans.setdefault(m.group(1), (int(m.group(2)), int(m.group(3))))
    return spans


def _written_chapters(project_dir: Path) -> int:
    """Max chapter number on disk under chapters/ (0 when none)."""
    best = 0
    chapters_dir = project_dir / "chapters"
    if not chapters_dir.is_dir():
        return 0
    for m in chapters_dir.glob("chapter-*.md"):
        n = m.stem.removeprefix("chapter-")
        if n.isdigit():
            best = max(best, int(n))
    return best


def _chapter_tokens(spans: list[VolumeSpan], token: str) -> str:
    """volume_summaries writes arabic tokens (第1卷); the map may use Chinese
    numerals (第一卷) — normalize by ordinal for the join.
    """
    for i, s in enumerate(spans):
        if s.token == token:
            return f"第{i + 1}卷"
    return token


def budget_verdict(project_dir: Path) -> BudgetVerdict:
    """Assemble the re-budget / drift / 保量 verdict from disk state alone."""
    vm_path = project_dir / "outline" / "volume_map.md"
    spans = parse_volume_spans(vm_path.read_text(encoding="utf-8")) if vm_path.is_file() else []
    planned_total = max((read_volume_boundaries(project_dir)), default=0) or max(
        (s.end for s in spans), default=0
    )
    implied, word_default = _implied_total(project_dir)
    findings: list[str] = []
    drifts: dict[str, int] = {}

    # 1) Re-budget entry: the human's target edit vs the landed plan.
    re_budget_pending = bool(implied and planned_total and implied != planned_total)
    if re_budget_pending:
        findings.append(
            f"re_budget_pending: novel.json 预算 {implied} 章 ≠ volume_map 已落 {planned_total} 章"
            "——target_word_count 已被人工修改，需重跑卷层设计后 --apply 回写"
        )

    # 2) Per-volume drift (±3 tolerated; two consecutive overshoots escalate).
    actual = _actual_spans(project_dir)
    consecutive_over = 0
    for s in spans:
        a = actual.get(_chapter_tokens(spans, s.token))
        if a is None:
            continue
        drift = (a[1] - a[0] + 1) - s.length
        drifts[s.token] = drift
        if drift > _DRIFT_TOLERANCE:
            consecutive_over += 1
            findings.append(
                f"volume_overrun: {s.token} 计划 {s.length} 章实际 {a[1] - a[0] + 1} 章"
                f"（超 {drift} 章 > ±{_DRIFT_TOLERANCE} 容差）"
            )
        else:
            consecutive_over = 0
    if consecutive_over >= _CONSECUTIVE_ESCALATION:
        findings.append(
            f"consecutive_overshoot: 连续 {consecutive_over} 卷超出 ±{_DRIFT_TOLERANCE} 容差"
            "——系统性低估，必须再预算（人工裁定新 target_word_count）"
        )

    # 3) Current-volume spillover + 保量 floor (G0.3 口径复用).
    written = _written_chapters(project_dir)
    if spans and written:
        current = spans[-1]
        for s in spans:
            if s.start <= written:
                current = s
        if written > current.end + _DRIFT_TOLERANCE:
            findings.append(
                f"volume_spillover: 已写到第 {written} 章而 {current.token} 计划止于第 {current.end} 章"
                f"（溢出 {written - current.end} 章 > ±{_DRIFT_TOLERANCE} 容差）"
            )
        if word_default:
            from shenbi.gates.shared import total_chars_md_text

            under = 0
            for n in range(current.start, min(written, current.end) + 1):
                ch = project_dir / "chapters" / f"chapter-{n}.md"
                if (
                    ch.is_file()
                    and total_chars_md_text(ch.read_text(encoding="utf-8")) < word_default
                ):
                    under += 1
            if under:
                findings.append(
                    f"word_floor: {current.token} 有 {under} 章低于 chapter_word.default "
                    f"={word_default}（G0.3 口径）——保量缺口需在再预算中计入"
                )

    return BudgetVerdict(
        planned_total=planned_total,
        implied_total=implied,
        re_budget_pending=re_budget_pending,
        drifts=drifts,
        findings=findings,
    )


def apply_budget_writeback(project_dir: Path) -> int:
    """Deterministic writeback after a re-budget's new volumes have landed:
    novel.json ``total_chapters`` := max volume boundary, and the volume_map
    skeleton (frontmatter + 卷界 line) re-derived. Returns the new total.
    """
    vm_path = project_dir / "outline" / "volume_map.md"
    if vm_path.is_file():
        text = vm_path.read_text(encoding="utf-8")
        synced = sync_volume_skeleton(text)
        if synced != text:
            safe_write(vm_path, synced.encode("utf-8"))
    return update_total_chapters(project_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "Volume budget").splitlines()[0])
    parser.add_argument("project_dir", type=str, help="novel project directory")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="deterministic writeback: total_chapters + skeleton (after re-budget volumes land)",
    )
    args = parser.parse_args(argv)
    project = Path(args.project_dir)
    if args.apply:
        total = apply_budget_writeback(project)
        sys.stdout.write(f"applied: total_chapters={total or '-'}\n")
    v = budget_verdict(project)
    sys.stdout.write(
        f"planned_total={v.planned_total} implied_total={v.implied_total} "
        f"re_budget_pending={str(v.re_budget_pending).lower()} drifts={v.drifts or '-'}\n"
    )
    for f in v.findings:
        sys.stdout.write(f"FINDING {f}\n")
    sys.stdout.write("verdict=" + ("OK" if v.ok else "NEEDS_ATTENTION") + "\n")
    return 0 if v.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
