"""R5: _append_to_pending_hooks preserves body sections + dual-source write."""

import shutil
from pathlib import Path

from shenbi.pipeline.hook_planting import _append_to_pending_hooks
from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records

FIXTURE = Path("tests/fixtures/truth-pending_hooks.md")


def _frontmatter_ids(text: str) -> set[str]:
    import yaml

    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1]) or {}
    return {h["id"] for h in fm.get("hooks", []) if isinstance(h, dict) and "id" in h}


def test_append_preserves_existing_body_and_table(tmp_path):
    """破坏性整写禁止: append 后既有 body/表仍在且新增记录三段同步。"""
    truth = tmp_path / "truth"
    truth.mkdir()
    target = truth / "pending_hooks.md"
    shutil.copy(FIXTURE, target)

    entries = [{"hook_id": "H99", "description": "新伏笔", "type": None, "category": None}]
    planted = _append_to_pending_hooks(tmp_path, entries, chapter=5)

    assert planted == 1
    text = target.read_text(encoding="utf-8")
    assert "## hooks" in text and "## 活跃伏笔" in text  # body 段保留
    records = parse_records(text)
    ids = {r["id"] for r in records}
    assert {"hook-ch1-001", "H99"} <= ids  # 旧记录未丢 + 新记录入 body
    fm_ids = _frontmatter_ids(text)
    assert "H99" in fm_ids  # frontmatter 同步(三个 frontmatter 读取方继续可用)
    assert detect_cross_section_drift(records, parse_markdown_table(text)) == []


def _frontmatter_only_variant() -> str:
    """历史生产 writer 形态: 真实 body 记录整体移入 frontmatter, body 全丢
    (派生自真实 skill 输出, G0.9 合法变体)。
    """
    import yaml

    real = FIXTURE.read_text(encoding="utf-8")
    records = parse_records(real)
    return (
        "---\n" + yaml.safe_dump({"hooks": records}, allow_unicode=True, sort_keys=False) + "---\n"
    )


def _body_freetext_only_variant() -> str:
    """body-only 自由文本生产态(truth_index Source-2 记载)。ID 用
    _HOOK_ID_RE 实际匹配的形态(H<N>), 映射自真实 fixture 的表行序。
    """
    real = FIXTURE.read_text(encoding="utf-8")
    n_rows = sum(1 for ln in real.splitlines() if ln.startswith("| hook-ch"))
    prose_ids = [f"H{i}" for i in range(1, n_rows + 1)]
    return (
        "# 伏笔池\n\n" + "\n".join(f"主角注意到 {hid} 的伏笔已种下。" for hid in prose_ids) + "\n"
    )


def test_append_migrates_frontmatter_only_legacy(tmp_path):
    """frontmatter-only 存量 append 后自动迁移为三段, frontmatter 记录不丢。"""
    truth = tmp_path / "truth"
    truth.mkdir()
    target = truth / "pending_hooks.md"
    target.write_text(_frontmatter_only_variant(), encoding="utf-8")
    entries = [{"hook_id": "H99", "description": "x", "type": None, "category": None}]
    _append_to_pending_hooks(tmp_path, entries, chapter=1)
    text = target.read_text(encoding="utf-8")
    assert "## hooks" in text and "## 活跃伏笔" in text
    ids = {r["id"] for r in parse_records(text)}
    assert {"hook-ch1-001", "hook-ch1-002", "hook-ch1-003", "H99"} <= ids
    assert detect_cross_section_drift(parse_records(text), parse_markdown_table(text)) == []


def test_append_dedup_reads_union_source(tmp_path):
    """去重走并集源: body-only 自由文本记录的 id 也算已存在, 不重复植入。"""
    truth = tmp_path / "truth"
    truth.mkdir()
    target = truth / "pending_hooks.md"
    target.write_text(_body_freetext_only_variant(), encoding="utf-8")
    entries = [{"hook_id": "H1", "description": "x", "type": None, "category": None}]
    assert _append_to_pending_hooks(tmp_path, entries, chapter=2) == 0
