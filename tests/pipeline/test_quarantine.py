"""T2b: quarantine + 截断拒绝 + 提取器硬化(spec #38 F329/T509/F234/F223)。

G0.9 说明:`### FILE:` 输入为手工构造的最小形态字符串而非 fixtures 引用——
本测试面是解析器边界行为(截断签名/缺失路径),非 skill 产物内容;构造性输入
对应被测代码路径的确定形态,引用真实产物无法制造"截断在最后一个 FILE 块"
这一受控条件。
"""

import pytest

from shenbi.contracts.paths import AmbiguousChapterError, extract_chapter
from shenbi.contracts.skills.pacing_design import PacingDesign
from shenbi.pipeline.dispatch_helper import (
    _is_truncated_file_output,
    _quarantine_output,
    _write_parsed_outputs,
)


class TestQuarantine:
    def test_missing_literal_path_quarantines_not_written(self, tmp_path) -> None:
        """F329:literal 路径不在 parsed → 不回退 __stdout__,quarantine 原始输出。"""
        parsed = {"a.md": "content-a"}
        written = _write_parsed_outputs(
            "raw response body",
            ["a.md", "b.md"],
            tmp_path,
            skill="shenbi-example",
            parsed=parsed,
        )
        assert "a.md" in written
        assert "b.md" not in written
        assert not (tmp_path / "b.md").exists()
        qfiles = list((tmp_path / "_quarantine").glob("shenbi-example-*.md"))
        assert len(qfiles) == 1  # dedup: one quarantine per call, not per path
        assert "raw response body" in qfiles[0].read_text(encoding="utf-8")

    def test_stdout_declared_path_still_written(self, tmp_path) -> None:
        """回归:`__stdout__` 作为契约声明路径正常落盘。"""
        written = _write_parsed_outputs(
            "whole output",
            ["__stdout__"],
            tmp_path,
            skill="shenbi-example",
            parsed={"__stdout__": "whole output"},
        )
        assert "__stdout__" in written


class TestTruncation:
    def test_truncated_file_output_detected(self) -> None:
        """T509:末个 ### FILE: 块无内容 → 截断。"""
        truncated = "### FILE: a.md\nsome content\n\n### FILE: b.md\n"
        assert _is_truncated_file_output(truncated) is True

    def test_complete_file_output_not_truncated(self) -> None:
        complete = "### FILE: a.md\nsome content\n\n### FILE: b.md\nmore content\n"
        assert _is_truncated_file_output(complete) is False

    def test_truncated_output_rejected_before_write(self, tmp_path) -> None:
        """截断输出 → 不落任何目标,quarantine 原始 stdout,结构化失败。"""
        from shenbi.exceptions import DispatchWriteFailureError

        truncated = "### FILE: a.md\nsome content\n\n### FILE: b.md\n"
        with pytest.raises(DispatchWriteFailureError, match="truncated"):
            _write_parsed_outputs(truncated, ["a.md", "b.md"], tmp_path, skill="shenbi-example")
        assert not (tmp_path / "a.md").exists()
        assert list((tmp_path / "_quarantine").glob("shenbi-example-*.md"))


class TestExtractChapterStrict:
    def test_ambiguous_raises_in_strict(self) -> None:
        with pytest.raises(AmbiguousChapterError):
            extract_chapter("chapter 3 draft and chapter 7 review", strict=True)

    def test_single_chapter_strict_ok(self) -> None:
        assert extract_chapter("chapter 3 draft", strict=True) == 3

    def test_default_behavior_unchanged(self) -> None:
        assert extract_chapter("chapter 3 draft and chapter 7 review") == 3


class TestPacingFromMarkdown:
    def test_prose_numbers_not_harvested(self) -> None:
        """F223:散文句中的数字不污染 beat 提取——beats 为空触发结构化
        ValidationError(收紧:不采散文数字,缺 beat 即显性失败)。
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="missing beats"):
            PacingDesign.from_markdown("第 3 章预算 25% 用于铺垫,后续再议。")

    def test_structured_row_harvested(self) -> None:
        d = PacingDesign.from_markdown(
            "| 铺垫 | 25% |\n| 升级: 30% |\n| 爆发: 30% |\n| 余波: 15% |"
            "\n| QUEST: 60% |\n| FIRE: 25% |\n| CONSTELLATION: 15% |\n"
            "battle dialogue introspection transition exploration conspiracy escape revelation emotion"
        )
        assert d.beats.get("铺垫") == 25.0
        assert d.beats.get("升级") == 30.0


def test_quarantine_output_direct(tmp_path) -> None:
    p = _quarantine_output(tmp_path, "shenbi-x", "raw text", "missing literal path")
    assert p.exists()
    assert "missing literal path" in p.read_text(encoding="utf-8")
    assert "raw text" in p.read_text(encoding="utf-8")
