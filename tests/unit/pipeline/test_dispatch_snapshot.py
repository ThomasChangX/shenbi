"""Spec #81 §1: raw disk snapshot captured pre-filter/pre-strip (O-2 semantics)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shenbi.contracts import OutputKind


def _mock_contract() -> dict[str, Any]:
    # 脚手架形态取自 tests/unit/pipeline/test_dispatch_helper.py::
    # test_multi_file_prompt_includes_schema_reminder（builder 直调 + mock 契约）
    return {
        "kind": OutputKind.ARTIFACT,
        "reads": ["style/style_profile.md"],
        "read_fields": {"style/style_profile.md": ["文风基准"]},
        "writes": ["chapters/chapter-1.md"],
        "updates": [],
    }


def test_raw_snapshot_is_disk_original_not_filtered_view(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("shenbi.contracts.loader.load_contract", lambda s: _mock_contract())
    target = tmp_path / "style" / "style_profile.md"
    target.parent.mkdir(parents=True)
    # 一节命中契约字段、一节不命中——fields 过滤视图必然丢第二节（:1100 filter_to_fields）
    target.write_text("## 文风基准\n命中内容\n## 漂移节\n独有内容\n", encoding="utf-8")

    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    system_prompt, user_prompt, output_paths, reads_manifest, raw_reads = _build_skill_prompt(
        "shenbi-chapter-drafting", tmp_path, "draft chapter 1", 1
    )

    key = next(k for k in raw_reads if "style_profile" in k)
    assert "漂移节" in raw_reads[key]  # 磁盘原文保留未命中节（pre-filter 捕获）
    assert "漂移节" not in user_prompt  # 注入面仍是过滤视图（行为不变）
    fields_entry = next(r for r in reads_manifest if r.get("mode") == "fields")
    assert fields_entry["matched_all"] is True  # 命中节在，声明字段全中
    assert fields_entry["resolved_fields"] == ["文风基准"]


def test_partial_hit_resolved_fields_subset(tmp_path: Path, monkeypatch):
    """Partial-hit form per spec #81 section 1 example: resolved_fields non-empty + matched_all False."""
    contract = _mock_contract()
    contract["read_fields"]["style/style_profile.md"] = ["文风基准", "不存在的节"]
    monkeypatch.setattr("shenbi.contracts.loader.load_contract", lambda s: contract)
    target = tmp_path / "style" / "style_profile.md"
    target.parent.mkdir(parents=True)
    target.write_text("## 文风基准\n命中内容\n", encoding="utf-8")

    from shenbi.pipeline.dispatch_helper import _build_skill_prompt

    *_rest, reads_manifest, raw_reads = _build_skill_prompt(
        "shenbi-chapter-drafting", tmp_path, "draft chapter 1", 1
    )
    entry = next(r for r in reads_manifest if r.get("mode") == "fields")
    assert entry["matched_all"] is False  # 逃生舱全量注入
    assert entry["resolved_fields"] == ["文风基准"]  # 命中的子集如实记
    key = next(k for k in raw_reads if "style_profile" in k)
    assert "命中内容" in raw_reads[key]
