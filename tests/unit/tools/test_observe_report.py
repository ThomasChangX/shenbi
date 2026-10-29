"""Spec #81 §3: observe_report four tables + coverage row (offline corpora)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

_TOOL = Path(__file__).resolve().parents[3] / "tools" / "observe_report.py"
_spec = importlib.util.spec_from_file_location("observe_report", _TOOL)
assert _spec is not None and _spec.loader is not None
observe_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(observe_report)
build_report = observe_report.build_report


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )


def _seed_corpus(tmp_path: Path) -> None:
    # ledger: 3 rows, all attempt=1 (2 skills × chapters)
    _write_jsonl(
        tmp_path / "cost" / "token-ledger.jsonl",
        [
            {
                "skill": "shenbi-chapter-drafting",
                "chapter": 1,
                "prompt_tokens": 21000,
                "attempt": 1,
                "estimated": False,
            },
            {
                "skill": "shenbi-chapter-drafting",
                "chapter": 2,
                "prompt_tokens": 23000,
                "attempt": 1,
                "estimated": False,
            },
            {
                "skill": "shenbi-state-settling",
                "chapter": 2,
                "prompt_tokens": 42000,
                "attempt": 1,
                "estimated": False,
            },
        ],
    )
    # trace: INIT + 2 DISPATCH (one loop_id=4 with a fields miss) + 1 RETRY
    from shenbi.trace.writer import TraceWriter

    w = TraceWriter(tmp_path)
    w.append(actor="t", actor_role="SYSTEM", action="INIT", target="t")
    w.append(
        actor="dispatch_helper",
        actor_role="SYSTEM",
        action="DISPATCH",
        target="skill:shenbi-chapter-drafting",
        skill="shenbi-chapter-drafting",
        payload={
            "chapter": 1,
            "loop_id": 4,
            "reads": [{"path": "style/style_profile.md", "mode": "fields", "matched_all": False}],
        },
    )
    w.append(
        actor="dispatch_helper",
        actor_role="SYSTEM",
        action="DISPATCH",
        target="skill:shenbi-chapter-drafting",
        skill="shenbi-chapter-drafting",
        payload={"chapter": 2, "loop_id": 0},
    )
    w.append(
        actor="chapter-loop",
        actor_role="SYSTEM",
        action="RETRY",
        target="ch2",
        skill="shenbi-chapter-drafting",
        payload={
            "chapter": 2,
            "skill": "shenbi-chapter-drafting",
            "reason": {
                "kind": "monitor_rewind",
                "chapter": 2,
                "issues": ["word_band:ch2:total_chars 1995 不在带 [2800,4000]"],
            },
            "loop_id": 1,
        },
    )
    # dispatches: 3 records, one shared system blob (dedup), real blobs on disk
    blobs = tmp_path / "observability" / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    import hashlib

    def _put(content: str) -> str:
        h = hashlib.sha256(content.encode()).hexdigest()
        (blobs / h).write_text(content, encoding="utf-8")
        return f"sha256:{h}"

    shared_sys = _put("SYS")
    recs = [
        {
            "seq": 1,
            "skill": "shenbi-chapter-drafting",
            "chapter": 1,
            "loop_id": 4,
            "system_prompt_blob": shared_sys,
            "user_prompt_blob": _put("U1"),
            "response_blob": _put("R1"),
            "reads": [],
        },
        {
            "seq": 2,
            "skill": "shenbi-chapter-drafting",
            "chapter": 2,
            "loop_id": 0,
            "system_prompt_blob": shared_sys,
            "user_prompt_blob": _put("U2"),
            "response_blob": _put("R2"),
            "reads": [],
        },
        {
            "seq": 3,
            "skill": "shenbi-state-settling",
            "chapter": 2,
            "loop_id": None,
            "system_prompt_blob": shared_sys,
            "user_prompt_blob": _put("U3"),
            "response_blob": None,
            "reads": [],
        },
    ]
    d = tmp_path / "observability" / "dispatches"
    d.mkdir(parents=True, exist_ok=True)
    for i, rec in enumerate(recs, 1):
        (d / f"{i:05d}-x-ch001-a1.json").write_text(
            json.dumps(rec, ensure_ascii=False), encoding="utf-8"
        )
    # escape state: one streak=2
    (tmp_path / "observability" / "escape-hatch-state.json").write_text(
        json.dumps({"streaks": {"style/style_profile.md|文风基准": {"streak": 2}}}),
        encoding="utf-8",
    )
    # stats: three keys zero
    (tmp_path / "observability" / "archive-stats.json").write_text(
        json.dumps(
            {"archive_write_failed": 0, "archive_quota_skip": 0, "archive_seq_collision": 0}
        ),
        encoding="utf-8",
    )


class TestReport:
    def test_four_tables_and_coverage_row(self, tmp_path: Path):
        _seed_corpus(tmp_path)
        md = build_report(tmp_path)
        for header in ("## 膨胀曲线", "## Loop depth", "## 失败簇", "## 逃逸舱", "## 归档覆盖"):
            assert header in md
        assert "ledger=3" in md and "archive=3" in md  # 覆盖行对账（attempt=1 口径）
        assert "monitor_rewind" in md  # 失败簇聚类
        assert "word_band:ch2" in md  # sample 原串
        assert "archive_quota_skip=0" in md  # WARN 三键汇总行
        assert "| 4 |" in md  # Loop depth: drafting ch1 max loop_id=4

    def test_dedup_ratio_and_blob_existence(self, tmp_path: Path):
        _seed_corpus(tmp_path)  # 3 档共用 SYS blob → stored < referenced
        md = build_report(tmp_path)
        assert "去重率" in md
        assert "blob 存在性: 8/8" in md  # 3 档 × 指针（SYS×3+U×3+R×2）全存在
        assert "0." in md.split("去重率")[1].split("（")[0]  # 比率 <1（去重生效）

    def test_missing_surfaces_degrade_to_explicit_note(self, tmp_path: Path):
        (tmp_path / "trace.jsonl").write_text("", encoding="utf-8")
        md = build_report(tmp_path)
        assert "无归档" in md  # 特性前项目明示降级，不炸
        assert "ledger=0" not in md or "archive=0" in md  # 不出现假对账

    def test_quota_skipped_blob_shows_degradation(self, tmp_path: Path):
        _seed_corpus(tmp_path)
        # 删一个 blob 文件 = 配额跳过/丢失形态 → 存在性降级注记
        blobs = tmp_path / "observability" / "blobs"
        next(iter(sorted(blobs.iterdir()))).unlink()
        md = build_report(tmp_path)
        assert "哈希在、内容失" in md
