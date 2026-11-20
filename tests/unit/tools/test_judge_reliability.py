"""Unit tests for tools/judge_reliability.py (spec #110).

Constructed structural corpora under tmp_path — G0.9 structural-input
exemption; the real starvation fixture is consumed read-only via its
canonical classifier (evidence-priority rule, spec acceptance #3).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

HARD_LINE = "- [BLOCKING] 时序矛盾：ch3 与 ch5 对同一事件的日期记述冲突\n"
MINOR_LINE = "- [MINOR] 用词重复\n"
# 生产词族 token（NARROW6「无法核对」——「无法验证」仅 WIDE12，不命中生产分类器）
STARVE_BODY = "**判定**: 不通过（无法核对）\n"


def _write(dir_: Path, name: str, body: str) -> None:
    p = dir_ / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_scan_audits_dual_caliber_ratings_and_hygiene(tmp_path) -> None:
    from tools.judge_reliability import AuditRecord, scan_audits

    audits = tmp_path / "audits"
    _write(audits, "chapter-1-texture.md", f"**判定**：有瑕疵\n{HARD_LINE}{MINOR_LINE}")
    _write(audits, "chapter-1-sensitivity.md", f"**判定**：有瑕疵\n{MINOR_LINE}")  # 仅 MINOR
    _write(audits, "chapter-2-texture.md", STARVE_BODY)  # 饿死形态→invalid
    _write(audits, "chapter-1-review-summary.md", "汇总（不参与）")
    res = scan_audits(audits)
    assert res.file_total == 3  # summary 排除（aggregate 无 -skill 段不匹配）
    by = {(r.chapter, r.skill): r for r in res.records}
    assert by[(1, "texture")] == AuditRecord(
        chapter=1, skill="texture", any_binary=1, hard_binary=1, hard_count=1
    )
    assert by[(1, "sensitivity")].any_binary == 1
    assert by[(1, "sensitivity")].hard_binary == 0
    assert by[(1, "sensitivity")].hard_count == 0
    assert (2, "texture") not in by  # invalid 剔除
    assert len(res.invalid) == 1 and "chapter-2-texture.md" in res.invalid[0]


def test_real_starve_fixture_classified_invalid() -> None:
    """验收 3 优先项：真实饿死 fixture 经 #109 单源分类器判 invalid。"""
    from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict

    fixture = REPO_ROOT / "tests/fixtures/audits/chapter-2-memo-compliance.md"
    assert fixture.exists() and check_audit_starve_verdict(fixture)
