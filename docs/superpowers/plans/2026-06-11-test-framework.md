# Shenbi Test Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full three-tier test, log, and analysis framework for Shenbi's 59 novel-writing skills, enabling iterative skill improvement through testing, scoring, and model cycling.

**Architecture:** Markdown-based test cases (inputs, expected outputs, rubrics) organized in a three-tier directory structure. A Python scoring script reads test outputs and rubrics to produce 0-100 scores. Round directories capture test reports, novel output, skill traces, and summary JSON. The existing test files in `tests/` (pressure-tests, skill-behavior, skill-triggering) are migrated into the new T1 structure.

**Tech Stack:** Markdown for test cases and rubrics; Python 3 for scoring/summary tooling; shell scripts for round execution protocol; git for version control of test artifacts.

**Design Spec:** `docs/specs/2026-06-11-test-plan-design.md`

**Note:** This plan covers infrastructure + T1 scaffolding + T2/T3 structure. Creating detailed test content for all 177 test cases is out of scope — each skill batch gets scaffolded rubrics and at least one test case; the rest are filled during iterative rounds.

---

## File Structure

```
tests/
├── tiers/
│   ├── t1-skill/
│   │   ├── _template/                          # Task 1
│   │   ├── using-shenbi/                       # Task 4
│   │   ├── shenbi-worldbuilding/               # Task 5
│   │   ├── shenbi-character-design/            # Task 6
│   │   ├── shenbi-story-architecture/          # Task 7
│   │   ├── shenbi-power-system/                # Task 8
│   │   ├── shenbi-faction-builder/             # Task 9
│   │   ├── shenbi-location-builder/            # Task 10
│   │   ├── shenbi-relationship-map/            # Task 11
│   │   ├── shenbi-pacing-design/               # Task 12
│   │   ├── shenbi-plot-thread-weaver/          # Task 13
│   │   ├── shenbi-genre-config/                # Task 14
│   │   ├── shenbi-volume-outlining/            # Task 15
│   │   ├── shenbi-chapter-planning/            # Task 16
│   │   ├── shenbi-foreshadowing-plant/         # Task 17
│   │   ├── shenbi-foreshadowing-track/         # Task 18
│   │   ├── shenbi-foreshadowing-resolve/       # Task 19
│   │   ├── shenbi-context-composing/           # Task 20
│   │   ├── shenbi-chapter-drafting/            # Task 21
│   │   ├── shenbi-style-polishing/             # Task 22
│   │   ├── shenbi-anti-detect/                 # Task 23
│   │   ├── shenbi-length-normalizing/          # Task 24
│   │   ├── shenbi-style-learning/              # Task 25
│   │   ├── shenbi-writing-skills/              # Task 26
│   │   ├── shenbi-review-character/            # Task 27
│   │   ├── shenbi-review-continuity/           # Task 28
│   │   ├── shenbi-review-dialogue/             # Task 29
│   │   ├── shenbi-review-pacing/               # Task 30
│   │   ├── shenbi-review-anti-ai/              # Task 31
│   │   ├── shenbi-review-foreshadowing/        # Task 32
│   │   ├── shenbi-review-world-rules/          # Task 33
│   │   ├── shenbi-review-sensitivity/          # Task 34
│   │   ├── shenbi-review-memo-compliance/      # Task 35
│   │   ├── shenbi-review-motivation/           # Task 36
│   │   ├── shenbi-review-pov/                  # Task 37
│   │   ├── shenbi-review-reader-pull/          # Task 38
│   │   ├── shenbi-review-highpoint/            # Task 39
│   │   ├── shenbi-review-texture/              # Task 40
│   │   ├── shenbi-review-long-span/            # Task 41
│   │   ├── shenbi-review-era/                  # Task 42
│   │   ├── shenbi-review-fanfic/               # Task 43
│   │   ├── shenbi-review-spinoff/              # Task 44
│   │   ├── shenbi-chapter-revision/            # Task 45
│   │   ├── shenbi-state-settling/              # Task 46
│   │   ├── shenbi-truth-sync/                  # Task 47
│   │   ├── shenbi-snapshot-manage/             # Task 48
│   │   ├── shenbi-volume-consolidation/        # Task 49
│   │   ├── shenbi-foundation-review/           # Task 50
│   │   ├── shenbi-drift-guidance/              # Task 51
│   │   ├── shenbi-intent-management/           # Task 52
│   │   ├── shenbi-chapter-pattern/             # Task 53
│   │   ├── shenbi-import-analysis/             # Task 54
│   │   ├── shenbi-character-extraction/        # Task 55
│   │   ├── shenbi-world-extraction/            # Task 56
│   │   ├── shenbi-canon-import/                # Task 57
│   │   ├── shenbi-short-outline/               # Task 58
│   │   ├── shenbi-short-drafting/              # Task 59
│   │   ├── shenbi-short-packaging/             # Task 60
│   │   ├── shenbi-sequel-writing/              # Task 61
│   │   └── shenbi-market-radar/                # Task 62
│   ├── t2-phase/                               # Task 63
│   └── t3-pipeline/                            # Task 64
├── rounds/                                     # Task 65
├── fixtures/                                   # Task 2
└── scoring.py                                  # Task 3
```

