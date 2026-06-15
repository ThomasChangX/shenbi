"""Shenbi novel-writing AI skill framework.

Submodules:
    - exceptions: typed exception hierarchy
    - logging: structlog configuration
    - scoring: rubric-based 0-100 scorer
    - phase_runner: T2/T3 phase state machine
    - summarize_round: round aggregation + G7 close
    - update_progress: progress.json single-writer
    - gates: G0-G7 gate enforcement (forwarder until PR-19)
    - dispatcher: sub-agent dispatch (forwarder until PR-20)
"""

__version__ = "0.1.0"
