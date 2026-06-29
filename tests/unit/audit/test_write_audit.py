from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.snapshot import snapshot_tree
from shenbi.audit.write_audit import audit_writes


def _hook_md(state: str = "PLANTED") -> str:
    return (
        "## 活跃伏笔\n\n"
        "| Hook ID | 类型 | 状态 |\n|---|---|---|\n| h1 | GENUINE | " + state + " |\n\n"
        f"## hooks\n\n- id: h1\n  state: {state}\n  type: GENUINE\n"
    )


def test_genre_skill_allowed_key_change(tmp_path: Path) -> None:
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps({"version": "1.0", "approval": {}}), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["genre-config.json"])
    cfg.write_text(json.dumps({"version": "2.0", "approval": {}}), encoding="utf-8")
    post = snapshot_tree(tmp_path, ["genre-config.json"])
    res = audit_writes("shenbi-genre-config", pre, post)
    assert res.violations == ()


def test_genre_skill_blocked_undeclared_key(tmp_path: Path) -> None:
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["genre-config.json"])
    cfg.write_text(json.dumps({"version": "1.0", "title": "x"}), encoding="utf-8")
    post = snapshot_tree(tmp_path, ["genre-config.json"])
    res = audit_writes("shenbi-genre-config", pre, post)
    assert any("title" in v for v in res.violations)


def test_track_skill_allowed_state_change(tmp_path: Path) -> None:
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    md.write_text(_hook_md("PLANTED"), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    md.write_text(_hook_md("RELEVANT"), encoding="utf-8")
    post = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-foreshadowing-track", pre, post)
    assert res.violations == ()
    assert res.drift == ()


def test_track_skill_blocked_subtlety_change(tmp_path: Path) -> None:
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    md.write_text(_hook_md("PLANTED"), encoding="utf-8")
    pre = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    md.write_text(
        _hook_md("PLANTED").replace(
            "- id: h1\n  state: PLANTED", "- id: h1\n  state: PLANTED\n  subtlety: 0.9"
        ),
        encoding="utf-8",
    )
    post = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-foreshadowing-track", pre, post)
    assert any("subtlety" in v for v in res.violations)


def test_cross_section_drift_detected(tmp_path: Path) -> None:
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    # YAML state=PLANTED 但表行写 RESOLVED → drift
    md.write_text(
        _hook_md("PLANTED").replace("| h1 | GENUINE | PLANTED |", "| h1 | GENUINE | RESOLVED |"),
        encoding="utf-8",
    )
    pre = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-foreshadowing-track", pre, pre)
    assert any("state" in d and "h1" in d for d in res.drift)


def test_undeclared_file_write_blocked(tmp_path: Path) -> None:
    """文件不在 OWNERSHIP 且不匹配声明写入 → 越权（file-level）。"""
    rogue = tmp_path / "truth" / "rogue.md"
    rogue.parent.mkdir(parents=True)
    rogue.write_text("x", encoding="utf-8")
    pre: dict[str, str | None] = {}
    post: dict[str, str | None] = {"truth/rogue.md": "x"}
    res = audit_writes("shenbi-chapter-drafting", pre, post)
    assert any("未声明写入" in v for v in res.violations)
