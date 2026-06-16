"""G4 checker for shenbi-genre-config."""

from __future__ import annotations
from typing import Any
import json
from pathlib import Path

from shenbi.gates.shared import (
    fail,
    jload,
    passed,
)


def g4_genre_config(fps: list[str], rd: str | None = None) -> str:
    """Genre config: valid JSON, fatigue_words array, audit_dimensions >= 5,
    chapter_word.default >= 1000.
    """
    c: list[dict[str, Any]] = []
    mf = []
    project_dir = str(Path(fps[0]).parent.parent) if fps else ""
    pd = Path(project_dir)

    gc_path = pd / "genre-config.json"
    if not gc_path.exists():
        mf.append("G4.gc.not_found")
    else:
        try:
            data = jload(str(gc_path))
            c.append({"id": "G4.gc.json_valid", "s": "PASS"})

            # fatigue_words array
            fw = data.get("fatigueWords") or data.get("fatigue_words") or {}
            if isinstance(fw, dict):
                has_words = any(isinstance(v, list) and len(v) > 0 for v in fw.values())
                if has_words:
                    c.append({"id": "G4.gc.fatigue_words", "s": "PASS"})
                else:
                    mf.append("G4.gc.fatigue_words:empty")
            elif isinstance(fw, list) and len(fw) > 0:
                c.append({"id": "G4.gc.fatigue_words", "s": "PASS"})
            else:
                mf.append("G4.gc.fatigue_words:missing")

            # audit_dimensions >= 5
            ad = data.get("auditDimensions") or data.get("audit_dimensions") or {}
            ad_count = len(ad) if isinstance(ad, dict) else (len(ad) if isinstance(ad, list) else 0)
            if ad_count < 5:
                mf.append(f"G4.gc.audit_dimensions:{ad_count}<5")
            else:
                c.append({"id": "G4.gc.audit_dimensions", "s": "PASS", "count": ad_count})

            # chapter_word.default (optional: SKILL.md schema has pacing but not chapter_word;
            # if present, validate it; if absent, skip without failing)
            cw = data.get("chapter_word") or data.get("chapterWord")
            if cw is not None:
                cw_default = cw.get("default", 0) if isinstance(cw, dict) else 0
                if cw_default < 1000:
                    mf.append(f"G4.gc.chapter_word:{cw_default}<1000")
                else:
                    c.append({"id": "G4.gc.chapter_word", "s": "PASS", "default": cw_default})
            else:
                c.append(
                    {
                        "id": "G4.gc.chapter_word",
                        "s": "SKIP",
                        "note": "chapter_word field not present (optional)",
                    }
                )

        except (json.JSONDecodeError, OSError):
            mf.append("G4.gc.invalid_json")

    if mf:
        return fail("G4-genre-config", c, "scoring", mf)
    return passed("G4-genre-config", c)
