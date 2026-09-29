"""
The data adapters: a DataFrame becomes a table, a Figure becomes a chart.

A sibling of ``pyhermes.pdf`` and on the same terms. It imports the builder, the
builder never imports it, and each backend is an optional extra imported
lazily, so the core install stays Jinja2-only and an AST test holds it there.
``[data]`` brings pandas and ``[charts]`` brings matplotlib, separately, so a
table author does not install a plotting library.
"""

from .charts import available as charts_available
from .charts import chart_from_figure, image_from_figure
from .exceptions import BackendMissingError, DataError
from .frames import available as frames_available
from .frames import table_from_frame

__all__ = [
    "BackendMissingError",
    "DataError",
    "chart_from_figure",
    "charts_available",
    "image_from_figure",
    "frames_available",
    "table_from_frame",
]
