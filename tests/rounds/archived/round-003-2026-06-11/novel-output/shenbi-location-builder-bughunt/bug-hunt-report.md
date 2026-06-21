# Bug-Hunt Report: shenbi-location-builder
**Date**: 2026-06-12
**Skill**: `skills/shenbi-location-builder/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

## Detection Summary
| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Contradictory travel times between 铁脊城 and 锻钢城: "乘马约三日" vs "快马半日可达" for the same 40km distance | error | `world/locations/铁脊城.md` L18, `world/locations/锻钢城.md` L18 | YES |

## Detection 1: Cross-Location Travel Time Contradiction (铁脊城 <-> 锻钢城)
### Defect Location
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-location-builder-bughunt/world/locations/铁脊城.md` -- L18
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-location-builder-bughunt/world/locations/锻钢城.md` -- L18

### Defect Description
The two location files describe the same route between 铁脊城 and 锻钢城 with the same distance but contradictory travel times. In `铁脊城.md` L18, the travel time from 铁脊城 to 锻钢城 is stated as `**行程时间**: 乘马约三日（必填）` (approximately three days by horse). In `锻钢城.md` L18, the travel time from 锻钢城 to its nearest landmark (铁脊城) is stated as `**行程时间**: 快马半日可达（必填）` (fast horse reaches in half a day). Both files agree on the distance: `**距离最近地标**: 40 km（必填）` at L17 in both files.

The contradiction is a 6x factor: 3 days (approximately 72 hours) vs half a day (approximately 12 hours, or even less if the journey is only during daylight). Even accounting for "乘马" (regular horse) vs "快马" (fast horse), a 6x difference for the same 40km distance is impossible under any reasonable travel speed assumptions. A horse at a slow walk covers approximately 5-6 km/h, making 40km achievable in 7-8 hours. Three days for 40km would imply an average speed of less than 0.6 km/h, which is walking pace with frequent stops -- incompatible with any mounted travel. Conversely, a fast horse covering 40km in half a day (approximately 6 hours) at approximately 7 km/h is physically plausible.

This contradiction violates cross-location spatial consistency: any plot event involving travel between these two cities (combat logistics, character movement, supply runs) would encounter unresolvable timeline conflicts depending on which file's travel time the writer references.

### Skill Rule Applied
**铁律二: 空间一致性**: "A 地点到 B 地点的距离、方向、行程时间必须与已设定一致；矛盾时人类仲裁"

**Evidence**:
- `铁脊城.md` L16-L18: `**最近地标**: 锻钢城（必填）` / `**距离最近地标**: 40 km（必填）` / `**行程时间**: 乘马约三日（必填）`
- `锻钢城.md` L16-L18: `**最近地标**: 铁脊城（必填）` / `**距离最近地标**: 40 km（必填）` / `**行程时间**: 快马半日可达（必填）`
- Both files L49-L52 (地理位置 section): Confirm bidirectional geographic relationship -- 铁脊城 lists 锻钢城 as "正北 40 km" with "灵能货运铁路直达", 锻钢城 lists 铁脊城 as "正南 40 km" with "灵能货运铁路直达"
- SKILL.md L33: "2. **空间一致性** -- A 地点到 B 地点的距离、方向、行程时间必须与已设定一致；矛盾时人类仲裁"
- SKILL.md L66-L68: "距离矩阵：A->B 的相对距离一旦确定不可轻易改动 / 地理逻辑：山、河、湖、城的位置关系必须自洽 / 行程时间：步行/骑行/飞行的合理时间"
- SKILL.md L168: Anti-Rationalization: `"跨地点一致性后面再核对"` -> Reality: `"一旦 A->B 距离写错，所有依赖此距离的情节连锁崩塌"`

### False Positive Check
Confirmed no clean content incorrectly flagged. Checked: Both files agree on distance (40km), direction (铁脊城 is south of 锻钢城 / 锻钢城 is north of 铁脊城), terrain (缓坡丘陵 with 灵能货运铁路), and neighboring landmarks. The sensory detail counts (6/5 in both files), functional event counts (>=3 in both), dominant senses, time-light-color coverage (>=2 periods), and section heading completeness all pass. The defect is strictly the travel time contradiction between the two files' frontmatter -- all other cross-location data is consistent.
