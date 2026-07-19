# Spec 14: Skill Contract and Description Quality Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Medium
> **Source:** SHOUT-OUT — discovered during cross-spec review of Specs 1-11
> **Relationship:** Independent of Specs 1-11

---

## 1. Executive Summary

The `AGENTS.md` workspace instructions specify strict rules for skill authoring:
- `name`: lowercase-kebab
- `description`: ONLY when-to-use trigger conditions, ≤500 chars. Never describes what the skill does.

The shenbi framework has 69 skills (67 functional + 2 meta). During the cross-spec review, it became clear that NONE of the 11 existing specs verify whether all 69 skills comply with these contract rules. The verification work across Specs 1-11 revealed multiple instances where skills have contracts that don't match their actual behavior:

1. **Spec 1 finding:** `shenbi-state-settling` has iron-rule #4 mandating incremental append, but no programmatic enforcement exists. The contract says "append" but the dispatch path overwrites. This contract-behavior mismatch is the root cause of truth file data loss.

2. **Spec 2 finding:** `shenbi-chapter-revision` SKILL.md defines spot-fix and rewrite modes but has no no-op/auto-skip output specification. The contract is incomplete, causing arbitrary output in no-op routes.

3. **Spec 3 finding:** `shenbi-chapter-revision` contract declares `updates: chapters/chapter-N.md` but in no-op mode it writes revision summaries there. The contract doesn't distinguish "update" (modify prose) from "overwrite" (replace with metadata).

4. **Spec 5 finding:** `shenbi-escalation-review` is dispatched reactively but its SKILL.md doesn't document the reactive dispatch pattern.

These are not isolated incidents — they represent a systemic gap in skill contract verification.

---

## 2. Root Cause Analysis

### 2.1 No Skill Contract Linting

There is no automated check that verifies:
- `description` field is ≤500 chars
- `description` contains only when-to-use triggers, not behavioral descriptions
- `reads:`, `writes:`, `updates:` fields accurately reflect what the skill's code/prompt actually does
- `writes:` paths are disjoint from `updates:` paths (write = create new, update = modify existing)
- The skill's actual output format matches its declared output contract

### 2.2 Contract-Behavior Mismatch Pattern

The root cause pattern across Specs 1-3:
1. SKILL.md declares a contract (e.g., "append-only updates")
2. The dispatch path (`_write_parsed_outputs` → `safe_write`) does NOT enforce the contract
3. The LLM follows the dispatch path's implicit behavior (emit full file → overwrite) rather than the contract's explicit behavior (append)
4. G4 validates the output format but NOT the write semantics

### 2.3 Missing Write Semantics in Contracts

The `reads:`/`writes:`/`updates:` YAML contract fields describe WHAT files are touched but not HOW:
- `writes:` — does "write" mean "create new file" or "overwrite if exists"?
- `updates:` — does "update" mean "append" or "replace"? The answer differs per file type (truth files = append, snapshots = replace) but the contract doesn't encode this.

Spec 1 proposes an `update_mode` frontmatter field, but this is per-file, not per-skill-contract. The skill contract itself should declare the write semantics.

---

## 3. Fix Strategy

### 3.1 Skill Contract Linter

Create a new G0 check (`G0.skill_contract`) that validates all 69 skills:

```python
def check_skill_contracts(skills_dir: Path) -> list[str]:
    """Validate all skill SKILL.md files against contract rules."""
    issues = []
    for skill_md in skills_dir.glob("*/SKILL.md"):
        frontmatter = _parse_frontmatter(skill_md)

        # Check description length
        desc = frontmatter.get("description", "")
        if len(desc) > 500:
            issues.append(f"G0.sc.desc_too_long:{skill_md.parent.name}:{len(desc)}")

        # Check description is trigger-only (heuristic: no imperative verbs)
        if _has_behavioral_description(desc):
            issues.append(f"G0.sc.desc_has_behavior:{skill_md.parent.name}")

        # Check writes/updates disjoint
        writes = set(frontmatter.get("writes", []))
        updates = set(frontmatter.get("updates", []))
        overlap = writes & updates
        if overlap:
            issues.append(f"G0.sc.write_update_overlap:{skill_md.parent.name}:{overlap}")

        # Check write semantics declared
        for field in ("writes", "updates"):
            for path in frontmatter.get(field, []):
                if not _has_write_semantics(frontmatter, path):
                    issues.append(f"G0.sc.missing_write_semantics:{skill_md.parent.name}:{path}")

    return issues
```

### 3.2 Add Write Semantics to Contract YAML

Extend skill frontmatter with explicit write semantics:

```yaml
contract:
  writes:
    - file: chapters/chapter-N-revision-decisions.json
      mode: create_or_overwrite  # new file or replace existing
  updates:
    - file: chapters/chapter-N.md
      mode: merge_prose          # merge revision into existing prose
      no_op_behavior: skip_write # in no-op mode, do NOT write this file
    - file: truth/resonance_trend.md
      mode: append_dedup         # append with deduplication by key
      key: chapter
```

### 3.3 Contract Enforcement in Dispatch Path

The dispatch path (`_write_parsed_outputs`) should read the skill's declared write semantics and enforce them:
- `mode: create_or_overwrite` → `safe_write(path, content)` (current behavior)
- `mode: merge_prose` → content-preservation guard (Spec 3 §3.2) + merge
- `mode: append_dedup` → `write_truth_file(mode="upsert")` (Spec 1 §3.2)
- `no_op_behavior: skip_write` → check revision route before writing

### 3.4 Skill Description Audit

Audit all 69 skills' descriptions for compliance:
- Generate a report of all skills with descriptions > 500 chars
- Flag descriptions that contain behavioral text ("This skill does X") rather than trigger conditions ("Use when Y happens")

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/gates/g0.py` (or new `g0_skill_contract.py`) | Add `G0.skill_contract` check | Validate all 69 skills at pipeline start |
| All 69 `skills/*/SKILL.md` | Add write semantics to contract YAML | Make implicit write behavior explicit |
| `src/shenbi/pipeline/dispatch_helper.py` (`_write_parsed_outputs`) | Read and enforce declared write semantics | Close contract-behavior gap |
| New tool: `tools/audit-skill-descriptions.py` | Generate compliance report | Surface description violations |

---

## 5. Verification Criteria

1. **G0.skill_contract passes** for all 69 skills
2. **All descriptions ≤ 500 chars** (automated check)
3. **No write/update overlap** in any skill contract
4. **All update paths declare write semantics** (mode + key)
5. **Dispatch path enforces declared semantics** — `mode: append_dedup` actually deduplicates
6. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 14 (this spec, Skill Contract and Description Quality)
    |
    +---> Depends on: Spec 1 (write_truth_file modes) — semantics reference these modes
    +---> Depends on: Spec 3 (content-size guard) — merge_prose mode uses this guard

Prerequisites: Specs 1 and 3 should define their write modes first
```
