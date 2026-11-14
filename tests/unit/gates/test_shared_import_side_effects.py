"""Spec #89 T4 AC4: importing gates.shared performs zero FS scans, holds no writers."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

from shenbi.gates import shared


@pytest.mark.unit
def test_import_shared_performs_no_iterdir(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    real = Path.iterdir

    def spy(self: Path) -> object:
        calls.append(str(self))
        return real(self)

    # reload 会把 compiled 正则等绑定换成新对象——跨文件顺序敏感（audit-T5 🟡：
    # test_meta_block_re_is_single_source 的身份断言被重绑炸）。快照/恢复 __dict__
    # 消除跨测试污染。
    snapshot = dict(vars(shared))
    monkeypatch.setattr(Path, "iterdir", spy)
    try:
        importlib.reload(shared)  # type: ignore[arg-type]
        assert calls == [], f"import-time FS scan detected: {calls}"
    finally:
        shared.__dict__.clear()
        shared.__dict__.update(snapshot)


@pytest.mark.unit
def test_shared_has_no_write_functions() -> None:
    for name, member in vars(shared).items():
        if inspect.isfunction(member) and member.__module__ == "shenbi.gates.shared":
            src = inspect.getsource(member)
            assert ".write_text(" not in src, f"{name} writes via write_text"
            assert "safe_write(" not in src, f"{name} writes via safe_write"
            assert ".mkdir(" not in src, f"{name} mkdirs"
