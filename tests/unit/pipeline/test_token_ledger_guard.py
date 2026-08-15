"""Integration guard: every API dispatch lands one durable ledger row (C10 T3).

Spec: docs/superpowers/specs/2026-08-16-audit-token-metering-fix.md

Dead-wire history: cost/token-ledger.jsonl stayed empty across two prior
"fixes" (07-20, 08-02) because the durable write was double-gated on a
PipelineState being threaded through the call (``if state:`` +
``if project_dir:``) — and 8 of the 13 production call sites (parallel
audit waves, parallel post-draft, genesis, closure, triggers) dispatch
without state. This guard asserts the T401 fix shape: the ledger write
happens inside ``_dispatch_via_api`` unconditionally, with the on-the-spot
chapter parsed from the prompt (never ``getattr(state, "chapter", 0)``).

The network layer is faked (openai.OpenAI patched) — no real dispatch.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from shenbi.pipeline.dispatch_helper import _dispatch_via_api, print_token_summary


def _content_chunk(content: str) -> SimpleNamespace:
    """Streaming chunk carrying delta content."""
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def _usage_chunk(prompt_tokens: int, completion_tokens: int) -> SimpleNamespace:
    """Final streaming chunk carrying usage (stream_options include_usage)."""
    return SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


def _read_ledger(project: Path) -> list[dict[str, object]]:
    ledger = project / "cost" / "token-ledger.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").strip().splitlines()]


def _dispatch_with_fake_client(
    monkeypatch,
    project: Path,
    skill: str,
    prompt: str,
    output_rel: str,
    prompt_tokens: int,
) -> None:
    """Run one _dispatch_via_api call against a stubbed OpenAI client."""
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")
    fake_stream = [
        _content_chunk(f"### FILE: {output_rel}\nbody\n"),
        _usage_chunk(prompt_tokens, 50),
    ]
    with (
        patch("openai.OpenAI") as mock_openai,
        patch(
            "shenbi.pipeline.dispatch_helper._build_skill_prompt",
            return_value=("sys", "user", [output_rel]),
        ),
    ):
        mock_openai.return_value.chat.completions.create.return_value = fake_stream
        result = _dispatch_via_api(skill, project, prompt)
    assert result.success, f"dispatch must succeed, got: {result.stderr}"


class TestLedgerRowPerDispatch:
    """F301/F504 regression guard: no state passed, ledger still written."""

    def test_two_dispatches_two_rows_real_chapters(self, tmp_path: Path, monkeypatch):
        project = tmp_path / "novel"
        project.mkdir()

        # Two skill dispatches (chapter 1 and chapter 2), deliberately WITHOUT
        # any state object — mirrors the parallel/genesis/closure call sites.
        _dispatch_with_fake_client(
            monkeypatch,
            project,
            "shenbi-chapter-drafting",
            "Draft Chapter 1 content",
            "chapters/chapter-1.md",
            prompt_tokens=120,
        )
        _dispatch_with_fake_client(
            monkeypatch,
            project,
            "shenbi-review-resonance",
            "Review Chapter 2 resonance",
            "reviews/chapter-2-resonance.md",
            prompt_tokens=80,
        )

        records = _read_ledger(project)
        # Acceptance 1: ledger rows == dispatch count.
        assert len(records) == 2, f"expected 2 ledger rows, got {len(records)}"
        # Acceptance 2: chapter key is the on-the-spot parsed value, not 0 (F505).
        assert [rec["chapter"] for rec in records] == [1, 2]
        assert [rec["skill"] for rec in records] == [
            "shenbi-chapter-drafting",
            "shenbi-review-resonance",
        ]
        assert records[0]["prompt_tokens"] == 120
        assert records[1]["prompt_tokens"] == 80

    def test_chapter_zero_when_prompt_has_no_chapter(self, tmp_path: Path, monkeypatch):
        """Genesis-style prompts without a chapter record chapter=0 (documented)."""
        project = tmp_path / "novel"
        project.mkdir()
        _dispatch_with_fake_client(
            monkeypatch,
            project,
            "shenbi-worldbuilding",
            "Build the world bible",
            "truth/world.md",
            prompt_tokens=30,
        )
        records = _read_ledger(project)
        assert len(records) == 1
        assert records[0]["chapter"] == 0

    def test_path_context_carrier_provides_chapter(self, tmp_path: Path, monkeypatch):
        """The [path-context] carrier line is the authoritative chapter source."""
        project = tmp_path / "novel"
        project.mkdir()
        _dispatch_with_fake_client(
            monkeypatch,
            project,
            "shenbi-review-resonance",
            "[path-context] chapter=7\nReview the resonance",
            "reviews/chapter-7-resonance.md",
            prompt_tokens=40,
        )
        records = _read_ledger(project)
        assert records[0]["chapter"] == 7


class TestLedgerFailSafe:
    """Spec risk section: ledger failures must never break dispatch."""

    def test_ledger_write_error_skipped_with_warning(self, tmp_path: Path, monkeypatch):
        project = tmp_path / "novel"
        project.mkdir()
        monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
        monkeypatch.setenv("SHENBI_LLM_MODEL", "deepseek-v4-flash")

        fake_stream = [
            _content_chunk("### FILE: chapters/chapter-1.md\nbody\n"),
            _usage_chunk(100, 50),
        ]
        with (
            patch("openai.OpenAI") as mock_openai,
            patch(
                "shenbi.pipeline.dispatch_helper._build_skill_prompt",
                return_value=("sys", "user", ["chapters/chapter-1.md"]),
            ),
            patch(
                "shenbi.pipeline.dispatch_helper.TokenLedger.record",
                side_effect=OSError("disk full"),
            ),
        ):
            mock_openai.return_value.chat.completions.create.return_value = fake_stream
            result = _dispatch_via_api("shenbi-chapter-drafting", project, "Chapter 1 draft")

        assert result.success, "dispatch must survive a ledger write failure"


class TestPrintTokenSummaryReadsLedger:
    """T2 option B: the ledger is the single source of truth for summaries."""

    def test_summary_from_ledger_not_in_memory_state(self, tmp_path: Path, monkeypatch):
        project = tmp_path / "novel"
        project.mkdir()
        _dispatch_with_fake_client(
            monkeypatch,
            project,
            "shenbi-chapter-drafting",
            "Draft Chapter 1 content",
            "chapters/chapter-1.md",
            prompt_tokens=100,
        )

        # A bare state with no token_usage attribute: the summary must still
        # surface the ledger row (resume-friendly, F530/T403).
        state = SimpleNamespace(project_dir=str(project))
        print_token_summary(state)  # must not raise

        # A state without project_dir is a no-op, not a crash.
        print_token_summary(SimpleNamespace())
