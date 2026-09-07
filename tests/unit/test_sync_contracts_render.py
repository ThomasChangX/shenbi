"""Behavioral tests for sync_contracts render/main (F112, spec #53 C15).

All writes go through tmp_path copies — sync_contracts is the in-repo
mutator that rewrites deps.json + every SKILL.md (never operate on real files).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import shenbi.sync_contracts as sc


def test_render_body_view_lists_roles() -> None:
    view = sc.render_body_view("shenbi-x", {"reads": ["a.md"], "writes": ["b.md"], "updates": []})
    assert "## 数据契约" in view
    assert "- **Reads:** a.md" in view
    assert "- **Writes:** b.md" in view
    assert "- **Updates:** none" in view
    assert view.startswith(sc.BODY_BANNER)
    assert sc.BODY_END in view


def test_render_body_into_prepends_when_missing(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("---\nname: x\n---\n\nbody text\n", encoding="utf-8")
    sc.render_body_into(skill_md, {"reads": [], "writes": ["w.md"], "updates": []})
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---\nname: x\n---")  # frontmatter intact
    assert sc.BODY_BANNER in text
    assert "body text" in text
    # idempotent: re-render is replace, not append
    sc.render_body_into(skill_md, {"reads": [], "writes": ["w.md"], "updates": []})
    assert skill_md.read_text(encoding="utf-8") == text


def test_render_body_into_replaces_existing_block(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    old_block = sc.render_body_view("x", {"reads": [], "writes": ["old"], "updates": []})
    skill_md.write_text(f"---\nname: x\n---\n{old_block}tail\n", encoding="utf-8")
    sc.render_body_into(skill_md, {"reads": [], "writes": ["new"], "updates": []})
    text = skill_md.read_text(encoding="utf-8")
    assert "**Writes:** new" in text
    assert "**Writes:** old" not in text
    assert "tail" in text


def test_render_body_into_no_frontmatter_is_noop(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    original = "no frontmatter here\n"
    skill_md.write_text(original, encoding="utf-8")
    sc.render_body_into(skill_md, {"reads": [], "writes": ["w"], "updates": []})
    # F130 branch: warns and leaves the file untouched (not silent)
    assert skill_md.read_text(encoding="utf-8") == original


def test_write_json_creates_parents_and_content(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "out.json"
    sc._write_json(target, {"k": "值"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"k": "值"}
    assert target.read_text(encoding="utf-8").endswith("\n")


def _make_tmp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Point sync_contracts module constants at a tmp copy; return paths."""
    skills = tmp_path / "skills"
    (skills / "shenbi-alpha").mkdir(parents=True)
    (skills / "shenbi-alpha" / "SKILL.md").write_text(
        "---\nname: shenbi-alpha\ncontract:\n  kind: artifact\n"
        "  reads: [truth/a.md]\n  writes: [out/alpha.md]\n  updates: []\n---\n\nalpha body\n",
        encoding="utf-8",
    )
    deps = tmp_path / "deps.json"
    deps.write_text(
        json.dumps(
            {"t2-phases": {"p1": {"prerequisites": ["shenbi-alpha"], "expected_outputs": []}}}
        ),
        encoding="utf-8",
    )
    dag = tmp_path / "dag.json"
    index = tmp_path / "index.json"
    monkeypatch.setattr(sc, "SKILLS", skills)
    monkeypatch.setattr(sc, "DEPS_PATH", deps)
    monkeypatch.setattr(sc, "DAG_PATH", dag)
    monkeypatch.setattr(sc, "INDEX_PATH", index)
    return {"skills": skills, "deps": deps, "dag": dag, "index": index}


def test_main_end_to_end_regenerates_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _make_tmp_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(
        sc,
        "load_all_contracts",
        lambda: {
            "shenbi-alpha": {
                "kind": "artifact",
                "reads": ["truth/a.md"],
                "writes": ["out/alpha.md"],
                "updates": [],
            }
        },
    )
    # real registry is read-only; keep the production loader for registry
    assert sc.main() == 0
    # deps.json: expected_outputs regenerated in place, org fields preserved
    deps_out = json.loads(paths["deps"].read_text(encoding="utf-8"))
    assert deps_out["t2-phases"]["p1"]["expected_outputs"] == ["out/alpha.md"]
    # dag + index written
    assert paths["dag"].exists()
    assert paths["index"].exists()
    index_out = json.loads(paths["index"].read_text(encoding="utf-8"))
    assert index_out["truth/a.md"]["reads"] == ["shenbi-alpha"]
    # SKILL.md got the auto block and kept its body
    skill_text = (paths["skills"] / "shenbi-alpha" / "SKILL.md").read_text(encoding="utf-8")
    assert sc.BODY_BANNER in skill_text
    assert "alpha body" in skill_text


def test_main_bails_when_no_contracts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_tmp_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "load_all_contracts", dict)
    assert sc.main() == 1


def test_main_fails_closed_on_corrupt_deps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _make_tmp_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(
        sc,
        "load_all_contracts",
        lambda: {
            "shenbi-alpha": {
                "kind": "artifact",
                "reads": ["truth/a.md"],
                "writes": ["out/alpha.md"],
                "updates": [],
            }
        },
    )
    paths["deps"].write_text("{corrupt", encoding="utf-8")
    assert sc.main() == 1
    # fail-closed: no partial artifact writes before the deps bail
    assert not paths["dag"].exists()
    assert not paths["index"].exists()
