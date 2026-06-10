# Clean Test: shenbi-short-packaging

## Skill Under Test
`skills/shenbi-short-packaging/SKILL.md`

## Test Setup
A 20-chapter short novel has been completed. The short packaging has been correctly run, producing packaging materials at `import/packaging/`.

All output is correct:
- Blurbs contain zero plot points from act 3; only tease act 1-2 setup
- Every selling point cites specific chapter + paragraph
- Cover prompt includes subject, scene, composition, color palette, style keywords
- Platform keywords match target platform tag taxonomy
- 4 titles (within 3-5 range), 2 blurbs (within 2-3 range), 4 selling points (within 3-5 range)
- All title candidates are semantically distinct

## Scenario
All short packaging output is correct and follows all skill rules.

## Agent Task
Run shenbi-short-packaging quality check on the packaging materials. Expected result: report zero issues.
