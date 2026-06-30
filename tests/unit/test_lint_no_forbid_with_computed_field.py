"""N7 lint tests: models with @computed_field cannot set extra='forbid'."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_lint_passes_on_current_contracts() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = str(repo / "tools" / "lint_no_forbid_with_computed_field.py")
    target = str(repo / "src" / "shenbi" / "contracts")
    r = subprocess.run([sys.executable, script, target], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_lint_catches_forbid_violation(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    script = str(repo / "tools" / "lint_no_forbid_with_computed_field.py")
    bad = tmp_path / "bad.py"
    bad.write_text(
        "from pydantic import BaseModel, computed_field\n"
        "class M(BaseModel):\n"
        "    model_config = {'extra': 'forbid'}\n"
        "    x: int\n"
        "    @computed_field\n"
        "    @property\n"
        "    def y(self) -> int: return self.x\n",
        encoding="utf-8",
    )
    r = subprocess.run([sys.executable, script, str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "forbid" in r.stderr.lower()
