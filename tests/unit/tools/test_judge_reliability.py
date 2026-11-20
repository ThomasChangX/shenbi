"""Unit tests for tools/judge_reliability.py (spec #110).

Constructed structural corpora under tmp_path — G0.9 structural-input
exemption; the real starvation fixture is consumed read-only via its
canonical classifier (evidence-priority rule, spec acceptance #3).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

HARD_LINE = "- [BLOCKING] 时序矛盾：ch3 与 ch5 对同一事件的日期记述冲突\n"
MINOR_LINE = "- [MINOR] 用词重复\n"
# 生产词族 token（NARROW6「无法核对」——「无法验证」仅 WIDE12，不命中生产分类器）
STARVE_BODY = "**判定**: 不通过（无法核对）\n"


def _write(dir_: Path, name: str, body: str) -> None:
    p = dir_ / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_scan_audits_dual_caliber_ratings_and_hygiene(tmp_path) -> None:
    from tools.judge_reliability import AuditRecord, scan_audits

    audits = tmp_path / "audits"
    _write(audits, "chapter-1-texture.md", f"**判定**：有瑕疵\n{HARD_LINE}{MINOR_LINE}")
    _write(audits, "chapter-1-sensitivity.md", f"**判定**：有瑕疵\n{MINOR_LINE}")  # 仅 MINOR
    _write(audits, "chapter-2-texture.md", STARVE_BODY)  # 饿死形态→invalid
    _write(audits, "chapter-1-review-summary.md", "汇总（不参与）")
    res = scan_audits(audits)
    assert res.file_total == 3  # summary 排除（aggregate 无 -skill 段不匹配）
    by = {(r.chapter, r.skill): r for r in res.records}
    assert by[(1, "texture")] == AuditRecord(
        chapter=1, skill="texture", any_binary=1, hard_binary=1, hard_count=1, any_count=2
    )
    assert by[(1, "sensitivity")].any_binary == 1
    assert by[(1, "sensitivity")].hard_binary == 0
    assert by[(1, "sensitivity")].hard_count == 0
    assert by[(1, "sensitivity")].any_count == 1
    assert (2, "texture") not in by  # invalid 剔除
    assert len(res.invalid) == 1 and "chapter-2-texture.md" in res.invalid[0]


def test_real_starve_fixture_classified_invalid() -> None:
    """验收 3 优先项：真实饿死 fixture 经 #109 单源分类器判 invalid。"""
    from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict

    fixture = REPO_ROOT / "tests/fixtures/audits/chapter-2-memo-compliance.md"
    assert fixture.exists() and check_audit_starve_verdict(fixture)


def test_cohen_kappa_identical_raters() -> None:
    from tools.judge_reliability import cohen_kappa

    res = cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0])
    assert res.kappa == 1.0 and res.agreement == 1.0 and res.n == 4 and res.warning is None


def test_cohen_kappa_prevalence_degenerate_warns() -> None:
    from tools.judge_reliability import cohen_kappa

    res = cohen_kappa([0, 0, 0, 0], [0, 0, 0, 0])  # 全零 flag 技能对
    assert res.kappa is None and res.warning is not None and "prevalence" in res.warning


def test_cronbach_alpha_identical_items_is_one() -> None:
    from tools.judge_reliability import cronbach_alpha

    assert cronbach_alpha([[1, 0, 1, 1], [1, 0, 1, 1], [1, 0, 1, 1]]) == 1.0


def test_cronbach_alpha_independent_items_near_zero() -> None:
    import random

    from tools.judge_reliability import cronbach_alpha

    rng = random.Random(110)
    items = [[float(rng.randint(0, 1)) for _ in range(400)] for _ in range(8)]
    alpha = cronbach_alpha(items)
    assert alpha is not None and abs(alpha) < 0.10  # 独立→α≈0


def test_pearson_and_slope_with_guards() -> None:
    from tools.judge_reliability import SlopeResult, pearson, slope_regression

    r = pearson([1, 2, 3, 4], [2, 4, 6, 8])
    assert r is not None and abs(r - 1.0) < 1e-9
    sr = slope_regression([1.0, 2.0, 3.0, 4.0], [78.0, 78.7, 79.4, 80.1])
    assert abs(sr.slope - 0.7) < 1e-9 and sr.t == float("inf")  # r=±1→∞（M2）
    assert slope_regression([1.0], [78.0]) == SlopeResult(0.0, 0.0, 0.0)  # n<2 自守


