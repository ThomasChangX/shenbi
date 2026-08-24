"""R5 (F637): pending_hooks dual-source canonical writer + union migration."""

from pathlib import Path

from shenbi.records.drift import detect_cross_section_drift, parse_markdown_table
from shenbi.records.parser import parse_records
from shenbi.records.writer import collect_records, render_pending_hooks

FIXTURE = Path("tests/fixtures/truth-pending_hooks.md")  # 真实产物 (G0.9)


def test_collect_records_union_all_sources():
    """fixture(frontmatter 无 hooks、body YAML+表全)→ 三源并入不丢记录。"""
    records = collect_records(FIXTURE.read_text(encoding="utf-8"))
    ids = {r["id"] for r in records}
    assert {"hook-ch1-001", "hook-ch1-002", "hook-ch1-003"} <= ids


def test_collect_records_body_only_freetext():
    """body-only 自由文本生产态: ID 扫描兜底得 PENDING 记录, 非空集。
    (合成 stimulus: collect_records 纯函数输入, 非 fixture 产物)
    """
    text = "# 伏笔池\n\n主角提到 H7 与 P0-3 已种下。\n"
    records = collect_records(text)
    ids = {r["id"] for r in records}
    assert {"H7", "P0-3"} <= ids
    for r in records:
        if r["id"] in ("H7", "P0-3"):
            assert r["state"] == "PENDING"
            assert r["type"] == ""


def test_collect_records_field_level_merge_body_wins():
    """同 id 双源: body 值优先, frontmatter 富字段保留。"""
    text = (
        "---\nhooks:\n- id: H1\n  state: PLANTED\n  content: 富字段\n---\n\n"
        "## hooks\n\n- id: H1\n  state: RESOLVED\n"
    )
    records = collect_records(text)
    assert len(records) == 1
    assert records[0]["state"] == "RESOLVED"
    assert records[0]["content"] == "富字段"


def test_render_roundtrip_idempotent_and_drift_free():
    """验收: writer 往返幂等 + append 后 detect_cross_section_drift == []。"""
    text = FIXTURE.read_text(encoding="utf-8")
    once = collect_records(text)
    rendered = render_pending_hooks(once)
    twice = collect_records(rendered)
    assert [r["id"] for r in once] == [r["id"] for r in twice]  # 首现序稳定
    assert detect_cross_section_drift(parse_records(rendered), parse_markdown_table(rendered)) == []


def test_render_resembles_real_fixture_shape():
    rendered = render_pending_hooks(collect_records(FIXTURE.read_text(encoding="utf-8")))
    assert rendered.startswith("---\n")
    assert "## hooks" in rendered
    assert "## 活跃伏笔" in rendered
    assert "| Hook ID |" in rendered
