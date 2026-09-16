#!/bin/bash
# SMOKE TOOL — drives `pipeline resume` in a loop until the first
# checkpoint/error, then STOPS and reports for human action.
#
# NOT for production runs (spec #64 C26 / F002): this script never
# approves checkpoints and never writes pipeline-state.json. On a blocked
# checkpoint, run `just pipeline-review <dir> <decision> [feedback]`
# manually, then re-run this script.
# Exit codes: 0 completed, 1 fatal error, 2 max loops, 3 blocked checkpoint (manual review required).
set -euo pipefail

PROJECT_DIR="${1:-novel-${USER}-$(date +%Y%m%d-%H%M%S)}"
MAX_LOOPS="${2:-5000}"

die() { echo "FATAL: $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)" || die "cannot resolve script dir"
cd "$SCRIPT_DIR" || die "cannot cd into $SCRIPT_DIR"

mkdir -p "$PROJECT_DIR" || die "cannot create project dir (hostile name?)"
exec > >(tee -a "$PROJECT_DIR/pipeline.log") 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
machine_status() { echo "SHENBI_STATUS:$1"; }

get_field() {
    python3 tools/extract_json_field.py "$1" || echo "unknown"
}

read_step() {
    python3 - "$PROJECT_DIR/pipeline-state.json" <<'PY' || echo "unknown"
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    cl = d.get("chapter_loop", {})
    print(f"{cl.get('current_chapter', 0)}-{cl.get('step_index', 0)}")
except Exception:
    print("unknown")
PY
}

LOOP=0
while [ "$LOOP" -lt "$MAX_LOOPS" ]; do
    LOOP=$((LOOP + 1))

    OUTPUT=$(uv run pipeline resume "$PROJECT_DIR" 2>&1) || true
    STATUS=$(printf '%s\n' "$OUTPUT" | get_field status)
    CP=$(printf '%s\n' "$OUTPUT" | get_field checkpoint)
    PHASE=$(printf '%s\n' "$OUTPUT" | get_field phase)
    CURRENT_STEP=$(read_step)

    log "[$LOOP] status=$STATUS phase=$PHASE cp=${CP:-none} step=$CURRENT_STEP"

    case "$STATUS" in
        ok)
            if [ "$PHASE" = "completed" ]; then
                log "*** PIPELINE COMPLETED SUCCESSFULLY! ***"
                machine_status '{"status":"completed"}'
                exit 0
            fi
            ;;
        blocked)
            machine_status "{\"status\":\"blocked\",\"checkpoint\":\"${CP:-unknown}\"}"
            log "BLOCKED at checkpoint '${CP:-unknown}' — manual review required."
            log "    just pipeline-review \"$PROJECT_DIR\" <approve|reject|modify> [feedback]"
            exit 3
            ;;
        error|failed)
            machine_status "{\"status\":\"$STATUS\"}"
            log "Pipeline $STATUS — manual investigation required (never auto-approved)."
            printf '%s\n' "$OUTPUT" | grep -i "error\|traceback" | head -5 || true
            exit 1
            ;;
        *)
            machine_status "{\"status\":\"unexpected\",\"raw\":\"$STATUS\"}"
            die "unexpected status: $STATUS"
            ;;
    esac
done

machine_status '{"status":"max-loops"}'
log "Max loops ($MAX_LOOPS) reached."
exit 2
