"""spec #72 T8: release_split v2 — declarative scene-atomic packing (G0.9 §4).

Real publish fixtures (tests/fixtures/publish) back the qidian 1:1 tier,
title extraction and CLI/freeze/ledger faces; the fanqie scene-packing tier
runs on tmp_path-constructed marker chapters (no real #72 artifacts exist
before #79's regeneration — spec §4 G0.9 structural exemption).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import tools.release_split as rs
from tools.release_split import (
    settled_chapters,
)

REPO = Path(__file__).resolve().parents[3]
FIX = REPO / "tests" / "fixtures" / "publish"

CW = json.dumps(
    {
        "chapter_word": {
            "default": 3200,
            "min": 2800,
            "max": 4000,
            "fanqie_update": {"min": 1800, "max": 2800},
        },
        "primary_platform": "qidian",
    }
)

HOOK1 = "他把数目又数了一遍？"
HOOK2 = "门在身后合上了，他为什么没回头？"
HOOK3 = "那盏灯还亮着，没有人去熄它。"


def _marker_chapter(n: int, scenes: list[tuple[int, str]]) -> str:
    parts = ["## PRE_WRITE_CHECK", "", "- x", "", f"# 第{n}章", f"# 章题{n}", ""]
    for size, hook in scenes:
        parts += ["<!--SCENE-->", "灯" * size, hook, ""]
    parts += ["## POST_WRITE_SELF_CHECK", "", "- y", ""]
    return "\n".join(parts)


def _proj(
    tmp_path: Path,
    chapters: tuple[int, ...] = (1, 2, 3, 4),
    *,
    config: str | None = CW,
    markered: dict[int, list[tuple[int, str]]] | None = None,
) -> Path:
    p = tmp_path / "proj"
    (p / "chapters").mkdir(parents=True)
    for n in chapters:
        if markered and n in markered:
            (p / "chapters" / f"chapter-{n}.md").write_text(
                _marker_chapter(n, markered[n]), encoding="utf-8"
            )
        else:
            shutil.copy(FIX / f"chapter-{n}.md", p / "chapters" / f"chapter-{n}.md")
    if config is not None:
        (p / "genre-config.json").write_text(config, encoding="utf-8")
    return p


def _settle(
    p: Path,
    chapters: tuple[int, ...],
    *,
    fail_chapter: int | None = None,
    skip_split_key: int | None = None,
) -> None:
    """Construct a pipeline-manifest with per-chapter gate records."""
    gates: dict[str, dict[str, object]] = {}
    for n in chapters:
        skills: dict[str, dict[str, object]] = {
            "shenbi-chapter-planning": {"G4": _rec("PASS")},
            "pipeline-scene-split": {"G4": _rec("PASS")},
        }
        if n == skip_split_key:
            del skills["pipeline-scene-split"]
        if n == fail_chapter:
            skills["shenbi-chapter-planning"]["G4"] = [_rec("PASS"), _rec("FAIL")]  # noqa: typed as object
        gates[str(n)] = skills  # type: ignore[assignment]
    (p / "pipeline-manifest.json").write_text(
        json.dumps({"gates": {"chapter_loop": gates}}), encoding="utf-8"
    )


def _rec(status: str) -> dict[str, object]:
    return {"timestamp": "t", "gate": "G4", "result": {"status": status}}


def _run_tool(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "release_split.py"), str(project), *args],
        capture_output=True,
        text=True,
        cwd=REPO,
    )


def _ledger(p: Path, platform: str) -> dict[str, Any]:
    return json.loads((p / "publish" / platform / "releases.json").read_text(encoding="utf-8"))


# ── parse: scenes from durable markers ──────────────────────────────────


@pytest.mark.unit
def test_parse_extracts_scenes(tmp_path: Path) -> None:
    f = tmp_path / "chapter-1.md"
    f.write_text(_marker_chapter(1, [(950, HOOK1), (950, HOOK2)]), encoding="utf-8")
    ch = rs.parse_chapter(f)
    assert [s.size for s in ch.scenes] == [950 + len(HOOK1), 950 + len(HOOK2)]
    assert ch.scenes[0].last_line == HOOK1
    assert "<!--SCENE-->" not in ch.scenes[0].text
    assert ch.title == "章题1"


@pytest.mark.unit
def test_parse_real_fixture_zero_scenes(tmp_path: Path) -> None:
    ch = rs.parse_chapter(FIX / "chapter-1.md")
    assert ch.title == "明白纸"
    assert ch.scenes == ()  # pre-#72 real outputs carry no markers


# ── settled window ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_settled_latest_per_key() -> None:
    p = _settle_mk({1: "PASS", 2: "FAIL", 3: "PASS"})
    assert settled_chapters(p) == {1, 3}


def _settle_mk(spec: dict[int, str]) -> Path:
    import tempfile

    td = tempfile.TemporaryDirectory()
    p = Path(td.name) / "proj"
    p.mkdir(parents=True)
    gates: dict[str, dict[str, object]] = {}
    for n, verdict in spec.items():
        recs: object = [_rec("FAIL"), _rec(verdict)] if verdict == "PASS" else [_rec(verdict)]
        gates[str(n)] = {
            "shenbi-chapter-planning": {"G4": recs},
            "pipeline-scene-split": {"G4": [_rec("PASS")]},
        }
    (p / "pipeline-manifest.json").write_text(
        json.dumps({"gates": {"chapter_loop": gates}}), encoding="utf-8"
    )
    import atexit

    atexit.register(td.cleanup)
    return p


@pytest.mark.unit
def test_follower_settles_via_split_key() -> None:
    """N+1 无 drafting 键（bundle 派发只落 leader）——拆分键即生成链证据。"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "proj"
        p.mkdir()
        gates: dict[str, dict[str, object]] = {
            "1": {
                "shenbi-chapter-drafting": {"G4": [_rec("PASS")]},
                "pipeline-scene-split": {"G4": [_rec("PASS")]},
            },
            "2": {"pipeline-scene-split": {"G4": [_rec("PASS")]}},
        }
        (p / "pipeline-manifest.json").write_text(
            json.dumps({"gates": {"chapter_loop": gates}}), encoding="utf-8"
        )
        assert settled_chapters(p) == {1, 2}


