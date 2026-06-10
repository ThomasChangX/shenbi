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
