#!/bin/bash
# dispatch-subagent.sh <skill_name> <test_type> <round_dir> [subagent_prompt]
# Wraps subagent dispatch for scoring independence (G3.4).
#
# Two modes:
#   --codex          Uses Codex CLI subagent (production)
#   --internal       Internal isolation scoring (development fallback)
# Default: --codex if codex CLI is available, else --internal
set -euo pipefail

SKILL="${1:-}"
TEST_TYPE="${2:-}"
ROUND_DIR="${3:-}"
PROMPT="${4:-}"

if [ -z "$SKILL" ] || [ -z "$TEST_TYPE" ] || [ -z "$ROUND_DIR" ]; then
    echo "Usage: dispatch-subagent.sh <skill_name> <test_type> <round_dir> [subagent_prompt]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Generate unique agent_id
AGENT_ID="$(basename "$ROUND_DIR")-${SKILL}-${TEST_TYPE}-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
echo "Agent ID: ${AGENT_ID}"

# Derive file_type from skill name for G2 validation
case "$SKILL" in
    shenbi-chapter-drafting|shenbi-style-polishing|shenbi-anti-detect|shenbi-length-normalizing)
        FILE_TYPE="chapter" ;;
    shenbi-state-settling|shenbi-foreshadowing-track|shenbi-foreshadowing-plant)
        FILE_TYPE="truth" ;;
    *)
        FILE_TYPE="chapter" ;;
esac

