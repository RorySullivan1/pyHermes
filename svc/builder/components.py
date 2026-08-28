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

import warnings
from typing import Any

from .engine import Renderer
from .enums import CardOrientation, ColumnKind, ImageAlign
from .exceptions import ValidationError
from .images import EmailImage, ImageAsset, coerce_image
from .models import Card, Column, NumberedItem, TableRow, _validate_url, coerce_column
from .textgen import format_link, html_to_text, join_blocks, link_line, table, wrap


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


class DataTable(Component):
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
    ):
        if not headers:
            raise ValidationError("DataTable requires at least one header.")
        if not rows:
            raise ValidationError("DataTable requires at least one row.")
        columns = [coerce_column(h, f"data_table.headers[{i}]") for i, h in enumerate(headers)]
        for i, row in enumerate(rows):
            row.validate()
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
            table(
                self.headers,
                [[cell.text for cell in row.cells] for row in self.rows],
                aligns=[column.align for column in self.resolved_columns()],
            ),
            wrap("\n".join(filter(None, (self.source, self.as_of)))),
        )

    def context(self) -> dict[str, Any]:
        columns = self.resolved_columns()
        return {
            "columns": [{"header": c.header, "align": c.align, "kind": c.kind} for c in columns],
            "rows": [
                {
                    "cells": [
                        {
                            "text": cell.text,
                            # The chain completes here: cell → column → position.
                            "align": cell.resolved_align(column.align),
                            "color": cell.color,
                            "background": cell.background,
                            "is_text": column.kind == ColumnKind.TEXT,
                        }
                        for cell, column in zip(r.cells, columns, strict=True)
                    ],
                    "alt": i % 2 == 1,  # alternating row background
                }
                for i, r in enumerate(self.rows)
            ],
            "source": self.source,
            "as_of": self.as_of,
            "subtitle": self.subtitle,
        }


class ChartBlock(Component):
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
    """

    template_path = "analysis/chart-block.html"

    def __init__(
        self,
        image_url: str | EmailImage,
        alt_text: str = "Chart",
        source: str = "",
        subtitle: str | None = None,
        width: int | None = None,
    ):
        if not image_url:
            raise ValidationError("ChartBlock requires an image_url.")
        self.image = coerce_image(
            image_url, alt=alt_text, field_name="chart.image_url", width=width
        )
        self.source = source
        self.subtitle = subtitle

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
        return self._with_subtitle(wrap(f"[{self.image.alt}]"), wrap(self.source))

    def context(self) -> dict[str, Any]:
        return {
            "chart_image_url": self.image.src,
            "chart_alt_text": self.image.alt,
            "chart_image_width": self.image.width or "",
            "chart_source": self.source,
            "subtitle": self.subtitle,
        }


class ImageBlock(Component):
    """
    A single image — optionally linked, captioned and aligned.

    The generic image component: any picture that is not a data exhibit.
    Charts keep their own component (:class:`ChartBlock`) for the border
    and attribution line.

    Args:
        image:    An :class:`~svc.builder.images.EmailImage`, or a plain URL
            string wrapped as a hosted image using ``alt_text``.
        alt_text: Alt text, used only when ``image`` is a bare URL string.
        caption:  Optional caption rendered beneath the image.
        link_url: Optional URL the image links to.
        align:    ``"center"`` (default), ``"left"`` or ``"right"``.
        subtitle: Optional sub-heading rendered above the image.
        width:    Display width in px, used only when ``image`` is a bare
            URL string.  ``None`` renders full width.

    Raises:
        ValidationError: On a missing image, an unsupported alignment, or
            an unsafe ``link_url`` scheme.
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
    ):
        if not image:
            raise ValidationError("ImageBlock requires an image.")
        if align not in self.ALIGNMENTS:
            raise ValidationError(
                f"Unsupported alignment '{align}'. Use: {[a.value for a in self.ALIGNMENTS]}"
            )
        _validate_url(link_url, "image.link_url")

        self.image = coerce_image(image, alt=alt_text, field_name="image", width=width)
        self.caption = caption
        self.link_url = link_url
        self.align = align
        self.subtitle = subtitle

    def images(self) -> list[EmailImage]:
        return [self.image]

    def text(self) -> str:
        """
        The alt text in brackets, its caption, and where a linked image goes.

        ``align`` projects to nothing: plain text has one column, so an
        alignment is presentation with nothing to present.
        """
        alt = f"[{self.image.alt}]"
        if self.link_url:
            alt = format_link(alt, self.link_url)
        return self._with_subtitle(wrap(alt), wrap(self.caption))

    def context(self) -> dict[str, Any]:
        return {
            "image_src": self.image.src,
            "image_alt": self.image.alt,
            "image_width": self.image.width or "",
            "image_align": self.align,
            "link_url": self.link_url,
            "caption": self.caption,
            "subtitle": self.subtitle,
        }


# ──────────────────────────────────────────────────────────────────────
# Text components  (templates/text/)
# ──────────────────────────────────────────────────────────────────────


class TextBlock(Component):
    """
    Simple narrative prose block.

    Args:
        content:  HTML or plain-text paragraph content.  May contain
                  multiple ``<p>`` tags for multi-paragraph blocks.
        subtitle: Optional sub-heading rendered above the prose.
    """

    template_path = "text/text-block.html"

    def __init__(self, content: str, subtitle: str | None = None):
        if not content:
            raise ValidationError("TextBlock requires content.")
        self.content = content
        self.subtitle = subtitle

    def text(self) -> str:
        """The prose, through #108's degrader — ``content`` is raw HTML."""
        return self._with_subtitle(wrap(html_to_text(self.content)))

    def context(self) -> dict[str, Any]:
        return {
            "text_content": self.content,
            "subtitle": self.subtitle,
        }


class ContactBlock(Component):
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
    ):
        if not heading:
            raise ValidationError("ContactBlock requires a heading.")
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
        }


class NumberedList(Component):
    """
    Numbered theme / item list (e.g. "Key Themes" section).

    Args:
        items:    List of NumberedItem instances.
        subtitle: Optional sub-heading rendered above the list.
    """

    template_path = "text/numbered-list.html"

    def __init__(self, items: list[NumberedItem], subtitle: str | None = None):
        if not items:
            raise ValidationError("NumberedList requires at least one item.")
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
                join_blocks(wrap(f"{item.number}. {item.title}"), wrap(html_to_text(item.body)))
                for item in self.items
            )
        )

    def context(self) -> dict[str, Any]:
        return {
            "items": [
                {
                    "number": it.number,
                    "title": it.title,
                    "body": it.body,
                }
                for it in self.items
            ],
            "subtitle": self.subtitle,
        }


class AuthorBlock(Component):
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
    ):
        if not name:
            raise ValidationError("AuthorBlock requires a name.")
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
        }
