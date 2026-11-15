"""Spec #105 T2: G4.av.vocab — out-of-vocab severity is a hard, discriminated gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.llm_output_integrity import (
    ALL_VOCAB_FORMS,
    PRODUCTION_VOCAB_FORMS,
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

    Bracket/bold wildcards cannot reach zero false positives (198 vol1 all-forms hits);
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
# audit-T4 轮 2 I-1: 断言必须逐字钉 token——旧正则产出 `高**`/`LEVEL:` 时
# 「有 issue」式断言照样通过（修复不可判别）。


def _tokens(tmp_path: Path, content: str, forms=PRODUCTION_VOCAB_FORMS) -> list[str]:
    import re as _re

    f = tmp_path / "chapter-9-x.md"
    f.write_text(content, encoding="utf-8")
    out = []
    for issue in check_audit_severity_vocab(f, forms=forms):
        m = _re.search(r"「(.+?)」", issue)
        assert m, issue
        out.append(m.group(1))
    return out


def test_bolded_cjk_value_token_is_exact(tmp_path: Path) -> None:
    """Production key form: bolded CJK value must capture `高`, not `高**`."""
    assert _tokens(tmp_path, "**严重度**：**高**") == ["高"]
    assert _tokens(tmp_path, "严重度: **高**") == ["高"]
    assert _tokens(tmp_path, "- **严重度**: **严重**") == ["严重"]


def test_bolded_in_vocab_value_green(tmp_path: Path) -> None:
    """Production key form: a bolded in-vocab value must not yield `BLOCKING**`."""
    assert _tokens(tmp_path, "**严重度**：**BLOCKING**") == []
    assert _tokens(tmp_path, "严重度: **MINOR**") == []


def test_cross_line_does_not_bridge(tmp_path: Path) -> None:
    """Cross-line must not bridge into one key capture.

    Proven with the out-of-vocab BLOCKER: a bridging capture would yield
    `BLOCKER**` and FAIL.
    """
    # key-form domain (under ALL the bold form catches the next line by design)
    assert _tokens(tmp_path, "**严重度**\n**BLOCKER**", forms=PRODUCTION_VOCAB_FORMS) == []


def test_level_word_skipped_token_is_exact(tmp_path: Path) -> None:
    """Severity Level: MAJOR must capture `MAJOR`, never `LEVEL:`."""
    assert _tokens(tmp_path, "Severity Level: MAJOR") == ["MAJOR"]


def test_resonance_verdict_word_not_severity_all_forms(tmp_path: Path) -> None:
    """audit-T4 disposition (d) pin: 阻断 is no longer in the CJK family.

    Under ALL forms the bold shape **阻断** must still PASS (the old family
    produced the single vol1 false positive).
    """
    f = tmp_path / "chapter-13-resonance.md"
    f.write_text("**阻断**\n", encoding="utf-8")
    assert check_audit_severity_vocab(f, forms=ALL_VOCAB_FORMS) == []
    from shenbi.contracts.severity import CJK_SEVERITY_WORDS

    assert "阻断" not in CJK_SEVERITY_WORDS


# ── audit-T4 轮 2 I-3: dispatch 首线发射 E2E（plan Step 8 前半） ──────────────


def test_dispatch_first_line_emits_vocab_finding(tmp_path: Path) -> None:
    """write_parsed_outputs is the only production emitter for G4.av.vocab.

    E2E pin: a key-form out-of-vocab value must land in the findings journal.
    """
    import json as _json

    from shenbi.pipeline.dispatch_helper import write_parsed_outputs

    (tmp_path / "audits").mkdir()
    write_parsed_outputs(
        "",
        ["audits/chapter-3-x.md"],
        tmp_path,
        skill=None,
        parsed={"audits/chapter-3-x.md": "## 判定: 通过\n\n严重度: 严重\n"},
    )
    pwi = tmp_path / "audits" / ".integrity-findings-3.jsonl"
    assert pwi.exists(), "real writer path must produce the PWI jsonl"
    findings = [
        _json.loads(line)["finding"]
        for line in pwi.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(f.startswith("G4.av.vocab:") for f in findings), findings