---

### Task 1: Create directory structure and template

**Files:**
- Create: `tests/tiers/t1-skill/_template/bug-hunt/rubric.md`
- Create: `tests/tiers/t1-skill/_template/bug-hunt/input/scenario.md`
- Create: `tests/tiers/t1-skill/_template/bug-hunt/expected/expected-output.md`
- Create: `tests/tiers/t1-skill/_template/clean/rubric.md`
- Create: `tests/tiers/t1-skill/_template/clean/input/scenario.md`
- Create: `tests/tiers/t1-skill/_template/clean/expected/expected-output.md`
- Create: `tests/tiers/t1-skill/_template/generative/rubric.md`
- Create: `tests/tiers/t1-skill/_template/generative/input/scenario.md`

- [ ] **Step 1: Create the full directory tree**

```bash
mkdir -p tests/tiers/t1-skill/_template/{bug-hunt,clean,generative}/{input,expected}
```

- [ ] **Step 2: Write bug-hunt template rubric**

Create `tests/tiers/t1-skill/_template/bug-hunt/rubric.md`:

```markdown
# T1 Bug-Hunt Rubric: <skill-name>

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Kill Switch
- Missed planted defect → total score = 0

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | [dimension from spec] | [weight]% | [standard from spec] |
| ... | ... | ... | ... |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
```

- [ ] **Step 3: Write clean template rubric**

Create `tests/tiers/t1-skill/_template/clean/rubric.md`:

```markdown
# T1 Clean Rubric: <skill-name>

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Kill Switch
- Any hallucinated defect → total score = 0

## Bespoke Dimensions (85%)

[Same bespoke dimensions as bug-hunt for this skill]

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
```

- [ ] **Step 4: Write generative template rubric**

Create `tests/tiers/t1-skill/_template/generative/rubric.md`:

```markdown
# T1 Generative Rubric: <skill-name>

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

[Same bespoke dimensions as bug-hunt for this skill]

## Note
Prose/narrative quality dimensions apply to generative tests only (not bug-hunt/clean).

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
```

- [ ] **Step 5: Write bug-hunt input template**

Create `tests/tiers/t1-skill/_template/bug-hunt/input/scenario.md`:

```markdown
# Bug-Hunt Test: <skill-name>

## Skill Under Test
`skills/<skill-name>/SKILL.md`

## Test Setup
Describe the novel project state before the test. List all files the skill reads.

## Scenario
Describe the test scenario with a planted defect. The defect must be:
- Specific: a single identifiable issue
- Detectable: the skill's instructions, if followed, will catch it
- Severity-classified: state whether it should be reported as error or warning

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| [file:paragraph] | [description of the bug] | error/warning |

## Agent Task
Describe what the agent should do (e.g., "run shenbi-review-character on chapter 11").
```

- [ ] **Step 6: Write bug-hunt expected output template**

Create `tests/tiers/t1-skill/_template/bug-hunt/expected/expected-output.md`:

```markdown
# Expected Output: <skill-name> Bug-Hunt

## Expected Findings

The agent MUST detect the following:

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | [description matching planted defect] | error/warning | [file:paragraph] |

## Expected Non-Findings

The agent MUST NOT report:
- [List aspects that are correct and should not be flagged]

## Expected Output Structure
- [List required output sections per the skill's SKILL.md]
```

- [ ] **Step 7: Write clean input template**

Create `tests/tiers/t1-skill/_template/clean/input/scenario.md`:

```markdown
# Clean Test: <skill-name>

## Skill Under Test
`skills/<skill-name>/SKILL.md`

## Test Setup
Describe the novel project state. All content is correct — no defects.

## Scenario
A scenario with no planted defects. All content adheres to truth files and skill rules.

## Agent Task
Describe what the agent should do. Expected result: report zero issues.
```

- [ ] **Step 8: Write clean expected output template**

Create `tests/tiers/t1-skill/_template/clean/expected/expected-output.md`:

