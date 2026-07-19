# Spec 18: Configuration Coherence and Threshold Governance Design

> **Date:** 2026-07-19
> **Status:** Design
> **Severity:** Critical
> **Source:** Systematic debugging Phase 1 evidence (E11, E34)
> **Consolidated from findings:**
> - E11: Config `resonance_global_floor=50` contradicts the 65 floor enforced inside resonance audit skills
> - E34: genre-config `texture` dimension disabled — the audit that would catch prose degradation was turned off

---

## 1. Executive Summary

Two configuration-level defects created blind spots that allowed quality degradation to go undetected:

1. **Threshold contradiction (E11):** `genre-config.json` sets `resonance_global_floor: 50`, but the resonance audit skill's internal gate enforces a 65 floor. This mismatch means chapters scoring 50-64 pass the state-level gate while the audit skill considers them failures. Three chapters (Ch50=51, Ch53=52, Ch54=64) scored below the 65 audit floor but above the 50 config floor, so they were neither revised nor flagged — they silently degraded.

2. **Safety-net disabled (E34):** `genre-config.json` has `auditDimensions.texture: false`. The `review-texture` audit is the primary detector of prose degradation (sensory detail, scene concreteness, environmental texture). Disabling it removed the only automated safety net that would have caught the system-term density explosion (Spec 4 E21/E22). This is the **root-cause explanation** for why prose collapse went undetected for 26 chapters.

**Root cause:** There is no configuration validation layer. Thresholds are defined in multiple places (config, skill prompts, gate code) with no single-source-of-truth enforcement. Audit dimensions can be disabled without warning about the quality-safety implications.

---

## 2. Root Cause Analysis

### 2.1 Threshold Drift Between Config and Code (E11)

The resonance scoring system has floors defined in at least two places:
- `genre-config.json` → `resonance_global_floor: 50` (used by pipeline state for routing decisions)
- `shenbi-review-resonance` SKILL.md → internal calibration gate uses 65 (used by the audit skill for pass/fail verdicts)
- `gates/g4/review_resonance.py` → verdict validation (checks format, not numeric threshold)

When the state machine reads `resonance_global_floor: 50` and sees a score of 52, it passes. But the audit skill considers 52 a failure (below its 65 internal floor). The chapter is not revised. This is a **silent quality erosion pathway** — the config is too lenient relative to the skill's own quality standard.

**Evidence:** Ch50 (score 51), Ch53 (score 52) passed the state's 50-floor gate but contain degenerate "参数宣告" prose. The audit files themselves note the quality problem but the routing logic didn't act.

### 2.2 Disabled Audit Dimension (E34)

`genre-config.json` → `auditDimensions.texture: false`. The `texture` audit (`shenbi-review-texture`) evaluates:
- 感官细节 (sensory detail)
- 场景临场感 (scene concreteness)
- 环境肌理 (environmental texture)

These are **exactly** the dimensions that collapse during prose degradation (Spec 4 E21/E22). With `texture: false`:
- The `audit_layer.py` genre-circle activation matrix skips `shenbi-review-texture`
- No audit file is generated for texture
- No G4 check validates texture dimensions
- No drift signal originates from texture

The prose collapse (0‰ → 109‰ system-term density over 56 chapters) was invisible because the one audit designed to detect it was turned off.

**Evidence:** `genre-config.json` line `"texture": false`. The 26-chapter degradation period (Ch30-56) coincides exactly with the period where texture audits would have flagged the problem.

---

## 3. Fix Strategy

### 3.1 Configuration Coherence Validator (G0 Check)

Create a G0 check that validates internal consistency of `genre-config.json`:

```python
# src/shenbi/gates/g0_config_coherence.py (new)

def check_config_coherence(project_dir: Path) -> list[str]:
    """Validate genre-config.json internal consistency."""
    issues = []
    config = json.loads((project_dir / "genre-config.json").read_text())

    # Check 1: Threshold single-source-of-truth
    config_floor = config.get("resonance_global_floor")
    skill_floor = _read_skill_floor("shenbi-review-resonance")
    if config_floor and skill_floor and config_floor != skill_floor:
        issues.append(
            f"G0.cc.threshold_mismatch:resonance_floor "
            f"config={config_floor} vs skill={skill_floor} — "
            f"chapters scoring {config_floor}-{skill_floor-1} will pass state "
            f"gate but fail audit skill silently"
        )

    # Check 2: Critical audit dimensions enabled
    critical_dimensions = {
        "texture": "prose degradation detection (sensory detail, scene concreteness)",
        "antiAi": "AI-generated text pattern detection",
        "continuity": "narrative continuity tracking",
    }
    audit_dims = config.get("auditDimensions", {})
    for dim, rationale in critical_dimensions.items():
        if not audit_dims.get(dim, True):  # Default True if absent
            issues.append(
                f"G0.cc.critical_audit_disabled:{dim} — "
                f"disabling this removes: {rationale}. "
                f"This is a quality safety net. Re-enable unless explicitly trading off."
            )

    # Check 3: Floor reasonableness
    if config_floor and config_floor < 60:
        issues.append(
            f"G0.cc.floor_too_low:resonance_global_floor={config_floor} — "
            f"floors below 60 allow degraded chapters to pass without revision"
        )

    return issues
```

