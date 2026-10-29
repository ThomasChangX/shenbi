"""Spec #81 §3 escape-hatch counter tests (offline, tmp_path structural corpora)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.observability import escape as esc


def _miss(path: str = "p", fields: list[str] | None = None) -> list[dict[str, Any]]:
    return [{"path": path, "mode": "fields", "fields": fields or ["A"], "matched_all": False}]


def _hit(path: str = "p", fields: list[str] | None = None) -> list[dict[str, Any]]:
    return [{"path": path, "mode": "fields", "fields": fields or ["A"], "matched_all": True}]


class TestCounter:
    def test_three_consecutive_misses_keyed_by_path_fields(self, tmp_path: Path):
        for _ in range(2):
            esc.update_escape_hatch_state(tmp_path, _miss())
        assert esc.escape_hatch_drift_check(tmp_path) == []
        esc.update_escape_hatch_state(tmp_path, _miss())  # 第 3 次
        drift = esc.escape_hatch_drift_check(tmp_path)
        assert len(drift) == 1 and drift[0]["streak"] == 3
        assert drift[0]["key"] == "p|A"

    def test_interleaved_different_fields_do_not_reset_each_other(self, tmp_path: Path):
        # O-1 交错读语义：同文件不同 fields 声明互不干扰（spec §3 键论证）
        for _ in range(3):
            esc.update_escape_hatch_state(tmp_path, _miss(fields=["A"]))
            esc.update_escape_hatch_state(tmp_path, _hit(fields=["B"]))  # B 命中只复位 B
        assert len(esc.escape_hatch_drift_check(tmp_path)) == 1  # A 键仍满 3

    def test_matched_resets_streak(self, tmp_path: Path):
        esc.update_escape_hatch_state(tmp_path, _miss())
        esc.update_escape_hatch_state(tmp_path, _miss())
        esc.update_escape_hatch_state(tmp_path, _hit())  # 同键命中 → 连击复位
        assert esc.escape_hatch_drift_check(tmp_path) == []
        esc.update_escape_hatch_state(tmp_path, _miss())  # 复位后从 1 重新起算
        assert esc.escape_hatch_drift_check(tmp_path) == []

    def test_absent_state_file_is_pass(self, tmp_path: Path):
        assert esc.escape_hatch_drift_check(tmp_path) == []

    def test_partial_json_tolerated_with_warn(self, tmp_path: Path, monkeypatch):
        state = tmp_path / "observability" / "escape-hatch-state.json"
        state.parent.mkdir(parents=True)
        state.write_text('{"streaks": {"p|A": {"streak"', encoding="utf-8")  # 半写 JSON
        warns: list[str] = []
        monkeypatch.setattr(esc.log, "warning", lambda event, **kw: warns.append(event))
        assert esc.escape_hatch_drift_check(tmp_path) == []
        assert (
            "escape_hatch_state_read_failed" in warns
        )  # audit-T3 I-1：静默 [] 会把漂移掩成 absent-PASS

    def test_counter_runs_even_when_archive_disabled(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SHENBI_ARCHIVE_DISPATCH", "0")
        for _ in range(3):
            esc.update_escape_hatch_state(tmp_path, _miss())
        assert len(esc.escape_hatch_drift_check(tmp_path)) == 1  # 计数器照常落盘（常开）
        raw = json.loads((tmp_path / "observability" / "escape-hatch-state.json").read_text())
        assert raw["streaks"]["p|A"]["streak"] == 3

    def test_full_mode_entries_ignored(self, tmp_path: Path):
        esc.update_escape_hatch_state(
            tmp_path, [{"path": "p", "mode": "full", "matched_all": True}]
        )
        assert not (tmp_path / "observability").exists()  # 无 fields 条目 → 不落盘


class TestBuilderWiring:
    def test_builder_wiring_renamed_heading_fires_drift(self, tmp_path: Path, monkeypatch):
        """End-to-end offline form of spec acceptance 7.2: run the REAL
        builder three times against a renamed heading -- dead-wire defense
        (plan R3-I1): the builder-to-counter wiring seam needs executable
        verification, not synthetic counter state.
        """
        from shenbi.contracts import OutputKind
        from shenbi.pipeline import dispatch_helper as dh

        mock_contract = {
            "kind": OutputKind.ARTIFACT,
            "reads": ["style/style_profile.md"],
            "read_fields": {"style/style_profile.md": ["漂移前标题"]},  # 契约声明旧字段
            "writes": ["chapters/chapter-1.md"],
            "updates": [],
        }
        monkeypatch.setattr("shenbi.contracts.loader.load_contract", lambda s: mock_contract)
        target = tmp_path / "style" / "style_profile.md"
        target.parent.mkdir(parents=True)
        target.write_text("## 漂移后标题\n内容\n", encoding="utf-8")  # 人为制造字段漂移
        for _ in range(3):
            dh._build_skill_prompt("shenbi-chapter-drafting", tmp_path, "draft ch1", 1)
        drift = esc.escape_hatch_drift_check(tmp_path)
        assert len(drift) == 1  # 3 次派发内 FAIL 链条成立
        assert drift[0]["streak"] == 3  # audit-T3 M-2：恰一次/派发（双计仍绿=接线缺陷）
        assert drift[0]["path"].endswith("style_profile.md")
        assert drift[0]["fields"] == ["漂移前标题"]
