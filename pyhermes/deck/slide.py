"""
``Slide`` — one idea on one sheet, and the unit a deck is laid out on.

A container of containers, in :class:`~pyhermes.brochure.panel.Panel`'s shape. In
the deck medium it is a fixed sheet with a title band and a footer band; in
every other medium it flattens to its sections, so a tree written for a deck
still renders as an email or a report.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from pyhermes.builder.components import Component
from pyhermes.builder.containers import Container
from pyhermes.builder.engine import Renderer, grounded, rebind, scheme_of
from pyhermes.builder.enums import TextAlign, VerticalAlign
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage, ImageAsset
from pyhermes.builder.models import check_valign
from pyhermes.builder.sizing import PageMargin, SizeScheme
from pyhermes.builder.textgen import join_blocks, underline, wrap
from pyhermes.document.page import Page


@dataclass(frozen=True)
class SlideBox:
    """
    The bands of one sheet, in px: computed from the page and the density, never passed in.

    The title band is the page's top margin, one title line and the gap under
    a section title; the footer band is the bottom margin. The body is what
    is left, and it is the box overflow is measured against.
    """

    width: int | float
    height: int | float
    inset: int | float
    margin_top: int | float
    title_height: int | float
    footer_height: int | float
    #: One title line, in px: the height the title is clipped to (#316).
    title_line: int = 0

    @classmethod
    def of(cls, scheme: SizeScheme) -> SlideBox:
        """The bands on ``scheme``'s page, at its density."""
        frame, kind = scheme.frame, scheme.type
        margin = frame.margin
        title_line = math.ceil(kind.title * kind.title_line)
        footer_line = math.ceil(kind.micro * kind.secondary_line)
        return cls(
            width=frame.sheet_width,
            height=frame.sheet_height or 0,
            inset=margin.left,
            margin_top=margin.top,
            title_height=margin.top + title_line + scheme.space.section_title_bottom,
            footer_height=max(margin.bottom, footer_line),
            title_line=title_line,
        )

    @property
    def body_top(self) -> int | float:
        """Where the body starts: under the title band."""
        return self.title_height

    @property
    def body_height(self) -> int | float:
        """The body's height: the sheet less both bands."""
        return self.height - self.title_height - self.footer_height

    @property
    def footer_top(self) -> int | float:
        """Where the footer band starts."""
        return self.height - self.footer_height

    @property
    def body_bottom(self) -> int | float:
        """The line copy may not pass."""
        return self.body_top + self.body_height

    def regions(self, layout: str, gutter: int | float) -> list[SlideRegion]:
        """
        The body's regions for ``layout``, main first: computed like a split's columns (#366).

        The copy between the page margins, less one ``gutter``, is split by the
        layout's weights, the side region floored. Each region's frame reaches
        half a gutter past its copy on both sides, so a band in it still has an
        edge to inset from, and the two frames meet at the gutter's middle.
        """
        if layout == "full":
            return [SlideRegion("main", 0, self.width, self.inset)]
        main_weight, side_weight = LAYOUTS[layout]
        available = self.width - 2 * self.inset - gutter
        side = math.floor(available * side_weight / (main_weight + side_weight))
        main = available - side
        half = _px(gutter / 2)
        return [
            SlideRegion("main", _px(self.inset - half), _px(main + gutter), half),
            SlideRegion("side", _px(self.inset + main + half), _px(side + gutter), half),
        ]


@dataclass(frozen=True)
class SlideRegion:
    """One region of a slide's body: its name, its frame's left edge and width, and its inset."""

    name: str
    left: int | float
    width: int | float
    inset: int | float


def _px(value: int | float) -> int | float:
    """``value`` as an int when it is whole, since a size token may not be an integral float."""
    return int(value) if float(value).is_integer() else value


#: The weights of each named slide layout, main region first (#366).
LAYOUTS: dict[str, tuple[int, ...]] = {"full": (1,), "split": (1, 1), "sidebar": (2, 1)}