@pytest.mark.unit
def test_unsettled_excluded_missing_split_key() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "proj"
        p.mkdir()
        gates: dict[str, dict[str, object]] = {
            "1": {"shenbi-chapter-drafting": {"G4": [_rec("PASS")]}},
            "2": {
                "shenbi-chapter-drafting": {"G4": [_rec("PASS")]},
                "pipeline-scene-split": {"G4": [_rec("PASS")]},
            },
        }
        (p / "pipeline-manifest.json").write_text(
            json.dumps({"gates": {"chapter_loop": gates}}), encoding="utf-8"
        )
        assert settled_chapters(p) == {2}  # 1 无拆分键（空洞不纳入）


# ── qidian tier: 1 章 = 1 更 ────────────────────────────────────────────


@pytest.mark.unit
def test_qidian_one_chapter_one_update(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    _settle(p, (1, 2))
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 0, r.stderr
    led = _ledger(p, "qidian")
    assert led["schema"] == "shenbi-releases-v2"
    per_ch = {c["chapter"]: len(c["releases"]) for c in led["chapters"]}
    assert per_ch == {1: 1, 2: 1}
    rel_files = sorted((p / "publish" / "qidian" / "releases").glob("release-*.md"))
    assert len(rel_files) == 2
    # 重题直发：题 = 章题（v1 双 H1 机制）
    titles = [r["title"] for c in led["chapters"] for r in c["releases"]]
    assert titles == ["明白纸", "城破那日"]


# ── fanqie tier: scene-atomic packing ───────────────────────────────────


@pytest.mark.unit
def test_fanqie_packs_scenes_declared_hooks(tmp_path: Path) -> None:
    scenes = {
        1: [(950, HOOK1), (950, HOOK2), (950, HOOK3)],
        2: [(950, HOOK1), (950, HOOK2), (950, HOOK3)],
    }
    p = _proj(tmp_path, (1, 2), markered=scenes)
    _settle(p, (1, 2))
    r = _run_tool(p, "--platform", "fanqie")
    assert r.returncode == 0, r.stderr
    led = _ledger(p, "fanqie")
    rels = [rel for c in led["chapters"] for rel in c["releases"]]
    # 6 场景 950×2=1900 → 3 更；每更落在场景边界（tail=场景钩）
    assert len(rels) == 3
    assert all(rel["cut_quality"] == "scene-hook" for rel in rels)
    tails = [rel["tail"] for rel in rels]
    # 分组 [[s1,s2],[s3,s4],[s5,s6]] → 尾钩 [钩2, 钩1, 钩3]
    assert tails == [HOOK2[:24], HOOK1[:24], HOOK3[:24]]
    for rel in rels:
        assert 1800 <= rel["chars"] <= 2800
    # 更文本无标记行
    for f in (p / "publish" / "fanqie" / "releases").glob("release-*.md"):
        assert "<!--SCENE-->" not in f.read_text(encoding="utf-8")


@pytest.mark.unit
def test_fanqie_cross_chapter_group(tmp_path: Path) -> None:
    # seq [1913,960,963,1910,963,960] → [[1913][960,963]×跨章][1910][963,960]]
    scenes = {
        1: [(1900, HOOK1), (950, HOOK2)],
        2: [(950, HOOK1), (1900, HOOK2), (950, HOOK1), (950, HOOK2)],
    }
    p = _proj(tmp_path, (1, 2), markered=scenes)
    _settle(p, (1, 2))
    r = _run_tool(p, "--platform", "fanqie")
    assert r.returncode == 0, r.stderr
    led = _ledger(p, "fanqie")
    assert led["totals"]["cross_chapter_groups"] >= 1


@pytest.mark.unit
def test_fanqie_unpackageable_defensive_exit1(tmp_path: Path) -> None:
    scenes = {1: [(1450, HOOK1), (1450, HOOK2), (1450, HOOK3)]}  # 灰域序列
    p = _proj(tmp_path, (1,), markered=scenes)
    _settle(p, (1,))
    r = _run_tool(p, "--platform", "fanqie")
    assert r.returncode == 1
    assert "不可打包" in r.stderr


@pytest.mark.unit
def test_fanqie_missing_config_exit1(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,), config=None, markered={1: [(950, HOOK1), (950, HOOK2)]})
    _settle(p, (1,))
    r = _run_tool(p, "--platform", "fanqie")
    assert r.returncode == 1
    assert "硬依赖" in r.stderr


