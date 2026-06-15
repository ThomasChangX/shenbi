#!/bin/bash
# Capture current shenbi-validate outputs as baseline for differential testing.
# Originally run BEFORE PR-19's modularization. Re-run after to verify equivalence.
set -euo pipefail

VG="uv run shenbi-validate"
OUT=tests/baselines/gate-outputs

mkdir -p "$OUT"

# G0
$VG G0 outline-example.md > "$OUT/G0.json" 2>&1 || true

# G2 with various file types
$VG G2 "tests/fixtures/novel-example.json" json > "$OUT/G2-internal.json" 2>&1 || true
$VG G2 "tests/fixtures/chapter-7-example.md" chapter > "$OUT/G2-chapter.json" 2>&1 || true
$VG G2 "tests/fixtures/truth-current_state.md" truth > "$OUT/G2-truth.json" 2>&1 || true

# G4 per skill -- the 20 skills with dedicated G4 checkers in src/shenbi/gates/g4/
# (plus 3 generic_* fallbacks that don't apply here). Iterating all 58 skill dirs
# produces noise (error responses for skills without checkers).
G4_SKILLS="anti_detect chapter_drafting chapter_planning character_design context_composing faction_builder foreshadowing_plant foreshadowing_track genre_config length_normalizing location_builder pacing_design plot_thread_weaver power_system relationship_map state_settling story_architecture style_polishing volume_outlining worldbuilding"
for skill in $G4_SKILLS; do
    # Skip generic checkers -- they take a fixture list, not a single skill fixture.
    case "$skill" in
        generic_*) continue ;;
    esac
    # G4 checkers dict uses hyphen-form keys (e.g. shenbi-genre-config), so we
    # must build the full name with hyphens to match.
    skill_hyphen="${skill//_/-}"
    full="shenbi-${skill_hyphen}"
    # Try multiple fixture naming conventions:
    # 1. Bare skill name (underscore form): chapter_drafting-example.md
    # 2. Hyphen form: chapter-drafting-example.md
    fixture=""
    for pattern in "${skill}-" "${skill_hyphen}-"; do
        fixture=$(find tests/fixtures -name "${pattern}*" -type f 2>/dev/null | head -1)
        [ -n "$fixture" ] && break
    done
    if [ -n "$fixture" ]; then
        $VG G4 "$full" "$fixture" > "$OUT/G4-${skill}.json" 2>&1 || true
    fi
done

# G6 / G7 with the live round-001. The archived round-001 only has
# enhancement-signals.json + summary.json (no progress.json/skill outputs),
# so it only ever yields FAIL and never covers a G6/G7 PASS path.
SAMPLE_ROUND=tests/rounds/round-001-2026-06-11
if [ -d "$SAMPLE_ROUND" ]; then
    $VG G6 genesis "$SAMPLE_ROUND" > "$OUT/G6.json" 2>&1 || true
    $VG G7 "$SAMPLE_ROUND" > "$OUT/G7.json" 2>&1 || true
fi

echo "Baseline regenerated at $OUT"
ls -la "$OUT"
