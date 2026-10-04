"""
Data at a glance, on A4 (#323): ``glance_layout``'s sections on paper.

The same objects on sheets, each kept whole by its ``figure`` hook.
Photographed from its PDF, one image a sheet.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument, RunningFooter

from . import _glance, _paged


def build(template_dir: Path | None = None) -> Document:
    """Build the A4 glance document. Deterministic: same bytes every call."""
    document = PagedDocument(
        {**_paged.facts(), "campaign_name": "Rates, at a Glance"},
        template_dir=template_dir,
        cover=EmptyCover(),
        running_footer=RunningFooter(label="Hermes Research", show_page_number=True),
        back_matter=EmptyBackMatter(),
    )
    for section in _glance.sections():
        document.add_section(section)
    return document
