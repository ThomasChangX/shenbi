"""Verify dispatch() has no reachable codex-api code path.

detect_mode() only returns 'codex' or 'internal'. The codex-api branch was
unreachable dead code. This test verifies the behavior (not source text): even
if detect_mode returned 'codex-api', dispatch must fall through to internal,
never call dispatch_codex_api.
"""

from __future__ import annotations

from pathlib import Path


class TestNoCodexApiBranch:
    def test_codex_api_mode_falls_through_to_internal(self, monkeypatch, tmp_path):
        """Behavioral test: if detect_mode somehow returned 'codex-api', dispatch()
        must NOT call dispatch_codex_api — it must fall through to internal mode.

        This is stronger than a source grep: it proves runtime unreachability
        and won't break on cosmetic edits (e.g. a comment mentioning codex-api).
        """
        import shenbi.dispatcher.executor as exec_mod
        import shenbi.dispatcher.modes.codex_api as codex_api_mod
        import shenbi.dispatcher.modes.internal as internal_mod
        from shenbi.dispatcher.executor import dispatch

        # Force detect_mode to return the removed mode value
        monkeypatch.setattr(exec_mod, "detect_mode", lambda: "codex-api")
        # Stub G1 (run_g1) so dispatch doesn't crash on missing files
        monkeypatch.setattr(exec_mod, "run_g1", lambda *a, **kw: {"status": "PASS"})
        # Stub internal dispatch so the fall-through returns cleanly (no real
        # subprocess work); also confirms dispatch reached internal, not codex_api.
        monkeypatch.setattr(internal_mod, "dispatch_internal", lambda *a, **kw: 0)
        # Spy on dispatch_codex_api — if called, the dead branch survived
        codex_api_called: list[bool] = []

        def spy(*a, **kw):
            codex_api_called.append(True)
            return 0

        monkeypatch.setattr(codex_api_mod, "dispatch_codex_api", spy)

        round_dir = tmp_path / "round"
        round_dir.mkdir()
        # Presence of pipeline-state.json skips G2 (the code's documented path),
        # so dispatch reaches the mode-dispatch branch without running a real
        # G2 subprocess on non-existent output files.
        (round_dir / "pipeline-state.json").write_text("{}", encoding="utf-8")
        # dispatch should return without calling codex_api (falls to internal)
        rc = dispatch("shenbi-worldbuilding", "generative", round_dir, "test")
        assert rc == 0
        assert not codex_api_called, (
            "dispatch_codex_api was called — the dead codex-api branch still routes to it"
        )