```markdown
# Expected Output: <skill-name> Clean

## Expected Findings

The agent MUST report zero issues. The input contains no defects.

## Expected Output Structure
- [List required output sections per the skill's SKILL.md]
```

- [ ] **Step 9: Write generative input template**

Create `tests/tiers/t1-skill/_template/generative/input/scenario.md`:

```markdown
# Generative Test: <skill-name>

## Skill Under Test
`skills/<skill-name>/SKILL.md`

## Test Setup
Describe the seed input and project state.

## Agent Task
Describe what the agent should produce (e.g., "create worldbuilding files for the novel described in the seed outline").

## Seed Input
[path to seed file or inline content]
```

- [ ] **Step 10: Commit**

```bash
git add tests/tiers/t1-skill/_template/
git commit -m "feat: add T1 test case templates for bug-hunt, clean, and generative tests"
```

---

### Task 2: Prepare test fixtures

**Files:**
- Create: `tests/fixtures/outline-example.md`
- Create: `tests/fixtures/report-example.txt`

- [ ] **Step 1: Copy and prepare outline fixture**

```bash
mkdir -p tests/fixtures
cp outline-example.md tests/fixtures/outline-example.md
```

- [ ] **Step 2: Convert and prepare report fixture**

```bash
iconv -f GB18030 -t UTF-8 report-example.txt > tests/fixtures/report-example.txt
```

- [ ] **Step 3: Verify fixtures**

```bash
wc -l tests/fixtures/outline-example.md tests/fixtures/report-example.txt
```

Expected: outline ~93 lines, report ~9752 lines, both readable UTF-8.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/
git commit -m "feat: add test fixtures from outline-example and report-example"
```

---

### Task 3: Create scoring script

**Files:**
- Create: `tests/scoring.py`

- [ ] **Step 1: Write the scoring script**

Create `tests/scoring.py`:

```python
#!/usr/bin/env python3
"""Score a test report against its rubric. Output structured JSON."""

import json
import sys
import os
import re
from pathlib import Path


