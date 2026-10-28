"""facts 测试共享 fixture（plan T2/R6-M1）。"""

from __future__ import annotations

import pytest

from shenbi.facts.schemas import FactsFile


@pytest.fixture
def props_file() -> FactsFile:
    return FactsFile.model_validate(
        {
            "$schema": "shenbi-facts-v1",
            "dim": "props",
            "facts": {
                "火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": ["ch3 老驼所授"]},
            },
            "ops_log": [],
        }
    )
