# Positive Quality Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a positive-quality scoring layer to shenbi (per-chapter `review-resonance` + per-volume `review-arc-payoff` + `foundation-review` anti-trope dimension), with drift detection, calibration, and enforced independent-agent scoring.

**Architecture:** Extend the proven `foundation-review` weighted-rubric pattern to two new layers. Deterministic logic (drift triggers, confidence calibration, block routing, trope matching) lives in `src/shenbi/skill_utils/` as tested Python; skill behavior lives in `SKILL.md`; output validation in `gates/g4/`; the independence rule is a top-level frontmatter marker `requires_independent_agent` enforced via `contract.py` + a G0 check.

**Tech Stack:** Python 3 (src/shenbi, uv, ruff/mypy strict, pytest, structlog), PyYAML frontmatter, Markdown skills, JSON config. Spec: `docs/superpowers/specs/2026-06-22-positive-quality-gates-design.md`.

**Spec refinements discovered during planning (authoritative — override spec frontmatter):**
- **R1:** A/B `reads` use `{file, fields}` dict form. `contract.py` currently rejects non-str → Task 0.1 extends the loader (this *is* the P7 forward-compat work).
- **R2:** Calibration anchor paths (`tests/fixtures/calibration/...`) are **scorer inputs**, not project I/O → they are NOT in the `reads` contract; they live in SKILL.md prose + the scoring dispatch prompt. (Spec §5.1/§6.2 frontmatter showed them in `reads` — do not copy that.)

---

## File Structure

**New Python (deterministic logic + framework):**
- `src/shenbi/contract.py` — MODIFY: accept dict-form reads; add `requires_independent_agent` loader.
- `src/shenbi/gates/g0.py` — MODIFY: add G0 check "report-kind ⇒ requires_independent_agent".
- `src/shenbi/skill_utils/drift_detection/__init__.py` + `compute_drift.py` + `__main__.py` — NEW: smoothing + per-chapter & per-volume triggers.
- `src/shenbi/skill_utils/review_resonance/__init__.py` + `routing.py` + `__main__.py` — NEW: 3-path block routing + revision cap.
- `src/shenbi/skill_utils/calibration/__init__.py` + `confidence.py` + `__main__.py` — NEW: confidence downgrade by anchor hit-rate.
- `src/shenbi/skill_utils/trope_detection/__init__.py` + `match_tropes.py` + `__main__.py` — NEW: tropeInventory matching.
- `src/shenbi/gates/g4/review_resonance.py` — NEW: G4 checker for A.
- `src/shenbi/gates/g4/review_arc_payoff.py` — NEW: G4 checker for B.
- `src/shenbi/gates/g4/generic.py` — MODIFY: register A/B in the router.

**New / modified skills (Markdown):**
- `skills/shenbi-review-resonance/SKILL.md` — NEW (A).
- `skills/shenbi-review-arc-payoff/SKILL.md` — NEW (B).
- `skills/shenbi-foundation-review/SKILL.md` — MODIFY (C: +反套路维度, rebalance).
- `skills/shenbi-chapter-planning/SKILL.md` — MODIFY (+`chapter_role` field).
- `skills/shenbi-chapter-drafting/SKILL.md` — MODIFY (PRE_WRITE_CHECK +共鸣短板).
- `skills/shenbi-drift-guidance/SKILL.md` — MODIFY (read trends, run drift triggers).
- `skills/shenbi-volume-consolidation/SKILL.md` — MODIFY (call B at boundary).
- `skills/using-shenbi/SKILL.md` — MODIFY (trigger map + audit activation).
- `skills/shenbi-review-*/SKILL.md` (×18) + `skills/shenbi-foundation-review/SKILL.md` — MODIFY: add `requires_independent_agent: true` + 铁律 line.

**Data / registry:**
- `docs/framework/truth-files.yaml` — MODIFY: +`truth/resonance_trend.md`, +`truth/arc_payoff_trend.md`, +`audits/volume-N-payoff.md` parametric + `audits/volume-*.md` glob.
- `tests/fixtures/genre-config-example.json` — MODIFY: +`tropeInventory` key.
- `tests/fixtures/calibration/resonance/*.md`, `.../arc-payoff/*.md` — NEW: anchor fixtures.
- `tests/tiers/t1-skill/shenbi-review-resonance/` — NEW (generative/bug-hunt/clean + rubric).
- `tests/tiers/t1-skill/shenbi-review-arc-payoff/` — NEW.
- `tests/tiers/deps.json` — MODIFY: add A/B to phases.

**Tests:**
- `tests/unit/skill_utils/test_drift_detection.py`, `test_routing.py`, `test_calibration.py`, `test_trope_detection.py`, `tests/unit/contract/test_dict_reads.py`, `tests/unit/gates/test_g0_independence.py` — NEW.

---

## Phase 0 — Foundation (cross-cutting infra)

Unblocks C, A, B. Each task ships green tests.

### Task 0.1: Extend contract loader (dict-form reads + independence marker)

**Files:**
- Modify: `src/shenbi/contract.py`
- Test: `tests/unit/contract/test_dict_reads.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/contract/test_dict_reads.py
from pathlib import Path
import textwrap
from shenbi.contract import load_contract, requires_independent_agent, ContractError


def _write_skill(tmp_path: Path, skill: str, fm: str) -> Path:
    skill_dir = tmp_path / "skills" / skill
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{fm}\n---\n# body\n", encoding="utf-8")
    return path


def test_dict_form_reads_extract_file_and_keep_fields(tmp_path, monkeypatch):
    _write_skill(tmp_path, "shenbi-test-dict",
        "name: shenbi-test-dict\n"
        "contract:\n  kind: report\n  reads:\n"
        "    - {file: truth/audit_drift.md, fields: [shortcomings]}\n"
        "    - truth/current_state.md\n"
        "  writes: [audits/chapter-N-dict.md]\n  updates: []\n")
    monkeypatch.setattr("shenbi.contract.SKILLS", tmp_path / "skills")
    c = load_contract("shenbi-test-dict")
    assert c["reads"] == ["truth/audit_drift.md", "truth/current_state.md"]
    assert c["read_fields"] == {"truth/audit_drift.md": ["shortcomings"]}


def test_requires_independent_agent_reads_top_level_field(tmp_path, monkeypatch):
    _write_skill(tmp_path, "shenbi-test-ind",
        "name: shenbi-test-ind\nrequires_independent_agent: true\n"
        "contract:\n  kind: report\n  reads: []\n  writes: [audits/x.md]\n  updates: []\n")
    monkeypatch.setattr("shenbi.contract.SKILLS", tmp_path / "skills")
    assert requires_independent_agent("shenbi-test-ind") is True


def test_requires_independent_agent_default_false(tmp_path, monkeypatch):
    _write_skill(tmp_path, "shenbi-test-noind",
        "name: shenbi-test-noind\n"
        "contract:\n  kind: artifact\n  reads: []\n  writes: [chapters/chapter-N.md]\n  updates: []\n")
    monkeypatch.setattr("shenbi.contract.SKILLS", tmp_path / "skills")
    assert requires_independent_agent("shenbi-test-noind") is False
```

