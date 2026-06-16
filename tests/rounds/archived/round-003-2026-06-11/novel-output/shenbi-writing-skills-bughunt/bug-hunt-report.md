# Bug-Hunt Report: shenbi-writing-skills

**Date**: 2026-06-12
**Skill Under Test**: `skills/shenbi-writing-skills/SKILL.md`
**Test Scenario**: `tests/tiers/t1-skill/shenbi-writing-skills/bug-hunt/input/scenario.md`

## Injected Defects

Three defects injected into `skills/custom-scene-transition/SKILL.md`:

1. **Weak iron laws**: Iron laws section rewritten with non-absolute language ("should", "recommended", "prefer to avoid", "generally", "usually") instead of required MUST/NEVER/ALWAYS.
2. **Missing anti-rationalization table**: Entire "## Anti-Rationalization Table" section removed. Only DOT flowchart and Red Flag checklist remain.
3. **Description trap**: Frontmatter description changed from trigger-condition-only to describing what the skill does: "Creates smooth scene transitions by managing emotional states, sensory anchors, and temporal markers between scenes."

**Injected file**: `tests/rounds/round-003-2026-06-11/novel-output/shenbi-writing-skills-bughunt/skills/custom-scene-transition/SKILL.md`

## Detection: Quality Check Results

Applying shenbi-writing-skills SKILL.md quality rules:

| # | Check Rule | Expected | Actual | Result |
|---|-----------|----------|--------|--------|
| 1 | Iron laws use absolute language (MUST/NEVER/ALWAYS) | MUST/NEVER/ALWAYS | "should", "recommended", "prefer to avoid" | FAIL |
| 2 | Anti-rationalization table present | Required section exists | Section absent | FAIL |
| 3 | Description = trigger condition only | "Use when..." | "Creates smooth scene transitions by..." | FAIL |
| 4 | DOT flowchart present | Required | Present and correct | PASS |
| 5 | Red flag checklist present | Required | Present and correct | PASS |
| 6 | Frontmatter format (name + description) | Valid YAML | Valid YAML | PASS |

## Findings

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| 1 | Iron law absoluteness violation -- 4+ rules use weak language instead of MUST/NEVER/ALWAYS | **error** | Line 82: "You should have one POV character per scene", Line 83: "You should always confirm the emotional state", Line 84: "It is recommended that scene transitions include a sensory anchor", Line 89: "Prefer to avoid abrupt POV shifts", Line 90: "Writers should not leave readers confused", Line 95: "Internal thoughts... are generally not recommended", Line 96: "Revealing information... is usually a violation", Line 97: "The narrator should typically maintain" |
| 2 | Skill completeness violation -- anti-rationalization table missing from skill body | **error** | Full document scan: "## Anti-Rationalization Table" section not found. Only DOT flowchart and Red Flag checklist present. Required per SKILL.md: "Each disciplinary skill MUST include an anti-rationalization table." |
| 3 | Description trap -- frontmatter description describes what skill does instead of when to trigger | **error** | Frontmatter line 3: `description: Creates smooth scene transitions by managing emotional states, sensory anchors, and temporal markers between scenes`. Should follow pattern: "Use when..." per SKILL.md frontmatter rules: "description 只描述触发条件" |

## Expected Non-Findings (Verified Clean)

- DOT flowchart is present and correctly structured -- NOT flagged
- Red flag checklist is present and complete -- NOT flagged
- Frontmatter YAML format is valid -- NOT flagged
- Name field uses valid characters (letters, digits, hyphens) -- NOT flagged

## Detection Verdict

**ALL 3 DEFECTS DETECTED.** The quality check rules in shenbi-writing-skills SKILL.md correctly catch all three planted defects:

1. Iron law absoluteness: SKILL.md iron law section states "关键规则使用绝对语言，不使用'通常'、'建议'、'推荐'" -- the injected text violates this with "should", "recommended", "prefer to avoid", "generally", "usually".
2. Missing anti-rationalization: SKILL.md requires "每个纪律性技能列举 AI 的偷懒借口及反驳" -- the section is entirely absent.
3. Description trap: SKILL.md frontmatter rules state "只描述触发条件，≤500字符" with explicit warning against describing what the skill does -- the injected description describes what it does.

## Summary

- **Defects injected**: 3
- **Defects detected**: 3
- **False positives**: 0
- **False negatives**: 0
- **Overall**: PASS -- quality check correctly identifies all three violations
