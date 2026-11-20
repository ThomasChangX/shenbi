"""Spec #118 T1/I-2: 声口阈值单源断言（可执行替代空转 lint 判据）."""

from __future__ import annotations

import subprocess
from pathlib import Path

from shenbi.text.voice_lexicon import (
    DEFAULT_VOICE_DENSITY_MIN,
    DEFAULT_VOICE_PRESENCE_MIN,
)

REPO = Path(__file__).resolve().parents[3]


def test_threshold_constants_pinned() -> None:
    assert DEFAULT_VOICE_PRESENCE_MIN == 1
    assert DEFAULT_VOICE_DENSITY_MIN == 2


def test_no_bare_copies_outside_single_source() -> None:
    """仓内（src/＋tools/）除单源 voice_lexicon 外无 presence/density 阈裸副本."""
    out = (
        subprocess.run(
            [
                "grep",
                "-rn",
                "-E",
                "DEFAULT_VOICE_(PRESENCE|DENSITY)_MIN\\s*=\\s*[0-9]",
                "src/",
                "tools/",
            ],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
        .stdout.strip()
        .splitlines()
    )
    assert all("voice_lexicon.py" in ln for ln in out), out
