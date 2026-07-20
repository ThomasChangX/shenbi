# Chapter File Format Specification

## Overview

Each chapter file (`chapters/chapter-N.md`) serves as both a novel chapter
deliverable and an internal quality-control document. It contains two types
of content:

1. **Prose Body** -- the actual novel chapter content (the deliverable)
2. **META Blocks** -- internal quality-control self-check artifacts (not prose)

## File Structure

```markdown
<!--META-BEGIN-->
## PRE_WRITE_CHECK
[core task, hooks to fulfill, taboos, ending pattern, AI traps,
 resonance gaps, transition budget]
<!--META-END-->

# Chapter N: [Title]

[Prose content -- the actual novel chapter]

<!--META-BEGIN-->
## POST_WRITE_SELF_CHECK
[transition density check, curiosity check, meta-narrative check]
<!--META-END-->
```

## META Blocks

META blocks are quality-control artifacts embedded in chapter files.
They are **not part of the novel prose**. They exist to:
- Document the writer's pre-write planning checklist (PRE_WRITE_CHECK)
- Document the writer's post-write self-assessment (POST_WRITE_SELF_CHECK)
- Provide traceability for quality gate verification

### META Block Ratio

Across 56 generated chapters, the average META block proportion is
approximately 31.3% of file size. The pipeline monitoring gate (G2.meta_ratio)
triggers a WARN when this exceeds 50%.

## Stripping META Blocks

Any consumer that reads chapter files for pure prose must strip META blocks.
The canonical stripping implementation is at `src/shenbi/gates/shared.py:120-121`:

```python
c = re.sub(r"<!--META-BEGIN-->.*?<!--META-END-->", "", c, flags=re.DOTALL)
```

### Consumers that MUST strip:
- Word count functions (e.g., `shared.py:word_count_md`)
- Chapter scoring and quality analysis
- External publication tools
- Human readers

### Consumers that may read META blocks:
- Pipeline quality gate verification (G2, G4)
- Audit and scoring skills
- The pipeline itself (for checkpointing and state tracking)

## Future: META Block Separation

In a future specification (post Spec 2 stabilization), META blocks will be
extracted to separate `chapters/chapter-N-meta.md` files. At that point:
- `chapters/chapter-N.md` becomes pure prose
- META stripping logic in `shared.py` is removed
- All downstream audit/scoring skills read from `chapter-N-meta.md`
