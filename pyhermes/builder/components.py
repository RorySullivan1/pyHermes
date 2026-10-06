"""
Component classes for the email builder.

Each component represents a reusable content block (KPI strip, data table,
chart, text block, etc.). Components are constructed with their data and
render themselves via their Jinja2 template.

Usage:
    engine = TemplateEngine()
    kpi = KpiStrip(items=[KpiItem("S&P 500", "5,234", "#4A7C59", "+1.42%")])
    html = kpi.render(engine)
"""

from __future__ import annotations

import textwrap
import warnings
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from pyhermes.config import get_config

from . import formats
from .apparatus import (
    MARKER,
    UNRESOLVED,
    Citing,
    note_anchor,
    note_ref_anchor,
    slugify,
    split_markers,
    text_markers,
    unmarked,
    validate_anchor,
)
from .engine import (
    Renderer,
    cell_width_of,
    on_ground,
    own_surface,
    placement_of,
    rebind,
    respaced,
    scheme_of,
)
from .enums import CardOrientation, ColumnKind, ImageAlign, RowKind
from .exceptions import ValidationError
from .images import EmailImage, ImageAsset, _displayed_height, coerce_image
from .models import (
    Badge,
    Card,
    Cell,
    Column,
    ColumnGroup,
    Footnote,
    NumberedItem,
    Series,
    TableRow,
    _validate_align,
    _validate_frame,
    _validate_url,
    coerce_column,
    coerce_groups,
    coerce_notes,
    coerce_series,
    tone_of,
    trend_of,
)
from .prose import PROSE_TOKENS, refuse_top_headings
from .sizing import Spacing, coerce_measure, coerce_spacing, measure_px
from .textgen import (
    LINE_WIDTH,
    decimal_pads,
    format_link,
    html_to_text,
    join_blocks,
    link_line,
    table,
    underline,
    wrap,
)

if TYPE_CHECKING:  # pragma: no cover
    from .surfaces import Aside


class CopyAlignment:
    """
    The ``align`` a prose component takes — declared once, mixed into five.

    ``BoxSurface``'s shape, for ``BoxSurface``'s reason: which components
    take an alignment is then **structural** rather than a convention
    somebody has to keep re-checking, and
    ``TestOnlyProseComponentsTakeAnAlignment`` reads the class hierarchy
    rather than a hand-written list.

    **Four components deliberately do not mix this in.**
    :class:`CardGroup` and :class:`DataTable` align *structurally* — a KPI
    cell is centred because it is a KPI cell, and a table column resolves
    from its ``kind`` (#117, #118). A second, coarser knob would be a
    competing answer to a question already answered, and it could only
    either override the column resolution (silently discarding
    ``Column.align``) or be ignored by it (a parameter that does nothing).
    :class:`ImageBlock` is excluded for the plain reason that it already
    has an ``align``, and that one places a *block* rather than aligning
    text — see :class:`~pyhermes.builder.enums.ImageAlign`. :class:`Contents`
    fixes its own: an entry is a title, a leader and a page, left to right.

    Unset means *inherit*: the component emits no declaration and takes
    whatever its container said, by ordinary CSS inheritance. There is no
    ``resolved_align()`` here on purpose — see :class:`Container` for why
    prose differs from a table cell.

    **Known limitation, filed as #130.** A component's declaration lands on
    the element the template emits. Where a caller wraps their content in
    their own paragraph tags — the documented pattern for
    :attr:`TextBlock.content` and :attr:`NumberedItem.body` — a ``p``
    cannot contain a ``p``, so the parser auto-closes the styled element
    and the copy becomes its *sibling*, inheriting from the container's
    cell instead. That predates this field and costs the body copy its
    ``font-family`` too; alignment is merely the first property whose
    fallback differs visibly. Plain text and inline markup are unaffected.
    """

    #: What the caller set, or ``""`` for *inherit from the container*.
    align: str = ""

    def validate_alignment(self, align: str | None) -> str:
        """Validate and normalise this component's alignment."""
        _validate_align(align or "", f"{type(self).__name__.lower()}.align")
        return align or ""

    def alignment_context(self) -> dict[str, Any]:
        """
        The alignment key every prose template reads.

        Always present, empty when unset: the templates gate on it with
        ``{% if align %}``, and under ``StrictUndefined`` an *undefined*
        name raises rather than testing falsey.
        """
        return {"align": self.align}


#: The sides a hosted figure may float to; empty means it does not float (#189, #359).
WRAPS = ("", "left", "right")


def check_wrap(wrap: object, width: int | None, owner: str) -> str:
    """``wrap`` as stored, refusing an unknown side or a float with no width to float at."""
    if wrap not in WRAPS:
        raise ValidationError(f"Unsupported wrap {wrap!r}. Use: {list(WRAPS[1:])}")
    if wrap and not width:
        raise ValidationError(
            f"a wrapped {owner} needs a display width: a float with no width "
            "takes the whole measure and leaves the prose nowhere to wrap"
        )
    return str(wrap)


#: The narrowest share of its cell a fill-width block may take (#357), the column floor's kin.
MIN_SHARE = 0.3


class CellShare:
    """
    A fill-width block set to a share of its cell (#357), mixed into four.

    A share is not a pixel, as a split's weights are not (#264). The block is
    placed by its section's alignment, read from the engine, because these
    blocks align structurally and take no ``align`` of their own. Unset, or
    ``1.0``, the block fills its cell and renders as it always has.
    """

    #: The share of its cell, or ``None`` to fill it.
    width: float | None = None

    def validate_share(self, width: object) -> float | None:
        """``width`` as stored; ``1.0`` is the same as unset."""
        if width is None:
            return None
        if isinstance(width, bool) or not isinstance(width, (int, float)):
            raise ValidationError(
                f"{type(self).__name__}'s width is a share of its cell, got: {width!r}"
            )
        if not MIN_SHARE <= width <= 1:
            raise ValidationError(
                f"{type(self).__name__}'s width is a share of its cell from {MIN_SHARE} "
                f"to 1.0, got: {width!r}"
            )
        return None if width == 1 else float(width)

    def _fill(self, engine: Renderer) -> str:
        """The block at its cell's full width."""
        return Component.render(self, engine)  # type: ignore[arg-type]

    def render(self, engine: Renderer) -> str:
        """The block, inside a layout table the share of its cell wide when it has one."""
        if self.width is None:
            return self._fill(engine)
        inner = rebind(engine, cell_width=int(cell_width_of(engine) * self.width))
        return engine.render(
            "common/share.html",
            {
                "content": self._fill(inner),
                "share": f"{self.width * 100:g}",
                "place": placement_of(engine),
            },
        )


class Exhibit:
    """
    What makes a chart, table or image *"Exhibit 3"* — mixed into all three.

    ``label`` opts an exhibit into numbering; unset, it renders exactly as it
    did before #181. Separate labels count separately, so *"Table 2"* and
    *"Figure 1"* coexist in one document.

    **The number is assigned, never chosen.** :class:`~pyhermes.builder.document.
    Document` walks its tree in reading order and sets :attr:`number` before
    each projection, so the markup and the text part are handed the same
    number. An exhibit never numbers itself: shared between two documents it
    would otherwise carry one document's number into the other.

    ``anchor`` overrides the derived ``id`` (``exhibit-3``); it is the only
    anchor an unlabelled exhibit can have.
    """

    label: str = ""
    anchor: str = ""

    #: Set by the document's walk; ``None`` when unlabelled or rendered alone.
    number: int | None = None

    #: The letter of the appendix this exhibit sits in, set by the walk (#309).
    appendix: str = ""

    def validate_exhibit(self, label: str, anchor: str) -> None:
        """Validate and store the two caller-facing fields."""
        name = type(self).__name__.lower()
        if label and not label.strip():
            raise ValidationError(f"'{name}.label' must not be blank, got: {label!r}")
        validate_anchor(anchor, f"{name}.anchor")
        self.label = label
        self.anchor = anchor
        self.number = None
        self.appendix = ""

    def resolved_anchor(self) -> str:
        """The ``id`` this exhibit carries, or ``""`` when it has none."""
        if self.anchor:
            return self.anchor
        if self.label and self.number:
            return f"{slugify(self.label, 'exhibit')}-{self._ordinal().lower().replace('.', '-')}"
        return ""

    def _ordinal(self) -> str:
        """``3``, or ``A.1`` in an appendix: the number as both projections print it."""
        return f"{self.appendix}.{self.number}" if self.appendix else str(self.number)

    def numbered(self, heading: str) -> str:
        """``heading`` behind this exhibit's number — the one string both projections print."""
        if not (self.label and self.number):
            return heading
        prefix = f"{self.label} {self._ordinal()}"
        return f"{prefix}{get_config().exhibit_separator}{heading}" if heading else prefix

    def listed(self) -> str:
        """This exhibit's entry in a list of exhibits: its numbered caption, markers removed."""
        return self.numbered(unmarked(getattr(self, "caption", "")))


