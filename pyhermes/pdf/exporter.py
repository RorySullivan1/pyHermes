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
from typing import TYPE_CHECKING, Any

from pyhermes.builder.document import Document
from pyhermes.builder.exceptions import PrintQualityWarning, warn_caller

from .exceptions import BackendError, BackendMissingError, PdfError, UnreachableResourceError
from .fetcher import build_fetcher
from .profile import PRINT, PdfProfile
from .tagging import retag_layout_tables

if TYPE_CHECKING:  # pragma: no cover
    from pyhermes.builder.sizing import PageFormat
    from pyhermes.deck import Deck


def available() -> bool:
    """Whether the PDF backend is installed, for a caller that wants to skip."""
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        # OSError: the wheel is installed but cffi could not load Pango,
        # Cairo or HarfBuzz from the system. Unavailable either way.
        return False
    return True


def render_pdf(document: Document, profile: PdfProfile = PRINT) -> bytes:
    """
    Render ``document`` to PDF bytes, written under ``profile``.

    The document's own :meth:`~pyhermes.builder.document.Document.render` produces
    the HTML, its :meth:`~pyhermes.builder.document.Document.assets` the images and
    its :meth:`~pyhermes.builder.document.Document.fonts` a house typeface's files;
    nothing else is read, and nothing is fetched. A reference the manifest
    does not cover raises
    :class:`~pyhermes.pdf.exceptions.UnreachableResourceError` naming the URL.
    ``PRINT`` leaves every image as it arrived; ``SCREEN`` downsamples.

    Raises:
        BackendMissingError: If WeasyPrint is not installed, or its system
            libraries will not load.
        UnreachableResourceError: If the document references a resource this
            exporter will not fetch.
        BackendError: On any other failure inside WeasyPrint.
    """
    weasyprint = _backend()
    html = document.render()
    fetcher = build_fetcher(document.assets() + document.fonts())
    kept = document.kept_sections()
    with _own_errors():
        source = weasyprint.HTML(string=html, url_fetcher=fetcher)
        if not kept:
            return bytes(source.write_pdf(finisher=_finisher(profile), **profile.options()))
        # HTML.write_pdf's own two steps, so the layout can be read in between.
        options = {**weasyprint.DEFAULT_OPTIONS, **profile.options()}
        laid_out = source.render(**options)
        _warn_tall_kept(laid_out, kept)
        known = {key: options[key] for key in weasyprint.DEFAULT_OPTIONS}
        return bytes(laid_out.write_pdf(finisher=_finisher(profile), **known))


def _finisher(profile: PdfProfile) -> Any:
    """
    The pass that corrects the structure tree, or ``None`` for a plain render.

    Attached only when the profile asks for a conformance variant, which is
    the only way a structure tree is written at all. Gating it here rather
    than relying on :func:`~pyhermes.pdf.tagging.retag_layout_tables` to no-op
    keeps an untagged render on exactly the code path it had before #202 —
    every existing golden and every byte-for-byte claim stays true by
    construction rather than by argument.
    """
    if profile.variant is None:
        return None
    return retag_layout_tables


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
    # The document renders outside the guard: a builder error is the
    # document's, and must not be reported as the backend's.
    html = document.render()
    fetcher = build_fetcher(document.assets() + document.fonts())
    with _own_errors():
        laid_out = weasyprint.HTML(string=html, url_fetcher=fetcher).render(**profile.options())
    _warn_tall_kept(laid_out, document.kept_sections())
    return laid_out


def _warn_tall_kept(laid_out: Any, kept: dict[str, str]) -> None:
    """
    Warn for each kept section the engine had to split anyway (#364).

    ``break-inside: avoid`` cannot hold a section taller than a sheet, so it
    moves to a fresh sheet and splits there, stranding the space it left.
    """
    sheets: dict[str, int] = {}
    for page in laid_out.pages:
        for anchor in page.anchors:
            if anchor in kept:
                sheets[anchor] = sheets.get(anchor, 0) + 1
    for anchor, count in sheets.items():
        if count > 1:
            warn_caller(
                f"{kept[anchor]} is kept together but runs over {count} sheets, so it "
                "strands the space before it. Drop keep_together, or split the section.",
                PrintQualityWarning,
            )


