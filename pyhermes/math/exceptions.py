"""
Exceptions for the equation renderer.

:class:`MathError` is a **sibling** of ``EmailBuilderError``, for the reason
``DataError`` is: a missing backend is setup, not a wrong document. A bad
argument still raises the builder's own ``ValidationError``.
"""


class MathError(Exception):
    """Base exception for everything the equation renderer rejects that is not data."""


class BackendMissingError(MathError):
    """Raised when matplotlib is not installed; the message names the install."""


class MathSyntaxError(MathError, ValueError):
    """Raised when mathtext cannot parse a source; names the source and the symbol."""
