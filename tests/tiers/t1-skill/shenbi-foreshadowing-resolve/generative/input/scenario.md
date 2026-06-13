# Generative Test: shenbi-foreshadowing-resolve

## Skill Under Test
`skills/shenbi-foreshadowing-resolve/SKILL.md`

## Test Setup
A novel project exists at the end of volume 2. The `tests/fixtures/pending-hooks-example.md` contains 12 active hooks with varying Chase Power values: 3 hooks have CP > 200 (red zone), 4 hooks have CP 100-200 (yellow/orange zone), and 5 hooks have CP < 100 (green zone). Two hooks are SMOKESCREEN type and one TRIGGERED hook is marked core_hook: true.

## Agent Task
Run shenbi-foreshadowing-resolve to resolve foreshadowing hooks at volume 2 end. Hooks with CP > 200 must trigger mandatory immediate resolution. Core hooks must achieve at least PARTIAL_PAYOFF, never FLAT_PAYOFF. High-CP hooks must be resolved first. Every active hook must be inventoried at volume end. SMOKESCREEN hooks must include truth revelation when resolved. Any ABANDON operations must have explicit human approval recorded.

## Seed Input
Hook state from `tests/fixtures/pending-hooks-example.md` and chapter summaries from `tests/fixtures/chapter-summaries-example.md`