def anchor_tops(document: Document) -> dict[str, float]:
    """
    Where each ``id`` in ``document`` landed: the top of its box, in px from its sheet's top.

    The first sheet an id lands on wins. An element the engine placed on no
    sheet, such as copy that ran off one, has no entry, which is how a fit
    check tells "past the line" from "off the sheet".
    """
    landed: dict[str, float] = {}
    for page in layout(document).pages:
        for anchor, position in page.anchors.items():
            landed.setdefault(anchor, position[1])
    return landed


def save_pdf(document: Document, output_path: str | Path, profile: PdfProfile = PRINT) -> Path:
    """Render under ``profile`` and write to disk, returning the resolved path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render_pdf(document, profile))
    return output_path


def render_handout(
    deck: Deck, page: PageFormat | None = None, profile: PdfProfile = PRINT
) -> bytes:
    """
    A deck's handout as PDF bytes: one ``page`` a sheet, each slide above its notes (#351).

    A view of the notes projection, not a PowerPoint notes page: the markup is
    :meth:`~pyhermes.deck.Deck.handout`, every slide the deck's own sheet
    scaled onto ``page`` (A4 portrait unless set), and the resource policy
    :func:`render_pdf`'s exactly.

    Raises:
        As :func:`render_pdf`.
    """
    weasyprint = _backend()
    html = deck.handout() if page is None else deck.handout(page)
    fetcher = build_fetcher(deck.assets() + deck.fonts())
    with _own_errors():
        source = weasyprint.HTML(string=html, url_fetcher=fetcher)
        return bytes(source.write_pdf(finisher=_finisher(profile), **profile.options()))


def save_handout(
    deck: Deck,
    output_path: str | Path,
    page: PageFormat | None = None,
    profile: PdfProfile = PRINT,
) -> Path:
    """Render the handout and write it to disk, returning the resolved path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(render_handout(deck, page, profile))
    return output_path


@contextmanager
def _own_errors() -> Iterator[None]:
    """
    Present this exporter's exceptions rather than the backend's.

    ``fail_on_errors=True`` makes a refused resource fatal, which is what we
    want — but WeasyPrint wraps the cause in a ``FatalURLFetchingError`` on
    the way out, so a caller who followed the documented contract and caught
    :class:`~pyhermes.pdf.exceptions.PdfError` would miss it. The same rule the
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
    except PdfError:
        raise
    except Exception as exc:
        raise BackendError(f"WeasyPrint failed: {exc}") from exc


def _backend() -> Any:
    """
    Import WeasyPrint, or say what to install.

    Typed ``Any`` rather than a module type: WeasyPrint is an optional extra,
    so mypy runs with it absent in CI and present on a developer's machine,
    and a tighter annotation is green in one and red in the other.

    Imported here rather than at module scope on purpose: ``pyhermes.pdf`` must be
    importable without the extra, so a caller can catch
    :class:`~pyhermes.pdf.exceptions.BackendMissingError` rather than an
    ``ImportError`` from somewhere in their own import graph.
    """
    try:
        import weasyprint
    except ImportError as exc:  # pragma: no cover - exercised by a monkeypatched test
        raise BackendMissingError(
            "Rendering a PDF needs WeasyPrint, which is an optional extra. "
            'Install it with: pip install "pyhermes[pdf]"'
        ) from exc
    except OSError as exc:  # pragma: no cover - exercised by a monkeypatched test
        # The wheel is present; a shared library it needs is not. cffi
        # raises OSError, not ImportError, and the fix is a system package.
        raise BackendMissingError(
            "WeasyPrint is installed but could not load a system library it needs "
            f"({exc}). It needs Pango, Cairo and HarfBuzz from the system; "
            "see the README's note on the [pdf] extra."
        ) from exc
    return weasyprint
