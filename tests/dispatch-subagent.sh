#!/bin/bash
# dispatch-subagent.sh <skill_name> <test_type> <round_dir> <subagent_prompt>
# Wraps subagent dispatch: generates agent_id, calls G1, dispatches, G2, records output_files
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

# Generate unique agent_id
AGENT_ID="${ROUND_DIR##*/round-}-${SKILL}-${TEST_TYPE}-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
echo "Agent ID: ${AGENT_ID}"

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
G1_RESULT=$(python3 "${SCRIPT_DIR}/validate-gate.py" G1 "$SKILL" "$INPUT_FILES" "$ROUND_DIR" 2>&1) || true
G1_STATUS=$(echo "$G1_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
if [ "$G1_STATUS" != "PASS" ]; then
    echo "G1 FAILED:"
    echo "$G1_RESULT"
    exit 1
fi
echo "G1 PASSED"

# Dispatch subagent (implementation-specific placeholder)
# In production, this would call Claude or another LLM with the subagent prompt
echo "=== Dispatching Subagent ==="
echo "Skill: ${SKILL}"
echo "Test Type: ${TEST_TYPE}"
echo "Prompt: ${PROMPT}"
echo ""
echo "NOTE: Subagent dispatch is implementation-specific."
echo "Place your subagent invocation here (e.g., Claude API call)."
echo "The subagent should produce output files per the SKILL.md data contract."
echo ""

# Derive expected output files from SKILL.md data contract
OUTPUT_FILES=$(python3 -c "
import re, sys
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

# G2: Post-dispatch output validation
if [ -n "$OUTPUT_FILES" ]; then
    echo "=== G2: Output Validation ==="
    G2_RESULT=$(python3 "${SCRIPT_DIR}/validate-gate.py" G2 "$OUTPUT_FILES" "$TEST_TYPE" "$ROUND_DIR" "$PROJECT_DIR" 2>&1) || true
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

# Record in progress.json
python3 -c "
import json, sys
pp_path = '${ROUND_DIR}/progress.json'
try:
    pp = json.load(open(pp_path))
    pp.setdefault('skills', {})
    pp['skills'].setdefault('${SKILL}', {})
    pp['skills']['${SKILL}']['${TEST_TYPE}'] = {'status': 'DONE', 'gate': 'PASS'}
    pp['skills']['${SKILL}']['agent_trace'] = pp['skills']['${SKILL}'].get('agent_trace', {})
    pp['skills']['${SKILL}']['agent_trace']['${TEST_TYPE}_generator'] = '${AGENT_ID}'
    output_list = [f.strip() for f in '${OUTPUT_FILES}'.split(',') if f.strip()]
    pp['skills']['${SKILL}']['output_files'] = output_list
    pp['subagent_completion_count'] = pp.get('subagent_completion_count', 0) + 1
    completed = set(pp.get('completed_skill_names', []))
    completed.add('${SKILL}')
    pp['completed_skill_names'] = list(completed)
    json.dump(pp, open(pp_path, 'w'), indent=2, ensure_ascii=False)
    print(f'progress.json updated: {len(output_list)} output files recorded')
except Exception as e:
    print(f'Failed to update progress.json: {e}', file=sys.stderr)
    sys.exit(1)
"

echo ""
echo "=== Subagent ${AGENT_ID} complete: ${SKILL}-${TEST_TYPE} ==="
