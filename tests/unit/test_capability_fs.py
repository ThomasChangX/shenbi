from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.capability_fs import CapabilityFS


def test_reads_allowed_under_capability_fs(tmp_path: Path) -> None:
    """Reads within allow_root succeed (the read-only backstop permits reads)."""
    f = tmp_path / "data.txt"
    f.write_text("hello", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    assert fs.read_text(f) == "hello"
    assert fs.read_bytes(f) == b"hello"
    assert fs.exists(f) is True


def test_list_dir_allowed(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    (tmp_path / "b.txt").write_text("2", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    names = fs.list_dir(tmp_path)
    assert set(names) == {"a.txt", "b.txt"}


def test_write_text_blocked(tmp_path: Path) -> None:
    """Any write through the read-only handle raises PermissionError."""
    f = tmp_path / "out.txt"
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.write_text(f, "x")


def test_write_bytes_blocked(tmp_path: Path) -> None:
    f = tmp_path / "out.bin"
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.write_bytes(f, b"x")


def test_unlink_blocked(tmp_path: Path) -> None:
    f = tmp_path / "out.txt"
    f.write_text("x", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.unlink(f)


def test_mkdir_blocked(tmp_path: Path) -> None:
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.mkdir(tmp_path / "sub")


def test_path_outside_allow_root_denied(tmp_path: Path) -> None:
    """Reads outside allow_root are rejected (sandbox enforces the boundary)."""
    inside = tmp_path / "in"
    inside.mkdir()
    outside = tmp_path / "out.txt"
    outside.write_text("z", encoding="utf-8")
    fs = CapabilityFS(inside)
    with pytest.raises(PermissionError):
        fs.read_text(outside)


def test_gate_purity_pattern(tmp_path: Path) -> None:
    """Example: a pure (read-only) function works under CapabilityFS.

    Injecting the read-only handle instead of a writable Path lets a gate run
    with a runtime guarantee that no FS mutation can occur (spec P5).
    """
    f = tmp_path / "input.txt"
    f.write_text("data", encoding="utf-8")
    fs = CapabilityFS(tmp_path)

    def pure_fn(read_text, path: Path) -> str:
        return read_text(path).upper()

    assert pure_fn(fs.read_text, f) == "DATA"
