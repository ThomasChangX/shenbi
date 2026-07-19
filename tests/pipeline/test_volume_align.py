"""Test volume alignment checker."""

from shenbi.pipeline.volume_align import (
    check_volume_alignment,
    extract_chapter_node,
    extract_key_terms,
)


def test_extract_chapter_node(tmp_path):
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True)
    vm = outline_dir / "volume_map.md"
    vm.write_text("""
## Chapter 5: The Bridge

Key terms: bridge, crossing, river, danger

### Chapter 6: The Gate

Key terms: gate, city, guard, entry
""")
    node = extract_chapter_node(vm, 5)
    assert node is not None
    assert "bridge" in node["desc"]


def test_extract_key_terms():
    text = "Key terms: bridge, crossing, river, danger"
    terms = extract_key_terms(text)
    assert "bridge" in terms


def test_high_match_rate_no_warning(tmp_path):
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True)
    vm = outline_dir / "volume_map.md"
    vm.write_text("## Chapter 3: Test\n\nKey terms: copper, coin, mystery")
    issues = check_volume_alignment(tmp_path, 3, "copper coin mystery in the scrapyard")
    # Should not produce warning when key terms match
    assert not any("WARNING" in i for i in issues)


def test_low_match_rate_warns(tmp_path):
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir(parents=True)
    vm = outline_dir / "volume_map.md"
    vm.write_text("## Chapter 3: Test\n\nKey terms: copper, coin, mystery, smith")
    issues = check_volume_alignment(tmp_path, 3, "unrelated content about flowers")
    assert any("WARNING" in i for i in issues)
