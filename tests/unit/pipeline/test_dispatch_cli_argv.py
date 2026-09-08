"""SDD #56 C18 T1.1: dispatch CLI argv capture-mode verification (F947 offline).

Characterization tests: they lock in the *current* argv shape produced by
``_find_ide_cli`` for both codex and zcode. If these fail, the dispatch
layer drifted from the C18 spec description — stop and re-run the phase-1
value gate instead of "fixing" the assertions.
"""

from __future__ import annotations

import shutil
from unittest import mock

from shenbi.pipeline import dispatch_helper

#: The 7-pattern meta-narration family from the C18 spec (must never be
#: injected into dispatch CLI argv or prompts).
META_NARRATION_PATTERNS: tuple[str, ...] = (
    "手动复制",
    "只读沙箱",
    "无法写入",
    "请手动",
    "manually copy",
    "read-only sandbox",
    "cannot write",
)


def test_cli_argv_contains_capture_mode_no_meta_narration_codex() -> None:
    with mock.patch.object(
        shutil, "which", side_effect=lambda n: "/usr/bin/fake" if n == "codex" else None
    ):
        argv = dispatch_helper._find_ide_cli()
    assert argv is not None
    assert argv[0] == "codex"
    joined = " ".join(argv)
    assert "sandbox_permissions=workspace-write" in joined
    for pattern in META_NARRATION_PATTERNS:
        assert pattern not in joined


def test_cli_argv_shared_flag_face_for_zcode() -> None:
    # Current state: the zcode branch returns the same codex-specific argv
    # (zcode-specific flags untested — spec #56 T1.1 deviation, recorded in
    # docs/superpowers/audit-runs/2026-09-08-c18-cleanup/dispatch-verification.md).
    def fake_which(name: str) -> str | None:
        return None if name == "codex" else "/usr/bin/fake-zcode"

    with mock.patch.object(shutil, "which", side_effect=fake_which):
        argv_zcode = dispatch_helper._find_ide_cli()
    with mock.patch.object(
        shutil, "which", side_effect=lambda n: "/usr/bin/fake" if n == "codex" else None
    ):
        argv_codex = dispatch_helper._find_ide_cli()
    assert argv_zcode is not None
    assert argv_zcode[0] == "zcode"
    assert argv_codex is not None
    assert argv_zcode[1:] == argv_codex[1:]
    joined = " ".join(argv_zcode)
    assert "sandbox_permissions=workspace-write" in joined
    for pattern in META_NARRATION_PATTERNS:
        assert pattern not in joined
