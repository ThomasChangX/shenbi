"""Spec #105 T2: G4.av.vocab — out-of-vocab severity is a hard, discriminated gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.llm_output_integrity import (
    ALL_VOCAB_FORMS,
    check_audit_severity_vocab,
)


def _issues(tmp_path: Path, content: str, forms=ALL_VOCAB_FORMS) -> list[str]:
    f = tmp_path / "chapter-9-x.md"
    f.write_text(content, encoding="utf-8")
    return check_audit_severity_vocab(f, forms=forms)


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
    # 全形态显式传参捕获三条（回放/#116 面；默认已是生产 key-only）
    assert len(check_audit_severity_vocab(f, forms=ALL_VOCAB_FORMS)) == 3


def test_resonance_verdict_word_not_severity(tmp_path: Path) -> None:
    """audit-T4 disposition (d): `阻断` is a ResonanceVerdict-domain word."""
    f = tmp_path / "chapter-13-resonance.md"
    f.write_text("**阻断**\n", encoding="utf-8")
    assert check_audit_severity_vocab(f) == []


# ── audit-T4 I-1: markdown emphasis / cross-line / Level-word capture ────────


@pytest.mark.parametrize(
    "content",
    [
        "**严重度**：**高**",  # bolded CJK value — must still FAIL
        "严重度: **高**",
        "- **严重度**: **严重**",
        "Severity Level: MAJOR",  # capture must be MAJOR, not LEVEL
    ],
)
def test_bolded_value_and_level_word_red(tmp_path: Path, content: str) -> None:
    assert any(i.startswith("G4.av.vocab:") for i in _issues(tmp_path, content)), content


@pytest.mark.parametrize(
    "content",
    [
        "**严重度**：**BLOCKING**",  # bolded in-vocab value must PASS (no `BLOCKING**` token)
        "**严重度**\n**BLOCKING**",  # cross-line must not bridge into one key capture
    ],
)
def test_bolded_in_vocab_value_green(tmp_path: Path, content: str) -> None:
    assert not any(i.startswith("G4.av.vocab:") for i in _issues(tmp_path, content)), content


def test_anchor_regexes_do_not_match_bare_words() -> None:
    """audit-T5 I1: the bracket/bold anchors must be group-wrapped — a bare
    severity word mid-line is never an anchor.
    """
    from shenbi.contracts.severity import BOLD_ANCHOR_RE, BRACKET_ANCHOR_RE

    assert not BRACKET_ANCHOR_RE.search("plain MINOR word")
    assert not BRACKET_ANCHOR_RE.search("- [MINOR·观察] 与 BLOCKING")
    assert not BOLD_ANCHOR_RE.search("plain BLOCKING word")
    assert BRACKET_ANCHOR_RE.search("- [BLOCKING] x").group(1) == "BLOCKING"  # type: ignore[union-attr]
    assert BOLD_ANCHOR_RE.search("**MINOR**").group(1) == "MINOR"  # type: ignore[union-attr]
