"""
Every size in the email, as one validated object per density.

A ``SizeScheme`` is four frozen scales — ``type`` (font sizes and
line-heights), ``space`` (section, column and region spacing),
``component`` (sizes off the global scale) and ``frame`` (the page and
the padding inside it, from which column widths are computed). ``frame``
is the one layer with **two** owners: its page comes from the medium's
:class:`PageFormat`, its paddings from the density.

``EmailMetadata.size_theme`` names a density; :meth:`Email.render` resolves
it, lays the medium's page over it (:meth:`SizeScheme.with_page`) and binds
the result as ``size``, so templates read ``{{ size.type.body }}``.

`.claude/rules/design-axes.md` carries why, and the token audit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from typing import Any, ClassVar

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

    list_ordinal_width: int | float = 22
    list_ordinal_gap: int | float = 12
    list_title_gap: int | float = 6
    list_body_line: int | float = 1.68

    author_name_gap: int | float = 4
    author_sep_gap: int | float = 4
    author_rule_gap: int | float = 14

    cta_width: int | float = 150
    cta_height: int | float = 38
    contact_pad_y: int | float = 22
    contact_pad_x: int | float = 24
    contact_heading_gap: int | float = 6
    contact_cta_gap: int | float = 16
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

#: Every shipped page by name, the way ``SIZE_SCHEMES`` names every density.
PAGE_FORMATS: dict[str, PageFormat] = {
    "default": DEFAULT_PAGE,
    "a4_portrait": A4_PORTRAIT,
    "a4_landscape": A4_LANDSCAPE,
    "letter_portrait": LETTER_PORTRAIT,
    "letter_landscape": LETTER_LANDSCAPE,
    "slide_16_9": SLIDE_16_9,
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
        the same precedence :meth:`svc.builder.regions.Region.context` gives
        an email's facts and :class:`~svc.builder.engine.BoundEngine` gives a
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
        "author_name_gap": 3,
        "author_rule_gap": 10,
        "cta_width": 140,
        "cta_height": 34,
        "contact_pad_y": 16,
        "contact_pad_x": 18,
        "contact_heading_gap": 4,
        "contact_cta_gap": 12,
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
        "contact_line": 1.7,
        "legal_line": 1.75,
    },
    frame={"pad_x": 40, "outer_pad_y": 36, "narrow_column": 260},
)

#: Every scheme the repo ships, by name. Repo-owned and never mutated at
#: runtime — a caller selects one by name; there is no register-your-own
#: path, for the reason in this module's docstring.
SIZE_SCHEMES: dict[SizeTheme, SizeScheme] = {
    SizeTheme.COMPACT: COMPACT_SIZES,
    SizeTheme.STANDARD: STANDARD_SIZES,
    SizeTheme.SPACIOUS: SPACIOUS_SIZES,
}


def resolve_size_scheme(value: SizeTheme | str) -> SizeScheme:
    """
    Turn whatever a caller supplied into a concrete :class:`SizeScheme`.

    Accepts a :class:`~svc.builder.enums.SizeTheme` member or its bare
    string, and nothing else — see this module's docstring for why a custom
    scheme object is deliberately not accepted here the way a custom
    ``Theme`` is.

    Called from :meth:`svc.builder.email.Email.render` and from
    :meth:`svc.builder.models.EmailMetadata.__post_init__`; the latter is
    what makes a bad theme name fail at construction rather than at render.
    """
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
        f"'size_theme' must be a SizeTheme or its name, got: {type(value).__name__}"
    )


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


def column_layout(weights: Sequence[int | float], scheme: SizeScheme) -> list[ColumnGeometry]:
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

    available = scheme.frame.inner - scheme.space.gutter * (count - 1)
    if available < count:
        raise ValidationError(
            f"{count} columns and {count - 1} gutter(s) of "
            f"{scheme.space.gutter}px leave {available}px inside a "
            f"{scheme.frame.inner}px content width — not enough for one pixel each."
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


def _gutter_pad(width: int, scheme: SizeScheme) -> int | float:
    """The horizontal padding a column of this width earns beside a gutter."""
    return (
        scheme.space.column_pad_x
        if width >= scheme.frame.narrow_column
        else scheme.space.column_pad_x_narrow
    )
