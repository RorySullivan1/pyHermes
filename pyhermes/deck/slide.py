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
from typing import Any

from pyhermes.builder.apparatus import MARKER, UNRESOLVED, Citing, split_markers, text_markers
from pyhermes.builder.components import Component
from pyhermes.builder.containers import Container, FullWidth
from pyhermes.builder.engine import Renderer, grounded, rebind, scheme_of
from pyhermes.builder.enums import TextAlign, VerticalAlign
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.glance import HeroStat
from pyhermes.builder.images import EmailImage, EmbedStrategy, ImageAsset
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
    #: The copy's left edge: zero unless a picture takes the sheet's other half (#348).
    left: int | float = 0
    #: The source band over the footer band, and its one line; zero without a source (#347).
    source_height: int | float = 0
    source_line: int = 0

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
        """The body's height: the sheet less both bands, and less a source band."""
        return self.height - self.title_height - self.footer_height - self.source_height

    @property
    def footer_top(self) -> int | float:
        """Where the footer band starts."""
        return self.height - self.footer_height

    @property
    def source_top(self) -> int | float:
        """Where the source band starts: where the body ends."""
        return self.footer_top - self.source_height

    def with_source(self, scheme: SizeScheme) -> SlideBox:
        """This box with a source band: one ``micro`` line and the gap over it (#347)."""
        line = math.ceil(scheme.type.micro * scheme.type.body_line)
        return replace(self, source_height=line + scheme.space.caption_gap, source_line=line)

    def picture(self, side: str) -> tuple[SlideBox, int | float, int | float]:
        """
        The copy's box beside a picture on ``side``, and the picture's left edge and width (#348).

        The picture takes half the sheet, floored, edge to edge; the copy and
        every band take the other half, at the same inset from its edges.
        """
        width = math.floor(self.width / 2)
        copy = self.width - width
        if side == "left":
            return replace(self, left=width, width=copy), 0, width
        return replace(self, width=copy), copy, width

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
            return [SlideRegion("main", self.left, self.width, self.inset)]
        main_weight, side_weight = LAYOUTS[layout]
        available = self.width - 2 * self.inset - gutter
        side = math.floor(available * side_weight / (main_weight + side_weight))
        main = available - side
        half = _px(gutter / 2)
        return [
            SlideRegion("main", _px(self.left + self.inset - half), _px(main + gutter), half),
            SlideRegion(
                "side", _px(self.left + self.inset + main + half), _px(side + gutter), half
            ),
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

#: The tones a caller names for a full-bleed picture, which has no one colour to measure (#348).
GROUNDS: tuple[str, ...] = ("light", "dark")

#: The sides a picture beside the copy may take (#348).
IMAGE_SIDES: tuple[str, ...] = ("left", "right")


def _check_picture(image: object, field: str, owner: str) -> None:
    """Refuse anything but an attached or inline ``EmailImage``: the exporter fetches nothing."""
    if not isinstance(image, EmailImage):
        raise ValidationError(
            f"{owner}'s {field} must be an EmailImage, got: {type(image).__name__}"
        )
    if image.strategy is EmbedStrategy.REMOTE:
        raise ValidationError(
            f"{owner}'s {field} is hosted, and the PDF exporter fetches nothing: "
            "attach it with EmailImage.attached()"
        )


class Slide(Container):
    """
    A run of sections confined to one sheet, under a title band and over a footer band.

    **The slide is the layout unit; the sheet is its CSS page.** Its sections
    render against a frame the sheet's width with ``pad_x`` at the page margin,
    so every container insets its copy level with the title. **Overflow is
    clipped**, as on a brochure panel; :func:`pyhermes.deck.overflowing_slides`
    makes the clip loud. **It flattens where slides do not exist**, byte for
    byte: no title, no pictures, and an anchor only on a deck.

    Args:
        sections:         The containers on this slide, in reading order.
        title:            The slide's title band, and its line in a contents list.
        notes:            What the presenter says over it: plain text, never rendered.
        background_color: The slide's ground, and the surface its sections sit on.
        align, anchor:    The copy's alignment; the title's ``id``, a slug when unset.
        layout, side:     ``"full"``, ``"split"`` or ``"sidebar"``, and the side
                          region's sections (#366).
        valign:           The copy's anchor: ``"top"``, ``"middle"`` or ``"bottom"`` (#355).
        source, as_of:    A fine-print line over the footer band; ``[@key]``
                          resolves, a footnote is refused (#347).
        background_image: A picture filling the sheet under the bands (#348), with
        ground:           ``"light"`` or ``"dark"``, the tone the type is set for.
        image:            A picture taking half the sheet, edge to edge (#348), on
        image_side:       ``"left"`` or ``"right"``.
        kicker:           A short label above the title, in the title band's top
                          margin, so the title keeps its line (#333).
    """

    template_path = "deck/slide.html"

    #: The body's layout: ``"full"``, ``"split"`` or ``"sidebar"`` (#366).
    layout: str = "full"

    #: The images this slide carries itself (standing rule 7), walked by :meth:`images`.
    IMAGE_FIELDS: tuple[str, ...] = ("background_image", "image")

    #: Whether the sheet prints the title, so the fit check measures it (#349).
    TITLE_BAND: bool = True

    #: How a citation in ``source`` is spelled, handed down by the deck's walk.
    citing: Citing = UNRESOLVED

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
        source: str | None = None,
        as_of: str | None = None,
        background_image: EmailImage | None = None,
        ground: str | None = None,
        image: EmailImage | None = None,
        image_side: str = "left",
        kicker: str | None = None,
    ):
        super().__init__(
            title=title,
            background_color=background_color,
            align=align,
            anchor=anchor,
            kicker=kicker,
        )
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
        self._check_source(source, as_of)
        self._check_pictures(background_image, ground, image, image_side, layout)
        self.layout = layout
        self.valign = check_valign(valign, self._name())
        # Everywhere but its own sheet, a laid-out slide is its regions in reading order.
        self.sections = [*sections, *(side or [])]
        self._side_count = len(side or [])
        self.notes = (notes or "").strip()
        self.source = source or ""
        self.as_of = as_of or ""
        self.background_image = background_image
        self.ground = ground or ""
        self.image = image
        self.image_side = image_side

    def _check_source(self, source: str | None, as_of: str | None) -> None:
        """Refuse a source that is not text, one calling a footnote, and a date with no source."""
        for name, value in (("source", source), ("as_of", as_of)):
            if value is not None and not isinstance(value, str):
                raise ValidationError(
                    f"{self._name()}'s {name} is plain text, got: {type(value).__name__}"
                )
        if source and MARKER.search(source):
            raise ValidationError(
                f"{self._name()}'s source calls a footnote, and a deck carries none: a "
                "slide's foot is its footer band. Cite with [@key], or write the source out."
            )
        if as_of and not source:
            raise ValidationError(f"{self._name()} has an as_of date but no source to date")

    def _check_pictures(
        self,
        background_image: EmailImage | None,
        ground: str | None,
        image: EmailImage | None,
        image_side: str,
        layout: str,
    ) -> None:
        """Refuse a hosted picture, a picture with no tone named, and two pictures on one sheet."""
        if background_image is not None:
            _check_picture(background_image, "background_image", self._name())
            if ground not in GROUNDS:
                raise ValidationError(
                    f"{self._name()}'s background_image needs ground= one of {list(GROUNDS)}: "
                    f"a photograph has no one colour to set the type against, got: {ground!r}"
                )
        elif ground is not None:
            raise ValidationError(f"{self._name()} names a ground but has no background_image")
        if image_side not in IMAGE_SIDES:
            raise ValidationError(
                f"{self._name()}'s image_side is one of {list(IMAGE_SIDES)}, got: {image_side!r}"
            )
        if image is None:
            return
        _check_picture(image, "image", self._name())
        if background_image is not None:
            raise ValidationError(
                f"{self._name()} has both a background_image and an image: one picture a slide"
            )
        if layout != "full":
            raise ValidationError(
                f"{self._name()} lays out {layout!r} beside a picture: the picture is "
                "the sheet's other half, so the copy beside it is one region"
            )

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

    def own_images(self) -> list[EmailImage]:
        """The pictures this slide carries itself, from ``IMAGE_FIELDS``."""
        return [image for name in self.IMAGE_FIELDS if (image := getattr(self, name, None))]

    def assets(self) -> list[ImageAsset]:
        """The manifest entries: this slide's own pictures, then every section's."""
        own = [asset for image in self.own_images() if (asset := image.asset)]
        return own + [asset for section in self.sections for asset in section.assets()]

    def images(self) -> list[EmailImage]:
        """Every image on this slide: its own pictures first, then its sections'."""
        return self.own_images() + [
            image for section in self.sections for image in section.images()
        ]

    def source_text(self) -> str:
        """The source line as plain text, its citations spelled, its date after it."""
        if not self.source:
            return ""
        source = text_markers(self.source, [], self.citing)
        return f"{source} as of {self.as_of}" if self.as_of else source

    def text(self) -> str:
        """This slide as plain text: its title, kicked and underlined, its sections, its source."""
        return join_blocks(
            self.headed(),
            *(section.text() for section in self.sections),
            wrap(self.source_text()),
        )

    def render(self, engine: Renderer) -> str:
        """
        The sections, bare.

        Only a deck knows a slide's number and its band, so the sheet is
        :meth:`render_sheet`, which the deck calls. Anywhere else a slide is
        its sections run on.
        """
        return "\n".join(section.render(engine) for section in self.sections)

    def sheet_box(self, box: SlideBox, scheme: SizeScheme) -> SlideBox:
        """The deck's ``box`` as this slide lays it out: less a source band, beside a picture."""
        if self.source:
            box = box.with_source(scheme)
        if self.image is not None:
            box = box.picture(self.image_side)[0]
        return box

    def _ink(self, engine: Renderer) -> Renderer:
        """``engine`` on this slide's ground: its colour as the surface, its type legible there."""
        if not (self.background_color or self.background_image):
            return engine
        theme = engine.theme
        if self.background_color:
            # The ground is the surface the sections sit on, as on a panel.
            theme = replace(theme, palette=replace(theme.palette, surface=self.background_color))
        if self.background_image:
            # A photograph has no one colour to measure, so the caller's tone stands in.
            ink = theme.on_ground("#000000" if self.ground == "dark" else "#FFFFFF")
        else:
            ink = theme.on_ground(self.background_color)
        return grounded(rebind(engine, theme=theme), ink)

    def render_sheet(
        self,
        engine: Renderer,
        box: SlideBox,
        number: int,
        label: str,
        footer: SheetFooter | None = None,
    ) -> str:
        """
        This slide as one sheet: its title band, its body and its footer band.

        ``box`` is the deck's, which this slide narrows for its own source and
        picture. ``number`` is the sheet's, counted by the deck, ``label`` the
        footer band's text, the firm and the current part, and ``footer`` how
        the band counts and what it marks (#352).
        """
        themed = self._ink(engine)
        scheme = scheme_of(engine)
        whole = box
        box = self.sheet_box(box, scheme)
        regions = []
        for region, sections in zip(
            box.regions(self.layout, scheme.space.gutter), (self.main, self.side), strict=False
        ):
            body = rebind(themed, size=_body_scheme(scheme, box, region))
            html = "\n".join(section.render(body) for section in sections)
            regions.append(
                {"name": region.name, "left": region.left, "width": region.width, "html": html}
            )
        picture: dict[str, Any] = {}
        if self.image is not None:
            _, left, width = whole.picture(self.image_side)
            picture = {"src": self.image.src, "alt": self.image.alt, "left": left, "width": width}
        return themed.render(
            self.template_path,
            {
                **self._base_context(themed),
                **(footer or SheetFooter.of(number)).context(),
                "regions": regions,
                "box": box,
                "number": number,
                "footer_label": label,
                "valign": self.valign,
                "source": self.source,
                "source_parts": split_markers(self.source, [], self.citing),
                "as_of": self.as_of,
                "background_image": self.background_image.src if self.background_image else "",
                "picture": picture,
                "kicker_rise": self.kicker_rise(scheme),
            },
        )

    def kicker_rise(self, scheme: SizeScheme) -> int | float:
        """How far the kicker lifts the title band's top padding: its line and its gap (#333)."""
        if not self.kicker:
            return 0
        return math.ceil(scheme.type.label * scheme.type.secondary_line) + scheme.space.caption_gap


