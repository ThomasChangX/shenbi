"""review_resonance subpackage.

The three-path ``route_block`` model was deleted (spec #33 T1b): production
routing authority is ``pipeline/revision_router.route_chapter_revision``
(reusing ``skill_utils/revision_routing``); the duplicate unwired model with
divergent thresholds was dead code. Confidence calibration lives in
``skill_utils/calibration`` and runs framework-side post-dispatch.
"""

__all__: list[str] = []
