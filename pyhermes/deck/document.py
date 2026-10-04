"""
``Deck`` — slides in order, one to a sheet, between a title slide and the disclosures.

The deck counterpart to :class:`~pyhermes.document.document.PagedDocument`. The
caller adds slides and dividers; the deck numbers every sheet, follows the
current part in each footer band, and projects the presenter's notes as a
third reading of the same tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Self

from pyhermes.builder.components import leaves
from pyhermes.builder.containers import Container
from pyhermes.builder.document import Document, RegionFacts
from pyhermes.builder.engine import Renderer, TemplateOverlay, scheme_of
from pyhermes.builder.enums import SizeTheme, TextAlign
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.glance import HeroStat
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import DocumentMetadata
from pyhermes.builder.sizing import (
    A4_PORTRAIT,
    SLIDE_16_9,
    PageFormat,
    SizeScheme,
    resolve_size_scheme,
)
from pyhermes.builder.textgen import join_sections, underline, wrap
from pyhermes.config import Config

from .medium import deck_medium
from .regions import ClosingSlide, DeckFooter, TitleSlide
from .slide import AgendaEntry, DividerSlide, SheetFooter, Slide, SlideBox, StatementSlide

#: A slide's own picture is shown, not pressed: one source pixel per CSS px (#348).
SLIDE_DPI = 96


@dataclass
class DeckMetadata(DocumentMetadata):
    """A document's facts, at the density a projected slide is read at by default (#301)."""

    size_theme: SizeTheme | str = SizeTheme.PRESENTATION