def test_shape_stats_mode_sd_and_cold_start() -> None:
    from tools.judge_reliability import shape_stats

    st = shape_stats([79.0] * 12 + [78.0] * 3 + [86.0, 74.0], ["high"] * 15 + ["mid"] * 2)
    sd = st["sd"]
    assert st["mode"] == (79.0, 12) and isinstance(sd, float) and sd > 0
    assert st["range"] == (74.0, 86.0)
    assert st["high_rate"] == 15 / 17 and st.get("insufficient") is None
    cold = shape_stats([79.0, 78.0, 77.0], ["high", "mid", "low"])
    assert cold.get("insufficient") is True


def test_anchor_position_counts_first_table_only(tmp_path) -> None:
    from tools.judge_reliability import anchor_position_counts

    audits = tmp_path / "audits"
    _write(
        audits,
        "chapter-1-resonance.md",
        "| 维度 | 得分 | 满分 | 置信度 | 对照锚点 | 相对位置 | 证据 | 裁判理由 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 情感落地 | 22 | 30 | high | AC-001 | 相当 | L45 | show 充分 |\n"
        "| 场景临场感 | 20 | 25 | mid | AC-004 | 更差 | L12 | 概述偏多 |\n\n"
        "## 其他表\n\n"
        "| 列甲 | 列乙 |\n|---|---|\n| x | 相当 |\n",  # 次表不误计（M1）
    )
    c = anchor_position_counts(audits)
    assert c["相当"] == 1 and c["更差"] == 1 and c["更好"] == 0


MINI_TREND = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
    + "".join(f"| {i} | 推进 | 20 | 20 | 20 | 15 | {75 + i} | high |  |\n" for i in range(1, 9))
)


def _mini_project(tmp_path: Path) -> Path:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)  # 幂等（确定性测试二次调用）
    (tmp_path / "truth" / "resonance_trend.md").write_text(
        "---\ntype: truth\n---\n\n# 共鸣趋势\n\n" + MINI_TREND, encoding="utf-8"
    )
    audits = tmp_path / "audits"
    for ch in range(1, 9):
        _write(
            audits,
            f"chapter-{ch}-sensitivity.md",
            f"**判定**：有瑕疵\n{HARD_LINE}" if ch % 2 else "**判定**：通过\n",
        )
        _write(
            audits,
            f"chapter-{ch}-resonance.md",
            "**判定**：通过 (80/100)\n"
            "| 维度 | 得分 | 满分 | 置信度 | 对照锚点 | 相对位置 | 证据 | 裁判理由 |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| 情感落地 | 22 | 30 | high | AC-001 | 相当 | L1 | x |\n",
        )
        _write(
            audits, f"chapter-{ch}-world-rules.md", "**判定**：通过\n"
        )  # 全零对→prevalence 退化行
        _write(audits, f"chapter-{ch}-pacing.md", "**判定**：通过\n")
    (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
    for ch in range(1, 9):
        (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(
            "字" * (1000 * ch), encoding="utf-8"
        )
    return tmp_path


def test_build_report_sections_and_determinism(tmp_path) -> None:
    from tools.judge_reliability import build_report

    report = build_report(_mini_project(tmp_path))
    for needle in (
        "前置数据卫生",
        "Cronbach α",
        "效度相关",
        "外部锚定未执行",
        "观测面",
        "prevalence",
    ):
        assert needle in report, f"报告缺节：{needle}"
    assert build_report(_mini_project(tmp_path)) == report  # 同输入同输出（_mini_project 幂等）


def test_group_pair_not_degrouped_emits_artifact_warning(tmp_path) -> None:
    """④(c) 红测：同族对（pov×dialogue）带伪影注记+族 OR 合成 rater 行（I2）。"""
    from tools.judge_reliability import build_report

    proj = _mini_project(tmp_path)
    for ch in range(1, 9):
        _write(proj / "audits", f"chapter-{ch}-pov.md", "**判定**：通过\n")
        _write(proj / "audits", f"chapter-{ch}-dialogue.md", "**判定**：通过\n")
    report = build_report(proj)
    assert "dialogue × pov" in report and "同派发伪影" in report
    assert "group-character(OR)" in report and "族 OR 合成" in report


def test_main_missing_trend_exits_two(tmp_path, capsys) -> None:
    """M7：数据面缺失 → stderr + exit 2（report_longitudinal 先例）。"""
    from tools.judge_reliability import main

    empty = tmp_path / "proj"
    (empty / "truth").mkdir(parents=True)
    assert main([str(empty)]) == 2
    assert "resonance_trend" in capsys.readouterr().err


def test_spec107_references_110_mcnemar() -> None:
    spec107 = REPO_ROOT / "docs/superpowers/specs/2026-11-15-spec107-reviewer-model-tier.md"
    text = spec107.read_text(encoding="utf-8")
    assert "#110" in text and "McNemar" in text, "#107 T2 须含 #110 McNemar 配对设计引用行"
