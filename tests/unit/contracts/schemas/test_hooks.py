# tests/unit/contracts/schemas/test_hooks.py
"""Tests for the HookState lifecycle enum + parser (fix D22).

Canaries:
- 6 canonical values present (PLANTED/RELEVANT/TRIGGERED/RESOLVED/ARCHIVED/EXPIRED).
- parse_hook_state is case-insensitive (lowercase ``triggered`` recognized).
- non-canonical ``TRIGGER`` folds to ``TRIGGERED``.
- ``state: EXPIRED`` loads and is NOT counted as TRIGGERED.
- empty/garbage input returns None (never raises) so call sites can short-circuit.
"""

from __future__ import annotations

from shenbi.contracts.schemas.hooks import HookState, parse_hook_state


class TestHookStateEnum:
    def test_six_canonical_values(self):
        assert {s.value for s in HookState} == {
            "PLANTED",
            "RELEVANT",
            "TRIGGERED",
            "RESOLVED",
            "ARCHIVED",
            "EXPIRED",
        }

    def test_is_str_enum(self):
        # str-enum: HookState.TRIGGERED == "TRIGGERED" (used in YAML comparisons)
        assert HookState.TRIGGERED == "TRIGGERED"


class TestParseHookState:
    def test_canonical_uppercase(self):
        assert parse_hook_state("TRIGGERED") is HookState.TRIGGERED
        assert parse_hook_state("PLANTED") is HookState.PLANTED
        assert parse_hook_state("EXPIRED") is HookState.EXPIRED

    def test_case_insensitive(self):
        # D22 canary: lowercase 'triggered' must be recognized.
        assert parse_hook_state("triggered") is HookState.TRIGGERED
        assert parse_hook_state("Triggered") is HookState.TRIGGERED
        assert parse_hook_state("tRiGgErEd") is HookState.TRIGGERED

    def test_noncanonical_trigger_maps_to_triggered(self):
        # SKILL.md:87 uses the bare 'TRIGGER' spelling.
        assert parse_hook_state("TRIGGER") is HookState.TRIGGERED
        assert parse_hook_state("trigger") is HookState.TRIGGERED

    def test_expired_not_triggered(self):
        # D22 canary: state: EXPIRED loads and is not counted as TRIGGERED.
        assert parse_hook_state("EXPIRED") is HookState.EXPIRED
        assert parse_hook_state("EXPIRED") is not HookState.TRIGGERED

    def test_expired_lowercase(self):
        assert parse_hook_state("expired") is HookState.EXPIRED

    def test_all_six_round_trip(self):
        for raw, expected in [
            ("PLANTED", HookState.PLANTED),
            ("RELEVANT", HookState.RELEVANT),
            ("TRIGGERED", HookState.TRIGGERED),
            ("RESOLVED", HookState.RESOLVED),
            ("ARCHIVED", HookState.ARCHIVED),
            ("EXPIRED", HookState.EXPIRED),
        ]:
            assert parse_hook_state(raw.lower()) is expected

    def test_empty_returns_none(self):
        assert parse_hook_state("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_hook_state("   ") is None

    def test_unknown_returns_none(self):
        # Unknown state does NOT raise (call sites short-circuit on None).
        assert parse_hook_state("FROBNICATED") is None
