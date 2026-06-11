# Bug-Hunt Test: shenbi-drift-guidance

## Skill Under Test
`skills/shenbi-drift-guidance/SKILL.md`

## Test Setup
A novel project has completed chapter 14 and multiple audits have been run. The audit reports contain findings at different severity levels:
- `audits/chapter-14-continuity.md`: Finding CC-F001 (error) — "Character Zhao Lin refers to an event that has not occurred yet"
- `audits/chapter-14-continuity.md`: Finding CC-F002 (warning) — "Market scene lacks sensory detail"
- `audits/chapter-14-character.md`: Finding CH-F001 (warning) — "Dialogue voice for Mei Ling inconsistent with profile in chapter 14"
- `audits/chapter-14-pacing.md`: Finding PC-F001 (warning) — "Middle section pacing slows noticeably"

The drift guidance output at `guidance/drift-chapter-14.md` contains 3 drift items. One of the items is derived from the error-level finding CC-F001, presenting it as guidance for the next chapter.

## Scenario
The drift guidance incorrectly conducts an error-level finding forward. Finding CC-F001 is classified as "error" in the audit, meaning it represents a definitive problem that must be fixed (not forwarded as drift guidance). Only warnings should pass through to drift guidance. However, the drift guidance output includes an item based on CC-F001 that says "Next chapter should address the timeline inconsistency with Zhao Lin's reference."

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `guidance/drift-chapter-14.md`: drift item 1 | Classification violation — error-level finding CC-F001 (character refers to event that has not occurred) is conducted forward as drift guidance; only warnings should pass, errors must be blocked | error |

## Agent Task
Run shenbi-drift-guidance quality check on the drift guidance output. The agent must detect that an error-level audit finding was incorrectly included in the drift guidance instead of being blocked.
