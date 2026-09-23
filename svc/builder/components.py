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
from collections.abc import Sequence
from typing import Any

from svc.config import get_config

from .apparatus import (
    note_anchor,
    note_ref_anchor,
    slugify,
    split_markers,
    text_markers,
    validate_anchor,
)
from .engine import Renderer
from .enums import CardOrientation, ColumnKind, ImageAlign, RowKind
from .exceptions import ValidationError
from .images import EmailImage, ImageAsset, coerce_image
from .models import (
    Card,
    Cell,
    Column,
    Footnote,
    NumberedItem,
    TableRow,
    _validate_align,
    _validate_url,
    coerce_column,
    coerce_notes,
)
from .textgen import (
    LINE_WIDTH,
    format_link,
    html_to_text,
    join_blocks,
    link_line,
    table,
    underline,
    wrap,
)


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
    text — see :class:`~svc.builder.enums.ImageAlign`. :class:`Contents`
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


class Exhibit:
    """
    What makes a chart, table or image *"Exhibit 3"* — mixed into all three.

    ``label`` opts an exhibit into numbering; unset, it renders exactly as it
    did before #181. Separate labels count separately, so *"Table 2"* and
    *"Figure 1"* coexist in one document.

    **The number is assigned, never chosen.** :class:`~svc.builder.document.
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

    def validate_exhibit(self, label: str, anchor: str) -> None:
        """Validate and store the two caller-facing fields."""
        name = type(self).__name__.lower()
        if label and not label.strip():
            raise ValidationError(f"'{name}.label' must not be blank, got: {label!r}")
        validate_anchor(anchor, f"{name}.anchor")
        self.label = label
        self.anchor = anchor
        self.number = None

    def resolved_anchor(self) -> str:
        """The ``id`` this exhibit carries, or ``""`` when it has none."""
        if self.anchor:
            return self.anchor
        if self.label and self.number:
            return f"{slugify(self.label, 'exhibit')}-{self.number}"
        return ""

    def numbered(self, heading: str) -> str:
        """``heading`` behind this exhibit's number — the one string both projections print."""
        if not (self.label and self.number):
            return heading
        prefix = f"{self.label} {self.number}"
        return f"{prefix}{get_config().exhibit_separator}{heading}" if heading else prefix


class Component:
    """
    Abstract base for all email components.

    Subclasses must set ``template_path`` and implement ``context()``.
    A component that renders an image also overrides ``images()``.
    """

    template_path: str = ""  # e.g. "analysis/kpi-strip.html"

    def context(self) -> dict[str, Any]:
        """Return the template context dict for this component."""
        raise NotImplementedError

    def images(self) -> list[EmailImage]:
        """
        Return every :class:`EmailImage` this component renders.

        Empty for the text and data components, which carry none. Override
        it in any component that emits an ``<img>``, so the email can
        collect the manifest of parts a delivery layer must attach.
        """
        return []

    def raw_html(self) -> list[str]:
        """
        The caller markup this component emits raw, for the document's link check.

        Empty by default: only the blessed raw-HTML fields carry markup, and a
        component holding one returns it so a ``#fragment`` in it is checked.
        """
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
            "uses it. See svc/builder/textgen.py for the formatting policy."
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
        return engine.render(self.template_path, self.context())


# ──────────────────────────────────────────────────────────────────────
# Analysis components  (templates/analysis/)
# ──────────────────────────────────────────────────────────────────────


class CardGroup(Component):
    """
    A set of callout cards, laid out horizontally or vertically.

    ``horizontal`` is the classic KPI strip — 2–4 cells across, sized to
    share the width.  ``vertical`` stacks the same cards one per row, which
    is also what the horizontal strip collapses to on a phone.

    Args:
        cards:       List of Card (or KpiItem) instances.
        orientation: ``"horizontal"`` (default) or ``"vertical"``.
        subtitle:    Optional sub-heading rendered above the group.

    Raises:
        ValidationError: On an unsupported orientation, a card count outside
            the orientation's limits, or an invalid card.
    """

    template_path = "analysis/card-group.html"

    # Members equal and hash as their string value, so membership tests and
    # equality checks below accept both a CardOrientation and a bare string.
    ORIENTATIONS = tuple(CardOrientation)

    def __init__(
        self,
        cards: list[Card],
        orientation: str | CardOrientation = CardOrientation.HORIZONTAL,
        subtitle: str | None = None,
    ):
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
            head = f"{card.label}: {card.value}" if card.value else card.label
            if card.sublabel:
                head = f"{head} ({card.sublabel})"
            lines.append(head)
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


