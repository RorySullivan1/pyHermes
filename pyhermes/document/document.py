"""
``PagedDocument`` — a document laid onto sheets, with the regions that implies.

:class:`~pyhermes.builder.document.Document` knows only that some regions render
before the body and some after. This is the paged medium's answer: a cover,
two running margin boxes and a back-matter page, each swappable for the
variant that fills no slot.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar, Self

from pyhermes.builder.components import contents_entries
from pyhermes.builder.containers import Container
from pyhermes.builder.document import Document, RegionFacts
from pyhermes.builder.engine import TemplateOverlay
from pyhermes.builder.enums import TextAlign
from pyhermes.builder.medium import Medium
from pyhermes.builder.models import DocumentMetadata
from pyhermes.builder.sizing import Spacing
from pyhermes.config import Config

from .medium import PAGED_MEDIUM
from .page import Page
from .regions import (
    BackMatter,
    ContentsPage,
    Cover,
    EmptyContentsPage,
    EmptyExhibitsPage,
    ExhibitsPage,
    RunningFooter,
    RunningHeader,
)


class PagedDocument(Document):
    """
    A document that opens on a cover, repeats a folio, and closes on its
    disclosures.

    The paged counterpart to :class:`~pyhermes.builder.email.Email`, on exactly
    the same terms: the facts are the metadata's, the presentation is each
    region's, and this class only says which regions there are and what each
    is handed.

    **Every slot the skeleton names is filled, so every region is supplied.**
    Under ``StrictUndefined`` an unfilled *name* is a render failure, so
    omitting a region is a deliberate act: pass ``EmptyCover()``,
    ``EmptyRunningFooter()`` and so on, as an email passes ``EmptyHeader()``.

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
        exhibits:       The list of exhibits after it (#308), opt-in too.
        config, template_overlay: As ``Document`` takes them.
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
        exhibits: ExhibitsPage | None = None,
        *,
        config: Config | None = None,
        template_overlay: TemplateOverlay = None,
    ):
        super().__init__(
            metadata,
            template_dir,
            medium if medium is not None else PAGED_MEDIUM,
            config=config,
            template_overlay=template_overlay,
        )
        self._cover = cover if cover is not None else Cover()
        self._running_header = running_header if running_header is not None else RunningHeader()
        self._running_footer = running_footer if running_footer is not None else RunningFooter()
        self._back_matter = back_matter if back_matter is not None else BackMatter()
        self._contents = contents if contents is not None else EmptyContentsPage()
        self._exhibits = exhibits if exhibits is not None else EmptyExhibitsPage()

    @property
    def cover(self) -> Cover:
        """The opening sheet. Read-only, as every region here is."""
        return self._cover

    @property
    def contents(self) -> ContentsPage:
        """The sheet listing the sections."""
        return self._contents

    @property
    def exhibits(self) -> ExhibitsPage:
        """The sheet listing the numbered exhibits."""
        return self._exhibits

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
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ) -> Self:
        """
        Append the sections as one :class:`Page`. Returns ``self`` for chaining.

        Shorthand for ``add_section(Page(...))``, with the same arguments. The
        page is still a node in the tree, so the sections flatten as ever
        where a medium has no sheets.
        """
        page = Page(sections, break_before, break_after, title, background_color, align, spacing)
        return self.add_section(page)

    def leading_regions(self) -> tuple[RegionFacts, ...]:
        """The cover, the two lists and the two margin boxes, each with what it renders."""
        return (
            (self._cover, self._facts(COVER_FACTS)),
            (self._contents, self._listed(self._contents)),
            (self._exhibits, self._listed(self._exhibits)),
            (self._running_header, self._facts(RUNNING_FACTS)),
            (self._running_footer, self._facts(RUNNING_FACTS)),
        )

    def trailing_regions(self) -> tuple[RegionFacts, ...]:
        """The closing sheet, on the same terms."""
        return ((self._back_matter, self._facts(BACK_MATTER_FACTS)),)

    def _body_sections(self) -> list[Container]:
        """
        The body, less the leading break of a page that opens it.

        The body always starts a sheet: the first, or the one after the cover
        or the contents. A break before its first section is redundant there,
        and the running boxes' seed leaves ahead of the body table make it
        open a blank sheet instead.
        """
        sections = super()._body_sections()
        if sections and sections[0].break_before:
            sections = [sections[0].opening(), *sections[1:]]
        return sections

    def _listed(self, sheet: ContentsPage) -> dict[str, Any]:
        """What a contents sheet lists, as the fact it is handed."""
        return {"contents_entries": contents_entries(self._listing(sheet.of, sheet.label))}

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
