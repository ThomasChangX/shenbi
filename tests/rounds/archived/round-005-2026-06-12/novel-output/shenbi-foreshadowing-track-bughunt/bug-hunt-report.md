# Bug-Hunt Report: shenbi-foreshadowing-track

## Defect Detection Results

### Defect 1: Core hook marked as ABANDONED — core hooks must never be abandoned
- **Detected**: yes
- **Location**: `tracking-chapter-10.md` — frontmatter: "status: ABANDONED" + "core_hook: true"
- **Violated Rule**: SKILL.md core hook protection — "core_hook: true 的钩子不得标记为 ABANDONED，必须被 resolve 或 defer"
- **Evidence**: A hook with core_hook: true has status ABANDONED. Core hooks represent story-critical foreshadowing — abandoning them causes story fracture. The only valid states for core hooks are active, planted, or resolved.
- **Severity**: error

## Summary
- Defects planted: 1, Detected: 1/1, False positives: 0
