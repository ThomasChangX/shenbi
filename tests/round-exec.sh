#!/bin/bash
# Execute a test round. Usage: ./round-exec.sh <model> <tier>
# Example: ./round-exec.sh claude T1
# All commands are macOS bash 3.2 compatible.

set -euo pipefail

MODEL="${1:?Usage: round-exec.sh <model> <tier>}"
TIER="${2:?Specify T1, T2, or T3}"
DATE=$(date +%Y-%m-%d)

# Find next round number
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

# Create directory structure directly (not cp -r from template)
mkdir -p "${ROUND_DIR}"/{t1-reports,t2-reports,t3-reports,novel-output,skill-traces}

# Write meta.json
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

# Write empty summary.json
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

# Write empty enhancement signals
echo '{"signals": []}' > "${ROUND_DIR}/enhancement-signals.json"

echo "Round directory: ${ROUND_DIR}"
echo "Next steps:"
echo "  1. Run ${TIER} tests (manual or automated)"
echo "  2. Place reports in ${ROUND_DIR}/${TIER_LOWER}-reports/"
echo "  3. Score reports with: python3 tests/scoring.py <rubric> <scores>"
echo "  4. Fill summary.json"
echo "  5. Update CHANGELOG.md"
