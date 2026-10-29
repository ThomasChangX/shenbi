"""Spec #81 §2/§1 wiring tests — fake streaming client pattern copied from
tests/unit/pipeline/test_token_ledger_guard.py::_dispatch_with_fake_client.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from shenbi.observability import archive as ar
from shenbi.pipeline import dispatch_helper as dh


def _content_chunk(content: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def _usage_chunk(p: int, c: int) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(prompt_tokens=p, completion_tokens=c, total_tokens=p + c),
    )


_OUT = "chapters/chapter-1.md"


def _dispatch_fake(
    monkeypatch,
    tmp_path,
    *,
    stream=None,
    state: Any = None,
    skill: str = "shenbi-chapter-drafting",
    prompt: str = "prompt ch1",
):
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")
    chunks = (
        stream
        if stream is not None
        else [_content_chunk(f"### FILE: {_OUT}\nbody\n"), _usage_chunk(100, 50)]
    )
    with (
        patch("openai.OpenAI") as mock_openai,
        patch(
            "shenbi.pipeline.dispatch_helper._build_skill_prompt",
            return_value=("sys", "user", [_OUT], [], {"style/style_profile.md": "# raw"}),
        ),
    ):
        mock_openai.return_value.chat.completions.create.return_value = chunks
        return dh._dispatch_via_api(skill, tmp_path, prompt, state=state)


def _state(loop: int = 7, feedback: str | None = "上一轮反馈") -> SimpleNamespace:
    return SimpleNamespace(
        chapter_loop=SimpleNamespace(
            retry_budget_consumed={"ch1-shenbi-chapter-drafting": loop},
            retry_feedback=(
                {"ch1-shenbi-chapter-drafting": feedback} if feedback is not None else {}
            ),
        )
    )


def _load_archive(tmp_path: Path) -> dict[str, Any]:
    files = list((tmp_path / "observability" / "dispatches").glob("*.json"))
    assert len(files) == 1, f"expected exactly 1 archive, got {len(files)}"
    return json.loads(files[0].read_text(encoding="utf-8"))


class TestSuccessArchive:
    def test_success_writes_archive_with_loop_id_and_feedback(self, tmp_path, monkeypatch):
        result = _dispatch_fake(monkeypatch, tmp_path, state=_state(), prompt="draft chapter 1")
        assert result.success
        rec = _load_archive(tmp_path)
        assert rec["loop_id"] == 7
        assert rec["feedback_ref"] == ar.sha256_of("上一轮反馈")
        blob = tmp_path / "observability" / "blobs" / rec["feedback_ref"].split(":", 1)[1]
        assert blob.read_text(encoding="utf-8") == "上一轮反馈"
        assert rec["response_blob"] == ar.sha256_of(result.stdout)
        assert rec["attempt"] == 1
        assert rec["chapter"] == 1  # "chapter 1" prompt 解析出章号 → 档名 ch001

    def test_no_state_means_null_loop_id_feedback(self, tmp_path, monkeypatch):
        result = _dispatch_fake(monkeypatch, tmp_path)  # state=None（8/13 无 state 调用点兼容）
        assert result.success
        rec = _load_archive(tmp_path)
        assert rec["loop_id"] is None and rec["feedback_ref"] is None

    def test_no_feedback_text_means_null_ref(self, tmp_path, monkeypatch):
        result = _dispatch_fake(monkeypatch, tmp_path, state=_state(feedback=None))
        assert result.success
        rec = _load_archive(tmp_path)
        assert rec["loop_id"] == 7 and rec["feedback_ref"] is None  # 首派无反馈可引

    def test_trace_payload_carries_additive_fields(self, tmp_path, monkeypatch):
        from shenbi.trace.writer import TraceWriter

        TraceWriter(tmp_path).append(  # 预置事件成链（trace 面已落地才追发纪律）
            actor="test", actor_role="SYSTEM", action="INIT", target="t"
        )
        result = _dispatch_fake(monkeypatch, tmp_path, state=_state())
        assert result.success
        events = [json.loads(l) for l in (tmp_path / "trace.jsonl").read_text().splitlines()]
        dispatch = [e for e in events if e["action"] == "DISPATCH"]
        assert len(dispatch) == 1
        payload = dispatch[0]["payload"]
        assert payload["loop_id"] == 7
        assert payload["feedback_ref"] == ar.sha256_of(
            "上一轮反馈"
        )  # audit-T4 M-3：§2 三字段端到端
        assert payload["archive_path"] is not None
        assert (tmp_path / payload["archive_path"]).exists()


class TestFailureBranches:
    def test_timeout_failure_branch_archives_with_null_response(self, tmp_path, monkeypatch):
        import httpx

        def _raise(*a, **k):
            raise httpx.TimeoutException("t")

        monkeypatch.setattr(dh, "_call_llm_streaming_with_retry", _raise)
        result = _dispatch_fake(monkeypatch, tmp_path, state=_state())
        assert not result.success
        rec = _load_archive(tmp_path)
        assert rec["response_blob"] is None and rec["finish_reason"] is None
        assert rec["loop_id"] == 7  # 加性字段照进失败档
        assert rec["usage"] is None or rec["usage"] == {}  # 失败分支 usage 豁免（audit-T4 M-3）

    def test_write_failure_branch_archives_despite_no_trace(self, tmp_path, monkeypatch):
        from shenbi.exceptions import DispatchWriteFailureError

        def _boom(*a, **k):
            raise DispatchWriteFailureError("sig")

        monkeypatch.setattr(dh, "_write_parsed_outputs", _boom)
        result = _dispatch_fake(monkeypatch, tmp_path)
        assert not result.success
        rec = _load_archive(tmp_path)  # 六类无 trace 返回位代表：归档仍在
        assert rec["response_blob"] is not None  # 有计费响应的失败
        assert not (tmp_path / "trace.jsonl").exists()  # 该失败位不发 DISPATCH trace

    def test_prompt_build_failure_no_archive_no_stats(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
        monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")

        def _boom(*a, **k):
            raise RuntimeError("contract missing")

        monkeypatch.setattr(dh, "_build_skill_prompt", _boom)
        result = dh._dispatch_via_api("shenbi-chapter-drafting", tmp_path, "prompt ch1")
        assert not result.success
        assert not (tmp_path / "observability" / "dispatches").exists()
        stats_file = tmp_path / "observability" / "archive-stats.json"
        assert (
            not stats_file.exists() or "archive_write_failed" not in stats_file.read_text()
        )  # audit-T4 M-4

    def test_archive_write_failure_never_blocks_dispatch(self, tmp_path, monkeypatch):
        def _failing_archive(*a, **k):
            raise RuntimeError("disk full")

        monkeypatch.setattr("shenbi.observability.archive.write_dispatch_archive", _failing_archive)
        result = _dispatch_fake(monkeypatch, tmp_path, state=_state())
        assert result.success  # fail-safe 纪律：归档炸不炸派发
        assert not (tmp_path / "observability" / "dispatches").exists()  # 归档确实没写成

    def test_disabled_env_writes_no_archive_but_dispatch_succeeds(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SHENBI_ARCHIVE_DISPATCH", "0")
        result = _dispatch_fake(monkeypatch, tmp_path, state=_state())
        assert result.success
        assert not (tmp_path / "observability" / "dispatches").exists()


class TestCacheManifestWiring:
    """audit-T2 M-4: cache-path manifest entries (source:cache) + raw pairing."""

    def test_inject_from_cache_creates_manifest_entry_and_raw(self, tmp_path, monkeypatch):
        from shenbi.contracts import OutputKind

        mock_contract = {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": [_OUT],
            "updates": [],
        }
        monkeypatch.setattr("shenbi.contracts.loader.load_contract", lambda s: mock_contract)
        shared = SimpleNamespace(
            raw_files={},
            world_rules="WORLD",
            character_list="CHARS",
            style_profile="STYLE",
            pending_hooks="HOOKS",
        )
        _, _, _, manifest, raw_reads = dh._build_skill_prompt(
            "shenbi-review-group-character",
            tmp_path,
            "prompt ch1",
            1,
            shared_context=shared,
        )
        cache_entries = [e for e in manifest if e.get("source") == "cache"]
        assert len(cache_entries) >= 3  # rules/character/style 注入（hooks 同）
        for e in cache_entries:
            assert e["mode"] == "full" and e["matched_all"] is True
            assert e["path"] in raw_reads  # raw 配对（缓存值）
        rules_path = next(e["path"] for e in cache_entries if "rules" in e["path"])
        assert raw_reads[rules_path] == "WORLD"