@dataclass(frozen=True)
class SheetFooter:
    """What one sheet's footer band prints beside the firm and the part: its counter and mark."""

    counter: str
    mark: str = ""

    @classmethod
    def of(cls, number: int) -> SheetFooter:
        """The bare number, as every footer band printed it before #352."""
        return cls(str(number))

    def context(self) -> dict[str, str]:
        """The template keys, under names no region fact takes."""
        return {"footer_counter": self.counter, "footer_mark": self.mark}


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

    TITLE_BAND = False

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

    def render_sheet(
        self,
        engine: Renderer,
        box: SlideBox,
        number: int,
        label: str,
        footer: SheetFooter | None = None,
        agenda: tuple[AgendaEntry, ...] = (),
    ) -> str:
        """
        The part's title and subtitle on the dark ground, over the footer band.

        ``agenda`` lists every part with its first sheet, this one marked (#350):
        the title then takes a sidebar layout's main region, and the list its side.
        """
        frames: dict[str, Any] = {}
        if agenda:
            main, side = box.regions("sidebar", scheme_of(engine).space.gutter)
            frames = {"main": main, "side": side}
        return engine.render(
            self.template_path,
            {
                **self._base_context(engine),
                **(footer or SheetFooter.of(number)).context(),
                "subtitle": self.subtitle,
                "valign": self.valign,
                "box": box,
                "number": number,
                "footer_label": label,
                "agenda": agenda,
                "frames": frames,
            },
        )


