#!/bin/bash
# Lock current SHA256 hashes of tool scripts into deps.json.
# Run after any intentional tool modification.
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== Locking tool hashes ==="
python3 -c "
import json, hashlib
from pathlib import Path
project = Path('${PROJECT}')
deps_path = project / 'tests' / 'tiers' / 'deps.json'
deps = json.loads(deps_path.read_text(encoding='utf-8'))
# PR-19 (P-1.E): validate-gate.py / scoring.py / phase-runner.py / summarize-round.py
# moved to src/shenbi/. Hash the src/shenbi/ tree instead.
tool_paths = [
    'src/shenbi/gates/cli.py',
    'src/shenbi/gates/shared.py',
    'src/shenbi/scoring.py',
    'src/shenbi/phase_runner.py',
    'src/shenbi/summarize_round.py',
]
new = {}
for rel in tool_paths:
    p = project / rel
    if p.exists():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        new[rel] = f'sha256:{h}'
        print(f'  {rel}: {h}')
deps['_tool_hashes'] = new
deps_path.write_text(json.dumps(deps, indent=2, ensure_ascii=False) + '\n')
print('Done.')
"
