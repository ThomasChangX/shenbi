# Bug-Hunt Report: shenbi-volume-outlining

**Date**: 2026-06-12
**Skill**: `skills/shenbi-volume-outlining/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

---

## Detection Summary

| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Volume 2 has zero cross-volume hooks (required: >= 3) | error | `story/volumes/volume-02-地下之根.md` L77 | YES |
| 2 | Hook type diversity is empty -- 0 types (required: >= 2) | error | `story/volumes/volume-02-地下之根.md` L117 | YES |
| 3 | Required 6-column hook table is entirely absent | error | `story/volumes/volume-02-地下之根.md` L116-117 | YES |

## Detection 1: Zero Cross-Volume Hooks

### Defect Location
`story/volumes/volume-02-地下之根.md` -- L77

### Defect Description
Volume 2's "跨卷桥接" section declares that all threads are resolved within the volume and explicitly states that no hooks carry forward to Volume 3:

L77: "第二卷所有线索已在本卷内圆满收束。地下网络训练完成，梵光教训已吸收，林烽思维转变已达成。无遗留钩子带入第三卷。"

The automated checklist at L125-126 confirms the gap with unchecked items:
- L125: `- [ ] 跨卷钩子 ≥ 3 个，类型 ≥ 2 种`
- L126: `- [ ] 钩子表 6 列全部非空`

The skill requires at least 3 entity hooks bridging to the next volume. Volume 2 has zero.

### Skill Rule Applied
**铁律三：跨卷桥接必有实体** -- "卷尾必须留下至少 1 个实体钩子（人物/物品/事件/信息）带入下卷"

**Evidence**: `story/volumes/volume-02-地下之根.md` L77: "第二卷所有线索已在本卷内圆满收束。地下网络训练完成，梵光教训已吸收，林烽思维转变已达成。无遗留钩子带入第三卷。"

---

## Detection 2: Hook Type Diversity Violation

### Defect Location
`story/volumes/volume-02-地下之根.md` -- L117

### Defect Description
The跨卷桥接汇总 reports hook type distribution as an empty list:

L117: `- 类型分布: []（≥ 2 种类型）`

The skill requires at least 2 distinct hook types from the allowed set {人物, 物品, 事件, 信息}. With zero hooks total, there are also zero hook types.

### Skill Rule Applied
**铁律三：跨卷桥接必有实体** -- "卷尾必须留下至少 1 个实体钩子（人物/物品/事件/信息）带入下卷"

The output format's 可自动检查的计数规则 further specifies: `钩子类型多样性 ≥ 2 种`

**Evidence**: `story/volumes/volume-02-地下之根.md` L117: `- 类型分布: []（≥ 2 种类型）`

---

## Detection 3: Hook Table Absent

### Defect Location
`story/volumes/volume-02-地下之根.md` -- L116-117

### Defect Description
The required 6-column hook table (using the EXACT format with columns: #, 钩子内容, 类型, 带入卷, 预期激活章, 当前状态) is completely absent. It has been replaced by summary prose at L116-117:

L116: `- 实体钩子数: 0（要求 ≥ 3）`
L117: `- 类型分布: []（≥ 2 种类型）`

The automated checklist at L126 confirms the table is missing: `- [ ] 钩子表 6 列全部非空`

### Skill Rule Applied
**铁律三：跨卷桥接必有实体** -- "卷尾必须留下至少 1 个实体钩子（人物/物品/事件/信息）带入下卷"

The output format specifies the hook table as mandatory with the instruction: "至少 3 行，至少 2 种不同类型" and column validation: "6 列全部非空，任一空值 = 不合格"

**Evidence**: `story/volumes/volume-02-地下之根.md` L116-117: the entire structured hook table is replaced by a two-line prose summary with `实体钩子数: 0` and `类型分布: []`.

### False Positive Check
Confirmed no clean content was incorrectly flagged. Checked: all other sections of Volume 2 pass their respective checks -- KR count = 3 (valid), all 3 KRs have opening+closing nodes, tension curve percentages sum to 100% (20+33+27+20=100) with each segment within allowed range, Objective is binary-judgeable, story_frame consistency section is fully populated, and KR chapter allocations have no single-chapter overload or gaps. Only the跨卷桥接 section violates the skill's rules.