@dataclass(frozen=True)
class AgendaEntry:
    """One part on a divider's agenda: its title, its first sheet, and whether it is this one."""

    title: str
    number: int
    current: bool


class StatementSlide(Slide):
    """
    One figure on a sheet of its own: a ``HeroStat`` centred on the theme's dark ground (#349).

    No title band, and no sections but the figure. The title, when given, is
    what a contents list names and the text part heads it with; the sheet
    carries only its anchor, so a contents entry still finds its page. In any
    other medium it is the figure itself.

    Args:
        stat:   The figure, at its own size.
        title:  The slide's line in a contents list; never drawn.
        notes:  As a ``Slide`` takes them.
        anchor: The ``id`` a contents entry links to; a slug of the title when unset.
    """

    template_path = "deck/statement.html"

    TITLE_BAND = False

    def __init__(
        self,
        stat: HeroStat,
        title: str | None = None,
        notes: str | None = None,
        anchor: str | None = None,
    ):
        if not isinstance(stat, HeroStat):
            raise ValidationError(
                f"a statement slide sets one HeroStat, got: {type(stat).__name__}. "
                "Several figures are a CardGroup on a slide."
            )
        self.stat = stat
        super().__init__(
            [FullWidth(content=stat, align="center")], title=title, notes=notes, anchor=anchor
        )

    def text(self) -> str:
        """The title, underlined, then the figure's own projection."""
        return join_blocks(underline(self.title or ""), self.stat.text())

    def render_sheet(
        self,
        engine: Renderer,
        box: SlideBox,
        number: int,
        label: str,
        footer: SheetFooter | None = None,
    ) -> str:
        """The figure centred in the body, on the dark ground, over the footer band."""
        dark = engine.theme.palette.header_bg
        theme = replace(engine.theme, palette=replace(engine.theme.palette, surface=dark))
        themed = grounded(rebind(engine, theme=theme), theme.on_ground(dark))
        region = box.regions("full", 0)[0]
        body = rebind(themed, size=_body_scheme(scheme_of(engine), box, region))
        return themed.render(
            self.template_path,
            {
                **self._base_context(themed),
                **(footer or SheetFooter.of(number)).context(),
                "html": "\n".join(section.render(body) for section in self.sections),
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
