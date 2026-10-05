"""
Organising content, on A4 (#334): ``organised_layout``'s sections on paper.

The same objects on a sheet: no event split across one, a kicker kept with
its title, and the teasers in one column. Photographed from its PDF, one
image a sheet.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument, RunningFooter

from . import _organised, _paged


def build(template_dir: Path | None = None) -> Document:
    """Build the A4 organised document. Deterministic: same bytes every call."""
    document = PagedDocument(
        {**_paged.facts(), "campaign_name": "Gilt Fund, Organised"},
        template_dir=template_dir,
        cover=EmptyCover(),
        running_footer=RunningFooter(label="Hermes Research", show_page_number=True),
        back_matter=EmptyBackMatter(),
    )
    for section in _organised.sections():
        document.add_section(section)
    return document
