"""
Custom exceptions for the email builder service, and the warnings for its soft limits.
"""

import sys
import warnings


class EmailBuilderError(Exception):
    """Base exception for all email builder errors."""

    pass


class TemplateError(EmailBuilderError):
    """Raised when a template cannot be loaded or rendered."""

    pass


class ValidationError(EmailBuilderError):
    """Raised when configuration data fails validation."""

    pass


class SizeError(EmailBuilderError):
    """Raised when the rendered email exceeds the size limit."""

    pass


class SizeWarning(UserWarning):
    """A rendered email or an assembled message is over its soft size threshold."""


class PrintQualityWarning(UserWarning):
    """An image is short of the pixels it needs to print at the configured dpi."""


def warn_caller(message: str, category: type[Warning]) -> None:
    """
    Warn at the first frame outside this package, whatever the call depth.

    A size check runs from ``render()``, ``Email.render()``, a builder shortcut
    or a brochure's constructor, so no fixed ``stacklevel`` names the caller.
    """
    frame = sys._getframe(1)
    level = 2
    while frame is not None and frame.f_globals.get("__name__", "").partition(".")[0] == "pyhermes":
        frame = frame.f_back  # type: ignore[assignment]
        level += 1
    warnings.warn(message, category, stacklevel=level)
