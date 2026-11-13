"""retry_routing coupling for spec #88 emission-contract rewrites."""

from __future__ import annotations

from shenbi.gates.g4.shadow import check_id
from shenbi.pipeline.retry_routing import classify_retry_family


def test_prop_handoff_gains_content_routing():
    # 有意修正：path-first 消灭后按 G4.cd 前缀路由
    assert classify_retry_family("G4.cd.prop_handoff:chapters/ch025.md:「灯」交接语境") == "content"


def test_xc_new_form_routes_content():
    assert classify_retry_family("G4.XC.pronoun_mismatch:ch1.md:代词违例") == "content"


def test_legacy_xc_colon_form_still_routes_content():
    # legacy 字面保留（历史反馈 blob 兼容）
    assert classify_retry_family("XC:chapter-1.md:角色「X」…") == "content"


def test_check_id_extracts_family_not_path():
    assert check_id("G4.cd.prop_handoff:「灯」交接语境") == "cd.prop_handoff"
