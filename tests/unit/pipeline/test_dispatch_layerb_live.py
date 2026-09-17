"""Dispatch-loop Layer B behavior tests (spec #65 §3.0).

Unlike tests/unit/pipeline/test_field_filtering.py (pure-function tests),
these exercise the REAL _build_skill_prompt read loop end-to-end: the
loader-normalized reads + read_fields sidecar must actually filter content
before it reaches user_prompt. G0.9: inputs are assembled from real
fixture products (real fixture file contents; trivial declared-header
seeding only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contracts import fields as fields_mod
from shenbi.pipeline import dispatch_helper as dh
from shenbi.pipeline.dispatch_helper import _build_skill_prompt

pytestmark = pytest.mark.unit


@pytest.fixture()
def warn_spy(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Spy WARN events on both emitting module loggers (repo structlog
    writes via PrintLoggerFactory — stdlib handlers see nothing; this is
    the tests/unit/contracts/test_fields.py:71-83 pattern applied to both
    emitters: fields module -> field_filter_missing_fields; dispatch_helper
    -> extractor_failed_fulltext).
    """
    events: dict[str, list[str]] = {"fields": [], "dispatch": []}

    def _spy(bucket: list[str], orig):
        def inner(event: str, **kw: object) -> None:
            bucket.append(event)
            orig(event, **kw)

        return inner

    monkeypatch.setattr(fields_mod.log, "warning", _spy(events["fields"], fields_mod.log.warning))
    monkeypatch.setattr(dh.log, "warning", _spy(events["dispatch"], dh.log.warning))
    return events


