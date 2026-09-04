"""T1610 (C28 R3b): true-append integrity findings — byte-identical output,
O(1) reads per append.

The old locked_transact shape re-read the whole jsonl per append (O(k^2)
byte traffic; first append has no file to read → 199 reads for 200 appends).
Its write path went through tempfile+os.replace (never Path.write_text), so
the discriminating spy is read_text, not write_text.
"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.pipeline.dispatch_helper import _append_integrity_findings


def test_append_output_matches_and_reads_constant(tmp_path: Path, monkeypatch: object) -> None:

    target = tmp_path / "chapters" / "chapter-1.md"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    out = tmp_path / "audits" / ".integrity-findings-1.jsonl"
    reads = {"n": 0}
    real_read = Path.read_text

    def counting(self: Path, *a: object, **k: object) -> str:
        if self == out:
            reads["n"] += 1
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting)  # type: ignore[attr-defined]
    for i in range(200):
        _append_integrity_findings(tmp_path, target, [f"issue-{i}"])
    assert reads["n"] == 0  # was 199: whole-file re-read per append
    reference = "".join(
        json.dumps({"file": "chapters/chapter-1.md", "finding": f"issue-{i}"}, ensure_ascii=False)
        + "\n"
        for i in range(200)
    )
    assert out.read_text(encoding="utf-8") == reference  # byte-identical
