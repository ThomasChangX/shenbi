# Bug-Hunt Test: shenbi-review-spinoff

## Skill Under Test
`skills/shenbi-review-spinoff/SKILL.md`

## Test Setup
A spinoff novel project exists alongside a parent novel. The parent novel's chapter summaries at `truth/parent_chapter_summaries.md` record all events. In the parent novel, the secret that "the mastermind is actually the protagonist's father" is revealed in parent chapter 7. The spinoff novel's chapter 3 at `drafts/spinoff-chapter-3.md` contains a reference to this secret: in paragraph 5, the spinoff character says "我们都知道幕后黑手其实就是他父亲。" (We all know the mastermind is actually his father.)

## Scenario
The agent runs a spinoff audit on spinoff chapter 3. The audit report at `audit/spinoff-review-ch3.md` does not flag the timeline leakage. Information that was only revealed in parent chapter 7 appears in spinoff chapter 3 — this is forbidden because spinoff chapter 3 occurs before parent chapter 7 in the shared timeline.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `drafts/spinoff-chapter-3.md`: paragraph 5 | Timeline leakage — spinoff chapter 3 references information (mastermind = father) that was only revealed in parent chapter 7; spinoff ch3 < parent ch7 = forbidden information | error |

## Agent Task
Run shenbi-review-spinoff audit on spinoff chapter 3. Find the planted defect where information from a later parent chapter leaks into an earlier spinoff chapter.
