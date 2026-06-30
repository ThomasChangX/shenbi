from pathlib import Path

from shenbi.contracts import load_contract, requires_independent_agent


def _write_skill(tmp_path: Path, skill: str, fm: str) -> Path:
    skill_dir = tmp_path / "skills" / skill
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{fm}\n---\n# body\n", encoding="utf-8")
    return path


def test_dict_form_reads_extract_file_and_keep_fields(tmp_path, monkeypatch):
    _write_skill(
        tmp_path,
        "shenbi-test-dict",
        "name: shenbi-test-dict\n"
        "contract:\n  kind: report\n  reads:\n"
        "    - {file: truth/audit_drift.md, fields: [shortcomings]}\n"
        "    - truth/current_state.md\n"
        "  writes: [audits/chapter-N-dict.md]\n  updates: []\n",
    )
    monkeypatch.setattr("shenbi.contracts.legacy.SKILLS", tmp_path / "skills")
    c = load_contract("shenbi-test-dict")
    assert c["reads"] == ["truth/audit_drift.md", "truth/current_state.md"]
    assert c["read_fields"] == {"truth/audit_drift.md": ["shortcomings"]}


def test_requires_independent_agent_reads_top_level_field(tmp_path, monkeypatch):
    _write_skill(
        tmp_path,
        "shenbi-test-ind",
        "name: shenbi-test-ind\nrequires_independent_agent: true\n"
        "contract:\n  kind: report\n  reads: []\n  writes: [audits/x.md]\n  updates: []\n",
    )
    monkeypatch.setattr("shenbi.contracts.legacy.SKILLS", tmp_path / "skills")
    assert requires_independent_agent("shenbi-test-ind") is True


def test_requires_independent_agent_default_false(tmp_path, monkeypatch):
    _write_skill(
        tmp_path,
        "shenbi-test-noind",
        "name: shenbi-test-noind\n"
        "contract:\n  kind: artifact\n  reads: []\n  writes: [chapters/chapter-N.md]\n  updates: []\n",
    )
    monkeypatch.setattr("shenbi.contracts.legacy.SKILLS", tmp_path / "skills")
    assert requires_independent_agent("shenbi-test-noind") is False
