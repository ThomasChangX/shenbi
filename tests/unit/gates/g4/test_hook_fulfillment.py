def test_arc_payoff_accepts_deferred_verdict(tmp_path):
    """Canary defect (semantic, dormant): the arc-payoff verdict vocabulary
    was binary (放行/阻断) — an arc whose payoff window extends beyond the
    current volume honestly reports 暂缓/待定, and the gate failed it
    structurally (no_valid_verdict), forcing escalations for honest output.
    暂缓 is a passing, disclosed verdict: the arc is not yet judgeable.
    """
    import json

    from shenbi.gates.g4.review_arc_payoff import g4_review_arc_payoff

    report = tmp_path / "arc-payoff.md"
    report.write_text(
        "# 弧线兑付审查\n\n"
        "## 明细表\n\n| 弧线 | 覆盖章节 | 兑现质量 |\n|---|---|---|\n| A1 | 1-9 | 18 |\n\n"
        "## 门判定\n\n"
        "判定：暂缓（弧线 A2 的兑付窗口在第 40 章，当前卷界不可评判；A1 放行）。\n\n"
        "伏笔兑现质量 18 ≥ 子地板 15 ✓\n\n"
        "证据：chapters/chapter-9.md L45\n",
        encoding="utf-8",
    )
    result = json.loads(g4_review_arc_payoff([str(report)]))
    mf = result.get("must_fix", [])
    assert not any("G4.ap.verdict" in m for m in mf), f"暂缓 must be a valid verdict: {mf}"
    verdicts = [c.get("v") for c in result.get("checks", []) if c.get("id") == "G4.ap.verdict"]
    assert verdicts and verdicts[0] == "暂缓"
