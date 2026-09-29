"""
Exceptions for the data adapters.

:class:`DataError` is a **sibling** of ``EmailBuilderError``, for the reason
``PdfError`` is: a missing optional backend is a setup problem, not a document
that is wrong. A frame whose *shape* is wrong still raises the builder's own
``ValidationError``, because that is a data problem the builder already names.
"""


class DataError(Exception):
    """Base exception for everything the data adapters reject that is not data."""


class BackendMissingError(DataError):
    """Raised when pandas or matplotlib is not installed.

    Each adapter is an optional extra, so the message names the install that
    fixes it rather than surfacing an ``ImportError`` from the caller's graph.
    """
