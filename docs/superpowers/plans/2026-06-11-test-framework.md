# Shenbi Test Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full three-tier test, log, and analysis framework for Shenbi's 59 novel-writing skills, enabling iterative skill improvement through testing, scoring, and model cycling.

**Architecture:** Markdown-based test cases (inputs, expected outputs, rubrics) organized in a three-tier directory structure. A Python scoring script reads test outputs and rubrics to produce 0-100 scores. Round directories capture test reports, novel output, skill traces, and summary JSON. The existing test files in `tests/` (pressure-tests, skill-behavior, skill-triggering) are migrated into the new T1 structure.

**Tech Stack:** Markdown for test cases and rubrics; Python 3 for scoring/summary tooling; shell scripts for round execution protocol; git for version control of test artifacts.

**Design Spec:** `docs/specs/2026-06-11-test-plan-design.md`

**Note:** This plan covers infrastructure + T1 scaffolding + T2/T3 structure. Creating detailed test content for all 177 test cases is out of scope — each skill batch gets scaffolded rubrics and at least one test case; the rest are filled during iterative rounds.

**Conventions:**
- Working directory for all commands: project root (`/Users/xiaotiac/Documents/GitHub/shenbi/`)
- Rubrics live at skill level: `tests/tiers/t1-skill/<skill-name>/rubric.md` (one file per skill, containing all test-type kill switches)
- Generative tests have NO `expected/` directory (per spec Section 2.2)
- All shell commands are macOS-compatible (bash 3.2)

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
- Create: `tests/tiers/t1-skill/_template/rubric.md`
- Create: `tests/tiers/t1-skill/_template/bug-hunt/input/scenario.md`
- Create: `tests/tiers/t1-skill/_template/bug-hunt/expected/expected-output.md`
- Create: `tests/tiers/t1-skill/_template/clean/input/scenario.md`
- Create: `tests/tiers/t1-skill/_template/clean/expected/expected-output.md`
- Create: `tests/tiers/t1-skill/_template/generative/input/scenario.md`

- [ ] **Step 1: Create the full directory tree**

```bash
mkdir -p tests/tiers/t1-skill/_template/{bug-hunt,clean}/{input,expected}
mkdir -p tests/tiers/t1-skill/_template/generative/input
```

- [ ] **Step 2: Write the single skill-level rubric template**

Create `tests/tiers/t1-skill/_template/rubric.md`:

```markdown
# T1 Rubric: <skill-name>

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | [dimension name] | [weight]% | [measurable standard] |
| ... | ... | ... | ... |

(Sum must equal 85%)

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted defect (false negative) → total score = 0
- HARD-GATE violation → total score = 0

### Clean Kill Switches
- Any hallucinated defect (false positive) → total score = 0
- HARD-GATE violation → total score = 0

### Generative Kill Switches
- HARD-GATE violation → total score = 0

## Dimension Applicability by Test Type

| Dimension scope | Bug-hunt | Clean | Generative |
|----------------|----------|-------|------------|
| Universal (1-2) | Yes | Yes | Yes |
| All bespoke | Yes (detection quality) | Yes (report quality) | Yes (output quality) |
| Prose/narrative quality | No | No | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
```

- [ ] **Step 3: Write bug-hunt input template**

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

- [ ] **Step 4: Write bug-hunt expected output template**

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

- [ ] **Step 5: Write clean input template**

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

- [ ] **Step 6: Write clean expected output template**

Create `tests/tiers/t1-skill/_template/clean/expected/expected-output.md`:

```markdown
# Expected Output: <skill-name> Clean

## Expected Findings

The agent MUST report zero issues. The input contains no defects.

## Expected Output Structure
- [List required output sections per the skill's SKILL.md]
```

- [ ] **Step 7: Write generative input template**

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

Note: generative tests have no `expected/` directory (per spec Section 2.2).

- [ ] **Step 8: Commit**

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
from pathlib import Path