class Slide(Container):
    """
    A run of sections confined to one sheet, under a title band and over a footer band.

    **The slide is the layout unit; the sheet is its CSS page.** Its sections
    render against a frame the sheet's width with ``pad_x`` set to the page
    margin, so every container insets its copy level with the title.

    **A fixed box, and overflow is clipped** rather than carried onto another
    sheet, as a brochure panel's is. :func:`pyhermes.deck.overflowing_slides`
    makes the clip loud.

    **It flattens where slides do not exist**, byte for byte, as a ``Page``
    and a ``Panel`` do. Its title is then not rendered, and it claims an
    anchor only on a deck, where the title band prints it.

    Args:
        sections:         The containers on this slide, in reading order.
        title:            The slide's title band, and its line in a contents list.
        notes:            What the presenter says over it: plain text, never
                          rendered, read back by :meth:`Deck.notes`.
        background_color: The slide's ground, and the surface its sections sit on.
        align:            Alignment inherited by the copy inside.
        anchor:           The title's ``id``; a slug of the title when unset.
        layout:           ``"full"``, ``"split"`` (equal halves) or ``"sidebar"``
                          (a main area two thirds wide, a side beside it) (#366).
        side:             The side region's sections; ``sections`` fill the main.
        valign:           The copy's anchor: ``"top"``, ``"middle"`` or ``"bottom"`` (#355).
    """

    template_path = "deck/slide.html"

    #: The body's layout: ``"full"``, ``"split"`` or ``"sidebar"`` (#366).
    layout: str = "full"

    def __init__(
        self,
        sections: list[Container],
        title: str | None = None,
        notes: str | None = None,
        background_color: str | None = None,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        *,
        layout: str = "full",
        side: list[Container] | None = None,
        valign: str | VerticalAlign = "top",
    ):
        super().__init__(title=title, background_color=background_color, align=align, anchor=anchor)
        self._check_sections(sections)
        if notes is not None and not isinstance(notes, str):
            raise ValidationError(
                f"{self._name()}'s notes are plain text, got: {type(notes).__name__}"
            )
        if layout not in LAYOUTS:
            raise ValidationError(
                f"{self._name()}'s layout is one of {list(LAYOUTS)}, got: {layout!r}"
            )
        if (layout == "full") != (not side):
            raise ValidationError(
                f"{self._name()} lays out {layout!r}: "
                + ("a full body has no side region; drop side=" if side else "give side=[...]")
            )
        if side:
            self._check_sections(side)
        self.layout = layout
        self.valign = check_valign(valign, self._name())
        # Everywhere but its own sheet, a laid-out slide is its regions in reading order.
        self.sections = [*sections, *(side or [])]
        self._side_count = len(side or [])
        self.notes = (notes or "").strip()

    @property
    def main(self) -> list[Container]:
        """The main region's sections: all of them on a full body."""
        return self.sections[: len(self.sections) - self._side_count]

    @property
    def side(self) -> list[Container]:
        """The side region's sections; none on a full body."""
        return self.sections[len(self.sections) - self._side_count :]

    def _check_sections(self, sections: list[Container]) -> None:
        """Refuse an empty slide, a boundary inside one, and anything not a section."""
        if not sections:
            raise ValidationError(f"{self._name()} needs at least one section; a divider has none")
        for section in sections:
            if isinstance(section, Page) or hasattr(section, "sections"):
                raise ValidationError(
                    f"{self._name()} may not contain a {type(section).__name__.lower()}: "
                    "a slide is one sheet, so a boundary inside one has no meaning"
                )
            if not isinstance(section, Container):
                raise ValidationError(
                    f"{self._name()} holds containers, got: {type(section).__name__}"
                )
            if section.keep_together or section.break_before:
                raise ValidationError(
                    f"{self._name()} holds a section with keep_together or break_before: "
                    "a slide is already one sheet, and never breaks (#364)"
                )

    def _name(self) -> str:
        """How errors name this slide."""
        return f"the slide titled {self.title!r}" if getattr(self, "title", None) else "a slide"

    def components(self) -> list[Component]:
        """Every component on this slide, in reading order."""
        return [component for section in self.sections for component in section.components()]

    def assets(self) -> list[ImageAsset]:
        """The manifest entries from every section here, in reading order."""
        return [asset for section in self.sections for asset in section.assets()]

    def images(self) -> list[EmailImage]:
        """Every image on this slide."""
        return [image for section in self.sections for image in section.images()]

    def text(self) -> str:
        """This slide as plain text: its title, underlined, then its sections."""
        return join_blocks(
            underline(self.title or ""), *(section.text() for section in self.sections)
        )

    def render(self, engine: Renderer) -> str:
        """
        The sections, bare.

        Only a deck knows a slide's number and its band, so the sheet is
        :meth:`render_sheet`, which the deck calls. Anywhere else a slide is
        its sections run on.
        """
        return "\n".join(section.render(engine) for section in self.sections)

    def render_sheet(self, engine: Renderer, box: SlideBox, number: int, label: str) -> str:
        """
        This slide as one sheet: its title band, its body and its footer band.

        ``number`` is the sheet's, counted by the deck, and ``label`` the
        footer band's text: the firm, and the part the slide belongs to.
        """
        themed = engine
        if self.background_color:
            # The ground is the surface the sections sit on, as on a panel, and
            # a dark one turns the type light in the bands and the body alike.
            palette = replace(engine.theme.palette, surface=self.background_color)
            theme = replace(engine.theme, palette=palette)
            themed = grounded(rebind(engine, theme=theme), theme.on_ground(self.background_color))
        scheme = scheme_of(engine)
        regions = []
        for region, sections in zip(
            box.regions(self.layout, scheme.space.gutter), (self.main, self.side), strict=False
        ):
            body = rebind(themed, size=_body_scheme(scheme, box, region))
            html = "\n".join(section.render(body) for section in sections)
            regions.append(
                {"name": region.name, "left": region.left, "width": region.width, "html": html}
            )
        return themed.render(
            self.template_path,
            {
                **self._base_context(themed),
                "regions": regions,
                "box": box,
                "number": number,
                "footer_label": label,
                "valign": self.valign,
            },
        )


