"""F516（C32 R4）：drift 归属以"本次 dispatch 实际写过的文件"为界。

既有 drift（内容级 YAML vs 派生表不一致，先于本次 dispatch 存在）不得归属到
零改动技能头上：快照 diff 为空（pre == post）→ 零违规且零 drift 归属，
record_audit_outcome 通过，rc 不级联降为 2。归属判据 = pre/post 快照 diff
（compute_file_change 的 added/modified），而非"文件当前状态是否漂移"。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from shenbi.audit.snapshot import snapshot_tree
from shenbi.audit.write_audit import audit_writes


def _hook_md(yaml_state: str = "PLANTED", table_state: str | None = None) -> str:
    """pending_hooks.md 形态：## 活跃伏笔 表 + ## hooks YAML 记录。

    table_state 与 yaml_state 不一致时即为 cross-section drift 内容
    （真实技能产物形态，对照 tests/unit/audit/test_write_audit.py）。
    """
    tbl = table_state if table_state is not None else yaml_state
    return (
        "## 活跃伏笔\n\n"
        "| Hook ID | 类型 | 状态 |\n|---|---|---|\n| h1 | GENUINE | " + tbl + " |\n\n"
        f"## hooks\n\n- id: h1\n  state: {yaml_state}\n  type: GENUINE\n"
    )


#: YAML state=PLANTED 但表行写 RESOLVED → 内容本身带既有 drift。
_DRIFTED = _hook_md("PLANTED", table_state="RESOLVED")


def test_zero_write_dispatch_has_zero_drift_attribution() -> None:
    """F516：pre == post（本次零写入）→ 零违规且零 drift 归属。

    文件内容自带既有 drift（前一技能或人工编辑造成），但本次 dispatch
    未写该文件 → 不得归属（不级联 rc=2）。
    """
    pre: dict[str, str | None] = {"truth/pending_hooks.md": _DRIFTED}
    res = audit_writes("shenbi-state-settling", pre, pre)
    assert res.violations == ()
    assert res.drift == ()


def test_zero_write_dispatch_returns_rc0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """验收（a）：零改动技能派发后 rc=0（构造 pre==post 快照场景）。

    复现 F516 生产路径：watch 面内文件带既有 drift、dispatch 实际零写入
    → 修复前 drift 被记为该次违规 → rc=2 级联；修复后 rc=0。
    """
    from shenbi.dispatcher import executor

    root = tmp_path / "project"
    (root / "truth").mkdir(parents=True)
    (root / "truth" / "pending_hooks.md").write_text(_DRIFTED, encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()

    monkeypatch.setattr(executor, "PROJECT_DIR", root)

    def _zero_write_dispatch(*_args: object, **_kwargs: object) -> int:
        return 0  # dispatch 成功且不写任何文件 → pre == post

    monkeypatch.setattr(executor, "dispatch", _zero_write_dispatch)

    rc = executor.dispatch_with_write_audit(
        "shenbi-state-settling", "generative", round_dir, "no chapter marker"
    )
    assert rc == 0
    ledger_lines = (round_dir / "write-audit.jsonl").read_text(encoding="utf-8").splitlines()
    last = json.loads(ledger_lines[-1])
    assert last["blocked"] is False
    assert last["violations"] == []
    assert last["drift"] == []


def test_drift_attributed_when_file_actually_written(tmp_path: Path) -> None:
    """守卫：本次确实写入（post != pre）且写入引入 drift → drift 仍被检出。

    防止修复过度（把 drift 检测整个关掉）：归属边界是"实际写过"，
    不是"永远不检 drift"。
    """
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    md.write_text(_hook_md("PLANTED"), encoding="utf-8")  # 一致内容
    pre = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    md.write_text(_DRIFTED, encoding="utf-8")  # dispatch 写入引入 drift
    post = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-state-settling", pre, post)
    assert any("state" in d and "h1" in d for d in res.drift)


def test_drift_on_newly_added_file_still_attributed(tmp_path: Path) -> None:
    """守卫：dispatch 新建（added）带 drift 的文件 → 归属本次 dispatch。"""
    md = tmp_path / "truth" / "pending_hooks.md"
    md.parent.mkdir(parents=True)
    md.write_text(_DRIFTED, encoding="utf-8")
    pre: dict[str, str | None] = {}
    post = snapshot_tree(tmp_path, ["truth/pending_hooks.md"])
    res = audit_writes("shenbi-state-settling", pre, post)
    assert any("state" in d and "h1" in d for d in res.drift)


def test_deleted_file_not_drift_checked_or_cascaded(tmp_path: Path) -> None:
    """守卫：文件被删除（post=None）→ 不做 drift 检测，违规由 OWNERSHIP status 判。"""
    pre: dict[str, str | None] = {"truth/pending_hooks.md": _DRIFTED}
    post: dict[str, str | None] = {"truth/pending_hooks.md": None}
    res = audit_writes("shenbi-state-settling", pre, post)
    assert res.drift == ()
    # F502：OWNERSHIP 管控文件整体删除 → record 级违规（非 drift）。
    assert any("删除" in v for v in res.violations)


def test_executor_wiring_matches_attribution_rule() -> None:
    """接线一致性：dispatch_with_write_audit 的 rc 降格只经 record_audit_outcome。"""
    from shenbi.audit._shared import AuditResult

    with (
        patch("shenbi.dispatcher.executor.dispatch", return_value=0),
        patch("shenbi.audit.snapshot.snapshot_tree", return_value={}),
        patch("shenbi.audit.record.record_audit_outcome", return_value=True) as rec,
    ):
        from shenbi.dispatcher import executor

        rc = executor.dispatch_with_write_audit(
            "shenbi-state-settling", "generative", Path("/tmp/round-x"), "x"
        )
    assert rc == 0
    # audit_writes 对空快照产出零违规零 drift（F516 上界场景）
    assert rec.call_args is not None
    result: AuditResult = rec.call_args[0][2]
    assert result.violations == ()
    assert result.drift == ()
