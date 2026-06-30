from __future__ import annotations

import string

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from shenbi.gates.g3_independence import scoring_independence_status

agent_id = st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=20)
skill = st.sampled_from(["shenbi-worldbuilding", "shenbi-chapter-drafting"])


@given(skill=skill)
@settings(max_examples=40, deadline=None)
def test_no_scorer_recorded_fails_closed(skill: str) -> None:
    """G3.4 fail-closed：progress.json 存在但无 current_scorer_agent → FAIL（空转 bug 的正确化）。"""
    status, _ = scoring_independence_status({"agent_trace": {skill: "agent-1"}}, skill)
    assert status == "FAIL"


@given(skill=skill)
@settings(max_examples=40, deadline=None)
def test_empty_progress_fails_closed(skill: str) -> None:
    status, _ = scoring_independence_status({}, skill)
    assert status == "FAIL"


@given(skill=skill, gen=agent_id)
@settings(max_examples=80, deadline=None)
def test_same_agent_fails(skill: str, gen: str) -> None:
    """生成者与评分者同一 agent（同源自评）→ FAIL。"""
    status, _ = scoring_independence_status(
        {"agent_trace": {skill: gen}, "current_scorer_agent": gen}, skill
    )
    assert status == "FAIL"


@given(skill=skill, gen=agent_id, scorer=agent_id)
@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
def test_different_agents_pass_only_when_distinct(skill: str, gen: str, scorer: str) -> None:
    """生成者与评分者不同 agent（独立评分）→ PASS。"""
    assume(scorer != gen)
    status, reason = scoring_independence_status(
        {"agent_trace": {skill: gen}, "current_scorer_agent": scorer}, skill
    )
    assert status == "PASS"
    assert reason == ""


@given(skill=skill)
@settings(max_examples=40, deadline=None)
def test_scorer_present_no_gen_trace_passes(skill: str) -> None:
    """有独立评分者、无该技能生成 trace（无法证同源）→ 不能判同源 → PASS。"""
    status, _ = scoring_independence_status({"current_scorer_agent": "scorer-9"}, skill)
    assert status == "PASS"
