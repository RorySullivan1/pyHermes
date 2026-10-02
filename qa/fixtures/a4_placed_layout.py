"""
Placement across media, on A4 (#361): ``placed_layout``'s sections on paper.

Nothing stacks on a sheet, so the reversed and unstacked splits print as
written. The page note prints and the email's button does not, one section is
kept whole and another opens a sheet without a ``Page``. Photographed from its
PDF, one image a sheet.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument, RunningFooter

from . import _paged, _placed


def build(template_dir: Path | None = None) -> Document:
    """Build the A4 placement document. Deterministic: same bytes every call."""
    document = PagedDocument(
        {**_paged.facts(), "campaign_name": "Rates, Placed"},
        template_dir=template_dir,
        cover=EmptyCover(),
        running_footer=RunningFooter(label="Hermes Research", show_page_number=True),
        back_matter=EmptyBackMatter(),
    )
    for section in _placed.sections():
        document.add_section(section)
    return document