@pytest.fixture()
def project_tree(tmp_path: Path) -> Path:
    """Minimal shenbi-chapter-planning read set, real fixture content."""
    (tmp_path / "truth").mkdir()
    (tmp_path / "outline").mkdir()
    # truth/chapter_summaries.md: chapter-planning declares fields [已完成章节]
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "## 已完成章节\n\n第1章：占位。\n\n## OTHER_STUFF\n\nXYZZY_LEAK_MARKER 不该进 prompt。\n",
        encoding="utf-8",
    )
    # outline/volume_map.md from the G0.11 production mirror
    (tmp_path / "outline" / "volume_map.md").write_text(
        Path("tests/fixtures/volume-map-xinghuo.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # truth/current_state.md: shenbi-native seeded lineage (declared fields all present)
    (tmp_path / "truth" / "current_state.md").write_text(
        "## 系统演化阶段\n\n中期。\n\n## 参数当前位置\n\n第3卷。\n\n## 进行中的情节线\n\n主线。\n",
        encoding="utf-8",
    )
    (tmp_path / "outline" / "story_frame.md").write_text("STORY_FRAME_MARKER", encoding="utf-8")
    (tmp_path / "truth" / "current_focus.md").write_text("focus", encoding="utf-8")
    (tmp_path / "truth" / "author_intent.md").write_text("intent", encoding="utf-8")
    (tmp_path / "truth" / "pending_hooks.md").write_text(
        "## 活跃伏笔\n\nA。\n\n## 伏笔统计\n\n2 条。\n", encoding="utf-8"
    )
    (tmp_path / "novel.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_declared_fields_filter_in_dispatch_loop(
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # Declared section survives
    assert "已完成章节" in user_prompt
    # Undeclared section of the same file must NOT reach the prompt
    assert "XYZZY_LEAK_MARKER" not in user_prompt
    # No dispatch-module WARN on this clean path (extractor events arrive in T4)
    assert warn_spy["dispatch"] == []


def test_escape_hatch_warns_and_fulltext_on_missing_field(
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    # Sabotage: remove a declared field's header -> escape hatch must fire
    (project_tree / "truth" / "pending_hooks.md").write_text(
        "## 别的节\n\n无声明节。\n", encoding="utf-8"
    )
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    assert "field_filter_missing_fields" in warn_spy["fields"]
    # Full-text fallback: undeclared section present
    assert "别的节" in user_prompt


def test_string_reads_unfiltered(project_tree: Path) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # outline/story_frame.md is a string read -> full content present
    # (marker chosen to differ from the input key itself)
    assert "STORY_FRAME_MARKER" in user_prompt


POWER_SYSTEM_FIXTURE = Path("tests/fixtures/world-power-system-example.md")


@pytest.fixture()
def factual_tree(tmp_path: Path) -> Path:
    """review-group-factual read set with real power_system fixture content."""
    (tmp_path / "world").mkdir()
    (tmp_path / "truth").mkdir()
    (tmp_path / "chapters").mkdir()
    (tmp_path / "audits").mkdir()
    ps = POWER_SYSTEM_FIXTURE.read_text(encoding="utf-8")
    (tmp_path / "world" / "power_system.md").write_text(ps, encoding="utf-8")
    (tmp_path / "world" / "rules.md").write_text("rules", encoding="utf-8")
    (tmp_path / "world" / "locations.md").write_text("loc", encoding="utf-8")
    (tmp_path / "world" / "story_bible.md").write_text("bible", encoding="utf-8")
    (tmp_path / "truth" / "current_state.md").write_text("## 主角状态\n\n甲。\n", encoding="utf-8")
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "## 已完成章节\n\n1。\n", encoding="utf-8"
    )
    (tmp_path / "chapters" / "chapter-26.md").write_text("# 第26章\n\n正文。", encoding="utf-8")
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_power_system_fields_filter_in_dispatch(
    factual_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    from shenbi.cost.estimate import estimate_prompt_tokens

    ps_full = POWER_SYSTEM_FIXTURE.read_text(encoding="utf-8")
    full_len = len(ps_full.encode("utf-8"))
    assert full_len > 50_000  # fixture sanity (synthetic sample, 58,113B)
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-review-group-factual", factual_tree, "audit ch26", chapter=26
    )
    # Declared sections survive, undeclared filtered away
    assert "力量天花板" in user_prompt and "代价机制" in user_prompt
    assert "等级表" not in user_prompt  # undeclared section (appears only at fixture :38)
    # All four declared fields matched -> escape hatch silent
    assert warn_spy["fields"] == [], warn_spy["fields"]
    # Spec §7 byte metric: isolate the power_system CONTRIBUTION by
    # subtracting a no-power_system baseline prompt.
    (factual_tree / "world" / "power_system.md").unlink()
    _, baseline, _ = _build_skill_prompt(
        "shenbi-review-group-factual", factual_tree, "audit ch26", chapter=26
    )
    contribution = len(user_prompt.encode("utf-8")) - len(baseline.encode("utf-8"))
    assert 4_000 < contribution < full_len * 0.75  # deep cut, bounded below
    assert estimate_prompt_tokens(user_prompt) < estimate_prompt_tokens(baseline + ps_full)


def test_volume_extractor_happy_path(project_tree: Path, warn_spy: dict[str, list[str]]) -> None:
    from shenbi.cost.estimate import estimate_prompt_tokens

    vm_text = (project_tree / "outline" / "volume_map.md").read_text(encoding="utf-8")
    full = len(vm_text.encode("utf-8"))
    assert full > 26_000
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # ch26 in the xinghuo map falls in volume 2 (第16-35章). Assert on the
    # distinctive volume TITLES (not 第N卷 numerals — bridge rows mention those).
    assert "铁与火" in user_prompt  # current volume 2 title survived
    assert "觉醒之火" not in user_prompt  # volume 1 title filtered away
    # Spec §7: extractor_failed_fulltext appears ONLY in the failure case —
    # the happy path must be WARN-free.
    assert "extractor_failed_fulltext" not in warn_spy["dispatch"]
    # Spec §4.4/§7 byte metric: total volume_map contribution must drop
    # from full-text 26,334B to structured slivers. Isolate by no-volume_map
    # baseline subtraction. The total = extractor slice (~960B) PLUS the
    # pre-existing Task-13 plan-skeleton injection (~3.3KB, also sliced —
    # never full text); both faces vanish without volume_map.
    (project_tree / "outline" / "volume_map.md").unlink()
    _, baseline, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    contribution = len(user_prompt.encode("utf-8")) - len(baseline.encode("utf-8"))
    assert 300 < contribution < full * 0.25  # slivers only, deep cut from 26KB
    assert estimate_prompt_tokens(user_prompt) < estimate_prompt_tokens(baseline + vm_text)


def test_volume_extractor_chapter_none_fulltext(project_tree: Path) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "no chapter", chapter=None
    )
    assert "第一卷" in user_prompt and "第五卷" in user_prompt  # full text


def test_volume_extractor_failure_fulltext_and_warn(
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    # Existing file, unresolvable chapter -> full text + named WARN (no silent drop)
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch9999", chapter=9999
    )
    assert "第一卷" in user_prompt  # full-text fallback
    assert "extractor_failed_fulltext" in warn_spy["dispatch"]


def test_real_chapter_planning_contract_has_extractor() -> None:
    # T3's sidecar wired to the REAL skill contract
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-chapter-planning")
    assert c["read_extractors"]["outline/volume_map.md"] == "volume_chapter"


def test_volume_extractor_carries_kr_and_tension(project_tree: Path) -> None:
    """Final-review I1: the extractor must carry the CURRENT chapter's KR
    block and the volume tension table (chapter-planning's priority chain
    names 卷纲 Key Result as a source — volume_map.md:90-166).
    """
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # ch26 falls in vol-2 KR3 (第26章-第30章): its block must survive…
    assert "KR3: 梵天遗产发现与盟友建立" in user_prompt
    # …other KR blocks must not leak
    assert "KR1: 根据地雏形建立" not in user_prompt
    # the volume tension table is volume-level planning context: full table
    assert "卷内张力曲线" in user_prompt


def test_volume_extractor_survives_unreadable_map(
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    """Final-review I2: a binary/unreadable volume_map must degrade to the
    sentinel/full-text path with a WARN — never raise out of the prompt
    builder (parity with the loop's own except-Exception read guard).
    """
    (project_tree / "outline" / "volume_map.md").write_bytes(b"\xff\xfe\x00binary")
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    assert "binary or unreadable" in user_prompt or "第一卷" in user_prompt
    assert "extractor_failed_fulltext" in warn_spy["dispatch"]


@pytest.mark.parametrize("chapter", [27, 30])  # mid-range and range-end of KR3 (26-30)
def test_volume_extractor_kr_covers_full_range(project_tree: Path, chapter: int) -> None:
    """Final-review r2-A: the KR block must be carried for EVERY chapter in
    its 章节范围, not just the range-start chapter (full form 第26章 - 第30章
    defeated the compact-range regex).
    """
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, f"plan ch{chapter}", chapter=chapter
    )
    assert "KR3: 梵天遗产发现与盟友建立" in user_prompt
    assert "KR2: 首次主动进攻与师徒信任建立" not in user_prompt