### 3.2 Single-Source-of-Truth for Thresholds

Define numeric thresholds in ONE location and have all consumers reference it:

```python
# src/shenbi/config/thresholds.py (new)

from dataclasses import dataclass

@dataclass(frozen=True)
class QualityThresholds:
    """Single source of truth for all quality thresholds."""
    resonance_global_floor: int = 65  # Used by BOTH state routing AND audit skill
    resonance_revision_trigger: int = 60  # Below this → force revision
    word_count_floor: int = 3000  # Minimum CJK characters per chapter
    protagonist_mention_floor: int = 3  # Minimum protagonist name mentions
    system_term_density_warn: int = 30  # per mille
    system_term_density_hard: int = 50  # per mille

DEFAULT_THRESHOLDS = QualityThresholds()

# All consumers import from here:
# - genre-config.json overrides are validated against these defaults
# - skill prompts reference these values (not hardcoded)
# - G4 checkers use these values
```

### 3.3 Audit Dimension Safety Matrix

Document which audit dimensions are critical safety nets and cannot be disabled without explicit risk acceptance:

```python
AUDIT_SAFETY_MATRIX = {
    "texture": {
        "critical": True,
        "detects": "prose degradation, sensory detail loss, scene concreteness collapse",
        "cannot_disable_without": "explicit human approval + alternative detection mechanism",
    },
    "antiAi": {
        "critical": True,
        "detects": "AI-generated text patterns, system-term leakage",
        "cannot_disable_without": "explicit human approval",
    },
    "dialogue": {
        "critical": False,
        "detects": "dialogue quality and naturalness",
        "can_disable": True,
    },
    # ... other dimensions
}
```

### 3.4 Config Change Audit Trail

Log all config changes with rationale:

```python
def update_genre_config(project_dir: Path, changes: dict, rationale: str):
    """Update genre-config with mandatory rationale for safety-critical changes."""
    config = _load_config(project_dir)

    for key, new_value in changes.items():
        old_value = _get_nested(config, key)

        # Block critical dimension disabling without explicit rationale
        if key.startswith("auditDimensions.") and new_value is False:
            dim = key.split(".")[-1]
            if AUDIT_SAFETY_MATRIX.get(dim, {}).get("critical"):
                if not rationale or len(rationale) < 50:
                    raise ConfigError(
                        f"Cannot disable critical audit '{dim}' without "
                        f">= 50 char rationale explaining the alternative detection mechanism"
                    )

        _set_nested(config, key, new_value)
        _log_config_change(project_dir, key, old_value, new_value, rationale)

    _save_config(project_dir, config)
```

---

## 4. Affected Files

| File | Change | Rationale |
|------|--------|-----------|
| `src/shenbi/gates/g0_config_coherence.py` (new) | Configuration coherence G0 check | Detect threshold contradictions and disabled safety nets |
| `src/shenbi/config/thresholds.py` (new) | Single-source-of-truth thresholds | Eliminate threshold drift between config/code/skills |
| `src/shenbi/gates/g0.py` | Wire in `check_config_coherence` | Run at pipeline start |
| `genre-config.json` (production) | Fix `resonance_global_floor: 50 → 65`, re-enable `texture: true` | Correct the two identified defects |

---

## 5. Verification Criteria

1. **G0.cc.threshold_mismatch** fires when config floor ≠ skill floor
2. **G0.cc.critical_audit_disabled** fires when texture/antiAi/continuity is disabled
3. **All thresholds** defined in one location (`thresholds.py`), consumed by config/skills/gates
4. **Critical audit dimension** cannot be disabled without >= 50 char rationale
5. **Production genre-config** has `resonance_global_floor >= 60` and `texture: true`
6. **Regression:** `just check` passes fully

---

## 6. Dependencies

```
Spec 18 (this spec, Configuration Coherence and Threshold Governance)
    |
    +---> Explains: Spec 4 E21/E22 (prose collapse went undetected because texture audit was disabled)
    +---> Enhances: Spec 2 E11/E12 (resonance floor mismatch caused silent quality erosion)

Prerequisites: None (standalone governance fix)
```
