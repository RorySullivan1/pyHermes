"""
Exceptions for the QR renderer.

:class:`QrError` is a **sibling** of ``EmailBuilderError``, for the reason
``MathError`` is: a missing backend is setup, not a wrong document. A bad URL
still raises the builder's own ``ValidationError``.
"""


class QrError(Exception):
    """Base exception for everything the QR renderer rejects that is not data."""


class BackendMissingError(QrError):
    """Raised when segno is not installed; the message names the install."""