def load_rubric(rubric_path):
    """Parse rubric.md to extract dimensions with weights."""
    dimensions = []
    in_table = False
    with open(rubric_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("| #") or stripped.startswith("|---"):
                in_table = True
                continue
            if in_table and stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if len(cells) >= 3 and cells[0].isdigit():
                    dimensions.append({
                        "num": int(cells[0]),
                        "name": cells[1],
                        "weight": int(cells[2].rstrip("%")),
                    })
            elif in_table and not stripped.startswith("|"):
                in_table = False
    return dimensions


def compute_score(dimensions, scores):
    """Compute weighted score from dimension scores."""
    total_weight = sum(d["weight"] for d in dimensions)
    weighted_sum = sum(
        scores.get(d["num"], 0) * d["weight"] for d in dimensions
    )
    if total_weight == 0:
        return 0
    return round(weighted_sum / total_weight, 2)


def classify(score):
    if score >= 90:
        return "PASS (excellent)"
    elif score >= 75:
        return "PASS (acceptable)"
    elif score >= 60:
        return "CONDITIONAL"
    else:
        return "FAIL"


def main():
    if len(sys.argv) < 3:
        print("Usage: scoring.py <rubric.md> <scores.json>")
        print("  scores.json format: {\"1\": 100, \"2\": 95, \"3\": 80, ...}")
        print("  Or: scoring.py <rubric.md> --interactive")
        sys.exit(1)

    rubric_path = sys.argv[1]
    dimensions = load_rubric(rubric_path)

    if sys.argv[2] == "--interactive":
        scores = {}
        print(f"Scoring: {rubric_path}")
        print(f"Found {len(dimensions)} dimensions\n")
        for d in dimensions:
            while True:
                try:
                    val = input(f"  {d['num']}. {d['name']} [{d['weight']}%] (0-100): ")
                    val = int(val)
                    if 0 <= val <= 100:
                        scores[d["num"]] = val
                        break
                    print("    Must be 0-100")
                except ValueError:
                    print("    Enter a number")
    else:
        with open(sys.argv[2]) as f:
            scores = {int(k): v for k, v in json.load(f).items()}

    final = compute_score(dimensions, scores)
    result = {
        "dimensions": [
            {"num": d["num"], "name": d["name"], "weight": d["weight"],
             "score": scores.get(d["num"], 0)}
            for d in dimensions
        ],
        "final_score": final,
        "classification": classify(final),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the scoring script against template rubric**

```bash
echo '{"1": 100, "2": 90, "3": 80, "4": 95, "5": 100}' > /tmp/test-scores.json
python3 tests/scoring.py tests/tiers/t1-skill/_template/bug-hunt/rubric.md /tmp/test-scores.json
```

Expected: JSON output with dimension scores and final_score.

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x tests/scoring.py
git add tests/scoring.py
git commit -m "feat: add scoring script for rubric-based test evaluation"
```

---

### Task 4: Create using-shenbi test cases

This task establishes the pattern for all subsequent skill tasks. Each skill gets bug-hunt, clean, and generative directories with rubric and test inputs.

**Files:**
- Create: `tests/tiers/t1-skill/using-shenbi/rubric.md`
- Create: `tests/tiers/t1-skill/using-shenbi/bug-hunt/input/scenario.md`
- Create: `tests/tiers/t1-skill/using-shenbi/bug-hunt/expected/expected-output.md`
- Create: `tests/tiers/t1-skill/using-shenbi/clean/input/scenario.md`
- Create: `tests/tiers/t1-skill/using-shenbi/clean/expected/expected-output.md`
- Create: `tests/tiers/t1-skill/using-shenbi/generative/input/scenario.md`

- [ ] **Step 1: Migrate existing trigger tests**

Copy the existing trigger test prompts from `tests/skill-triggering/prompts/` into the bug-hunt format:

```bash
mkdir -p tests/tiers/t1-skill/using-shenbi/{bug-hunt,clean,generative}/{input,expected}
```

- [ ] **Step 2: Write rubric for using-shenbi**

Create `tests/tiers/t1-skill/using-shenbi/rubric.md`:

```markdown
# T1 Rubric: using-shenbi

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Kill Switch
- 3+ wrong route in a single round → total score = 0
- Allowing HARD-GATE bypass → total score = 0

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Trigger accuracy | 25% | Routes to correct skill per trigger map; wrong route = 0 per instance |
| 4 | 1% rule compliance | 20% | For borderline requests, checks all applicable skills before responding |
| 5 | HARD-GATE enforcement | 20% | Rejects proceeding without prerequisite |
| 6 | Full skill list coverage | 10% | Can route to all 59 skills |
| 7 | Red flag detection | 10% | Detects and flags red-flag conditions |

## Scoring Rules
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
```

- [ ] **Step 3: Write bug-hunt scenario — wrong route**

Create `tests/tiers/t1-skill/using-shenbi/bug-hunt/input/scenario.md`:

```markdown
# Bug-Hunt Test: using-shenbi

## Skill Under Test
`skills/using-shenbi/SKILL.md`

## Test Setup
No novel project needed. Agent is fresh.

## Scenario
Present 10 natural language requests from the existing trigger test prompts in `tests/skill-triggering/prompts/`. Three of them are deliberately ambiguous — the request could match two skills, and the wrong one is more obvious.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Request 3 | "帮我看看角色" — agent routes to shenbi-character-design instead of shenbi-review-character | error |
| Request 7 | "检查时间线" — agent routes to shenbi-world-rules instead of shenbi-review-continuity | error |
| Request 9 | "润色" — agent skips checking anti-detect and goes straight to polishing | warning |

## Agent Task
Process each request through the using-shenbi skill-check flow.
```

- [ ] **Step 4: Write bug-hunt expected output**

Create `tests/tiers/t1-skill/using-shenbi/bug-hunt/expected/expected-output.md`:

```markdown
# Expected Output: using-shenbi Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| 1 | Request 3 misrouted to character-design instead of review-character | error | Trigger map says "看看角色" → review, not design |
| 2 | Request 7 misrouted to world-rules instead of review-continuity | error | "时间线" keywords match continuity audit |
| 3 | Request 9 skipped anti-detect check before polishing | warning | 1% rule requires checking all applicable skills |

## Expected Output Structure
- Each request shows the skill-check flow
- Route decisions are explicit
- 1% rule is documented for borderline cases
```

- [ ] **Step 5: Write clean scenario**

Create `tests/tiers/t1-skill/using-shenbi/clean/input/scenario.md`:

```markdown
# Clean Test: using-shenbi

## Skill Under Test
`skills/using-shenbi/SKILL.md`

## Test Setup
No novel project. Agent is fresh.

## Scenario
Present 10 natural language requests with clear, unambiguous skill triggers from the trigger map. All should route correctly.

## Agent Task
Process each request through the using-shenbi skill-check flow.
```

- [ ] **Step 6: Write clean expected output**

Create `tests/tiers/t1-skill/using-shenbi/clean/expected/expected-output.md`:

```markdown
# Expected Output: using-shenbi Clean

## Expected Findings
Zero issues. All 10 requests route to the correct skill per the trigger map.
```

- [ ] **Step 7: Write generative scenario**

Create `tests/tiers/t1-skill/using-shenbi/generative/input/scenario.md`:

```markdown
# Generative Test: using-shenbi

## Skill Under Test
`skills/using-shenbi/SKILL.md`

## Test Setup
A novel project exists with `novel.json`, `genre-config.json`, world/, characters/, truth/, and 5 chapters.

## Agent Task
Handle 20 diverse requests covering: novel creation, chapter writing, auditing, revision, management, import, short stories, market research, and borderline cases. The agent must apply the 1% rule, HARD-GATEs, and red flag detection.

## Seed Input
Full novel project state is described inline.
```

- [ ] **Step 8: Commit**

```bash
git add tests/tiers/t1-skill/using-shenbi/
git commit -m "feat: add T1 test cases for using-shenbi dispatcher skill"
```

---

### Tasks 5-62: Create T1 test cases for remaining skills

Each task follows the same pattern as Task 4. For each of the 58 remaining skills:

1. Create directory: `tests/tiers/t1-skill/<skill-name>/{bug-hunt,clean,generative}/{input,expected}`
2. Write `rubric.md` with dimensions from the spec Section 4
3. Write bug-hunt `input/scenario.md` and `expected/expected-output.md`
4. Write clean `input/scenario.md` and `expected/expected-output.md`
5. Write generative `input/scenario.md`
6. Commit

**Rubric content comes directly from the spec** — each skill's dimensions are defined in `docs/specs/2026-06-11-test-plan-design.md` Section 4.

**Existing test migration:** Many skills already have test content in `tests/skill-behavior/` and `tests/skill-triggering/`. These should be adapted into the new format:

| Existing test file | Maps to |
|---|---|
| `tests/skill-behavior/review-catches-bug/phase2-character-bug.md` | `t1-skill/shenbi-review-character/bug-hunt/` |
| `tests/skill-behavior/review-catches-bug/phase2-continuity-bug.md` | `t1-skill/shenbi-review-continuity/bug-hunt/` |
| `tests/skill-behavior/review-catches-bug/phase2-foreshadowing-bug.md` | `t1-skill/shenbi-review-foreshadowing/bug-hunt/` |
| `tests/skill-behavior/review-catches-bug/phase2-pacing-bug.md` | `t1-skill/shenbi-review-pacing/bug-hunt/` |
| `tests/skill-behavior/review-catches-bug/phase4-dialogue-bug.md` | `t1-skill/shenbi-review-dialogue/bug-hunt/` |
| `tests/skill-behavior/review-catches-bug/phase4-memo-compliance-bug.md` | `t1-skill/shenbi-review-memo-compliance/bug-hunt/` |
| `tests/skill-behavior/review-catches-bug/phase4-reader-pull-bug.md` | `t1-skill/shenbi-review-reader-pull/bug-hunt/` |
| `tests/skill-behavior/review-catches-bug/phase4b-*.md` (11 files) | Corresponding `t1-skill/shenbi-review-*/bug-hunt/` |
| `tests/skill-behavior/revision-fixes-issue/*.md` (2 files) | `t1-skill/shenbi-chapter-revision/bug-hunt/` |
| `tests/skill-triggering/prompts/phase2-*-trigger.md` (4 files) | `t1-skill/<target-skill>/bug-hunt/` trigger portion |
| `tests/pressure-tests/prompts/*.md` (2 files) | `t1-skill/shenbi-review-anti-ai/bug-hunt/` and `t1-skill/shenbi-chapter-drafting/bug-hunt/` |

**Batching recommendation:** Group by category for parallel subagent execution:
- Batch A: Genesis skills (Tasks 5-14, 10 skills)
- Batch B: Planning skills (Tasks 15-20, 6 skills)
- Batch C: Drafting + polishing skills (Tasks 21-26, 6 skills)
- Batch D: Audit skills (Tasks 27-44, 18 skills) — largest batch, highest value
- Batch E: Revision + state management (Tasks 45-53, 9 skills)
- Batch F: Import + short story + special (Tasks 54-62, 9 skills)

**Rubric generation is mechanical** — each rubric.md copies the skill's dimensions from the spec Section 4 verbatim into the template from Task 1. No creativity needed.

---

### Task 63: Create T2 phase test structure

**Files:**
- Create: `tests/tiers/t2-phase/genesis/rubric.md`
- Create: `tests/tiers/t2-phase/genesis/input/seed.md`
- Create: `tests/tiers/t2-phase/genesis/expected/expected-outputs.md`
- Create: `tests/tiers/t2-phase/architecture/rubric.md`
- Create: `tests/tiers/t2-phase/planning/rubric.md`
- Create: `tests/tiers/t2-phase/drafting/rubric.md`
- Create: `tests/tiers/t2-phase/audit/rubric.md`
- Create: `tests/tiers/t2-phase/management/rubric.md`
- Create: `tests/tiers/t2-phase/import/rubric.md`
- Create: `tests/tiers/t2-phase/foundation/rubric.md`
- Create: `tests/tiers/t2-phase/short-story/rubric.md`

- [ ] **Step 1: Create T2 directories**

```bash
for phase in genesis architecture planning drafting audit management import foundation short-story; do
  mkdir -p tests/tiers/t2-phase/$phase/{input,expected}
done
```

- [ ] **Step 2: Write genesis phase rubric**

Create `tests/tiers/t2-phase/genesis/rubric.md` using the T2 Sequential dimensions from spec Section 5.1:

```markdown
# T2 Phase Rubric: Genesis

Phase: worldbuilding → power-system → faction-builder → location-builder → character-design → relationship-map
Seed: tests/fixtures/outline-example.md

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Handoff integrity | 20% | Every skill receives correctly structured input from previous skill; missing fields = -5% per field |
| 2 | Cross-skill consistency | 20% | Zero contradictions between outputs of different skills (e.g., character-design doesn't violate worldbuilding rules) |
| 3 | State propagation accuracy | 15% | Truth files updated by skill N correctly read by skill N+1; stale reads = -10% per instance |
| 4 | Phase output completeness | 15% | All files expected at phase end present and non-empty |
| 5 | Regression within phase | 15% | No skill's output during T2 scores below its T1 score on same input |
| 6 | Execution time | 5% | No single skill exceeds 10 minutes; total phase under 60 minutes |
| 7 | Human gate compliance | 10% | Every hard-gate pause respected |

## Kill Switch
Any skill's output scores below its T1 score on same input → phase = 0.

## Expected Output Files
- novel.json
- genre-config.json
- world/story_bible.md
- world/rules.md
- world/locations.md
- world/power_system.md
- world/factions.md
- characters/protagonist.md
- characters/relationships.md
- truth/ (all templates)
```

- [ ] **Step 3: Write audit phase rubric (parallel)**

Create `tests/tiers/t2-phase/audit/rubric.md` using the T2 Audit dimensions from spec Section 5.2:

```markdown
# T2 Phase Rubric: Audit

Phase: All 18 review-* skills run on the same drafted chapter
Input: Output from Drafting phase

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Cross-audit consistency | 25% | Findings from different audits don't contradict each other |
| 2 | Full coverage | 20% | All 18 audit skills produce reports; none skipped |
| 3 | Finding deduplication | 15% | Same issue not reported at different severities without justification |
| 4 | Severity alignment | 15% | Cross-referenced findings explained |
| 5 | Phase output completeness | 15% | All 18 audit reports present and non-empty |
| 6 | Execution time | 10% | No single audit exceeds 10 minutes; total under 30 minutes |

## Kill Switch
Any audit skill's report scores below its T1 score on same chapter → phase = 0.
```

- [ ] **Step 4: Write remaining phase rubrics**

For each remaining phase, create `rubric.md` by copying the dimension table from the spec:
- Architecture, Planning, Drafting, Management, Import, Foundation: use T2 Sequential dimensions (spec Section 5.1). List the phase's skill chain and expected output files.
- Short-story: use T2 Short story dimensions (spec Section 5.3). List the phase's skill chain and expected output files.

- [ ] **Step 5: Create genesis seed input**

Create `tests/tiers/t2-phase/genesis/input/seed.md`:

```markdown
# Genesis Phase Seed

Use `tests/fixtures/outline-example.md` as the seed outline.

Agent instructions:
1. Run shenbi-worldbuilding with the outline as input. Approve the output.
2. Run shenbi-power-system with worldbuilding output. Approve.
3. Run shenbi-faction-builder with worldbuilding output. Approve.
4. Run shenbi-location-builder with worldbuilding output. Approve.
5. Run shenbi-character-design with all previous output. Approve.
6. Run shenbi-relationship-map with all previous output. Approve.

After each skill, verify handoff integrity: does the next skill find all required input files?
```

- [ ] **Step 6: Create import seed input**

Create `tests/tiers/t2-phase/import/input/seed.md`:

```markdown
# Import Phase Seed

Use `tests/fixtures/report-example.txt` (UTF-8) as the source novel.

Agent instructions:
1. Run shenbi-import-analysis on the full text.
2. Run shenbi-character-extraction with analysis output.
3. Run shenbi-world-extraction with analysis output.
4. Run shenbi-canon-import with analysis output.

After each skill, verify handoff integrity.
```

- [ ] **Step 7: Commit**

```bash
git add tests/tiers/t2-phase/
git commit -m "feat: add T2 phase test structure with rubrics for all 9 phases"
```

---

### Task 64: Create T3 pipeline test structure

**Files:**
- Create: `tests/tiers/t3-pipeline/long-form/rubric.md`
- Create: `tests/tiers/t3-pipeline/long-form/input/seed.md`
- Create: `tests/tiers/t3-pipeline/short-form/rubric.md`
- Create: `tests/tiers/t3-pipeline/short-form/input/seed.md`
- Create: `tests/tiers/t3-pipeline/import-form/rubric.md`
- Create: `tests/tiers/t3-pipeline/import-form/input/seed.md`

- [ ] **Step 1: Create T3 directories**

```bash
for variant in long-form short-form import-form; do
  mkdir -p tests/tiers/t3-pipeline/$variant/{input,expected}
done
```

- [ ] **Step 2: Write long-form rubric**

Create `tests/tiers/t3-pipeline/long-form/rubric.md` with the 9 T3 universal dimensions from spec Section 6.1.

- [ ] **Step 3: Write short-form rubric**

Create `tests/tiers/t3-pipeline/short-form/rubric.md` with the 5 dimension replacements from spec Section 6.2 (short-form variant).

- [ ] **Step 4: Write import-form rubric**

Create `tests/tiers/t3-pipeline/import-form/rubric.md` with the 5 dimension replacements from spec Section 6.2 (import-form variant).

- [ ] **Step 5: Write pipeline seed inputs**

For long-form: seed references `tests/fixtures/outline-example.md` with instructions to run full pipeline (genesis → architecture → planning → drafting 5 chapters → audit → revision → state-settling → management).

For short-form: seed references `tests/fixtures/outline-example.md` with instructions to run short-outline → short-drafting → short-packaging.

For import-form: seed references `tests/fixtures/report-example.txt` with instructions to run import-analysis → character-extraction → world-extraction → canon-import.

- [ ] **Step 6: Commit**

```bash
git add tests/tiers/t3-pipeline/
git commit -m "feat: add T3 pipeline test structure with rubrics for all 3 variants"
```

---

### Task 65: Create round execution infrastructure

**Files:**
- Create: `tests/rounds/CHANGELOG.md`
- Create: `tests/rounds/round-000-TEMPLATE/`
- Create: `tests/round-exec.sh`

- [ ] **Step 1: Create rounds directory and CHANGELOG**

```bash
mkdir -p tests/rounds
```

Create `tests/rounds/CHANGELOG.md`:

```markdown
# Test Round Changelog

All rounds are logged here. Each entry records the model, tier, scores, and fixes applied.

## Format
- T1 band breakdown: PASS (90+), CONDITIONAL (60-74), FAIL (0-59)
- Fixes are SKILL.md changes with file references
```

- [ ] **Step 2: Create round template directory**

```bash
mkdir -p tests/rounds/round-000-TEMPLATE/{t1-reports,t2-reports,t3-reports,novel-output,skill-traces}
```

Create `tests/rounds/round-000-TEMPLATE/meta.json`:

```json
{
  "round": "000",
  "date": "",
  "model": "",
  "tier_target": "T1",
  "skill_versions": {},
  "notes": "Template — copy to start a new round"
}
```

Create `tests/rounds/round-000-TEMPLATE/summary.json`:

```json
{
  "round": "000",
  "model": "",
  "tier_target": "T1",
  "t1_scores": {},
  "t2_scores": {},
  "t3_scores": {},
  "kill_switches": [],
  "enhancement_signals": [],
  "band_breakdown": {
    "pass": 0,
    "conditional": 0,
    "fail": 0
  },
  "next_actions": []
}
```

Create `tests/rounds/round-000-TEMPLATE/enhancement-signals.json`:

```json
{
  "signals": []
}
```

- [ ] **Step 3: Write round execution script**

Create `tests/round-exec.sh`:

```bash
#!/bin/bash
# Execute a test round. Usage: ./round-exec.sh <model> <tier>
# Example: ./round-exec.sh claude T1

set -euo pipefail

MODEL="${1:?Usage: round-exec.sh <model> <tier>}"
TIER="${2:?Specify T1, T2, or T3}"
DATE=$(date +%Y-%m-%d)
ROUND_DIR=""

# Find next round number
LAST=$(ls -d tests/rounds/round-* 2>/dev/null | grep -v TEMPLATE | sort -V | tail -1)
if [ -z "$LAST" ]; then
  NUM=1
else
  NUM=$(($(basename "$LAST" | grep -o '^[0-9]*') + 1))
fi
ROUND_NUM=$(printf "%03d" $NUM)
ROUND_DIR="tests/rounds/round-${ROUND_NUM}-${DATE}"

echo "=== Creating round ${ROUND_NUM}: ${MODEL} / ${TIER} ==="

# Copy template
cp -r tests/rounds/round-000-TEMPLATE "$ROUND_DIR"

# Fill meta
cat > "${ROUND_DIR}/meta.json" << EOF
{
  "round": "${ROUND_NUM}",
  "date": "${DATE}",
  "model": "${MODEL}",
  "tier_target": "${TIER}",
  "skill_versions": {},
  "notes": ""
}
EOF

echo "Round directory: ${ROUND_DIR}"
echo "Next steps:"
echo "  1. Run ${TIER} tests (manual or automated)"
echo "  2. Place reports in ${ROUND_DIR}/${TIER,,}-reports/"
echo "  3. Score reports with: python3 tests/scoring.py <rubric> <scores>"
echo "  4. Fill summary.json"
echo "  5. Update CHANGELOG.md"
```

- [ ] **Step 4: Make executable and commit**

```bash
chmod +x tests/round-exec.sh
git add tests/rounds/ tests/round-exec.sh
git commit -m "feat: add round execution infrastructure with template and init script"
```

---

### Task 66: Migrate existing tests into new structure

**Files:**
- Modify: existing `tests/skill-behavior/` files → adapted into `tests/tiers/t1-skill/`
- Modify: existing `tests/skill-triggering/` files → adapted into `tests/tiers/t1-skill/`
- Modify: existing `tests/pressure-tests/` files → adapted into `tests/tiers/t1-skill/`

- [ ] **Step 1: Migrate skill-behavior bug-hunt tests**

For each file in `tests/skill-behavior/review-catches-bug/`, copy the test content into the corresponding `t1-skill/shenbi-review-*/bug-hunt/input/scenario.md`. Extract the planted bug details into `expected/expected-output.md`.

Example for `phase2-character-bug.md`:

```bash
# Copy content and adapt format
cp tests/skill-behavior/review-catches-bug/phase2-character-bug.md \
   tests/tiers/t1-skill/shenbi-review-character/bug-hunt/input/scenario.md
```

Then manually edit to add the scenario header template and extract expected output.

- [ ] **Step 2: Migrate skill-triggering tests**

For each trigger prompt, adapt into a bug-hunt scenario where the "bug" is routing to the wrong skill:

```bash
# The trigger tests test correct routing — these become clean tests
# Create corresponding bug-hunt versions with deliberate misrouting scenarios
```

- [ ] **Step 3: Migrate pressure tests**

Adapt the pressure tests into bug-hunt scenarios:

```bash
# pressure-test "audit-skip" → shenbi-review-anti-ai bug-hunt (agent tries to skip audit)
# pressure-test "chapter-writing" → shenbi-chapter-drafting bug-hunt (agent skips PRE_WRITE_CHECK)
```

- [ ] **Step 4: Commit**

```bash
git add tests/tiers/t1-skill/
git commit -m "feat: migrate existing tests into new T1 structure"
```

---

### Task 67: Self-review and commit

- [ ] **Step 1: Verify directory structure**

```bash
find tests/tiers -type d | sort
```

Expected: all 59 skill directories under t1-skill, 9 phase directories under t2-phase, 3 variant directories under t3-pipeline.

- [ ] **Step 2: Verify all rubrics exist**

```bash
find tests/tiers -name "rubric.md" | wc -l
```

Expected: 59 (T1 skills) + 9 (T2 phases) + 3 (T3 variants) = 71 rubric files.

- [ ] **Step 3: Verify fixtures**

```bash
file tests/fixtures/outline-example.md tests/fixtures/report-example.txt
```

Expected: both UTF-8 text.

- [ ] **Step 4: Verify scoring script**

```bash
python3 tests/scoring.py tests/tiers/t1-skill/using-shenbi/rubric.md --interactive <<< "100
100
100
100
100
100
"
```

Expected: JSON output with score.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete Shenbi test framework infrastructure"
```
