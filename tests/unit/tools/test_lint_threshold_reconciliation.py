"""Spec #93 T1b/T1c — threshold reconciliation lint: constant-reading,
containment test, mandatory keyword, --strict FAIL mode.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LINT = REPO_ROOT / "tools" / "lint_threshold_reconciliation.py"


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(LINT), *argv], capture_output=True, text=True)


def _allowlist(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    p = tmp_path / "allowlist.json"
    p.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return p


def _skill_md(tmp_path: Path, constellation: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(
        f"| 卷 | QUEST% | FIRE% | CONSTELLATION% | 检查结果 |\n"
        f"| 标准卷: QUEST 40 FIRE 30 CONSTELLATION {constellation} |\n",
        encoding="utf-8",
    )
    return p


def _entry(skill_md: Path, **overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "skill": "shenbi-pacing-design",
        "pattern": "标准卷: QUEST",
        "keyword": "CONSTELLATION",
        "file": str(skill_md),  # 绝对路径: REPO_ROOT / abs 保持原值
        "checker": "src/shenbi/contracts/skills/pacing_design.py",
    }
    entry.update(overrides)
    return entry


def test_out_of_band_50_warns(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "50-60%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)]))])
    assert r.returncode == 0  # WARN-only (--strict 在 Task 3 接线)
    assert "threshold_drift" in r.stdout and "50-60" in r.stdout


def test_partial_overlap_10_20_rejected(tmp_path: Path) -> None:
    # SKILL 写 10-20 与硬带 [15,40] 相交但不包含 —— 旧相交式放行，包含式必拒
    skill = _skill_md(tmp_path, "10-20%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)]))])
    assert r.returncode == 0
    assert "threshold_drift" in r.stdout and "10-20" in r.stdout


def test_in_band_contained_no_warn(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "15-25%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)]))])
    assert r.returncode == 0
    assert r.stdout == ""


def test_missing_keyword_warns(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "15-25%")
    entry = _entry(skill)
    del entry["keyword"]
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry]))])
    assert r.returncode == 0
    assert "keyword_missing" in r.stdout


def test_bounds_field_ignored(tmp_path: Path) -> None:
    # bounds 已从 schema 删除 —— 即便残留旧字段也不得参与判定 (deletion test)
    skill = _skill_md(tmp_path, "50-60%")
    entry = _entry(skill, bounds=[0, 100])
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry]))])
    assert "threshold_drift" in r.stdout and "50-60" in r.stdout  # 常量带赢，残留 bounds 失效


# --- T1c: --strict FAIL 态 (spec #93 Task 3) ---


def test_repo_allowlist_strict_clean() -> None:
    r = _run(["--strict"])
    assert r.returncode == 0
    assert r.stdout == ""


def test_strict_drift_fails(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "50-60%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)])), "--strict"])
    assert r.returncode == 1
    assert "threshold_drift" in r.stdout


def test_strict_partial_overlap_fails(tmp_path: Path) -> None:
    # 包含式的核心增量判据面: 相交不包含 → strict FAIL (旧相交式下此断言红)
    skill = _skill_md(tmp_path, "10-20%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)])), "--strict"])
    assert r.returncode == 1
    assert "threshold_drift" in r.stdout and "10-20" in r.stdout


def test_strict_keyword_missing_fails(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "15-25%")
    entry = _entry(skill)
    del entry["keyword"]
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry])), "--strict"])
    assert r.returncode == 1
    assert "keyword_missing" in r.stdout


def test_non_strict_drift_still_exits_zero(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "50-60%")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [_entry(skill)]))])
    assert r.returncode == 0
    assert "threshold_drift" in r.stdout


# --- 存在性 FAIL 面 (Task 2 审查 M-1 rider: 恢复被旧重写删除的覆盖) ---


def test_file_missing_warns_strict_fails(tmp_path: Path) -> None:
    entry = _entry(tmp_path / "ghost.md")  # file 字段指向不存在文件
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry])), "--strict"])
    assert r.returncode == 1
    assert "file_missing" in r.stdout


def test_checker_missing_warns_strict_fails(tmp_path: Path) -> None:
    skill = _skill_md(tmp_path, "15-25%")
    entry = _entry(skill, checker="src/none.py")
    r = _run(["--allowlist", str(_allowlist(tmp_path, [entry])), "--strict"])
    assert r.returncode == 1
    assert "checker_missing" in r.stdout