- [ ] **Step 2: Run, verify FAIL** — `uv run pytest tests/unit/contract/test_dict_reads.py -v` → ImportError / KeyError (`read_fields`, `requires_independent_agent`).

- [ ] **Step 3: Implement**

Edit `src/shenbi/contract.py`:

```python
# 1. Extend Contract TypedDict (add read_fields; keep backward compat)
class Contract(TypedDict):
    kind: OutputKind
    reads: list[str]
    writes: list[str]
    updates: list[str]
    read_fields: dict[str, list[str]]   # only populated for dict-form reads
```

```python
# 2. New helper to normalize a read item (str | dict) -> (path, fields|None)
def _normalize_read_item(item: Any) -> tuple[str, list[str] | None]:
    if isinstance(item, str):
        return item, None
    if isinstance(item, dict) and "file" in item:
        fields = item.get("fields")
        if fields is not None and not (isinstance(fields, list) and all(isinstance(x, str) for x in fields)):
            raise ContractError("contract.reads[].fields must be list[str]", field="reads")
        return str(item["file"]), fields
    raise ContractError("contract.reads[] must be str or {file, fields?}", field="reads")
```

```python
# 3. Rewrite the reads loop inside _validate
    validated: dict[str, list[str]] = {}
    read_fields: dict[str, list[str]] = {}
    for field in ("reads", "writes", "updates"):
        val = raw.get(field)
        if not isinstance(val, list):
            raise ContractError(f"contract.{field} must be a list", skill=skill, field=field)
        out: list[str] = []
        for item in val:
            if field == "reads":
                path, fields = _normalize_read_item(item)
                if not resolves(path, registry):
                    raise ContractError("contract path does not resolve in registry",
                                        skill=skill, field=field, path=path)
                out.append(path)
                if fields is not None:
                    read_fields[path] = fields
            else:
                if not isinstance(item, str):
                    raise ContractError(f"contract.{field} must be list[str]", skill=skill, field=field)
                if not resolves(item, registry):
                    raise ContractError("contract path does not resolve in registry",
                                        skill=skill, field=field, path=item)
                out.append(item)
        validated[field] = out
    return {"kind": kind, "reads": validated["reads"], "writes": validated["writes"],
            "updates": validated["updates"], "read_fields": read_fields}
```

```python
# 4. New public loader for the independence marker
def requires_independent_agent(skill: str) -> bool:
    """Read the top-level frontmatter flag (not under contract:)."""
    path = _skill_path(skill)
    if not path.exists():
        raise ContractError("skill SKILL.md not found", skill=skill)
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return False
    return bool(data.get("requires_independent_agent", False))
```

- [ ] **Step 4: Run, verify PASS** — `uv run pytest tests/unit/contract/test_dict_reads.py -v` → 3 passed.
- [ ] **Step 5: Regression** — `uv run pytest tests/unit/contract -v` (existing contract tests still pass; `read_fields` added to all returns).
- [ ] **Step 6: Commit** — `git add src/shenbi/contract.py tests/unit/contract/test_dict_reads.py && git commit -m "feat(contract): accept dict-form reads + load requires_independent_agent"`

### Task 0.2: Registry entries for new truth/report files

**Files:** Modify `docs/framework/truth-files.yaml`

- [ ] **Step 1: Add concepts** — under the `truth:` block add:
```yaml
  - {name: truth/resonance_trend.md, kind: truth}
  - {name: truth/arc_payoff_trend.md, kind: truth}
```
Under the audits/foundation block add:
```yaml
  - {name: audits/volume-N-payoff.md, kind: report}   # parametric: N
```
- [ ] **Step 2: Add parametric + glob** — under `patterns:` add:
```yaml
  - {parametric: audits/volume-N-payoff.md, glob: audits/volume-*.md}
```
Under `globs:` add:
```yaml
  - {pattern: audits/volume-*.md}
```
- [ ] **Step 3: Verify resolution** — `uv run python -c "from shenbi.contract import load_registry, resolves; r=load_registry(); assert resolves('truth/resonance_trend.md', r) and resolves('truth/arc_payoff_trend.md', r) and resolves('audits/volume-3-payoff.md', r); print('OK')"`
- [ ] **Step 4: Commit** — `git add docs/framework/truth-files.yaml && git commit -m "feat(registry): add resonance_trend, arc_payoff_trend, volume payoff audit"`

### Task 0.3: G0 check — report-kind ⇒ requires_independent_agent

**Files:** Modify `src/shenbi/gates/g0.py` · Test: `tests/unit/gates/test_g0_independence.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/gates/test_g0_independence.py
from shenbi.gates.g0 import check_independence_markers


def test_report_skill_without_marker_fails():
    skills = {"shenbi-review-foo": {"kind": "report", "has_marker": False}}
    issues = check_independence_markers(skills)
    assert any("shenbi-review-foo" in i for i in issues)


def test_artifact_skill_without_marker_ok():
    skills = {"shenbi-chapter-drafting": {"kind": "artifact", "has_marker": False}}
    assert check_independence_markers(skills) == []


def test_report_skill_with_marker_ok():
    skills = {"shenbi-review-resonance": {"kind": "report", "has_marker": True}}
    assert check_independence_markers(skills) == []
```

- [ ] **Step 2: Run, verify FAIL** — import error (`check_independence_markers`).
- [ ] **Step 3: Implement** in `g0.py`:

```python
from shenbi.contract import OutputKind, load_contract, requires_independent_agent

def check_independence_markers(skills: dict[str, dict]) -> list[str]:
    """G0 sub-check: every report-kind skill must declare requires_independent_agent.

    `skills[skill] = {"kind": OutputKind, "has_marker": bool}` (caller assembles via
    load_contract + requires_independent_agent).
    """
    issues: list[str] = []
    for skill, meta in skills.items():
        if meta["kind"] == OutputKind.REPORT and not meta["has_marker"]:
            issues.append(
                f"G0.independence:{skill}: report-kind skill missing "
                f"'requires_independent_agent: true' (spec §8.1)"
            )
    return issues
```

Wire into `gate_G0` in `src/shenbi/gates/g0.py` as a new **G0.13** block, inserted immediately before the final `return passed("G0", checks)` (after the G0.12 block):

