# Spec 21: Semantic Index Population and Parser Schema Coherence Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Medium
> **Source:** Systematic debugging Phase 1 evidence (E30)
> **Consolidated from findings:**
> - E30: truth-index.json has empty hooks:{} and rules:{} — no entities indexed despite 56 chapters

> **Correction note (audit):** E33 (the claim that `G4.rules.count` returns 0 for `## 规则` headings) was found to be FALSE. `gates/g4/worldbuilding.py:88-96` ALREADY handles `## 规则` headings via `heading_rules = len(re.findall(r"## 规则\s*[：:.]?\s*[一二三四五六七八九十\d]+", rc))` and uses `max(heading_rules, numbered_rules)`. The G4 gate is correct. The sole verified defect is the `truth_index.py` parser mismatch documented below. E33 has been removed from this spec.

---

## 1. Executive Summary

A single parser **runs successfully but returns empty results** because its matching pattern doesn't align with the actual file format:

1. **Empty entity index (E30):** `truth-index.json` has `hooks: {}` and `rules: {}` — completely empty despite 56 chapters with active foreshadowing tracking and 10 worldbuilding rules. The rule extraction pattern in `truth_index.py` fails to match the actual `world/rules.md` heading format.

**Verified defect:** `truth_index.py:32` compiles `_RULE_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$")`. This regex expects numeric IDs (`## 1:` or `## R1:`). But production `world/rules.md` uses Chinese ordinals (`## 规则一：`, `## 规则二：`, …). Because the regex requires a digit after `## `, it matches ZERO headings — leaving `truth-index.json` with empty `rules: {}`.

**Note on G4:** The G4 worldbuilding gate (`gates/g4/worldbuilding.py:88-96`) is NOT defective. It already counts `## 规则` headings correctly via `max(heading_rules, numbered_rules)`. No change to the G4 gate is required or proposed by this spec.

**Root cause:** The `truth_index.py` rule parser pattern was written against an assumed numeric-ID format that doesn't match what the skills actually produce. The parser silently succeeds (no error) but extracts zero entities — a "silent success failure" pattern.

---

## 2. Root Cause Analysis

### 2.1 truth_index.py Empty Hooks/Rules (E30)

`truth_index.py` builds a `TruthIndex` by:
- Indexing characters from `characters/*.md` frontmatter `name` field
- Indexing hooks from `truth/pending_hooks.md` frontmatter `hooks` list
- Indexing rules from `world/rules.md` headings

The production `truth-index.json` shows:
- `characters`: partially populated (林烽 indexed)
- `hooks: {}` — EMPTY despite `pending_hooks.md` existing with hook data
- `rules: {}` — EMPTY despite `world/rules.md` having 10 rules

**Likely cause:** The hook indexing reads frontmatter `hooks` list, but `pending_hooks.md` may store hooks in the markdown body (not frontmatter), or the frontmatter format changed. The rule indexing pattern doesn't match `## 规则` headings.

### 2.2 truth_index.py Rule Parser Mismatch (the sole verified defect)

The real defect is in `truth_index.py:32`:

```python
_RULE_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$")
```

This regex requires a **numeric ID** immediately after `## ` — either `## 1:`, `## 42:`, or `## R1:`. The capturing group `(R?\d+)` will only match strings beginning with an optional `R` followed by digits.

But production `world/rules.md` uses **Chinese ordinals**:

```markdown
## 规则一：能量守恒
## 规则二：信息衰减
...
## 规则十：叙事闭环
```

Because none of these headings start with a digit (they start with the CJK character `规`), `_RULE_RE` matches ZERO headings. The rule extractor then writes nothing into `index.rules`, leaving `truth-index.json` with empty `rules: {}`.

**Why this was previously mis-diagnosed:** The original E33 finding blamed the G4 gate (`gates/g4/worldbuilding.py`) for "returning 0 rules." That was FALSE — the G4 gate at lines 88-96 already handles `## 规则` headings via `heading_rules = len(re.findall(r"## 规则\s*[：:.]?\s*[一二三四五六七八九十\d]+", rc))` and uses `max(heading_rules, numbered_rules)`, so it returns the correct count. The empty `truth-index.json` rules are produced entirely by the `truth_index.py` parser, which is the only defective component.

