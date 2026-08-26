"""
The email's size vocabulary — one validated object per density.

Sizes were 57 ``font-size`` declarations, 50 ``line-height`` values and
roughly 90 padding/margin literals spread across 20 template files, plus the
680px frame arithmetic written out twice per column in eight container
templates. An implied scale clearly existed; nothing named it, nothing owned
it, and nothing could vary it. This module is that owner.

::

    EmailMetadata.size_theme        ("compact" | "standard" | "spacious")
            |  resolved ONCE in Email.render()
            v
    SizeScheme                      (frozen, validated at construction)
    +-- type       TypeScale        font sizes + the shared line-heights
    +-- space      SpacingScale     section, column, region and rhythm spacing
    +-- component  ComponentScale   sizes that do not follow the global scale
    +-- frame      FrameGeometry    outer width and padding; column widths
                                    are arithmetic over this, not literals
            |  bound onto the engine as one namespace
            v
    templates read {{ size.type.body }}, {{ size.space.gutter }}, ...

**Callers pick a theme, never a px.** ``size_theme`` accepts a
:class:`~svc.builder.enums.SizeTheme` member or its bare string and nothing
else — deliberately narrower than ``theme``, which also accepts a custom
:class:`~svc.builder.theming.Theme`. The asymmetry is the point: a palette is
an email's voice and a house style may legitimately need its own, whereas
density interacts with the 102 KB clipping limit, Outlook's Word engine and
the mobile collapse all at once. A scheme nobody has rendered in a real
client is a compatibility claim nobody has tested. Widening this later is
additive; narrowing it would not be.


The audit — token, value, and the sites each one covers
-------------------------------------------------------

Every number below was read out of the templates before anything moved, and
``STANDARD`` reproduces each one exactly. ``r/`` is ``regions/``, ``c/`` is
``common/containers/``.

**type** — font sizes (px) and the line-heights shared across components::

    title            28    r/header, r/header-minimal (firm name)
    title_mobile     22    base.html .mobile-title override
    section          17    the <h2> in every container; numbered-list ordinal
    subheading       16    r/footer-contact heading
    item_title       15    text/numbered-list item title
    body             14    container cell default, text/text-block prose,
                           text/numbered-list body, text/author-block name
    secondary        13    every component subtitle, masthead campaign name,
                           analysis/data-table cell, card body,
                           r/footer-contact description and CTA label
    small            11    masthead date/issue bar, author job title + email
    label            10    analysis/data-table column header
    micro            9.5   card label and sublabel, chart/table source,
                           image caption, masthead disclaimer bar,
                           r/footer-legal disclaimer and copyright

    title_line       1.2   title, section <h2>, card value, list ordinal
    heading_line     1.3   campaign name, list item title, author name
    body_line        1.72  container cell, text-block prose
    secondary_line   1.4   subtitles, card sublabel, disclaimer bar,
                           author job title

**space** — spacing, in px. ``pad_x`` (32) lives on the frame, since the
frame's horizontal padding is what makes the content 616 wide::

    gutter                    16   between columns (margin-right + ghost table)
    section_title_top         22   c/full-width <h2> cell, top
    section_title_top_split    2   the same cell in a multi-column container
    section_title_bottom      12   both of the above, bottom
    content_top               16   c/full-width content cell, top
    content_bottom            14   c/full-width content cell, bottom
    column_top                 2   a column cell, top
    column_bottom             26   a column cell, bottom
    column_pad_x              20   a column at least frame.narrow_column wide
    column_pad_x_narrow       16   a column narrower than that
    mobile_pad_y / _x       20/18  base.html .mobile-pad override
    block_gap                 16   text-block paragraph, between list items
    subtitle_gap              12   below any component subtitle
    caption_gap                8   above a source, caption, or card body
    masthead_bar_y             7   disclaimer bar
    masthead_logo_top         18   logo row
    masthead_title_top        10   firm-name cell, top
    masthead_title_bottom      6   firm-name cell, bottom
    masthead_campaign_bottom   8   campaign-name cell, bottom
    masthead_meta_top         10   date/issue bar, top
    masthead_meta_bottom      18   date/issue bar, bottom
    masthead_vml_height      180   the v:rect box Outlook draws instead of
                                   the CSS background image
    footer_contact_top         8   contact band, top
    footer_contact_bottom     30   contact band, bottom
    footer_legal_top          20   disclaimer band, top
    footer_legal_bottom        8   disclaimer band, bottom
    footer_copyright_top       6   copyright band, top
    footer_copyright_bottom   24   copyright band, bottom

**component** — what does not follow the global scale::

    kpi_value             21    card value font-size
    card_pad_y / _x     14/16   a vertical card's cell — and, deliberately,
                                base.html's .kpi-cell mobile override, since
                                the collapse *is* the vertical layout
    kpi_pad_y / _x      16/12   a horizontal KPI cell
    card_label_gap         6    below the card label
    card_value_gap         4    below the card value
    card_body_line       1.6    card prose
    table_cell_pad        12    analysis/data-table <th> and <td>
    list_ordinal_width    22    the ordinal column
    list_ordinal_gap      12    between ordinal and item body
    list_title_gap         6    below a list item's title
    list_body_line       1.68   list item prose
    author_name_gap        4    below the author's name
    author_sep_gap         4    around the middot between title and email
    author_rule_gap       14    above the byline, both halves of the rule
    cta_width            150    contact button, VML and CSS alike
    cta_height            38    ditto (VML height == CSS line-height)
    contact_pad_y / _x  22/24   inside the contact card
    contact_heading_gap    6    below the contact heading
    contact_cta_gap       16    above the contact button
    contact_line         1.55   contact description
    legal_line           1.6    footer disclaimer

**frame** — the geometry every column width is derived from::

    width              680   the outer email table
    pad_x               32   its horizontal padding, so inner == 616
    outer_pad_y         28   the wrapper band above and below the email
    mobile_breakpoint  700   the @media max-width that collapses columns
    narrow_column      300   at or above this, a column takes the wider
                             horizontal cell padding; below it, the narrower

Four line-heights say the same thing
------------------------------------

``body_line`` 1.72, ``list_body_line`` 1.68, ``card_body_line`` 1.6 and
``legal_line`` 1.6 / ``contact_line`` 1.55 are five spellings of "roomy"
that differ only because they were typed in five files. The audit records
that rather than fixing it: collapsing them changes rendered output, and
this epic's whole claim is that ``STANDARD`` does not move. They are named
by site so a later PR can collapse them deliberately, with a golden diff
that is the point rather than the problem.

Deliberate literals — sizes that stay hardcoded
-----------------------------------------------

A px value in a template is a bug *unless* it is one of these, each of which
is structural rather than scale-participating:

* ``font-size:1px`` on the preheader — a hider, not type.
* ``font-size:0; line-height:0`` on the accent rule's spacer cell, with
  ``height="1"`` — a 1px rule drawn with a border, not a line of text.
* ``padding:1px 1px 1px 1px`` on a highlighted container — the hairline
  frame itself.
* ``border-width`` (1px, 2px), ``border-radius`` (3px, 4px) and
  ``arcsize="8%"`` — shape, not density.
* ``letter-spacing`` (0.2–0.6px) — optical correction for uppercase micro
  type; it tracks the typeface, not the scale.
* ``text-shadow`` offsets and ``max-width:{{ logo_width }}px`` — the latter
  is the caller's own number.

Validation
----------

Every token is a positive ``int`` or a **non-integral** ``float``. That
second half is not fussiness: a scheme storing ``14.0`` would render
``font-size:14.0px``, which is legal CSS and a byte-identity failure, and
the one genuinely fractional size in the email (``micro`` = 9.5) means the
rule cannot simply be "ints only". Line-heights obey the same rule, so
``1.72`` is fine and ``2.0`` is rejected in favour of ``2``.
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
    for spec in fields(instance):  # type: ignore[arg-type]
        value = getattr(instance, spec.name)
        name = f"{prefix}.{spec.name}"
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
    section_title_top_split: int | float = 2
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
    masthead_logo_top: int | float = 18
    masthead_title_top: int | float = 10
    masthead_title_bottom: int | float = 6
    masthead_campaign_bottom: int | float = 8
    masthead_meta_top: int | float = 10
    masthead_meta_bottom: int | float = 18
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
class FrameGeometry:
    """
    The outer frame, and the arithmetic every column width comes from.

    ``inner`` is a property rather than a field on purpose: a stored inner
    width could disagree with ``width - 2 * pad_x``, and one of the two
    would then be silently wrong. The eight container templates that each
    wrote out this arithmetic twice per column are exactly what that
    disagreement looks like in practice.
    """

    width: int | float = 680
    pad_x: int | float = 32
    outer_pad_y: int | float = 28
    mobile_breakpoint: int | float = 700
    narrow_column: int | float = 300

    def __post_init__(self) -> None:
        _validate_size_fields(self, "frame")
        if self.pad_x * 2 >= self.width:
            raise ValidationError(
                f"'frame.pad_x' ({self.pad_x}) leaves no content width inside "
                f"'frame.width' ({self.width})."
            )
        if self.mobile_breakpoint <= self.width:
            raise ValidationError(
                f"'frame.mobile_breakpoint' ({self.mobile_breakpoint}) must exceed "
                f"'frame.width' ({self.width}), or the email would collapse to its "
                f"mobile layout at its own design width."
            )

    @property
    def inner(self) -> int | float:
        """The content width: ``width`` less the frame padding on both sides."""
        return self.width - 2 * self.pad_x


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


#: The shipped density — every value exactly what the templates hardcoded
#: before this module existed. It is the byte-identity reference the whole
#: sizing epic is measured against.
STANDARD_SIZES = SizeScheme()

#: Every scheme the repo ships, by name. Repo-owned and never mutated at
#: runtime; ``COMPACT`` and ``SPACIOUS`` are populated by #43.
SIZE_SCHEMES: dict[SizeTheme, SizeScheme] = {
    SizeTheme.STANDARD: STANDARD_SIZES,
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
    """One column's computed width and the horizontal padding it earns."""

    width: int
    pad_x: int | float


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

    Each column also carries the padding it earns: a column at least
    ``frame.narrow_column`` wide takes ``space.column_pad_x``, a narrower
    one takes ``space.column_pad_x_narrow``. That threshold is not invented
    here — it is read back out of the templates, where a 300px or 420px
    column had 20px of padding and a 292px or smaller one had 16px.
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

    return [
        ColumnGeometry(
            width=width,
            pad_x=(
                scheme.space.column_pad_x
                if width >= scheme.frame.narrow_column
                else scheme.space.column_pad_x_narrow
            ),
        )
        for width in widths
    ]
