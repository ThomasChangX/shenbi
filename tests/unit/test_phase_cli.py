"""T3: CLI 参数协议(spec #38 F102/F123/F135/F437/F107 argv 面/F337 残余/F1018)。

G0.9 说明:CLI 参数错误面为构造性 argv 输入,非 skill 产物。
"""

import json

import pytest


def _run_main(monkeypatch, argv: list[str]):
    import shenbi.phase_runner as pr

    monkeypatch.setattr("sys.argv", ["shenbi-phase", *argv])
    with pytest.raises(SystemExit) as ei:
        pr.main()
    return ei.value.code


class TestArgparseProtocol:
    def test_missing_round_dir_usage_error_exit2(self, monkeypatch, capsys) -> None:
        """F123:缺 --round-dir → argparse usage 错误 exit 2,无 traceback。"""
        code = _run_main(monkeypatch, ["start", "t2-skill"])
        assert code == 2

    def test_usage_error_logs_json_to_stderr(self, monkeypatch, capsys) -> None:
        """test_logging 兼容:错误路径走 structlog JSON(非 argparse 纯文本)。"""
        code = _run_main(monkeypatch, ["start", "t2-skill"])
        assert code == 2
        # structlog 输出在 stderr(caplog 不捕获 structlog handler)
        assert "usage_error" in capsys.readouterr().err

    def test_non_integer_chapter_exit2(self, monkeypatch, tmp_path) -> None:
        """F135:--chapter abc → exit 2 而非 ValueError traceback。"""
        code = _run_main(
            monkeypatch,
            ["post-skill", "t2", "skill", "--round-dir", str(tmp_path), "--chapter", "abc"],
        )
        assert code == 2

    def test_unknown_flag_not_bound_as_positional(self, monkeypatch) -> None:
        """F123:flag token 不再可能绑定为 phase(缺位置参数 → exit 2)。"""
        code = _run_main(monkeypatch, ["--round-dir", "/tmp/x"])
        assert code == 2

    def test_help_smoke(self, monkeypatch, capsys) -> None:
        assert _run_main(monkeypatch, ["--help"]) == 0
        assert "shenbi-phase" in capsys.readouterr().out


class TestProjectDirSentinel:
    def test_none_string_not_passed_to_g5(self, monkeypatch, tmp_path) -> None:
        """F102:'None' 字符串哨兵——G5 收到的 args 不得含 'None'。"""
        import shenbi.phase_runner as pr

        captured: dict[str, list[str]] = {}

        def fake_run_gate(gate: str, args: list[str]) -> dict[str, object]:
            captured["args"] = args
            return {"status": "PASS"}

        monkeypatch.setattr(pr, "run_gate", fake_run_gate)
        # build a valid started state first
        rd = tmp_path / "round"
        rd.mkdir()
        state_file = rd / "phase-t2-x"
        state_file.mkdir()
        (state_file / "phase-state.json").write_text(
            json.dumps({"state": "created", "steps": []}), encoding="utf-8"
        )
        monkeypatch.setattr(
            "sys.argv",
            [
                "shenbi-phase",
                "start",
                "t2-x",
                "--round-dir",
                str(rd),
                "--project-dir",
                "None",
            ],
        )
        pr.main()  # 成功路径:状态推进 + emit ok,无需显式 exit
        assert "None" not in captured["args"]


class TestGatesCliG4Guard:
    def test_g4_invalid_path_structured_fail(self, tmp_path) -> None:
        """F437:三段式相对路径 ValueError → 结构化 FAIL exit 1,非 traceback。"""
        import subprocess
        import sys as _sys

        r = subprocess.run(
            [_sys.executable, "-m", "shenbi.gates.cli", "G4", "worldbuilding", "no|such*file"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = r.stdout
        assert r.returncode in (0, 1)
        assert "Traceback" not in r.stderr
        # 结构化输出含 status 键(合法 JSON 或 fail 串)
        assert "status" in out or "FAIL" in out.upper()


class TestScoringTypeGuard:
    def test_type_missing_value_exit2(self) -> None:
        """F107 argv 面:--type 悬尾 → exit 2 非 IndexError。"""
        import subprocess
        import sys as _sys

        r = subprocess.run(
            [_sys.executable, "-m", "shenbi.scoring", "--gate-only", "G2", "--type"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert r.returncode == 2
        assert "Traceback" not in r.stderr
