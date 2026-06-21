# Bug-Hunt Report: shenbi-relationship-map
**Date**: 2026-06-12
**Skill**: `skills/shenbi-relationship-map/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

## Detection Summary
| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | 林烽-格鲁斯塔夫 relationship missing evolution trajectory: no 起始状态, no 演化轨迹, no 预期终态 | error | `characters/relationships.md` L98-L116 | YES |

## Detection 1: Missing Evolution Trajectory for Protagonist-Antagonist Relationship
### Defect Location
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-relationship-map-bughunt/characters/relationships.md` -- L98-L116

### Defect Description
The relationship pair 林烽-格鲁斯塔夫 (protagonist-antagonist, the central conflict driver of the entire novel) at L98-L116 contains type classification, interest grounding, faction affiliations, and 5 information boundary entries (ASYM-009 through ASYM-014) -- but the evolution planning fields required by the SKILL.md are entirely missing. The section has only `**当前状态**` at L114-L116 ("bitter enemies（激烈敌对）。两人竞争生存利益...") describing current antagonism, but lacks:
- **起始状态** -- no Act-anchored starting state for the relationship
- **演化轨迹** -- no turning points mapped to Act/story structure
- **预期终态** -- no expected end state with arc direction (FALL/REDEMPTION/etc.)

For comparison, all 31 other relationship pairs in the same file have complete evolution plans. For example, the adjacent 林烽-老政委 pair (L49-L70) includes `**起始状态** (Act 1末)` at L64, a 4-stage `**演化轨迹**` at L65-L69 spanning Act 2 through Act 3, and `**预期终态**` at L70. The anti-rationalization table explicitly rejects the excuse: "关系演化太麻烦，先写主线" -> Reality: "关系无演化 = 角色扁平 = 200章后人物失温".

### Skill Rule Applied
**铁律三: 关系可演化**: "每个关系必须定义起点状态和预期终点状态（中间可分段）"

**Evidence**:
- `relationships.md` L98-L116: The entire 林烽-格鲁斯塔夫 section -- compare L114 `**当前状态**` (not `**起始状态**`) to the required fields per SKILL.md L97-L100 output format: `**起始状态**: [第1章时]`, `**演化轨迹**: - 第N章: [变化]`, `**预期终态**: [升温/破裂/...]`
- `relationships.md` L49-L70: Neighboring 林烽-老政委 pair fully compliant -- `**起始状态**` at L64, `**演化轨迹**` L65-L69, `**预期终态**` L70
- SKILL.md L38: "3. **关系可演化** -- 每个关系必须定义起点状态和预期终点状态（中间可分段）"
- SKILL.md L80: Evolution directions defined: "升温/降温/破裂/重建/反转/揭露（揭示隐藏关系）"
- SKILL.md L147: Anti-Rationalization: `"关系演化太麻烦，先写主线"` -> Reality: `"关系无演化 = 角色扁平 = 200章后人物失温"`

### False Positive Check
Confirmed no clean content incorrectly flagged. Checked: All 31 other relationship pairs have complete `**起始状态**`, `**演化轨迹**`, and `**预期终态**` fields. The 5 ASYM entries (L105-L112) and interest/emotion grounding (L100-L101) in the 林烽-格鲁斯塔夫 section are valid content -- only the missing evolution fields constitute the defect. The defect is isolated to this single relationship pair.
