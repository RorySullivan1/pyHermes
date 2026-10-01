"""
A research note on A4: every long-form piece in one paged document (#312).

A cover, a contents sheet and a list of exhibits, three body sections with
citations, glossary links and a key-takeaways callout, then a bibliography, a
glossary and two lettered appendices. ``research_note`` is the same content as
an email; together their goldens pin that the numbering agrees across media.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.document import (
    BackMatter,
    ContentsPage,
    Cover,
    ExhibitsPage,
    PagedDocument,
    RunningFooter,
    RunningHeader,
)

from . import _paged, _research


def build(template_dir: Path | None = None) -> Document:
    """Build the A4 research note. Deterministic: same bytes every call."""
    document = PagedDocument(
        {**_paged.facts(), "campaign_name": "Momentum After Costs"},
        template_dir=template_dir,
        cover=Cover(title="Momentum After Costs", subtitle="A research note"),
        contents=ContentsPage(heading="Contents"),
        exhibits=ExhibitsPage(heading="Tables and Figures", label="Exhibit"),
        running_header=RunningHeader(label="Momentum After Costs", follow="section"),
        running_footer=RunningFooter(label="Hermes Research", show_page_number=True),
        back_matter=BackMatter(heading="Important Disclosures"),
    )
    for section in _research.sections():
        document.add_section(section)
    return document
