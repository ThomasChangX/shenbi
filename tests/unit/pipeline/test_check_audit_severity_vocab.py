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


def test_production_forms_key_only_ignores_bracket_bold(tmp_path: Path) -> None:
    """audit-T4 disposition (a): production wires the key form only.

    Bracket/bold wildcards cannot reach zero false positives (199 vol1 hits);
    they stay on the replay face for #116 data collection.
    """
    from shenbi.pipeline.llm_output_integrity import PRODUCTION_VOCAB_FORMS

    f = tmp_path / "chapter-9-x.md"
    f.write_text("- [MAJOR] 节奏断裂\n**BLOCKER** 失控\n严重度: 严重\n", encoding="utf-8")
    issues = check_audit_severity_vocab(f, forms=PRODUCTION_VOCAB_FORMS)
    assert len(issues) == 1, issues  # 只有 key 形触发
    assert "严重" in issues[0]
    # 全形态默认仍捕获三条（回放/#116 面）
    assert len(check_audit_severity_vocab(f)) == 3


def test_resonance_verdict_word_not_severity(tmp_path: Path) -> None:
    """audit-T4 disposition (d): `阻断` is a ResonanceVerdict-domain word."""
    f = tmp_path / "chapter-13-resonance.md"
    f.write_text("**阻断**\n", encoding="utf-8")
    assert check_audit_severity_vocab(f) == []
