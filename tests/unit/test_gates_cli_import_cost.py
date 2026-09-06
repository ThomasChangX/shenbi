"""T1604 (C28 R4): gates.cli top-level import must stay under 50ms.

The gate CLI is spawned as a subprocess ~5-6 times per chapter; 96% of the
0.29-0.37s spawn was import cost (jieba via text.cjk + eager loading of all
11 gate modules + the logging/cli_utils/gates.shared chains). This test pins
the importtime cumulative for ``shenbi.gates.cli`` below 50,000us.
"""

import subprocess
import sys


def _importtime_cumulative_us(dotted: str) -> int:
    proc = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", f"from shenbi.gates import {dotted}"],
        capture_output=True,
        text=True,
        check=True,
    )
    # importtime stderr lines: "import time: self [us] | cumulative | package"
    for line in reversed(proc.stderr.splitlines()):
        if line.split("|")[-1].strip() == f"shenbi.gates.{dotted}":
            parts = [p.strip() for p in line.replace("import time:", "").split("|") if p.strip()]
            if len(parts) >= 2:
                return int(parts[1])
    raise AssertionError(f"shenbi.gates.{dotted} not found in importtime output")


def test_gates_cli_top_level_import_under_50ms() -> None:
    """Min of 3 samples: single-shot importtime is load-sensitive (observed
    3.97ms typical but 57ms under pytest-xdist worker contention on main,
    post-PR #153). The min approximates the unloaded cold-import cost, which
    is the quantity this perf bound pins; max/median would re-introduce
    CI-machine-load flakiness the bound cannot control.
    """
    assert min(_importtime_cumulative_us("cli") for _ in range(3)) < 50_000
