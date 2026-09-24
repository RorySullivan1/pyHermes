"""
``PagedDocument`` — a document laid onto sheets, with the regions that implies.

:class:`~svc.builder.document.Document` knows only that some regions render
before the body and some after. This is the paged medium's answer: a cover,
two running margin boxes and a back-matter page, each swappable for the
variant that fills no slot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Self

from svc.builder.components import contents_entries
from svc.builder.containers import Container
from svc.builder.document import Document, RegionFacts
from svc.builder.engine import Renderer
from svc.builder.enums import TextAlign
from svc.builder.medium import Medium
from svc.builder.models import DocumentMetadata

from .medium import PAGED_MEDIUM
from .page import Page
from .regions import (
    BackMatter,
    ContentsPage,
    Cover,
    EmptyContentsPage,
    RunningFooter,
    RunningHeader,
)


class PagedDocument(Document):
    """
    A document that opens on a cover, repeats a folio, and closes on its
    disclosures.

    The paged counterpart to :class:`~svc.builder.email.Email`, on exactly
    the same terms: the facts are the metadata's, the presentation is each
    region's, and this class only says which regions there are and what each
    is handed.

    **The skeleton names four slots, so four regions are always supplied.**
    Under ``StrictUndefined`` an unfilled *name* is a render failure rather
    than an empty block, which is what makes omitting a region a deliberate
    act: pass ``EmptyCover()``, ``EmptyRunningFooter()`` and so on, the way
    an email passes ``EmptyHeader()``.

    Args:
        metadata:       Mapping of facts, or a ``DocumentMetadata``.
        template_dir:   Root of the templates. Defaults to the packaged copy.
        cover:          The opening sheet.
        running_header: The line in the top margin of every sheet.
        running_footer: The line in the bottom margin, usually the folio.
        back_matter:    The closing sheet carrying the disclosures.
        medium:         Which page. Defaults to A4 portrait.
        contents:       The sheet listing the sections, after the cover.
                        Opt-in, unlike the rest: a two-sheet factsheet is
                        not improved by a third that indexes it.
    """

    METADATA: ClassVar[type[DocumentMetadata]] = DocumentMetadata

    def __init__(
        self,
        metadata: dict[str, Any] | DocumentMetadata,
        template_dir: Path | None = None,
        cover: Cover | None = None,
        running_header: RunningHeader | None = None,
        running_footer: RunningFooter | None = None,
        back_matter: BackMatter | None = None,
        medium: Medium | None = None,
        contents: ContentsPage | None = None,
    ):
        super().__init__(metadata, template_dir, medium if medium is not None else PAGED_MEDIUM)
        self._cover = cover if cover is not None else Cover()
        self._running_header = running_header if running_header is not None else RunningHeader()
        self._running_footer = running_footer if running_footer is not None else RunningFooter()
        self._back_matter = back_matter if back_matter is not None else BackMatter()
        self._contents = contents if contents is not None else EmptyContentsPage()

    @property
    def cover(self) -> Cover:
        """The opening sheet. Read-only, as every region here is."""
        return self._cover

    @property
    def contents(self) -> ContentsPage:
        """The sheet listing the sections."""
        return self._contents

    @property
    def running_header(self) -> RunningHeader:
        """The top margin's line."""
        return self._running_header

    @property
    def running_footer(self) -> RunningFooter:
        """The bottom margin's line."""
        return self._running_footer

    @property
    def back_matter(self) -> BackMatter:
        """The closing sheet."""
        return self._back_matter

    def add_page(
        self,
        sections: list[Container],
        break_before: bool = True,
        break_after: bool = False,
        title: str | None = None,
        background_color: str | None = None,
        align: str | TextAlign | None = None,
    ) -> Self:
        """
        Append the sections as one :class:`Page`. Returns ``self`` for chaining.

        Shorthand for ``add_section(Page(...))``, with the same arguments. The
        page is still a node in the tree, so the sections flatten as ever
        where a medium has no sheets.
        """
        page = Page(sections, break_before, break_after, title, background_color, align)
        return self.add_section(page)

    def leading_regions(self) -> tuple[RegionFacts, ...]:
        """The cover, the contents and the two margin boxes, each with what it renders."""
        entries = contents_entries(self._contents_entries())
        return (
            (self._cover, self._facts(COVER_FACTS)),
            (self._contents, {"contents_entries": entries}),
            (self._running_header, self._facts(RUNNING_FACTS)),
            (self._running_footer, self._facts(RUNNING_FACTS)),
        )

    def trailing_regions(self) -> tuple[RegionFacts, ...]:
        """The closing sheet, on the same terms."""
        return ((self._back_matter, self._facts(BACK_MATTER_FACTS)),)

    def _body_context(self, engine: Renderer, sections: list[Container]) -> dict[str, Any]:
        """
        The body, less the leading break of a page that opens it.

        The body always starts a sheet: the first, or the one after the cover
        or the contents. A break before its first section is redundant there,
        and the running boxes' seed leaves ahead of the body table make it
        open a blank sheet instead.
        """
        if sections and isinstance(sections[0], Page):
            sections = [sections[0].opening(), *sections[1:]]
        return super()._body_context(engine, sections)

    def _facts(self, names: tuple[str, ...]) -> dict[str, Any]:
        """The named facts, read off the metadata this document was built from."""
        return {name: getattr(self._metadata, name) for name in names}


#: Facts the cover renders. Passed *down* to it; the region layers them over
#: its own context, so it cannot shadow one.
COVER_FACTS: tuple[str, ...] = (
    "firm_name",
    "campaign_name",
    "department",
    "date_range",
    "issue_label",
)

#: Facts a running margin box may fall back to for its label.
RUNNING_FACTS: tuple[str, ...] = ("firm_name", "campaign_name", "date_range")

#: The closing sheet's copy is a fact: the document owns the wording, the
#: region owns only how the page presents it.
BACK_MATTER_FACTS: tuple[str, ...] = ("header_disclaimer",)