class Deck(Document):
    """
    A deck: a title slide, slides and dividers, and the disclosures, one sheet each.

    **One idea is one sheet.** A slide never carries over: its body is a fixed
    box, and copy that does not fit is clipped and named by
    :func:`~pyhermes.deck.overflowing_slides`. :meth:`add_section` is refused,
    because a bare section has no sheet; :meth:`add_slide` gives it one.

    **Every sheet is numbered in Python**, the title slide included, so the
    footer band, a contents list on paper and the notes all agree on which
    slide is 4. The title slide carries no bands, as a cover carries no folio.

    **Footnotes are refused.** A note floats to a sheet's foot, which the footer
    band occupies; a slide's ``source`` line carries a source instead.

    Args:
        metadata:      Mapping of facts, or a ``DocumentMetadata``. A mapping
                       defaults to the ``presentation`` density.
        page:          The sheet. ``SLIDE_16_9`` by default, or ``SLIDE_4_3``.
        title_slide:   The opening slide; ``EmptyTitleSlide()`` for none.
        closing_slide: The disclosures; ``EmptyClosingSlide()`` for none.
        template_dir, config, template_overlay: As ``Document`` takes them.
        divider_agenda: Every divider lists every part, the current one marked (#350).
        footer:        How the footer band counts and what it marks (#352).

    Raises:
        ValidationError: If the page leaves no body between the bands.
    """

    METADATA: ClassVar[type[DocumentMetadata]] = DeckMetadata

    def __init__(
        self,
        metadata: dict[str, Any] | DocumentMetadata,
        page: PageFormat = SLIDE_16_9,
        title_slide: TitleSlide | None = None,
        closing_slide: ClosingSlide | None = None,
        template_dir: Path | None = None,
        *,
        config: Config | None = None,
        template_overlay: TemplateOverlay = None,
        divider_agenda: bool = False,
        footer: DeckFooter | None = None,
    ):
        if page.height is None:
            raise ValidationError("a slide is a fixed sheet; give the page a height")
        super().__init__(
            metadata,
            template_dir,
            deck_medium(page),
            config=config,
            template_overlay=template_overlay,
        )
        self._title_slide = title_slide if title_slide is not None else TitleSlide()
        self._closing_slide = closing_slide if closing_slide is not None else ClosingSlide()
        if footer is not None and not isinstance(footer, DeckFooter):
            raise ValidationError(f"a deck's footer is a DeckFooter, got: {type(footer).__name__}")
        self.divider_agenda = bool(divider_agenda)
        self.footer = footer or DeckFooter()
        box = self.box()
        if box.body_height <= 0:
            raise ValidationError(
                f"a {page.width} by {page.height}px sheet leaves no body between its title "
                f"and footer bands at this density; the bands take {box.title_height} and "
                f"{box.footer_height}px"
            )

    @property
    def title_slide(self) -> TitleSlide:
        """The opening slide."""
        return self._title_slide

    @property
    def closing_slide(self) -> ClosingSlide:
        """The disclosures."""
        return self._closing_slide

    @property
    def slides(self) -> list[Slide]:
        """Every slide and divider, in order."""
        return [section for section in self._sections if isinstance(section, Slide)]

    def box(self) -> SlideBox:
        """The bands of every sheet in this deck, at its page and density."""
        return SlideBox.of(self._scheme())

    def slide_box(self, slide: Slide) -> SlideBox:
        """The bands of ``slide``'s sheet: the deck's, less its source band, beside its picture."""
        return slide.sheet_box(self.box(), self._scheme())

    def _scheme(self) -> SizeScheme:
        """The density on this deck's page."""
        scheme = resolve_size_scheme(self._metadata.size_theme)
        return scheme.with_page(self._medium.page_format)

    def sheet_count(self) -> int:
        """How many sheets the deck prints: the title slide, every slide, the disclosures."""
        return self._opening() + len(self.slides) + (1 if self._closing_slide.TEMPLATE_PATHS else 0)

    def _opening(self) -> int:
        """1 when the deck opens on a title slide, which takes sheet one."""
        return 1 if self._title_slide.TEMPLATE_PATHS else 0

    def _footer(self, number: int) -> SheetFooter:
        """What sheet ``number``'s footer band prints beside the firm and the part."""
        return SheetFooter(self.footer.count(number, self.sheet_count()), self.footer.label)

    def add_section(self, container: Container) -> Self:
        """Refused: a bare section has no sheet. Use :meth:`add_slide`."""
        raise ValidationError(
            "a deck lays out slides, one to a sheet; wrap the section in a slide: "
            "deck.add_slide([section], title=...)"
        )

    def add_slide(
        self,
        sections: list[Container] | Slide,
        title: str | None = None,
        *,
        notes: str | None = None,
        background_color: str | None = None,
        align: str | TextAlign | None = None,
        layout: str = "full",
        side: list[Container] | None = None,
        valign: str = "top",
        source: str | None = None,
        as_of: str | None = None,
        background_image: EmailImage | None = None,
        ground: str | None = None,
        image: EmailImage | None = None,
        image_side: str = "left",
    ) -> Self:
        """
        Append the sections as one :class:`Slide`, or a ``Slide`` you built. Returns ``self``.

        Every other argument is the ``Slide``'s: ``layout``, ``side`` and
        ``valign`` (#366, #355), the source line (#347) and the pictures (#348).

        Raises:
            ValidationError: For a slide's own reasons, a footnote, a picture too
                coarse for the sheet, or an anchor the deck already has; the
                deck is left as it was.
        """
        if isinstance(sections, Slide):
            if (
                title
                or notes
                or background_color
                or align
                or side
                or source
                or as_of
                or background_image
                or ground
                or image
                or layout != "full"
                or valign != "top"
                or image_side != "left"
            ):
                raise ValidationError(
                    "add_slide takes a Slide or its arguments, not both; set them on the Slide"
                )
            slide = sections
        else:
            slide = Slide(
                sections,
                title,
                notes,
                background_color,
                align,
                layout=layout,
                side=side,
                valign=valign,
                source=source,
                as_of=as_of,
                background_image=background_image,
                ground=ground,
                image=image,
                image_side=image_side,
            )
        return self._append(slide)

    def add_statement(
        self, stat: HeroStat, title: str | None = None, *, notes: str | None = None
    ) -> Self:
        """Append a :class:`StatementSlide`: one figure on a sheet of its own (#349)."""
        return self._append(StatementSlide(stat, title, notes))

    def add_divider(
        self,
        title: str,
        subtitle: str | None = None,
        *,
        notes: str | None = None,
        valign: str = "bottom",
    ) -> Self:
        """Append a divider: a part's title, which the slides after it follow. Returns ``self``."""
        return self._append(DividerSlide(title, subtitle, notes, valign=valign))

    def _append(self, slide: Slide) -> Self:
        """Add ``slide`` through the document's checks, then refuse a note or a coarse picture."""
        self._check_pictures(slide)
        Document.add_section(self, slide)
        if self._footnotes():
            self._sections.pop()
            self._walk()
            raise ValidationError(
                "a deck cannot carry footnotes: a note floats to the foot of a sheet, and a "
                "slide's foot is its footer band. Put the source in the slide's source line."
            )
        return self

    def _check_pictures(self, slide: Slide) -> None:
        """
        Hold a slide's own pictures to one source pixel per CSS px of the box each fills.

        Below that warns and below half raises, the brochure's floor at a screen's
        density rather than a press's (#348).
        """
        from pyhermes.brochure.checks import validate_image_resolution

        box = self.box()
        fills: list[tuple[EmailImage, int | float]] = []
        if slide.background_image is not None:
            fills.append((slide.background_image, box.width))
        if slide.image is not None:
            fills.append((slide.image, box.picture(slide.image_side)[2]))
        with self.configured():
            validate_image_resolution(fills, dpi=SLIDE_DPI)

    def number(self, slide: Slide) -> int:
        """The sheet ``slide`` prints on, counting the title slide when there is one."""
        for index, candidate in enumerate(self.slides, start=1):
            if candidate is slide:
                return index + self._opening()
        raise ValidationError(f"{slide._name()} is not in this deck")

    def notes(self) -> str:
        """
        The presenter's notes: one block per slide that has any, headed by its number and title.

        A third reading of the tree, beside the markup and the text part. The
        text part is the deck as a reader reads it; the notes are what the
        presenter says over it, so neither projection carries them.
        """
        self.validate()
        return join_sections(
            *(
                f"{underline(_notes_heading(self.number(slide), slide))}\n\n{wrap(slide.notes)}"
                for slide in self.slides
                if slide.notes
            )
        )

    def leading_regions(self) -> tuple[RegionFacts, ...]:
        """The title slide, with the facts it presents and the sheet's bands."""
        return ((self._title_slide, {**self._facts(TITLE_FACTS), "deck_box": self.box()}),)

    def trailing_regions(self) -> tuple[RegionFacts, ...]:
        """The disclosures, numbered as the sheet after the last slide."""
        number = len(self.slides) + self._opening() + 1
        footer = self._footer(number)
        return (
            (
                self._closing_slide,
                {
                    **self._facts(CLOSING_FACTS),
                    "deck_box": self.box(),
                    "closing_number": number,
                    "closing_label": self._metadata.firm_name,
                    "closing_counter": footer.counter,
                    "closing_mark": footer.mark,
                },
            ),
        )

    def _body_context(self, engine: Renderer, sections: list[Container]) -> dict[str, Any]:
        """Every slide as a sheet, numbered, its footer naming the firm and the current part."""
        return {
            "sections_html": "\n".join(self._sheets(engine)),
            "imaged": any(slide.background_image for slide in self.slides),
            "handout": None,
        }

    def _sheets(self, engine: Renderer) -> list[str]:
        """Each slide's sheet, in order: its number, its part, its footer and any agenda."""
        box = SlideBox.of(scheme_of(engine))
        dividers = [slide for slide in self.slides if isinstance(slide, DividerSlide)]
        sheets, part = [], ""
        for slide in self.slides:
            number = self.number(slide)
            if isinstance(slide, DividerSlide):
                part = slide.title or ""
            label = " · ".join(filter(None, (self._metadata.firm_name, part)))
            footer = self._footer(number)
            if isinstance(slide, DividerSlide) and self.divider_agenda:
                agenda = tuple(
                    AgendaEntry(d.title or "", self.number(d), d is slide) for d in dividers
                )
                sheets.append(slide.render_sheet(engine, box, number, label, footer, agenda))
            else:
                sheets.append(slide.render_sheet(engine, box, number, label, footer))
        return sheets

    def handout(self, page: PageFormat = A4_PORTRAIT) -> str:
        """
        The handout's markup: one ``page`` a sheet, the sheet scaled above its notes (#351).

        Each sheet is the deck's own markup at the deck's own density, scaled
        to the page's width between its margins, so a slide in the handout is
        laid out exactly as the slide shown. The title slide and the
        disclosures get a page too, with no notes. ``pyhermes.pdf.render_handout``
        lays it onto paper.
        """
        if page.height is None:
            raise ValidationError("a handout is printed; give its page a height")
        with self.configured():
            self.validate()
            engine = self._bound_engine()
            ctx = self._metadata.to_dict()
            ctx.update(self._body_context(engine, []))
            regions: dict[str, Any] = {}
            for region, facts in self.leading_regions() + self.trailing_regions():
                regions.update(region.render_slots(engine, facts))
            ctx.update(regions)
            pairs = [("", regions["title_slide_html"])] if self._opening() else []
            pairs += zip((slide.notes for slide in self.slides), self._sheets(engine), strict=True)
            if self._closing_slide.TEMPLATE_PATHS:
                pairs.append(("", regions["closing_slide_html"]))
            box = self.box()
            margin = page.margin
            width = page.width - margin.left - margin.right
            scale = width / box.width
            ctx["handout"] = {
                "width": page.width,
                "height": page.height,
                "margin": margin,
                "scale": round(scale, 6),
                "frame_width": width,
                "frame_height": round(box.height * scale, 3),
                "sheets": [
                    {"html": html, "notes": [p.strip() for p in note.split("\n\n") if p.strip()]}
                    for note, html in pairs
                ],
            }
            return engine.render(self._medium.skeleton, ctx)

    def _marked(self) -> list[tuple[str, Any, list[str]]]:
        """Each slide's components, then its source line, slide by slide, in reading order."""
        marked: list[tuple[str, Any, list[str]]] = []
        for slide in self.slides:
            marked.extend(
                (type(c).__name__, c, c.marked_copy()) for c in leaves(slide.components())
            )
            marked.append((slide._name(), slide, [slide.source] if slide.source else []))
        return marked

    def _contents_entries(self, skip: Container | None = None) -> list[tuple[str, str]]:
        """``(title, anchor)`` for every titled slide and divider, less the one ``skip`` sits on."""
        return [
            (slide.heading(), slide.resolved_anchor())
            for slide in self.slides
            if slide.title and skip not in slide.sections
        ]

    def _anchors(self) -> list[tuple[str, str]]:
        """The document's anchors, and each titled slide's, which its title band carries."""
        slides = [
            (anchor, f"the slide titled {slide.title!r}")
            for slide in self.slides
            if (anchor := slide.resolved_anchor())
        ]
        return slides + super()._anchors()

    def _facts(self, names: tuple[str, ...]) -> dict[str, Any]:
        """The named facts, read off the metadata this deck was built from."""
        return {name: getattr(self._metadata, name) for name in names}


def _notes_heading(number: int, slide: Slide) -> str:
    """``Slide 4: Title``, or ``Slide 4`` for an untitled slide."""
    return f"Slide {number}: {slide.title}" if slide.title else f"Slide {number}"


#: Facts the title slide presents. Handed *down*; the region layers them over its own keys.
TITLE_FACTS: tuple[str, ...] = ("firm_name", "campaign_name", "department", "date_range")

#: The disclosures are a fact: the deck owns the wording, the region the slide.
CLOSING_FACTS: tuple[str, ...] = ("header_disclaimer",)


__all__ = ["CLOSING_FACTS", "SLIDE_DPI", "TITLE_FACTS", "Deck", "DeckMetadata"]
