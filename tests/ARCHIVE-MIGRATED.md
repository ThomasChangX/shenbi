# Test Migration Record

Existing test files have been adapted into the new T1 structure below. The original directories are kept for reference:

- `tests/skill-behavior/` — original skill behavior tests
- `tests/skill-triggering/` — original skill trigger tests
- `tests/pressure-tests/` — original pressure tests

## Migration Mapping

### skill-behavior/review-catches-bug/ → T1 bug-hunt scenarios

| Source | Target |
|--------|--------|
| `skill-behavior/review-catches-bug/phase2-character-bug.md` | `tiers/t1-skill/shenbi-review-character/bug-hunt/input/scenario-phase2-character.md` |
| `skill-behavior/review-catches-bug/phase2-continuity-bug.md` | `tiers/t1-skill/shenbi-review-continuity/bug-hunt/input/scenario-phase2-continuity.md` |
| `skill-behavior/review-catches-bug/phase2-foreshadowing-bug.md` | `tiers/t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario-phase2-foreshadowing.md` |
| `skill-behavior/review-catches-bug/phase2-pacing-bug.md` | `tiers/t1-skill/shenbi-review-pacing/bug-hunt/input/scenario-phase2-pacing.md` |
| `skill-behavior/review-catches-bug/phase3-foreshadowing-lifecycle.md` | `tiers/t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario-lifecycle.md` |
| `skill-behavior/review-catches-bug/phase3-plant-track-resolve.md` | `tiers/t1-skill/shenbi-foreshadowing-track/bug-hunt/input/scenario-plant-track-resolve.md` |
| `skill-behavior/review-catches-bug/phase3-volume-consolidation.md` | `tiers/t1-skill/shenbi-volume-consolidation/bug-hunt/input/scenario-phase3-volume-consolidation.md` |
| `skill-behavior/review-catches-bug/phase4-dialogue-bug.md` | `tiers/t1-skill/shenbi-review-dialogue/bug-hunt/input/scenario-phase4-dialogue.md` |
| `skill-behavior/review-catches-bug/phase4-memo-compliance-bug.md` | `tiers/t1-skill/shenbi-review-memo-compliance/bug-hunt/input/scenario-phase4-memo.md` |
| `skill-behavior/review-catches-bug/phase4-reader-pull-bug.md` | `tiers/t1-skill/shenbi-review-reader-pull/bug-hunt/input/scenario-phase4-reader-pull.md` |
| `skill-behavior/review-catches-bug/phase4b-era-bug.md` | `tiers/t1-skill/shenbi-review-era/bug-hunt/input/scenario-phase4b-era.md` |
| `skill-behavior/review-catches-bug/phase4b-fanfic-bug.md` | `tiers/t1-skill/shenbi-review-fanfic/bug-hunt/input/scenario-phase4b-fanfic.md` |
| `skill-behavior/review-catches-bug/phase4b-highpoint-bug.md` | `tiers/t1-skill/shenbi-review-highpoint/bug-hunt/input/scenario-phase4b-highpoint.md` |
| `skill-behavior/review-catches-bug/phase4b-long-span-bug.md` | `tiers/t1-skill/shenbi-review-long-span/bug-hunt/input/scenario-phase4b-long-span.md` |
| `skill-behavior/review-catches-bug/phase4b-memo-compliance-bug.md` | `tiers/t1-skill/shenbi-review-memo-compliance/bug-hunt/input/scenario-pressure.md` |
| `skill-behavior/review-catches-bug/phase4b-motivation-bug.md` | `tiers/t1-skill/shenbi-review-motivation/bug-hunt/input/scenario-phase4b-motivation.md` |
| `skill-behavior/review-catches-bug/phase4b-pov-bug.md` | `tiers/t1-skill/shenbi-review-pov/bug-hunt/input/scenario-phase4b-pov.md` |
| `skill-behavior/review-catches-bug/phase4b-reader-pull-bug.md` | `tiers/t1-skill/shenbi-review-reader-pull/bug-hunt/input/scenario-pressure.md` |
| `skill-behavior/review-catches-bug/phase4b-texture-bug.md` | `tiers/t1-skill/shenbi-review-texture/bug-hunt/input/scenario-phase4b-texture.md` |
| `skill-behavior/review-catches-bug/phase4b-world-rules-bug.md` | `tiers/t1-skill/shenbi-review-world-rules/bug-hunt/input/scenario-phase4b-world-rules.md` |

### skill-behavior/revision-fixes-issue/ → T1 bug-hunt scenarios

| Source | Target |
|--------|--------|
| `skill-behavior/revision-fixes-issue/phase2-polishing-fix.md` | `tiers/t1-skill/shenbi-style-polishing/bug-hunt/input/scenario-phase2-polishing.md` |
| `skill-behavior/revision-fixes-issue/phase4b-revision-mode-routing.md` | `tiers/t1-skill/shenbi-chapter-revision/bug-hunt/input/scenario-phase4b-revision-routing.md` |

### skill-triggering/prompts/ → using-shenbi routing scenarios

| Source | Target |
|--------|--------|
| `skill-triggering/prompts/phase2-character-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-character.md` |
| `skill-triggering/prompts/phase2-continuity-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-continuity.md` |
| `skill-triggering/prompts/phase2-foreshadowing-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-foreshadowing.md` |
| `skill-triggering/prompts/phase2-polishing-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-polishing.md` |
| `skill-triggering/prompts/phase3-foreshadowing-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-foreshadowing.md` |
| `skill-triggering/prompts/phase3-intent-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-intent.md` |
| `skill-triggering/prompts/phase3-snapshot-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-snapshot.md` |
| `skill-triggering/prompts/phase3-truth-sync-trigger.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-truth-sync.md` |
| `skill-triggering/prompts/phase4-management-triggers.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase4-management.md` |
| `skill-triggering/prompts/phase4b-audit-triggers.md` | `tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase4b-audit.md` |

### pressure-tests/prompts/ → T1 bug-hunt scenarios

| Source | Target |
|--------|--------|
| `pressure-tests/prompts/audit-skipping-pressure.md` | `tiers/t1-skill/shenbi-review-anti-ai/bug-hunt/input/scenario-pressure.md` |
| `pressure-tests/prompts/chapter-writing-pressure.md` | `tiers/t1-skill/shenbi-chapter-drafting/bug-hunt/input/scenario-pressure.md` |
| `pressure-tests/prompts/foreshadowing-fatigue-pressure.md` | `tiers/t1-skill/shenbi-foreshadowing-track/bug-hunt/input/scenario-pressure.md` |
| `pressure-tests/prompts/import-shortcut-pressure.md` | `tiers/t1-skill/shenbi-import-analysis/bug-hunt/input/scenario-pressure.md` |
| `pressure-tests/prompts/snapshot-skip-pressure.md` | `tiers/t1-skill/shenbi-snapshot-manage/bug-hunt/input/scenario-pressure.md` |
| `pressure-tests/prompts/state-drift-pressure.md` | `tiers/t1-skill/shenbi-state-settling/bug-hunt/input/scenario-pressure.md` |

## Notes

- Original files are NOT deleted — they remain in their original locations
- Migrated files are added as additional test scenarios alongside scaffolded `scenario.md` files
- All targets already had existing `scenario.md` files, so migrated files use alternative names:
  - `scenario-pressure.md` for pressure test migrations
  - `scenario-lifecycle.md` for lifecycle-specific tests
  - `scenario-phase{N}-{name}.md` for phase-specific bug hunt tests
  - `routing-phase{N}-{name}.md` for skill trigger routing tests
