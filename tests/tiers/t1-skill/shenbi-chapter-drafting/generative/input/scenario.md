# Generative Test: shenbi-chapter-drafting

## Skill Under Test
`skills/shenbi-chapter-drafting/SKILL.md`

## Test Setup
A novel project exists with completed chapter memo at `tests/fixtures/chapter-plan-example.md`. Truth files include character voice profiles at `tests/fixtures/character-profile-example.md`, foreshadowing pool at `tests/fixtures/pending-hooks-example.md`, and chapter summaries at `tests/fixtures/chapter-summaries-example.md`. The project is ready to draft chapter 5.

## Agent Task
Run shenbi-chapter-drafting to draft chapter 5 from the memo. The agent must:
1. Complete PRE_WRITE_CHECK before any drafting
2. Draft the chapter executing all memo specifications
3. Keep AI-typical transition words under 1/3000 word density
4. Match all character voice profiles in dialogue
5. Show emotions through action/sensation
6. Create a chapter-end hook in the last 300 words
7. Include all foreshadowing items specified in the memo
8. Maintain varied paragraph rhythm

## Seed Input
Chapter memo from `tests/fixtures/chapter-plan-example.md`, character profiles from `tests/fixtures/character-profile-example.md`, foreshadowing state from `tests/fixtures/pending-hooks-example.md`
