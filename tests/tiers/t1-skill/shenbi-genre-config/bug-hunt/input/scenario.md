# Bug-Hunt Test: shenbi-genre-config

## Skill Under Test
`skills/shenbi-genre-config/SKILL.md`

## Test Setup
A novel project exists with a genre-config file:
- `genre-config.json` — current genre configuration with banned words, caution words, and audit dimensions

## Scenario
The genre-config has been modified by the skill. A change was made to the banned word list (added 5 new entries) and to the audit dimension settings (enabled 3 new dimensions). However, no backup of the original `genre-config.json` was created before the modifications were applied. The modification log shows the changes but no backup path. This violates the change safety requirement that a backup must exist before any modification.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `genre-config.json` modification log | No backup created before modifying genre-config.json — original file was overwritten directly | error |

## Agent Task
Run shenbi-genre-config quality check on the recent configuration change. The agent must detect that no backup was created before the modification.
