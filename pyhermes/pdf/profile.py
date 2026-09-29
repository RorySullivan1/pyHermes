"""
How a PDF is written, as opposed to what it says: the image policy, the
conformance variant and the file identifier, named once as a ``PdfProfile``.

Two presets. ``PRINT`` leaves every image as it arrived and is
:func:`~pyhermes.pdf.render_pdf`'s default, so no existing caller's bytes move.
``SCREEN`` downsamples to 150 dpi at the displayed size and is what
:func:`~pyhermes.pdf.pdf_attachment` defaults to. `digital-pdf.md` has the numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import ProfileError

__all__ = ["PRINT", "SCREEN", "TAGGED", "PDF_VARIANTS", "PdfProfile"]

#: The variants WeasyPrint 70 writes, by the name it takes them under. Listed
#: rather than read off the backend, because a profile must validate with the
#: ``[pdf]`` extra absent; a test holds the list to the installed backend's.
PDF_VARIANTS = frozenset(
    {
        "pdf/a-1a",
        "pdf/a-1b",
        "pdf/a-2a",
        "pdf/a-2b",
        "pdf/a-2u",
        "pdf/a-3a",
        "pdf/a-3b",
        "pdf/a-3u",
        "pdf/a-4e",
        "pdf/a-4f",
        "pdf/a-4u",
        "pdf/ua-1",
        "pdf/ua-2",
        "pdf/x-1a",
        "pdf/x-3",
        "pdf/x-4",
        "pdf/x-5g",
    }
)

#: The JPEG quality scale's top, as WeasyPrint documents it. Pillow accepts 100,
#: and above 95 it disables parts of the compressor for no visible gain.
MAX_JPEG_QUALITY = 95


@dataclass(frozen=True)
class PdfProfile:
    """
    The options a PDF is written under, validated at construction.

    ``dpi`` caps a raster image's resolution at the size it is displayed, so
    an image already below it is untouched. ``jpeg_quality`` re-encodes a JPEG
    source and leaves a PNG alone, because a lossy step on a chart's flat
    colour costs clarity and saves little. ``optimize_images`` is Pillow's
    lossless pass. ``identifier`` is the first half of the PDF's ``/ID``:
    ``None`` writes none unless the variant requires one, and then WeasyPrint
    derives it from the file's own bytes. Every field is deterministic, so a
    profile can never make two renders of one document differ.

    A brochure may be written under ``SCREEN``: the result is a proof for a
    screen, not a press file, because a press wants the images untouched.
    """

    name: str
    dpi: int | None = None
    jpeg_quality: int | None = None
    optimize_images: bool = False
    variant: str | None = None
    identifier: bytes | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ProfileError("a PdfProfile needs a name, for the messages that cite it")
        if self.dpi is not None and self.dpi <= 0:
            raise ProfileError(f"dpi must be positive, or None to keep every image, got {self.dpi}")
        quality = self.jpeg_quality
        if quality is not None and not 0 <= quality <= MAX_JPEG_QUALITY:
            raise ProfileError(f"jpeg_quality must be 0 to {MAX_JPEG_QUALITY}, got {quality}")
        if self.variant is not None and self.variant not in PDF_VARIANTS:
            raise ProfileError(
                f"variant {self.variant!r} is not one WeasyPrint writes; "
                f"expected one of {', '.join(sorted(PDF_VARIANTS))}, or None"
            )
        if self.identifier is not None and not self.identifier:
            raise ProfileError("identifier must be non-empty bytes, or None")

    def options(self) -> dict[str, Any]:
        """The profile as WeasyPrint's rendering options, for ``write_pdf``."""
        return {
            "dpi": self.dpi,
            "jpeg_quality": self.jpeg_quality,
            "optimize_images": self.optimize_images,
            "pdf_variant": self.variant,
            "pdf_identifier": self.identifier,
        }


#: Every image as it arrived. The default for :func:`~pyhermes.pdf.render_pdf`.
PRINT = PdfProfile(name="PRINT")

#: Images at 150 dpi where they are displayed, JPEGs at quality 85. The default
#: for :func:`~pyhermes.pdf.pdf_attachment`, because an attached PDF is read on a screen.
SCREEN = PdfProfile(name="SCREEN", dpi=150, jpeg_quality=85, optimize_images=True)

#: ``SCREEN`` plus a structure tree, written to PDF/UA-1. Opt-in rather than
#: the default: it costs 11% to 32% more bytes, and a reader who never needs
#: the tags should not pay for them. Correct since #202 — before it, every
#: layout table was announced as a data table and a decorative image was a
#: figure with no alternate text, which is why this preset did not exist.
#: `digital-pdf.md` carries the measurements and why ``SCREEN`` stays untagged.
TAGGED = PdfProfile(
    name="TAGGED", dpi=150, jpeg_quality=85, optimize_images=True, variant="pdf/ua-1"
)
