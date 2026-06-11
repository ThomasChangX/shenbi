# Generative Test: shenbi-anti-detect

## Skill Under Test
`skills/shenbi-anti-detect/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `drafts/chapter-5.md` that is known to contain AI markers from the drafting process. An initial AI marker audit has been run, identifying several marker points in the text.

## Agent Task
Run shenbi-anti-detect on the chapter with known AI markers. The agent must:
1. Identify all AI marker points in the text
2. Rewrite only at detected marker points — no wholesale rewriting
3. Preserve all content: plot, characters, foreshadowing unchanged
4. Preserve authorial voice; introduce zero new AI-typical patterns
5. Iterate up to 3 passes; if all fail, revert to best version
6. Produce a before/after audit comparison with per-marker-type breakdown

## Seed Input
Drafted chapter from `drafts/chapter-5.md` with known AI markers
