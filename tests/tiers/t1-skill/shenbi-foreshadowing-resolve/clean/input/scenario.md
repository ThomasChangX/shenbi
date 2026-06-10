# Clean Test: shenbi-foreshadowing-resolve

## Skill Under Test
`skills/shenbi-foreshadowing-resolve/SKILL.md`

## Test Setup
A novel project exists with correct foreshadowing resolution output at volume 2 end:
- All hooks with CP > 200 have been resolved or have mandatory resolution scheduled
- Core hooks (core_hook: true) achieved at least PARTIAL_PAYOFF — none are FLAT_PAYOFF
- High-CP hooks were resolved first in the priority order
- Complete inventory of all active hooks at volume end
- SMOKESCREEN hooks resolved with truth revelation accompanying the payoff
- No ABANDON operations without explicit human approval recorded

## Scenario
All foreshadowing resolution content is correct and follows all skill rules. No missed high-CP hooks, no low-quality core hook payoffs, no missing volume inventory.

## Agent Task
Run shenbi-foreshadowing-resolve quality check on the existing resolution output. Expected result: report zero issues.
