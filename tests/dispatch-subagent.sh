#!/bin/bash
# Backward-compat shim. Dispatch logic now lives in shenbi.dispatcher.cli.
# This shim will be REMOVED in PR-22 (rename novel-output cleanup).
set -euo pipefail
exec uv run shenbi-dispatch "$@"
