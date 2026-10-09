"""
Every size in the email, as one validated object per density.

A ``SizeScheme`` is four frozen scales — ``type`` (font sizes and
line-heights), ``space`` (section, column and region spacing),
``component`` (sizes off the global scale) and ``frame`` (the page and
the padding inside it, from which column widths are computed). ``frame``
is the one layer with **two** owners: its page comes from the medium's
:class:`PageFormat`, its paddings from the density.

``size_theme`` names a density or passes a derived :class:`SizeScheme`;
``render()`` lays the medium's page over it and binds it as ``size``, which
templates read. :class:`Spacing` derives it again for one object's subtree.

`.claude/rules/design-axes.md` carries why, and the token audit.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, replace
from typing import Any, ClassVar

from pyhermes.config import get_config

from .enums import SizeTheme
from .exceptions import ValidationError


def _validate_size_fields(instance: object, prefix: str) -> None:
    """
    Run every token of a frozen layer through the numeric rule.

    ``bool`` is rejected explicitly: it is an ``int`` subclass, so
    ``padding=True`` would otherwise sail through and render as ``1px``.
    """
    optional = getattr(type(instance), "OPTIONAL", ())
    for spec in fields(instance):  # type: ignore[arg-type]
        value = getattr(instance, spec.name)
        name = f"{prefix}.{spec.name}"
        # A token named OPTIONAL may be None, and None is a *state* rather
        # than a missing number: a continuous frame has no page height, and
        # a medium that never collapses has no breakpoint.
        if value is None and spec.name in optional:
            continue
        if isinstance(value, PageMargin):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(
                f"'{name}' must be a positive number, got: {type(value).__name__}"
            )
        if value <= 0:
            raise ValidationError(f"'{name}' must be positive, got: {value}")
        if isinstance(value, float) and value.is_integer():
            raise ValidationError(
                f"'{name}' is the integral float {value}, which would render as "
                f"'{value}px' and break byte-identity. Pass {int(value)} instead."
            )


@dataclass(frozen=True)
class TypeScale:
    """
    Font sizes, and the line-heights more than one component shares.

    Named by role rather than by number, for the reason the colour epic
    learned: a value-keyed vocabulary is byte-identical and useless, because
    changing the masthead would silently change every body heading that
    happened to share its size.
    """

    title: int | float = 28
    title_mobile: int | float = 22
    section: int | float = 17
    subheading: int | float = 16
    item_title: int | float = 15
    body: int | float = 14
    secondary: int | float = 13
    small: int | float = 11
    label: int | float = 10
    micro: int | float = 9.5

    title_line: int | float = 1.2
    heading_line: int | float = 1.3
    body_line: int | float = 1.72
    secondary_line: int | float = 1.4

    #: A prose block's longest line, in ``ch`` (#358): written as px from ``body``.
    measure_standard: int | float = 75
    measure_narrow: int | float = 60

    def __post_init__(self) -> None:
        _validate_size_fields(self, "type")


@dataclass(frozen=True)
class SpacingScale:
    """
    Padding, gaps and the column gutter — the email's vertical rhythm.

    The frame's horizontal padding is **not** here: it lives on
    :class:`FrameGeometry`, because it is what makes the content 616px wide
    and every column width derives from that.
    """

    gutter: int | float = 16
    section_title_top: int | float = 22
    section_title_bottom: int | float = 12
    content_top: int | float = 16
    content_bottom: int | float = 14
    column_top: int | float = 2
    column_bottom: int | float = 26
    column_pad_x: int | float = 20
    column_pad_x_narrow: int | float = 16
    mobile_pad_y: int | float = 20
    mobile_pad_x: int | float = 18
    block_gap: int | float = 16
    subtitle_gap: int | float = 12
    caption_gap: int | float = 8

    masthead_bar_y: int | float = 7
    masthead_top: int | float = 18
    masthead_title_bottom: int | float = 6
    masthead_campaign_bottom: int | float = 8
    masthead_meta_top: int | float = 10
    masthead_meta_bottom: int | float = 18
    #: The v:rect Outlook draws in place of the CSS background image, and a
    #: box the masthead has to *fit inside*: the textbox carries
    #: ``mso-fit-shape-to-text:false``, so the shape does not grow with its
    #: content, and anything past it falls onto the flat band instead of the
    #: photograph.
    #:
    #: It did not fit until the masthead became a 2x2 grid. Stacked — a logo
    #: band above the copy — the natural height was 178.6 / 207.5 / 244.6 px
    #: against boxes of 150 / 180 / 220, overflowing by ~25-29px at every
    #: density, and the department line took that to ~44-47. Pairing the logo
    #: with the title and the department with the subtitle removed a whole
    #: band: 143.0 / 163.9 / 190.6 px, inside the box everywhere, and the
    #: department now costs nothing because it shares a row. Both figures
    #: measured in Chromium; keep the headroom in mind before adding a line
    #: to the masthead, since exceeding it degrades quietly rather than
    #: loudly.
    masthead_vml_height: int | float = 180

    footer_contact_top: int | float = 8
    footer_contact_bottom: int | float = 30
    footer_legal_top: int | float = 20
    footer_legal_bottom: int | float = 8
    footer_copyright_top: int | float = 6
    footer_copyright_bottom: int | float = 24

    def __post_init__(self) -> None:
        _validate_size_fields(self, "space")


@dataclass(frozen=True)
class ComponentScale:
    """
    Sizes that do not follow the global scale linearly.

    A KPI value is 21px because it is a number meant to be read across a
    room, not because 21 is a step on the type scale; a table cell's padding
    answers to column density, not to the section rhythm. Keeping them here
    means a theme can make the body denser without shrinking the one number
    the reader came for.
    """

    kpi_value: int | float = 21
    #: One figure set alone (#322): larger than ``kpi_value`` in every density.
    hero_value: int | float = 44
    card_pad_y: int | float = 14
    card_pad_x: int | float = 16
    kpi_pad_y: int | float = 16
    kpi_pad_x: int | float = 12
    card_label_gap: int | float = 6
    card_value_gap: int | float = 4
    card_body_line: int | float = 1.6

    table_cell_pad: int | float = 12
    #: The same cell at the mobile breakpoint (#132). A data table has no
    #: collapse — stacking its columns would destroy the alignment that is
    #: the only reason to render one — so the one thing that can give a
    #: narrow viewport room back is the padding. Curated, not halved: the
    #: frame's own mobile tightening is 18px against 32, and these follow
    #: that ratio rather than a multiplier.
    table_cell_pad_mobile: int | float = 6
    #: The thickness of a figure's in-cell bar (#227). A box, not spacing.
    table_bar_height: int | float = 6
    #: The height of a change's drawn arrow (#319); its base is 1.2 times it.
    trend_arrow: int | float = 7
    #: The space between two slots of a separated row, a gutter each side of it (#398),
    #: and the connector arrow's length there (#399); its base is four fifths of that.
    connector: int | float = 24
    #: A sparkline's box (#321): the height of its tallest bar, each bar's
    #: width, and the gap between two.
    sparkline_height: int | float = 24
    sparkline_bar: int | float = 4
    sparkline_gap: int | float = 1
    #: Above and below each row of a bar list (#320).
    bar_list_pad: int | float = 5
    #: A badge's padding inside its tint (#325), and a status column's dot (#326).
    badge_pad_y: int | float = 2
    badge_pad_x: int | float = 6
    status_dot: int | float = 8
    #: Above and below each fact in a fact list (#330).
    fact_pad: int | float = 6
    #: A timeline's date column, its marker and the rule joining them (#331), and
    #: the space under each event.
    timeline_date: int | float = 96
    timeline_marker: int | float = 10
    timeline_rule: int | float = 2
    timeline_gap: int | float = 14
    #: A teaser's thumbnail in a one-column list (#332).
    teaser_thumb: int | float = 120

    list_ordinal_width: int | float = 22
    list_ordinal_gap: int | float = 12
    list_title_gap: int | float = 6
    list_body_line: int | float = 1.68

    prose_gap: int | float = 10
    prose_indent: int | float = 24
    prose_item_gap: int | float = 4

    author_name_gap: int | float = 4
    author_sep_gap: int | float = 4
    author_rule_gap: int | float = 14

    cta_width: int | float = 150
    cta_height: int | float = 38
    contact_pad_y: int | float = 22
    contact_pad_x: int | float = 24
    contact_heading_gap: int | float = 6
    contact_cta_gap: int | float = 16
    callout_pad_y: int | float = 16
    callout_pad_x: int | float = 20
    contact_line: int | float = 1.55
    legal_line: int | float = 1.6

    def __post_init__(self) -> None:
        _validate_size_fields(self, "component")


@dataclass(frozen=True)
class PageMargin:
    """
    The four print margins of a sheet, in px at 96 dpi.

    Its own type because zero is a real margin here: the continuous page an
    email renders into has none, where every other size token must be
    positive. Validated here, and exempt from that rule in the layers that
    carry it.
    """

    top: int | float = 0
    right: int | float = 0
    bottom: int | float = 0
    left: int | float = 0

    def __post_init__(self) -> None:
        for spec in fields(self):
            value = getattr(self, spec.name)
            name = f"page.margin.{spec.name}"
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"'{name}' must be a number, got: {type(value).__name__}")
            if value < 0:
                raise ValidationError(f"'{name}' must not be negative, got: {value}")
            if isinstance(value, float) and value.is_integer():
                raise ValidationError(
                    f"'{name}' is the integral float {value}, which would render as "
                    f"'{value}px'. Pass {int(value)} instead."
                )


@dataclass(frozen=True)
class PageFormat:
    """
    The page a medium renders onto: how wide, how tall, when it collapses.

    **The medium owns this, not the density.** A page is a property of where
    a document is read — an email client's column, a sheet of A4, a slide —
    and the three shipped densities prove it: not one of them changes the
    width, only the padding inside it. ``Medium.page_format`` declares it and
    :meth:`SizeScheme.with_page` layers it over the density at render time.

    ``height`` of ``None`` means **continuous**: an email body and a web page
    end where their content does. ``mobile_breakpoint`` of ``None`` means the
    frame never collapses, which is what a printed page does.

    ``width`` and ``height`` are the **sheet**, what ``@page size`` prints.
    The **frame** the tables are sized to is the sheet less its ``margin``
    (#175), and the arithmetic lives in :attr:`frame_width` and
    :attr:`frame_height` rather than in any template.
    """

    OPTIONAL: ClassVar[tuple[str, ...]] = ("height", "mobile_breakpoint")

    width: int | float
    height: int | float | None = None
    mobile_breakpoint: int | float | None = None
    margin: PageMargin = PageMargin()

    def __post_init__(self) -> None:
        _validate_size_fields(self, "page")
        if not isinstance(self.margin, PageMargin):
            raise ValidationError(
                f"'page.margin' must be a PageMargin, got: {type(self.margin).__name__}"
            )
        if self.margin.left + self.margin.right >= self.width:
            raise ValidationError(
                f"'page.margin' left and right ({self.margin.left} + {self.margin.right}) "
                f"leave no content width inside 'page.width' ({self.width})."
            )
        if self.height is not None and self.margin.top + self.margin.bottom >= self.height:
            raise ValidationError(
                f"'page.margin' top and bottom ({self.margin.top} + {self.margin.bottom}) "
                f"leave no content height inside 'page.height' ({self.height})."
            )
        if self.mobile_breakpoint is not None and self.mobile_breakpoint <= self.width:
            raise ValidationError(
                f"'page.mobile_breakpoint' ({self.mobile_breakpoint}) must exceed "
                f"'page.width' ({self.width}), or the document would collapse to its "
                f"mobile layout at its own design width."
            )

    @property
    def orientation(self) -> str:
        """
        ``continuous``, ``portrait``, ``landscape`` or ``square``.

        Derived rather than stored: a declared orientation is a second fact
        about the same two numbers, and the two can disagree. This one
        cannot be wrong about the page it describes.
        """
        if self.height is None:
            return "continuous"
        if self.height > self.width:
            return "portrait"
        return "landscape" if self.width > self.height else "square"

    @property
    def frame_width(self) -> int | float:
        """The width inside the side margins: what the body tables fill."""
        return self.width - self.margin.left - self.margin.right

    @property
    def frame_height(self) -> int | float | None:
        """The height inside the top and bottom margins; ``None`` when continuous."""
        if self.height is None:
            return None
        return self.height - self.margin.top - self.margin.bottom


#: The shipped page: the 680px column this package has always rendered into,
#: continuous, collapsing at 700. The single source for those numbers — the
#: frame layer's defaults and ``DEFAULT_MEDIUM`` both read them from here.
DEFAULT_PAGE = PageFormat(width=680, mobile_breakpoint=700)


#: The shipped page presets, in px at 96 dpi — the resolution WeasyPrint and
#: every browser assume, where 1px is 0.75pt. A4 is 210x297mm and Letter
#: 8.5x11in; the slide is the pragmatic 16:9 pixel size rather than a paper.
#:
#: None of them declares a ``mobile_breakpoint``: a sheet of paper does not
#: collapse to a phone layout, and a breakpoint the skeleton never reads
#: would be a number pretending to be a rule.
#:
#: Each paper keeps one margin all round and in either orientation (#175):
#: 20mm (76px) on A4, 0.75in (72px) on Letter. The frame's own ``pad_x``
#: still insets the copy inside it. A slide is projected rather than
#: printed, so it keeps a narrower 10mm (38px). No preset's frame is 680px
#: wide, deliberately: a template still reading the email's frame would
#: then render correctly on paper and nothing could see it.
A4_MARGIN = PageMargin(top=76, right=76, bottom=76, left=76)
LETTER_MARGIN = PageMargin(top=72, right=72, bottom=72, left=72)
SLIDE_MARGIN = PageMargin(top=38, right=38, bottom=38, left=38)

A4_PORTRAIT = PageFormat(width=794, height=1123, margin=A4_MARGIN)
A4_LANDSCAPE = PageFormat(width=1123, height=794, margin=A4_MARGIN)
LETTER_PORTRAIT = PageFormat(width=816, height=1056, margin=LETTER_MARGIN)
LETTER_LANDSCAPE = PageFormat(width=1056, height=816, margin=LETTER_MARGIN)
SLIDE_16_9 = PageFormat(width=1280, height=720, margin=SLIDE_MARGIN)
#: The older projector shape (#296), at the 16:9 slide's margin.
SLIDE_4_3 = PageFormat(width=1024, height=768, margin=SLIDE_MARGIN)

#: Every shipped page by name, the way ``SIZE_SCHEMES`` names every density.
PAGE_FORMATS: dict[str, PageFormat] = {
    "default": DEFAULT_PAGE,
    "a4_portrait": A4_PORTRAIT,
    "a4_landscape": A4_LANDSCAPE,
    "letter_portrait": LETTER_PORTRAIT,
    "letter_landscape": LETTER_LANDSCAPE,
    "slide_16_9": SLIDE_16_9,
    "slide_4_3": SLIDE_4_3,
}


@dataclass(frozen=True)
class FrameGeometry:
    """
    The resolved frame: the medium's page and the density's edge spacing.

    Templates read this as ``size.frame``. Its page dimensions come from a
    :class:`PageFormat` the medium owns and its paddings from the density,
    so a preset cannot decide how wide a page is and a medium cannot decide
    how roomy it feels.

    ``inner`` is a property rather than a field on purpose: a stored inner
    width could disagree with ``width - 2 * pad_x``, and one of the two
    would then be silently wrong. The eight container templates that each
    wrote out this arithmetic twice per column are exactly what that
    disagreement looks like in practice.
    """

    OPTIONAL: ClassVar[tuple[str, ...]] = PageFormat.OPTIONAL

    width: int | float = DEFAULT_PAGE.frame_width
    height: int | float | None = DEFAULT_PAGE.frame_height
    mobile_breakpoint: int | float | None = DEFAULT_PAGE.mobile_breakpoint
    margin: PageMargin = DEFAULT_PAGE.margin
    pad_x: int | float = 32
    outer_pad_y: int | float = 28
    narrow_column: int | float = 300

    def __post_init__(self) -> None:
        _validate_size_fields(self, "frame")
        if not isinstance(self.margin, PageMargin):
            raise ValidationError(
                f"'frame.margin' must be a PageMargin, got: {type(self.margin).__name__}"
            )
        if self.pad_x * 2 >= self.width:
            raise ValidationError(
                f"'frame.pad_x' ({self.pad_x}) leaves no content width inside "
                f"'frame.width' ({self.width})."
            )
        if self.mobile_breakpoint is not None and self.mobile_breakpoint <= self.width:
            raise ValidationError(
                f"'frame.mobile_breakpoint' ({self.mobile_breakpoint}) must exceed "
                f"'frame.width' ({self.width}), or the email would collapse to its "
                f"mobile layout at its own design width."
            )

    @property
    def inner(self) -> int | float:
        """The content width: ``width`` less the frame padding on both sides."""
        return self.width - 2 * self.pad_x

    @property
    def sheet_width(self) -> int | float:
        """The printed sheet: the frame plus its side margins."""
        return self.width + self.margin.left + self.margin.right

    @property
    def sheet_height(self) -> int | float | None:
        """The printed sheet's height; ``None`` for a continuous frame."""
        if self.height is None:
            return None
        return self.height + self.margin.top + self.margin.bottom


@dataclass(frozen=True)
class SizeScheme:
    """
    One complete density: the four layers together.

    Frozen and fully validated, so a ``SizeScheme`` that exists is a
    ``SizeScheme`` that renders — no token is optional, and
    ``StrictUndefined`` cannot be tripped by a half-built one.
    """

    LAYERS: ClassVar[dict[str, type]] = {
        "type": TypeScale,
        "space": SpacingScale,
        "component": ComponentScale,
        "frame": FrameGeometry,
    }

    type: TypeScale = TypeScale()
    space: SpacingScale = SpacingScale()
    component: ComponentScale = ComponentScale()
    frame: FrameGeometry = FrameGeometry()

    def __post_init__(self) -> None:
        for name, layer_cls in self.LAYERS.items():
            value = getattr(self, name)
            if not isinstance(value, layer_cls):
                raise ValidationError(
                    f"'{name}' must be a {layer_cls.__name__}, got: {type(value).__name__}"
                )

    def derive(self, **layers: Any) -> SizeScheme:
        """
        A copy of this scheme with some tokens changed.

        Each keyword is a layer name; its value is either a whole layer
        instance or a mapping of the fields to override. This is how the
        shipped presets are written: what a preset *decides* is then the
        literal content of its definition, and everything it inherits is
        visibly inherited rather than restated.

        ``replace`` re-runs each layer's ``__post_init__``, so the result is
        validated exactly as a hand-built one would be.
        """
        unknown = set(layers) - set(self.LAYERS)
        if unknown:
            raise ValidationError(
                f"unknown size layer(s) {sorted(unknown)}; known layers: {sorted(self.LAYERS)}"
            )
        resolved: dict[str, Any] = {}
        for name, override in layers.items():
            layer_cls = self.LAYERS[name]
            if isinstance(override, layer_cls):
                resolved[name] = override
            elif isinstance(override, dict):
                current = getattr(self, name)
                unknown_fields = set(override) - {f.name for f in fields(layer_cls)}
                if unknown_fields:
                    raise ValidationError(
                        f"unknown token(s) {sorted(unknown_fields)} for size layer "
                        f"'{name}'; known: {sorted(f.name for f in fields(layer_cls))}"
                    )
                resolved[name] = replace(current, **override)
            else:
                raise ValidationError(
                    f"size layer '{name}' must be a {layer_cls.__name__} or a mapping "
                    f"of its tokens, got: {type(override).__name__}"
                )
        return replace(self, **resolved)

    def with_page(self, page: PageFormat) -> SizeScheme:
        """
        This density, rendered onto ``page``.

        The page is layered **over** the density's frame, never under it —
        the same precedence :meth:`pyhermes.builder.regions.Region.context` gives
        an email's facts and :class:`~pyhermes.builder.engine.BoundEngine` gives a
        bound value. What the medium owns cannot be shadowed from below, so a
        caller who derived a frame width of their own does not quietly change
        the page an email is printed on.
        """
        frame = replace(
            self.frame,
            width=page.frame_width,
            height=page.frame_height,
            mobile_breakpoint=page.mobile_breakpoint,
            margin=page.margin,
        )
        # A density already describing this page *is* the answer, so it is
        # returned unchanged rather than copied. That keeps one scheme object
        # shared across every render at the shipped page, which a test relies
        # on to prove the scheme is threaded rather than rebuilt per template.
        return self if frame == self.frame else self.derive(frame=frame)


#: The shipped density — every value exactly what the templates hardcoded
#: before this module existed. It is the byte-identity reference the whole
#: sizing epic is measured against.
STANDARD_SIZES = SizeScheme()

#: Denser: more of the letter on one screen, without shrinking what a
#: reader actually reads.
#:
#: Written as a ``derive`` so the diff *is* the design: every number below
#: is a decision, and everything absent is deliberately inherited. Four
#: rules shape it, and none of them is a multiplier —
#:
#: * **Type shrinks from the top down.** The masthead loses 4px and body
#:   copy loses 1; ``label`` and ``micro`` do not move at all. Fine print at
#:   9.5px is already at the readability floor, and a "compact" theme that
#:   made a disclaimer unreadable would be a broken theme, not a dense one.
#: * **Leading tightens less than type does.** Smaller type needs
#:   proportionally *more* leading, not less, so ``body_line`` goes 1.72 to
#:   1.6 rather than tracking the 14-to-13 drop.
#: * **Most of the density is spacing.** Padding and gaps are what a reader
#:   experiences as airiness, and they are also what costs the least
#:   legibility to reclaim.
#: * **The number the reader came for shrinks least.** ``kpi_value`` gives
#:   up 2px of 21; a KPI strip exists to be read across a room.
COMPACT_SIZES = SizeScheme().derive(
    type={
        "title": 24,
        "title_mobile": 20,
        "section": 16,
        "subheading": 15,
        "item_title": 14,
        "body": 13,
        "secondary": 12,
        "small": 10,
        # label (10) and micro (9.5) hold: the readability floor.
        "title_line": 1.15,
        "heading_line": 1.25,
        "body_line": 1.6,
        "secondary_line": 1.35,
    },
    space={
        "gutter": 12,
        "section_title_top": 16,
        "section_title_bottom": 8,
        "content_top": 12,
        "content_bottom": 10,
        "column_bottom": 18,
        "column_pad_x": 16,
        "column_pad_x_narrow": 12,
        "mobile_pad_y": 14,
        "mobile_pad_x": 14,
        "block_gap": 12,
        "subtitle_gap": 8,
        "caption_gap": 6,
        "masthead_bar_y": 5,
        "masthead_top": 12,
        "masthead_title_bottom": 4,
        "masthead_campaign_bottom": 6,
        "masthead_meta_top": 8,
        "masthead_meta_bottom": 12,
        "masthead_vml_height": 150,
        "footer_contact_top": 6,
        "footer_contact_bottom": 20,
        "footer_legal_top": 14,
        "footer_legal_bottom": 6,
        "footer_copyright_top": 4,
        "footer_copyright_bottom": 16,
    },
    component={
        "kpi_value": 19,
        "hero_value": 36,
        "bar_list_pad": 4,
        "badge_pad_y": 1,
        "badge_pad_x": 5,
        "status_dot": 7,
        "fact_pad": 4,
        "timeline_date": 84,
        "timeline_marker": 8,
        "timeline_gap": 10,
        "teaser_thumb": 96,
        "trend_arrow": 6,
        "connector": 20,
        "sparkline_height": 18,
        "sparkline_bar": 3,
        "card_pad_y": 10,
        "card_pad_x": 12,
        "kpi_pad_y": 12,
        "kpi_pad_x": 10,
        "card_label_gap": 4,
        "card_value_gap": 3,
        "card_body_line": 1.5,
        "table_cell_pad": 8,
        "table_cell_pad_mobile": 4,
        "list_ordinal_width": 20,
        "list_ordinal_gap": 10,
        "list_title_gap": 4,
        "list_body_line": 1.55,
        "prose_gap": 8,
        "prose_indent": 22,
        "prose_item_gap": 3,
        "author_name_gap": 3,
        "author_rule_gap": 10,
        "cta_width": 140,
        "cta_height": 34,
        "contact_pad_y": 16,
        "contact_pad_x": 18,
        "contact_heading_gap": 4,
        "contact_cta_gap": 12,
        "callout_pad_y": 12,
        "callout_pad_x": 16,
        "contact_line": 1.45,
        "legal_line": 1.5,
    },
    # The frame width does not move — see the epic's non-goals. What moves
    # is how much of it is margin: 24px of side padding instead of 32 gives
    # every column 16px more to work with.
    frame={"pad_x": 24, "outer_pad_y": 20},
)

#: Airier: fewer things per screen, each with room around it.
#:
#: Not the inverse of ``COMPACT`` applied to the same numbers — the two were
#: curated separately, and it shows in ``narrow_column``, the one token that
#: moves *down* in the roomiest theme:
#:
#: * A 24px gutter spends more of the frame between the columns, so a
#:   two-up split lands at 288px, just under the 300px threshold. Holding
#:   the threshold there would have handed the airiest theme the *tightest*
#:   column padding — and a 288px column carrying 15px type is not narrow,
#:   it is half the email. 260 is where the distinction actually falls here.
#: * Type grows across the whole scale, ``micro`` included: 10.5px fine
#:   print is the one place where "spacious" is a legibility gain rather
#:   than a stylistic one.
#: * Leading opens further than type grows, which is what makes long prose
#:   read as unhurried rather than merely large.
SPACIOUS_SIZES = SizeScheme().derive(
    type={
        "title": 32,
        "title_mobile": 24,
        "section": 19,
        "subheading": 18,
        "item_title": 16,
        "body": 15,
        "secondary": 14,
        "small": 12,
        "label": 11,
        "micro": 10.5,
        "title_line": 1.25,
        "heading_line": 1.4,
        "body_line": 1.85,
        "secondary_line": 1.5,
    },
    space={
        "gutter": 24,
        "section_title_top": 30,
        "section_title_bottom": 16,
        "content_top": 22,
        "content_bottom": 20,
        "column_top": 4,
        "column_bottom": 34,
        "column_pad_x": 26,
        "column_pad_x_narrow": 20,
        "mobile_pad_y": 26,
        "mobile_pad_x": 22,
        "block_gap": 22,
        "subtitle_gap": 16,
        "caption_gap": 12,
        "masthead_bar_y": 10,
        "masthead_top": 24,
        "masthead_title_bottom": 8,
        "masthead_campaign_bottom": 12,
        "masthead_meta_top": 14,
        "masthead_meta_bottom": 24,
        "masthead_vml_height": 220,
        "footer_contact_top": 12,
        "footer_contact_bottom": 40,
        "footer_legal_top": 28,
        "footer_legal_bottom": 12,
        "footer_copyright_top": 10,
        "footer_copyright_bottom": 32,
    },
    component={
        "kpi_value": 24,
        "hero_value": 52,
        "bar_list_pad": 7,
        "badge_pad_y": 3,
        "badge_pad_x": 8,
        "status_dot": 9,
        "fact_pad": 8,
        "timeline_date": 108,
        "timeline_marker": 12,
        "timeline_gap": 20,
        "teaser_thumb": 144,
        "trend_arrow": 8,
        "connector": 28,
        "sparkline_height": 28,
        "sparkline_bar": 5,
        "sparkline_gap": 2,
        "card_pad_y": 20,
        "card_pad_x": 22,
        "kpi_pad_y": 22,
        "kpi_pad_x": 16,
        "card_label_gap": 8,
        "card_value_gap": 6,
        "card_body_line": 1.75,
        "table_cell_pad": 16,
        "table_cell_pad_mobile": 8,
        "list_ordinal_width": 26,
        "list_ordinal_gap": 16,
        "list_title_gap": 8,
        "list_body_line": 1.8,
        "author_name_gap": 6,
        "author_sep_gap": 6,
        "author_rule_gap": 20,
        "cta_width": 170,
        "cta_height": 44,
        "contact_pad_y": 30,
        "contact_pad_x": 32,
        "contact_heading_gap": 8,
        "contact_cta_gap": 22,
        "callout_pad_y": 20,
        "callout_pad_x": 26,
        "contact_line": 1.7,
        "legal_line": 1.75,
    },
    frame={"pad_x": 40, "outer_pad_y": 36, "narrow_column": 260},
)

#: Packed for print (#211): a quantitative sheet at a printed factsheet's
#: density, where ``compact`` is still tuned for a screen.
#:
#: Derived from ``COMPACT`` rather than ``STANDARD``, so what dense decides
#: *beyond* compact is the literal content below. Three rules, in the shape
#: of compact's four:
#:
#: * **The readability floor moves, and stops at 8px.** ``label`` and
#:   ``micro`` held in compact; on paper 9px is 6.75pt and 8.5px is 6.4pt,
#:   both above the 6pt below which fine print is not read.
#: * **Leading tightens less than type.** Body type gives up 2px of 13;
#:   ``body_line`` gives up 0.2 of 1.6, the smaller share.
#: * **Most of the density is still spacing**, and a table row is where it
#:   is spent: ``table_cell_pad`` 4 against compact's 8 is the move that
#:   takes a row from about 37px to about 21px.
#:
#: The frame's ``pad_x`` is 12 because a sheet already has a printed margin;
#: an email's padding is the only margin it has.
DENSE_SIZES = COMPACT_SIZES.derive(
    type={
        "title": 20,
        "title_mobile": 18,
        "section": 13,
        "subheading": 12,
        "item_title": 12,
        "body": 11,
        "secondary": 10.5,
        "small": 9.5,
        "label": 9,
        "micro": 8.5,
        "title_line": 1.15,
        "heading_line": 1.2,
        "body_line": 1.4,
        "secondary_line": 1.3,
    },
    space={
        "gutter": 10,
        "section_title_top": 10,
        "section_title_bottom": 5,
        "content_top": 6,
        "content_bottom": 6,
        "column_bottom": 8,
        "column_pad_x": 10,
        "column_pad_x_narrow": 8,
        "block_gap": 8,
        "subtitle_gap": 5,
        "caption_gap": 4,
        "masthead_top": 8,
        "masthead_meta_top": 6,
        "masthead_meta_bottom": 8,
        "footer_contact_bottom": 12,
        "footer_legal_top": 8,
        "footer_copyright_bottom": 10,
    },
    component={
        "kpi_value": 17,
        "hero_value": 30,
        "bar_list_pad": 2,
        "badge_pad_y": 1,
        "badge_pad_x": 4,
        "status_dot": 6,
        "fact_pad": 3,
        "timeline_date": 76,
        "timeline_marker": 7,
        "timeline_gap": 8,
        "teaser_thumb": 88,
        "trend_arrow": 5,
        "connector": 18,
        "sparkline_height": 16,
        "card_pad_y": 6,
        "card_pad_x": 8,
        "kpi_pad_y": 6,
        "kpi_pad_x": 8,
        "card_label_gap": 3,
        "card_value_gap": 2,
        "card_body_line": 1.35,
        "table_cell_pad": 4,
        "table_cell_pad_mobile": 3,
        "list_ordinal_width": 18,
        "list_ordinal_gap": 8,
        "list_title_gap": 3,
        "list_body_line": 1.4,
        "prose_gap": 5,
        "prose_indent": 18,
        "prose_item_gap": 2,
        "author_name_gap": 2,
        "author_sep_gap": 3,
        "author_rule_gap": 8,
        "contact_pad_y": 10,
        "contact_pad_x": 12,
        "contact_heading_gap": 3,
        "contact_cta_gap": 8,
        "callout_pad_y": 8,
        "callout_pad_x": 12,
        "contact_line": 1.35,
        "legal_line": 1.35,
    },
    frame={"pad_x": 12, "outer_pad_y": 10},
)

#: Read across a room, or on a screen at a glance (#301).
#:
#: Derived from ``SPACIOUS`` and set from the deck fixture's PDF. A 1280px
#: slide is a 960pt sheet, PowerPoint's own 13.33in, so 1px prints as 0.75pt.
#: ``spacious`` measured 11.25pt body and a 24pt title there, a printed
#: report's sizes; this sets 15pt body, a 30pt title and 33pt KPI values.
#: Leading tightens rather than loosens: a slide is read in lines, and its
#: height is fixed. `deck.md` has the measurements and the photographs.
PRESENTATION_SIZES = SPACIOUS_SIZES.derive(
    type={
        "title": 40,
        "title_mobile": 32,
        "section": 28,
        "subheading": 24,
        "item_title": 22,
        "body": 20,
        "secondary": 18,
        "small": 16,
        "label": 14,
        "micro": 13,
        "title_line": 1.15,
        "heading_line": 1.25,
        "body_line": 1.45,
        "secondary_line": 1.35,
    },
    space={
        "gutter": 32,
        "section_title_top": 18,
        "section_title_bottom": 14,
        "content_top": 12,
        "content_bottom": 12,
        "column_bottom": 16,
        "column_pad_x": 28,
        "column_pad_x_narrow": 24,
        "block_gap": 18,
        "subtitle_gap": 12,
        "caption_gap": 10,
    },
    component={
        "kpi_value": 44,
        "hero_value": 88,
        "bar_list_pad": 8,
        "badge_pad_y": 3,
        "badge_pad_x": 9,
        "status_dot": 11,
        "fact_pad": 9,
        "timeline_date": 150,
        "timeline_marker": 16,
        "timeline_rule": 3,
        "timeline_gap": 22,
        "teaser_thumb": 180,
        "trend_arrow": 11,
        "connector": 40,
        "sparkline_height": 40,
        "sparkline_bar": 8,
        "sparkline_gap": 2,
        "kpi_pad_y": 20,
        "kpi_pad_x": 18,
        "card_body_line": 1.4,
        "table_cell_pad": 10,
        "table_bar_height": 8,
        "list_ordinal_width": 34,
        "list_body_line": 1.45,
        "cta_width": 200,
        "cta_height": 52,
        "contact_line": 1.45,
        "legal_line": 1.45,
    },
)

#: Every scheme the repo ships, by name. Repo-owned and never mutated at
#: runtime: a house density is a ``derive`` passed as an object (#212), not
#: a name registered here.
SIZE_SCHEMES: dict[SizeTheme, SizeScheme] = {
    SizeTheme.COMPACT: COMPACT_SIZES,
    SizeTheme.STANDARD: STANDARD_SIZES,
    SizeTheme.SPACIOUS: SPACIOUS_SIZES,
    SizeTheme.DENSE: DENSE_SIZES,
    SizeTheme.PRESENTATION: PRESENTATION_SIZES,
}

#: The shipped densities no email client has rendered. The email medium
#: refuses them, as it refuses a custom scheme, unless
#: ``Config.allow_custom_email_density`` says the caller has.
PRINT_DENSITIES: frozenset[SizeTheme] = frozenset({SizeTheme.DENSE, SizeTheme.PRESENTATION})

#: A density one medium alone may take, by ``Medium.name`` (#301). A slide's
#: type on an A4 sheet or in an inbox is a mistake, not a choice, and no
#: config switch admits it, unlike a print density in an email.
MEDIUM_DENSITIES: dict[SizeTheme, str] = {SizeTheme.PRESENTATION: "deck"}


def resolve_size_scheme(value: SizeTheme | str | SizeScheme) -> SizeScheme:
    """
    Turn whatever a caller supplied into a concrete :class:`SizeScheme`.

    Accepts a :class:`~pyhermes.builder.enums.SizeTheme` member, its bare string,
    or a :class:`SizeScheme`, which is returned unchanged. Anything else is
    refused. Which medium may take which density is the document's check.
    """
    if isinstance(value, SizeScheme):
        return value
    if isinstance(value, str):
        try:
            return SIZE_SCHEMES[SizeTheme(value)]
        except ValueError:
            raise ValidationError(
                f"unknown size theme {value!r}; known themes: "
                f"{sorted(t.value for t in SIZE_SCHEMES)}"
            ) from None
        except KeyError:
            raise ValidationError(
                f"size theme {value!r} has no scheme yet; available: "
                f"{sorted(t.value for t in SIZE_SCHEMES)}"
            ) from None
    raise ValidationError(
        f"'size_theme' must be a SizeTheme, its name, or a SizeScheme, got: {type(value).__name__}"
    )


# ----------------------------------------------------------------------
# Spacing — the per-object override, as a derive of the bound scheme (#213)
# ----------------------------------------------------------------------

#: Tokens no object may move: the medium's page, and the column threshold
#: that follows from it. ``frame.inner`` is a property and so already unnamed.
WIDTH_TOKENS: frozenset[str] = frozenset(
    {"width", "height", "margin", "mobile_breakpoint", "narrow_column"}
)

#: Component tokens that are type rather than spacing: a font size and the
#: leadings. The ``type`` layer is refused whole.
_COMPONENT_TYPE_TOKENS: frozenset[str] = frozenset(
    {
        "kpi_value",
        "hero_value",
        "card_body_line",
        "list_body_line",
        "contact_line",
        "legal_line",
    }
)

#: Component tokens that size a box rather than space it: the button, the
#: column a list's ordinals sit in, a table cell's bar, a change's arrow, a sparkline, a dot,
#: a timeline's date column, marker and rule, and a teaser's thumbnail.
_COMPONENT_BOX_TOKENS: frozenset[str] = frozenset(
    {
        "cta_width",
        "cta_height",
        "list_ordinal_width",
        "table_bar_height",
        "trend_arrow",
        "connector",
        "sparkline_height",
        "sparkline_bar",
        "sparkline_gap",
        "status_dot",
        "timeline_date",
        "timeline_marker",
        "timeline_rule",
        "teaser_thumb",
    }
)

#: Tokens a subtree may not move on a medium that is not paged. The email's
#: ``@media`` block reads the document's scheme, never a subtree's, so each
#: of these would render one way wide and another way collapsed. ``pad_x``
#: joins them because every section, the masthead and the footer share it.
UNPAGED_UNSAFE_TOKENS: frozenset[str] = frozenset(
    {"pad_x", "mobile_pad_x", "mobile_pad_y", "card_pad_x", "card_pad_y", "table_cell_pad_mobile"}
)


def _token_owners() -> dict[str, tuple[str, ...]]:
    """Every token name, and the layer or layers that declare it."""
    owners: dict[str, tuple[str, ...]] = {}
    for layer, layer_cls in SizeScheme.LAYERS.items():
        for spec in fields(layer_cls):
            owners[spec.name] = owners.get(spec.name, ()) + (layer,)
    return owners


#: Token name to the layers declaring it. One layer each today; a name that
#: ever appears in two is refused by :class:`Spacing` rather than guessed.
TOKEN_LAYERS: dict[str, tuple[str, ...]] = _token_owners()


@dataclass(frozen=True, init=False)
class Spacing:
    """
    Named spacing tokens one object moves for itself and everything inside it.

    ``Spacing(content_top=6)`` or ``Spacing({"table_cell_pad": 3})``. A token
    is named flat and its layer is found for the caller. The width, the type
    scale and every leading are refused: an object moves its spacing, never
    its measure or its voice.

    Validated at construction by applying it to ``STANDARD_SIZES``, so a bad
    value fails with the same message a bad preset would.
    """

    items: tuple[tuple[str, int | float], ...]

    def __init__(self, tokens: Mapping[str, int | float] | None = None, /, **named: int | float):
        if tokens is not None and not isinstance(tokens, Mapping):
            raise ValidationError(
                f"Spacing takes a mapping of token names, got: {type(tokens).__name__}"
            )
        merged = {**(tokens or {}), **named}
        if not merged:
            raise ValidationError("a Spacing names at least one token; pass None for none")
        for name in merged:
            _check_spacing_token(name)
        object.__setattr__(self, "items", tuple(sorted(merged.items())))
        self.applied_to(STANDARD_SIZES)

    @property
    def tokens(self) -> dict[str, int | float]:
        """The tokens this override moves, by name."""
        return dict(self.items)

    def by_layer(self) -> dict[str, dict[str, int | float]]:
        """The same tokens grouped by layer, in the shape :meth:`SizeScheme.derive` takes."""
        grouped: dict[str, dict[str, int | float]] = {}
        for name, value in self.items:
            grouped.setdefault(TOKEN_LAYERS[name][0], {})[name] = value
        return grouped

    def applied_to(self, scheme: SizeScheme) -> SizeScheme:
        """``scheme`` with these tokens moved, and every other inherited."""
        return scheme.derive(**self.by_layer())

    def check_medium(self, paged: bool, medium: str, owner: str) -> None:
        """
        Refuse the tokens a non-paged medium cannot honour in a subtree.

        Raises:
            ValidationError: Naming the tokens, the owner and the medium.
        """
        unsafe = [name for name, _ in self.items if name in UNPAGED_UNSAFE_TOKENS]
        if unsafe and not paged:
            raise ValidationError(
                f"{owner} moves {', '.join(repr(name) for name in unsafe)} on the "
                f"'{medium}' medium, whose mobile collapse reads the document's scheme "
                "and not a subtree's, so it would render one way wide and another "
                "collapsed. Move it on a paged medium, or for the whole document."
            )

    def __repr__(self) -> str:
        return f"Spacing({', '.join(f'{name}={value!r}' for name, value in self.items)})"


def _check_spacing_token(name: object) -> None:
    """Refuse a name no object may move, saying which rule it breaks."""
    if not isinstance(name, str):
        raise ValidationError(f"a spacing token is named by a string, got: {name!r}")
    if name in WIDTH_TOKENS:
        raise ValidationError(
            f"'{name}' is the medium's width, and never a spacing token: the page "
            "belongs to the PageFormat and the columns to column_layout"
        )
    owners = TOKEN_LAYERS.get(name)
    if owners is None:
        raise ValidationError(f"unknown spacing token {name!r}")
    if len(owners) > 1:
        raise ValidationError(f"spacing token {name!r} is ambiguous: layers {list(owners)}")
    if owners[0] == "type" or name in _COMPONENT_TYPE_TOKENS:
        raise ValidationError(
            f"'{name}' is type, not spacing: an object may move its spacing, "
            "and the type scale is the document's"
        )
    if name in _COMPONENT_BOX_TOKENS:
        raise ValidationError(f"'{name}' sizes a box, and is not spacing")


def coerce_spacing(
    value: Spacing | Mapping[str, int | float] | None, allowed: Sequence[str], owner: str
) -> Spacing | None:
    """
    ``value`` as a :class:`Spacing`, checked against the tokens ``owner`` reads.

    A token outside ``allowed`` is refused by name: moving a token the
    object's template never reads would be a silent no-op.
    """
    if value is None:
        return None
    spacing = value if isinstance(value, Spacing) else Spacing(value)
    unread = [name for name, _ in spacing.items if name not in allowed]
    if unread:
        readable = ", ".join(allowed) if allowed else "none"
        raise ValidationError(
            f"{owner} reads no {', '.join(repr(name) for name in unread)}; "
            f"the spacing it may move: {readable}"
        )
    return spacing


# ----------------------------------------------------------------------
# Column geometry — the arithmetic eight templates used to write out by hand
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class ColumnGeometry:
    """
    One column's computed width and the padding on each of its sides.

    The two horizontal paddings are **not** the same number, and that is the
    point: a column's *outer* edge faces the frame, which already supplies
    ``frame.pad_x``, so padding it again would indent that column's text past
    the section heading above it. Only the gutter-facing sides are padded
    here. See :func:`column_layout`.
    """

    width: int
    pad_left: int | float
    pad_right: int | float


def _remainder_order(count: int) -> list[int]:
    """
    Which columns get the leftover pixels, in order: outside-in.

    ``[0, n-1, 1, n-2, ...]``. Three equal columns of 584px cannot each be
    194.67 wide, so two of them gain a pixel — and *which* two is a design
    decision that was already made, by hand, in ``col-33-33-33.html``:
    195 / 194 / 195. Outside-in reproduces it, and it is the right rule
    independently. A reader notices an asymmetric left/right pair; nobody
    notices a centre column one pixel narrower than its neighbours.
    """
    order: list[int] = []
    low, high = 0, count - 1
    while low <= high:
        order.append(low)
        if high != low:
            order.append(high)
        low, high = low + 1, high - 1
    return order


def column_layout(
    weights: Sequence[int | float], scheme: SizeScheme, within: int | None = None
) -> list[ColumnGeometry]:
    """
    Split the frame's content width into columns, per the ratio's weights.

    Weights are normalised by their own sum rather than assumed to total
    100 — which is what makes ``"33-33-33"`` exact thirds rather than 99%
    of the frame with a 6px hole in it.

    Widths are integers because Outlook's Word engine reads the ``width``
    **attribute**, and an attribute is an integer. They sum to exactly the
    space between the gutters: floor every column, then hand the remainder
    out in :func:`_remainder_order`, largest fractional part first.

    Each column also carries the padding it earns on its **gutter-facing**
    sides: a column at least ``frame.narrow_column`` wide takes
    ``space.column_pad_x``, a narrower one takes ``space.column_pad_x_narrow``.
    That threshold is not invented here — it is read back out of the
    templates, where a 300px or 420px column had 20px of padding and a 292px
    or smaller one had 16px.

    The outer edges take **zero**, because the band is inset by
    ``frame.pad_x`` and padding it twice is what made every multi-column
    section hang 12-16px to the left of its own heading (#85). The gap
    *between* two columns is unchanged: their facing paddings plus the
    gutter, exactly as before.
    """
    count = len(weights)
    if count < 1:
        raise ValidationError("a column layout needs at least one column")
    total = sum(weights)
    if total <= 0:
        raise ValidationError(f"column weights must be positive, got: {list(weights)}")

    # ``within`` is a cell's own width when the split sits inside one (#263).
    content_width = scheme.frame.inner if within is None else within
    available = content_width - scheme.space.gutter * (count - 1)
    if available < count:
        raise ValidationError(
            f"{count} columns and {count - 1} gutter(s) of "
            f"{scheme.space.gutter}px leave {available}px inside a "
            f"{content_width}px content width — not enough for one pixel each."
        )

    exact = [available * weight / total for weight in weights]
    widths = [int(value) for value in exact]
    remainder = int(available) - sum(widths)
    if remainder:
        order = _remainder_order(count)
        ranked = sorted(order, key=lambda index: -(exact[index] - widths[index]))
        for index in ranked[:remainder]:
            widths[index] += 1

    last = count - 1
    return [
        ColumnGeometry(
            width=width,
            pad_left=0 if index == 0 else _gutter_pad(width, scheme),
            pad_right=0 if index == last else _gutter_pad(width, scheme),
        )
        for index, width in enumerate(widths)
    ]


def column_content_widths(
    weights: Sequence[int | float], scheme: SizeScheme, within: int | None = None
) -> list[int]:
    """Each column's width less its padding: what a block inside it is rendered into."""
    return [
        int(col.width - col.pad_left - col.pad_right)
        for col in column_layout(weights, scheme, within)
    ]


def _gutter_pad(width: int, scheme: SizeScheme) -> int | float:
    """The horizontal padding a column of this width earns beside a gutter."""
    return (
        scheme.space.column_pad_x
        if width >= scheme.frame.narrow_column
        else scheme.space.column_pad_x_narrow
    )


# ----------------------------------------------------------------------
# Stacking on a phone (#362, #363)
# ----------------------------------------------------------------------

#: The narrowest viewport the package supports (#133): what an unstacked split must fit.
PHONE_FLOOR = 375

#: The orders a split may stack in on a phone. ``False`` keeps it side by side.
STACK_ORDERS = ("natural", "reverse")


def coerce_stack(stack: object, owner: str) -> str | bool:
    """
    ``stack`` as stored: ``"natural"``, ``"reverse"`` or ``False``.

    ``True`` reads as ``"natural"``, the order a stacking split has always had.

    Raises:
        ValidationError: On any other value, naming the three.
    """
    if stack is True:
        return "natural"
    if stack is False or (isinstance(stack, str) and stack in STACK_ORDERS):
        return stack
    raise ValidationError(f"{owner}'s stack takes 'natural', 'reverse' or False, got: {stack!r}")


def shares(widths: Sequence[int | float], gutter: int | float, within: int | float) -> list[str]:
    """
    Each column's width, then the gutter's, as a percentage of ``within``, for an unstacked split.

    Floored at four places, so the row never sums past the cell and wraps.
    """

    def share(px: int | float) -> str:
        floored = math.floor(px / within * 1_000_000) / 10_000
        return f"{floored:.4f}".rstrip("0").rstrip(".")

    return [share(width) for width in widths] + [share(gutter)]


def check_unstacked(weights: Sequence[int | float], available: int | float, owner: str) -> None:
    """
    Refuse ``stack=False`` when a column would fall under ``Config.min_column_px`` on a phone.

    ``available`` is what the columns share at the phone floor, gutters taken
    out; each column is its weight's share of it.

    Raises:
        ValidationError: Naming the narrowest column's width at the floor.
    """
    floor = get_config().min_column_px
    total = sum(weights)
    widths = [available * weight / total for weight in weights]
    narrowest = min(range(len(widths)), key=widths.__getitem__)
    if widths[narrowest] < floor:
        raise ValidationError(
            f"{owner} with stack=False keeps its columns side by side on a phone, where "
            f"column {narrowest + 1} is {widths[narrowest]:.0f}px wide at the {PHONE_FLOOR}px "
            f"floor, below Config.min_column_px ({floor}). Let it stack, or give that column "
            "more weight."
        )


# ----------------------------------------------------------------------
# The measure — a prose block's longest line (#358)
# ----------------------------------------------------------------------

#: The measures a prose block takes: two token names, and ``full`` for none.
MEASURES = ("standard", "narrow", "full")

#: One ``ch`` in em: CSS's unit for a measure, the advance of "0", in the body
#: stack's named face (0.61em). `design-axes.md` has the measurements, including
#: the substitute face a print engine without that face sets.
CH_EM = 0.6


def coerce_measure(measure: object, owner: str) -> str | None:
    """
    ``measure`` as stored: one of :data:`MEASURES`, or ``None`` for the medium's.

    Raises:
        ValidationError: On anything else, naming the three.
    """
    if measure is None or (isinstance(measure, str) and measure in MEASURES):
        return measure
    raise ValidationError(f"{owner}'s measure is one of {list(MEASURES)} or None, got: {measure!r}")


def measure_px(scheme: SizeScheme, measure: str) -> int:
    """The px a ``standard`` or ``narrow`` measure caps a line at, at ``scheme``'s body size."""
    characters = getattr(scheme.type, f"measure_{measure}")
    return math.ceil(characters * scheme.type.body * CH_EM)


def _token(value: float) -> int | float:
    """``value`` as a scheme stores it: an int when whole, so ``14.0`` never renders."""
    rounded = round(value, 1)
    return int(rounded) if rounded == int(rounded) else rounded


def fine_print(scheme: SizeScheme) -> SizeScheme:
    """
    ``scheme`` with a section's copy set in fine print, on paper (#393).

    Fine print is ``micro``, the size an exhibit's disclosure is set in, at the
    legal page's leading. Titles keep their size. The measure keeps its px, so
    a sheet of fine print is not set in a column a third narrower.
    """
    fine = scheme.type.micro
    scale = scheme.type.body / fine
    return scheme.derive(
        type={
            "body": fine,
            "secondary": fine,
            "small": fine,
            "label": min(scheme.type.label, fine),
            "item_title": scheme.type.small,
            "body_line": scheme.component.legal_line,
            "secondary_line": scheme.component.legal_line,
            "measure_standard": _token(scheme.type.measure_standard * scale),
            "measure_narrow": _token(scheme.type.measure_narrow * scale),
        }
    )
