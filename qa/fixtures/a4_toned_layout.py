"""
Brand tones, on A4 (#387): ``toned_layout``'s sections on paper.

The same gold and sky on a sheet, beside the untouched semantic tones.
Photographed from its PDF, one image a sheet.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument, RunningFooter

from . import _paged, _toned


def build(template_dir: Path | None = None) -> Document:
    """Build the A4 toned document. Deterministic: same bytes every call."""
    document = PagedDocument(
        {**_paged.facts(), "campaign_name": "The Fund, In Brand", "theme": _toned.THEME},
        template_dir=template_dir,
        cover=EmptyCover(),
        running_footer=RunningFooter(label="Hermes Research", show_page_number=True),
        back_matter=EmptyBackMatter(),
    )
    for section in _toned.sections():
        document.add_section(section)
    return document
