# Bug-Hunt Test: shenbi-foreshadowing-track

## Skill Under Test
`skills/shenbi-foreshadowing-track/SKILL.md`

## Test Setup
A novel project exists with foreshadowing tracking output for chapter 10 in `truth/pending_hooks.md`. Among the tracked hooks is `hook-001` (玉佩秘密), marked with `core_hook: true` and `status: ABANDONED`. The abandonment decision was made without human approval and without justification in the notes.

## Scenario
The foreshadowing tracking for chapter 10 has been completed. In the updated `truth/pending_hooks.md`, hook-001 (玉佩秘密) — a core hook with `core_hook: true` — has been marked as `status: ABANDONED`. The skill's iron rules state that `core_hook: true` hooks must never be ABANDONED, as abandoning a core hook causes story structure to break.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `truth/pending_hooks.md`: hook-001 entry | Core hook (core_hook: true) "玉佩秘密" marked as ABANDONED — core hooks must never be abandoned as this causes story fracture | error |

## Agent Task
Run shenbi-foreshadowing-track quality check on the chapter 10 tracking output. The agent must detect that a core hook has been inappropriately abandoned.
