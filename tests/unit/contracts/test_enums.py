from __future__ import annotations

from typing import get_args

from shenbi.contracts.enums import ALL_ENUMS, ActorRole, CPZone, Severity, Verdict


def test_severity_members() -> None:
    assert set(get_args(Severity)) == {"BLOCKING", "CRITICAL", "MINOR"}


def test_verdict_members() -> None:
    assert set(get_args(Verdict)) == {"通过", "有瑕疵", "不通过"}


def test_cpzone_members() -> None:
    assert set(get_args(CPZone)) == {"GREEN", "ORANGE", "RED"}


def test_actor_role_members() -> None:
    assert set(get_args(ActorRole)) == {"GENERATOR", "SCORER", "GATE", "SKILL", "HUMAN"}


def test_all_enums_complete() -> None:
    assert set(ALL_ENUMS.keys()) == {"Severity", "Verdict", "CPZone", "ActorRole"}
