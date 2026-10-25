"""spec #75 T6: scene-split step wiring + G4.xc manifest + revision fanout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import shenbi.pipeline.chapter_loop as cl

CW = json.dumps({"chapter_word": {"default": 3200, "min": 2800, "max": 4000}})


def _mk_bundle(n: int, pronoun: str = "他") -> str:
    filler = pronoun * 4 + "数了一遍。" * 380  # POV 可推导的正文
    parts = [
        f"===CH:{n}===",
        "## PRE_WRITE_CHECK",
        "",
        "- x",
        "",
        f"# 第{n}章",
        f"# 章题{n}",
        "",
        "<!--SCENE-->",
        filler,
        f"{n}号钩一？",
        "<!--SCENE-->",
        filler,
        f"{n}号钩二？",
        "",
        "## POST_WRITE_SELF_CHECK",
        "",
        "- y",
        "",
    ]
    return "\n".join(parts)


@pytest.mark.integration
def test_split_step_records_g4_xc(tmp_path: Path) -> None:
    p = tmp_path / "proj"
    (p / "chapters").mkdir(parents=True)
    (p / "staging" / "chapters").mkdir(parents=True)
    (p / "genre-config.json").write_text(CW, encoding="utf-8")
    (p / "staging" / "chapter-1-bundle.md").write_text(_mk_bundle(1), encoding="utf-8")
    (p / "staging" / "chapters" / "chapter-1-decisions.json").write_text("{}", encoding="utf-8")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            cl,
            "run_gate_g4",
            lambda *a, **kw: {"status": "PASS", "checks": [], "must_fix": []},
        )
        issues = cl._run_scene_split_step(p, 1)
    assert issues == []
    mf = json.loads((p / "pipeline-manifest.json").read_text(encoding="utf-8"))
    gates = mf["gates"]["chapter_loop"]["1"]["pipeline-scene-split"]
    assert "G4" in gates and "G4.xc" in gates  # 双键分离（latest-wins 防掩蔽）


@pytest.mark.integration
def test_xc_fail_feeds_circuit_breaker(tmp_path: Path) -> None:
    p = tmp_path / "proj"
    (p / "chapters").mkdir(parents=True)
    (p / "staging" / "chapters").mkdir(parents=True)
    (p / "genre-config.json").write_text(CW, encoding="utf-8")
    # 双章 bundle 但 ch1 正文 POV 我 → xc 会断（ch2 vs ch1）——构造单章避免
    (p / "staging" / "chapter-2-bundle.md").write_text(_mk_bundle(2, "他"), encoding="utf-8")
    (p / "staging" / "chapters" / "chapter-2-decisions.json").write_text("{}", encoding="utf-8")
    # ch1 第一人称 → ch2 第三人称 = POV 断裂
    (p / "chapters" / "chapter-1.md").write_text("我看见。我的手。我的账。", encoding="utf-8")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            cl,
            "run_gate_g4",
            lambda *a, **kw: {"status": "PASS", "checks": [], "must_fix": []},
        )
        issues = cl._run_scene_split_step(p, 2)
    assert any(i.startswith("XC ch2") for i in issues)


@pytest.mark.integration
def test_revision_fanout_bidirectional(tmp_path: Path) -> None:
    p = tmp_path / "proj"
    (p / "chapters").mkdir(parents=True)
    (p / "genre-config.json").write_text(CW, encoding="utf-8")
    (p / "chapters" / "chapter-1.md").write_text(
        "## PRE_WRITE_CHECK\n\n- x\n\n# 第1章\n# 题\n\n<!--SCENE-->\n我看见灯。\n钩？\n"
        "<!--SCENE-->\n我的手冷。\n钩二？\n\n## POST_WRITE_SELF_CHECK\n\n- y\n",
        encoding="utf-8",
    )
    (p / "chapters" / "chapter-1-pre-rev.md").write_text(
        (p / "chapters" / "chapter-1.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (p / "chapters" / "chapter-2.md").write_text(
        "## PRE_WRITE_CHECK\n\n- x\n\n# 第2章\n# 题2\n\n<!--SCENE-->\n他坐下。\n钩？\n"
        "<!--SCENE-->\n他起身。\n钩二？\n\n## POST_WRITE_SELF_CHECK\n\n- y\n",
        encoding="utf-8",
    )
    issues = cl._revalidate_revised_chapter(p, 1)
    # ch2 vs 修订后 ch1 的 POV 断裂被后向扇出捕获
    assert any("跨章复验 ch2" in i and "POV" in i for i in issues), issues[:4]
