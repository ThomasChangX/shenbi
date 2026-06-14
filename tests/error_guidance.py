"""User-facing error guidance catalog.

Maps error class names to explanation + suggested action + doc URL.
Consumed by CLI boundary to display actionable error messages.
"""

from typing import NamedTuple


class ErrorGuidance(NamedTuple):
    explanation: str
    action: str
    doc_url: str | None


ERROR_GUIDANCE: dict[str, ErrorGuidance] = {
    "RegistryStaleError": ErrorGuidance(
        explanation="Source files changed since registry.lock.json was built.",
        action="Run: python3 tests/build_registry.py\nThen commit updated lockfile.",
        doc_url="docs/registry.md#stale-lockfile",
    ),
    "RegistryMissingError": ErrorGuidance(
        explanation="registry.lock.json does not exist.",
        action="Run: python3 tests/build_registry.py",
        doc_url="docs/registry.md#missing-lockfile",
    ),
    "GateMarkerMissingError": ErrorGuidance(
        explanation="Scoring requires gate markers as proof gates passed.",
        action="Run the listed gates first, then retry scoring.",
        doc_url="docs/gates.md#missing-markers",
    ),
    "SchemaValidationError": ErrorGuidance(
        explanation="Skill output did not match its schema.",
        action="Re-run skill execution. If persistent, review meta.yaml.writes.",
        doc_url="docs/schemas.md#validation-errors",
    ),
    "SubAgentTimeoutError": ErrorGuidance(
        explanation="Sub-agent did not respond within timeout.",
        action="Check sub-agent health. Increase SHENBI_SUBAGENT_TIMEOUT if needed.",
        doc_url="docs/dispatcher.md#timeouts",
    ),
    "ToolTamperError": ErrorGuidance(
        explanation="A locked framework tool was modified without re-locking.",
        action="Run: bash tests/lock-tool-hashes.sh\nIf unintended, investigate tampering.",
        doc_url="docs/integrity.md#tool-tamper",
    ),
}


def get_guidance(error: Exception) -> ErrorGuidance | None:
    """Get user-facing guidance for an error."""
    return ERROR_GUIDANCE.get(type(error).__name__)
