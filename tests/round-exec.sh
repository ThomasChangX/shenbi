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

  for subdir in novel-output t1-reports skill-traces; do
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

mkdir -p "${ROUND_DIR}"/{t1-reports,t2-reports,t3-reports,novel-output,skill-traces}

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

echo "Round directory: ${ROUND_DIR}"
echo "Next steps:"
echo "  1. Run ${TIER} tests (manual or automated)"
echo "  2. Place reports in ${ROUND_DIR}/${TIER_LOWER}-reports/"
echo "  3. Score reports with: python3 tests/scoring.py <rubric> <scores>"
echo "  4. Fill summary.json"
echo "  5. Update CHANGELOG.md"
echo ""
echo "Validate with: $0 --validate ${ROUND_DIR}"