```python
    # G0.13 — independence markers: every report-kind skill must declare
    # requires_independent_agent (spec §8.1). Deterministic frontmatter check.
    from shenbi.contract import (
        load_contract, requires_independent_agent, OutputKind as _OK, ContractError,
    )
    indep_issues: list[str] = []
    for d in SKILLS.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        try:
            c = load_contract(d.name)
        except ContractError:
            continue  # contract issues surface in their own checks
        if c["kind"] == _OK.REPORT and not requires_independent_agent(d.name):
            indep_issues.append(d.name)
    if indep_issues:
        return fail(
            "G0",
            checks + [{"id": "G0.13", "s": "FAIL",
                       "r": f"report skills missing requires_independent_agent: {indep_issues}"}],
            "round_creation",
            ["G0.13: add 'requires_independent_agent: true' to listed skills"],
        )
    checks.append({"id": "G0.13", "s": "PASS", "note": "all report-kind skills declare independence"})
```

Note: `check_independence_markers` (the unit-tested helper) is the pure logic; G0.13 is the wiring that assembles inputs via `load_contract` + `requires_independent_agent` and calls it. Keep the helper tested in isolation (Task 0.3 Step 1) so G0 wiring is thin.

- [ ] **Step 4: Run, verify PASS** — `uv run pytest tests/unit/gates/test_g0_independence.py -v` → 3 passed.
- [ ] **Step 5: Commit** — `git add src/shenbi/gates/g0.py tests/unit/gates/test_g0_independence.py && git commit -m "feat(g0): enforce requires_independent_agent on report-kind skills"`

### Task 0.4: Migrate all existing report-kind skills to declare independence

**Files:** 18× `skills/shenbi-review-*/SKILL.md` + `skills/shenbi-foundation-review/SKILL.md`

This is a deterministic, identical 2-part edit per file. Apply to every file in this list:
`shenbi-review-anti-ai, shenbi-review-character, shenbi-review-continuity, shenbi-review-dialogue, shenbi-review-era, shenbi-review-fanfic, shenbi-review-foreshadowing, shenbi-review-highpoint, shenbi-review-long-span, shenbi-review-memo-compliance, shenbi-review-motivation, shenbi-review-pacing, shenbi-review-pov, shenbi-review-reader-pull, shenbi-review-sensitivity, shenbi-review-spinoff, shenbi-review-texture, shenbi-review-world-rules, shenbi-foundation-review`.

- [ ] **Step 1: Add the frontmatter marker** — in each file, insert `requires_independent_agent: true` on the line immediately after `description:` (before `contract:`).
- [ ] **Step 2: Add the 铁律 line** — in each file's `## 铁律` section, add as item #1:
```
1. **独立评分** — 本 skill 产出评分/审核判断，必须在 context-cleaned 独立 subagent 执行；drafting/planning agent 不得执行本 skill（spec §8.1）
```
(renumber existing items).
- [ ] **Step 3: Verify via G0** — `uv run python -c "from shenbi.contract import load_contract, requires_independent_agent, OutputKind; import pathlib; bugs=[]; [bugs.append(s) for s in (p.name for p in pathlib.Path('skills').iterdir() if p.is_dir()) if (load_contract(s)['kind']==OutputKind.REPORT and not requires_independent_agent(s))]; print('MISSING:', bugs or 'none')"`
- [ ] **Step 4: Commit** — `git add skills/ && git commit -m "feat(skills): declare requires_independent_agent on all report-kind skills"`

> **No `dispatcher/executor.py` change needed.** The dispatcher already runs every skill via a fresh subagent (`codex` / `codex-api` / `internal` modes all start clean-context). `requires_independent_agent` is a **declaration** that (a) G0.13 enforces is present on report-kind skills, and (b) production orchestration (`using-shenbi`) honors in prose. Do not add dispatch-branching code — it would be dead.

### Task 0.5: tropeInventory schema + loader

**Files:** Modify `tests/fixtures/genre-config-example.json` · New `src/shenbi/skill_utils/trope_detection/__init__.py`, `match_tropes.py`, `__main__.py` · Test `tests/unit/skill_utils/test_trope_detection.py`

- [ ] **Step 1: Add tropeInventory to fixture** — in `genre-config-example.json`, add top-level key:
```json
  "tropeInventory": [
    {
      "trope": "废柴逆袭",
      "signatures": ["主角开局被退婚/受辱", "获得金手指(系统/老爷爷/血脉)", "首次展示实力打脸轻视者"],
      "overuse_threshold": 2,
      "rewrite_hint": "淡化金手指的万能性；让首次胜利伴随真实代价"
    },
    {
      "trope": "天降系统",
      "signatures": ["脑海中出现系统面板", "任务-奖励循环驱动行为", "系统解释一切机制"],
      "overuse_threshold": 1,
      "rewrite_hint": "将部分机制来源改为世界内生规则，减少系统直接喂饭"
    }
  ],
```
- [ ] **Step 2: Write failing test**

```python
# tests/unit/skill_utils/test_trope_detection.py
from shenbi.skill_utils.trope_detection.match_tropes import Trope, count_trope_hits, trope_overuse


def test_count_hits_matches_signature_keywords():
    t = Trope("废柴逆袭", ["主角开局被退婚", "获得金手指"], 2, "淡化")
    beats = ["主角开局被退婚，未婚妻当众悔婚", "主角获得金手指老爷爷", "主角吃了一碗面"]
    assert count_trope_hits(beats, t) == 2


def test_overuse_flagged_above_threshold():
    t = Trope("天降系统", ["系统面板", "任务奖励"], 1, "改")
    assert trope_overuse(2, t) is True
    assert trope_overuse(1, t) is False
```

- [ ] **Step 3: Run, verify FAIL.**
- [ ] **Step 4: Implement**

```python
# src/shenbi/skill_utils/trope_detection/match_tropes.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Trope:
    trope: str
    signatures: list[str]
    overuse_threshold: int
    rewrite_hint: str

def count_trope_hits(beats: list[str], trope: Trope) -> int:
    """Count story beats that match any signature (keyword substring match).

    NOTE: production uses LLM semantic matching in the scoring agent; this
    deterministic helper supports the trope-detection unit test (spec §10)
    and the fixture validation. Keyword match is the testable proxy.
    """
    hits = 0
    for beat in beats:
        if any(sig in beat for sig in trope.signatures):
            hits += 1
    return hits

def trope_overuse(hit_count: int, trope: Trope) -> bool:
    return hit_count > trope.overuse_threshold
```

Add `__init__.py` (re-export) and `__main__.py` (CLI: `uv run python -m shenbi.skill_utils.trope_detection --config genre-config.json --beats-file beats.txt`).

- [ ] **Step 5: Run, verify PASS.**
- [ ] **Step 6: Commit** — `git commit -m "feat(trope-detection): tropeInventory schema + match helper"`

### Task 0.6: Calibration fixture scaffolding + hash lock (NEW G0.14)

**Files:** `tests/fixtures/calibration/README.md` + `.gitkeep`s · Modify `src/shenbi/gates/g0.py` · `tests/tiers/deps.json`

