"""Spec #91 T3: ledger_archive lock-window red/green (no sleep, deterministic)."""

import threading
from pathlib import Path

import pytest

from shenbi.pipeline import ledger_archive as la
from shenbi.pipeline.truth_io import path_lock, path_lock_held
from shenbi.safe_write import safe_write

# fixture MUST pass POOL_SPEC shape gates: `## 总览` + `## 详情` + a
# 详情-section matching HOOK_HEADING_RE (blueprint: tests/unit/pipeline/test_ledger_archive.py:150-155)
LIVE_TEXT = (
    "---\ntype: truth\n---\n\n# 伏笔池\n\n## 总览\n\n| Hook ID（钩子名） | 当前生命周期 | 种植章 |\n"
    "| MH01（灵印） | RESOLVED | 4 |\n\n## 详情\n\n### MH01（灵印）\n\n"
    "- lifecycle_state: RESOLVED\n- resolve_chapter: 30\n"
)
B_LINE = "- lifecycle_state: RESOLVED-by-b\n"  # B's committed update


def _write_b(path: Path) -> None:
    with path_lock(path):  # B takes the lock properly
        text = path.read_text(encoding="utf-8")
        safe_write(path, (text + B_LINE).encode("utf-8"))


@pytest.mark.xfail(
    strict=True,
    reason="spec #91 T3 fixed: reads now hold the path lock, so B's committed update survives (was lost to A's blind write)",
)
def test_red_thread_b_update_lost(tmp_path, monkeypatch):
    # RED on current code: A reads OUTSIDE the lock; B's locked write
    # during A's parse window is clobbered by A's blind write.
    live = tmp_path / "truth" / "pending_hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(LIVE_TEXT, encoding="utf-8")
    gate = threading.Event()
    proceed = threading.Event()
    orig = la._section_fields

    def hooked(spec, section):
        if not gate.is_set():
            gate.set()
            proceed.wait(timeout=5)  # hold A in its lock-free window
        return orig(spec, section)

    monkeypatch.setattr(la, "_section_fields", hooked)
    errors: list[Exception] = []

    def run_a():
        try:
            la.archive_ledger(tmp_path, 30, la.POOL_SPEC)
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=run_a)
    t.start()
    assert gate.wait(timeout=5)
    assert not errors  # shape gates passed; A parked in its lock-free parse window
    _write_b(live)  # B commits inside A's window
    proceed.set()
    t.join(timeout=5)
    assert not errors
    assert B_LINE not in live.read_text(encoding="utf-8")  # B LOST → red asserts the defect


def test_green_read_holds_lock(tmp_path, monkeypatch):
    live = tmp_path / "truth" / "pending_hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(LIVE_TEXT, encoding="utf-8")
    seen: list[bool] = []
    orig = Path.read_text

    def spy(self, *a, **k):
        if self == live:  # only watch the live ledger file
            seen.append(path_lock_held(self))  # public probe imported at module top (r3 审查 I2)
        return orig(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", spy)
    la.archive_ledger(tmp_path, 30, la.POOL_SPEC)
    assert seen and all(seen)  # every live-read happened under the path lock


def test_green_both_writers_survive(tmp_path):  # r2 审查 I5；断言落点 r3 审查 C1 修正
    live = tmp_path / "truth" / "pending_hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(LIVE_TEXT, encoding="utf-8")
    _write_b(
        live
    )  # B commits first (properly locked) → B's line is INSIDE the section span A reads
    la.archive_ledger(tmp_path, 30, la.POOL_SPEC)  # A archives afterwards
    # archive semantics: the whole section span (INCLUDING B's line) is moved
    # verbatim to the archive file and replaced by a tombstone in live.
    # "Both writers survive" therefore asserts: B's line lives on in the
    # ARCHIVE file, and the live file carries A's tombstone marker.
    archive = tmp_path / "truth" / "pending_hooks_archive.md"
    assert B_LINE in archive.read_text(encoding="utf-8")  # B's committed update preserved
    assert "archived_to" in live.read_text(encoding="utf-8")  # A's tombstone present
