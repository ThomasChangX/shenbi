"""Tests that _dispatch_via_api records response.usage to the ledger (spec §3.1)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _fake_response(content: str, usage=None):
    """Build an object shaped like the OpenAI ChatCompletion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=usage,
    )


class TestUsageCapture:
    def test_usage_recorded_on_success(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
        monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-pro")

        usage = SimpleNamespace(prompt_tokens=111, completion_tokens=222, total_tokens=333)
        # NOTE: _write_parsed_outputs expects "### FILE: <path>" markers
        # (see dispatch_helper._parse_file_outputs).
        fake_resp = _fake_response("### FILE: chapters/chapter-1.md\nbody\n", usage=usage)

        with (
            patch("openai.OpenAI") as mock_openai,
            patch(
                "shenbi.pipeline.dispatch_helper._build_skill_prompt",
                return_value=("sys", "user", ["chapters/chapter-1.md"]),
            ),
        ):
            mock_openai.return_value.chat.completions.create.return_value = fake_resp
            from shenbi.pipeline.dispatch_helper import _dispatch_via_api

            _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")

        ledger = (tmp_path / "cost" / "token-ledger.jsonl").read_text(encoding="utf-8")
        rec = json.loads(ledger.strip().splitlines()[-1])
        assert rec["skill"] == "shenbi-chapter-drafting"
        assert rec["prompt_tokens"] == 111
        assert rec["completion_tokens"] == 222
        assert rec["total_tokens"] == 333
        assert rec["model"] == "deepseek-v4-pro"

    def test_missing_usage_does_not_crash(self, tmp_path: Path, monkeypatch):
        """An endpoint that omits response.usage must not break dispatch."""
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
        fake_resp = _fake_response("### FILE: chapters/chapter-1.md\nbody\n", usage=None)
        with (
            patch("openai.OpenAI") as mock_openai,
            patch(
                "shenbi.pipeline.dispatch_helper._build_skill_prompt",
                return_value=("sys", "user", ["chapters/chapter-1.md"]),
            ),
        ):
            mock_openai.return_value.chat.completions.create.return_value = fake_resp
            from shenbi.pipeline.dispatch_helper import _dispatch_via_api

            result = _dispatch_via_api("shenbi-chapter-drafting", tmp_path, "Chapter 1 draft")
            assert result.success  # dispatch still succeeds
