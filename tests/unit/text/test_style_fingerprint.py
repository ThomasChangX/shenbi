"""Spec #77 T1 tests: four fingerprint metrics on constructed inputs (G0.9
structural exemption) + real-data calibration notes live in progress.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.text.style_fingerprint import (
    classify_opener,
    fingerprints,
    question_density,
    simile_domains,
)


@pytest.mark.unit
def test_question_density_dialogue_domain() -> None:
    body = "他问：「真的吗？为什么？怎么办？」他说完，走了很远很远的路，路过很多地方。"
    per_k, n_chars = question_density(body)
    assert n_chars >= 3
    assert per_k > 0


@pytest.mark.unit
def test_simile_domains_punctuation_window_and_morpheme_guard() -> None:
    body2 = "像一张纸。像那本账。像半张饼。"
    d2 = simile_domains(body2)
    assert d2["纸账册"] == 2 and d2["粮食物"] == 1
    # 好像/影像 词素不计
    d3 = simile_domains("好像有光。影像很清楚。画像上无人。")
    assert sum(d3.values()) == 0


@pytest.mark.unit
def test_classify_opener_skips_headings_and_quotes() -> None:
    body = "# Chapter 5:\n\n<!--META-->「谁？」\n\n他把米袋数了三遍。"
    # 数了 命中清点族（族序优先于数数族）
    assert classify_opener(body) == "清点"


def _mk_proj(tmp_path: Path, chapters: dict[int, str]) -> Path:
    (tmp_path / "chapters").mkdir(parents=True)
    for n, text in chapters.items():
        (tmp_path / "chapters" / f"chapter-{n}.md").write_text(text, encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_question_warn_consecutive(tmp_path: Path) -> None:
    noisy = "「真的吗？为什么呢？怎么办呀？到底行不行？谁说了算？」" * 20
    quiet = "他推门，落座，研墨，抄写，一天过去。"
    d = _mk_proj(tmp_path, {1: quiet, 2: quiet, 3: quiet, 4: quiet, 5: noisy})
    rows = fingerprints(d, 5)
    # 窗口 3-5：仅 ch5 超 → 无连续对 → 不 WARN
    assert not any("问号" in r for r in rows), rows
    d2 = _mk_proj(tmp_path / "b", {3: noisy, 4: noisy, 5: noisy})
    rows2 = fingerprints(d2, 5)
    assert any("style-warn:问号密度" in r for r in rows2)


@pytest.mark.unit
def test_simile_same_domain_warn_constructed(tmp_path: Path) -> None:
    same = "像一张纸。像半本账。像那册子。像一页契。像粗布。像细绳。像旧簿。"
    d = _mk_proj(tmp_path, {1: same, 2: same, 3: same})
    rows = fingerprints(d, 3)
    assert any("style-warn:喻体域" in r and "纸账册" in r for r in rows), rows


@pytest.mark.unit
def test_other_domain_info_not_warn(tmp_path: Path) -> None:
    odd = "像一场梦。像某个梦。像另一场梦。像更多的梦。像无穷的梦。像梦中的梦。"
    d = _mk_proj(tmp_path, {1: odd, 2: odd, 3: odd})
    rows = fingerprints(d, 3)
    assert any("style-info" in r for r in rows)
    assert not any("style-warn:喻体域" in r for r in rows)


@pytest.mark.unit
def test_opener_run_warn_constructed(tmp_path: Path) -> None:
    counting = "他把米袋数了三遍。然后出门。"
    other = "西仓的门朝北开着。风很大。"
    d = _mk_proj(tmp_path, {1: counting, 2: counting, 3: counting})
    rows = fingerprints(d, 3)
    assert any("style-warn:开头同构" in r and "清点" in r for r in rows), rows
    d2 = _mk_proj(tmp_path / "b", {1: other, 2: counting, 3: other})
    assert not any("开头同构" in r for r in fingerprints(d2, 3))


@pytest.mark.unit
def test_pre_rev_excluded_from_window(tmp_path: Path) -> None:
    counting = "他把米袋数了三遍。"
    other = "西仓的门朝北开着。"
    d = _mk_proj(tmp_path, {1: counting, 2: counting, 3: other})
    # pre-rev 备份若计入则 1-3 全计数族 → WARN；排除后 ch3 打断 → 不 WARN
    (d / "chapters" / "chapter-3-pre-rev.md").write_text(counting, encoding="utf-8")
    assert not any("开头同构" in r for r in fingerprints(d, 3))


@pytest.mark.unit
def test_genre_config_style_fingerprint_ranges(tmp_path: Path) -> None:
    import json

    from shenbi.contracts.skills.genre_config import GenreConfig

    gc_path = Path(__file__).resolve().parents[3] / "novel-xinghuo-vol1/genre-config.json"
    if not gc_path.is_file():
        pytest.skip("project data not present")
    base = json.loads(gc_path.read_text(encoding="utf-8"))
    base["market_params"]["styleFingerprint"] = {"question_per_k": 20, "simile_share": 0.6}
    GenreConfig.model_validate(base)
    bad = json.loads(json.dumps(base))
    bad["market_params"]["styleFingerprint"]["question_per_k"] = 99
    import pytest as _pytest

    with _pytest.raises(ValueError, match="styleFingerprint"):
        GenreConfig.model_validate(bad)


@pytest.mark.unit
def test_hook_appends_style_warn_rows(tmp_path: Path) -> None:
    """接线面：fingerprints 行经 _append_style_warn 落盘（append-only）。"""
    from shenbi.pipeline.chapter_loop import _append_style_warn

    (tmp_path / "truth").mkdir()
    _append_style_warn(tmp_path, "[style-warn:问号密度] ch3 测试行")
    _append_style_warn(tmp_path, "[style-warn:问号密度] ch3 测试行")
    text = (tmp_path / "truth" / "audit_drift.md").read_text(encoding="utf-8")
    assert text.count("测试行") == 2  # append-only：重复行保留（计数器结构性免疫）
    from shenbi.pipeline.triggers import count_drift_alerts

    assert count_drift_alerts(text) == 0  # 结构性排除验证


@pytest.mark.unit
def test_counting_opener_share_warn_constructed(tmp_path: Path) -> None:
    """指标 4：≥6 章窗内计数开篇占比超上限 → WARN（构造真阳性）。"""
    counting = "他把米袋数了三遍。然后出门。"
    other = "西仓的门朝北开着。风很大。"
    chapters = {n: (counting if n != 4 else other) for n in range(1, 7)}
    chapters[6] = counting  # 审计锚章
    d = _mk_proj(tmp_path, chapters)
    # pre-rev 备份不得膨胀分母
    (d / "chapters" / "chapter-4-pre-rev.md").write_text(other, encoding="utf-8")
    rows = fingerprints(d, 6)
    assert any("style-warn:数数开头" in r and "5/6" in r for r in rows), rows
    # 占比不过半不报
    d2 = _mk_proj(tmp_path / "b", {n: (other if n % 2 else counting) for n in range(1, 7)})
    assert not any("数数开头" in r for r in fingerprints(d2, 6))
