"""G5_CHECKER_GLOBS is module-level and importable (spec #60 T0a-1)."""

from shenbi.gates.g5 import G5_CHECKER_GLOBS


def test_globs_module_level_importable():
    assert isinstance(G5_CHECKER_GLOBS, dict)
    assert G5_CHECKER_GLOBS["shenbi-worldbuilding"] == [
        "novel.json",
        "genre-config.json",
        "world/*.md",
        "truth/*.md",
    ]


def test_globs_entry_count_baseline():
    # 19 at extraction time; Task 8 adds 9 -> 28. Pin the floor, not the ceiling.
    assert len(G5_CHECKER_GLOBS) >= 19
