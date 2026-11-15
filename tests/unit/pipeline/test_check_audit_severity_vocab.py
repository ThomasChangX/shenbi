"""Spec #105 T2: G4.av.vocab — out-of-vocab severity is a hard, discriminated gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.llm_output_integrity import check_audit_severity_vocab


def _issues(tmp_path: Path, content: str) -> list[str]:
    f = tmp_path / "chapter-9-x.md"
    f.write_text(content, encoding="utf-8")
    return check_audit_severity_vocab(f)


@pytest.mark.parametrize(
    "content",
    [
        "- [MAJOR] 节奏断裂",
        "**BLOCKER** 全章失控",
        "严重度: 严重",
        "严重度: 高",
        "严重度: 高。",  # r3-I1: 尾部标点剥离红钉（进 parametrize 非 prose）
        "- [major] 节奏断裂",
        "Severity: MAJOR",
    ],
)
def test_out_of_vocab_red(tmp_path: Path, content: str) -> None:
    assert any(i.startswith("G4.av.vocab:") for i in _issues(tmp_path, content))


@pytest.mark.parametrize(
    "content",
    [
        "- [MINOR] 措辞建议",
        "- [minor] 措辞建议",
        "本章有一点 major 问题。",
        "severity:BLOCKING/CRITICAL/MINOR",
        "**严重度**：BLOCKING / CRITICAL / MINOR",
        "**判定**: 通过",
        "**章节**: 第 9 章",
        "- [读者回报] 回报偏弱",
        "- [MINOR·观察] 观察",
        "**严重度**",
        "**Severity**",
        '"severity": "low"',  # M-5: 引号值绿测（r4-I1 gap 类防御验收钉——非 QUOTED_VALUE_TAIL，r5-M2 归因更正）
        "严重度: ERROR（对应 BLOCKING）",  # r2-M2: 括注剥离——剥后 ERROR∈词表 PASS（不剥=误报）
        "| 严重度 | 结果 |",  # 表头 key 名——非声明
    ],
)
def test_in_vocab_or_exempt_green(tmp_path: Path, content: str) -> None:
    assert not any(i.startswith("G4.av.vocab:") for i in _issues(tmp_path, content))