@pytest.mark.unit
def test_unsettled_chapter_excluded(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    _settle(p, (1,), fail_chapter=2)
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 0, r.stderr
    led = _ledger(p, "qidian")
    assert [c["chapter"] for c in led["chapters"]] == [1]


@pytest.mark.unit
def test_through_narrows_not_forces(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2, 3, 4))
    _settle(p, (1, 2, 3, 4))
    r = _run_tool(p, "--platform", "qidian", "--through", "2")
    assert r.returncode == 0, r.stderr
    led = _ledger(p, "qidian")
    assert [c["chapter"] for c in led["chapters"]] == [1, 2]


@pytest.mark.unit
def test_platform_default_from_config(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,), markered={1: [(950, HOOK1), (950, HOOK2)]})
    _settle(p, (1,))
    # primary_platform=qidian → 缺省走起点档
    r = _run_tool(p)
    assert r.returncode == 0, r.stderr
    assert (p / "publish" / "qidian" / "releases.json").is_file()


@pytest.mark.unit
def test_platform_fallback_fanqie(tmp_path: Path) -> None:
    no_platform = json.dumps(
        {
            "chapter_word": {
                "default": 3200,
                "fanqie_update": {"min": 1800, "max": 2800},
            }
        }
    )
    p = _proj(tmp_path, (1,), config=no_platform, markered={1: [(950, HOOK1), (950, HOOK2)]})
    _settle(p, (1,))
    r = _run_tool(p)
    assert r.returncode == 0, r.stderr
    assert (p / "publish" / "fanqie" / "releases.json").is_file()


# ── 冻结三元 + 账本生命周期（v2 语义保留） ─────────────────────────────


