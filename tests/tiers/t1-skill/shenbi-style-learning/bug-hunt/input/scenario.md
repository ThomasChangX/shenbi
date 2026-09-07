# Bug-Hunt Test: shenbi-style-learning

## Skill Under Test
`skills/shenbi-style-learning/SKILL.md`

## Test Setup
A novel project exists with reference writing samples at `tests/fixtures/samples/reference-texts/`. The agent has run style learning on the reference texts and produced a style profile at `tests/fixtures/style-profile-example.md`.

## Scenario
The style learning pass has been completed. The produced style profile mixes interpretive readings into what should be pure objective statistics. Specifically:

1. **Interpretive quality readings**: The profile's interpretation blocks include claims like:
   - "词汇丰富度高，作者用词多样化"
   - "情绪表达高度克制"
   - "作者有意识地使用短段制造节奏断裂"

   These are evaluative readings of the author's intent and quality, not pure measurements of what is.

2. **Per-chapter metric gaps**: The 各章统计 table computes 字数/句数/段数/词数/平均句长/平均段长 per chapter, but omits the per-chapter 对白占比 and 修辞模式 breakdowns that the global sections compute — so chapter-level dialogue ratio and rhetoric distribution cannot be verified from the profile.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/style-profile-example.md`: 解读/综合画像 sections | Objectivity violation — profile mixes interpretive judgments such as "词汇丰富度高，作者用词多样化" into what the skill requires to be pure objective statistics | error |
| `tests/fixtures/style-profile-example.md`: metrics section | Incomplete metrics — per-chapter table omits dialogue ratio and rhetoric breakdown, so chapter-level dimensions computed globally cannot be verified | error |

## Agent Task
Run shenbi-style-learning quality check on the produced style profile. The agent must detect the interpretive judgments (violating objectivity) and the unverifiable per-chapter statistical dimensions.
