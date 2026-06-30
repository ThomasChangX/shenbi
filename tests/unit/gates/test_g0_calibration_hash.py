"""Unit tests for G0.14: calibration anchor hash lock.

Function contract (mirrors the g0_purity tuple-returning helpers):

- check_calibration_integrity(
        calibration_dir: Path, deps_path: Path
  ) -> tuple[list[dict], str | None, list[str]]
    G0.14 sub-check: compute a combined SHA256 over every file under
    ``tests/fixtures/calibration/**`` and compare to the locked value at
    ``deps.json._calibration_hashes.combined``. Returns
    ``(checks, fail_reason_or_None, must_fix)``.

    Failure modes:
      * key missing from deps.json -> FAIL, hint: run tests/lock-tool-hashes.sh
      * hash mismatch             -> FAIL, hint: tamper/drift detected
      * match                     -> PASS
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g0 import check_calibration_integrity


def _write_deps(deps_path: Path, combined: str | None) -> dict[str, Any]:
    """Write a minimal deps.json with the given _calibration_hashes.combined.

    If ``combined`` is None the key is omitted entirely (missing-lock case).
    """
    deps: dict[str, Any] = {"_tool_hashes": {}}
    if combined is not None:
        deps["_calibration_hashes"] = {"combined": combined}
    deps_path.write_text(json.dumps(deps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return deps


def _compute_combined(calibration_dir: Path) -> str:
    """Mirror the gate's hash algorithm so tests can build a known-good lock.

    Must stay in sync with check_calibration_integrity, including CRLF→LF
    normalization (Windows git/filesystem may produce CRLF on write).
    """
    h = hashlib.sha256()
    for p in sorted(
        calibration_dir.rglob("*"),
        key=lambda x: str(x.relative_to(calibration_dir)).replace(os.sep, "/"),
    ):
        if p.is_file() and p.name != ".gitkeep":
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


@pytest.mark.unit
def test_empty_dir_with_locked_empty_hash_passs(tmp_path: Path) -> None:
    """Scaffolding state: no anchors yet, empty-set hash is locked -> PASS."""
    cal_dir = tmp_path / "calibration"
    cal_dir.mkdir()
    deps = tmp_path / "deps.json"
    _write_deps(deps, _compute_combined(cal_dir))

    checks, fail_reason, must_fix = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is None
    assert must_fix == []
    assert checks[0]["id"] == "G0.14"
    assert checks[0]["s"] == "PASS"


@pytest.mark.unit
def test_missing_lock_entry_fails_with_hint(tmp_path: Path) -> None:
    """deps.json without _calibration_hashes at all must FAIL and name the lock script."""
    cal_dir = tmp_path / "calibration"
    cal_dir.mkdir()
    deps = tmp_path / "deps.json"
    _write_deps(deps, combined=None)  # no _calibration_hashes key

    checks, fail_reason, must_fix = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is not None
    assert checks[0]["s"] == "FAIL"
    assert any("lock-tool-hashes.sh" in m for m in must_fix), must_fix


@pytest.mark.unit
def test_tamper_then_restore(tmp_path: Path) -> None:
    """Adding/modifying an anchor after locking must FAIL; restoring must PASS."""
    cal_dir = tmp_path / "calibration"
    cal_dir.mkdir()
    deps = tmp_path / "deps.json"

    # Lock the empty scaffolding state.
    _write_deps(deps, _compute_combined(cal_dir))
    _, fail_reason, _ = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is None

    # Tamper: drop in a real anchor file (Phase 2/3 will author these).
    (cal_dir / "情感落地-high.md").write_text(
        "## excerpt\n\n## expected_band\n\n## rationale\n", encoding="utf-8"
    )
    checks, fail_reason, must_fix = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is not None
    assert checks[0]["s"] == "FAIL"
    assert checks[0]["r"].lower().startswith("calibration")  # terse FAIL reason
    assert any("lock-tool-hashes.sh" in m for m in must_fix), must_fix

    # Restore: remove the anchor file, return to locked state.
    (cal_dir / "情感落地-high.md").unlink()
    _, fail_reason, _ = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is None


@pytest.mark.unit
def test_multiple_anchors_content_change_detected(tmp_path: Path) -> None:
    """After authoring several anchors and locking, editing one's content fails."""
    cal_dir = tmp_path / "calibration"
    cal_dir.mkdir()
    deps = tmp_path / "deps.json"

    for name in ("情感落地-high", "情感落地-mid", "情感落地-low"):
        (cal_dir / f"{name}.md").write_text(f"## excerpt\n\n## {name}\n", encoding="utf-8")
    _write_deps(deps, _compute_combined(cal_dir))
    _, fail_reason, _ = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is None

    # Silent content drift inside an existing file.
    (cal_dir / "情感落地-mid.md").write_text("## excerpt\n\nTAMPERED\n", encoding="utf-8")
    checks, fail_reason, _ = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is not None
    assert checks[0]["s"] == "FAIL"


@pytest.mark.unit
def test_nested_subdirectories_included(tmp_path: Path) -> None:
    """Anchors may live in per-dimension subdirs; all must be in the combined hash."""
    cal_dir = tmp_path / "calibration"
    sub = cal_dir / "情感落地"
    sub.mkdir(parents=True)
    (sub / "high.md").write_text("## excerpt\n\n## high\n", encoding="utf-8")
    deps = tmp_path / "deps.json"
    _write_deps(deps, _compute_combined(cal_dir))

    _, fail_reason, _ = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is None

    # Add a sibling subdir file without re-locking -> FAIL.
    sub2 = cal_dir / "叙事张力"
    sub2.mkdir()
    (sub2 / "mid.md").write_text("## excerpt\n\n## mid\n", encoding="utf-8")
    checks, fail_reason, _ = check_calibration_integrity(cal_dir, deps)
    assert fail_reason is not None
