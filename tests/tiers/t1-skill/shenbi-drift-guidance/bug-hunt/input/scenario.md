# Bug-Hunt Test: shenbi-drift-guidance

## Skill Under Test
`skills/shenbi-drift-guidance/SKILL.md`

## Test Setup
A novel project has completed chapter 14 and multiple audits have been run. The audit reports contain findings at different severity levels:
- `tests/fixtures/audit-report-example.md`: 发现项 #1 (warning, voice) — 了字密度超标 at 行59 (neighbour dialogue)
- `tests/fixtures/audit-report-example.md`: PRE_WRITE_CHECK 了字密度 row — WARNING (行 59)
- `tests/fixtures/audit-report-example.md`: OOC 检测 — 未发现角色行为违反已建立的性格 (clean)
- `tests/fixtures/audit-report-example.md`: 结果 header — 通过（1 warning, 0 errors）, 评分 9/10

The drift guidance output at `tests/fixtures/report-example.txt` contains 3 drift items. One of the items is derived from the audit's single warning-level finding (发现项 #1), presenting the 了字密度 issue as guidance for the next chapter.

## Scenario
The drift guidance forwards a warning-level finding but strips its provenance. 发现项 #1 is classified as warning in the audit and carries a precise location anchor (行59). Warnings may pass through to drift guidance, but each forwarded item must carry its source finding's severity marker and location anchor so the guidance stays traceable. The drift guidance output includes an item based on 发现项 #1 that drops both the warning classification and the 行59 anchor.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/report-example.txt`: drift item 1 | Provenance violation — drift item derived from audit 发现项 #1 (warning, 行59) drops both the severity marker and the 行59 location anchor; forwarded guidance must stay traceable to its source finding | error |

## Agent Task
Run shenbi-drift-guidance quality check on the drift guidance output. The agent must detect that the forwarded warning-derived drift item lost its severity classification and location anchor.
