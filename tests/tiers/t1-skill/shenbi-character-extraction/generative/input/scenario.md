# Generative Test: shenbi-character-extraction

## Skill Under Test
`skills/shenbi-character-extraction/SKILL.md`

## Test Setup
A novel manuscript with 12 chapters of an urban fantasy story has been analyzed. Import analysis output exists at `import/analysis/02_characters.md` identifying 5 characters. No character cards have been generated yet.

## Agent Task
Run shenbi-character-extraction on the analyzed manuscript. The agent must:
1. Read import/analysis/02_characters.md and source chapters for each character's appearances
2. Extract personality traits with >=1 quoted passage and chapter.paragraph reference per trait
3. Generate voice fingerprints with statistical extraction (word frequency, sentence length, catchphrases) from actual dialogue
4. Identify character arcs with chapter-specific behavioral evidence for start and turning points
5. Build complete relationship network — all named pairs with interaction scenes must have entries
6. Mark all non-derivable items as "unconfirmed"

## Seed Input
Analyzed manuscript at `import/analysis/02_characters.md` with source `chapters/*.md` (12 chapters)