**Fix scope:** Only `truth_index.py` needs correction. The G4 gate is correct and must not be changed.

---

## 3. Fix Strategy

### 3.1 Parser-Format Compatibility Tests

For every parser/indexer, create a test that verifies it extracts ≥1 entity from a known-good fixture:

```python
# tests/unit/pipeline/test_truth_index_population.py

def test_truth_index_extracts_hooks_from_fixture():
    """Verify truth_index extracts hooks from a known-good pending_hooks.md."""
    project_dir = create_test_project_with_hooks()
    index = build_index(project_dir)

    assert len(index.hooks) > 0, (
        "truth_index extracted zero hooks — parser format mismatch. "
        "Verify the hook extraction pattern matches the actual pending_hooks.md format."
    )

def test_truth_index_extracts_rules_from_fixture():
    """Verify truth_index extracts rules from a known-good rules.md."""
    project_dir = create_test_project_with_rules()
    index = build_index(project_dir)

    assert len(index.rules) > 0, (
        "truth_index extracted zero rules — parser format mismatch."
    )
```

### 3.2 Fix the truth_index.py Rule Parser (`_RULE_RE`)

The defective regex at `truth_index.py:32` is:
```python
_RULE_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$")  # expects ## 1: / ## R1:
```

Replace it with a multi-format rule parser that accepts Chinese ordinals (`## 规则一：`) as well as numeric IDs:

```python
# truth_index.py — replaces the single numeric-only _RULE_RE
_RULE_HEADING_RE = re.compile(
    r"^##\s+规则\s*[：:.]?\s*([一二三四五六七八九十\d]+)[:：]?\s*(.+)$"
)
_RULE_NUMERIC_RE = re.compile(r"^##\s+(R?\d+)[:.]?\s*(.+)$")

def _parse_rules(rules_text: str) -> list[tuple[str, str]]:
    """Parse worldbuilding rule headings. Supports both formats:
       - Chinese ordinals: ## 规则一：能量守恒
       - Numeric IDs:      ## 1: / ## R1:
    """
    rules = []
    for line in rules_text.splitlines():
        m = _RULE_HEADING_RE.match(line) or _RULE_NUMERIC_RE.match(line)
        if m:
            rules.append((m.group(1), m.group(2).strip()))
    return rules
```

This is the ONLY code change required. The G4 gate (`gates/g4/worldbuilding.py`) must NOT be modified — it already counts `## 规则` headings correctly via `max(heading_rules, numbered_rules)`.

### 3.2b Hook Parser Fix

The `truth_index.py:_index_hooks()` (line 123) reads the frontmatter `hooks` list. Production `pending_hooks.md` stores hooks in the YAML frontmatter `hooks` array (in deterministic plant format) AND in the markdown body. The index only reads frontmatter. If frontmatter is empty (e.g., hooks were written to body only), the index returns empty.

**Fix:** `_index_hooks()` should ALSO parse the body for hook entries by scanning for `## .*伏笔` headings and extracting hook IDs via `_HOOK_ID_RE`. This dual-source extraction (frontmatter + body) ensures hooks are indexed regardless of which write path produced them.

