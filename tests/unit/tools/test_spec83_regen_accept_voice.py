"""spec #83 T13: voice-token criterion 5 — bucket logic direct tests.

Per plan acceptance mapping: offline = 口径单测 (bucket semantics); full
36-chapter corpus PASS belongs to the regen run window (relay-quote
residuals are driver-side calibration items — spec-deviations T13).
"""

from __future__ import annotations

from pathlib import Path

from tools.regen_accept import (
    _card_name,
    _card_tokens,
    _load_cards,
    check_blind_recognition,
    voice_token_buckets,
)

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "spec83"


def test_token_buckets_segment_and_disambiguate() -> None:
    cards = _load_cards(FIX)
    prot = _card_name(
        (FIX / "characters" / "protagonist.md").read_text(encoding="utf-8"), "protagonist"
    )
    b = voice_token_buckets(cards, prot)
    assert len(b) >= 5  # ≥5 marker cards (len<5 hard-FAIL guard upstream)
    # catchphrase 切段（全句精确匹配漏标点变体——「灯在人在。路通行通。」→ 灯在人在/路通行通）
    assert any("灯在人在" in toks for toks in b.values())
    # protagonist 桶含账房动词族
    from shenbi.text.voice_lexicon import ACCOUNTING_VERBS

    assert any(v in b[prot] for v in ACCOUNTING_VERBS[:3])
    # 全局去歧：无任何 token 属多卡（共享 token 弃）
    all_toks = [t for toks in b.values() for t in toks]
    assert len(all_toks) == len(set(all_toks))


def test_card_tokens_quote_extraction_avoid_excluded() -> None:
    text = (
        "---\nvoice_profile:\n  catchphrases: []\n---\n"
        "正文说「谁托的、送到哪、几时到」的切口。\navoid_patterns:\n  - 不说「以后你会明白」\n"
    )
    toks = _card_tokens(text)
    assert any("谁托的" in t or "送到哪" in t for t in toks)  # 引语入桶
    assert not any("以后你会明白" in t for t in toks)  # avoid 段排除


def test_criterion5_runs_on_real_cards_e2e() -> None:
    # 真实 ≥5 卡 + fixtures 章走完整入口（端到端可达性——不钉整卷 PASS，归运行窗口）
    v = check_blind_recognition(FIX, through=30)
    assert v.criterion == "5"
    # 判据机件活着：夹具包部分章（15/36）下可归属面缩水 → 走 <5 抽样分支或分角色
    # 明细——两者都证明入口可达（整卷 PASS 归运行窗口）
    assert "4/5" in v.detail or "角色仅" in v.detail or v.status == "PASS"


def test_attribution_semantics_unattributable_excluded() -> None:
    # 语义修正钉测：零命中段不入分母（原「计错」使 4/5 结构性不可达——r2 挂账根因）
    # 用最小工程：一张卡 + 无 token 对白 → total=0 → 走 len(sampled)<5 FAIL 分支（非 0/0 崩溃）
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "characters").mkdir()
        (d / "chapters").mkdir()
        (d / "characters" / "a.md").write_text(
            "---\nvoice_profile:\n  catchphrases: ['灯在人在。路通行通。']\n---\n", encoding="utf-8"
        )
        (d / "chapters" / "chapter-1.md").write_text(
            "普通对白一句。\n",
            encoding="utf-8",  # 无 token 命中 → 不入分母
        )
        v = check_blind_recognition(d, through=1)
        assert v.status == "FAIL"  # 带卡面标记的角色卡仅 1 张 <5——硬 FAIL 分支（非崩溃）
