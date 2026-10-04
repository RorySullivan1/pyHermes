"""
Data at a glance, drawn without images (#318): a ranking, a series and one figure.

Each is drawn from table cells and theme tokens, so it renders in Outlook with
images blocked and projects to readable text. `.claude/rules/glance.md` records why.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import formats
from .components import Component, CopyAlignment
from .enums import Tone
from .exceptions import ValidationError
from .models import (
    Series,
    _require,
    _validate_tone,
    coerce_series,
    is_figure,
    tone_of,
)
from .sizing import Spacing
from .textgen import wrap


@dataclass(frozen=True)
class BarItem:
    """
    One labelled value in a :class:`BarList`.

    Attributes:
        label: What the bar stands for. Plain text, escaped on the way out.
        value: The raw figure, written by the list's ``value_format``.
        tone:  A ``Tone`` for this bar and its figure; empty takes the list's.
    """

    label: str
    value: Any
    tone: str = ""

    def validate(self) -> None:
        _require(self.label, "bar_item.label")
        if not is_figure(self.value) or self.value != self.value:
            raise ValidationError(
                f"bar_item {self.label!r} must carry a number, got: {self.value!r}"
            )
        _validate_tone(self.tone, "bar_item.tone")


def _coerce_item(item: Any, index: int) -> BarItem:
    """A :class:`BarItem`, or a ``(label, value)`` or ``(label, value, tone)`` tuple."""
    if isinstance(item, BarItem):
        bar = item
    elif isinstance(item, tuple) and len(item) in (2, 3):
        bar = BarItem(*item)
    else:
        raise ValidationError(
            f"bar_list.items[{index}] must be a BarItem or a (label, value[, tone]) "
            f"tuple, got: {item!r}"
        )
    bar.validate()
    return bar


class BarList(Component):
    """
    Ranked horizontal bars from labelled values: top holdings, sector weights (#320).

    Each row is the label, a bar sized to the largest absolute value, and the
    formatted figure. The bar is the data table's in-cell bar, so the markup
    every medium already draws is the one this draws. A list carries none of a
    table's header, rules or data-table semantics: it is a layout table.

    Args:
        items:        ``(label, value)`` or ``(label, value, tone)`` pairs, or
                      :class:`BarItem` objects, in the order they are drawn.
        value_format: How each figure is written, as a column's ``format`` is.
        tone:         ``auto`` (each figure's sign decides), a ``Tone`` for every
                      bar, or ``None`` for the theme's accent.
        diverging:    Draw negatives to the left of a centre rule. Unset, a
                      negative value is refused.
        title:        A small heading above the list.
        subtitle:     The italic standfirst every component may carry.
        spacing:      Moves ``bar_list_pad``, each row's padding above and below,
                      ``table_cell_pad``, the space either side of a bar, and the
                      gaps under the title and the subtitle.
    """

    template_path = "analysis/bar-list.html"

    SPACING_TOKENS = ("bar_list_pad", "table_cell_pad", "caption_gap", "subtitle_gap")

    def __init__(
        self,
        items: Sequence[BarItem | tuple[Any, ...]],
        value_format: Callable[[Any], str] = formats.number,
        tone: str | None = None,
        diverging: bool = False,
        title: str | None = None,
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not items:
            raise ValidationError("BarList requires at least one item.")
        if not callable(value_format):
            raise ValidationError(f"BarList's value_format must be callable, got: {value_format!r}")
        if tone not in (None, "auto"):
            _validate_tone(str(tone), "bar_list.tone")
        self.items = [_coerce_item(item, i) for i, item in enumerate(items)]
        negative = next((item for item in self.items if item.value < 0), None)
        if negative is not None and not diverging:
            raise ValidationError(
                f"BarList item {negative.label!r} is negative ({negative.value!r}); "
                "pass diverging=True to draw it left of a centre rule."
            )
        self.value_format = value_format
        self.tone = tone
        self.diverging = diverging
        self.title = title
        self.subtitle = subtitle

    def _tone(self, item: BarItem) -> str:
        """The item's tone, then the list's, with ``auto`` read off the sign."""
        if item.tone:
            return item.tone
        if self.tone == "auto":
            return str(tone_of(item.value, self.value_format))
        return self.tone or ""

    def widths(self) -> list[int]:
        """Each bar's share of its track in whole percents, from the largest absolute value."""
        end = max(abs(item.value) for item in self.items)
        return [round(100 * abs(item.value) / end) if end else 0 for item in self.items]

    def text(self) -> str:
        """Two aligned columns: the labels, then the formatted figures."""
        labels = [item.label for item in self.items]
        values = [self.value_format(item.value) for item in self.items]
        left = max(map(len, labels))
        right = max(map(len, values))
        rows = "\n".join(
            f"{label.ljust(left)}  {value.rjust(right)}"
            for label, value in zip(labels, values, strict=True)
        )
        title = wrap(self.title) if self.title else ""
        return self._with_subtitle(title, rows)

    def context(self) -> dict[str, Any]:
        return {
            "title": self.title or "",
            "subtitle": self.subtitle,
            "diverging": self.diverging,
            "items": [
                {
                    "label": item.label,
                    "value": self.value_format(item.value),
                    "tone": self._tone(item),
                    "bar": width,
                    "negative": item.value < 0,
                }
                for item, width in zip(self.items, self.widths(), strict=True)
            ],
        }


class Sparkline(Component):
    """
    A short series drawn as cell bars: "up for a third quarter" as a shape (#321).

    Each bar's height is scaled to the series' own lowest and highest. The last
    bar takes the series' tone and the rest the theme's rule, so the eye lands
    where the series ends. The same series rides a card as ``KpiItem(trend=...)``
    and a table as ``Column(kind="sparkline")``.

    Args:
        values:         Two to ``Config.sparkline_max`` figures, oldest first.
        tone:           ``auto`` (last against first), a ``Tone``, or unset for neutral.
        highlight_last: Tone the last bar alone; ``False`` tones every bar.
        value_format:   How the summary writes the lowest, last and highest.
        subtitle:       The italic standfirst every component may carry.
        spacing:        Moves ``caption_gap``, above the summary, and ``subtitle_gap``.
    """

    template_path = "analysis/sparkline.html"

    SPACING_TOKENS = ("caption_gap", "subtitle_gap")

    def __init__(
        self,
        values: Sequence[Any] | Series,
        tone: str | None = None,
        highlight_last: bool = True,
        value_format: Callable[[Any], str] | None = None,
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.series = coerce_series(values, value_format)
        if tone not in (None, "auto"):
            _validate_tone(str(tone), "sparkline.tone")
        self.tone = tone
        self.highlight_last = highlight_last
        self.subtitle = subtitle

    def resolved_tone(self) -> str:
        """The series' tone: stated, read off last against first, or neutral."""
        if self.tone == "auto":
            return str(tone_of(self.series.values[-1] - self.series.values[0]))
        return self.tone or str(Tone.NEUTRAL)

    def text(self) -> str:
        """``min 3.1 · last 4.2 · max 4.2``, written by the series' format."""
        return self._with_subtitle(wrap(self.series.summary()))

    def context(self) -> dict[str, Any]:
        return {
            "spark": self.series.drawn(self.resolved_tone(), self.highlight_last),
            "subtitle": self.subtitle,
        }


class HeroStat(CopyAlignment, Component):
    """
    One figure set very large, with its label and a line of context (#322).

    For a statement slide, a brochure's cover figure or an email's lead number,
    where a one-card ``CardGroup`` reads as a lonely card. It has no border and
    no ground of its own: it sits on its section's surface, so a dark section
    turns its type light through the ground's rebinding (#266). The value is set
    at ``hero_value``, larger than ``kpi_value`` in every density.

    Args:
        value:   The figure, already written. Plain text.
        label:   What it measures, set small above the context.
        context: A line saying why it matters; empty for none.
        tone:    A ``Tone`` for the figure; unset, the theme's heading colour.
        align:   ``left``, ``center`` or ``right``; unset inherits the section's.
        spacing: Moves ``card_value_gap``, under the figure, and ``card_label_gap``,
                 under the label.
    """

    template_path = "analysis/hero-stat.html"

    SPACING_TOKENS = ("card_value_gap", "card_label_gap")

    def __init__(
        self,
        value: str,
        label: str,
        context: str | None = None,
        tone: str | None = None,
        align: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        _require(value, "hero_stat.value")
        _require(label, "hero_stat.label")
        _validate_tone(tone or "", "hero_stat.tone")
        self.value = value
        self.label = label
        self.context_line = context or ""
        self.tone = tone or ""
        self.align = self.validate_alignment(align)

    @classmethod
    def from_number(
        cls,
        label: str,
        value: Any,
        fmt: Callable[[Any], str] = formats.number,
        *,
        context: str | None = None,
        tone: str | None = None,
        good: str = "up",
        align: str | None = None,
    ) -> HeroStat:
        """
        A figure written with ``fmt``, on ``KpiItem.from_number``'s pattern.

        Untoned by default: one figure set alone is a statement, not a move.
        ``tone="auto"`` reads its sign through ``tone_of``, and ``good="down"``
        flips it for a figure whose rise is bad news.
        """
        if good not in ("up", "down"):
            raise ValidationError(f"good must be 'up' or 'down', got: {good!r}")
        if tone == "auto":
            moved = tone_of(value, fmt)
            flip = {Tone.POSITIVE: Tone.NEGATIVE, Tone.NEGATIVE: Tone.POSITIVE}
            tone = str(flip.get(moved, moved) if good == "down" else moved)
        return cls(fmt(value), label, context=context, tone=tone, align=align)

    def text(self) -> str:
        """``38 bps — 2s10s, steepest since 2022``."""
        line = f"{self.value} — {self.label}"
        return self._with_subtitle(
            wrap(f"{line}, {self.context_line}" if self.context_line else line)
        )

    def context(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "label": self.label,
            "context": self.context_line,
            "tone": self.tone,
            **self.alignment_context(),
        }