```python
# truth_index.py — extend _index_hooks() to parse BOTH sources

def _index_hooks(project_dir: Path) -> dict[str, dict]:
    """Index hooks from pending_hooks.md.

    Dual-source extraction:
      1. YAML frontmatter `hooks` array (authoritative, written by hook_planting.py)
      2. Markdown body `## ...伏笔` headings (written by foreshadowing-track /
         state-settling LLM path) — extracted via _HOOK_ID_RE so hooks are
         indexed even when the frontmatter is empty or out of sync.
    """
    hooks: dict[str, dict] = {}
    hooks_path = project_dir / "truth" / "pending_hooks.md"
    if not hooks_path.exists():
        return hooks

    text = hooks_path.read_text(encoding="utf-8")

    # Source 1: YAML frontmatter `hooks` list (existing behavior, line 123+)
    frontmatter, _, body = _split_frontmatter(text)
    if frontmatter:
        for h in frontmatter.get("hooks", []) or []:
            hid = h.get("id")
            if hid:
                hooks[hid] = h

    # Source 2: markdown body `## .*伏笔` headings — extract hook IDs via _HOOK_ID_RE.
    # Catches entries written to the body only (frontmatter empty/out of sync).
    for line in body.splitlines():
        if re.match(r"^##\s+.*伏笔", line):
            for hid_match in _HOOK_ID_RE.finditer(line):
                hid = hid_match.group(0)
                if hid not in hooks:
                    hooks[hid] = {"id": hid, "source": "body"}

    return hooks
```

### 3.3 Silent-Success-Failure Detection

Add a post-index assertion:

```python
def build_index(project_dir: Path) -> TruthIndex:
    """Build truth entity index with population assertions."""
    index = _do_build_index(project_dir)

    # SILENT-SUCCESS-FAILURE DETECTION
    # If files exist but index is empty, the parser format is wrong
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if hooks_file.exists() and hooks_file.stat().st_size > 100:
        if not index.hooks:
            logger.warning(
                "truth_index_empty_hooks",
                file=str(hooks_file),
                size=hooks_file.stat().st_size,
                msg="pending_hooks.md exists with content but index extracted zero hooks — "
                    "parser format mismatch likely"
            )

    rules_file = project_dir / "world" / "rules.md"
    if rules_file.exists() and rules_file.stat().st_size > 100:
        if not index.rules:
            logger.warning(
                "truth_index_empty_rules",
                file=str(rules_file),
                size=rules_file.stat().st_size,
                msg="rules.md exists with content but index extracted zero rules — "
                    "parser format mismatch likely"
            )

    return index
```

### 3.4 Periodic Re-indexing with Validation

Spec 7 §3.5 proposes periodic truth-index rebuilding. Add population validation after each rebuild:

```python
def rebuild_truth_index(project_dir: Path) -> TruthIndex:
    index = build_index(project_dir)

    # Validate population
    if not index.hooks and not index.rules and not index.characters:
        raise IndexPopulationError(
            "Truth index is completely empty despite source files existing. "
            "Parser patterns do not match file formats."
        )

    safe_write(project_dir / "truth-index.json", index.to_json())
    return index
```

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/pipeline/truth_index.py` (`_RULE_RE`, line 32) | Replace numeric-only regex with multi-format parser accepting Chinese ordinals `## 规则一：` | Index actual rule entities instead of an empty set |
| `src/shenbi/pipeline/truth_index.py` (hook extraction, `_index_hooks` line 123) | Extend `_index_hooks()` to parse body `## .*伏笔` headings in addition to frontmatter (dual-source extraction, §3.2b) + add population assertions | Index actual hook entities regardless of which write path (deterministic plant vs LLM body) produced them |
| `tests/unit/pipeline/test_truth_index_population.py` (new) | Population validation tests | Prevent silent-success failures |

> **Not changed:** `src/shenbi/gates/g4/worldbuilding.py` — the G4 gate already handles `## 规则` headings correctly and is out of scope for this spec.

---

## 5. Verification Criteria

1. **truth-index.json** has non-empty hooks (>= 1) when pending_hooks.md has content — verified from BOTH the frontmatter `hooks` array AND the markdown body `## .*伏笔` headings (dual-source extraction per §3.2b)
2. **truth-index.json** has non-empty rules (>= 1) when rules.md has content
3. **truth_index.py** `_RULE_RE` / `_parse_rules` matches `## 规则一：…` headings (not zero)
4. **G4 gate unchanged:** `gates/g4/worldbuilding.py` is NOT modified by this spec
5. **Population warning** logged when index is empty but source files have content
6. **Population test** fails if parser extracts zero entities from a known-good fixture
7. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 21 (this spec, Semantic Index Population and Parser Coherence)
    |
    +---> Enhances: Spec 1 (truth file system depends on accurate entity index)
    +---> Enhances: Spec 15 (embedding infrastructure uses entity index for Route A)

Prerequisites: None (standalone parser fix)
```
