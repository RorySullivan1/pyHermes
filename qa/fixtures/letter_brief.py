"""
Print typography, on US Letter (#385): a three-sheet product brief.

A display masthead, a justified overview, two qualified exhibits, a fine-print
section after a reading-size one on one sheet, and a sheet of disclosures in
fine print, all set in a house typeface the PDF embeds. Photographed from its
PDF, one image a sheet.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.builder.sizing import LETTER_PORTRAIT
from pyhermes.document import (
    EmptyBackMatter,
    EmptyCover,
    PagedDocument,
    RunningFooter,
    paged_medium,
)

from . import _brief, _paged

#: The sheets this document lays out to; the PDF test asserts it.
SHEETS = 3


def build(template_dir: Path | None = None) -> Document:
    """Build the Letter brief. Deterministic: same bytes every call."""
    document = PagedDocument(
        {**_paged.facts(), "campaign_name": "Product brief", "font_theme": _brief.FONTS},
        template_dir=template_dir,
        medium=paged_medium(LETTER_PORTRAIT),
        cover=EmptyCover(),
        running_footer=RunningFooter(label="Meridian Broad Market Fund", show_page_number=True),
        back_matter=EmptyBackMatter(),
    )
    for section in _brief.sections():
        document.add_section(section)
    return document