class Component:
    """
    Abstract base for all email components.

    Subclasses must set ``template_path`` and implement ``context()``.
    A component that renders an image also overrides ``images()``.

    Every public component takes ``spacing=``: a
    :class:`~pyhermes.builder.sizing.Spacing`, or a mapping, moving only the
    ``SPACING_TOKENS`` its own template reads.
    """

    template_path: str = ""  # e.g. "analysis/kpi-strip.html"

    #: The spacing tokens this component's template reads (#215).
    SPACING_TOKENS: ClassVar[tuple[str, ...]] = ()

    #: This component's spacing override, or ``None`` for the bound scheme's.
    spacing: Spacing | None = None

    #: Whether this block paints its own surface, and so keeps the theme's type
    #: on a section's own ground (#266) rather than the ground's.
    OWN_SURFACE: ClassVar[bool] = False

    #: How this component's document spells a citation, handed down by the walk (#310).
    citing: Citing = UNRESOLVED

    def _coerce_spacing(
        self, spacing: Spacing | Mapping[str, int | float] | None
    ) -> Spacing | None:
        """``spacing`` checked against this class's ``SPACING_TOKENS``."""
        return coerce_spacing(spacing, self.SPACING_TOKENS, type(self).__name__)

    def context(self) -> dict[str, Any]:
        """Return the template context dict for this component."""
        raise NotImplementedError

    def render_context(self, engine: Renderer) -> dict[str, Any]:
        """:meth:`context`, and what this block renders of the blocks it holds; a leaf adds none."""
        return self.context()

    def images(self) -> list[EmailImage]:
        """
        Return every :class:`EmailImage` this component renders.

        Empty for the text and data components, which carry none. Override
        it in any component that emits an ``<img>``, so the email can
        collect the manifest of parts a delivery layer must attach.
        """
        return []

    def children(self) -> list[Component]:
        """The blocks this one holds, in reading order: none for a leaf (#261)."""
        return []

    def raw_html(self) -> list[str]:
        """
        The caller markup this component emits raw, for the document's link check.

        Empty by default: only the blessed raw-HTML fields carry markup, and a
        component holding one returns it so a ``#fragment`` in it is checked.
        """
        return []

    def marked_copy(self) -> list[str]:
        """Every field that may carry a marker, in reading order: where citations come from."""
        return []

    def anchors(self) -> list[tuple[str, str]]:
        """``(anchor, owner)`` for each destination this block defines beyond an exhibit's."""
        return []

    def footnotes(self) -> list[Footnote]:
        """
        Every note this component's copy calls, in reading order (#182).

        Empty by default, like :meth:`images`. The document walks it to
        number notes across the whole tree, so a component carrying notes
        overrides it or they are never numbered.
        """
        return list(getattr(self, "notes", []))

    def assets(self) -> list[ImageAsset]:
        """
        Return the attachment manifest entries for this component.

        Derived from :meth:`images` — only ``CID`` images produce one, so a
        component whose images are all hosted returns an empty list.
        """
        return [image.asset for image in self.images() if image.asset is not None]

    def text(self) -> str:
        """
        Return this component's plain-text projection (#109).

        The mirror of :meth:`images`, with the **opposite default**: an
        absent image list is empty, an absent projection is an *error*. A
        component with no visual content can exist — a spacer would — but a
        *content* component invisible to text-mode readers is exactly the
        accessibility failure epic #53 exists to fix, so a subclass that
        never implements this fails the first email that projects it rather
        than vanishing from the text part silently.

        Every projection is built from this component's own data. Nothing
        here parses the render: the text part is a second projection of the
        section tree, not a degradation of the first one.
        """
        raise NotImplementedError(
            f"{type(self).__name__} has no text() projection. Every component needs "
            "one, or it disappears from the plain-text part of every email that "
            "uses it. See pyhermes/builder/textgen.py for the formatting policy."
        )

    def _with_subtitle(self, *blocks: str) -> str:
        """
        This component's blocks, behind its own subtitle.

        Nine of the ten public components carry a ``subtitle`` — the italic
        standfirst above their content — and it belongs to the *component*,
        not to the container: ``FullWidth`` and the splits take a ``title``
        and nothing else. ``ContactBlock`` is the one that has no subtitle
        field, so this reads the attribute defensively rather than assuming.
        """
        subtitle = getattr(self, "subtitle", None)
        return join_blocks(wrap(subtitle) if subtitle else "", *blocks)

    def render(self, engine: Renderer) -> str:
        """
        Render the component to an HTML string.

        Args:
            engine: Anything with a ``render`` method — a TemplateEngine,
                    or the bound view Email.render() hands down.

        Returns:
            Rendered HTML fragment.
        """
        if not self.template_path:
            raise ValidationError(f"{self.__class__.__name__} has no template_path set.")
        grounded = self.OWN_SURFACE and on_ground(engine)
        engine = own_surface(engine) if self.OWN_SURFACE else engine
        engine = respaced(engine, self.spacing, type(self).__name__)
        html = engine.render(self.template_path, self.render_context(engine))
        return engine.render("common/surface.html", {"content": html}) if grounded else html


def descendants(components: Sequence[Component]) -> list[Component]:
    """Every component, each followed by those it holds, depth first in reading order."""
    found: list[Component] = []
    for component in components:
        found.append(component)
        found.extend(descendants(component.children()))
    return found


def leaves(components: Sequence[Component]) -> list[Component]:
    """
    The components that hold none, in reading order: what the document numbers and walks.

    An exhibit is one stop even when it holds blocks, a grid its panels or a
    chart its key (#335): the walk numbers the exhibit, never what it holds.
    """
    found: list[Component] = []
    for component in components:
        held = component.children()
        if held and not isinstance(component, Exhibit):
            found.extend(leaves(held))
        else:
            found.append(component)
    return found


# ──────────────────────────────────────────────────────────────────────
# Analysis components  (templates/analysis/)
# ──────────────────────────────────────────────────────────────────────


