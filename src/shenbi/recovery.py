"""Automatic recovery strategy definitions.

P-1.C defines interfaces; P-3 (failure catalog) implements recovery logic.
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


from enum import Enum


class RecoveryStrategy(Enum):
    """How to respond when an error occurs."""

    NONE = "none"
    AUTO_RETRY = "auto_retry"
    AUTO_REBUILD = "auto_rebuild"
    HALT = "halt"


RECOVERY_STRATEGIES: dict[str, RecoveryStrategy] = {
    "RegistryStaleError": RecoveryStrategy.AUTO_REBUILD,
    "RegistryMissingError": RecoveryStrategy.AUTO_REBUILD,
    "GateMarkerMissingError": RecoveryStrategy.NONE,
    "SchemaValidationError": RecoveryStrategy.NONE,
    "SubAgentTimeoutError": RecoveryStrategy.AUTO_RETRY,
    "ToolTamperError": RecoveryStrategy.HALT,
}
