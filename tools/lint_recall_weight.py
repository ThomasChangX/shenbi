#!/usr/bin/env python3
"""Offline CLI shell for spec #78 recall/weight lints.

Logic lives in shenbi.text.recall_weight (voice_lexicon→lint_voice_meme form).
"""

from __future__ import annotations

import sys
from pathlib import Path

from shenbi.text.recall_weight import main

if __name__ == "__main__":
    argv = [
        str(Path(a)) if i == 0 and not a.startswith("-") else a for i, a in enumerate(sys.argv[1:])
    ]
    sys.exit(main(argv))
