"""spec #106 T3b: resonance backfill with no-text + starved-product guards."""

from pathlib import Path
from types import SimpleNamespace

from shenbi.pipeline.resonance_backfill import backfill_resonance

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)


def _seed(tmp_path: Path, *, chapter_file: bool, report_text: str | None) -> None:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "truth" / "resonance_trend.md").write_text(
        "\n".join([HEADER, SEP, "| 26 | 未声明 | - | - | - | - | pending | low |  |"]) + "\n",
        encoding="utf-8",
    )
    if chapter_file:
        ch_dir = tmp_path / "chapters"
        ch_dir.mkdir(exist_ok=True)
        (ch_dir / "chapter-26.md").write_text("# 第二十六章\n\n正文。", encoding="utf-8")
        # 契约预检 seed（audit-plan N3）：missing_audit_reads 按 review-resonance
        # 契约 6 条 reads 严格判（plans/style/anchors/audit_drift 不在 OPTIONAL_READS）
        (tmp_path / "plans").mkdir(exist_ok=True)
        (tmp_path / "plans" / "chapter-26-plan.md").write_text("## 1. 当前任务\n", encoding="utf-8")
        (tmp_path / "style").mkdir(exist_ok=True)
        (tmp_path / "style" / "style_profile.md").write_text(
            "# style\n## 11. 综合画像\n## 6. 修辞模式\n", encoding="utf-8"
        )
        (tmp_path / "benchmarks" / "anchors").mkdir(parents=True, exist_ok=True)
        (tmp_path / "truth" / "audit_drift.md").write_text("# drift\n", encoding="utf-8")
    audits = tmp_path / "audits"
    audits.mkdir(exist_ok=True)
    if report_text is not None:
        (audits / "chapter-26-resonance.md").write_text(report_text, encoding="utf-8")


def _ok_dispatch(monkeypatch, seen=None):
    def fake(*a, **k):
        if seen is not None:
            seen.append(1)
        return SimpleNamespace(success=True, returncode=0, stderr="", stdout="")

    monkeypatch.setattr("shenbi.pipeline.dispatch_helper.dispatch_skill", fake)


def test_backfill_refuses_missing_chapter_text(tmp_path, monkeypatch):
    _seed(tmp_path, chapter_file=False, report_text=None)
    seen = []
    _ok_dispatch(monkeypatch, seen)
    result = backfill_resonance(tmp_path, [26])
    assert result["refused_missing_text"] == [26] and not seen
    assert "pending" in (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")


def test_backfill_refuses_starved_product(tmp_path, monkeypatch):
    _seed(
        tmp_path,
        chapter_file=True,
        report_text="```verdict\n判定: 待补（正文未提供）\n```\n",
    )
    _ok_dispatch(monkeypatch)
    result = backfill_resonance(tmp_path, [26])
    assert result["refused_bad_product"] == [26]
    assert "pending" in (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")


def test_backfill_success_upserts_row(tmp_path, monkeypatch):
    _seed(
        tmp_path,
        chapter_file=True,
        report_text="```verdict\n判定: 通过\n共振: 81/100\n```\n",
    )
    _ok_dispatch(monkeypatch)
    result = backfill_resonance(tmp_path, [26])
    assert result["filled"] == [26]
    row = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
    assert "| 26 |" in row and "81" in row and "pending" not in row


def test_backfill_default_targets_pending(tmp_path, monkeypatch):
    _seed(
        tmp_path,
        chapter_file=True,
        report_text="```verdict\n判定: 通过\n共振: 81/100\n```\n",
    )
    _ok_dispatch(monkeypatch)
    result = backfill_resonance(tmp_path, None)  # None → 自动取 pending 行章
    assert result["filled"] == [26]
