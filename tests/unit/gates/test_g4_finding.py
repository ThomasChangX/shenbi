"""finding() emitter contract tests (spec #88 T1)."""

from __future__ import annotations

from shenbi.gates.shared import finding


class TestFindingEmitter:
    def test_id_only(self):
        assert finding("cd.no_hook") == "G4.cd.no_hook"

    def test_id_and_file(self):
        assert finding("cd.no_hook", file="chapters/ch001.md") == "G4.cd.no_hook:chapters/ch001.md"

    def test_full(self):
        assert finding("ss.facts_ops", detail="非法 op", file="truth/facts.md") == (
            "G4.ss.facts_ops:truth/facts.md:非法 op"
        )

    def test_id_and_detail_no_file(self):
        assert finding("cd.counter", detail="缺锚") == "G4.cd.counter:缺锚"

    def test_prefix_never_doubled(self):
        # 防 helper 无脑加前缀造 G4.G4.——传入已带前缀时先剥
        assert finding("G4.cd.title") == "G4.cd.title"