> **Correction (from reading g0.py):** G0.11 only hashes explicit `mirror_map` pairs (e.g. `outline-example.md`↔source) — it does **not** cover arbitrary fixtures. So calibration anchors get a **new G0.14** check with its own hash lock (mirrors the existing `_tool_hashes` pattern in deps.json), not G0.11.

- [ ] **Step 1: Create README** documenting the anchor schema: each file = `## excerpt` + `## expected_band` + `## rationale`; 3 anchors (high/mid/low) per dimension.
- [ ] **Step 2: Add G0.14 to `gate_G0`** (before final return, after G0.13): compute a combined SHA256 over every file under `tests/fixtures/calibration/**`, compare to `deps.json._calibration_hashes.combined`; FAIL on mismatch (detects anchor tampering / drift). TDD: `tests/unit/gates/test_g0_calibration_hash.py` — tamper an anchor → FAIL; restore → PASS; missing lock entry → FAIL with "run lock script".
- [ ] **Step 3: Extend `tests/lock-tool-hashes.sh`** to also compute & write `_calibration_hashes` into deps.json (re-run after authoring anchors in Phase 2/3, and whenever anchors change).
- [ ] **Step 4: Commit** — `git commit -m "feat(calibration): scaffolding + G0.14 hash lock"`

---

## Phase 1 — C: foundation-review anti-trope dimension

Depends on Phase 0 (tropeInventory). Small; validates the pattern.

### Task 1.1: Modify foundation-review SKILL.md (rebalance + 反套路维度)

**Files:** Modify `skills/shenbi-foundation-review/SKILL.md`

- [ ] **Step 1: Rebalance the 5-dimension table to 6** — replace the weights per spec §7.2: 核心冲突 30→25 (floor 18→15), 角色区分度 20→15, add 反套路/原创性 10. Add the rationale note (spec §7.2 再平衡 rationale).
- [ ] **Step 2: Add the dimension scoring subsection** — scoring worksheet rows for 反套路/原创性:
```markdown
### 六、反套路/原创性（满分10）

| 评分项 | 满分 | 得分 | 证据引用 | 裁判理由 |
|--------|------|------|---------|---------|
| 套路依赖度（核心节拍对照 genre-config.tropeInventory，命中数 ≤ overuse_threshold） | 5 | X | [文件:段落] | [≤1句] |
| 反转/新颖度（核心设定存在 ≥1 处对题材套路的颠覆或新颖组合） | 5 | X | [文件:段落] | [≤1句] |
| **小计** | **10** | **XX** | | |
```
- [ ] **Step 3: Add scoring procedure** — "读取 `genre-config.json` 的 `tropeInventory`，将 `outline/story_frame.md` 的弧节拍对照每个套路的 `signatures`；命中数 > `overuse_threshold` → 套路依赖度扣分，并列出命中的节拍 + `rewrite_hint`。"
- [ ] **Step 4: Update 总评 table** to 6 rows summing 100; keep ≥80 floor, 核心冲突 ≥15 sub-floor.
- [ ] **Step 5: Update the T1 rubric** `tests/tiers/t1-skill/shenbi-foundation-review/rubric.md` bespoke dimensions to reflect the 6-dim rubric.
- [ ] **Step 6: Run G2/G4 + commit** — `git commit -m "feat(foundation-review): add 反套路/原创性 dimension, rebalance to 6 dims"`

> **Note:** Rebalancing 30→25 / 20→15 invalidates prior `foundation-review` T1 scores (the rubric changed). Re-score foundation-review in the next test round; do not carry over old scores.

---

## Phase 2 — A: shenbi-review-resonance (the core)

Depends on Phase 0 + 1. Largest phase.

### Task 2.1: Drift detection util (smoothing + triggers)

**Files:** New `src/shenbi/skill_utils/drift_detection/__init__.py`, `compute_drift.py`, `__main__.py` · Test `tests/unit/skill_utils/test_drift_detection.py`

- [ ] **Step 1: Write failing tests** (per spec §8.3 triggers + §10 drift-trigger test)

```python
# tests/unit/skill_utils/test_drift_detection.py
from shenbi.skill_utils.drift_detection.compute_drift import (
    smooth, detect_chapter_drift, detect_volume_drift, DriftFinding
)

def test_smooth_3_point_window():
    assert smooth([10.0, 10.0, 7.0, 7.0, 7.0]) == [10.0, 9.0, 8.0, 7.0, 7.0]

def test_smooth_boundary_2_point():
    # first/last use 2-point (self + sole neighbor)
    assert smooth([10.0, 12.0]) == [11.0, 11.0]

def test_chapter_drift_monotonic_decline_triggers():
    scores = [24.0, 23.0, 21.0, 18.0]  # smoothed: ~24, 22.67, 20.67, 18.0 — monotonic decline ≥3
    f = detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6)
    assert any(f.kind == "monotonic_decline" for f in f)

def test_chapter_drift_sigma_requires_min_samples():
    scores = [24.0, 10.0]  # only 2 samples — sigma trigger must NOT fire
    f = detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6)
    assert all(f.kind != "below_mean_2sigma" for f in f)

def test_chapter_drift_stable_series_no_trigger():
    scores = [22.0]*8
    assert detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6) == []

def test_volume_drift_two_volume_decline_triggers():
    assert len(detect_volume_drift([82.0, 74.0])) == 1   # consecutive 2-volume decline
    assert detect_volume_drift([74.0, 82.0]) == []


def test_chapter_drift_human_overridden_excluded():
    # spec §8.3: human_overridden chapters excluded from trigger stats.
    # Chapter index 2 overridden -> must break the decline run (no false trigger),
    # even though the raw series would otherwise fire monotonic_decline.
    scores = [24.0, 23.0, 21.0, 18.0]
    assert detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6,
                                exclude_indices={2}) == []
    # and without exclusion it DOES fire (sanity):
    assert detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6) != []
```

- [ ] **Step 2: Run, verify FAIL.**
- [ ] **Step 3: Implement**

