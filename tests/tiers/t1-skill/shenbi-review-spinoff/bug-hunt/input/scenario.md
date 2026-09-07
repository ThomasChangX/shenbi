# Bug-Hunt Test: shenbi-review-spinoff

## Skill Under Test
`skills/shenbi-review-spinoff/SKILL.md`

## Test Setup
A spinoff novel project exists alongside a parent novel. The parent novel's chapter summaries at `tests/fixtures/chapter-summaries-example.md` record all events and plant the hidden external-power hint as scattered fragments: hook-ch1-003 is deliberately seeded across three fragments (furnace inscription, collector's wording, neighbor's mine remark), and both files record the phrase "上面定的规矩" for the collector. The spinoff novel's chapter at `tests/fixtures/chapter-draft-example.md` contains a scene touching the same hidden power: the collector attributes the debt rules to the unnamed authority, saying plainly that these are 上面定的规矩.

## Scenario
The agent runs a spinoff audit on the spinoff chapter. The audit report at `tests/fixtures/audit-report-example.md` does not flag the foreshadowing leakage. Information that the parent novel deliberately keeps as unexplained fragments (per the parent summaries' fragment-scattering strategy for hook-ch1-003) is asserted directly in the spinoff chapter — collapsing the parent's foreshadowing plan across the shared timeline.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: collector dialogue | Foreshadowing leakage — spinoff chapter asserts the hidden authority behind "上面定的规矩" as common knowledge, while the parent summaries (hook-ch1-003) keep the same hint as deliberately scattered fragments; the audit does not flag the plan collapse | error |

## Agent Task
Run shenbi-review-spinoff audit on the spinoff chapter. Find the planted defect where information the parent novel deliberately withholds as fragments leaks into the spinoff as direct assertion.
