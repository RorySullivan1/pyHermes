"""
Render a document to PDF bytes through WeasyPrint.

The third exporter, on the send adapters' terms: it takes what the builder
produces, owns its own wire format, and owns nothing else. No network, no
credentials, no opinion about where the bytes go afterwards.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from svc.builder.document import Document

from .exceptions import BackendMissingError, UnreachableResourceError
from .fetcher import build_fetcher
from .profile import PRINT, PdfProfile


def available() -> bool:
    """Whether the PDF backend is installed, for a caller that wants to skip."""
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        return False
    return True


def render_pdf(document: Document, profile: PdfProfile = PRINT) -> bytes:
    """
    Render ``document`` to PDF bytes, written under ``profile``.

    The document's own :meth:`~svc.builder.document.Document.render` produces
    the HTML and its :meth:`~svc.builder.document.Document.assets` the images;
    nothing else is read, and nothing is fetched. A reference the manifest
    does not cover raises
    :class:`~svc.pdf.exceptions.UnreachableResourceError` naming the URL.
    ``PRINT`` leaves every image as it arrived; ``SCREEN`` downsamples.

    Raises:
        BackendMissingError: If WeasyPrint is not installed.
        UnreachableResourceError: If the document references a resource this
            exporter will not fetch.
    """
    weasyprint = _backend()
    html = document.render()
    with _own_errors():
        return bytes(
            weasyprint.HTML(string=html, url_fetcher=build_fetcher(document.assets())).write_pdf(
                **profile.options()
            )
        )


def page_count(document: Document) -> int:
    """
    How many sheets ``document`` lays out to.

    Laid out rather than guessed: it is the only way to know, and it is what
    makes a claim about a page break checkable. Shares
    :func:`render_pdf`'s resource policy exactly.
    """
    return len(layout(document).pages)


def layout(document: Document, profile: PdfProfile = PRINT) -> Any:
    """
    ``document`` laid out by the print engine, before any PDF is written.

    WeasyPrint's own rendered document: its ``pages`` each carry ``anchors``,
    the position of every element with an ``id``, which is how a check asks
    where something landed. Typed ``Any`` for :func:`_backend`'s reason.
    Shares :func:`render_pdf`'s resource policy exactly, and carries
    ``profile`` so its own ``write_pdf()`` writes what :func:`render_pdf` would.
    """
    weasyprint = _backend()
    with _own_errors():
        return weasyprint.HTML(
            string=document.render(), url_fetcher=build_fetcher(document.assets())
        ).render(**profile.options())


def save_pdf(document: Document, output_path: str | Path, profile: PdfProfile = PRINT) -> Path:
    """Render under ``profile`` and write to disk, returning the resolved path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render_pdf(document, profile))
    return output_path


@contextmanager
def _own_errors() -> Iterator[None]:
    """
    Present this exporter's exceptions rather than the backend's.

    ``fail_on_errors=True`` makes a refused resource fatal, which is what we
    want — but WeasyPrint wraps the cause in a ``FatalURLFetchingError`` on
    the way out, so a caller who followed the documented contract and caught
    :class:`~svc.pdf.exceptions.PdfError` would miss it. The same rule the
    send adapters hold: an exporter owns its own error tree, and the
    underlying error stays chained.
    """
    weasyprint = _backend()
    try:
        yield
    except weasyprint.urls.FatalURLFetchingError as exc:
        cause = exc.__cause__
        if isinstance(cause, UnreachableResourceError):
            raise cause from exc
        raise UnreachableResourceError(str(exc)) from exc


def _backend() -> Any:
    """
    Import WeasyPrint, or say what to install.

    Typed ``Any`` rather than a module type: WeasyPrint is an optional extra,
    so mypy runs with it absent in CI and present on a developer's machine,
    and a tighter annotation is green in one and red in the other.

    Imported here rather than at module scope on purpose: ``svc.pdf`` must be
    importable without the extra, so a caller can catch
    :class:`~svc.pdf.exceptions.BackendMissingError` rather than an
    ``ImportError`` from somewhere in their own import graph.
    """
    try:
        import weasyprint
    except ImportError as exc:  # pragma: no cover - exercised by a monkeypatched test
        raise BackendMissingError(
            "Rendering a PDF needs WeasyPrint, which is an optional extra. "
            'Install it with: pip install "pyhermes[pdf]"'
        ) from exc
    return weasyprint
