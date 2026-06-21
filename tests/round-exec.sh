#!/bin/bash
# Execute a test round. Usage: ./round-exec.sh <model> <tier>
# Validate: ./round-exec.sh --validate <round-dir>
# All commands are macOS bash 3.2 compatible.

set -euo pipefail

# Validate mode: check that a round was actually executed
if [ "${1:-}" = "--validate" ]; then
  ROUND_DIR="${2:?Usage: round-exec.sh --validate <round-dir>}"
  ERRORS=0

  if [ ! -f "${ROUND_DIR}/summary.json" ]; then
    echo "FAIL: summary.json not found"
    ERRORS=$((ERRORS + 1))
  fi

  FRAMEWORK_SKILLS=$(ls tests/tiers/t1-skill/ | grep -v _template | sort)
  SUMMARY_SKILLS=$(python3 -c "import json; d=json.load(open('${ROUND_DIR}/summary.json')); print('\n'.join(sorted(d.get('t1_scores',{}).keys())))" 2>/dev/null || true)
  if [ -n "$SUMMARY_SKILLS" ]; then
    DIFF_OUTPUT=$(diff <(echo "$FRAMEWORK_SKILLS") <(echo "$SUMMARY_SKILLS") 2>/dev/null || true)
    if [ -n "$DIFF_OUTPUT" ]; then
      echo "WARN: Skill names in summary.json don't match framework directories"
      echo "$DIFF_OUTPUT"
    fi
  fi

  # Determine which report dir to check based on tier
  TIER_TARGET=$(python3 -c "import json; print(json.load(open('${ROUND_DIR}/meta.json')).get('tier_target','T1'))" 2>/dev/null || echo "T1")
  TIER_LOWER=$(echo "$TIER_TARGET" | tr '[:upper:]' '[:lower:]')
  REPORT_DIR="${TIER_LOWER}-reports"

  for subdir in skill-output "$REPORT_DIR" skill-traces; do
    COUNT=$(find "${ROUND_DIR}/${subdir}" -type f 2>/dev/null | wc -l)
    if [ "$COUNT" -eq 0 ]; then
      echo "FAIL: ${subdir}/ is empty (no output generated)"
      ERRORS=$((ERRORS + 1))
    else
      echo "OK: ${subdir}/ has ${COUNT} files"
    fi
  done

  if [ ! -f "${ROUND_DIR}/enhancement-signals.json" ]; then
    echo "WARN: enhancement-signals.json not found"
  fi

  if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "VALIDATION FAILED: ${ERRORS} errors found. Round was not properly executed."
    exit 1
  else
    echo ""
    echo "VALIDATION PASSED: Round appears properly executed."
    exit 0
  fi
fi

# Create mode
MODEL="${1:?Usage: round-exec.sh <model> <tier>}"
TIER="${2:?Specify T1, T2, or T3}"
DATE=$(date +%Y-%m-%d)

LAST=$(ls -d tests/rounds/round-* 2>/dev/null | { grep -v TEMPLATE || true; } | sort | tail -1)
if [ -z "$LAST" ]; then
  NUM=1
else
  NUM=$(($(basename "$LAST" | sed 's/round-\([0-9]*\).*/\1/') + 1))
fi
ROUND_NUM=$(printf "%03d" $NUM)
ROUND_DIR="tests/rounds/round-${ROUND_NUM}-${DATE}"
TIER_LOWER=$(echo "$TIER" | tr '[:upper:]' '[:lower:]')

echo "=== Creating round ${ROUND_NUM}: ${MODEL} / ${TIER} ==="

# G0: Environment readiness check
echo "=== G0: Environment Check ==="
G0_RESULT=$(uv run shenbi-validate G0 "${SEED_FILE:-outline-example.md}" 2>&1) || true
G0_STATUS=$(echo "$G0_RESULT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
if [ "$G0_STATUS" != "PASS" ]; then
    echo "G0 FAILED:"
    echo "$G0_RESULT"
    exit 1
fi
EXPECTED_CHAPTERS=$(echo "$G0_RESULT" | python3 -c "import sys,json;d=json.load(sys.stdin);print([c for c in d.get('checks',[]) if c.get('id')=='G0.3'][0].get('expected_chapters','N/A'))" 2>/dev/null || echo "N/A")
echo "G0 PASSED (expected chapters: ${EXPECTED_CHAPTERS})"

mkdir -p "${ROUND_DIR}"/{t1-reports,t2-reports,t3-reports,skill-output,skill-traces}

# progress.json: written via update-progress.py single-writer (no direct edits)
uv run shenbi-progress init "${ROUND_DIR}" "${TIER}" --expected-chapters "${EXPECTED_CHAPTERS}"

# Override tokens
TOKEN1=$(python3 -c "import secrets;print(secrets.token_hex(16))")
TOKEN2=$(python3 -c "import secrets;print(secrets.token_hex(16))")
TOKEN3=$(python3 -c "import secrets;print(secrets.token_hex(16))")
python3 -c "
import hashlib,json
ts=['$TOKEN1','$TOKEN2','$TOKEN3']
hs=[{'hash':hashlib.sha256(t.encode()).hexdigest(),'spent':False} for t in ts]
json.dump({'tokens':hs},open('${ROUND_DIR}/.token-hashes.json','w'),indent=2)
"
chmod 600 "${ROUND_DIR}/.token-hashes.json"

# Keep existing meta.json and summary.json for backward compatibility
cat > "${ROUND_DIR}/meta.json" << EOF
{
  "round": "${ROUND_NUM}",
  "date": "${DATE}",
  "model": "${MODEL}",
  "tier_target": "${TIER}",
  "skill_versions": {},
  "notes": ""
}
EOF

cat > "${ROUND_DIR}/summary.json" << EOF
{
  "round": "${ROUND_NUM}",
  "model": "${MODEL}",
  "tier_target": "${TIER}",
  "t1_scores": {},
  "t2_scores": {},
  "t3_scores": {},
  "kill_switches": [],
  "enhancement_signals": [],
  "band_breakdown": {"pass_excellent": 0, "pass_acceptable": 0, "conditional": 0, "fail": 0},
  "next_actions": []
}
EOF

echo '{"enhancement_signals": []}' > "${ROUND_DIR}/enhancement-signals.json"

echo ""
echo "=== Round ${ROUND_NUM} Override Tokens (SAVE THESE) ==="
echo "Token 1: $TOKEN1"
echo "Token 2: $TOKEN2"
echo "Token 3: $TOKEN3"
echo "=== Each token is SINGLE-USE. Store securely. ==="
echo ""
echo "Round directory: ${ROUND_DIR}"
echo "progress.json: ${ROUND_DIR}/progress.json"
echo "Validate with: $0 --validate ${ROUND_DIR}"
