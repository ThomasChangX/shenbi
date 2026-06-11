#!/bin/bash
# Integration tests for validate-gate.py
#
# Validates that every gate type returns parseable JSON with "gate" and "status"
# fields, and tests end-to-end behavior against real project data.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VALIDATE_GATE="$SCRIPT_DIR/validate-gate.py"
ROUNDS_DIR="$SCRIPT_DIR/rounds"
SEED_FILE="$PROJECT_DIR/outline-example.md"

PASS=0
FAIL=0

test_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
test_fail() { echo "  FAIL: $1 — $2"; FAIL=$((FAIL + 1)); }

# ---------------------------------------------------------------------------
# Helper: run a gate and parse the JSON result.  Returns the JSON object via
# a global variable GATE_JSON.  Set GATE_EXIT to the exit code.
# ---------------------------------------------------------------------------
run_gate() {
    local gate="$1"
    shift
    GATE_JSON=""
    GATE_EXIT=0
    # Capture stdout; allow non-zero exit (unknown gate exits 1)
    GATE_JSON=$(python3 "$VALIDATE_GATE" "$gate" "$@" 2>&1) || GATE_EXIT=$?
}

# Helper: assert JSON field equals expected value
assert_json_field() {
    local label="$1" field="$2" expected="$3"
    local actual
    actual=$(echo "$GATE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null) || true
    if [ "$actual" = "$expected" ]; then
        test_pass "$label ($field=$expected)"
    else
        test_fail "$label" "expected $field='$expected', got '$actual'"
    fi
}

# Helper: assert JSON has a field (non-empty)
assert_json_has_field() {
    local label="$1" field="$2"
    local actual
    actual=$(echo "$GATE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null) || true
    if [ -n "$actual" ]; then
        test_pass "$label (has $field='$actual')"
    else
        test_fail "$label" "expected non-empty field '$field'"
    fi
}

# Helper: assert JSON is valid and has gate + status
assert_valid_gate_json() {
    local label="$1"
    local ok
    ok=$(echo "$GATE_JSON" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'gate' in d and 'status' in d:
        print('OK')
    else:
        print('MISSING_FIELDS')
except Exception as e:
    print('INVALID_JSON:' + str(e))
" 2>/dev/null) || true
    if [ "$ok" = "OK" ]; then
        test_pass "$label (valid JSON with gate+status)"
    else
        test_fail "$label" "invalid or incomplete JSON: $ok"
    fi
}

# Helper: assert JSON check with given id exists
assert_check_exists() {
    local label="$1" check_id="$2"
    local found
    found=$(echo "$GATE_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
checks = d.get('checks', [])
found = any(c.get('id') == '$check_id' for c in checks)
print('YES' if found else 'NO')
" 2>/dev/null) || true
    if [ "$found" = "YES" ]; then
        test_pass "$label (check $check_id exists)"
    else
        test_fail "$label" "check $check_id not found"
    fi
}

echo ""
echo "================================================"
echo "Integration Tests — validate-gate.py"
echo "================================================"
echo ""

# ===========================================================================
# Test 1: G0 Environment Check with seed file
# ===========================================================================
echo "--- Test 1: G0 Environment Check ---"

if [ -f "$SEED_FILE" ]; then
    run_gate "G0" "$SEED_FILE"
    assert_valid_gate_json "G0 seed-file"
    assert_json_field "G0 seed-file status" "status" "PASS"
    assert_check_exists "G0 expected_chapters" "G0.3"
else
    echo "  SKIP: seed file not found at $SEED_FILE"
fi

# ===========================================================================
# Test 2: G2 Chapter Validation
# ===========================================================================
echo ""
echo "--- Test 2: G2 Chapter Validation ---"

CHAPTER_FILE=$(find "$ROUNDS_DIR" -path "*/chapters/chapter-*.md" -type f 2>/dev/null | head -1 || true)

if [ -n "$CHAPTER_FILE" ] && [ -f "$CHAPTER_FILE" ]; then
    run_gate "G2" "$CHAPTER_FILE" "chapter"
    assert_valid_gate_json "G2 chapter ($(basename "$CHAPTER_FILE"))"
    assert_json_has_field "G2 chapter gate field" "gate"
else
    echo "  SKIP: no chapter files found in $ROUNDS_DIR"
fi

# ===========================================================================
# Test 3: G4 Chapter Drafting
# ===========================================================================
echo ""
echo "--- Test 3: G4 Chapter Drafting ---"

if [ -n "${CHAPTER_FILE:-}" ] && [ -f "${CHAPTER_FILE:-}" ]; then
    run_gate "G4" "chapter-drafting" "$CHAPTER_FILE"
    assert_valid_gate_json "G4 chapter-drafting ($(basename "$CHAPTER_FILE"))"
    assert_json_has_field "G4 chapter-drafting gate field" "gate"
else
    echo "  SKIP: no chapter file from Test 2"
fi

# ===========================================================================
# Test 4: G7 Round Close
# ===========================================================================
echo ""
echo "--- Test 4: G7 Round Close ---"

ROUND_DIR=$(find "$ROUNDS_DIR" -maxdepth 1 -type d -name "round-*" 2>/dev/null | head -1 || true)

if [ -n "$ROUND_DIR" ] && [ -d "$ROUND_DIR" ]; then
    run_gate "G7" "$ROUND_DIR"
    assert_valid_gate_json "G7 round ($(basename "$ROUND_DIR"))"

    # Accept any status: PASS, FAIL, or INCOMPLETE are all valid
    G7_STATUS=$(echo "$GATE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null) || true
    case "$G7_STATUS" in
        PASS|FAIL|INCOMPLETE|UNIMPLEMENTED)
            test_pass "G7 round status is valid ($G7_STATUS)"
            ;;
        *)
            test_fail "G7 round status" "unexpected status: $G7_STATUS"
            ;;
    esac
else
    echo "  SKIP: no round directories found in $ROUNDS_DIR"
fi

# ===========================================================================
# Test 5: All Gates Return Valid JSON
# ===========================================================================
echo ""
echo "--- Test 5: All Gates Return Valid JSON ---"

# Test G0 without args (should return SKIP-based result)
run_gate "G0"
assert_valid_gate_json "G0 no-args"

# Test G5 — needs just a phase name to return structured JSON
run_gate "G5" "genesis"
assert_valid_gate_json "G5 genesis"

# Test G6 — needs a pipeline name
run_gate "G6" "long-form"
assert_valid_gate_json "G6 long-form"

# Test G_TRANSITION — needs from_phase, to_phase, round_dir
# Use round-001 as it exists; gate will fail cleanly (no progress.json) but return valid JSON
if [ -n "${ROUND_DIR:-}" ] && [ -d "${ROUND_DIR:-}" ]; then
    run_gate "G_TRANSITION" "generative" "bug-hunt" "$ROUND_DIR"
    assert_valid_gate_json "G_TRANSITION"
else
    # Fallback: call with dummy path, will fail gracefully
    run_gate "G_TRANSITION" "generative" "bug-hunt" "$ROUNDS_DIR/round-001-2026-06-11"
    assert_valid_gate_json "G_TRANSITION (fallback)"
fi

# Test G_DISPATCH
if [ -n "${ROUND_DIR:-}" ] && [ -d "${ROUND_DIR:-}" ]; then
    run_gate "G_DISPATCH" "generative" "$ROUND_DIR"
    assert_valid_gate_json "G_DISPATCH"
else
    run_gate "G_DISPATCH" "generative" "$ROUNDS_DIR/round-001-2026-06-11"
    assert_valid_gate_json "G_DISPATCH (fallback)"
fi

# Test G_RECONCILE
if [ -n "${ROUND_DIR:-}" ] && [ -d "${ROUND_DIR:-}" ]; then
    run_gate "G_RECONCILE" "$ROUND_DIR"
    assert_valid_gate_json "G_RECONCILE"
else
    run_gate "G_RECONCILE" "$ROUNDS_DIR/round-001-2026-06-11"
    assert_valid_gate_json "G_RECONCILE (fallback)"
fi

# ===========================================================================
# Test 6: validate-gate.py CLI
# ===========================================================================
echo ""
echo "--- Test 6: validate-gate.py CLI ---"

# 6a: No args should print usage and exit 1
USAGE_OUTPUT=$(python3 "$VALIDATE_GATE" 2>&1) || USAGE_EXIT=$?
if [ "${USAGE_EXIT:-0}" -eq 1 ] && echo "$USAGE_OUTPUT" | grep -q "Usage:"; then
    test_pass "CLI no-args prints Usage and exits 1"
else
    test_fail "CLI no-args" "expected usage message with exit 1, got exit=${USAGE_EXIT:-0}"
fi

# 6b: Unknown gate returns UNKNOWN_GATE status and exits 1
UNKNOWN_OUTPUT=$(python3 "$VALIDATE_GATE" "NONEXISTENT_GATE_XYZ" 2>&1) || UNKNOWN_EXIT=$?
if [ "${UNKNOWN_EXIT:-0}" -eq 1 ]; then
    UNKNOWN_STATUS=$(echo "$UNKNOWN_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null) || true
    if [ "$UNKNOWN_STATUS" = "UNKNOWN_GATE" ]; then
        test_pass "CLI unknown gate returns UNKNOWN_GATE status"
    else
        test_fail "CLI unknown gate" "expected UNKNOWN_GATE status, got '$UNKNOWN_STATUS'"
    fi
else
    test_fail "CLI unknown gate" "expected exit 1, got exit=${UNKNOWN_EXIT:-0}"
fi

# ===========================================================================
# Results
# ===========================================================================
echo ""
echo "================================================"
echo "=== Results: $PASS passed, $FAIL failed ==="
echo "================================================"

if [ "$FAIL" -eq 0 ]; then
    echo ""
    echo "All integration tests passed."
    exit 0
else
    echo ""
    echo "Some integration tests failed.  See FAIL lines above."
    exit 1
fi
