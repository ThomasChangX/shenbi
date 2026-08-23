"""F345: parallel audit waves must run G3 for requires_independent skills."""

import json
from pathlib import Path
from typing import Any

from shenbi.pipeline.chapter_loop import _g3_parallel_wave


def _flatten(data: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(v: Any) -> None:
        if isinstance(v, dict) and "gate" in v:
            out.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(data)
    return out


def _status(e: dict[str, Any]) -> Any:
    r = e.get("result")
    return r.get("status") if isinstance(r, dict) else e.get("status")


def test_g3_parallel_wave_records_manifest(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    # review-* audit skills are requires_independent; worldbuilding is not
    skills = ["shenbi-review-pacing", "shenbi-worldbuilding"]
    g3_results = _g3_parallel_wave(skills, project, chapter=3)
    manifest = json.loads((project / "pipeline-manifest.json").read_text(encoding="utf-8"))
    per_skill = manifest["gates"]["chapter_loop"]["3"]
    g3_skills = {
        skill
        for skill, gates in per_skill.items()
        if "G3" in gates and _status(gates["G3"]) == "FAIL"
    }
    assert g3_skills == {"shenbi-review-pacing"}
    assert len(g3_results) == 1


def test_g3_parallel_wave_no_independent_skills_noop(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    g3_results = _g3_parallel_wave(["shenbi-worldbuilding"], project, chapter=3)
    assert g3_results == []
    assert not (project / "pipeline-manifest.json").exists()
