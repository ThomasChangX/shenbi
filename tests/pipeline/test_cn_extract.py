"""R6: Chinese node/bridge/volume-context extraction (spec #6 direction 6).

Real fixture driven (tests/fixtures/volume-map-xinghuo.md, G0.9/G0.11).
"""

from pathlib import Path

from shenbi.pipeline._shared import (
    _resolve_volume_at_runtime,
    bridges_for_chapter,
    read_bridges,
    read_chapter_node,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"
TEXT = FIXTURE.read_text(encoding="utf-8")


def test_chapter_nodes_from_ch5_not_garbage():
    """Acceptance: ch5+ nodes non-None, role/content not bridge garbage."""
    for ch in (5, 26, 56):
        node = read_chapter_node(TEXT, ch)
        assert node is not None, f"ch{ch} node missing"
        assert node["role"].strip()
        assert "梵天铭文" not in node["content"]  # bridge content must not leak into nodes


def test_bridges_aggregate_all_five_sections():
    """Acceptance: aggregate ALL five bridge sections (not just volume 1)."""
    bridges = read_bridges(TEXT)
    activations = {b.activation for b in bridges if b.activation}
    assert 36 in activations  # vol-2 table
    assert 26 in activations  # vol-1 table


def test_vol1_bridge_surfaces_at_26_vol2_at_36_not_30():
    b = read_bridges(TEXT)
    at26 = bridges_for_chapter(b, 26)
    at30 = bridges_for_chapter(b, 30)
    at36 = bridges_for_chapter(b, 36)
    at40 = bridges_for_chapter(b, 40)
    assert any(
        "梵天铭文" in s for s in at26
    )  # vol-1 row (activation 26-28 -> min 26, compact range)
    # vol-2 section real rows (volume_map.md:165-168)
    assert not any("操纵战争的铁证" in s or "科恩·怀特曼" in s for s in at30)  # not @30
    assert any("操纵战争的铁证" in s for s in at36)  # @36
    assert any("科恩·怀特曼" in s for s in at40)  # @40


def test_sequel_rows_excluded():
    """Acceptance (negative): sequel rows excluded by predicate, not by window."""
    b = read_bridges(TEXT)
    assert not any("续作" in x.target_volume for x in b)
    for ch in range(1, 11):
        for s in bridges_for_chapter(b, ch):
            assert "星际探索飞船" not in s


def test_volume_context_real_names(tmp_path):
    """Acceptance: volume context non-empty on Chinese projects (real names)."""
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    (proj / "outline" / "volume_map.md").write_text(TEXT, encoding="utf-8")
    got = _resolve_volume_at_runtime(proj, 20)
    assert got is not None
    name, start, end = got
    assert name == "第二卷：铁与火"  # real header, suffix stripped, not "Volume 2"
    assert (start, end) == (16, 35)


def test_context_assemble_volume_block_end_to_end(tmp_path):
    """Consumer end-to-end: volume context block non-empty on Chinese projects."""
    from shenbi.pipeline.context_assemble import _load_volume_context

    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    (proj / "outline" / "volume_map.md").write_text(TEXT, encoding="utf-8")
    block = _load_volume_context(proj, 20)
    assert "第二卷" in block and "铁与火" in block  # returns str


def test_english_node_regression():
    """English `| N |` flush-left rows are NOT matched (bare form dropped by
    design — the R6 garbage bug; legacy English maps deferred to #16/#25).
    """
    en = "## Volume 1\n\n| 5 | opening | hero awakens |\n"
    assert read_chapter_node(en, 5) is None
