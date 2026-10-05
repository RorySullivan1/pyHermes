"""
Organising content (#329): a box of facts, a run of dated events, a list of further reading.

Each is a layout table of plain-text fields, so it renders in Outlook, stacks
on a phone where it has columns, and projects to text that keeps its shape.
`.claude/rules/design-axes.md` records the layouts and `builder-architecture.md`
why a timeline's body is plain text.
"""

from __future__ import annotations

import math
import textwrap
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import formats
from .components import Component
from .engine import Renderer, cell_width_of, respaced, scheme_of
from .exceptions import ValidationError
from .images import EmailImage
from .models import Badge, Cell, _require, _validate_url, is_figure
from .sizing import Spacing
from .textgen import LINE_WIDTH, join_blocks, link_line, wrap

#: The column counts a fact list and a teaser list take.
COLUMN_COUNTS = (1, 2, 3)


def _check_columns(columns: object, count: int, owner: str) -> int:
    """``columns`` as one of :data:`COLUMN_COUNTS`, and no more than there are items."""
    if not isinstance(columns, int) or isinstance(columns, bool) or columns not in COLUMN_COUNTS:
        raise ValidationError(f"{owner} takes columns of 1, 2 or 3, got: {columns!r}")
    if columns > count:
        raise ValidationError(f"{owner} has {count} item(s) for {columns} columns")
    return columns


def _shares(engine: Renderer, columns: int) -> dict[str, str]:
    """Each column's share of the cell this list fills, once the gutters take theirs."""
    gutter = 100 * scheme_of(engine).space.gutter / cell_width_of(engine) if columns > 1 else 0
    return {"share": f"{round((100 - gutter * (columns - 1)) / columns, 2):g}"}


# ──────────────────────────────────────────────────────────────────────
# Fact list (#330)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Fact:
    """One label and its value, written: what a :class:`FactList` draws."""

    label: str
    value: str
    numeric: bool = False
    tone: str = ""


def _coerce_fact(label: object, value: object, fmt: Callable[[Any], str], index: int) -> Fact:
    """A label and a string, a figure or a :class:`Cell`, as a written :class:`Fact`."""
    owner = f"fact_list.facts[{index}]"
    if not isinstance(label, str) or not label.strip():
        raise ValidationError(f"{owner} needs a label: plain text, got: {label!r}")
    if isinstance(value, Cell):
        value.validate()
        if value.color or value.background or value.badge:
            raise ValidationError(
                f"{owner} ({label!r}) takes a tone, not a colour, background or badge"
            )
        written = value.text or (fmt(value.value) if is_figure(value.value) else "")
        _require(written, f"{owner}.value")
        return Fact(label, written, numeric=True, tone=value.tone)
    if is_figure(value):
        return Fact(label, fmt(value), numeric=True)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f"{owner} ({label!r}) takes a string, a number or a Cell, got: {value!r}"
        )
    return Fact(label, value)


