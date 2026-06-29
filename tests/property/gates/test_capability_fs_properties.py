from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from shenbi.capability_fs import CapabilityFS


@given(content=st.text(min_size=0, max_size=200, alphabet=st.characters(blacklist_characters="\r\n", blacklist_categories=("Cs",))))
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_read_text_roundtrips(tmp_path: Path, content: str) -> None:
    f = tmp_path / "a.txt"
    f.write_text(content, encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    assert fs.read_text(f) == content


@given(data=st.binary(min_size=0, max_size=64))
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_read_bytes_roundtrips(tmp_path: Path, data: bytes) -> None:
    f = tmp_path / "b.bin"
    f.write_bytes(data)
    assert CapabilityFS(tmp_path).read_bytes(f) == data


def test_any_write_raises_permissionerror(tmp_path: Path) -> None:
    f = tmp_path / "w.txt"
    f.write_text("x", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    for op in (
        lambda: fs.write_text(f, "y"),
        lambda: fs.write_bytes(f, b"y"),
        lambda: fs.unlink(f),
        lambda: fs.mkdir(tmp_path / "sub"),
    ):
        with pytest.raises(PermissionError):
            op()


def test_path_outside_allow_root_denied(tmp_path: Path) -> None:
    inside = tmp_path / "in"
    inside.mkdir()
    outside = tmp_path / "out.txt"
    outside.write_text("z", encoding="utf-8")
    fs = CapabilityFS(inside)
    with pytest.raises((PermissionError, FileNotFoundError)):
        fs.read_text(outside)


def test_exists_and_list_dir_read_only(tmp_path: Path) -> None:
    (tmp_path / "c.txt").write_text("1", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    assert fs.exists(tmp_path / "c.txt") is True
    assert fs.exists(tmp_path / "nope") is False
    names = fs.list_dir(tmp_path)
    assert "c.txt" in names
