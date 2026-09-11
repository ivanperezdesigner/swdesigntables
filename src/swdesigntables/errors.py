"""Exception and warning hierarchy for swdesigntables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swdesigntables.validation import ValidationReport

__all__ = [
    "DesignTableError",
    "ValidationError",
    "DuplicateColumnError",
    "DuplicateConfigurationError",
    "UnknownColumnError",
    "InvalidNameError",
    "ReservedNameError",
    "UnknownParameterError",
    "DesignTableWarning",
]


class DesignTableError(Exception):
    """Base class for every error raised by this package."""


class ValidationError(DesignTableError):
    """Raised when a table fails validation.

    The full report is available on the ``report`` attribute, so a caller can
    inspect every issue instead of parsing the message.
    """

    def __init__(self, message: str, report: ValidationReport | None = None) -> None:
        super().__init__(message)
        self.report = report


class DuplicateColumnError(ValidationError):
    """Two columns render the same header."""


class DuplicateConfigurationError(ValidationError):
    """Two configurations share a name."""


class UnknownColumnError(ValidationError):
    """A configuration supplies a value for a column that was never declared."""


class InvalidNameError(ValidationError):
    """A configuration, sheet or defined name is not usable in SOLIDWORKS."""


class ReservedNameError(InvalidNameError):
    """A name reserved by SOLIDWORKS was used (for example ``_SWX``)."""


class UnknownParameterError(DesignTableError):
    """A parameter name was requested that is not in the registry."""


class DesignTableWarning(UserWarning):
    """Something is probably a mistake, but the file is still written.

    Promote these to errors with ``-W error::swdesigntables.DesignTableWarning``.
    """
