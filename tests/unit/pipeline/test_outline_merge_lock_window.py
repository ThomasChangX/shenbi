"""Spec #91 T3: dispatch_helper outline-merge lock-window red/green (deterministic)."""

import threading
from pathlib import Path

import pytest

from shenbi.pipeline import dispatch_helper as dh
from shenbi.pipeline.truth_io import path_lock, path_lock_held

B_LINE = "- B 的串行提交行：外部写者\n"


def _write_b(path: Path) -> None:
    with path_lock(path):
        text = path.read_text(encoding="utf-8")
        from shenbi.safe_write import safe_write

        safe_write(path, (text + B_LINE).encode("utf-8"))


@pytest.mark.xfail(
    strict=True,
    reason="spec #91 T3 fixed: outline-merge base read now holds the path lock, so B's committed update is merged on top of (was clobbered by stale base)",
)
def test_red_stale_base_loses_b(tmp_path, monkeypatch):
    live = tmp_path / "outline" / "thread_map.md"
    live.parent.mkdir(parents=True)
    live.write_text("## 线索总览\n\n| A |\n|---|\n| 1 |\n", encoding="utf-8")
    gate = threading.Event()
    proceed = threading.Event()
    orig = dh._strip_hr_lines

    def hooked(content):
        if not gate.is_set():
            gate.set()
            proceed.wait(timeout=5)  # hold A between its (formerly lock-free) read and the lock
        return orig(content)

    monkeypatch.setattr(dh, "_strip_hr_lines", hooked)
    errors: list[Exception] = []

    def run_a():
        try:
            dh.route_append_dedup_write(
                tmp_path,
                "outline/thread_map.md",
                "### T1: 测试线索\n- 状态: open\n- 当前进度: 起点\n",
                key_field="thread",
            )
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=run_a)
    t.start()
    assert gate.wait(timeout=5)
    assert not errors  # A parked between read and lock (pre-fix shape)
    _write_b(live)  # B commits inside A's stale-base window
    proceed.set()
    t.join(timeout=5)
    assert not errors
    assert B_LINE not in live.read_text(encoding="utf-8")  # B LOST to stale-base blind merge


def test_green_read_holds_lock(tmp_path, monkeypatch):
    live = tmp_path / "outline" / "thread_map.md"
    live.parent.mkdir(parents=True)
    live.write_text("## 线索总览\n\n| A |\n|---|\n| 1 |\n", encoding="utf-8")
    seen: list[bool] = []
    orig = Path.read_text

    def spy(self, *a, **k):
        if self == live:
            seen.append(path_lock_held(self))
        return orig(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", spy)
    dh.route_append_dedup_write(
        tmp_path,
        "outline/thread_map.md",
        "### T1: 测试线索\n- 状态: open\n- 当前进度: 起点\n",
        key_field="thread",
    )
    assert seen and all(seen)  # every outline base-read happened under the path lock
