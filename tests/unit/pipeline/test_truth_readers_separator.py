"""truth_readers table parsing: separator-row tolerance (probe14 batch #9 #6).

probe13's genesis 总览 table shipped WITHOUT a markdown separator row between
header and first data row (the SKILL template has one; the model dropped it —
markdown renders identically). Every table branch in _parse_tables starts at
``i + 2`` assuming the separator exists, so the FIRST data row (MH01) was
eaten: 16 rows parsed to 15, truth-index 31/32, MH01 silently absent from
every downstream reader. Fixture = the real probe13 output (G0.9).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.truth_readers import read_pending_hooks

_FIXTURE = Path(__file__).parents[2] / "fixtures" / "pending-hooks-probe13.md"


@pytest.mark.unit
def test_separatorless_genesis_table_keeps_first_row() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "truth").mkdir()
        (root / "truth" / "pending_hooks.md").write_text(
            _FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        hooks = read_pending_hooks(root)
    ids = {h["id"] for h in hooks}
    assert "MH01" in ids, "separatorless header must not eat the first data row"
    # the full genesis pool (probe13) carries MH01..MH16
    assert len(ids) == 16


@pytest.mark.unit
def test_table_with_separator_still_parses() -> None:
    """The canonical form (separator present) must keep working — start at
    i+1 with separator-skip, not i+2.
    """
    import tempfile

    body = (
        "# 伏笔池\n\n## 总览\n\n"
        "| Hook ID（钩子名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| MH01（测试钩子一） | PLANTED | 1 | 10（一卷） | ITEM | 0.5 | 12 | FLAT |\n"
        "| MH02（测试钩子二） | PLANTED | 2 | 12（一卷） | ITEM | 0.5 | 12 | FLAT |\n"
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "truth").mkdir()
        (root / "truth" / "pending_hooks.md").write_text(body, encoding="utf-8")
        hooks = read_pending_hooks(root)
    ids = {h["id"] for h in hooks}
    assert ids == {"MH01", "MH02"}
