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

from .attachment import PDF_MIME_TYPE, pdf_attachment
from .exceptions import BackendMissingError, PdfError, ProfileError, UnreachableResourceError
from .exporter import available, layout, page_count, render_pdf, save_pdf
from .profile import PDF_VARIANTS, PRINT, SCREEN, TAGGED, PdfProfile

__all__ = [
    "BackendMissingError",
    "available",
    "layout",
    "PdfError",
    "PDF_VARIANTS",
    "PdfProfile",
    "PRINT",
    "ProfileError",
    "SCREEN",
    "TAGGED",
    "UnreachableResourceError",
    "page_count",
    "PDF_MIME_TYPE",
    "pdf_attachment",
    "render_pdf",
    "save_pdf",
]