```python
# src/shenbi/skill_utils/drift_detection/compute_drift.py
from __future__ import annotations
import statistics
from dataclasses import dataclass
from enum import StrEnum

class DriftKind(StrEnum):
    MONOTONIC_DECLINE = "monotonic_decline"
    BELOW_MEAN_2SIGMA = "below_mean_2sigma"
    VOLUME_DECLINE = "volume_decline"

@dataclass(frozen=True)
class DriftFinding:
    kind: DriftKind
    dim: str
    detail: str

def smooth(scores: list[float]) -> list[float]:
    """3-point moving average; 2-point at boundaries."""
    n = len(scores)
    if n == 0:
        return []
    if n == 1:
        return [scores[0]]
    out = [(scores[0] + scores[1]) / 2]
    for i in range(1, n - 1):
        out.append((scores[i - 1] + scores[i] + scores[i + 1]) / 3)
    out.append((scores[n - 2] + scores[n - 1]) / 2)
    return out

def detect_chapter_drift(
    raw: list[float], dim: str, min_samples_sigma: int = 6,
    exclude_indices: set[int] | None = None,
) -> list[DriftFinding]:
    """spec §8.3. exclude_indices = chapters flagged human_overridden (excluded
    from trigger stats so overrides don't poison detection)."""
    excl = exclude_indices or set()
    s = smooth(raw)
    findings: list[DriftFinding] = []
    # (a) monotonic decline ≥3 consecutive non-excluded, cumulative ≥3
    run, start, prev = 0, 0, None
    for i, v in enumerate(s):
        if i in excl:
            run, start, prev = 0, i + 1, None
            continue
        if prev is not None and v < prev:
            run += 1
        else:
            run, start = 1, i
        prev = v
        if run >= 3 and (s[start] - v) >= 3:
            findings.append(DriftFinding(DriftKind.MONOTONIC_DECLINE, dim,
                f"{dim} declined {s[start]:.1f}->{v:.1f} over chapters {start+1}-{i+1}"))
            break
    # (b) below mean − 2σ over non-excluded, ≥2 consecutive non-excluded
    kept = [v for i, v in enumerate(s) if i not in excl]
    if len(kept) >= min_samples_sigma:
        mean = statistics.mean(kept)
        sd = statistics.pstdev(kept) or 1e-9
        below_run = 0
        for i, v in enumerate(s):
            if i in excl:
                below_run = 0
                continue
            if v < mean - 2 * sd:
                below_run += 1
                if below_run >= 2:
                    findings.append(DriftFinding(DriftKind.BELOW_MEAN_2SIGMA, dim,
                        f"{dim} < mean-2σ ({mean-2*sd:.1f}) for ≥2 consecutive chapters"))
                    break
            else:
                below_run = 0
    return findings

def detect_volume_drift(volume_scores: list[float]) -> list[DriftFinding]:
    if len(volume_scores) >= 2 and volume_scores[-1] < volume_scores[-2]:
        return [DriftFinding(DriftKind.VOLUME_DECLINE, "overall",
            f"volume overall declined {volume_scores[-2]}->{volume_scores[-1]}")]
    return []
```

Add `__init__.py` (re-export) and `__main__.py`. The CLI reads `truth/resonance_trend.md` and `truth/arc_payoff_trend.md` (see **Trend file format** below), prints `DriftFinding`s, and with `--write-audit-drift` appends them to `truth/audit_drift.md`. Exit code: non-zero if any finding (so drift-guidance / CI can gate on it).

**Trend file format (machine-parseable — the contract between SKILL.md writers and the drift CLI):**

`truth/resonance_trend.md` — one markdown table row per chapter (the SKILL.md `### 趋势` section appends here):
```
| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |
| 1 | 高潮 | 22 | 20 | 18 | 15 | 75 | high |  |
| 2 | 过渡 | 14 | 18 | 20 | 13 | 65 | mid |  |
| 3 | 高潮 | 12 | 16 | 18 | 10 | 56 | high | true |
```

`truth/arc_payoff_trend.md` — one row per volume:
```
| volume | 弧情感交付 | 伏笔兑现质量 | 线索收束 | 期待债务结算 | 角色弧推进 | overall |
| 1 | 20 | 22 | 16 | 12 | 13 | 83 |
```