class DataTable(Exhibit, Component):
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
        disclosure: Optional compliance copy qualifying this exhibit —
                  justified fine print beneath the attribution. Plain
                  text, escaped on the way out; see `disclosure.md` for when
                  it belongs here rather than on ``Footer.disclaimer``.
        label, anchor: Numbering and its ``id``; see :class:`Exhibit`.
        notes:    Footnotes called by ``[^n]`` in ``caption`` or ``source``.

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
    position, and :func:`~svc.builder.textgen.table` is handed the resolved
    alignments rather than re-deriving them — which is what stops the HTML
    and the plain-text part disagreeing about the same table.
    """

    template_path = "analysis/data-table.html"

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
    ):
        self.validate_exhibit(label, anchor)
        self.notes = coerce_notes(notes, [caption, source], "DataTable")
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
        self.columns = columns
        self.rows = rows
        self.source = source
        self.as_of = as_of
        self.subtitle = subtitle
        self.caption = caption
        self.disclosure = disclosure

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
            wrap(text_markers(self.numbered(self.caption), self.notes)),
            table(
                self.headers,
                [[cell.text for cell in row.cells] for row in self.rows],
                aligns=[column.align for column in self.resolved_columns()],
                kinds=[row.kind for row in self.rows],
            ),
            wrap("\n".join(filter(None, (text_markers(self.source, self.notes), self.as_of)))),
            wrap(self.disclosure),
        )

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

    def context(self) -> dict[str, Any]:
        columns = self.resolved_columns()
        alt_by_row = self._striping()
        return {
            "columns": [{"header": c.header, "align": c.align, "kind": c.kind} for c in columns],
            "rows": [
                {
                    "kind": r.kind,
                    "cells": [
                        {
                            "text": cell.text,
                            # The chain completes here: cell → column → position.
                            "align": cell.resolved_align(column.align),
                            "color": cell.color,
                            "tone": cell.tone,
                            "background": cell.background,
                            "is_text": column.kind == ColumnKind.TEXT,
                            # A row header, not a data cell: the first column
                            # labels the figures beside it, so it is the `th`
                            # a reader navigates by. Keyed on the resolved
                            # kind rather than the position, so a table whose
                            # first column is genuinely numeric — a rank —
                            # does not claim to head its row.
                            "row_header": index == 0 and column.kind == ColumnKind.TEXT,
                        }
                        for index, (cell, column) in enumerate(zip(r.cells, columns, strict=True))
                    ],
                    # Striping counts *data* rows: a subhead in the middle of a
                    # table must not invert the tint of everything beneath it.
                    "alt": alt_by_row[id(r)],
                }
                for r in self.rows
            ],
            "source": self.source,
            "source_parts": split_markers(self.source, self.notes),
            "as_of": self.as_of,
            "subtitle": self.subtitle,
            "caption": self.numbered(self.caption),
            "caption_parts": split_markers(self.numbered(self.caption), self.notes),
            "anchor": self.resolved_anchor(),
            "disclosure": self.disclosure,
        }


class ChartBlock(Exhibit, CopyAlignment, Component):
    """
    A chart image, bordered, with source attribution.

    The charting specialisation of :class:`ImageBlock` — same image
    handling, plus the hairline border and the attribution line a data
    exhibit needs.

    Args:
        image_url: An :class:`~svc.builder.images.EmailImage`, or a plain
            URL string, which is wrapped as a hosted image using
            ``alt_text``.  Pass an ``EmailImage`` to embed the chart by
            ``cid:`` so it renders in Outlook without a download prompt.
        alt_text:  Accessibility alt text.  Ignored when ``image_url`` is
            an ``EmailImage``, which carries its own.
        source:    Attribution string.
        subtitle:  Optional sub-heading rendered above the chart.
        width:     Display width in px.  Ignored when ``image_url`` is an
            ``EmailImage``, which carries its own.  ``None`` renders full
            width, as before.
        disclosure: Optional compliance copy qualifying this exhibit —
                  justified fine print beneath the attribution. Plain
                  text, escaped on the way out; see `disclosure.md` for when
                  it belongs here rather than on ``Footer.disclaimer``.
        caption:  Optional heading line above the chart, where its number goes.
        label, anchor: Numbering and its ``id``; see :class:`Exhibit`.
        notes:    Footnotes called by ``[^n]`` in ``caption`` or ``source``.
    """

    template_path = "analysis/chart-block.html"

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
    ):
        if not image_url:
            raise ValidationError("ChartBlock requires an image_url.")
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

    def text(self) -> str:
        """
        The alt text in brackets, then the attribution.

        ``alt`` is required at construction, so this projection is never
        empty — which is the whole reason that rule exists.
        """
        return self._with_subtitle(
            wrap(text_markers(self.numbered(self.caption), self.notes)),
            wrap(f"[{self.image.alt}]"),
            wrap(text_markers(self.source, self.notes)),
            wrap(self.disclosure),
        )

    def context(self) -> dict[str, Any]:
        return {
            "chart_image_url": self.image.src,
            "chart_alt_text": self.image.alt,
            "chart_image_width": self.image.width or "",
            "chart_source": self.source,
            "chart_source_parts": split_markers(self.source, self.notes),
            "caption": self.numbered(self.caption),
            "caption_parts": split_markers(self.numbered(self.caption), self.notes),
            "anchor": self.resolved_anchor(),
            # Bare, not ``chart_``-prefixed: all three exhibits include one
            # shared partial, so they must agree on the key it reads.
            "disclosure": self.disclosure,
            "subtitle": self.subtitle,
            **self.alignment_context(),
        }


class ImageBlock(Exhibit, Component):
    """
    A single image — optionally linked, captioned and aligned.

    The generic image component: any picture that is not a data exhibit.
    Charts keep their own component (:class:`ChartBlock`) for the border
    and attribution line.

    Args:
        image:    An :class:`~svc.builder.images.EmailImage`, or a plain URL
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

    Raises:
        ValidationError: On a missing image, a bad alignment or link scheme.
    """

    template_path = "media/image-block.html"

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
    ):
        if not image:
            raise ValidationError("ImageBlock requires an image.")
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

    def images(self) -> list[EmailImage]:
        return [self.image]

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
        caption = text_markers(self.numbered(self.caption), self.notes)
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
            "image_align": self.align,
            "link_url": self.link_url,
            "caption": self.numbered(self.caption),
            "caption_parts": split_markers(self.numbered(self.caption), self.notes),
            "anchor": self.resolved_anchor(),
            "disclosure": self.disclosure,
            "subtitle": self.subtitle,
        }


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
    """

    template_path = "text/text-block.html"

    def __init__(
        self,
        content: str,
        subtitle: str | None = None,
        align: str | None = None,
        notes: Sequence[Footnote | str] | None = None,
        drop_cap: bool = False,
    ):
        if not content:
            raise ValidationError("TextBlock requires content.")
        self.align = self.validate_alignment(align)
        self.notes = coerce_notes(notes, [content], "TextBlock")
        self.content = content
        self.subtitle = subtitle
        self.drop_cap = drop_cap

    def render(self, engine: Renderer) -> str:
        """
        As any component, except that a drop cap on paper wraps the first letter.

        A real element rather than ``::first-letter``: WeasyPrint lays out the
        first line before a floated pseudo-element, so the line ran over the
        letter it should have wrapped. The caller's markup is otherwise untouched.
        """
        if not (self.drop_cap and engine.medium.paged):
            return super().render(engine)
        ctx = self.context()
        ctx["text_parts"] = split_markers(_with_drop_cap(self.content), self.notes)
        return engine.render(self.template_path, ctx)

    def raw_html(self) -> list[str]:
        return [self.content]

    def text(self) -> str:
        """The prose, through #108's degrader — ``content`` is raw HTML."""
        return self._with_subtitle(wrap(html_to_text(text_markers(self.content, self.notes))))

    def context(self) -> dict[str, Any]:
        return {
            "text_content": self.content,
            "text_parts": split_markers(self.content, self.notes),
            "subtitle": self.subtitle,
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

    template_path = "text/pull-quote.html"

    def __init__(self, text: str, attribution: str | None = None, align: str | None = None):
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

    template_path = "text/contact-block.html"

    def __init__(
        self,
        heading: str,
        description: str = "",
        cta_label: str = "Contact Us",
        cta_url: str = "",
        align: str | None = None,
    ):
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

    def __init__(
        self,
        items: list[NumberedItem],
        subtitle: str | None = None,
        align: str | None = None,
    ):
        if not items:
            raise ValidationError("NumberedList requires at least one item.")
        self.align = self.validate_alignment(align)
        for item in items:
            item.validate()
        self.items = items
        self.subtitle = subtitle

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
                    wrap(html_to_text(text_markers(item.body, item.footnotes()))),
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
                    "body_parts": split_markers(it.body, it.footnotes()),
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

    def __init__(
        self,
        name: str,
        job_title: str = "",
        email: str = "",
        subtitle: str | None = None,
        align: str | None = None,
    ):
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


class Contents(Component):
    """
    An "In this issue" list: every titled section, linked to its heading.

    **The document fills it; the caller only places it.** A component cannot
    see the tree it sits in, so :class:`~svc.builder.document.Document` hands
    it the section titles and anchors in reading order before each
    projection, leaving out the section that holds the list itself.

    One class and one template serve both media. On paper the paged
    skeleton's stylesheet appends each entry's page number, a figure only the
    print engine knows; in an email the same markup is a linked list with no
    page column, because there are no pages. The paged medium's own contents
    sheet is :class:`~svc.document.regions.ContentsPage`, which renders the
    same partial.

    Args:
        subtitle: Optional sub-heading rendered above the list.
    """

    template_path = "text/contents.html"

    def __init__(self, subtitle: str | None = None):
        self.subtitle = subtitle
        #: ``(title, anchor)`` per listed section, assigned by the document.
        self.entries: list[tuple[str, str]] = []

    def text(self) -> str:
        """The titles, one per line and unnumbered: plain text has no pages to cite."""
        return self._with_subtitle(wrap("\n".join(title for title, _ in self.entries)))

    def context(self) -> dict[str, Any]:
        return {
            "subtitle": self.subtitle,
            "contents_entries": contents_entries(self.entries),
        }


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