@pytest.mark.unit
def test_freeze_unchanged_semantics(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,))
    _settle(p, (1,))
    assert _run_tool(p, "--platform", "qidian").returncode == 0
    led = _ledger(p, "qidian")
    led["chapters"][0]["releases"][0]["published"] = True
    (p / "publish" / "qidian" / "releases.json").write_text(
        json.dumps(led, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # 章未变：复跑 exit 0 且 published 位保持
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 0, r.stderr
    led2 = _ledger(p, "qidian")
    assert led2["chapters"][0]["releases"][0]["published"] is True


@pytest.mark.unit
def test_freeze_hash_drift_blocked(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,))
    _settle(p, (1,))
    assert _run_tool(p, "--platform", "qidian").returncode == 0
    led = _ledger(p, "qidian")
    led["chapters"][0]["releases"][0]["published"] = True
    (p / "publish" / "qidian" / "releases.json").write_text(
        json.dumps(led, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # 章正文漂移 → 内容哈希变 → 冻结硬错
    ch = p / "chapters" / "chapter-1.md"
    ch.write_text(ch.read_text(encoding="utf-8") + "\n多出来的一段。\n", encoding="utf-8")
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 1
    assert "冻结" in r.stderr


@pytest.mark.unit
def test_title_pattern_kept(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,))
    _settle(p, (1,))
    r = _run_tool(p, "--platform", "qidian", "--title-pattern", "《{章题}》")
    assert r.returncode == 0, r.stderr
    led = _ledger(p, "qidian")
    assert led["chapters"][0]["releases"][0]["title"] == "《明白纸》"


@pytest.mark.unit
def test_no_settled_chapters_exit1(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,))  # 无 manifest → 零已收束
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 1
    assert "已收束" in r.stderr


@pytest.mark.unit
def test_v1_heuristics_retired() -> None:
    import tools.release_split as mod

    for gone in ("SCENE_TRANSITION_WORDS", "TIERS", "classify_pair", "plan_releases", "CutSignals"):
        assert not hasattr(mod, gone), gone


# ── T8-F1 集成回归：真实拆分步产物 → settled 窗口（writer/reader 契约） ──


@pytest.mark.integration
def test_real_split_step_manifest_settles(tmp_path: Path) -> None:
    """End-to-end writer→reader: run the REAL _run_scene_split_step, then
    release_split must see both chapters settled (the T8-F1 breakage was
    exactly this contract — hand-built manifests on both sides hid it).
    """
    import shenbi.pipeline.chapter_loop as cl

    p = _proj(tmp_path, (1,), markered={1: [(1900, HOOK1), (1900, HOOK2)]})
    (p / "staging").mkdir(exist_ok=True)
    for n in (1,):
        side = p / "staging" / "chapters" / f"chapter-{n}-decisions.json"
        side.parent.mkdir(parents=True, exist_ok=True)
        side.write_text("{}", encoding="utf-8")
    bundle = ["===CH:1===", "## PRE_WRITE_CHECK", "", "- x", "", "# 第1章", "# 章题1", ""]
    for size, hook in [(1900, HOOK1), (1900, HOOK2)]:
        bundle += ["<!--SCENE-->", "灯" * size, hook, ""]
    bundle += ["## POST_WRITE_SELF_CHECK", "", "- y", ""]
    (p / "staging" / "chapter-1-bundle.md").write_text("\n".join(bundle), encoding="utf-8")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            cl,
            "run_gate_g4",
            lambda *a, **kw: {"status": "PASS", "checks": [], "must_fix": []},
        )
        assert cl._run_scene_split_step(p, 1) == []
    mf = json.loads((p / "pipeline-manifest.json").read_text(encoding="utf-8"))
    assert "pipeline-scene-split" in mf["gates"]["chapter_loop"]["1"]
    r = _run_tool(p, "--platform", "fanqie")
    assert r.returncode == 0, r.stderr
    led = _ledger(p, "fanqie")
    assert [c["chapter"] for c in led["chapters"]] == [1]


# ── F5: 保留面补网（v1 迁移缩水面） ─────────────────────────────────────


@pytest.mark.unit
def test_freeze_seq_drift_requires_renumber(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    _settle(p, (1, 2))
    assert _run_tool(p, "--platform", "qidian").returncode == 0
    led = _ledger(p, "qidian")
    led["chapters"][0]["releases"][0]["published"] = True
    led["chapters"][0]["releases"][0]["seq"] = 99  # 人为制造序号漂移
    led["chapters"][0]["releases"][0]["file"] = "release-0099.md"
    (p / "publish" / "qidian" / "releases.json").write_text(
        json.dumps(led, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 1
    assert "renumber" in r.stderr


@pytest.mark.unit
def test_freeze_vanished_chapter_blocks(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1, 2))
    _settle(p, (1, 2))
    assert _run_tool(p, "--platform", "qidian").returncode == 0
    led = _ledger(p, "qidian")
    led["chapters"][1]["releases"][0]["published"] = True
    (p / "publish" / "qidian" / "releases.json").write_text(
        json.dumps(led, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _settle(p, (1,))  # 章 2 跌出已收束窗口（模拟状态回退）
    (p / "chapters" / "chapter-2.md").unlink()
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 1
    assert "消失" in r.stderr


@pytest.mark.unit
def test_orphan_release_cleanup(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,))
    _settle(p, (1,))
    assert _run_tool(p, "--platform", "qidian").returncode == 0
    rel_dir = p / "publish" / "qidian" / "releases"
    orphan = rel_dir / "release-9999.md"
    orphan.write_text("孤儿", encoding="utf-8")
    assert _run_tool(p, "--platform", "qidian").returncode == 0
    assert not orphan.exists()


@pytest.mark.unit
def test_qidian_markers_stripped(tmp_path: Path) -> None:
    p = _proj(tmp_path, (1,), markered={1: [(1900, HOOK1), (1900, HOOK2)]})
    _settle(p, (1,))
    r = _run_tool(p, "--platform", "qidian")
    assert r.returncode == 0, r.stderr
    for f in (p / "publish" / "qidian" / "releases").glob("release-*.md"):
        assert "<!--SCENE-->" not in f.read_text(encoding="utf-8")