Parser (`compute_drift.parse_trend(path, dims) -> dict[dim, list[(score, excluded)]]`): read the table, map header→column, collect per-dimension score lists + the `human_overridden` flag → `exclude_indices`. **Rows with non-numeric scores (e.g. `overall = pending` from a failed dispatch, spec §9 / Task 4.3 Step 2b) are skipped** — not coerced, not counted toward sample N (so a pending chapter doesn't corrupt σ). Unit-test the parser against the above fixtures (`tests/unit/skill_utils/test_drift_detection.py`: add `test_parse_resonance_trend_excludes_overridden` + `test_parse_skips_pending_rows`).

- [ ] **Step 4: Run, verify PASS** — all 6 tests green.
- [ ] **Step 5: Commit** — `git commit -m "feat(drift-detection): smoothing + chapter/volume drift triggers"`

### Task 2.2: Confidence calibration util

**Files:** `src/shenbi/skill_utils/calibration/__init__.py`, `confidence.py`, `__main__.py` · Test `tests/unit/skill_utils/test_calibration.py`

- [ ] **Step 1: Failing test**

```python
from shenbi.skill_utils.calibration.confidence import calibrate_confidence, HitRate

def test_high_confidence_downgraded_when_anchor_hitrate_low():
    # scorer reported "high" but only hit 60% of anchors it judged high → downgrade to mid
    assert calibrate_confidence("high", HitRate(high_confidence=0.6, threshold=0.8)) == "mid"

def test_high_confidence_kept_when_hitrate_ok():
    assert calibrate_confidence("high", HitRate(high_confidence=0.9, threshold=0.8)) == "high"

def test_low_never_upgraded():
    assert calibrate_confidence("low", HitRate(high_confidence=0.99, threshold=0.8)) == "low"
```

- [ ] **Step 2: Run FAIL.**
- [ ] **Step 3: Implement**

```python
# src/shenbi/skill_utils/calibration/confidence.py
from dataclasses import dataclass

@dataclass(frozen=True)
class HitRate:
    high_confidence: float   # fraction of high-confidence anchor judgments that were correct
    threshold: float = 0.8

def calibrate_confidence(reported: str, hr: HitRate) -> str:
    """LLM scorers are overconfident. Downgrade 'high' → 'mid' when anchor hit-rate < threshold.
    Never upgrade. (spec §8.2 置信度校准)"""
    if reported == "high" and hr.high_confidence < hr.threshold:
        return "mid"
    return reported
```

- [ ] **Step 4: PASS · Step 5: Commit** — `feat(calibration): confidence downgrade by anchor hit-rate`

### Task 2.3: Block routing util (3-path + revision cap)

**Files:** `src/shenbi/skill_utils/review_resonance/__init__.py`, `routing.py`, `__main__.py` · Test `tests/unit/skill_utils/test_routing.py`

- [ ] **Step 1: Failing test**

```python
from shenbi.skill_utils.review_resonance.routing import route_block, Routing, RevisionLoop

def test_clear_pass_when_above_threshold():
    r = route_block(overall=82, threshold=75, floors={"情感落地": (22, 20)},
                    confidence="high", prior_revisions=0)
    assert r.path is Routing.PASS

def test_clear_fail_auto_revise():
    r = route_block(overall=40, threshold=75, floors={}, confidence="high", prior_revisions=0)
    assert r.path is Routing.AUTO_REVISE

def test_borderline_goes_to_human():
    r = route_block(overall=73, threshold=75, floors={}, confidence="high", prior_revisions=0)  # within ±5
    assert r.path is Routing.HUMAN_REVIEW

def test_low_confidence_goes_to_human():
    r = route_block(overall=40, threshold=75, floors={}, confidence="low", prior_revisions=0)
    assert r.path is Routing.HUMAN_REVIEW

def test_third_clear_fail_escalates_to_human():
    r = route_block(overall=40, threshold=75, floors={}, confidence="high", prior_revisions=2)
    assert r.path is Routing.HUMAN_REVIEW   # cap reached, no more auto-revise
```

- [ ] **Step 2: Run FAIL.**
- [ ] **Step 3: Implement**

```python
# src/shenbi/skill_utils/review_resonance/routing.py
from dataclasses import dataclass
from enum import StrEnum

class Routing(StrEnum):
    PASS = "pass"
    AUTO_REVISE = "auto_revise"
    HUMAN_REVIEW = "human_review"

MAX_AUTO_REVISIONS = 2

def route_block(overall: float, threshold: float, floors: dict[str, tuple[float, float]],
                confidence: str, prior_revisions: int) -> Routing:
    """spec §5.4 three-path routing + 2-revision cap."""
    floor_ok = all(score >= floor for score, floor in floors.values())
    if overall >= threshold and floor_ok:
        return Routing.PASS
    # blocked below
    near_threshold = abs(overall - threshold) <= 5
    if confidence == "low" or near_threshold:
        return Routing.HUMAN_REVIEW
    # high confidence, clearly below (>5 under threshold)
    if prior_revisions >= MAX_AUTO_REVISIONS:
        return Routing.HUMAN_REVIEW     # cap → escalate
    return Routing.AUTO_REVISE
```

- [ ] **Step 4: PASS · Step 5: Commit** — `feat(routing): 3-path block routing + revision cap`

### Task 2.4: chapter-planning SKILL.md — add `chapter_role` field

**Files:** Modify `skills/shenbi-chapter-planning/SKILL.md`

- [ ] **Step 1:** In the chapter memo template (the 8-段式), add a required `chapter_role` field with allowed values `高潮/兑现 | 推进/转折 | 过渡/铺垫`. Place it in section 1 (本章核心任务) as a leading tag. Add a 铁律 line: "每个备忘必须声明 chapter_role，驱动 review-resonance 校准阈值（spec §5.1）".
- [ ] **Step 2: Update G4 checker** `src/shenbi/gates/g4/chapter_planning.py` to require the `chapter_role` token. TDD:

```python
# tests/unit/gates/g4/test_chapter_planning_role.py
def test_plan_without_chapter_role_fails_g4(tmp_path):
    plan = tmp_path / "plans/chapter-1-plan.md"; plan.parent.mkdir(parents=True)
    plan.write_text("# plan\n## 1. 核心任务\n...\n", encoding="utf-8")  # no chapter_role
    assert "FAIL" in g4_chapter_planning([str(plan)], None)

def test_plan_with_chapter_role_passes(tmp_path):
    plan = tmp_path / "plans/chapter-1-plan.md"; plan.parent.mkdir(parents=True)
    plan.write_text("# plan\nchapter_role: 高潮\n## 1. 核心任务\n...\n", encoding="utf-8")
    assert "PASS" in g4_chapter_planning([str(plan)], None)
```
Impl: in `g4_chapter_planning`, add a regex check `re.search(r"chapter_role\s*[:：]\s*(高潮|兑现|推进|转折|过渡|铺垫)", content)`; append `G4.cp.missing_chapter_role` on miss.
- [ ] **Step 3: Commit** — `feat(chapter-planning): emit chapter_role for resonance calibration`

### Task 2.5: chapter-drafting SKILL.md — PRE_WRITE_CHECK +共鸣短板

**Files:** Modify `skills/shenbi-chapter-drafting/SKILL.md`

- [ ] **Step 1:** In the PRE_WRITE_CHECK template, add a line `- 共鸣短板（读 truth/audit_drift）: [本章重点防范的体验轴短板]`. Update the output-format block identically.
- [ ] **Step 2: Update G2.8** is a substring check on `## PRE_WRITE_CHECK` — still passes. No gate change needed.
- [ ] **Step 3: Commit** — `feat(chapter-drafting): PRE_WRITE_CHECK reads resonance shortcomings`

### Task 2.6: Author review-resonance SKILL.md (full content)

**Files:** Create `skills/shenbi-review-resonance/SKILL.md`

- [ ] **Step 1: Write the SKILL.md** — full content per spec §5. Frontmatter (corrected per R1/R2 — anchors NOT in reads, dict-form reads for fields):

```yaml
---
name: shenbi-review-resonance
description: "Use when a finished chapter needs a positive quality score on emotional landing, presence, prose craft, and reader reward — runs in an independent agent"
requires_independent_agent: true
contract:
  kind: report
  reads:
    - {file: chapters/chapter-N.md, fields: [prose, POST_WRITE_SELF_CHECK]}
    - {file: plans/chapter-N-plan.md, fields: [chapter_role, core_task]}
    - {file: style/style_profile.md, fields: [voice_fingerprint]}
  writes:
    - audits/chapter-N-resonance.md
  updates:
    - truth/audit_drift.md
    - truth/resonance_trend.md
---
```

Body sections (per spec §5): HARD-GATE (no scoring without a chapter + plan); 铁律 (独立评分 anchor-first, 先确定性, show-not-tell evidence, confidence必报); 流程 DOT graph (read → load anchors → score 4 dims → route via §5.4 → write report + trend); 评分维度表 (§5.2); 校准门逻辑 (§5.3, read `chapter_role` → threshold); 置信度守护与分流 (§5.4 three-path table + revision cap); 输出格式 (§5.5 full template); 与现有负向门边界 (§5.6); Anti-Rationalization table; 缺陷证据格式 (4-element). The prose references `tests/fixtures/calibration/resonance/*.md` anchors (scorer input, not contract).

- [ ] **Step 2: Verify contract loads** — `uv run python -c "from shenbi.contract import load_contract; print(load_contract('shenbi-review-resonance'))"`
- [ ] **Step 3: Commit** — `feat(review-resonance): add skill`

### Task 2.7: G4 checker for review-resonance

**Files:** New `src/shenbi/gates/g4/review_resonance.py` · Modify `src/shenbi/gates/g4/generic.py` · Test `tests/unit/gates/g4/test_review_resonance.py`

- [ ] **Step 1: Failing test**

```python
# tests/unit/gates/g4/test_review_resonance.py
from pathlib import Path
from shenbi.gates.g4.review_resonance import g4_review_resonance

VALID = """# 共鸣评分报告
## 评分明细
| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |
| 情感落地 | 22 | 30 | high | `c.md` L45 | show |
## 校准门判定
判定: 通过
"""

def test_valid_report_passes(tmp_path):
    f = tmp_path / "audits/chapter-1-resonance.md"; f.parent.mkdir(parents=True)
    f.write_text(VALID, encoding="utf-8")
    assert "PASS" in g4_review_resonance([str(f)], None)

def test_missing_confidence_column_fails(tmp_path):
    f = tmp_path / "audits/chapter-1-resonance.md"; f.parent.mkdir(parents=True)
    f.write_text("# 共鸣评分报告\n## 评分明细\n| 维度 | 得分 |\n| x | 10 |\n", encoding="utf-8")
    assert "FAIL" in g4_review_resonance([str(f)], None)
```

- [ ] **Step 2: Run FAIL.**
- [ ] **Step 3: Implement** — validate the report has: 评分明细 table with columns (维度/得分/满分/置信度/证据/裁判理由), 校准门判定 section with a 判定 line (通过/阻断/待人机复核), evidence with file+line refs. Use regex checks analogous to `g4_generic_bughunt`.
- [ ] **Step 4: Register in router** — in `generic.py` `gate_G4`, add to the late-imports + checkers dict: `"shenbi-review-resonance": g4_review_resonance`. **Also** add `shenbi-review-resonance` to `G4_CHECKER_SKILLS` in `src/shenbi/gates/shared.py` (keeps G0.12 coverage accounting correct).
- [ ] **Step 5: PASS · Step 6: Commit** — `feat(g4): review-resonance checker`

### Task 2.8: drift-guidance SKILL.md — read trends, run drift triggers

**Files:** Modify `skills/shenbi-drift-guidance/SKILL.md`

- [ ] **Step 1:** Add a flow step: "读取 `truth/resonance_trend.md` 与 `truth/arc_payoff_trend.md`，调用 `python -m shenbi.skill_utils.drift_detection` 得到 DriftFinding，将 findings 写入 `truth/audit_drift.md`（逐章纠偏 + 卷级纠偏）". Reference the trigger definitions in spec §8.3 (do not redefine).
- [ ] **Step 2: Commit** — `feat(drift-guidance): consume resonance/arc trends, emit drift findings`

### Task 2.9: Calibration anchor fixtures (resonance, 4 dims × 3 levels)

**Files:** `tests/fixtures/calibration/resonance/{情感落地,场景临场感,文笔质感,读者回报}/{high,mid,low}.md`

- [ ] **Step 1:** Author 12 anchor files per the Phase 0.6 schema. Each: a real ~150-word prose excerpt + `expected_band` (e.g., 情感落地 high → 24-30) + rationale. These are human-curated (spec §8.2 bootstrap). The high/mid/low must be clearly distinguishable on that dimension.
- [ ] **Step 2: Verify hash** — G0.11 covers them.
- [ ] **Step 3: Commit** — `feat(calibration): resonance anchor fixtures (4 dims × 3 levels)`

### Task 2.10: T1 test dir for review-resonance

**Files:** `tests/tiers/t1-skill/shenbi-review-resonance/{rubric.md, generative/input/scenario.md, bug-hunt/input/scenario.md, bug-hunt/expected/expected-output.md, clean/input/scenario.md, clean/expected/expected-output.md}`

- [ ] **Step 1: Rubric** per the `_template/rubric.md` structure: Universal 15% (adherence 10%, completeness 5%) + Bespoke 85% covering: 4-dim scoring quality (40%), evidence rigor/file+line (20%), confidence+routing correctness (15%), gate-decision correctness (10%). Bug-hunt kill switch: missed planted resonance flaw → 0; misclassified as anti-ai → 0. Clean kill switch: hallucinated deduction → 0.
- [ ] **Step 2: generative scenario** — a fixture chapter + plan + style_profile + genre-config; skill must produce a scored report.
- [ ] **Step 3: bug-hunt scenario** — inject a resonance-specific flaw (spec §10: 欠交付/压平高潮/无回报 — NOT an anti-ai tell); expected output = the flaw located + score dropped.
- [ ] **Step 4: clean scenario** — strong chapter; expected = high scores, zero deductions.
- [ ] **Step 5: Commit** — `feat(t1): review-resonance test dir`

### Task 2.11: Unit tests for the new deterministic test-types (spec §10)

**Files:** `tests/unit/skill_utils/test_drift_triggers_integration.py`, `tests/unit/skill_utils/test_confidence_routing_integration.py`, `tests/unit/skill_utils/test_trope_detection.py` (extended)

- [ ] **Step 1:** Integration tests that exercise the full drift-trigger path (trend fixture → `detect_chapter_drift` → findings match spec §8.3 positive/negative cases), the confidence→routing path (high+low-hitrate → mid → routing changes AUTO_REVISE→HUMAN_REVIEW), and trope overuse detection. These are the §10 "漂移触发/置信度校准/套路检测" tests.
- [ ] **Step 2: Commit** — `test: deterministic-logic integration for resonance`

---

## Phase 3 — B: shenbi-review-arc-payoff

Depends on Phase 2 (shares calibration/routing/independence pattern + reads `resonance_trend`).

### Task 3.1: Author review-arc-payoff SKILL.md

**Files:** Create `skills/shenbi-review-arc-payoff/SKILL.md`

- [ ] **Step 1: Write SKILL.md** per spec §6. Frontmatter (R1/R2 corrected):

```yaml
---
name: shenbi-review-arc-payoff
description: "Use at a volume/arc boundary to gate advancement on arc emotional delivery, foreshadowing payoff quality, thread resolution, expectation-debt settlement, and character arc — runs in an independent agent"
requires_independent_agent: true
contract:
  kind: report
  reads:
    - chapters/*.md                       # narrowed to arc range in prose
    - {file: outline/volume_map.md, fields: [volume_promise, arc_beats]}
    - {file: truth/pending_hooks.md, fields: [resolved_this_arc, carried_forward]}
    - truth/resonance_trend.md            # §6.3 弧情感交付佐证
  writes:
    - audits/volume-N-payoff.md
  updates:
    - truth/audit_drift.md
    - truth/arc_payoff_trend.md
---
```

Body: HARD-GATE (前置: 弧内章节全部 resonance 通过); 铁律; 流程 (read arc chapters + trends → score 5 dims → gate); 评分维度表 (§6.3 incl. 期待债务结算 Chase-Power logic + resonance_trend 用途 note); 门逻辑 (§6.4: ≥80 且 伏笔兑现质量≥15); 输出格式; Anti-Rationalization; 证据格式.

- [ ] **Step 2: Verify contract** — `uv run python -c "from shenbi.contract import load_contract; print(load_contract('shenbi-review-arc-payoff'))"`
- [ ] **Step 3: Commit** — `feat(review-arc-payoff): add skill`

### Task 3.2: G4 checker for review-arc-payoff + register

**Files:** New `src/shenbi/gates/g4/review_arc_payoff.py` · Modify `generic.py` · Test

- [ ] **Step 1:** TDD + implement, analogous to Task 2.7 (validate 5-dim table + 门判定 + 伏笔兑现质量 sub-floor). Register `"shenbi-review-arc-payoff": g4_review_arc_payoff`.
- [ ] **Step 2: Commit** — `feat(g4): review-arc-payoff checker`

### Task 3.3: volume-consolidation SKILL.md — invoke B at boundary

**Files:** Modify `skills/shenbi-volume-consolidation/SKILL.md`

- [ ] **Step 1:** Add flow step: "卷 consolidation 完成后，触发 `shenbi-review-arc-payoff`（独立 agent）。B 未通过（<80 或 伏笔兑现质量<15）→ 阻断下一卷推进，按处方修订。"
- [ ] **Step 2: Commit** — `feat(volume-consolidation): invoke arc-payoff gate at boundary`

### Task 3.4: Calibration anchor fixtures (arc-payoff, 5 dims × 3 levels)

**Files:** `tests/fixtures/calibration/arc-payoff/{弧情感交付,伏笔兑现质量,线索收束,期待债务结算,角色弧推进}/{high,mid,low}.md`

- [ ] **Step 1:** 15 anchor files. For 伏笔兑现质量: high = surprising+earned payoff excerpt; low = perfunctory payoff excerpt. Commit.

### Task 3.5: T1 test dir for review-arc-payoff

**Files:** `tests/tiers/t1-skill/shenbi-review-arc-payoff/{rubric.md, generative|bug-hunt|clean/...}`

- [ ] **Step 1:** Mirror Task 2.10 structure. bug-hunt injects a perfunctory-payoff flaw (not an anti-ai tell). Commit.

### Task 3.6: Cross-volume drift macro-trigger test

**Files:** `tests/unit/skill_utils/test_volume_drift_macro.py`

- [ ] **Step 1:** Fixture `arc_payoff_trend` sequences: declining (82→74→68) → assert `detect_volume_drift` fires + would block next volume per §8.3 macro trigger; stable → no fire. Commit.

---

## Phase 4 — Integration & framework wiring

### Task 4.1: deps.json — register A/B

**Files:** Modify `tests/tiers/deps.json`

- [ ] **Step 1:** Add `shenbi-review-resonance` to the `drafting` t2-phase prerequisites (after `shenbi-style-polishing`); add `shenbi-review-arc-payoff` to a `consolidation` phase (or `drafting` volume-boundary) prerequisites. If no consolidation phase exists, add A/B to `_out_of_pipeline` with a note, and ensure the T2/T3 fixtures reference them at the right stage.
- [ ] **Step 2: Commit** — `feat(deps): register review-resonance + review-arc-payoff`

### Task 4.2: Regenerate contracts / DAG

- [ ] **Step 1:** `uv run shenbi-validate` contract sync (or `uv run python -m shenbi.sync_contracts`) to regenerate `docs/framework/dependency-dag.json` including A/B edges.
- [ ] **Step 2:** Verify no contract-completeness lint errors (`just check`).
- [ ] **Step 3: Commit** — `chore(contracts): regenerate DAG with A/B`

### Task 4.3: using-shenbi trigger map + audit activation

**Files:** Modify `skills/using-shenbi/SKILL.md`

- [ ] **Step 1:** Add to the Skill Trigger Map: 「共鸣评分」/「正向质量」/「这章写得好不好」 → `shenbi-review-resonance`; 「卷质量」/「整卷交付」/「伏笔兑现」 → `shenbi-review-arc-payoff`.
- [ ] **Step 2:** Add resonance + arc-payoff to the default audit activation list (resonance per-chapter default-on; arc-payoff at volume boundary).
- [ ] **Step 2b:** Document the `resonance_pending` dispatch-failure path (spec §9): if `review-resonance` dispatch fails (timeout/error after provider retry), the orchestrator marks the chapter `resonance_pending` in `truth/resonance_trend.md` (a row with overall = `pending`), does **not** block `chapter-drafting` of the next chapter, and queues re-evaluation. Add this as a 铁律/flow note in `using-shenbi`. (No code — orchestration behavior; the trend parser in Task 2.1 must treat `pending` rows as non-numeric/skip.)
- [ ] **Step 3: Commit** — `feat(using-shenbi): trigger map + audit activation for positive gates`

### Task 4.4: Re-lock tool hashes + full G0

- [ ] **Step 1:** Tool files changed (`contract.py`, `g0.py`, `g4/*`, `skill_utils/*`) → run `bash tests/lock-tool-hashes.sh` to update `deps.json._tool_hashes`.
- [ ] **Step 2:** `uv run shenbi-validate G0 <seed>` (via `bash tests/round-exec.sh claude T1`) — confirm G0 PASS including the new G0.independence check.
- [ ] **Step 3:** `just check` (ruff + mypy + pytest, 80% branch / 90% line coverage).
- [ ] **Step 4: Commit** — `chore: re-lock tool hashes; G0 green with positive gates`

---

## Self-Review (run after writing — findings already folded in above)

**1. Spec coverage:** Every spec section maps to a task — §5→Tasks 2.1-2.11; §6→3.1-3.6; §7→1.1; §8.1→0.1/0.3/0.4; §8.2→0.6/2.2/2.9/3.4; §8.3→2.1/2.8/3.6; §8.4→0.5/1.1; §8.5→2.4/2.5/2.8/3.3/0.4; §9→2.3 + the §9 rows are behavior, validated via tests; §10→2.10/2.11/3.5/3.6 + calibration tests; §11/12/13→covered by structure. **Two spec corrections (R1/R2) documented at top — these override the spec's frontmatter sketches.**

**2. Placeholder scan:** No "TBD/TODO". Migrations (Task 0.4) are a precise batch edit with explicit file list + identical edit (not a placeholder — it's a deterministic operation). Fixture authoring (2.9/3.4) specifies exact schema + dimension/level matrix; prose content is legitimately creative test-data, not a plan gap.

**3. Type consistency:** `Routing` enum, `DriftFinding`/`DriftKind`, `Trope`, `HitRate` defined once and reused across tasks/tests. `route_block` signature consistent in test + impl. `requires_independent_agent` loader signature consistent.

**Open items deferred to execution (legitimate, not placeholders):**
- Exact regex patterns in G4 checkers (2.7/3.2) follow the established `g4_generic_bughunt` pattern; final patterns tuned against real outputs during T1.
- Anchor fixture prose content (2.9/3.4) is human-curated creative data per spec §8.2 bootstrap.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-22-positive-quality-gates.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for a plan this size (4 phases, ~25 tasks).

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach? (Phase 0 first regardless — it unblocks everything and validates the contract/gate integration before authoring skills.)
