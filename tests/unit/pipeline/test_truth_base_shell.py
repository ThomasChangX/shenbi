"""Base-state shell predicate + single-table header bootstraps (batch #15 #44/#38).

probe20 death chain (adjudication /tmp/probe20-adjudication-008.md): the
escalation-reject ``clear_staging`` destroyed reviewed settle staging, the
re-dispatch feedback described a world the shell bases did not carry, and
the model's only rational output — a whole-file creation form — was
rejected by a guard with no first-write exemption for chapter-keyed
targets. The shell predicate below is the shared decision core: SHELL
means "no real data to protect" (creation form sanctioned), FILLED means
the scaffold ban is live (rows/field increments only).
"""

from __future__ import annotations

from typing import ClassVar

from shenbi.pipeline.truth_io import _TABLE_HEADER_BOOTSTRAP, base_is_shell, ensure_table_header

#: probe20 truth/current_state.md verbatim (status: initialized template):
#: frontmatter + H1 + quote + （待填充） placeholder sections, zero data.
_SHELL_CURRENT_STATE = """---
type: truth
category: state
status: initialized
generated_at: 2026-10-02T22:55:40Z
---

# 当前世界状态

> 此文件由 state-settling 首次运行时填充实际数据。

## 时间锚

（待填充）

## 势力态势

（待填充）

## 主角处境

（待填充）

## 待处理压力

（待填充）
"""

#: probe20 truth/chapter_summaries.md template head: instructional prose
#: under ## 格式约定 is guidance, not data.
_SHELL_SUMMARIES = """---
type: truth
category: state
status: initialized
---

# 逐章摘要

> 此文件由 state-settling 首次运行时填充实际数据。

## 格式约定

每章一条，记录：章号 / 一句话事件 / 出场角色 / 推进的支线 / 新增或回收的伏笔 / 结尾钩子。

## 已归档章节

（待填充）
"""

_FILLED_CURRENT_STATE = """---
type: truth
category: state
status: filled
---

# 当前世界状态

| 章节 | 位置 | 时间锚 | 主角处境 | 势力态势 | 待处理压力 |
|------|------|--------|---------|---------|-----------|
| 第1章 | 三号采灵场井下 | 落潮夜 | 瞒报老刘 | 查点丁口 | 老刘之死 |
"""


class TestBaseIsShell:
    def test_template_sections_with_placeholders_are_shell(self):
        assert base_is_shell(_SHELL_CURRENT_STATE) is True

    def test_instructional_prose_is_ignorable(self):
        assert base_is_shell(_SHELL_SUMMARIES) is True

    def test_empty_and_blank_are_shell(self):
        assert base_is_shell("") is True
        assert base_is_shell("   \n\n  ") is True

    def test_real_table_row_is_filled(self):
        assert base_is_shell(_FILLED_CURRENT_STATE) is False

    def test_placeholder_only_table_row_is_still_shell(self):
        text = "# 表\n\n| 章节 | 位置 |\n|------|------|\n| （待填充） | （待填充） |\n"
        assert base_is_shell(text) is True

    def test_structural_header_separator_rows_only_are_shell(self):
        text = "# 表\n\n| 章节 | 位置 |\n|------|------|\n"
        assert base_is_shell(text) is True

    def test_hook_heading_is_filled(self):
        assert base_is_shell("# 伏笔池\n\n### MH01（灯座划痕）\n- type: SYMBOLIC\n") is False

    def test_real_data_bullet_is_filled(self):
        assert base_is_shell("# 账\n\n- 灯油: 见底\n") is False

    def test_real_prose_outside_instructional_sections_is_filled(self):
        assert base_is_shell("# 状态\n\n主角已在井口报数十一。\n") is False

    def test_genesis_hook_registry_quote_and_template_placeholder_is_shell(self):
        text = (
            "---\ntype: truth\ncategory: state\nstatus: initialized\n---\n\n"
            "# 伏笔池\n\n> 此文件由 state-settling 首次运行时填充实际数据。\n\n"
            "（待填充：已埋设伏笔、埋设章节、计划回收章节、当前状态。）\n"
        )
        assert base_is_shell(text) is True


class TestSingleTableBootstraps:
    """#38/#44: five single-table keyed files get contract-header bootstraps.

    emotional_arcs (dual-table) and character_matrix (genesis-filled) are
    deliberately absent; audit_drift is YAML-form and owned by a
    create_or_overwrite merger — a markdown header would corrupt it.
    """

    EXPECTED: ClassVar[dict[str, int | None]] = {
        "current_state.md": 6,
        "particle_ledger.md": 5,
        "subplot_board.md": 5,
        "chapter_summaries.md": 6,
        "arc_payoff_trend.md": None,  # column count pinned by header itself
    }

    def test_single_table_and_composite_files_registered(self):
        for name in self.EXPECTED:
            assert name in _TABLE_HEADER_BOOTSTRAP, f"{name} must have a bootstrap header"
        # #18-6 (probe24): the composite-key files joined the map — their
        # contract keys only activate via the header, and a headerless first
        # write degrades 章节,角色/角色A,角色B to first-column. audit_drift
        # stays out (YAML-form owned by a create_or_overwrite merger).
        assert "emotional_arcs.md" in _TABLE_HEADER_BOOTSTRAP
        assert "character_matrix.md" in _TABLE_HEADER_BOOTSTRAP
        assert "audit_drift.md" not in _TABLE_HEADER_BOOTSTRAP

    def test_bootstrap_prepends_header_and_separator_on_bare_row(self):
        header = _TABLE_HEADER_BOOTSTRAP["current_state.md"]
        out = ensure_table_header(
            "current_state.md", "| 第1章 | 井下 | 落潮夜 | 瞒报 | 查点 | 压力 |"
        )
        assert out.split("\n")[0] == header
        assert out.split("\n")[1] == "|" + "---|" * (header.count("|") - 1)
        assert "| 第1章 |" in out

    def test_bootstrap_idempotent_when_header_present(self):
        content = _FILLED_CURRENT_STATE
        assert ensure_table_header("current_state.md", content) == content

    def test_bootstrap_appends_header_on_frontmatter_stub_base(self):
        """#38 extension (probe22 adjudication #006 P1-2): a frontmatter stub
        base (``---`` first line, zero pipe rows) triggered NEITHER bootstrap
        branch — the first write chained data rows onto a headerless shell
        and _key_columns silently degraded composite keys to first-column.
        Headers are the composite-key ACTIVATION condition: on a table-less
        shell the contract header must be appended where the rows will land
        (EOF).
        """
        out = ensure_table_header("subplot_board.md", _SHELL_CURRENT_STATE)
        header = _TABLE_HEADER_BOOTSTRAP["subplot_board.md"]
        lines = out.rstrip("\n").split("\n")
        assert lines[-2] == header
        assert lines[-1] == "|" + "---|" * (header.count("|") - 1)
        assert _SHELL_CURRENT_STATE.rstrip() in out  # shell preserved verbatim
        # idempotent: the second write sees the header and changes nothing
        assert ensure_table_header("subplot_board.md", out) == out

    def test_registered_headers_start_with_key_column(self):
        """The key column must be first for the keyed upsert to address rows."""
        for name in self.EXPECTED:
            first_cell = _TABLE_HEADER_BOOTSTRAP[name].split("|")[1].strip()
            assert first_cell in ("章节", "chapter", "volume", "Bridge ID"), (
                f"{name}: key column must lead the pinned header (got {first_cell!r})"
            )
