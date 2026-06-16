# First Novel

This guide walks through running a T1 (skill-level) and T2 (phase-level) validation pipeline on a new novel project.

## Prerequisites

- Shenbi installed (see [Installation](installation.md))
- A seed file with target word count and genre

## Running T1 (skill validation)

```bash
just gate G0 seed.md
just dispatch shenbi-worldbuilding generative round-001
```

## Running T2 (phase transition)

```bash
just gate G5 architecture round-001
```

Full pipeline documentation is forthcoming.
