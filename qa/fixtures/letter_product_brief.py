"""
Single-sheet print pieces, on US Letter (#386): a three-sheet product brief.

A masthead band run to the sheet's edges, three boxes joined by "+" signs, a
scenario table pointing by a connector arrow at a dashed verdict, a grey band
run to the edges, a sheet of fine-print disclosures with a logo pinned to its
foot, and no running box on the masthead sheet. Photographed from its PDF, one
image a sheet.
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
    RunningHeader,
    paged_medium,
)

from . import _brief, _paged, _product_brief

#: The sheets this document lays out to; the PDF test asserts it.
SHEETS = 3

#: What the running boxes say on every sheet but the first.
LABEL = "Meridian Broad Market Fund"


def build(template_dir: Path | None = None) -> Document:
    """Build the Letter product brief. Deterministic: same bytes every call."""
    document = PagedDocument(
        {
            **_paged.facts(),
            "campaign_name": "Product brief",
            "font_theme": _brief.FONTS,
            "theme": _product_brief.THEME,
        },
        template_dir=template_dir,
        medium=paged_medium(LETTER_PORTRAIT),
        cover=EmptyCover(),
        running_header=RunningHeader(label=LABEL, skip_first=True),
        running_footer=RunningFooter(label=LABEL, show_page_number=True, skip_first=True),
        back_matter=EmptyBackMatter(),
    )
    for section in _product_brief.sections():
        document.add_section(section)
    return document
