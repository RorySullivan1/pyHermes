"""
The QR renderer: a URL becomes the image a ``QrCode`` takes (#344).

A sibling of ``pyhermes.math`` on the same terms. It imports the builder, the
builder never imports it, and segno is the ``[qr]`` extra, imported lazily,
so the core install stays Jinja2-only.
"""

from .adapter import available, qr_code, render_qr
from .exceptions import BackendMissingError, QrError

__all__ = ["BackendMissingError", "QrError", "available", "qr_code", "render_qr"]
