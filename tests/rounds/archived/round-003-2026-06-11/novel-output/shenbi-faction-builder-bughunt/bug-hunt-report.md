# Bug-Hunt Report: shenbi-faction-builder

**Date**: 2026-06-12
**Skill**: `skills/shenbi-faction-builder/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

---

## Detection Summary

| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Faction described as completely unified with zero internal contradictions | error | `world/factions/meidelan-maiban.md` L38-46 | YES |

## Detection 1: Missing Internal Contradictions in 梅德兰买办资产阶级

### Defect Location
`world/factions/meidelan-maiban.md` -- L38-46

### Defect Description
The "### 内部矛盾" section of the 梅德兰买办资产阶级 faction explicitly describes the organization as a perfectly unified monolith with no internal divisions whatsoever:

- L38: "梅德兰买办资产阶级是一个高度统一的整体。尽管在组织架构上分为矿业、贸易、金融三个分会，但三个分会之间不存在实质性的利益分歧或路线冲突。"
- L40: "所有成员...共享完全相同的利益目标"
- L41: "每个人对列塔尼亚的态度也完全一致"
- L44: "当前激化程度：无。买办阶级不存在任何内部矛盾，全体成员思想统一、利益一致、行动协调。"
- L46: "潜在引爆点：无。由于买办阶级完全统一，不存在任何可能从内部引爆的矛盾点。"

The faction is presented as "铁板一块" (a monolithic block) with zero internal tension, zero factional splits, zero dissenting voices, and zero potential stress points. The skill's internal矛盾 table (which requires at least 3 rows) is replaced by prose that repeatedly emphasizes the complete absence of any internal conflict.

### Skill Rule Applied
**铁律二：内部必有矛盾** -- "健康的势力必须存在至少 1 个内部派系分歧；铁板一块 = 失真"

**Evidence**: `world/factions/meidelan-maiban.md` L38: "梅德兰买办资产阶级是一个高度统一的整体。" L44: "当前激化程度：无。买办阶级不存在任何内部矛盾，全体成员思想统一、利益一致、行动协调。" L46: "潜在引爆点：无。由于买办阶级完全统一，不存在任何可能从内部引爆的矛盾点。"

### False Positive Check
Confirmed no clean content was incorrectly flagged. Checked: all other sections of the faction profile are structurally valid (层级结构 has 6 rows with proper structure, 跨势力动态 has 4 entries with valid relationship types, 利益驱动 has substantive prose, 锚点角色 names a key character). The internal contradictions section is the sole violator -- it contains zero矛盾 entries where the skill requires at least 3 (per the output format's 可自动检查的计数规则: "内部矛盾数 ≥ 3 个") and at minimum 1 per 铁律二.