def load_rubric(rubric_path):
    """Parse rubric.md to extract dimensions with weights and kill switches."""
    dimensions = []
    kill_switches = []
    in_table = False
    in_kill_switch = False
    with open(rubric_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("## Kill Switches") or stripped.startswith("## Kill Switch"):
                in_kill_switch = True
                in_table = False
                continue
            if stripped.startswith("## ") and in_kill_switch:
                in_kill_switch = False
            if in_kill_switch and "total score = 0" in stripped.lower():
                kill_switches.append(stripped.lstrip("- ").rstrip())
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
    return dimensions, kill_switches


def compute_score(dimensions, scores, kill_switch_triggered=False):
    """Compute weighted score from dimension scores. Kill switch overrides to 0."""
    if kill_switch_triggered:
        return 0
    total_weight = sum(d["weight"] for d in dimensions)
    if total_weight == 0:
        return 0
    weighted_sum = sum(
        scores.get(d["num"], 0) * d["weight"] for d in dimensions
    )
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
        print("Usage: scoring.py <rubric.md> <scores.json> [--kill-switch]")
        print("  scores.json format: {\"1\": 100, \"2\": 95, \"3\": 80, ...}")
        print("  --kill-switch: force final score to 0 (any kill switch triggered)")
        print("  Or: scoring.py <rubric.md> --interactive")
        sys.exit(1)

    rubric_path = sys.argv[1]
    dimensions, kill_switches = load_rubric(rubric_path)

    kill_switch_triggered = "--kill-switch" in sys.argv

    if sys.argv[2] == "--interactive":
        scores = {}
        print(f"Scoring: {rubric_path}")
        print(f"Found {len(dimensions)} dimensions")
        if kill_switches:
            print(f"Kill switches ({len(kill_switches)}):")
            for ks in kill_switches:
                print(f"  - {ks}")
            print()
            ks_input = input("Kill switch triggered? (y/n): ").strip().lower()
            if ks_input == "y":
                kill_switch_triggered = True
        print()
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
                except EOFError:
                    print("\n    Input ended. Using 0 for remaining dimensions.")
                    break
        # Fill any missing dimensions with 0
        for d in dimensions:
            if d["num"] not in scores:
                scores[d["num"]] = 0
    else:
        scores_file = sys.argv[2]
        if scores_file == "--kill-switch":
            scores = {}
        else:
            with open(scores_file) as f:
                scores = {int(k): v for k, v in json.load(f).items()}

    final = compute_score(dimensions, scores, kill_switch_triggered)
    result = {
        "dimensions": [
            {"num": d["num"], "name": d["name"], "weight": d["weight"],
             "score": scores.get(d["num"], 0)}
            for d in dimensions
        ],
        "kill_switch_triggered": kill_switch_triggered,
        "kill_switches": kill_switches,
        "final_score": final,
        "classification": classify(final),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the scoring script against using-shenbi rubric**

After Task 4 is complete, test against the real rubric:

```bash
echo '{"1": 100, "2": 95, "3": 100, "4": 100, "5": 100, "6": 100, "7": 100}' > /tmp/test-scores.json
python3 tests/scoring.py tests/tiers/t1-skill/using-shenbi/rubric.md /tmp/test-scores.json
```

Expected: JSON output with final_score ~99.25, classification "PASS (excellent)".

Then test kill-switch override:

```bash
python3 tests/scoring.py tests/tiers/t1-skill/using-shenbi/rubric.md /tmp/test-scores.json --kill-switch
```

Expected: JSON output with final_score 0, classification "FAIL".

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

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tests/tiers/t1-skill/using-shenbi/{bug-hunt,clean}/{input,expected}
mkdir -p tests/tiers/t1-skill/using-shenbi/generative/input
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

Each task follows this exact pattern. Shown here for **shenbi-worldbuilding** (Task 5) as the canonical example. All subsequent tasks repeat this pattern with the skill's own dimensions from the spec.

#### Task 5 Example: shenbi-worldbuilding

- [ ] **Step 1: Create directories**

```bash
mkdir -p tests/tiers/t1-skill/shenbi-worldbuilding/{bug-hunt,clean}/{input,expected}
mkdir -p tests/tiers/t1-skill/shenbi-worldbuilding/generative/input
```

- [ ] **Step 2: Write rubric.md**

Create `tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md`:

```markdown
# T1 Rubric: shenbi-worldbuilding

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output files/sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Internal consistency | 15% | Zero contradictions within world rules; hard rules are mutually compatible |
| 4 | Prose quality | 10% | story_bible.md is narrative prose paragraphs; bullet-point lists = 0 |
| 5 | Deduplication | 10% | Each fact appears in exactly one canonical file |
| 6 | Hook potential | 15% | "Undercurrent" section seeds ≥3 future conflict sources |
| 7 | Scalability | 15% | Structure supports 200+ chapters without retcon |
| 8 | Rule enforceability | 10% | Hard rules are concrete and testable; "magic is mysterious" = fail |
| 9 | Template completeness | 10% | All required output files present with all required fields |

## Kill Switches by Test Type

### Bug-Hunt
- Missed planted defect → total score = 0
- HARD-GATE violation → total score = 0

### Clean
- Any hallucinated defect → total score = 0
- HARD-GATE violation → total score = 0

### Generative
- HARD-GATE violation → total score = 0

## Dimension Applicability

| Dimension | Bug-hunt | Clean | Generative |
|-----------|----------|-------|------------|
| 1-2 (Universal) | Yes | Yes | Yes |
| 3,5,7-9 | Yes | Yes | Yes |
| 4,6 (Prose/narrative) | No | No | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum
- Kill switch → final = 0
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
```

- [ ] **Step 3: Write bug-hunt input**

Create `tests/tiers/t1-skill/shenbi-worldbuilding/bug-hunt/input/scenario.md`:

```markdown
# Bug-Hunt Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
No project exists. Agent starts fresh.

## Scenario
Using `tests/fixtures/outline-example.md` as input, run shenbi-worldbuilding to create the world.
The output has a planted defect: two hard rules contradict each other.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| world/rules.md rule 1 vs rule 4 | Rule 1 says "灵能无法凭空产生" but rule 4 describes a scenario where灵能 IS created from nothing | error |

## Agent Task
Run shenbi-worldbuilding, then audit the output for internal consistency.
```

- [ ] **Step 4: Write bug-hunt expected output**

Create `tests/tiers/t1-skill/shenbi-worldbuilding/bug-hunt/expected/expected-output.md`:

```markdown
# Expected Output: shenbi-worldbuilding Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Rule 1 contradicts rule 4:灵能守恒 vs 灵能凭空产生 | error | world/rules.md |

## Expected Output Structure
- novel.json with required fields
- genre-config.json with fatigue words and audit dimensions
- world/story_bible.md (narrative prose, 4 sections)
- world/rules.md (up to 10 hard rules)
- world/locations.md (3-5 core locations)
- truth/ directory templates
```

- [ ] **Step 5: Write clean input**

Create `tests/tiers/t1-skill/shenbi-worldbuilding/clean/input/scenario.md`:

```markdown
# Clean Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
A fully correct worldbuilding output exists: novel.json, genre-config.json, world/story_bible.md, world/rules.md, world/locations.md, truth/ templates. All rules are internally consistent. All prose is narrative paragraphs. All locations have atmosphere.

## Agent Task
Run shenbi-worldbuilding quality check on the existing output. Expected: report zero issues.
```

- [ ] **Step 6: Write clean expected output**

Create `tests/tiers/t1-skill/shenbi-worldbuilding/clean/expected/expected-output.md`:

```markdown
# Expected Output: shenbi-worldbuilding Clean

## Expected Findings
Zero issues. The worldbuilding output is internally consistent, uses prose format, and has all required files.
```

- [ ] **Step 7: Write generative input**

Create `tests/tiers/t1-skill/shenbi-worldbuilding/generative/input/scenario.md`:

```markdown
# Generative Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
No project exists. Agent starts fresh.

## Agent Task
Run shenbi-worldbuilding using `tests/fixtures/outline-example.md` as the seed outline. Produce all required output files.

## Seed Input
`tests/fixtures/outline-example.md`
```

- [ ] **Step 8: Commit**

```bash
git add tests/tiers/t1-skill/shenbi-worldbuilding/
git commit -m "feat: add T1 test cases for shenbi-worldbuilding"
```

#### Tasks 6-62: Remaining skills

Each of these tasks follows the exact same pattern as Task 5 above (Steps 1-8), with:
- Directory name matching the skill name
- Rubric dimensions copied verbatim from the corresponding skill section in the design spec `docs/specs/2026-06-11-test-plan-design.md` Section 4
- Bug-hunt, clean, and generative scenarios tailored to the skill's purpose

**Rubric dimensions source** (each skill's section in the spec):

| Task | Skill | Spec Section |
|------|-------|-------------|
| 6 | shenbi-character-design | 4.1 |
| 7 | shenbi-story-architecture | 4.1 |
| 8 | shenbi-power-system | 4.1 |
| 9 | shenbi-faction-builder | 4.1 |
| 10 | shenbi-location-builder | 4.1 |
| 11 | shenbi-relationship-map | 4.1 |
| 12 | shenbi-pacing-design | 4.1 |
| 13 | shenbi-plot-thread-weaver | 4.1 |
| 14 | shenbi-genre-config | 4.1 |
| 15 | shenbi-volume-outlining | 4.1 |
| 16 | shenbi-chapter-planning | 4.2 |
| 17 | shenbi-foreshadowing-plant | 4.2 |
| 18 | shenbi-foreshadowing-track | 4.2 |
| 19 | shenbi-foreshadowing-resolve | 4.2 |
| 20 | shenbi-context-composing | 4.2 |
| 21 | shenbi-chapter-drafting | 4.3 |
| 22 | shenbi-style-polishing | 4.3 |
| 23 | shenbi-anti-detect | 4.3 |
| 24 | shenbi-length-normalizing | 4.3 |
| 25 | shenbi-style-learning | 4.3 |
| 26 | shenbi-writing-skills | 4.9 |
| 27-44 | shenbi-review-* (18 audit skills) | 4.4 (shared + unique) |
| 45 | shenbi-chapter-revision | 4.5 |
| 46 | shenbi-state-settling | 4.6 |
| 47 | shenbi-truth-sync | 4.6 |
| 48 | shenbi-snapshot-manage | 4.6 |
| 49 | shenbi-volume-consolidation | 4.6 |
| 50 | shenbi-foundation-review | 4.6 |
| 51 | shenbi-drift-guidance | 4.6 |
| 52 | shenbi-intent-management | 4.6 |
| 53 | shenbi-chapter-pattern | 4.6 |
| 54 | shenbi-import-analysis | 4.7 |
| 55 | shenbi-character-extraction | 4.7 |
| 56 | shenbi-world-extraction | 4.7 |
| 57 | shenbi-canon-import | 4.7 |
| 58 | shenbi-short-outline | 4.8 |
| 59 | shenbi-short-drafting | 4.8 |
| 60 | shenbi-short-packaging | 4.8 |
| 61 | shenbi-sequel-writing | 4.9 |
| 62 | shenbi-market-radar | 4.9 |

**Execution batching for subagent-driven development:**
- Batch A: Genesis skills (Tasks 5-15, 11 skills)
- Batch B: Planning skills (Tasks 16-20, 5 skills)
- Batch C: Drafting + polishing skills (Tasks 21-26, 6 skills)
- Batch D: Audit skills (Tasks 27-44, 18 skills) — largest batch
- Batch E: Revision + state management (Tasks 45-53, 9 skills)
- Batch F: Import + short story + special (Tasks 54-62, 9 skills)

**Existing test migration** (Task 66) adapts these files as starting bug-hunt inputs:

| Existing test file | Target location |
|---|---|
| `tests/skill-behavior/review-catches-bug/phase2-character-bug.md` | `t1-skill/shenbi-review-character/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase2-continuity-bug.md` | `t1-skill/shenbi-review-continuity/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase2-foreshadowing-bug.md` | `t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase2-pacing-bug.md` | `t1-skill/shenbi-review-pacing/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase4-dialogue-bug.md` | `t1-skill/shenbi-review-dialogue/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase4-memo-compliance-bug.md` | `t1-skill/shenbi-review-memo-compliance/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase4-reader-pull-bug.md` | `t1-skill/shenbi-review-reader-pull/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase4b-*.md` (10 files) | Corresponding `t1-skill/shenbi-review-*/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase3-foreshadowing-lifecycle.md` | `t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase3-plant-track-resolve.md` | `t1-skill/shenbi-foreshadowing-track/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/review-catches-bug/phase3-volume-consolidation.md` | `t1-skill/shenbi-volume-consolidation/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/revision-fixes-issue/phase4b-revision-mode-routing.md` | `t1-skill/shenbi-chapter-revision/bug-hunt/input/scenario.md` |
| `tests/skill-behavior/revision-fixes-issue/phase2-polishing-fix.md` | `t1-skill/shenbi-style-polishing/bug-hunt/input/scenario.md` |
| `tests/skill-triggering/prompts/phase2-*-trigger.md` (4 files) | `t1-skill/using-shenbi/bug-hunt/` (routing scenarios) |
| `tests/skill-triggering/prompts/phase3-*-trigger.md` (4 files) | `t1-skill/using-shenbi/bug-hunt/` (routing scenarios) |
| `tests/pressure-tests/prompts/audit-skip-tendency.md` | `t1-skill/shenbi-review-anti-ai/bug-hunt/input/scenario.md` |
| `tests/pressure-tests/prompts/chapter-writing-flow.md` | `t1-skill/shenbi-chapter-drafting/bug-hunt/input/scenario.md` |

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

Create `tests/tiers/t3-pipeline/long-form/rubric.md`:

```markdown
# T3 Pipeline Rubric: Long-Form

Seed: tests/fixtures/outline-example.md → genesis → architecture → planning → drafting (5+ chapters) → audit → revision → state-settling → management

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | End-to-end data integrity | 15% | Every truth file consistent from genesis through final chapter; zero orphaned or contradictory state entries |
| 2 | Novel output coherence | 15% | All character actions groundable to established motivations; no unexplained plot jumps; chapter transitions reference prior events; all planted foreshadowing traceable in text |
| 3 | Cross-phase state consistency | 15% | Genesis world rules hold through drafting; character arcs from character-design visible in chapters; foreshadowing planted = tracked and resolved or deferred |
| 4 | Audit pass rate | 15% | All chapters pass all activated audit dimensions after revision |
| 5 | Revision non-regression | 10% | Chapter revision fixes audit issues without introducing new ones; pre/post audit scores only improve |
| 6 | Foreshadowing lifecycle completeness | 10% | Every planted hook tracked, advanced, and resolved or explicitly deferred; zero orphaned hooks |
| 7 | Full project file completeness | 5% | All expected files exist: novel.json, genre-config.json, world/*, characters/*, truth/*, chapters/*, outline/* |
| 8 | Literary quality | 10% | Final chapters: zero AI-typical phrasing (per anti-ai audit), chapter openings create pull (per reader-pull), emotional beats land (show-don't-tell), dialogue reads naturally (per dialogue audit) |
| 9 | State accumulation integrity | 5% | After 5 chapters: truth files have consistent entries for all chapters, no stale state, character_matrix reflects all relationship changes, pending_hooks has no expired unresolved hooks |

## Kill Switch
Any chapter fails sensitivity audit (platform-prohibited content) → pipeline = 0.
```

- [ ] **Step 3: Write short-form rubric**

Create `tests/tiers/t3-pipeline/short-form/rubric.md`:

```markdown
# T3 Pipeline Rubric: Short-Form

Seed: tests/fixtures/outline-example.md → short-outline → short-drafting → short-packaging

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Short-form data integrity | 15% | Outline, all chapters, and packaging materials are mutually consistent; character names, settings, and events match across all outputs |
| 2 | Novel output coherence | 15% | All character actions groundable to established motivations; no unexplained plot jumps; chapter transitions reference prior events; all planted foreshadowing traceable in text |
| 3 | Short-form internal consistency | 15% | Character behavior in chapters matches outline character descriptions; plot events in chapters follow outline chapter tasks; no contradictions between chapters |
| 4 | Audit pass rate | 15% | All chapters pass all activated audit dimensions after revision |
| 5 | Pacing tightness | 10% | No chapter exceeds pacing-design word count range by >30%; act proportions match short-outline spec |
| 6 | Story completeness | 10% | Story has beginning, climax, and resolution; all threads opened in act 1 are closed by act 3 |
| 7 | Full project file completeness | 5% | Outline, all chapters, and packaging materials present and non-empty |
| 8 | Literary quality | 10% | Zero AI-typical phrasing, chapter openings create pull, emotional beats land, dialogue reads naturally |
| 9 | Packaging fidelity | 5% | Title, blurb, and selling points accurately represent the generated story content |

## Kill Switch
Any chapter fails sensitivity audit → pipeline = 0.
```

- [ ] **Step 4: Write import-form rubric**

Create `tests/tiers/t3-pipeline/import-form/rubric.md`:

```markdown
# T3 Pipeline Rubric: Import-Form

Seed: tests/fixtures/report-example.txt → import-analysis → character-extraction → world-extraction → canon-import

## Dimensions

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | End-to-end data integrity | 15% | All extracted files consistent with source text; no contradictions between extraction outputs |
| 2 | Extraction fidelity | 15% | All extracted characters/world/events traceable to source with zero fabrication; unconfirmed items list is exhaustive |
| 3 | Cross-phase state consistency | 15% | Characters extracted in character-extraction match those identified in import-analysis; world rules match story bible |
| 4 | Import completeness | 15% | All 4 import skills produce output; character files, world files, canon files, and analysis all present |
| 5 | Evidence coverage | 10% | ≥80% of extracted facts have chapter.paragraph evidence; <20% marked "unconfirmed" |
| 6 | Foreshadowing lifecycle completeness | 10% | Every identified foreshadowing element tracked in extraction output |
| 7 | Full project file completeness | 5% | import/analysis/*, characters/*, world/*, import/canon/* all present and non-empty |
| 8 | Import report quality | 10% | Analysis summary has accurate statistics; downstream task checklist is complete and actionable |
| 9 | Cross-extraction consistency | 5% | Characters in character-extraction exist in import-analysis; world rules consistent with story bible |

## Kill Switch
Any fabricated fact not marked "unconfirmed" → pipeline = 0.
```

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

## Example Entry

## Round 001 (2026-06-11) — Claude
- T1: 42/59 skills at 100
- T1 band breakdown: 42 PASS (90+), 10 CONDITIONAL (60-74), 7 FAIL (0-59)
- T2: not started (T1 incomplete)
- T3: not started
- Fixes applied: promoted BDI to HARD-GATE in skills/shenbi-review-character/SKILL.md
- Enhancement signals: 12 confusion points, 8 missing coverage items
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
# All commands are macOS bash 3.2 compatible.

set -euo pipefail

MODEL="${1:?Usage: round-exec.sh <model> <tier>}"
TIER="${2:?Specify T1, T2, or T3}"
DATE=$(date +%Y-%m-%d)

# Find next round number
LAST=$(ls -d tests/rounds/round-* 2>/dev/null | grep -v TEMPLATE | sort | tail -1)
if [ -z "$LAST" ]; then
  NUM=1
else
  NUM=$(($(basename "$LAST" | sed 's/round-\([0-9]*\).*/\1/') + 1))
fi
ROUND_NUM=$(printf "%03d" $NUM)
ROUND_DIR="tests/rounds/round-${ROUND_NUM}-${DATE}"
TIER_LOWER=$(echo "$TIER" | tr '[:upper:]' '[:lower:]')

echo "=== Creating round ${ROUND_NUM}: ${MODEL} / ${TIER} ==="

# Create directory structure directly (not cp -r from template)
mkdir -p "${ROUND_DIR}"/{t1-reports,t2-reports,t3-reports,novel-output,skill-traces}

# Write meta.json
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

# Write empty summary.json
cat > "${ROUND_DIR}/summary.json" << EOF
{
  "round": "${ROUND_NUM}",
  "model": "${MODEL}",
  "tier_target": "${TIER}",
  "t1_scores": {},
  "t2_scores": {},
  "t3_scores": {},
  "kill_switches": [],
  "enhancement_signals": [],
  "band_breakdown": {"pass": 0, "conditional": 0, "fail": 0},
  "next_actions": []
}
EOF

# Write empty enhancement signals
echo '{"signals": []}' > "${ROUND_DIR}/enhancement-signals.json"

echo "Round directory: ${ROUND_DIR}"
echo "Next steps:"
echo "  1. Run ${TIER} tests (manual or automated)"
echo "  2. Place reports in ${ROUND_DIR}/${TIER_LOWER}-reports/"
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

### Task 65b: Create skill trace template and summary aggregation script

**Files:**
- Create: `tests/rounds/round-000-TEMPLATE/skill-traces/trace-template.md`
- Create: `tests/summarize-round.py`

- [ ] **Step 1: Write skill trace template**

Create `tests/rounds/round-000-TEMPLATE/skill-traces/trace-template.md`:

```markdown
## Skill Trace: <skill-name> / <test-type>

### Agent Execution Log
- Skill loaded: yes/no
- Sections followed: [list which SKILL.md sections executed]
- Sections skipped: [list which sections missed or shortcut]
- Steps reordered: [any deviation from defined flow]
- Hard-gates triggered: [list any HARD-GATE blocks hit]
- Anti-rationalization table invoked: yes/no (if applicable)

### Output Quality
- Completeness: all expected output sections produced? [yes/no + details]
- Accuracy: findings correct (true positives vs false positives)? [yes/no + details]
- Actionability: recommendations specific enough to act on? [yes/no + details]

### Skill Enhancement Signals
- Confusion points: [where agent misinterpreted instructions]
- Missing coverage: [scenarios the skill doesn't handle but should]
- Over-specification: [instructions that are redundant or contradictory]
- Prompt adherence: [did agent follow DOT flowcharts exactly?]
- Edge cases: [novel situations not covered by current spec]
```

- [ ] **Step 2: Write summary aggregation script**

Create `tests/summarize-round.py`:

```python
#!/usr/bin/env python3
"""Aggregate per-skill scores into a round summary with band breakdown."""

import json
import sys
from pathlib import Path


def classify(score):
    if score >= 90:
        return "pass"
    elif score >= 60:
        return "conditional"
    else:
        return "fail"


def main():
    if len(sys.argv) < 2:
        print("Usage: summarize-round.py <round-dir>")
        sys.exit(1)

    round_dir = Path(sys.argv[1])
    summary_path = round_dir / "summary.json"

    if not summary_path.exists():
        print(f"No summary.json found in {round_dir}")
        sys.exit(1)

    with open(summary_path) as f:
        summary = json.load(f)

    # Compute band breakdown from t1_scores
    t1 = summary.get("t1_scores", {})
    bands = {"pass": 0, "conditional": 0, "fail": 0}
    for skill, score in t1.items():
        bands[classify(score)] += 1

    summary["band_breakdown"] = bands
    summary["next_actions"] = []

    fail_skills = [s for s, v in t1.items() if v < 60]
    cond_skills = [s for s, v in t1.items() if 60 <= v < 90]

    if fail_skills:
        summary["next_actions"].append(f"Fix failing skills: {', '.join(fail_skills)}")
    if cond_skills:
        summary["next_actions"].append(f"Improve conditional skills: {', '.join(cond_skills)}")
    if not fail_skills and not cond_skills:
        summary["next_actions"].append("All T1 skills at 100. Ready for T2.")

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Round summary updated: {bands['pass']} PASS, {bands['conditional']} CONDITIONAL, {bands['fail']} FAIL")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create benchmarks directory**

```bash
mkdir -p tests/benchmarks/models/{claude,gemini}
```

- [ ] **Step 4: Commit**

```bash
chmod +x tests/summarize-round.py
git add tests/rounds/round-000-TEMPLATE/skill-traces/ tests/summarize-round.py tests/benchmarks/
git commit -m "feat: add skill trace template, summary aggregation script, and benchmarks directory"
```

---

### Task 66: Migrate existing tests into new structure

**Files:**
- Modify: existing `tests/skill-behavior/` files → adapted into `tests/tiers/t1-skill/`
- Modify: existing `tests/skill-triggering/` files → adapted into `tests/tiers/t1-skill/`
- Modify: existing `tests/pressure-tests/` files → adapted into `tests/tiers/t1-skill/`
- Create: `tests/ARCHIVE-MIGRATED.md` (documents what was migrated and where originals live)

After migration, the original directories (`tests/skill-behavior/`, `tests/skill-triggering/`, `tests/pressure-tests/`) are kept as-is for reference. They are not deleted — the new structure lives alongside them. `tests/ARCHIVE-MIGRATED.md` documents the mapping so future maintainers know both structures exist.

- [ ] **Step 1: Migrate skill-behavior bug-hunt tests**

For each file in `tests/skill-behavior/review-catches-bug/`, copy the test content into the corresponding `t1-skill/shenbi-review-*/bug-hunt/input/scenario.md`. Extract the planted bug details into `expected/expected-output.md`.

Example for `phase2-character-bug.md`:

```bash
# Copy content and adapt format
cp tests/skill-behavior/review-catches-bug/phase2-character-bug.md \
   tests/tiers/t1-skill/shenbi-review-character/bug-hunt/input/scenario.md
```

Then manually edit to add the scenario header template and extract expected output.

- [ ] **Step 2: Migrate skill-triggering tests as routing scenarios**

The existing trigger tests test correct routing. These become routing scenarios in `t1-skill/using-shenbi/bug-hunt/` — the agent must correctly route each trigger phrase to the right skill. Adapt each trigger prompt into a scenario.md entry listing the expected target skill.

```bash
# Example: phase2-character-trigger.md becomes a routing scenario entry
# Agent is given the trigger phrase and must route to shenbi-review-character
# A "wrong route" variant is also created as a planted defect scenario
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
