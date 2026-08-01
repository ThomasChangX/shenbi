#!/bin/bash
# Automated pipeline runner for shenbi novel generation.
# Auto-approves checkpoints. Skips steps that get stuck (>3 escalations).
set -euo pipefail

PROJECT_DIR="${1:-novel-${USER}-$(date +%Y%m%d-%H%M%S)}"
MAX_LOOPS="${2:-5000}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Capture all output inside the project directory for multi-user isolation.
mkdir -p "$PROJECT_DIR"
exec > >(tee -a "$PROJECT_DIR/pipeline.log") 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }

LOOP=0
LAST_STATE=""
STUCK_COUNT=0

while [ "$LOOP" -lt "$MAX_LOOPS" ]; do
    LOOP=$((LOOP + 1))

    OUTPUT=$(uv run pipeline resume "$PROJECT_DIR" 2>&1) || true
    STATUS=$(echo "$OUTPUT" | grep -o '"status": "[^"]*"' | tail -1 | cut -d'"' -f4)
    CP=$(echo "$OUTPUT" | grep -o '"checkpoint": "[^"]*"' | tail -1 | cut -d'"' -f4 || echo "")
    PHASE=$(echo "$OUTPUT" | grep -o '"phase": "[^"]*"' | tail -1 | cut -d'"' -f4 || echo "?")

    # Read current step for stuck detection
    CURRENT_STEP=$(python3 -c "
import json
try:
    d=json.load(open('$PROJECT_DIR/pipeline-state.json'))
    cl=d.get('chapter_loop',{})
    print(f\"{cl.get('current_chapter',0)}-{cl.get('step_index',0)}\")
except: print('unknown')
" 2>/dev/null)

    log "[$LOOP] status=$STATUS phase=$PHASE cp=${CP:-none} step=$CURRENT_STEP"

    case "$STATUS" in
        ok)
            STUCK_COUNT=0
            LAST_STATE=""
            if [ "$PHASE" = "completed" ]; then
                log "*** PIPELINE COMPLETED SUCCESSFULLY! ***"
                exit 0
            fi
            ;;

        blocked)
            if [ -z "$CP" ]; then
                log "ERROR: blocked without checkpoint type"
                exit 1
            fi

            # Stuck detection: same step keeps failing
            if [ "$CURRENT_STEP" = "$LAST_STATE" ]; then
                STUCK_COUNT=$((STUCK_COUNT + 1))
            else
                STUCK_COUNT=1
                LAST_STATE="$CURRENT_STEP"
            fi

            if [ "$STUCK_COUNT" -ge 3 ]; then
                log "STUCK: step $CURRENT_STEP failed $STUCK_COUNT times. Advancing past it."
                uv run pipeline review "$PROJECT_DIR" approve 2>&1 | tail -1
                # Advance to next step by incrementing step_index
                python3 -c "
import json
from pathlib import Path
d=json.load(open('$PROJECT_DIR/pipeline-state.json'))
cl=d['chapter_loop']
cl['step_index'] = cl.get('step_index',0) + 1
cl['retry_counts'] = {}
json.dump(d, open('$PROJECT_DIR/pipeline-state.json','w'), indent=2)
print(f'Advanced to step {cl[\"step_index\"]}')
" 2>/dev/null
                STUCK_COUNT=0
                LAST_STATE=""
            else
                log "Auto-approving checkpoint: $CP (attempt $STUCK_COUNT)"
                uv run pipeline review "$PROJECT_DIR" approve 2>&1 | tail -1
            fi
            ;;

        error|failed)
            if echo "$OUTPUT" | grep -q "escalation\|gate\|dispatch"; then
                log "Auto-approving error..."
                uv run pipeline review "$PROJECT_DIR" approve 2>&1 | tail -1
            else
                log "FATAL: pipeline error"
                echo "$OUTPUT" | grep -i "error\|traceback" | head -5
                exit 1
            fi
            ;;

        *)
            log "FATAL: unexpected status: $STATUS"
            exit 1
            ;;
    esac
done

log "Max loops ($MAX_LOOPS) reached."
exit 2