class DividerSlide(Slide):
    """
    A slide with no body: a part's title, set large on the theme's ``header_bg``.

    Its title starts a part, and the slides after it carry that title in their
    footer band until the next divider. In any other medium it renders
    nothing and projects its title, underlined, so a reader of the text part
    still sees where a part begins.

    Args:
        title:    The part's name. Required: a divider says where you are.
        subtitle: A line under it.
        notes:    As a ``Slide`` takes them.
        anchor:   The title's ``id``; a slug of the title when unset.
        valign:   Where the title sits in the body's height; ``"bottom"``, where
                  a slide's body ends, unless set (#355).
    """

    template_path = "deck/divider.html"

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        notes: str | None = None,
        anchor: str | None = None,
        *,
        valign: str | VerticalAlign = "bottom",
    ):
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("a divider needs a title: it is what the slides after it follow")
        if subtitle is not None and not isinstance(subtitle, str):
            raise ValidationError(
                f"a divider's subtitle is plain text, got: {type(subtitle).__name__}"
            )
        self.subtitle = subtitle or ""
        super().__init__([], title=title, notes=notes, anchor=anchor, valign=valign)

    def _check_sections(self, sections: list[Container]) -> None:
        """Nothing to check: a divider has no body."""

    def text(self) -> str:
        """The part's title, underlined, and its subtitle under it."""
        return join_blocks(underline(self.title or ""), wrap(self.subtitle))

    def render_sheet(self, engine: Renderer, box: SlideBox, number: int, label: str) -> str:
        """The part's title and subtitle on the dark ground, over the footer band."""
        return engine.render(
            self.template_path,
            {
                **self._base_context(engine),
                "subtitle": self.subtitle,
                "valign": self.valign,
                "box": box,
                "number": number,
                "footer_label": label,
            },
        )


def _body_scheme(scheme: SizeScheme, box: SlideBox, region: SlideRegion) -> SizeScheme:
    """
    The density, on a frame the region's width and the body's height.

    ``pad_x`` becomes the region's inset, the one horizontal padding every
    container already applies: the page margin for a full body, so the copy
    sits level with the title. No margin and no breakpoint: a slide's sheet
    has neither.
    """
    frame = replace(
        scheme.frame,
        width=region.width,
        height=box.body_height,
        mobile_breakpoint=None,
        margin=PageMargin(),
        pad_x=region.inset,
    )
    return scheme.derive(frame=frame)
