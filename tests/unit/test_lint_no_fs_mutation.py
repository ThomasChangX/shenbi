from __future__ import annotations

from pathlib import Path

from tools.lint_no_fs_mutation import lint_dir

# --- Detection: mutation primitives MUST be flagged ---


def test_flags_write_text(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.write_text('x')\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "write_text" in vs[0]


def test_flags_write_bytes(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.write_bytes(b'x')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_unlink(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.unlink()\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "unlink" in vs[0]


def test_flags_path_open_write(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.open('w')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_path_open_append(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.open('a')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_builtin_open_write(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("open(p, 'w')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_os_replace(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("os.replace(a, b)\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "os.replace" in vs[0]


def test_flags_shutil_copy(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("shutil.copy2(a, b)\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "shutil" in vs[0]


def test_flags_nested_open_in_json_dump(tmp_path: Path) -> None:
    """json.dump(data, open(path, 'w')) -- the nested open is caught."""
    f = tmp_path / "bad.py"
    f.write_text("json.dump(data, open(path, 'w'))\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


# --- No false positives: reads and safe operations MUST NOT be flagged ---


def test_allows_read_text(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.read_text()\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_open_read_default(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.open()\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_open_read_explicit(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.open('r')\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_builtin_open_read(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("open(p)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_json_dumps(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("json.dumps(x)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_os_path_exists(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("os.path.exists(p)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_mkdir(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.mkdir(parents=True)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_dynamic_mode_open(tmp_path: Path) -> None:
    """Dynamic mode (not a constant) is not flagged (conservative)."""
    f = tmp_path / "ok.py"
    f.write_text("open(p, mode)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []
