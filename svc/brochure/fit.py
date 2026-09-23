"""
Whether every panel's copy fits inside its safe line, asked of the print engine.

A panel clips what overflows it (#186), and a clip is silent in the PDF. This
lays the brochure out and reads back where each panel's closing sentinel
landed. It needs the ``[pdf]`` extra, imported only on use.
"""

from __future__ import annotations

from .document import Brochure
from .imposition import face_name, impose


def overflowing_panels(brochure: Brochure) -> list[str]:
    """
    Every panel whose copy runs past its safe line, named by reader index and face.

    A panel's sentinel lands below ``height - inset`` when its copy overflows
    within the sheet, and nowhere at all when it overflows off it: the print
    engine records no position for an element it did not place on a page.
    Empty when everything fits.

    Raises:
        svc.pdf.BackendMissingError: If WeasyPrint is not installed.
    """
    from svc.pdf import layout

    landed: dict[str, float] = {}
    for page in layout(brochure).pages:
        for anchor, position in page.anchors.items():
            landed.setdefault(anchor, position[1])
    overflowing = []
    for box, panel in zip(impose(brochure.fold), brochure.panels, strict=True):
        y = landed.get(f"panel-{box.reader}-end")
        if y is None or y > box.height - brochure.inset(panel):
            overflowing.append(f"panel {box.reader} ({face_name(brochure.fold, box.reader)})")
    return overflowing
