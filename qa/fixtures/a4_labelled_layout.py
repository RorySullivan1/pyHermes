"""
Labels and status, on A4 (#328): ``labelled_layout``'s sections on paper.

The same badges, dots and tags on a sheet, rounded as a browser draws them.
Photographed from its PDF, one image a sheet.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument, RunningFooter

from . import _labelled, _paged


def build(template_dir: Path | None = None) -> Document:
    """Build the A4 labelled document. Deterministic: same bytes every call."""
    document = PagedDocument(
        {**_paged.facts(), "campaign_name": "Rates, Labelled"},
        template_dir=template_dir,
        cover=EmptyCover(),
        running_footer=RunningFooter(label="Hermes Research", show_page_number=True),
        back_matter=EmptyBackMatter(),
    )
    for section in _labelled.sections():
        document.add_section(section)
    return document