class FactList(Component):
    """
    Label and value rows in one to three columns: inception, AUM, ISIN, fees (#330).

    The box of facts a factsheet, a deal summary or a slide's side column
    carries, without a data table's header row and semantics, or a glossary's
    anchors. With two or three columns the facts flow down, then across, and
    the columns stack on a phone through the skeleton's ``stack-column`` rule.

    Args:
        facts:        A mapping of label to value, in its insertion order, or a
                      list of ``(label, value)`` pairs. A value is plain text, a
                      figure written by ``value_format``, or a
                      :class:`~pyhermes.builder.models.Cell` whose ``tone`` is kept.
        columns:      1, 2 or 3, and no more than there are facts.
        title:        A small heading above the list.
        value_format: How a figure value is written.
        subtitle:     The italic standfirst every component may carry.
        spacing:      Moves ``fact_pad``, above and below each fact, ``gutter``,
                      between columns, and the gaps under the title and the subtitle.
    """

    template_path = "text/fact-list.html"

    SPACING_TOKENS = ("fact_pad", "gutter", "caption_gap", "subtitle_gap")

    def __init__(
        self,
        facts: Mapping[str, Any] | Sequence[tuple[str, Any]],
        columns: int = 1,
        title: str | None = None,
        value_format: Callable[[Any], str] = formats.number,
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        pairs = list(facts.items()) if isinstance(facts, Mapping) else list(facts)
        if not pairs:
            raise ValidationError("FactList requires at least one fact.")
        if not callable(value_format):
            raise ValidationError(
                f"FactList's value_format must be callable, got: {value_format!r}"
            )
        written = []
        for index, pair in enumerate(pairs):
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValidationError(
                    f"fact_list.facts[{index}] must be a (label, value) pair, got: {pair!r}"
                )
            written.append(_coerce_fact(*pair, value_format, index))
        self.facts = written
        self.columns = _check_columns(columns, len(written), "FactList")
        self.title = title
        self.subtitle = subtitle

    def flowed(self) -> list[list[Fact]]:
        """The facts down each column in turn, the earlier columns the longer."""
        depth = math.ceil(len(self.facts) / self.columns)
        return [self.facts[start : start + depth] for start in range(0, len(self.facts), depth)]

    def text(self) -> str:
        """``Inception:  12 March 2019``, the values aligned after the longest label."""
        width = max(len(fact.label) for fact in self.facts) + 1
        rows = "\n".join(f"{(fact.label + ':').ljust(width)}  {fact.value}" for fact in self.facts)
        return self._with_subtitle(wrap(self.title) if self.title else "", rows)

    def render(self, engine: Renderer) -> str:
        """The list, its column shares measured against the cell it fills."""
        engine = respaced(engine, self.spacing, type(self).__name__)
        return engine.render(
            self.template_path, {**self.context(), **_shares(engine, self.columns)}
        )

    def context(self) -> dict[str, Any]:
        return {
            "title": self.title or "",
            "subtitle": self.subtitle,
            "columns": [
                [
                    {
                        "label": fact.label,
                        "value": fact.value,
                        "numeric": fact.numeric,
                        "tone": fact.tone,
                    }
                    for fact in column
                ]
                for column in self.flowed()
            ],
        }


# ──────────────────────────────────────────────────────────────────────
# Timeline (#331)
# ──────────────────────────────────────────────────────────────────────

#: What a timeline event's ``state`` may be, beside unset.
EVENT_STATES = ("done", "next")


@dataclass(frozen=True)
class Event:
    """
    One dated milestone on a :class:`Timeline`.

    Every field is plain text, escaped on the way out: the body too, since a
    raw-HTML field here would be a sixth, and the set is closed at five.

    Attributes:
        date:  When, as the caller writes it: ``14 Oct``, ``2026-10-14``, ``Q4``.
        title: What happens.
        body:  A line of detail; empty for none.
        state: ``"done"``, ``"next"``, or empty for one still to come.
    """

    date: str
    title: str
    body: str = ""
    state: str = ""

    def validate(self, owner: str = "event") -> None:
        for name in ("date", "title"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{owner}.{name} is plain text and required, got: {value!r}")
        if not isinstance(self.body, str):
            raise ValidationError(f"{owner}.body is plain text, got: {type(self.body).__name__}")
        if self.state and self.state not in EVENT_STATES:
            raise ValidationError(
                f"{owner}.state is one of {list(EVENT_STATES)} or unset, got: {self.state!r}"
            )


class Timeline(Component):
    """
    Dated milestones on a vertical rule: an events calendar, a deal's steps (#331).

    Each event is its date, a marker on the rule, then its title and body. The
    marker is a capsule as tall as the title's line, and the rule runs from
    each into the next, unbroken, and stops at the last. A marker's tone and
    fill come from the event's state: a filled accent for done, a ring in the
    accent for next, a ring in the rule's tone for one still to come.
    Vertical in every medium: the Word engine has no horizontal flow that
    survives a phone. On paper no event splits across a sheet.

    Args:
        events:   :class:`Event` objects, or ``(date, title)`` and
                  ``(date, title, body)`` tuples, in the order they happen.
        subtitle: The italic standfirst every component may carry.
        spacing:  Moves ``timeline_gap``, under each event, ``table_cell_pad``,
                  either side of the marker, and ``subtitle_gap``.
    """

    template_path = "text/timeline.html"

    SPACING_TOKENS = ("timeline_gap", "table_cell_pad", "subtitle_gap")

    def __init__(
        self,
        events: Sequence[Event | tuple[str, ...]],
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not events:
            raise ValidationError("Timeline requires at least one event.")
        self.events = [_coerce_event(event, index) for index, event in enumerate(events)]
        self.subtitle = subtitle

    def text(self) -> str:
        """``2026-10-14  Earnings — body (done)``, one event a line, wrapped under its title."""
        width = max(len(event.date) for event in self.events)
        indent = " " * (width + 2)
        lines = []
        for event in self.events:
            line = f"{event.date.ljust(width)}  {event.title}"
            if event.body:
                line += f" — {event.body}"
            if event.state:
                line += f" ({event.state})"
            lines.append(textwrap.fill(line, LINE_WIDTH, subsequent_indent=indent))
        return self._with_subtitle("\n".join(lines))

    def context(self) -> dict[str, Any]:
        last = len(self.events) - 1
        return {
            "subtitle": self.subtitle,
            "events": [
                {
                    "date": event.date,
                    "title": event.title,
                    "body": event.body,
                    "state": event.state,
                    "last": index == last,
                }
                for index, event in enumerate(self.events)
            ],
        }


def _coerce_event(event: object, index: int) -> Event:
    """An :class:`Event`, or a ``(date, title[, body])`` tuple, validated."""
    if isinstance(event, tuple) and len(event) in (2, 3):
        event = Event(*event)
    if not isinstance(event, Event):
        raise ValidationError(
            f"timeline.events[{index}] must be an Event or a (date, title[, body]) tuple, "
            f"got: {event!r}"
        )
    event.validate(f"timeline.events[{index}]")
    return event


# ──────────────────────────────────────────────────────────────────────
# Teaser list (#332)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Teaser:
    """
    One piece of further reading in a :class:`TeaserList`: its title is the link.

    Attributes:
        title:   The piece's title, plain text; the link's label.
        url:     Where it is: http, https, mailto, cid or relative.
        date:    When it was published, as the caller writes it.
        summary: A line saying what it argues, plain text.
        image:   A thumbnail, an :class:`~pyhermes.builder.images.EmailImage`.
        tags:    Labels drawn as a tag row's neutral badges (#327).
    """

    title: str
    url: str
    date: str = ""
    summary: str = ""
    image: EmailImage | None = None
    tags: Sequence[str] = field(default_factory=tuple)

    def validate(self, owner: str = "teaser") -> None:
        for name in ("title", "url"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{owner}.{name} is required, got: {value!r}")
        _validate_url(self.url, f"{owner}.url")
        for name in ("date", "summary"):
            if not isinstance(getattr(self, name), str):
                raise ValidationError(f"{owner}.{name} is plain text")
        if self.image is not None and not isinstance(self.image, EmailImage):
            raise ValidationError(
                f"{owner}.image is an EmailImage, got: {type(self.image).__name__}"
            )
        if isinstance(self.tags, str):
            raise ValidationError(f"{owner}.tags is a list of labels, got a string")
        for position, tag in enumerate(self.tags):
            Badge(tag).validate(f"{owner}.tags[{position}]")

    def text(self) -> str:
        """``Title: https://…``, then its date and summary, then its tags."""
        about = " — ".join(part for part in (self.date, self.summary) if part)
        tags = "Tags: " + ", ".join(self.tags) if self.tags else ""
        lines = (link_line(self.title, self.url), wrap(about), tags)
        return "\n".join(line for line in lines if line)


class TeaserList(Component):
    """
    Linked teasers for further reading, one to three across (#332).

    A research note's "recent publications": a title that links, a date, a
    line of summary, an optional thumbnail and tags, each teaser the same
    shape. Two or three across sit side by side and stack on a phone; on
    paper and on a slide the list is one column, each title still linked.

    Args:
        teasers:  :class:`Teaser` objects, in reading order.
        columns:  1, 2 or 3 across in an email, and no more than there are teasers.
        subtitle: The italic standfirst every component may carry.
        spacing:  Moves ``block_gap``, under each teaser, ``caption_gap``, between
                  a teaser's lines, ``badge_pad_y`` and ``badge_pad_x`` inside each
                  tag, and ``subtitle_gap``.
    """

    template_path = "text/teaser-list.html"

    SPACING_TOKENS = ("block_gap", "caption_gap", "badge_pad_y", "badge_pad_x", "subtitle_gap")

    def __init__(
        self,
        teasers: Sequence[Teaser],
        columns: int = 1,
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not teasers:
            raise ValidationError("TeaserList requires at least one teaser.")
        for index, teaser in enumerate(teasers):
            if not isinstance(teaser, Teaser):
                raise ValidationError(
                    f"teaser_list.teasers[{index}] must be a Teaser, got: {type(teaser).__name__}"
                )
            teaser.validate(f"teaser_list.teasers[{index}]")
        self.teasers = list(teasers)
        self.columns = _check_columns(columns, len(self.teasers), "TeaserList")
        self.subtitle = subtitle

    def images(self) -> list[EmailImage]:
        return [teaser.image for teaser in self.teasers if teaser.image is not None]

    def text(self) -> str:
        return self._with_subtitle(join_blocks(*(teaser.text() for teaser in self.teasers)))

    def render(self, engine: Renderer) -> str:
        """The teasers across in an email, and one column on paper and on a slide."""
        engine = respaced(engine, self.spacing, type(self).__name__)
        across = 1 if engine.medium.paged else self.columns
        scheme = scheme_of(engine)
        # A thumbnail sits beside a lone column's copy, and tops each column across.
        within = int(cell_width_of(engine) - scheme.space.gutter * (across - 1)) // across
        widest = int(scheme.component.teaser_thumb) if across == 1 else within
        teasers = self.teasers
        rows = [teasers[start : start + across] for start in range(0, len(teasers), across)]
        return engine.render(
            self.template_path,
            {
                "subtitle": self.subtitle,
                "across": across,
                **_shares(engine, across),
                "rows": [[self._drawn(teaser, widest) for teaser in row] for row in rows],
            },
        )

    @staticmethod
    def _drawn(teaser: Teaser, widest: int) -> dict[str, Any]:
        """One teaser as the template draws it; a thumbnail no wider than ``widest``."""
        image = teaser.image
        thumb = None
        if image is not None:
            width = min(image.width or widest, widest)
            thumb = {"src": image.src, "alt": image.alt, "width": width, "url": teaser.url}
        return {
            "title": teaser.title,
            "url": teaser.url,
            "date": teaser.date,
            "summary": teaser.summary,
            "image": thumb,
            "tags": [Badge(tag).drawn() for tag in teaser.tags],
        }

    def context(self) -> dict[str, Any]:
        """Unused: the list renders against its medium, which :meth:`render` reads."""
        return {}
