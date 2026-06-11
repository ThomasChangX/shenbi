# Generative Test: shenbi-market-radar

## Skill Under Test
`skills/shenbi-market-radar/SKILL.md`

## Test Setup
A new urban fantasy novel is being planned for the Qidian platform. The project has `novel.json` (platform: Qidian, genre: urban fantasy) and `genre-config.json`. No market research has been done yet.

## Agent Task
Run shenbi-market-radar for the project. The agent must:
1. Search platform leaderboards and analyze top-20 titles in urban fantasy
2. Ensure every recommendation references specific leaderboard rank or trend data point
3. Flag any element with >60% occurrence in top-20 as saturated
4. Include differentiation suggestions for every trend signal
5. Create a decision checklist where every item is a single action with one-line rationale
6. Tie opening strategy to specific genre + platform data
7. Identify >=2 competitive works with rationale

## Seed Input
Project config at `novel.json` (platform: Qidian, genre: urban fantasy) with `genre-config.json`
