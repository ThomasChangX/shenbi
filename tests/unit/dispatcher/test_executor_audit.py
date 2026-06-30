from __future__ import annotations

import json
from pathlib import Path

import shenbi.dispatcher.executor as ex
from shenbi.dispatcher.executor import dispatch_with_write_audit


def _cfg() -> dict[str, object]:
    return {"version": "1.0", "updated": "2026-06-12", "approval": {}}


def test_audit_passes_on_allowed_genre_key_change(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setattr(ex, "derive_output_files", lambda s: ["genre-config.json"])  # type: ignore[attr-defined]
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps(_cfg()), encoding="utf-8")

    def allowed(skill: str, tt: str, rd: Path, prompt: str) -> int:
        d = json.loads(cfg.read_text(encoding="utf-8"))
        d["version"] = "2.0"  # 允许
        cfg.write_text(json.dumps(d), encoding="utf-8")
        return 0

    monkeypatch.setattr(ex, "dispatch", allowed)  # type: ignore[attr-defined]
    rc = dispatch_with_write_audit("shenbi-genre-config", "generative", tmp_path, "p")
    assert rc == 0
    assert (tmp_path / "write-audit.jsonl").exists()


def test_audit_blocks_on_undeclared_genre_key(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setattr(ex, "derive_output_files", lambda s: ["genre-config.json"])  # type: ignore[attr-defined]
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps(_cfg()), encoding="utf-8")

    def forbidden(skill: str, tt: str, rd: Path, prompt: str) -> int:
        d = json.loads(cfg.read_text(encoding="utf-8"))
        d["title"] = "x"  # genre-config 真实 9 键之外 → 越权
        cfg.write_text(json.dumps(d), encoding="utf-8")
        return 0

    monkeypatch.setattr(ex, "dispatch", forbidden)  # type: ignore[attr-defined]
    rc = dispatch_with_write_audit("shenbi-genre-config", "generative", tmp_path, "p")
    assert rc == 2  # GATE_FAIL
    last = json.loads((tmp_path / "write-audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last["blocked"] is True


def test_dispatch_primitive_still_present() -> None:
    """现有 dispatch 原语保留，未破坏。"""
    assert callable(ex.dispatch)
    assert callable(ex.dispatch_with_write_audit)
