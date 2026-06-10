# Generative Test: shenbi-drift-guidance

## Skill Under Test
`skills/shenbi-drift-guidance/SKILL.md`

## Test Setup
A novel project has completed chapter 18 and multiple audits have been run with a mix of error-level and warning-level findings. Audit reports exist at `audits/` including continuity, character, pacing, and foreshadowing audits. Each finding has a severity classification (error or warning) and a finding ID.

## Agent Task
Run shenbi-drift-guidance to produce drift guidance for the next chapter. The agent must:
1. Block all error-level findings (do not forward them)
2. Forward only warning-level findings as drift items
3. Ensure ≤5 drift items total (cap enforcement)
4. Make each item actionable with specific "what next chapter should do" guidance
5. Include targeted_chapter field with chapter number for each item
6. Make each item traceable to a specific audit finding (audit name + finding ID)

## Seed Input
Audit reports from `audits/`, truth files from `truth/`
