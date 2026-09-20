"""Spec #68 T4: observations — ledger per-chapter, truth growth, coverage."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _record(
    tmp_path: Path,
    chapter: int,
    *,
    cost: float = 0.01,
    minutes: int = 0,
    attempt: int = 1,
) -> None:
    """经真实写方 TokenLedger.record 追加一行；timestamp/cost 回写为受控值。

    行仍由 record 追加，字段集与 iter_records 兼容契约一致。
    """
    from shenbi.cost.ledger import TokenLedger

    led = TokenLedger(tmp_path)
    usage = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
    led.record("shenbi-chapter-drafting", chapter, usage, attempt=attempt)
    lines = (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[-1])
    row["timestamp"] = (
        datetime(2026, 9, 21, 12, 0, tzinfo=UTC) + timedelta(minutes=minutes)
    ).isoformat()
    row["estimated_cost_usd"] = cost
    lines[-1] = json.dumps(row, ensure_ascii=False)
    (tmp_path / "cost" / "token-ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestLedgerStats:
    """ledger 按章聚合 + 墙钟 + 跳行披露。"""

    def test_per_chapter_aggregation_and_wallclock(self, tmp_path):
        from tools.report_longitudinal import ledger_stats

        _record(tmp_path, 1, cost=0.01, minutes=0, attempt=1)
        _record(tmp_path, 1, cost=0.02, minutes=30, attempt=2)
        _record(tmp_path, 2, cost=0.03, minutes=90)
        stats = ledger_stats(tmp_path, [1, 2], {1: 10000, 2: 20000})
        by_ch = {e["chapter"]: e for e in stats["per_chapter"]}
        assert by_ch[1]["cost_usd"] == pytest.approx(0.03)
        assert by_ch[1]["wall_clock_s"] == 1800.0
        assert by_ch[2]["cost_per_10k"] == pytest.approx(0.015)
        assert by_ch[1]["attempts"] == 2  # max(attempt) 语义（spec §1「attempt 聚合」）
        assert stats["skipped_rows"] == 0 and stats["chapters_covered"] == 2

    def test_skipped_rows_disclosed(self, tmp_path):
        from tools.report_longitudinal import ledger_stats

        _record(tmp_path, 1)
        led = tmp_path / "cost" / "token-ledger.jsonl"
        led.write_text(led.read_text(encoding="utf-8") + "{corrupt\n", encoding="utf-8")
        stats = ledger_stats(tmp_path, [1], {1: 10000})
        assert stats["skipped_rows"] == 1

    def test_missing_ledger_zero_coverage(self, tmp_path):
        from tools.report_longitudinal import ledger_stats

        stats = ledger_stats(tmp_path, [1], {1: 10000})
        assert stats["per_chapter"] == [] and stats["chapters_covered"] == 0


class TestTruthGrowth:
    """truth 增长曲线 + 条件性注记 + 真实 fixture 面。"""

    def test_current_sizes_and_conditional_note(self, tmp_path):
        from tools.report_longitudinal import truth_growth

        truth = tmp_path / "truth"
        truth.mkdir()
        (truth / "current_state.md").write_text("# 状态\n" + "x" * 500, encoding="utf-8")
        out = truth_growth(tmp_path)
        assert any(e["file"] == "current_state.md" and e["bytes"] > 500 for e in out["current"])
        assert "快照" in out["note"] or "snapshot" in out["note"]

    def test_real_fixture_truth_face(self, tmp_path):
        """spec 验收：chapter-025 真实产物提供 truth 面基准——真实尺寸可读且非空。"""
        import shutil

        from tools.report_longitudinal import truth_growth

        src = (
            Path(__file__).resolve().parent.parent
            / "fixtures"
            / "snapshots"
            / "chapter-025"
            / "truth"
        )
        shutil.copytree(src, tmp_path / "truth")
        out = truth_growth(tmp_path)
        assert {e["file"] for e in out["current"]} >= {
            "current_state.md",
            "character_matrix.md",
            "pending_hooks.md",
        }
        assert all(e["bytes"] > 0 for e in out["current"])


class TestTruthGrowthSnapshots:
    """快照在场分支：条目带快照身份（相对路径）+ 覆盖注记。"""

    def test_snapshot_entries_carry_identity(self, tmp_path):
        from tools.report_longitudinal import truth_growth

        for snap in ("chapter-001", "chapter-002"):
            d = tmp_path / "snapshots" / snap / "truth"
            d.mkdir(parents=True)
            (d / "current_state.md").write_text("# 状态\n" + "x" * 100, encoding="utf-8")
        out = truth_growth(tmp_path)
        assert {e["snapshot"] for e in out["snapshots"]} == {
            "snapshots/chapter-001/truth/current_state.md",
            "snapshots/chapter-002/truth/current_state.md",
        }
        assert "快照面覆盖 2" in out["note"]


class TestEvaluateIntegration:
    """T4 并网：三键在场 + 判定面与 T2 字节不变。"""

    def test_observation_keys_present_and_verdict_untouched(self, tmp_path):
        from tests.unit.test_report_longitudinal import _mk_project
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            cjk_per_ch=28000,
        )
        report = evaluate(tmp_path)
        assert set(report) >= {"taxonomy", "scalability", "coverage"}
        assert report["coverage"]["resonance_rows"] == [3, 3]
        # 分子与分母同口径：未提交章的 trend 行不计入（防 >100% 披露）
        _write_extra = tmp_path / "truth" / "resonance_trend.md"
        with _write_extra.open("a", encoding="utf-8") as fh:
            fh.write("| 9 | 高潮 | 22 | 20 | 22 | 18 | 90 | high |  |\n")
        from tools.report_longitudinal import evaluate as _ev

        assert _ev(tmp_path)["coverage"]["resonance_rows"] == [3, 3]
        assert report["coverage"]["audits_chapters"] == [0, 3]  # audits/ 不存在 → none
        assert report["coverage"]["ledger_chapters"] == [0, 3]
        assert report["taxonomy"]["audit_sources"] == {"raw": 0, "aggregate": 0, "none": 3}
        assert report["taxonomy"]["unclassified"] == 0
        assert report["verdict"] == "pass" and report["exit_code"] == 0
        assert report["reasons"] == []


class TestCliEndToEnd:
    """CLI 三态 + 双报告落盘。"""

    def test_pass_project_writes_both_reports_exit0(self, tmp_path):
        from tests.unit.test_report_longitudinal import _mk_project
        from tools.report_longitudinal import main

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            cjk_per_ch=28000,
        )
        rc = main([str(tmp_path)])
        assert rc == 0
        md = tmp_path / "metrics" / "longitudinal-report.md"
        js = tmp_path / "metrics" / "longitudinal-report.json"
        assert md.exists() and js.exists()
        data = json.loads(js.read_text(encoding="utf-8"))
        assert data["schema"] == "shenbi-longitudinal-verdict-v1"
        assert data["verdict"] == "pass" and data["exit_code"] == 0
        assert set(data) >= {
            "verdict",
            "exit_code",
            "reasons",
            "disclosures",
            "n_target",
            "n_done",
            "segments",
            "volume",
            "per_chapter",
            "trend",
            "drift_findings",
            "coverage",
            "taxonomy",
            "scalability",
            "pending_checkpoint",
        }
        assert "责任子系统" in md.read_text(encoding="utf-8")

    def test_fail_exit1(self, tmp_path):
        from tests.unit.test_report_longitudinal import _mk_project
        from tools.report_longitudinal import main

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 95, 2: 80, 3: 79},
            target=84000,
            cjk_per_ch=28000,
        )
        assert main([str(tmp_path)]) == 1

    def test_data_error_exit2(self, tmp_path, capsys):
        from tools.report_longitudinal import main

        (tmp_path / "novel.json").write_text("{ broken", encoding="utf-8")
        assert main([str(tmp_path)]) == 2
        assert "novel.json" in capsys.readouterr().err
        assert not (tmp_path / "metrics").exists()  # data-error 不写盘（fail-closed）


class TestJustfileRecipes:
    """recipe 在场 + 语义三要素 + check 不调用。"""

    def test_e2e_recipes_present_and_semantics_documented(self):
        justfile = Path(__file__).resolve().parent.parent.parent / "justfile"
        text = justfile.read_text(encoding="utf-8")
        assert "e2e-report" in text and "e2e-canary" in text
        assert "#!/usr/bin/env bash" in text.split("e2e-report")[1][:200]  # shebang 形式
        canary_block = text.split("e2e-canary")[1][:900]
        assert "checkpoint" in canary_block and "pipeline-review" in canary_block

    def test_check_does_not_invoke_e2e(self):
        justfile = Path(__file__).resolve().parent.parent.parent / "justfile"
        text = justfile.read_text(encoding="utf-8")
        check_block = text.split("\ncheck:")[1].split("\n\n")[0] if "\ncheck:" in text else ""
        assert "e2e-report" not in check_block and "e2e-canary" not in check_block


class TestMalformedStateFacesExit2:
    """PR #237 Copilot：malformed state 结构 → exit-2 而非 AttributeError 崩溃。"""

    def test_chapter_loop_non_dict_is_data_error(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, load_state_dict

        (tmp_path / "pipeline-state.json").write_text('{"chapter_loop": "oops"}', encoding="utf-8")
        with pytest.raises(LongitudinalDataError, match="chapter_loop"):
            load_state_dict(tmp_path)

    def test_checkpoint_history_non_list_is_data_error(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, load_state_dict

        (tmp_path / "pipeline-state.json").write_text('{"checkpoint_history": 7}', encoding="utf-8")
        with pytest.raises(LongitudinalDataError, match="checkpoint_history"):
            load_state_dict(tmp_path)

    def test_cli_maps_malformed_state_to_exit2(self, tmp_path):
        from tools.report_longitudinal import main

        (tmp_path / "novel.json").write_text(
            '{"target_word_count": 3000, "total_chapters": 3}', encoding="utf-8"
        )
        (tmp_path / "pipeline-state.json").write_text('{"chapter_loop": []}', encoding="utf-8")
        assert main([str(tmp_path)]) == 2