# Derive input files from SKILL.md data contract
INPUT_FILES=$(python3 -c "
import re, sys, json
skill_md_path = '${PROJECT_DIR}/skills/${SKILL}/SKILL.md'
try:
    skill_md = open(skill_md_path).read()
    reads = re.findall(r'\*\*Reads:\*\*\s*(.*)', skill_md)
    files = []
    for line in reads:
        files.extend(re.findall(r'\`([^\`]+)\`', line))
    print(json.dumps(files))
except Exception:
    print('[]')
")

# G1: Pre-dispatch input validation
echo "=== G1: Input Validation ==="
G1_RESULT=$(uv run shenbi-validate G1 "$SKILL" "$INPUT_FILES" "$ROUND_DIR" 2>&1) || true
G1_STATUS=$(echo "$G1_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
if [ "$G1_STATUS" != "PASS" ]; then
    echo "G1 FAILED:"
    echo "$G1_RESULT"
    exit 1
fi
echo "G1 PASSED"

# Derive output files from SKILL.md data contract (skill has already executed)
OUTPUT_FILES=$(python3 -c "
import re
skill_md_path = '${PROJECT_DIR}/skills/${SKILL}/SKILL.md'
try:
    skill_md = open(skill_md_path).read()
    writes = re.findall(r'\*\*Writes:\*\*\s*(.*)', skill_md)
    updates = re.findall(r'\*\*Updates:\*\*\s*(.*)', skill_md)
    files = []
    for line in writes + updates:
        files.extend(re.findall(r'\`([^\`]+)\`', line))
    print(','.join(files))
except Exception:
    print('')
")

# G2: Output validation — verifies the skill's output files exist and are well-formed.
# Runs in both codex and --internal modes (the skill execution happened earlier).
if [ -n "$OUTPUT_FILES" ]; then
    echo "=== G2: Output Validation ==="
    G2_RESULT=$(uv run shenbi-validate G2 "$OUTPUT_FILES" "$FILE_TYPE" "$ROUND_DIR" "$PROJECT_DIR" 2>&1) || true
    G2_STATUS=$(echo "$G2_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    if [ "$G2_STATUS" != "PASS" ]; then
        echo "G2 FAILED:"
        echo "$G2_RESULT"
        exit 1
    fi
    echo "G2 PASSED"
else
    echo "=== G2: Skipped (no output files derived from SKILL.md) ==="
fi

# === Subagent Dispatch ===
echo "=== Dispatching Scoring Subagent ==="

# Detect dispatch mode
MODE="internal"
if command -v codex &>/dev/null; then
    MODE="codex"
elif [ -n "${CODEX_API_KEY:-}" ]; then
    MODE="codex-api"
fi
echo "Dispatch mode: ${MODE}"

SCORES_FILE="${ROUND_DIR}/t1-reports/${SKILL}-${TEST_TYPE}-scores-subagent.json"
RUBRIC_PATH="${RUBRIC:-tests/tiers/t1-skill/${SKILL}/rubric.md}"

if [ "$MODE" = "codex" ]; then
    # Production: Codex CLI subagent (fresh session, no parent context).
    # codex exec takes prompt as positional arg; -o writes the agent's final
    # message to a file. We then extract the JSON scores object from it.
    if [ -z "$PROMPT" ]; then
        echo "ERROR: codex mode requires a non-empty prompt (arg 4)" >&2
        exit 1
    fi
    echo "Dispatching via codex exec..."
    RAW_OUT="${SCORES_FILE}.raw"
    # 10-minute timeout — scoring subagents should finish well under this.
    # Use gtimeout (GNU coreutils on macOS) if available, else timeout, else none.
    TIMEOUT_BIN=""
    if command -v gtimeout &>/dev/null; then
        TIMEOUT_BIN="gtimeout 600"
    elif command -v timeout &>/dev/null; then
        TIMEOUT_BIN="timeout 600"
    else
        echo "WARN: neither gtimeout nor timeout found — running without timeout" >&2
    fi
    # shellcheck disable=SC2086
    $TIMEOUT_BIN codex exec -C "${PROJECT_DIR}" \
        -o "${RAW_OUT}" "${PROMPT}" || {
        rc=$?
        if [ $rc -eq 124 ]; then
            echo "ERROR: codex exec timed out after 600s" >&2
        else
            echo "ERROR: codex exec failed (exit $rc)" >&2
        fi
        exit 1
    }
    # Extract the JSON object { "1": N, "2": N, ... } from the agent's response
    python3 -c "
import json, re, sys
raw = open('${RAW_OUT}').read()
m = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
if not m:
    print('ERROR: no JSON object found in codex output', file=sys.stderr)
    sys.exit(1)
try:
    obj = json.loads(m.group(0))
except json.JSONDecodeError as e:
    print(f'ERROR: invalid JSON from codex: {e}', file=sys.stderr)
    sys.exit(1)
json.dump(obj, open('${SCORES_FILE}', 'w'))
"
    rm -f "${RAW_OUT}"
    # Compute final score via scoring.py (enforces gate markers, REJECT, etc.)
    SCORE_OUTPUT=$(uv run shenbi-score \
        "${RUBRIC_PATH}" \
        "${SCORES_FILE}" \
        --test-type "${TEST_TYPE}" \
        --round-dir "${ROUND_DIR}" \
        --subagent)
    SCORING_EXIT=$?
    if [ $SCORING_EXIT -ne 0 ]; then
        echo "scoring.py exited ${SCORING_EXIT}:" >&2
        echo "$SCORE_OUTPUT" >&2
        exit $SCORING_EXIT
    fi
    FINAL_SCORE=$(echo "$SCORE_OUTPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('final_score', 0))")
    uv run shenbi-progress mark-done "${ROUND_DIR}" "${SKILL}" "${TEST_TYPE}" "${FINAL_SCORE}"
    echo "$SCORE_OUTPUT"
elif [ "$MODE" = "codex-api" ]; then
    echo "ERROR: codex-api mode not implemented (use codex CLI or --internal)" >&2
    exit 1
else
    # Development fallback: dispatcher performs scoring manually.
    # G3.4 compliance: dispatcher must clear generation context before scoring.
    # This script has done: agent_id generation, G1 (input check), G2 (output check),
    # and saved the scoring prompt for traceability. The dispatcher must do the rest.
    echo "=== Internal Mode: Dispatcher completes scoring manually ==="
    echo "WARNING: Production uses codex CLI. This mode requires manual scoring."

    PROMPT_FILE="${ROUND_DIR}/skill-traces/${SKILL}-${TEST_TYPE}-prompt.md"
    echo "$PROMPT" > "$PROMPT_FILE"
    echo "  Prompt saved: ${PROMPT_FILE}"
    echo "  Expected output files: ${OUTPUT_FILES:-<none derived>}"
    echo ""
    echo "  DISPATCHER MUST NOW (in a fresh / context-cleared session):"
    echo "    1. Score outputs against rubric using the saved prompt"
    echo "    2. Write scores JSON to: ${SCORES_FILE}"
    echo "       Format: {\"1\": <int>, \"2\": <int>, ...} for all rubric dimensions"
    echo "    3. uv run shenbi-score ${RUBRIC_PATH} ${SCORES_FILE} \\"
    echo "           --test-type ${TEST_TYPE} --round-dir ${ROUND_DIR} --subagent"
    echo "    4. uv run shenbi-progress mark-done ${ROUND_DIR} ${SKILL} ${TEST_TYPE} <final_score>"
    echo ""
    echo "  Scoring will REJECT (exit 2) if dimensions are missing."
fi

echo ""
echo "=== Subagent ${AGENT_ID} complete: ${SKILL}-${TEST_TYPE} (mode: ${MODE}) ==="
