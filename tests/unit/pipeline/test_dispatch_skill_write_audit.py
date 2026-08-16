"""C32 R3 回归(F518 P1):API/IDE 派发路由的写审计覆盖.

spec: docs/superpowers/audit-runs/2026-08-15/findings-ledger.md F518 /
zone-reports/Z5-review-r1.md -- 此前 ``dispatch_skill`` 的 API 与 IDE 两条
生产路由整体绕过 Tier B 写审计(仅 legacy CLI 子进程路由经
``dispatch_with_write_audit`` 被审计),模块 docstring 反向声称"复用而非绕过".

本文件驱动真实路由层(dispatch_skill 的 env/CLI 探测分流),monkeypatch
fake 派发函数(不触发真实 LLM);watch 面经真实契约推导(不 stub
derive_output_files--Z5-review-r1 覆盖空洞 #4 指出 stub 掩蔽路由缺陷),
fixture 用真实技能产物形状(G0.9):genre-config-example.json 顶层键恰为
OWNERSHIP 真实 9 键.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import shenbi.pipeline.dispatch_helper as dh
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill

PROJECT = Path(__file__).resolve().parents[3]
GENRE_FIXTURE = PROJECT / "tests" / "fixtures" / "genre-config-example.json"

SKILL = "shenbi-genre-config"
#: prompt 不含章节号 → chapter=None(genre-config 契约路径无占位符,不受影响)
PROMPT = "update genre config"


def _seed_genre_config(pd: Path) -> None:
    """用真实 fixture 内容预置 genre-config.json(模拟派发前状态)."""
    (pd / "genre-config.json").write_text(
        GENRE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )


def _fake_api_writing(mutate: Any) -> Any:
    """构造 fake _dispatch_via_api:按 mutate 修改 genre-config.json 后返回成功."""

    def fake(skill: str, project_dir: Path, prompt: str, **kwargs: Any) -> DispatchResult:
        cfg_path = project_dir / "genre-config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        mutate(cfg)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        return DispatchResult(True, 0, "{}", "")

    return fake


def _last_ledger_record(audit_dir: Path) -> dict[str, Any]:
    lines = (audit_dir / "write-audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines, "write-audit.jsonl 为空"
    return json.loads(lines[-1])


# -- RED 主断言:API 路由派发后 write-audit.jsonl 有记录 --


def test_api_route_records_write_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    _seed_genre_config(tmp_path)
    monkeypatch.setattr(
        dh,
        "_dispatch_via_api",
        _fake_api_writing(lambda c: c.update({"approval": c.get("approval", {})})),
    )

    result = dispatch_skill(SKILL, tmp_path, PROMPT)

    assert result.success is True
    assert result.returncode == 0
    ledger = tmp_path / "write-audit.jsonl"
    assert ledger.exists(), "API 路由派发后必须留下写审计账本记录(F518)"
    rec = _last_ledger_record(tmp_path)
    assert rec["skill"] == SKILL
    assert rec["blocked"] is False
    assert "genre-config.json" in rec["checked_files"]


# -- 越权语义与 legacy 路径一致:违规记 rc=2,不吞 --


def test_api_route_blocks_undeclared_key_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    _seed_genre_config(tmp_path)
    # rogueKey 不在 genre-config 真实 9 个 OWNERSHIP write_keys 内 → 越权
    monkeypatch.setattr(
        dh, "_dispatch_via_api", _fake_api_writing(lambda c: c.update({"rogueKey": "越权"}))
    )

    result = dispatch_skill(SKILL, tmp_path, PROMPT)

    assert result.success is False
    assert result.returncode == 2  # GATE_FAIL,与 dispatch_with_write_audit 语义一致
    assert "rogueKey" in result.stderr  # 违规原因不吞
    rec = _last_ledger_record(tmp_path)
    assert rec["blocked"] is True
    assert any("rogueKey" in v for v in rec["violations"])


def test_failed_api_dispatch_not_upgraded_but_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """派发自身失败(rc=-1)时:仍记审计账本,但 rc 不被改写为 2."""
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    _seed_genre_config(tmp_path)

    def fake(skill: str, project_dir: Path, prompt: str, **kwargs: Any) -> DispatchResult:
        cfg_path = project_dir / "genre-config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["rogueKey"] = "失败路径上的越权"
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        return DispatchResult(False, -1, "", "API call failed")

    monkeypatch.setattr(dh, "_dispatch_via_api", fake)
    result = dispatch_skill(SKILL, tmp_path, PROMPT)

    assert result.success is False
    assert result.returncode == -1  # 失败就是失败,不覆盖
    rec = _last_ledger_record(tmp_path)
    assert rec["blocked"] is True


# -- IDE 路由:同一钩子形态(最小实现)--


def test_ide_route_records_write_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHENBI_LLM_API_KEY", raising=False)
    monkeypatch.setattr(dh, "_find_ide_cli", lambda: ["codex", "exec"])

    def fake_ide(skill: str, project_dir: Path, prompt: str, **kwargs: Any) -> DispatchResult:
        (project_dir / "genre-config.json").write_text(
            GENRE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return DispatchResult(True, 0, "out", "")

    monkeypatch.setattr(dh, "_dispatch_via_ide", fake_ide)
    result = dispatch_skill(SKILL, tmp_path, PROMPT)

    assert result.success is True
    ledger = tmp_path / "write-audit.jsonl"
    assert ledger.exists(), "IDE 路由派发后必须留下写审计账本记录(F518)"
    rec = _last_ledger_record(tmp_path)
    assert rec["skill"] == SKILL
    assert rec["blocked"] is False


# -- 不崩:审计基础设施异常不得掩盖派发结果 --


def test_audit_infra_crash_preserves_dispatch_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    _seed_genre_config(tmp_path)
    monkeypatch.setattr(dh, "_dispatch_via_api", _fake_api_writing(lambda c: None))

    def boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("audit infra broken")

    import shenbi.audit.write_audit as wa
    from shenbi.logging import configure_logging

    # 生产形态:structlog 绑定 stderr(PrintLoggerFactory(sys.stderr))。单测默认
    # 未 configure,structlog 走默认 stdout —— 先 configure 让本用例按生产流断言
    # (cache_logger_on_first_use=False 使其绑定 capsys 当前捕获的 sys.stderr;
    # 全局配置由 tests/conftest.py 的 _isolate_structlog_config 在 teardown 恢复).
    configure_logging()
    monkeypatch.setattr(wa, "audit_writes", boom)
    result = dispatch_skill(SKILL, tmp_path, PROMPT)

    assert result.success is True  # 审计崩溃不吞派发结果
    assert result.returncode == 0
    # fail-open 但必须 LOUD:infra 错误事件确实发声到 stderr —— caplog 捕不到
    # structlog(自定义 PrintLoggerFactory),必须 capsys.
    assert "write_audit_infra_error" in capsys.readouterr().err


# -- 账本位置:显式 round_dir 优先(与 legacy 路由 rd 推导一致)--


def test_round_dir_receives_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    _seed_genre_config(tmp_path)
    round_dir = tmp_path / "round-001"
    round_dir.mkdir()
    monkeypatch.setattr(dh, "_dispatch_via_api", _fake_api_writing(lambda c: None))
    dispatch_skill(SKILL, tmp_path, PROMPT, round_dir=round_dir)
    assert (round_dir / "write-audit.jsonl").exists()
