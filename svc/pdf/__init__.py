"""
The PDF exporter: a rendered document, laid onto sheets.

The third exporter beside ``svc.gmail`` and ``svc.outlook``, and on the same
contract — it owns its wire format and nothing else. What it adds to that
contract is a **resource policy**: it makes no network requests, serving
``cid:`` references from the document's own manifest and refusing every other
URL by name.

WeasyPrint is an optional extra (``pip install "pyhermes[pdf]"``), imported
lazily, so the core install stays Jinja2-only and an AST test holds it there.
"""

from .exceptions import BackendMissingError, PdfError, UnreachableResourceError
from .exporter import available, layout, page_count, render_pdf, save_pdf

__all__ = [
    "BackendMissingError",
    "available",
    "layout",
    "PdfError",
    "UnreachableResourceError",
    "page_count",
    "render_pdf",
    "save_pdf",
]
