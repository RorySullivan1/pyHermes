"""
Whether every panel's copy fits inside its safe line, asked of the print engine.

A panel clips what overflows it (#186), and a clip is silent in the PDF. This
lays the brochure out and reads back where each panel's closing sentinel
landed. It needs the ``[pdf]`` extra, imported only on use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .document import Brochure
from .imposition import face_name, impose

if TYPE_CHECKING:  # pragma: no cover - the exporter is imported only on use
    from pyhermes.pdf import Layout


def overflowing_panels(brochure: Brochure, laid_out: Layout | None = None) -> list[str]:
    """
    Every panel whose copy runs past its safe line, named by reader index and face.

    A panel's sentinel lands below ``height - inset`` when its copy overflows
    within the sheet, and nowhere at all when it overflows off it: the print
    engine records no position for an element it did not place on a page.
    Empty when everything fits. ``laid_out``, a :func:`~pyhermes.pdf.layout`
    of this brochure, is read rather than laying it out again.

    Raises:
        ValueError: If ``laid_out`` is a layout of another document.
        pyhermes.pdf.BackendMissingError: If WeasyPrint is not installed.
    """
    from pyhermes.pdf import anchor_tops

    if laid_out is not None and laid_out.document is not brochure:
        raise ValueError("laid_out is a layout of another document, not this brochure")
    landed = anchor_tops(brochure if laid_out is None else laid_out)
    overflowing = []
    for box, panel in zip(impose(brochure.fold), brochure.panels, strict=True):
        y = landed.get(f"panel-{box.reader}-end")
        if y is None or y > box.height - brochure.inset(panel):
            overflowing.append(f"panel {box.reader} ({face_name(brochure.fold, box.reader)})")
    return overflowing
