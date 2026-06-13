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
names = ['validate-gate.py', 'scoring.py', 'phase-runner.py', 'summarize-round.py']
new = {}
for n in names:
    p = project / 'tests' / n
    if p.exists():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        new[n] = f'sha256:{h}'
        print(f'  {n}: {h}')
deps['_tool_hashes'] = new
deps_path.write_text(json.dumps(deps, indent=2, ensure_ascii=False) + '\n')
print('Done.')
"
