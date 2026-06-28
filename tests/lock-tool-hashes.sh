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
# moved to src/shenbi/. Hash the full src/shenbi/ tree so new helpers
# (Wave 1+: revision_routing, escalation, foreshadowing_recall, etc.)
# are auto-included without manual list maintenance.
tool_paths = [
    str(p.relative_to(project))
    for p in (project / 'src' / 'shenbi').rglob('*.py')
    if '__pycache__' not in str(p)
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

echo "=== Locking calibration anchor hashes ==="
python3 -c "
import json, hashlib
from pathlib import Path
project = Path('${PROJECT}')
deps_path = project / 'tests' / 'tiers' / 'deps.json'
deps = json.loads(deps_path.read_text(encoding='utf-8'))
# Combined SHA256 over every file under tests/fixtures/calibration/**
# (excluding .gitkeep). Empty scaffolding state hashes the empty byte
# stream, which is a stable, lockable value.
cal_dir = project / 'tests' / 'fixtures' / 'calibration'
h = hashlib.sha256()
if cal_dir.exists():
    for p in sorted(cal_dir.rglob('*')):
        if p.is_file() and p.name != '.gitkeep':
            h.update(p.read_bytes())
combined = h.hexdigest()
deps.setdefault('_calibration_hashes', {})['combined'] = combined
deps_path.write_text(json.dumps(deps, indent=2, ensure_ascii=False) + '\n')
file_count = sum(
    1 for p in cal_dir.rglob('*') if p.is_file() and p.name != '.gitkeep'
) if cal_dir.exists() else 0
print(f'  calibration files: {file_count}')
print(f'  combined: {combined}')
print('Done.')
"
