"""C28 防回归基线三条 (spec #42 簇级验收): registry 解析 / 门禁冷启动 / 标题有界读取.

These are tracking baselines (no threshold assertions) — deterministic
thresholds live in the T1/T5 unit tests; compare console stats across runs.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from shenbi.contracts.loader import _parse_registry_uncached

pytestmark = pytest.mark.benchmark

_FIX = Path(__file__).resolve().parents[1] / "fixtures"


def test_registry_parse_baseline(benchmark: Any) -> None:
    """T1613/F215: uncached registry YAML parse (was paid per dispatch)."""
    benchmark(_parse_registry_uncached)


def test_gate_cold_start_baseline(benchmark: Any) -> None:
    """T1604: gate CLI cold-start wall time in a fresh subprocess
    (was ~370ms import cost per spawn, 5-6 spawns per chapter).
    """

    def _cold_import_ms() -> float:
        t0 = time.perf_counter()
        subprocess.run(
            [sys.executable, "-c", "from shenbi.gates import cli"],
            check=True,
        )
        return (time.perf_counter() - t0) * 1000

    benchmark(_cold_import_ms)


def test_title_bounded_read_baseline(benchmark: Any, tmp_path: Path) -> None:
    """T1609: previous-titles lookup on a 112-chapter corpus
    (was N-1 full-text reads, now bounded 4KB prefixes).
    """
    from shenbi.pipeline.chapter_loop import _load_previous_titles
    from tests.pipeline.helpers.c28_corpus import expand_chapter_corpus

    expand_chapter_corpus(_FIX / "multi-chapter-example", tmp_path, n=112)
    benchmark(lambda: _load_previous_titles(tmp_path, 112))
