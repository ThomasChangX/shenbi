"""Prose↔declaration closure lint tests (spec #58 C20 T1).

Synthetic SKILL.md bodies live in tmp_path (the test_g4_directory.py G0.9
boundary adjudication: tmp_path assembly is not a tests/fixtures artifact).
The real registry loads from docs/framework/truth-files.yaml.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tools.lint_contract_prose import find_violations, main

AUTOGEN = """<!-- AUTO-GENERATED from frontmatter — do not edit -->

## 数据契约

- **Reads:** truth/zz-declared.md
- **Writes:** truth/zz-drift.md
- **Updates:**

<!-- END AUTO-GENERATED -->
"""


def _mk_skill(
    root: Path,
    name: str,
    contract: Mapping[str, object],
    body: str,
    extra_files: Sequence[str] = (),
) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n\n{body}\n\n{AUTOGEN}", encoding="utf-8")
    for f in extra_files:
        (d / f).write_text("reference\n", encoding="utf-8")


def _r1(contracts: Mapping[str, Mapping[str, object]], root: Path):
    r1, _ = find_violations(contracts, root)
    return {(s, r) for s, r, _rule in r1}


def _r2(contracts: Mapping[str, Mapping[str, object]], root: Path):
    _, r2 = find_violations(contracts, root)
    return set(r2)


@pytest.mark.unit
def test_r2_frontmatter_mention_is_not_prose(tmp_path):
    # The write target's filename appears ONLY inside the frontmatter block —
    # declarations are not prose evidence, must still be flagged.
    c = {
        "shenbi-zz": {
            "reads": [],
            "writes": [{"file": "truth/zz-drift.md", "mode": "create_or_overwrite"}],
            "updates": [],
        }
    }
    d = tmp_path / "shenbi-zz"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: shenbi-zz\nother: truth/zz-drift.md\n---\n\n正文零提及。\n",
        encoding="utf-8",
    )
    assert ("shenbi-zz", "truth/zz-drift.md") in _r2(c, tmp_path)


@pytest.mark.unit
def test_r1_undeclared_relative_path_flagged(tmp_path):
    # zzdir/ 不在 truth-files.yaml 词表——registry 层不会兜底
    c = {"shenbi-zz": {"reads": ["truth/zz-declared.md"], "writes": [], "updates": []}}
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "读取 zzdir/zz-undeclared.md 后决策。")
    assert ("shenbi-zz", "zzdir/zz-undeclared.md") in _r1(c, tmp_path)


@pytest.mark.unit
def test_r1_bare_basename_vs_declared_path_passes(tmp_path):
    c = {"shenbi-zz": {"reads": ["characters/protagonist.md"], "writes": [], "updates": []}}
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "先读 protagonist.md 的弧光。")
    assert not any(s == "shenbi-zz" and r == "protagonist.md" for s, r in _r1(c, tmp_path))


@pytest.mark.unit
def test_r1_body_glob_vs_declared_glob_passes(tmp_path):
    c = {"shenbi-zz": {"reads": ["characters/*.md"], "writes": [], "updates": []}}
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "expand 模式读 characters/**/*.md 全量。")
    assert not _r1(c, tmp_path)


@pytest.mark.unit
def test_r1_offset_form_canonicalization_passes(tmp_path):
    c = {
        "shenbi-zz": {
            "reads": ["chapters/chapter-{N-3}.md"],
            "writes": [],
            "updates": [],
        }
    }
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "近章结尾核对 chapters/chapter-(N-3).md。")
    assert not _r1(c, tmp_path)


@pytest.mark.unit
def test_r1_skill_bundle_reference_passes(tmp_path):
    c = {"shenbi-zz": {"reads": [], "writes": [], "updates": []}}
    _mk_skill(
        tmp_path,
        "shenbi-zz",
        c["shenbi-zz"],
        "检查清单见 anti-ai-reference.md。",
        extra_files=["anti-ai-reference.md"],
    )
    assert not _r1(c, tmp_path)


@pytest.mark.unit
def test_r1_autogen_block_not_counted(tmp_path):
    c = {"shenbi-zz": {"reads": ["truth/zz-declared.md"], "writes": [], "updates": []}}
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "无引用正文。")
    # truth/zz-drift.md only appears inside AUTOGEN — must NOT be flagged
    assert not any("zz-drift" in r for _s, r in _r1(c, tmp_path))


@pytest.mark.unit
def test_r1_registry_vocabulary_passes(tmp_path):
    c = {"shenbi-zz": {"reads": [], "writes": [], "updates": []}}
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "读 truth/pending_hooks.md 全文。")
    assert not _r1(c, tmp_path)


@pytest.mark.unit
def test_r2_declared_write_without_body_step_flagged(tmp_path):
    c = {
        "shenbi-zz": {
            "reads": [],
            "writes": [{"file": "truth/zz-drift.md", "mode": "create_or_overwrite"}],
            "updates": [],
        }
    }
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "正文从不提及该产物。")
    assert ("shenbi-zz", "truth/zz-drift.md") in _r2(c, tmp_path)


@pytest.mark.unit
def test_r2_autogen_only_mention_still_flagged(tmp_path):
    # The write target appears ONLY in the AUTO-GENERATED summary block —
    # the exact F812 shape. Must still be a violation.
    c = {
        "shenbi-zz": {
            "reads": [],
            "writes": [{"file": "truth/zz-drift.md", "mode": "create_or_overwrite"}],
            "updates": [],
        }
    }
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "其余正文。")
    assert ("shenbi-zz", "truth/zz-drift.md") in _r2(c, tmp_path)


@pytest.mark.unit
def test_r2_body_step_passes(tmp_path):
    c = {
        "shenbi-zz": {
            "reads": [],
            "writes": [{"file": "truth/zz-drift.md", "mode": "create_or_overwrite"}],
            "updates": [],
        }
    }
    _mk_skill(tmp_path, "shenbi-zz", c["shenbi-zz"], "## 产出\n写出 zz-drift.md 的指导。")
    assert not any(s == "shenbi-zz" for s, _t in _r2(c, tmp_path))


@pytest.mark.unit
def test_meta_skills_exempt(tmp_path):
    c = {"using-shenbi": {"reads": [], "writes": [], "updates": []}}
    _mk_skill(tmp_path, "using-shenbi", c["using-shenbi"], "读 outline/zz-undeclared.md 全量。")
    r1, r2 = find_violations(c, tmp_path)
    assert not r1 and not r2


@pytest.mark.unit
def test_fail_flag_exit_semantics(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(
        "tools.lint_contract_prose.find_violations",
        lambda *a, **k: ([("s", "r", "R1_UNDECLARED")], []),
    )
    assert main(["--fail"]) == 1
    assert main([]) == 0
    monkeypatch.setattr("tools.lint_contract_prose.find_violations", lambda *a, **k: ([], []))
    assert main(["--fail"]) == 0
    out = capsys.readouterr().out
    assert main(["--list-exempt"]) == 0
    out = capsys.readouterr().out
    assert "meta-exempt: using-shenbi" in out
    assert "meta-exempt: shenbi-writing-skills" in out
    assert "allowlist[skill-bundle]" in out
