# Generative Test: shenbi-review-resonance

## Skill Under Test
`skills/shenbi-review-resonance/SKILL.md`

## Test Setup
A finished chapter has just been written and needs its positive resonance score. The following inputs exist:
- `tests/fixtures/chapter-7-example.md` — the finished chapter prose (with POST_WRITE_SELF_CHECK)
- `tests/fixtures/chapter-plan-example.md` — the chapter plan; for this test it declares `chapter_role: 推进/转折`
- `tests/fixtures/style-profile-example.md` — the voice_fingerprint / sentence_rhythm the prose is scored against
- `tests/fixtures/genre-config-example.json` — genre config (tropeInventory, fatigue words)
- `tests/fixtures/calibration/resonance/**/*.md` — the high/mid/low anchors for 情感落地 / 场景临场感 / 文笔质感 / 读者回报

## Agent Task
Run shenbi-review-resonance (in an independent agent — the drafting context must be cleared) to score the finished chapter. The agent must:
1. Load the calibration anchors and score each of the 4 dimensions anchor-first (情感落地 30 / 场景临场感 25 / 文笔质感 25 / 读者回报 20), locating each excerpt's band relative to the high/mid/low anchors
2. Report confidence as high/mid/low per-dimension AND overall; apply confidence calibration (self-reported high with anchor hit-rate < 0.8 → downgrade to mid)
3. Land every dimension score on original-text line numbers + quoted excerpt; for 情感落地 name the strongest emotion + its trigger line and judge show-vs-tell
4. Apply the calibration gate for `chapter_role: 推进/转折` (overall threshold ≥65, no dimension sub-floor) using the deterministic helper, not hand-judgment
5. Produce the full output: 评分明细 table, 校准门判定, a 共鸣短板 entry appended into the project's truth/audit_drift.md file, and a resonance_trend.md append row in truth/ (overall + 4 dimension scores + confidence band)
6. Route the result via §5.4 (放行 / 自动 chapter-revision / 人机复核)

## Seed Input
Finished chapter from `tests/fixtures/chapter-7-example.md`; plan from `tests/fixtures/chapter-plan-example.md` (chapter_role = 推进/转折); style from `tests/fixtures/style-profile-example.md`; genre config from `tests/fixtures/genre-config-example.json`; anchors from `tests/fixtures/calibration/resonance/`.