class CardGroup(CellShare, Component):
    """
    A set of callout cards, laid out horizontally or vertically.

    ``horizontal`` is the classic KPI strip — 2–4 cells across, sized to
    share the width.  ``vertical`` stacks the same cards one per row, which
    is also what the horizontal strip collapses to on a phone.

    Args:
        cards:       List of Card (or KpiItem) instances.
        orientation: ``"horizontal"`` (default) or ``"vertical"``.
        subtitle:    Optional sub-heading rendered above the group.
        width:       A share of the cell, 0.3 to 1.0, placed by the section's align (#357).

    Raises:
        ValidationError: On an unsupported orientation, a card count outside
            the orientation's limits, or an invalid card.
    """

    OWN_SURFACE = True

    template_path = "analysis/card-group.html"

    SPACING_TOKENS = (
        "card_pad_y",
        "card_pad_x",
        "kpi_pad_y",
        "kpi_pad_x",
        "card_label_gap",
        "card_value_gap",
        "caption_gap",
        "subtitle_gap",
        *PROSE_TOKENS,
    )

    # Members equal and hash as their string value, so membership tests and
    # equality checks below accept both a CardOrientation and a bare string.
    ORIENTATIONS = tuple(CardOrientation)

    def __init__(
        self,
        cards: list[Card],
        orientation: str | CardOrientation = CardOrientation.HORIZONTAL,
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        width: float | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.width = self.validate_share(width)
        if orientation not in self.ORIENTATIONS:
            raise ValidationError(
                f"Unsupported orientation '{orientation}'. "
                f"Use: {[o.value for o in self.ORIENTATIONS]}"
            )
        # Horizontal cells share the row width, so the count is bounded;
        # a vertical stack has no such constraint.
        if orientation == CardOrientation.HORIZONTAL and not 2 <= len(cards) <= 4:
            raise ValidationError("A horizontal CardGroup requires 2–4 items.")
        if orientation == CardOrientation.VERTICAL and not cards:
            raise ValidationError("A vertical CardGroup requires at least one item.")
        for card in cards:
            card.validate()
        self.cards = cards
        self.orientation = orientation
        self.subtitle = subtitle

    def raw_html(self) -> list[str]:
        return [card.body for card in self.cards if card.body]

    def text(self) -> str:
        """
        One card per line: ``label: value (sublabel)``, prose beneath.

        ``orientation`` projects to nothing. A horizontal strip and a vertical
        stack are one card per line either way — the mobile collapse already
        established that as the canonical linear order, so plain text inherits
        an ordering the design system had already decided rather than picking
        a second one.
        """
        lines = []
        for card in self.cards:
            label = card.label
            if isinstance(card.badge, Badge):
                label = f"{label} {card.badge.text()}"
            head = f"{label}: {card.value}" if card.value else label
            if card.sublabel:
                head = f"{head} ({card.sublabel})"
            lines.append(head)
            if isinstance(card.trend, Series):
                lines.append(card.trend.summary())
            if card.body:
                lines.append(html_to_text(card.body))
        return self._with_subtitle(wrap("\n".join(lines)))

    def context(self) -> dict[str, Any]:
        return {
            "cards": [
                {
                    "label": c.label,
                    "value": c.value,
                    "color": c.color,
                    "tone": c.tone,
                    "sublabel": c.sublabel,
                    "body": c.body,
                    "arrow": c.arrow,
                    "trend": c.trend.drawn(c.tone) if isinstance(c.trend, Series) else None,
                    "badge": c.badge.drawn() if isinstance(c.badge, Badge) else None,
                }
                for c in self.cards
            ],
            "orientation": self.orientation,
            "subtitle": self.subtitle,
        }


class KpiStrip(CardGroup):
    """
    Deprecated alias for a horizontal :class:`CardGroup`.

    .. deprecated::
        Use ``CardGroup(cards, orientation="horizontal")``.
    """

    def __init__(self, items: list[Card], subtitle: str | None = None):
        warnings.warn(
            "KpiStrip is deprecated; use CardGroup(cards, orientation='horizontal').",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(items, orientation="horizontal", subtitle=subtitle)

    @property
    def items(self) -> list[Card]:
        """The group's cards, under the old attribute name."""
        return self.cards


class DataTable(CellShare, Exhibit, Component):
    """
    Financial data table with headers, alternating row colours, and
    colour-coded numeric cells.

    Args:
        headers:  Column headers. Either bare strings or :class:`Column`
                  instances, mixed freely — a string is coerced to a
                  ``Column`` whose presentation resolves from its position,
                  which is what the old ``loop.first`` convention meant.
        rows:     List of TableRow instances.
        source:   Attribution string (e.g. "Source: Bloomberg").
        as_of:    Date string (e.g. "March 28, 2026").
        subtitle: Optional sub-heading rendered above the table.
        caption:  Optional table caption (#120). Renders as a ``caption``
                  element — the table's own accessible **name**, which is
                  what a screen reader announces when it reaches the table.
        disclosure: Optional compliance copy beneath the attribution; plain
                  text, escaped. `disclosure.md` says when to use it.
        label, anchor: Numbering and its ``id``; see :class:`Exhibit`.
        notes:    Footnotes called by ``[^n]`` in the caption, the source, a
                  column's header or a cell's text (#224).
        groups:   Optional :class:`ColumnGroup` heads spanning the columns,
                  left to right (#223); their spans sum to the column count.
        frame:    ``"solid"`` or ``"dashed"`` draws a frame in the theme's rule
                  round the table, inset by a cell's padding (#390); unset for none.

    **``caption`` and ``subtitle`` are separate on purpose**, even when a
    caller would write the same words in both. ``subtitle`` is presentation
    copy that happens to sit above the table; ``caption`` is the table's
    name, attached to it in the markup. Rendering the subtitle *as* the
    caption would have been fewer fields and would have moved every existing
    golden — changing what shipped emails announce, to say a standfirst where
    a name belongs. A separate field is byte-identical and reversible.

    An email with several tables is where this earns its keep: without a
    caption a reader hears "table" each time, with nothing to tell them
    apart.

    **Alignment resolves in Python, once, and both projections read it**
    (#117). The template no longer decides alignment or face from a column's
    position, and :func:`~pyhermes.builder.textgen.table` is handed the resolved
    alignments rather than re-deriving them — which is what stops the HTML
    and the plain-text part disagreeing about the same table.
    """

    OWN_SURFACE = True

    template_path = "analysis/data-table.html"

    SPACING_TOKENS = (
        "table_cell_pad",
        "caption_gap",
        "subtitle_gap",
    )

    def __init__(
        self,
        headers: list[str | Column],
        rows: list[TableRow],
        source: str = "",
        as_of: str = "",
        subtitle: str | None = None,
        caption: str = "",
        disclosure: str = "",
        label: str = "",
        anchor: str = "",
        notes: Sequence[Footnote | str] | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        groups: Sequence[ColumnGroup] | None = None,
        *,
        width: float | None = None,
        frame: str | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.width = self.validate_share(width)
        self.validate_exhibit(label, anchor)
        if frame is not None:
            _validate_frame(frame, "data_table.frame")
        self.frame = frame
        if not headers:
            raise ValidationError("DataTable requires at least one header.")
        if not rows:
            raise ValidationError("DataTable requires at least one row.")
        columns = [coerce_column(h, f"data_table.headers[{i}]") for i, h in enumerate(headers)]
        for i, row in enumerate(rows):
            row.validate()
            # A subhead labels the rows beneath it, so one cell is the honest
            # way to write one — it is padded to the table's width here rather
            # than making the caller spell out the empties. Anything between
            # one and the full width is still a mistake worth catching.
            if row.kind == RowKind.SUBHEAD and len(row.cells) == 1 < len(columns):
                row.cells = row.cells + [Cell() for _ in range(len(columns) - 1)]
            if len(row.cells) != len(columns):
                raise ValidationError(
                    f"DataTable row {i} has {len(row.cells)} cells but there are "
                    f"{len(columns)} headers; the table would render misaligned."
                )
        for index, column in enumerate(columns):
            if column.align_decimal and column.resolved_kind(index) is not ColumnKind.NUMERIC:
                raise ValidationError(
                    f"'column.align_decimal' is set on the {column.resolved_kind(index)} "
                    f"column {column.header!r}; only figures have a decimal point to align."
                )
        for i, row in enumerate(rows):
            row.cells = [
                _formatted(cell, column, index, i)
                for index, (cell, column) in enumerate(zip(row.cells, columns, strict=True))
            ]
        _check_figures(columns, rows)
        _check_statuses(columns, rows)
        # Reading order, so a marker anywhere in the table is checked once (#224).
        copy = [caption, source, *(c.header for c in columns)]
        self.notes = coerce_notes(
            notes, copy + [cell.text for row in rows for cell in row.cells], "DataTable"
        )
        self.columns = columns
        self.groups = coerce_groups(groups, len(columns))
        self.rows = rows
        self.source = source
        self.as_of = as_of
        self.subtitle = subtitle
        self.caption = caption
        self.disclosure = disclosure

    def marked_copy(self) -> list[str]:
        return [
            self.caption,
            *self.headers,
            *(cell.text for row in self.rows for cell in row.cells),
            self.source,
        ]

    @property
    def headers(self) -> list[str]:
        """The column headings, as the plain strings the caller may have passed."""
        return [column.header for column in self.columns]

    def resolved_columns(self) -> list[Column]:
        """
        Every column with its alignment and kind filled in.

        **The single source both projections read.** Computing this twice —
        once for the markup and once for the text — is exactly how the two
        parts would come to disagree about which column is the label, which
        is the failure this method exists to make impossible.
        """
        return [column.resolved(index) for index, column in enumerate(self.columns)]

    def text(self) -> str:
        """Aligned columns, then the attribution lines."""
        return self._with_subtitle(
            wrap(text_markers(self.numbered(self.caption), self.notes, self.citing)),
            table(
                [text_markers(header, self.notes, self.citing) for header in self.headers],
                [
                    [
                        text + " " * pad + (f" {cell.badge.text()}" if cell.badge else "")
                        for text, pad, cell in zip(texts, pads, row.cells, strict=True)
                    ]
                    for texts, pads, row in zip(
                        self._spelled(), self._pads(), self.rows, strict=True
                    )
                ],
                aligns=[column.align for column in self.resolved_columns()],
                kinds=[row.kind for row in self.rows],
                groups=[(group.label, group.span) for group in self.groups],
                units=self._units(),
            ),
            wrap(
                "\n".join(
                    filter(None, (text_markers(self.source, self.notes, self.citing), self.as_of))
                )
            ),
            wrap(self.disclosure),
        )

    def _spelled(self) -> list[list[str]]:
        """Every cell's text with its markers spelled as the document's numbers."""
        return [
            [text_markers(cell.text, self.notes, self.citing) for cell in row.cells]
            for row in self.rows
        ]

    def _pads(self, hang_markers: bool = False) -> list[list[int]]:
        """
        Per cell, the spaces that line a column's points up (#226).

        One count for both projections, from the spelled text. On a page a
        marker is a superscript that hangs past the point, so the markup asks
        with ``hang_markers`` and a marked cell is measured without it.
        """
        spelled = self._spelled()
        if hang_markers:
            spelled = [[MARKER.sub("", cell.text) for cell in row.cells] for row in self.rows]
        pads = [[0] * len(self.columns) for _ in self.rows]
        figures = [i for i, row in enumerate(self.rows) if row.kind != RowKind.SUBHEAD]
        for c, column in enumerate(self.columns):
            if column.align_decimal:
                column_pads = decimal_pads([spelled[r][c] for r in figures])
                for r, pad in zip(figures, column_pads, strict=True):
                    pads[r][c] = pad
        return pads

    def _bar_ends(self) -> list[float]:
        """Per column, the figure a full bar stands for: the scale's top, or the largest."""
        ends: list[float] = []
        for index, column in enumerate(self.columns):
            figures = [r.cells[index].value for r in self.rows if r.kind == RowKind.DATA]
            if not column.bar:
                ends.append(0)
            else:
                ends.append(column.scale.high if column.scale else max(figures, default=0))
        return ends

    @staticmethod
    def _status(row: TableRow, cell: Cell, column: Column) -> str:
        """The tone of a status cell's dot (#326); empty off a status column or a subhead."""
        if column.kind != ColumnKind.STATUS or row.kind == RowKind.SUBHEAD or not cell.text:
            return ""
        return (column.statuses or {})[cell.text]

    def _figure(self, row: TableRow, cell: Cell, column: Column, end: float) -> dict[str, Any]:
        """
        A data cell's heat and bar (#227); neither on a total or a subhead.

        Its arrow (#319) reads the raw figure on any row that carries one but a
        subhead, since a total's change has a direction too.
        """
        heat = bar = None
        if row.kind == RowKind.DATA and column.scale is not None:
            position, toward = column.scale.position(cell.value)
            heat = {"position": position, "toward": str(toward)}
        if row.kind == RowKind.DATA and column.bar:
            fraction = min(1, max(0, cell.value / end)) if end > 0 else 0
            bar = round(fraction * 100)
        arrow = ""
        if column.arrow and row.kind != RowKind.SUBHEAD and cell.value is not None:
            arrow = str(trend_of(cell.value, column.format))
        spark = None
        if isinstance(cell.value, Series):
            tone = cell.tone or (column.tone if column.tone != "auto" else "")
            if column.tone == "auto":
                tone = str(tone_of(cell.value.values[-1] - cell.value.values[0]))
            spark = cell.value.drawn(tone)
        return {
            "heat": heat,
            "bar": bar,
            "bar_color": "",
            "reverse": False,
            "arrow": arrow,
            "spark": spark,
        }

    def _units(self) -> list[str]:
        """One unit per column, or none at all when no column names one."""
        units = [column.unit for column in self.columns]
        return units if any(units) else []

    def _striping(self) -> dict[int, bool]:
        """Which rows take the alternating tint, counting data rows only."""
        alt: dict[int, bool] = {}
        seen = 0
        for row in self.rows:
            if row.kind == RowKind.DATA:
                alt[id(row)] = seen % 2 == 1
                seen += 1
            else:
                alt[id(row)] = False
        return alt

    def _widths(self) -> list[str]:
        """
        Each column's share as a percentage attribute, or all empty when no weight is set.

        The shares are rounded to whole percents by largest remainder, so they sum
        to exactly 100.
        """
        if all(column.width is None for column in self.columns):
            return [""] * len(self.columns)
        weights = [1 if column.width is None else column.width for column in self.columns]
        exact = [100 * weight / sum(weights) for weight in weights]
        shares = [int(share) for share in exact]
        by_remainder = sorted(range(len(exact)), key=lambda i: shares[i] - exact[i])
        for index in by_remainder[: 100 - sum(shares)]:
            shares[index] += 1
        return [f"{share}%" for share in shares]

    def context(self) -> dict[str, Any]:
        columns = self.resolved_columns()
        alt_by_row = self._striping()
        pads = self._pads(hang_markers=True)
        ends = self._bar_ends()
        return {
            "columns": [
                {
                    "header": c.header,
                    "parts": split_markers(c.header, self.notes, self.citing),
                    "align": c.align,
                    "kind": c.kind,
                    "width": width,
                    "rule_after": c.rule_after,
                }
                for c, width in zip(columns, self._widths(), strict=True)
            ],
            "groups": [{"label": g.label, "span": g.span} for g in self.groups],
            "frame": self.frame or "",
            "units": self._units(),
            "rows": [
                {
                    "kind": r.kind,
                    "cells": [
                        {
                            "text": cell.text,
                            "parts": split_markers(cell.text, self.notes, self.citing),
                            "pad": pad,
                            **self._figure(r, cell, self.columns[index], ends[index]),
                            # The chain completes here: cell → column → position.
                            "align": cell.resolved_align(column.align),
                            "color": cell.color,
                            "tone": cell.tone,
                            "background": cell.background,
                            "is_text": column.kind in (ColumnKind.TEXT, ColumnKind.STATUS),
                            "status": self._status(r, cell, column),
                            "badge": cell.badge.drawn() if isinstance(cell.badge, Badge) else None,
                            # A row header, not a data cell: the first column
                            # labels the figures beside it, so it is the `th`
                            # a reader navigates by. Keyed on the resolved
                            # kind rather than the position, so a table whose
                            # first column is genuinely numeric — a rank —
                            # does not claim to head its row.
                            "row_header": index == 0 and column.kind == ColumnKind.TEXT,
                        }
                        for index, (cell, column, pad) in enumerate(
                            zip(r.cells, columns, row_pads, strict=True)
                        )
                    ],
                    # Striping counts *data* rows: a subhead in the middle of a
                    # table must not invert the tint of everything beneath it.
                    "alt": alt_by_row[id(r)],
                }
                for r, row_pads in zip(self.rows, pads, strict=True)
            ],
            "source": self.source,
            "source_parts": split_markers(self.source, self.notes, self.citing),
            "as_of": self.as_of,
            "subtitle": self.subtitle,
            "caption": self.numbered(self.caption),
            "caption_parts": split_markers(self.numbered(self.caption), self.notes, self.citing),
            "anchor": self.resolved_anchor(),
            "disclosure": self.disclosure,
        }


def _check_statuses(columns: list[Column], rows: list[TableRow]) -> None:
    """Every word in a status column is one its statuses name (#326); a subhead holds none."""
    for index, column in enumerate(columns):
        if column.kind != ColumnKind.STATUS:
            continue
        for row in rows:
            word = row.cells[index].text
            if row.kind != RowKind.SUBHEAD and word and word not in (column.statuses or {}):
                raise ValidationError(
                    f"status column {column.header!r} has no status {word!r}; "
                    f"it names {list(column.statuses or {})}"
                )


def _check_figures(columns: list[Column], rows: list[TableRow]) -> None:
    """A scale or a bar reads each data row's raw figure, so each must have one."""
    for index, column in enumerate(columns):
        if column.scale is None and not column.bar and not column.arrow:
            continue
        if column.resolved_kind(index) is not ColumnKind.NUMERIC:
            raise ValidationError(
                f"the {column.resolved_kind(index)} column {column.header!r} carries a scale, "
                "a bar or an arrow; only figures can be tinted or drawn."
            )
        for i, row in enumerate(rows):
            if row.kind == RowKind.DATA and row.cells[index].value is None:
                raise ValidationError(
                    f"DataTable row {i}, column {column.header!r}: the cell "
                    f"{row.cells[index].text!r} has no raw figure for its scale, bar "
                    "or arrow to read."
                )


def _formatted(cell: Cell, column: Column, index: int, row: int) -> Cell:
    """
    ``cell``, written through its column's format when it holds only a raw figure.

    The single place a figure becomes text (#225), so the markup and ``text()``
    read one string. A string, or a figure already written, is left as it is.
    """
    sparkline = column.resolved_kind(index) is ColumnKind.SPARKLINE
    if isinstance(cell.value, tuple) != sparkline and cell.value is not None:
        raise ValidationError(
            f"DataTable row {row}, column {column.header!r}: "
            + (
                f"the sparkline column holds {cell.value!r}; give it a list of figures"
                if sparkline
                else f"a list of figures {cell.value!r} belongs in a kind='sparkline' column"
            )
        )
    if sparkline and cell.value is not None:
        series = coerce_series(
            cell.value, column.format, f"DataTable row {row}, column {column.header!r}"
        )
        drawn = Cell(text=series.summary(), align=cell.align, tone=cell.tone, value=series)
        drawn.validate()
        return drawn
    if cell.value is None or cell.text:
        return cell
    if column.format is None and column.resolved_kind(index) is ColumnKind.TEXT:
        raise ValidationError(
            f"DataTable row {row} holds the raw figure {cell.value!r} in the text column "
            f"{column.header!r}; give the column a format or write the cell as text."
        )
    formatted = Cell.from_number(
        cell.value,
        column.format or formats.number,
        tone=cell.tone or column.tone,
        align=cell.align,
        background=cell.background,
    )
    formatted.color = cell.color
    return formatted


class ChartBlock(Exhibit, CopyAlignment, Component):
    """
    A chart image, bordered, with source attribution.

    The charting specialisation of :class:`ImageBlock` — same image
    handling, plus the hairline border and the attribution line a data
    exhibit needs.

    Args:
        image_url: An :class:`~pyhermes.builder.images.EmailImage`, or a plain
            URL string, which is wrapped as a hosted image using
            ``alt_text``.  Pass an ``EmailImage`` to embed the chart by
            ``cid:`` so it renders in Outlook without a download prompt.
        alt_text:  Accessibility alt text.  Ignored when ``image_url`` is
            an ``EmailImage``, which carries its own.
        source:    Attribution string.
        subtitle:  Optional sub-heading rendered above the chart.
        width:     Display width in px, unless ``image_url`` is an ``EmailImage``,
            which carries its own. ``None`` renders full width, as before.
        disclosure: Optional compliance copy qualifying this exhibit —
                  justified fine print beneath the attribution. Plain
                  text, escaped on the way out; see `disclosure.md` for when
                  it belongs here rather than on ``Footer.disclaimer``.
        caption:  Optional heading line above the chart, where its number goes.
        label, anchor: Numbering and its ``id``; see :class:`Exhibit`.
        notes:    Footnotes called by ``[^n]`` in ``caption`` or ``source``.
        wrap:     As on :class:`ImageBlock`, when a :class:`TextBlock` hosts it (#359).
        legend:   The chart's key in markup, beneath it (#337).
    """

    template_path = "analysis/chart-block.html"

    SPACING_TOKENS = (
        "caption_gap",
        "subtitle_gap",
    )

    def __init__(
        self,
        image_url: str | EmailImage,
        alt_text: str = "Chart",
        source: str = "",
        subtitle: str | None = None,
        width: int | None = None,
        align: str | None = None,
        disclosure: str = "",
        caption: str = "",
        label: str = "",
        anchor: str = "",
        notes: Sequence[Footnote | str] | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        wrap: str = "",
        legend: Component | None = None,
    ):
        from .exhibits import Legend  # the legend module builds on this one

        self.spacing = self._coerce_spacing(spacing)
        if not image_url:
            raise ValidationError("ChartBlock requires an image_url.")
        if legend is not None and not isinstance(legend, Legend):
            raise ValidationError(f"ChartBlock's legend is a Legend, got {type(legend).__name__}.")
        self.legend = legend
        self.validate_exhibit(label, anchor)
        self.notes = coerce_notes(notes, [caption, source], "ChartBlock")
        self.align = self.validate_alignment(align)
        self.image = coerce_image(
            image_url, alt=alt_text, field_name="chart.image_url", width=width
        )
        self.source = source
        self.subtitle = subtitle
        self.disclosure = disclosure
        self.caption = caption
        self.wrap = check_wrap(wrap, self.image.width, "ChartBlock")

    @property
    def image_url(self) -> str:
        """The resolved ``src`` for the chart image."""
        return self.image.src

    @property
    def alt_text(self) -> str:
        """The chart's alt text."""
        return self.image.alt

    def images(self) -> list[EmailImage]:
        return [self.image]

    def children(self) -> list[Component]:
        return [self.legend] if self.legend else []

    def marked_copy(self) -> list[str]:
        return [self.caption, self.source]

    def text(self) -> str:
        """
        The alt text in brackets, its key, then the attribution.

        ``alt`` is required at construction, so this projection is never
        empty — which is the whole reason that rule exists.
        """
        return self._with_subtitle(
            wrap(text_markers(self.numbered(self.caption), self.notes, self.citing)),
            wrap(f"[{self.image.alt}]"),
            self.legend.text() if self.legend else "",
            wrap(text_markers(self.source, self.notes, self.citing)),
            wrap(self.disclosure),
        )

    def render_context(self, engine: Renderer) -> dict[str, Any]:
        legend = self.legend.render(engine) if self.legend else ""
        return {**self.context(), "legend": legend}

    def context(self) -> dict[str, Any]:
        return {
            "chart_image_url": self.image.src,
            "chart_alt_text": self.image.alt,
            "chart_image_width": self.image.width or "",
            "chart_source": self.source,
            "chart_source_parts": split_markers(self.source, self.notes, self.citing),
            "caption": self.numbered(self.caption),
            "caption_parts": split_markers(self.numbered(self.caption), self.notes, self.citing),
            "anchor": self.resolved_anchor(),
            # Bare, not ``chart_``-prefixed: all three exhibits include one
            # shared partial, so they must agree on the key it reads.
            "disclosure": self.disclosure,
            "subtitle": self.subtitle,
            "legend": "",
            **self.alignment_context(),
        }


class ImageBlock(Exhibit, Component):
    """
    A single image — optionally linked, captioned and aligned. Charts keep
    :class:`ChartBlock`, for the border and attribution line.

    Args:
        image:    An :class:`~pyhermes.builder.images.EmailImage`, or a plain URL
            string wrapped as a hosted image using ``alt_text``.
        alt_text: Alt text, used only when ``image`` is a bare URL string.
        decorative: The image carries no information; emits ``alt=""`` and
            projects to nothing in the text part. Also bare-string only.
        caption:  Optional caption rendered beneath the image.
        disclosure: Optional compliance copy qualifying this exhibit —
                  justified fine print beneath the attribution. Plain
                  text, escaped on the way out; see `disclosure.md` for when
                  it belongs here rather than on ``Footer.disclaimer``.
        link_url: Optional URL the image links to.
        align:    ``"center"`` (default), ``"left"`` or ``"right"``.
        subtitle: Optional sub-heading rendered above the image.
        width:    Display width in px, used only when ``image`` is a bare
            URL string.  ``None`` renders full width.
        label, anchor, notes: As on :class:`ChartBlock`; markers go in ``caption``.
        wrap:     ``"left"`` or ``"right"``: on paper, float to that side of the
            :class:`TextBlock` hosting it as ``figure`` (#189). Needs a width.

    Raises:
        ValidationError: On a missing image, a bad alignment or link scheme, or
            a ``wrap`` with no width to float at.
    """

    template_path = "media/image-block.html"

    SPACING_TOKENS = (
        "caption_gap",
        "subtitle_gap",
    )

    WRAPS = WRAPS

    ALIGNMENTS = tuple(ImageAlign)

    def __init__(
        self,
        image: str | EmailImage,
        alt_text: str = "",
        caption: str = "",
        link_url: str = "",
        align: str | ImageAlign = ImageAlign.CENTER,
        subtitle: str | None = None,
        width: int | None = None,
        decorative: bool = False,
        disclosure: str = "",
        label: str = "",
        anchor: str = "",
        notes: Sequence[Footnote | str] | None = None,
        wrap: str = "",
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not image:
            raise ValidationError("ImageBlock requires an image.")
        check_wrap(wrap, 1, "ImageBlock")
        self.validate_exhibit(label, anchor)
        self.notes = coerce_notes(notes, [caption], "ImageBlock")
        if align not in self.ALIGNMENTS:
            raise ValidationError(
                f"Unsupported alignment '{align}'. Use: {[a.value for a in self.ALIGNMENTS]}"
            )
        _validate_url(link_url, "image.link_url")

        self.image = coerce_image(
            image, alt=alt_text, field_name="image", width=width, decorative=decorative
        )
        self.caption = caption
        self.link_url = link_url
        self.align = align
        self.subtitle = subtitle
        self.disclosure = disclosure
        self.wrap = check_wrap(wrap, self.image.width, "ImageBlock")

    def images(self) -> list[EmailImage]:
        return [self.image]

    def marked_copy(self) -> list[str]:
        return [self.caption]

    def text(self) -> str:
        """
        The alt text in brackets, its caption, and where a linked image goes.

        A **decorative** image projects to nothing at all, not to an empty
        ``[]`` — the mirror of the HTML side, where ``alt=""`` tells a screen
        reader to skip it. Its caption still projects, because a caption is
        copy the reader is meant to read either way.

        ``align`` projects to nothing: plain text has one column, so an
        alignment is presentation with nothing to present.
        """
        caption = text_markers(self.numbered(self.caption), self.notes, self.citing)
        if self.image.decorative:
            return self._with_subtitle(wrap(caption), wrap(self.disclosure))
        alt = f"[{self.image.alt}]"
        if self.link_url:
            alt = format_link(alt, self.link_url)
        return self._with_subtitle(wrap(alt), wrap(caption), wrap(self.disclosure))

    def context(self) -> dict[str, Any]:
        return {
            "image_src": self.image.src,
            "image_alt": self.image.alt,
            "image_decorative": self.image.decorative,
            "image_width": self.image.width or "",
            # Only a paged, decorative image reads this; see the template.
            "image_height": _displayed_height(self.image.data, self.image.width) or "",
            "image_align": self.align,
            "link_url": self.link_url,
            "caption": self.numbered(self.caption),
            "caption_parts": split_markers(self.numbered(self.caption), self.notes, self.citing),
            "anchor": self.resolved_anchor(),
            "disclosure": self.disclosure,
            "subtitle": self.subtitle,
        }


class MathBlock(Exhibit, Component):
    """
    A display equation: a rendered image and the LaTeX source it came from (#229).

    The builder never renders LaTeX; ``pyhermes.math`` does, behind the ``[math]``
    extra, and hands the bytes here. The source is the image's alt text and the
    text part's projection, so it survives every medium. `math.md` records why.

    Args:
        image:   PNG bytes, attached by ``cid:`` with the source as alt, or an
                 :class:`~pyhermes.builder.images.EmailImage` whose alt is the source.
        latex:   The source, without ``$``. One expression; no newline.
        lines:   Instead of ``latex``, the sources of a multi-line display, one
                 image; the source is then the lines joined by newlines (#232).
        width:   Display width in px, used only when ``image`` is bytes.
        caption, disclosure, label, anchor, notes, wrap: as on :class:`ImageBlock` (#359).
        align:   ``"center"`` (default), ``"left"`` or ``"right"``.
    """

    template_path = "media/math-block.html"

    SPACING_TOKENS = ("caption_gap",)

    ALIGNMENTS = tuple(ImageAlign)

    def __init__(
        self,
        image: bytes | EmailImage,
        latex: str = "",
        caption: str = "",
        width: int | None = None,
        align: str | ImageAlign = ImageAlign.CENTER,
        disclosure: str = "",
        label: str = "",
        anchor: str = "",
        notes: Sequence[Footnote | str] | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        lines: Sequence[str] | None = None,
        wrap: str = "",
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.lines = _equation_lines(latex, lines)
        latex = "\n".join(self.lines)
        if align not in self.ALIGNMENTS:
            raise ValidationError(
                f"'math_block.align' must be one of {[a.value for a in self.ALIGNMENTS]}, "
                f"got: {align!r}"
            )
        self.validate_exhibit(label, anchor)
        self.notes = coerce_notes(notes, [caption], "MathBlock")
        self.image = _equation_image(image, latex, width)
        self.latex = latex
        self.caption = caption
        self.align = align
        self.disclosure = disclosure
        self.wrap = check_wrap(wrap, self.image.width, "MathBlock")

    def images(self) -> list[EmailImage]:
        return [self.image]

    def marked_copy(self) -> list[str]:
        return [self.caption]

    def text(self) -> str:
        """The numbered caption, each line of the source in ``$ $``, the disclosure."""
        caption = text_markers(self.numbered(self.caption), self.notes, self.citing)
        source = "\n".join(f"${line}$" for line in self.lines)
        return self._with_subtitle(wrap(caption), source, wrap(self.disclosure))

    def context(self) -> dict[str, Any]:
        return {
            "image_src": self.image.src,
            "image_alt": self.image.alt,
            "image_width": self.image.width or "",
            "image_align": self.align,
            "caption": self.numbered(self.caption),
            "caption_parts": split_markers(self.numbered(self.caption), self.notes, self.citing),
            "anchor": self.resolved_anchor(),
            "disclosure": self.disclosure,
        }


def _equation_lines(latex: str, lines: Sequence[str] | None) -> list[str]:
    """The source's lines: ``latex`` alone, or ``lines``, never both."""
    if lines is None:
        if not isinstance(latex, str) or not latex.strip():
            raise ValidationError(f"'math_block.latex' is required, got: {latex!r}")
        if "\n" in latex:
            raise ValidationError(
                "'math_block.latex' holds a newline; one expression per image. "
                "For several lines, render them with math_block(lines=...)."
            )
        return [latex]
    if latex:
        raise ValidationError("'math_block' takes 'latex' or 'lines', not both")
    if isinstance(lines, str) or not lines:
        raise ValidationError(f"'math_block.lines' must be a non-empty list, got: {lines!r}")
    for line in lines:
        if not isinstance(line, str) or not line.strip() or "\n" in line:
            raise ValidationError(f"'math_block.lines' holds a blank or broken line: {line!r}")
    return list(lines)


def _equation_image(image: bytes | EmailImage, latex: str, width: int | None) -> EmailImage:
    """The equation's image, whose alt is its source by contract."""
    if isinstance(image, bytes | bytearray):
        return EmailImage.attached(bytes(image), alt=latex, width=width)
    if not isinstance(image, EmailImage):
        raise ValidationError(
            f"'math_block.image' must be PNG bytes or an EmailImage, got {type(image).__name__}"
        )
    if image.decorative or image.alt != latex:
        raise ValidationError(
            f"'math_block.image' alt must be the source {latex!r}, got {image.alt!r}; "
            "an equation's alt text is its LaTeX, so it is never decorative."
        )
    return image


# ──────────────────────────────────────────────────────────────────────
# Text components  (templates/text/)
# ──────────────────────────────────────────────────────────────────────


class TextBlock(CopyAlignment, Component):
    """
    Simple narrative prose block.

    Args:
        content:  HTML or plain-text paragraph content.  May contain
                  multiple ``<p>`` tags for multi-paragraph blocks.
        subtitle: Optional sub-heading rendered above the prose.
        notes:    Footnotes, each called by a ``[^n]`` marker in ``content``.
        drop_cap: Set the first letter large, on paper only (#189). An email
                  renders byte for byte as without it: the Word engine's
                  ``::first-letter`` is unreliable, and a wrong drop cap is
                  worse than none.
        figure:   An :class:`ImageBlock`, :class:`ChartBlock` or :class:`MathBlock`
                  the prose wraps round on paper, to the side its ``wrap`` names
                  (#189, #359); above the prose in an email. Unnumbered and
                  unnoted: the document's walk sees this block, not what it hosts.
        measure:  ``"standard"``, ``"narrow"`` or ``"full"`` (none): the longest
                  line, written only where the cell is wider (#358). Unset takes
                  the medium's, which only paper sets.
        aside:    An :class:`~pyhermes.builder.surfaces.Aside` the prose wraps round
                  on paper, a third of the column wide; a callout above the
                  prose in an email (#343). One float a block: not with ``figure``.
    """

    template_path = "text/text-block.html"

    SPACING_TOKENS = (
        "block_gap",
        "subtitle_gap",
        *PROSE_TOKENS,
    )

    def __init__(
        self,
        content: str,
        subtitle: str | None = None,
        align: str | None = None,
        notes: Sequence[Footnote | str] | None = None,
        drop_cap: bool = False,
        figure: ImageBlock | ChartBlock | MathBlock | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        measure: str | None = None,
        aside: Aside | None = None,
    ):
        from .surfaces import Aside  # a surface renders through this very class

        self.spacing = self._coerce_spacing(spacing)
        if not content:
            raise ValidationError("TextBlock requires content.")
        if aside is not None and not isinstance(aside, Aside):
            raise ValidationError(f"TextBlock.aside takes an Aside, got: {type(aside).__name__}")
        if aside is not None and figure is not None:
            raise ValidationError(
                "a TextBlock hosts one float: a figure or an aside, not both. "
                "Put the second in a block of its own."
            )
        refuse_top_headings(content, "TextBlock.content")
        if figure is not None and not isinstance(figure, (ImageBlock, ChartBlock, MathBlock)):
            raise ValidationError(
                "TextBlock.figure takes an ImageBlock, a ChartBlock or a MathBlock, "
                f"got: {type(figure).__name__}"
            )
        if figure is not None and (figure.label or figure.notes):
            raise ValidationError(
                "a TextBlock's figure cannot be numbered or carry notes: the document "
                "numbers what it walks, and it walks this block, not its figure"
            )
        self.align = self.validate_alignment(align)
        self.notes = coerce_notes(notes, [content], "TextBlock")
        self.content = content
        self.subtitle = subtitle
        self.drop_cap = drop_cap
        self.figure = figure
        self.aside = aside
        self.measure = coerce_measure(measure, "TextBlock")

    def render(self, engine: Renderer) -> str:
        """
        As any component, with a figure placed and, on paper, the first letter set.

        The drop cap is a real element rather than ``::first-letter``: WeasyPrint
        lays out the first line before a floated pseudo-element, so the line ran
        over the letter it should have wrapped. The caller's markup is otherwise
        untouched. A figure floats on paper and sits above the prose elsewhere.
        """
        engine = respaced(engine, self.spacing, type(self).__name__)
        ctx = self.context()
        # Dark mode forces `.body-text` to the theme's dark type, lost on a section's own ground.
        ctx["body_class"] = "" if on_ground(engine) else "body-text"
        paged = engine.medium.paged
        if self.drop_cap and paged:
            ctx["text_parts"] = split_markers(_with_drop_cap(self.content), self.notes, self.citing)
        if self.figure is not None:
            ctx["figure_html"] = self.figure.render(engine)
            ctx["figure_wrap"] = self.figure.wrap if paged else ""
            ctx["figure_width"] = self.figure.image.width or ""
        if self.aside is not None:
            width = cell_width_of(engine)
            if paged:
                # A third of the column, or up to half a narrow one (a panel's), so
                # the box keeps room for copy inside its padding.
                floor = 8 * scheme_of(engine).component.callout_pad_x
                width = int(max(width // 3, min(width // 2, floor)))
            ctx["aside_html"] = self.aside.render(engine, width)
            ctx["aside_side"] = self.aside.side if paged else ""
            ctx["aside_width"] = width
        ctx["measure_px"], ctx["measure_place"] = self._measure(engine)
        return engine.render(self.template_path, ctx)

    def _measure(self, engine: Renderer) -> tuple[int | str, str]:
        """The px this block's lines cap at, and how it sits; ``""`` where its cell already fits."""
        measure = self.measure or engine.medium.measure
        if not measure or measure == "full":
            return "", ""
        cap = measure_px(scheme_of(engine), measure)
        if cell_width_of(engine) <= cap:
            return "", ""
        return cap, self.align or placement_of(engine)

    def raw_html(self) -> list[str]:
        return [self.content]

    def images(self) -> list[EmailImage]:
        """The figure's image, when there is one (standing rule 7)."""
        return self.figure.images() if self.figure is not None else []

    def marked_copy(self) -> list[str]:
        return [self.content]

    def text(self) -> str:
        """The figure, then the prose through #108's degrader — ``content`` is raw HTML."""
        prose = wrap(html_to_text(text_markers(self.content, self.notes, self.citing)))
        figure = self.figure.text() if self.figure is not None else ""
        aside = self.aside.text() if self.aside is not None else ""
        return self._with_subtitle(figure, prose, aside)

    def context(self) -> dict[str, Any]:
        return {
            "text_content": self.content,
            "body_class": "body-text",
            "text_parts": split_markers(self.content, self.notes, self.citing),
            "subtitle": self.subtitle,
            "figure_html": "",
            "figure_wrap": "",
            "figure_width": "",
            "aside_html": "",
            "aside_side": "",
            "aside_width": "",
            **self.alignment_context(),
        }


class PullQuote(CopyAlignment, Component):
    """
    A line lifted from the copy and set large, beside a rule (#189).

    The same markup in every medium, which is its email degradation: a
    highlighted band an Outlook reader sees exactly as a printed page does.
    Both fields are plain text, escaped, so it opens no raw-HTML surface.

    Args:
        text:        The quoted words, without quotation marks.
        attribution: Who said them, set beneath. Optional.
        align:       Alignment for the quote's copy; inherits when unset.
    """

    OWN_SURFACE = True

    template_path = "text/pull-quote.html"

    SPACING_TOKENS = (
        "block_gap",
        "caption_gap",
        "column_pad_x",
    )

    def __init__(
        self,
        text: str,
        attribution: str | None = None,
        align: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not text:
            raise ValidationError("PullQuote requires text.")
        self.align = self.validate_alignment(align)
        self.text_value = text
        self.attribution = attribution

    def text(self) -> str:
        """The quote indented four spaces, and its attribution beneath."""
        lines = wrap(f'"{self.text_value}"').splitlines()
        if self.attribution:
            lines.append(f"-- {self.attribution}")
        return self._with_subtitle("\n".join(f"    {line}" for line in lines))

    def context(self) -> dict[str, Any]:
        return {
            "quote": self.text_value,
            "attribution": self.attribution or "",
            **self.alignment_context(),
        }


def _with_drop_cap(html: str) -> str:
    """``html`` with its first visible character, or entity, wrapped for the drop cap."""
    index = 0
    while index < len(html):
        if html[index] == "<":
            index = html.find(">", index) + 1 or len(html)
        elif html[index].isspace():
            index += 1
        else:
            end = html.find(";", index) + 1 if html[index] == "&" else index + 1
            letter = html[index:end]
            return f'{html[:index]}<span class="drop-cap">{letter}</span>{html[end:]}'
    return html


class ContactBlock(CopyAlignment, Component):
    """
    A contact call-to-action card: heading, blurb, and a button.

    The body-component form of what used to be the footer's contact card.
    Placed like any component — ``FullWidth(content=ContactBlock(...))`` —
    typically as the last section. Owns the Outlook ``v:roundrect`` / anchor
    dual button. Validates at construction, like every model here.
    """

    OWN_SURFACE = True

    template_path = "text/contact-block.html"

    SPACING_TOKENS = (
        "contact_pad_y",
        "contact_pad_x",
        "contact_heading_gap",
        "contact_cta_gap",
    )

    def __init__(
        self,
        heading: str,
        description: str = "",
        cta_label: str = "Contact Us",
        cta_url: str = "",
        align: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not heading:
            raise ValidationError("ContactBlock requires a heading.")
        self.align = self.validate_alignment(align)
        if not cta_url:
            raise ValidationError("ContactBlock requires a cta_url.")
        _validate_url(cta_url, "ContactBlock.cta_url")
        self.heading = heading
        self.description = description
        self.cta_label = cta_label
        self.cta_url = cta_url

    def text(self) -> str:
        """
        Heading, blurb, and the call to action as ``label: url``.

        ``description`` does **not** go through the degrader: unlike the five
        blessed surfaces it is escaped on its way into the template, so it is
        plain text already and degrading it would decode entities the caller
        wrote literally.
        """
        return self._with_subtitle(
            wrap(self.heading),
            wrap(self.description),
            wrap(link_line(self.cta_label, self.cta_url)),
        )

    def context(self) -> dict[str, Any]:
        return {
            "contact_heading": self.heading,
            "contact_description": self.description,
            "contact_cta_label": self.cta_label,
            "contact_url": self.cta_url,
            **self.alignment_context(),
        }


class NumberedList(CopyAlignment, Component):
    """
    Numbered theme / item list (e.g. "Key Themes" section).

    Args:
        items:    List of NumberedItem instances.
        subtitle: Optional sub-heading rendered above the list.
    """

    template_path = "text/numbered-list.html"

    SPACING_TOKENS = (
        "block_gap",
        "subtitle_gap",
        "list_ordinal_gap",
        "list_title_gap",
        *PROSE_TOKENS,
    )

    def __init__(
        self,
        items: list[NumberedItem],
        subtitle: str | None = None,
        align: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not items:
            raise ValidationError("NumberedList requires at least one item.")
        self.align = self.validate_alignment(align)
        for item in items:
            item.validate()
        self.items = items
        self.subtitle = subtitle

    def marked_copy(self) -> list[str]:
        return [item.body for item in self.items]

    def text(self) -> str:
        """
        ``1. Title`` and its body, one item per block.

        The ordinals come from the shipped ``NumberedItem.number`` field
        rather than from an enumeration, because the caller chose them — and
        this is the surface that carries them as *data*, which is why #108's
        degrader can project an ``ol`` as plain bullets without losing
        anything anyone expressed.
        """
        return self._with_subtitle(
            *(
                join_blocks(
                    wrap(f"{item.number}. {item.title}"),
                    wrap(html_to_text(text_markers(item.body, item.footnotes(), self.citing))),
                )
                for item in self.items
            )
        )

    def raw_html(self) -> list[str]:
        return [item.body for item in self.items]

    def footnotes(self) -> list[Footnote]:
        """Every item's notes, item by item."""
        return [note for item in self.items for note in item.footnotes()]

    def context(self) -> dict[str, Any]:
        return {
            "items": [
                {
                    "number": it.number,
                    "title": it.title,
                    "body": it.body,
                    "body_parts": split_markers(it.body, it.footnotes(), self.citing),
                }
                for it in self.items
            ],
            "subtitle": self.subtitle,
            **self.alignment_context(),
        }


class AuthorBlock(CopyAlignment, Component):
    """
    Author attribution byline.

    Args:
        name:      Full name.
        job_title: Job title or role (e.g. "Chief Market Strategist").
        email:     Contact email address.
        subtitle:  Optional sub-heading rendered above the byline.
    """

    template_path = "text/author-block.html"

    SPACING_TOKENS = (
        "author_name_gap",
        "author_sep_gap",
        "author_rule_gap",
        "subtitle_gap",
    )

    def __init__(
        self,
        name: str,
        job_title: str = "",
        email: str = "",
        subtitle: str | None = None,
        align: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not name:
            raise ValidationError("AuthorBlock requires a name.")
        self.align = self.validate_alignment(align)
        self.name = name
        self.job_title = job_title
        self.email = email
        self.subtitle = subtitle

    def text(self) -> str:
        """The byline: name, then role and address on one line."""
        byline = " · ".join(filter(None, (self.job_title, self.email)))
        return self._with_subtitle(wrap("\n".join(filter(None, (self.name, byline)))))

    def context(self) -> dict[str, Any]:
        return {
            "author_name": self.name,
            "author_job_title": self.job_title,
            "author_email": self.email,
            "subtitle": self.subtitle,
            **self.alignment_context(),
        }


class Contents(CellShare, Component):
    """
    An "In this issue" list: every titled section, linked to its heading.

    **The document fills it; the caller only places it.** A component cannot
    see the tree it sits in, so :class:`~pyhermes.builder.document.Document` hands
    it the section titles and anchors in reading order before each
    projection, leaving out the section that holds the list itself.

    ``of="exhibits"`` lists the numbered exhibits instead (#308), each under
    the heading it carries, so a list of tables and figures is the same walk
    read another way. ``label`` narrows it to one label's sequence.

    One class and one template serve both media. On paper the paged
    skeleton's stylesheet appends each entry's page number, a figure only the
    print engine knows; in an email the same markup is a linked list with no
    page column, because there are no pages. The paged medium's own contents
    sheet is :class:`~pyhermes.document.regions.ContentsPage`, which renders the
    same partial.

    Args:
        subtitle: Optional sub-heading rendered above the list.
        of:       ``"sections"`` (the default) or ``"exhibits"``.
        label:    With ``of="exhibits"``, list only this label: ``"Table"``.
        width:    A share of the cell, 0.3 to 1.0, placed by the section's align (#357).
    """

    template_path = "text/contents.html"

    SPACING_TOKENS = (
        "caption_gap",
        "subtitle_gap",
    )

    def __init__(
        self,
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        of: str = "sections",
        label: str | None = None,
        *,
        width: float | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.width = self.validate_share(width)
        self.of, self.label = check_listing(of, label, "Contents")
        self.subtitle = subtitle
        #: ``(title, anchor)`` per listed entry, assigned by the document.
        self.entries: list[tuple[str, str]] = []

    def text(self) -> str:
        """The titles, one per line and unnumbered: plain text has no pages to cite."""
        return self._with_subtitle(wrap("\n".join(title for title, _ in self.entries)))

    def context(self) -> dict[str, Any]:
        return {
            "subtitle": self.subtitle,
            "contents_entries": contents_entries(self.entries),
        }


#: What a contents list may list: the titled sections, or the numbered exhibits.
LISTINGS = ("sections", "exhibits")


def check_listing(of: str, label: str | None, owner: str) -> tuple[str, str | None]:
    """``(of, label)`` validated: a known listing, and a label only on exhibits."""
    if of not in LISTINGS:
        raise ValidationError(f"{owner}(of=...) takes one of {list(LISTINGS)}, got: {of!r}")
    if label is not None and (of != "exhibits" or not label.strip()):
        raise ValidationError(
            f"{owner}(label=...) narrows a list of exhibits to one label, such as 'Table'; "
            f"got label={label!r} with of={of!r}."
        )
    return of, label


def contents_entries(entries: list[tuple[str, str]]) -> list[dict[str, str]]:
    """The shape the shared contents partial reads, from ``(title, anchor)`` pairs."""
    return [{"title": title, "anchor": anchor} for title, anchor in entries]


class Endnotes(Component):
    """
    A document's notes gathered at its end: the email's honest footnote (#182).

    An email client has no sheet foot, so the notes a paged document floats
    to the foot of each sheet are listed here, after the last section, each
    linked back to its marker. The plain-text part prints the same list in
    every medium. Not public: the document builds one when it has notes, and
    a caller never places it.
    """

    template_path = "common/endnotes.html"

    def __init__(self, notes: list[Footnote], heading: str = "Notes"):
        self.notes = notes
        self.heading = heading

    def text(self) -> str:
        """``[7] Returns are gross of fees.``, one per note, wrapped under its number."""
        lines = [
            textwrap.fill(
                f"[{note.number}] {note.text}",
                LINE_WIDTH,
                subsequent_indent=" " * (len(str(note.number)) + 3),
            )
            for note in self.notes
        ]
        return join_blocks(underline(self.heading), "\n".join(lines))

    def context(self) -> dict[str, Any]:
        return {
            "notes_heading": self.heading,
            "notes": [
                {
                    "number": note.number,
                    "text": note.text,
                    "anchor": note_anchor(note.number or 0),
                    "ref_anchor": note_ref_anchor(note.number or 0),
                }
                for note in self.notes
            ],
        }
