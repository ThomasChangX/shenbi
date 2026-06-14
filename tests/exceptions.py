"""Typed exception hierarchy for Shenbi framework.

All errors inherit from ShenbiError. Each error carries structured
context for logging, failure catalog (P3), and user-facing guidance.

"""

from typing import Any


class ShenbiError(Exception):
    """Base for all Shenbi errors."""

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        **context: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = context

    def to_dict(self) -> dict[str, Any]:
        """Serialize for failure catalog and structured logging."""
        return {
            "error_class": type(self).__name__,
            "message": self.message,
            "context": self.context,
            "cause_class": type(self.cause).__name__ if self.cause else None,
            "cause_message": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message


class FrameworkError(ShenbiError):
    """Framework infrastructure issue."""


class RegistryError(FrameworkError):
    """Registry lockfile issues."""


class RegistryStaleError(RegistryError):
    """Source files changed since lockfile was built."""

    def __init__(self, mismatches: list[tuple[str, str, str]], lockfile_generated_at: str) -> None:
        super().__init__(
            f"{len(mismatches)} source files changed since lockfile built at "
            f"{lockfile_generated_at}",
            mismatches=mismatches[:5],
            total_mismatches=len(mismatches),
            lockfile_generated_at=lockfile_generated_at,
        )
        self.mismatches = mismatches


class RegistryMissingError(RegistryError):
    """Lockfile doesn't exist."""


class RegistryCorruptError(RegistryError):
    """Lockfile is corrupt."""


class SchemaValidationError(FrameworkError):
    """Pydantic schema validation failed."""


class DefectApplicationError(FrameworkError):
    """Defect patch failed to apply."""


class MigrationError(FrameworkError):
    """Skill migration failed."""


class DispatcherError(FrameworkError):
    """Sub-agent dispatch failure."""


class SubAgentTimeoutError(DispatcherError):
    """Sub-agent timed out."""


class SubAgentProtocolError(DispatcherError):
    """Sub-agent returned invalid output."""


class SubAgentUnavailableError(DispatcherError):
    """No executor available."""


class ConfigurationError(FrameworkError):
    """Configuration invalid."""


class IntegrityError(ShenbiError):
    """Data integrity violation."""


class ToolTamperError(IntegrityError):
    """Tool modified without re-locking hash."""


class GateError(ShenbiError):
    """Gate check failure (user error)."""

    def __init__(
        self,
        gate: str,
        must_fix: list[str],
        blocked_action: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(
            f"Gate {gate} failed: {len(must_fix)} must-fix items",
            gate=gate,
            must_fix=must_fix,
            blocked_action=blocked_action,
            **context,
        )
        self.gate = gate
        self.must_fix = must_fix
        self.blocked_action = blocked_action


class GateMarkerMissingError(GateError):
    """Required gate markers not found."""

    def __init__(self, gate: str, missing_markers: list[str]) -> None:
        super().__init__(
            gate=gate,
            must_fix=[f"Run gate {m} before scoring" for m in missing_markers],
            blocked_action="scoring",
            missing_markers=missing_markers,
        )


class ScoringError(ShenbiError):
    """Scoring computation failure."""


class ScoringRejectError(ScoringError):
    """Scoring validation rejected the result."""
