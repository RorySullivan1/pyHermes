"""
A rendered document as a file to send: the PDF exporter's side of an attachment.

The exporter renders and the delivery layer carries. This module is the one
place the two meet, and the dependency runs one way: ``svc.pdf`` builds an
``Attachment`` and ``svc.delivery`` never learns what a PDF or a profile is.
"""

from __future__ import annotations

from svc.builder.document import Document
from svc.delivery.message import Attachment

from .exporter import render_pdf
from .profile import SCREEN, PdfProfile

__all__ = ["PDF_MIME_TYPE", "pdf_attachment"]

PDF_MIME_TYPE = "application/pdf"


def pdf_attachment(document: Document, filename: str, profile: PdfProfile = SCREEN) -> Attachment:
    """
    ``document`` rendered under ``profile``, as an ``application/pdf`` attachment.

    ``SCREEN`` is the default here while ``PRINT`` is :func:`render_pdf`'s: a
    PDF built to be attached is built to be read on a screen. A profile that
    keeps every image at full resolution leaves a ``size_hint`` naming
    ``SCREEN``, which the message's size budget quotes if the send is too big.

    Raises:
        MessageError: If ``filename`` is not a bare file name.
        PdfError: If the document cannot be rendered.
    """
    return Attachment(
        data=render_pdf(document, profile),
        filename=filename,
        mime_type=PDF_MIME_TYPE,
        size_hint=_size_hint(profile),
    )


def _size_hint(profile: PdfProfile) -> str:
    """What would shrink a PDF written under ``profile``, or nothing if already capped."""
    if profile.dpi is not None:
        return ""
    return (
        f"rendered under the {profile.name} profile, which keeps every image at its "
        "source resolution; pdf_attachment(..., profile=SCREEN) caps them at "
        f"{SCREEN.dpi} dpi"
    )
