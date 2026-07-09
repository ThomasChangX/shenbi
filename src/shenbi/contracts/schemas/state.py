"""ProgressDoc / SummaryDoc: producer-uncontrolled state files.

progress.json / summary.json are written by shell heredocs and lack unified
writers, so they routinely carry keys the contract layer does not own. They use
``extra: ignore`` (NOT ``forbid``) so loading never fails at runtime. Once the
writers are unified, these upgrade to ``extra: forbid`` (spec 2).

C3 fix from plan review: ProgressDoc/SummaryDoc MUST be ``ignore``; the other
schema models in this package are ``forbid``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ProgressDoc(BaseModel):
    model_config = {"extra": "ignore"}
    skills: dict[str, Any] = {}
    completed_skill_names: list[str] = []
    scoring_history: list[Any] = []


class SummaryDoc(BaseModel):
    model_config = {"extra": "ignore"}
    t1_scores: dict[str, Any] = {}
    t2_scores: dict[str, Any] = {}
    t3_scores: dict[str, Any] = {}
