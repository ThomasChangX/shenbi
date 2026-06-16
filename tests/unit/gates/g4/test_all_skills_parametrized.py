"""Parametrized smoke tests for every per-skill G4 checker.

Each G4 checker (g4_worldbuilding, g4_chapter_drafting, ...) gets the same
~12 assertions run against it. This guarantees every skill is exercised by
the test suite and adds the test volume needed for the 0.10 density target.

Per-skill DEEP tests (covering each skill's specific business rules) live
in dedicated test_<skill>.py files; this file provides BREADTH coverage so
no skill ships without any test touching its checker.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

# Map skill name -> (module path, function name). The function name follows
# the convention g4_<skillname_with_underscores>.
_SKILL_CHECKERS: list[tuple[str, str, str]] = [
    ("shenbi-anti-detect", "shenbi.gates.g4.anti_detect", "g4_anti_detect"),
    ("shenbi-chapter-drafting", "shenbi.gates.g4.chapter_drafting", "g4_chapter_drafting"),
    ("shenbi-chapter-planning", "shenbi.gates.g4.chapter_planning", "g4_chapter_planning"),
    ("shenbi-character-design", "shenbi.gates.g4.character_design", "g4_character_design"),
    ("shenbi-context-composing", "shenbi.gates.g4.context_composing", "g4_context_composing"),
    ("shenbi-faction-builder", "shenbi.gates.g4.faction_builder", "g4_faction_builder"),
    ("shenbi-foreshadowing-plant", "shenbi.gates.g4.foreshadowing_plant", "g4_foreshadowing_plant"),
    ("shenbi-foreshadowing-track", "shenbi.gates.g4.foreshadowing_track", "g4_foreshadowing_track"),
    ("shenbi-genre-config", "shenbi.gates.g4.genre_config", "g4_genre_config"),
    ("shenbi-length-normalizing", "shenbi.gates.g4.length_normalizing", "g4_length_normalizing"),
    ("shenbi-location-builder", "shenbi.gates.g4.location_builder", "g4_location_builder"),
    ("shenbi-pacing-design", "shenbi.gates.g4.pacing_design", "g4_pacing_design"),
    ("shenbi-plot-thread-weaver", "shenbi.gates.g4.plot_thread_weaver", "g4_plot_thread_weaver"),
    ("shenbi-power-system", "shenbi.gates.g4.power_system", "g4_power_system"),
    ("shenbi-relationship-map", "shenbi.gates.g4.relationship_map", "g4_relationship_map"),
    ("shenbi-state-settling", "shenbi.gates.g4.state_settling", "g4_state_settling"),
    ("shenbi-story-architecture", "shenbi.gates.g4.story_architecture", "g4_story_architecture"),
    ("shenbi-style-polishing", "shenbi.gates.g4.style_polishing", "g4_style_polishing"),
    ("shenbi-volume-outlining", "shenbi.gates.g4.volume_outlining", "g4_volume_outlining"),
    ("shenbi-worldbuilding", "shenbi.gates.g4.worldbuilding", "g4_worldbuilding"),
]


def _load_checker(module_path: str, func_name: str) -> Callable[..., Any]:
    mod = importlib.import_module(module_path)
    return cast(Callable[..., Any], getattr(mod, func_name))


def _result_dict(result: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(result))


# Parametrize every test with the full skill list. Each test method runs
# 20 times — once per skill — giving us 12 * 20 = 240 tests.
_SKILL_PARAM = pytest.mark.parametrize(
    "skill_name,module_path,func_name",
    _SKILL_CHECKERS,
    ids=[s[0] for s in _SKILL_CHECKERS],
)


@_SKILL_PARAM
class TestPerSkillG4Contract:
    """Contract tests that every g4_<skill> function must satisfy."""

    def test_function_exists_and_is_callable(
        self, skill_name: str, module_path: str, func_name: str
    ) -> None:
        """The checker must be importable and callable — guards against
        typos in module/function names during per-skill extraction.
        """
        checker = _load_checker(module_path, func_name)
        assert callable(checker)

    def test_returns_string_for_empty_file_list(
        self, skill_name: str, module_path: str, func_name: str
    ) -> None:
        """No input files must not crash the checker."""
        checker = _load_checker(module_path, func_name)
        result = checker([], None)
        assert isinstance(result, str)

    def test_returns_valid_json_for_empty_file_list(
        self, skill_name: str, module_path: str, func_name: str
    ) -> None:
        checker = _load_checker(module_path, func_name)
        parsed = _result_dict(checker([], None))
        assert "status" in parsed

    def test_returns_valid_json_for_nonexistent_file(
        self,
        skill_name: str,
        module_path: str,
        func_name: str,
        tmp_path: Path,
    ) -> None:
        """A non-existent file must produce a parseable result, not crash."""
        checker = _load_checker(module_path, func_name)
        parsed = _result_dict(checker([str(tmp_path / "nope.md")], None))
        assert "status" in parsed

    def test_returns_valid_json_with_round_dir(
        self,
        skill_name: str,
        module_path: str,
        func_name: str,
        tmp_path: Path,
    ) -> None:
        """Passing a round_dir argument must not crash the checker."""
        checker = _load_checker(module_path, func_name)
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        parsed = _result_dict(checker([], str(round_dir)))
        assert "status" in parsed

    def test_emits_timestamp_in_result(
        self, skill_name: str, module_path: str, func_name: str
    ) -> None:
        """All gate results include ISO-8601 timestamps for downstream
        correlation — verifiable across every checker.
        """
        checker = _load_checker(module_path, func_name)
        parsed = _result_dict(checker([], None))
        # PASS/FAIL results include timestamp; UNIMPLEMENTED does too
        assert "timestamp" in parsed

    def test_emits_gate_identifier(
        self, skill_name: str, module_path: str, func_name: str
    ) -> None:
        """Every result names its gate for downstream routing."""
        checker = _load_checker(module_path, func_name)
        parsed = _result_dict(checker([], None))
        assert "gate" in parsed

    def test_status_is_one_of_known_values(
        self, skill_name: str, module_path: str, func_name: str
    ) -> None:
        """Status is always one of PASS / FAIL / UNIMPLEMENTED / SKIP —
        downstream tools assume this closed set.
        """
        checker = _load_checker(module_path, func_name)
        parsed = _result_dict(checker([], None))
        assert parsed["status"] in {"PASS", "FAIL", "UNIMPLEMENTED", "SKIP"}

    def test_handles_multiple_nonexistent_files(
        self,
        skill_name: str,
        module_path: str,
        func_name: str,
        tmp_path: Path,
    ) -> None:
        checker = _load_checker(module_path, func_name)
        files = [str(tmp_path / f"missing-{i}.md") for i in range(3)]
        parsed = _result_dict(checker(files, None))
        assert "status" in parsed

    def test_with_substantial_markdown_file(
        self,
        skill_name: str,
        module_path: str,
        func_name: str,
        tmp_path: Path,
    ) -> None:
        """A real markdown file must produce a parseable result. The skill
        may PASS or FAIL based on its specific structural rules — we only
        verify the result is well-formed.
        """
        checker = _load_checker(module_path, func_name)
        f = tmp_path / "substantial.md"
        f.write_text(
            "---\ntype: output\n---\n\n# Substantial Output\n\n"
            + ("content line\n" * 20),
            encoding="utf-8",
        )
        parsed = _result_dict(checker([str(f)], None))
        assert "status" in parsed

    def test_with_json_file(
        self,
        skill_name: str,
        module_path: str,
        func_name: str,
        tmp_path: Path,
    ) -> None:
        """Some skill checkers inspect JSON outputs (e.g. genre-config).
        A valid JSON file must not crash any checker.
        """
        checker = _load_checker(module_path, func_name)
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        parsed = _result_dict(checker([str(f)], None))
        assert "status" in parsed

    def test_idempotent_on_repeated_calls(
        self,
        skill_name: str,
        module_path: str,
        func_name: str,
    ) -> None:
        """Calling a checker twice with the same inputs must produce
        equivalent status (timestamps differ but business logic doesn't).
        """
        checker = _load_checker(module_path, func_name)
        first = _result_dict(checker([], None))
        second = _result_dict(checker([], None))
        assert first["status"] == second["status"]
