"""
The data adapters: a DataFrame becomes a table, a Figure becomes a chart.

A sibling of ``svc.pdf`` and on the same terms. It imports the builder, the
builder never imports it, and each backend is an optional extra imported
lazily, so the core install stays Jinja2-only and an AST test holds it there.
``[data]`` brings pandas and ``[charts]`` brings matplotlib, separately, so a
table author does not install a plotting library.
"""

from .exceptions import BackendMissingError, DataError
from .frames import available as frames_available
from .frames import table_from_frame

__all__ = [
    "BackendMissingError",
    "DataError",
    "frames_available",
    "table_from_frame",
]
