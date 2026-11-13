"""spec #88 T3: id inventory bidirectional assertions + property invariants."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

IDS = set(
    json.loads(Path("tests/fixtures/g4-id-inventory.json").read_text(encoding="utf-8"))["ids"]
)


def test_retained_keys_in_inventory():
    from shenbi.pipeline.chapter_loop import G4_CHECK_MAP

    assert set(G4_CHECK_MAP) <= IDS


def test_inventory_subset_of_ast_enumeration():
    # 反向防漂：清单 ⊆ 生成器现树枚举（stale id 即红）
    from tools.gen_g4_id_inventory import enumerate_ids

    assert set(enumerate_ids()) >= IDS


@given(st.sampled_from(sorted(IDS)))
def test_any_id_extractable_roundtrip(cid):
    from shenbi.gates.g4.shadow import check_id

    assert check_id(f"G4.{cid}:f:d") == cid or check_id(f"G4.{cid}:f:d").startswith(cid)


@pytest.mark.unit
def test_only_two_active_keys():
    from shenbi.pipeline.chapter_loop import G4_CHECK_MAP

    assert set(G4_CHECK_MAP) == {"transition", "fatigue"}


@pytest.mark.unit
def test_exact_match_not_substring():
    from shenbi.pipeline.chapter_loop import _classify_g4_failures

    hard, soft, warn = _classify_g4_failures(["G4.cd.post_transition_cross:p:t"])
    assert len(hard) == 1 and not soft  # 有意修正：旧子串误判 SOFT


@pytest.mark.unit
def test_dot_boundary_prefix():
    from shenbi.pipeline.chapter_loop import _classify_g4_failures

    _, soft, _ = _classify_g4_failures(["G4.transition.density:p:8>7"])
    assert len(soft) == 1  # 真前缀族仍 SOFT


@pytest.mark.unit
def test_unknown_defaults_hard():
    from shenbi.pipeline.chapter_loop import _classify_g4_failures

    hard, soft, warn = _classify_g4_failures(["G4.future.check:p:x"])
    assert len(hard) == 1


@given(
    st.one_of(
        st.sampled_from(["transition", "fatigue", "transition.x", "fatigue.density"]),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_.", min_size=1, max_size=16),
    )
)
def test_softwarn_implies_covered(seed):
    # property 主不变量：任何被判 SOFT/WARN 的 item，其 extracted id ∈ 覆盖键集
    # （轮4 I2：st.text 无字典导向，纯 text 生成 "transition" 概率天文低——
    #   sampled_from 种子臂保证 SOFT 臂非平凡执行，text 臂保持任意串对抗性）
    from shenbi.pipeline.chapter_loop import _classify_g4_failures

    item = f"G4.{seed}:f:d"
    _, soft, warn = _classify_g4_failures([item])
    for out in (soft, warn):
        for it in out:
            fam = it.split(":", 1)[0][len("G4.") :]
            assert (
                fam == "transition"
                or fam == "fatigue"
                or fam.startswith(("transition.", "fatigue."))
            )
