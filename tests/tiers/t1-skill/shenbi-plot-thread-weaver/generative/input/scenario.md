# Generative Test: shenbi-plot-thread-weaver

## Skill Under Test
`skills/shenbi-plot-thread-weaver/SKILL.md`

## Test Setup
A novel project exists with completed story architecture and volume outline output. No plot thread files exist yet.

## Agent Task
Run shenbi-plot-thread-weaver using the story architecture and volume output as context. Produce `tests/fixtures/chapter-plan-example.md` and `tests/fixtures/chapter-plan-example.md`. Ensure every chapter advances at least one thread (no blank chapters), A-lines don't exceed max_gap (default 2 chapters for P0), C-lines resolve within their planned span, subplot climaxes complement volume climaxes, thread crossings serve dramatic effect, and priority classifications are accurate (P0=novel-critical, P1=volume-critical, P2=arc-supporting, P3=flavor).

## Seed Input
Story architecture + volume output produced by prior skills from `tests/fixtures/outline-example.md`
