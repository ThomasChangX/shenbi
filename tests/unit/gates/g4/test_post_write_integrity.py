"""Tests for the G4 checker that consumes post-write integrity findings.

Probe2 escalation-1 (2026-09-30): persisted findings are append-only and were
consumed verbatim — one transient finding (a truncated audit write, later
rewritten complete and settled) permanently poisoned every later G4 composite
for that chapter. The checker now revalidates each finding against current
disk state (raw path, then de-staged twin) and drops non-reproducing entries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.gates.g4.generic import _merge_pwi_into_result, g4_post_write_integrity


def _write_findings(project_dir: Path, chapter: int, findings: list[dict[str, Any]]) -> None:
    p = project_dir / "audits" / f".integrity-findings-{chapter}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\n".join(json.dumps(f, ensure_ascii=False) for f in findings) + "\n",
        encoding="utf-8",
    )


class TestG4PostWriteIntegrity:
    def test_no_findings_passes(self, tmp_path):
        result = g4_post_write_integrity(tmp_path, chapter=1)
        assert result["status"] == "PASS"

    def test_model_leakage_fails(self, tmp_path):
        ch = tmp_path / "chapters" / "chapter-56.md"
        ch.parent.mkdir(parents=True)
        ch.write_text("Revision complete. 全文已改写。\n", encoding="utf-8")
        _write_findings(
            tmp_path,
            56,
            [
                {
                    "file": "chapters/chapter-56.md",
                    "finding": "G4.pi.model_leakage:chapter-56.md — leak",
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=56)
        assert result["status"] == "FAIL"
        assert any("model_leakage" in c["id"] for c in result["checks"])

    def test_fence_imbalance_warns(self, tmp_path):
        ch = tmp_path / "chapters" / "chapter-1.md"
        ch.parent.mkdir(parents=True)
        ch.write_text("正文\n```\n未闭合围栏\n", encoding="utf-8")
        _write_findings(
            tmp_path,
            1,
            [
                {
                    "file": "chapters/chapter-1.md",
                    "finding": "G4.pi.fence_imbalance:chapter-1.md — odd",
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=1)
        assert result["status"] == "WARN"

    def test_stale_finding_dropped_after_staging_commit(self, tmp_path):
        """Probe2 escalation-1 exact scenario: the finding fired on a
        truncated staging write; the complete rewrite settled to audits/.
        The stale entry must not poison later G4 composites.
        """
        audit = tmp_path / "audits" / "chapter-1-foreshadowing.md"
        audit.parent.mkdir(parents=True)
        audit.write_text(
            "## 审计报告\n**结果**: 有瑕疵\n\n- [BLOCKING] 发现一条\n",
            encoding="utf-8",
        )
        _write_findings(
            tmp_path,
            1,
            [
                {
                    "file": "staging/audits/chapter-1-foreshadowing.md",
                    "finding": (
                        "G4.ac.no_verdict:chapter-1-foreshadowing.md — "
                        "audit file contains no verdict/conclusion marker"
                    ),
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=1)
        assert result["status"] == "PASS"
        assert result["checks"] == []

    def test_missing_file_finding_dropped(self, tmp_path):
        _write_findings(
            tmp_path,
            2,
            [
                {
                    "file": "chapters/chapter-2.md",
                    "finding": "G4.pi.model_leakage:chapter-2.md — leak",
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=2)
        assert result["status"] == "PASS"

    def test_reproduced_no_verdict_kept_via_destaged_twin(self, tmp_path):
        """A genuinely bad settled audit must NOT be pardoned by the
        staging-path normalization — the de-staged twin re-check fails.
        """
        audit = tmp_path / "audits" / "chapter-3-audit.md"
        audit.parent.mkdir(parents=True)
        audit.write_text("## 审计过程\n" + ("逐条核对了伏笔池与正文。\n" * 60), encoding="utf-8")
        _write_findings(
            tmp_path,
            3,
            [
                {
                    "file": "staging/audits/chapter-3-audit.md",
                    "finding": (
                        "G4.ac.no_verdict:chapter-3-audit.md — "
                        "audit file contains no verdict/conclusion marker"
                    ),
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=3)
        assert result["status"] == "FAIL"
        assert any("no_verdict" in c["id"] for c in result["checks"])

    def test_unknown_prefix_kept_conservatively(self, tmp_path):
        """Future finding classes cannot be re-mapped — keep them (when the
        file exists; a missing file drops the finding regardless of prefix).
        """
        ch = tmp_path / "chapters" / "chapter-4.md"
        ch.parent.mkdir(parents=True)
        ch.write_text("正文\n", encoding="utf-8")
        _write_findings(
            tmp_path,
            4,
            [
                {
                    "file": "chapters/chapter-4.md",
                    "finding": "G4.zz.future_check:chapter-4.md — unknown",
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=4)
        # Unknown prefixes keep the finding but keep the default WARN class
        # (only _POST_WRITE_FAIL_PREFIXES escalate to FAIL).
        assert result["status"] == "WARN"
        assert any("future_check" in c["id"] for c in result["checks"])

    def test_reproduced_fail_finding_enters_must_fix(self, tmp_path):
        ch = tmp_path / "chapters" / "chapter-5.md"
        ch.parent.mkdir(parents=True)
        ch.write_text("Revision complete. 全文已改写。\n", encoding="utf-8")
        _write_findings(
            tmp_path,
            5,
            [
                {
                    "file": "chapters/chapter-5.md",
                    "finding": "G4.pi.model_leakage:chapter-5.md — leak",
                }
            ],
        )
        result = g4_post_write_integrity(tmp_path, chapter=5)
        assert result["status"] == "FAIL"
        assert any("model_leakage" in mf for mf in result["must_fix"])


class TestMergePwiIntoResult:
    def test_pwi_fail_propagates_must_fix(self):
        """A reproduced integrity finding must reach must_fix — the
        generic_failure '(no must_fix details)' death loop only closes when
        _classify_g4_failures can see the strings.
        """
        base = json.dumps({"status": "PASS", "checks": [], "must_fix": []})
        pwi = {
            "status": "FAIL",
            "checks": [{"id": "G4.pi.model_leakage", "s": "FAIL", "r": "leak"}],
            "must_fix": ["G4.pi.model_leakage:chapter-9.md — leak"],
        }
        merged = json.loads(_merge_pwi_into_result(base, pwi))
        assert merged["status"] == "FAIL"
        assert "G4.pi.model_leakage:chapter-9.md — leak" in merged["must_fix"]
        assert any(c["id"] == "G4.pi.model_leakage" for c in merged["checks"])

    def test_pwi_pass_leaves_result_untouched(self):
        base = json.dumps({"status": "PASS", "checks": [], "must_fix": []})
        pwi = {"status": "PASS", "checks": [], "must_fix": []}
        merged = json.loads(_merge_pwi_into_result(base, pwi))
        assert merged["status"] == "PASS"
        assert merged["must_fix"] == []


def test_vocab_and_dispatch_integrity_findings_fail_the_gate(tmp_path) -> None:
    """Spec #105 M-7: new G4.av.* ids must map to FAIL with must_fix entries.

    Existing post-write tests only cover G4.pi.*; the new gates share the
    _POST_WRITE_FAIL_PREFIXES tuple, so the regression risk is low but was
    previously unpinned.
    """
    import json

    from shenbi.gates.g4.generic import g4_post_write_integrity

    (tmp_path / "audits").mkdir()
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-5.md").write_text("# 第五章\n\n正文。\n", encoding="utf-8")
    (tmp_path / "audits" / "chapter-5-x.md").write_text("严重度: 严重\n", encoding="utf-8")
    (tmp_path / "audits" / "chapter-5-y.md").write_text(
        "- [BLOCKING] 派发完整性：请补齐 `chapters/chapter-5.md` 后重跑\n", encoding="utf-8"
    )
    journal = tmp_path / "audits" / ".integrity-findings-5.jsonl"
    rows = [
        {
            "finding": "G4.av.vocab:chapter-5-x.md — L1:词表外严重度",
            "file": "audits/chapter-5-x.md",
        },
        {
            "finding": "G4.av.dispatch_integrity:chapter-5-y.md — L1:派发完整性签名",
            "file": "audits/chapter-5-y.md",
        },
    ]
    journal.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )

    result = g4_post_write_integrity(tmp_path, chapter=5)
    assert result["status"] == "FAIL", result
    ids = [m.split(":")[0] for m in result.get("must_fix", [])]
    assert "G4.av.vocab" in ids, ids
    assert "G4.av.dispatch_integrity" in ids, ids
