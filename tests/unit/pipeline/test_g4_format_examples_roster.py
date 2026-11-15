"""Spec #105 T4a: G4_FORMAT_EXAMPLES roster — first three keys pinned.

Roster diff ledger lives in .superpowers/sdd/spec-deviations.md (T4): 287
checker ids vs 19+3 example keys — only keys with live-evidence fallback rows
are backfilled; the rest stay known-gap on purpose.
"""

from __future__ import annotations


def test_scene_budget_key_present() -> None:
    from shenbi.pipeline.chapter_loop import G4_FORMAT_EXAMPLES

    example = G4_FORMAT_EXAMPLES["G4.cp.scene_budget"]
    assert "场景预算与收束钩" in example
    assert "配对型" in example
    assert "2-3 场景" in example


def test_vocab_key_present() -> None:
    from shenbi.pipeline.chapter_loop import G4_FORMAT_EXAMPLES

    example = G4_FORMAT_EXAMPLES["G4.av.vocab"]
    for word in ("BLOCKING", "CRITICAL", "MINOR"):
        assert word in example
    assert "词表外" in example


def test_dispatch_integrity_key_present() -> None:
    from shenbi.pipeline.chapter_loop import G4_FORMAT_EXAMPLES

    example = G4_FORMAT_EXAMPLES["G4.av.dispatch_integrity"]
    assert "预检" in example
    assert "无效" in example
    assert "chapters/" in example


def test_examples_nonempty_strings() -> None:
    from shenbi.pipeline.chapter_loop import G4_FORMAT_EXAMPLES

    for key, value in G4_FORMAT_EXAMPLES.items():
        assert isinstance(value, str) and value.strip(), key
