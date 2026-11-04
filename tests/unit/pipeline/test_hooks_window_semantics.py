"""Spec #95 T3 (r1.6 ②): hooks window semantics — active∪named + priority budget.

Two failure modes this pins (00189 evidence):
- 未点名活钩不可见 → 模型重造（R5 盲写面）：active hooks the plan did NOT name
  must still keep their detail sections.
- 点名过宽零裁剪：ch41 named all 14 live hooks → 42.2k chars detail body ran
  into the 32k per-file cap mid-tail. Combined details beyond the char budget
  are dropped lowest-priority-first (unnamed-active before named) with
  per-section disclosure.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.read_extractors import DETAILS_CHAR_BUDGET, extract_hooks_audit_scoped

FIXTURES = Path(__file__).resolve().parents[3] / "tests/fixtures/spec95/00189-reads"


def _hooks_content() -> str:
    raw = (FIXTURES / "07-staging__truth__pending_hooks.md").read_bytes()
    return raw.split(b"-->" + b"\n", 1)[1].decode("utf-8")


def _project(tmp_path: Path, named_ids: set[str]) -> Path:
    """Grounding face: plan hook-account table naming exactly `named_ids`."""
    rows = "\n".join(f"| {h} | advance |" for h in sorted(named_ids))
    (tmp_path / "plans").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plans" / "chapter-41-plan.md").write_text(
        f"## 7. 本章 hook 账\n\n| ID | 操作 |\n|----|------|\n{rows}\n",
        encoding="utf-8",
    )
    return tmp_path


def test_unnamed_active_hook_detail_kept(tmp_path: Path) -> None:
    """点名 1 钩，其余 13 为活钩——active 纳入后预算内活钩详情可见（R5 盲写面修复）。

    具体保哪几段由（优先级,文件序）+预算决定——断言语义不钉特定 id。
    """
    proj = _project(tmp_path, {"MH02"})
    out = extract_hooks_audit_scoped(proj, 41, _hooks_content())
    assert "### MH02" in out  # 点名优先级一：预算内必保
    kept_ids = {
        ln.split("（")[0].strip("# ").strip() for ln in out.splitlines() if ln.startswith("### ")
    }
    assert len(kept_ids - {"MH02"}) >= 1  # 至少一段未点名活钩详情在窗
    assert "＋active" in out


def test_named_all_budget_truncates_lowest_priority(tmp_path: Path) -> None:
    """ch41 形态：点名全部活钩→详情超预算→按优先级截断并逐段披露。"""
    proj = _project(tmp_path, {f"MH{n:02d}" for n in range(1, 15)})
    out = extract_hooks_audit_scoped(proj, 41, _hooks_content())
    assert "[extractor:hooks_audit_scoped]" in out
    kept_sections = out.count("### MH")
    assert kept_sections < 14  # 42.2k > 预算——不再全保留
    assert "已省略" in out and "chars" in out  # 逐段披露
    detail_chars = sum(len(sec) for sec in out.split("### ")[1:])
    assert detail_chars <= DETAILS_CHAR_BUDGET * 1.5  # 有界收敛
