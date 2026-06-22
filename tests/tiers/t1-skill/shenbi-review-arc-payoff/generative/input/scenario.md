# Generative Test: shenbi-review-arc-payoff

## Skill Under Test
`skills/shenbi-review-arc-payoff/SKILL.md`

## Test Setup
A volume/arc boundary has been reached and the arc-payoff score is needed. The following inputs exist:
- `tests/fixtures/multi-chapter-example/*.md` — the arc's chapter prose (chapters 1-5, the finished volume)
- `tests/fixtures/outline-example.md` — the volume outline carrying `volume_promise` + `arc_beats` for the arc under evaluation
- `tests/fixtures/truth-pending_hooks.md` — the pending-hooks truth file (resolved_this_arc + carried_forward)
- `tests/fixtures/truth-pending_hooks.md` also supplies the resonance_trend佐证 for 弧情感交付 (per-chapter 情感落地 series)
- `tests/fixtures/style-profile-example.md` — voice fingerprint for prose-craft cross-check
- `tests/fixtures/calibration/arc-payoff/**/*.md` — the high/mid/low anchors for 弧情感交付 / 伏笔兑现质量 / 线索收束 / 期待债务结算 / 角色弧推进

## Agent Task
Run shenbi-review-arc-payoff (in an independent agent — the volume-consolidation / drafting context must be cleared) to score the finished arc. The agent must:
1. Confirm the HARD-GATE precondition: arc chapters all passed resonance, volume prose + volume_map both present (else report `arc_payoff_pending`, no score)
2. Load the calibration anchors and score each of the 5 dimensions anchor-first (弧情感交付 25 / 伏笔兑现质量 25 / 线索收束 20 / 期待债务结算 15 / 角色弧推进 15), locating each arc's band relative to the high/mid/low anchors
3. Report confidence as high/mid/low per-dimension AND overall; apply confidence calibration (self-reported high with anchor hit-rate < 0.8 → downgrade to mid)
4. Land every dimension score on original-text file + line numbers + quoted excerpt; for 伏笔兑现质量 judge whether each resolved hook is "surprising+earned" vs "perfunctory/旁白交代"
5. Apply the §6.4 binary gate (overall ≥80 且 伏笔兑现质量 ≥15 → 放行; else 阻断+处方) as fixed thresholds, not hand-judgment
6. Produce the full output: 评分明细 table, 门判定, 处方 (if 阻断), 跨卷短板 → `truth/audit_drift.md`, and a `truth/arc_payoff_trend.md` append row

## Seed Input
Finished arc chapters from `tests/fixtures/multi-chapter-example/`; volume outline from `tests/fixtures/outline-example.md`; pending hooks from `tests/fixtures/truth-pending_hooks.md`; style from `tests/fixtures/style-profile-example.md`; anchors from `tests/fixtures/calibration/arc-payoff/`.
