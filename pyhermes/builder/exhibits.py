"""
Exhibits that group (#335): a chart's key stated in markup, and lettered panels in one exhibit.

A :class:`Legend` says in HTML what each colour of a picture means, so the key
survives blocked images and the plain-text part. A :class:`FigureGrid` holds two
to four charts or pictures as one numbered exhibit, each panel lettered and
anchored beneath the grid's own anchor. `.claude/rules/apparatus.md` records the
anchor scheme, and `data-layer.md` why the legend never styles the plot.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from string import ascii_lowercase
from typing import Any

from .apparatus import split_markers, text_markers
from .components import ChartBlock, Component, Exhibit, ImageBlock
from .engine import Renderer, cell_width_of, respaced, scheme_of
from .enums import Tone
from .exceptions import ValidationError
from .images import EmailImage
from .models import Footnote, _validate_color, coerce_notes
from .sizing import Spacing
from .textgen import join_blocks, wrap
from .theming import SERIES_TOKENS, Theme, chart_colors, resolve_theme

# ──────────────────────────────────────────────────────────────────────
# Legend (#337)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LegendEntry:
    """
    One line of a chart's key: a swatch, then what it stands for (#337).

    The swatch names its colour exactly one way: a ``tone``, a ``series``, the
    index of a colour in the theme's chart cycle (what ``chart_style`` hands the
    plot), or a ``color``, which must be one of those chart colours. A hex is
    checked against the document's theme when its section is added, because
    only the document knows its theme.

    Attributes:
        label:  What the colour stands for, plain text.
        tone:   ``positive``, ``negative`` or ``neutral``.
        color:  A ``#RRGGBB`` from the theme's chart colours.
        series: ``0`` for the first chart colour, and so on.
    """

    label: str
    tone: str | None = None
    color: str | None = None
    series: int | None = None

    def validate(self, owner: str) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValidationError(f"{owner} needs a label: plain text, got: {self.label!r}")
        named = [name for name in ("tone", "color", "series") if getattr(self, name) is not None]
        if len(named) != 1:
            raise ValidationError(
                f"{owner} names its colour one way, by tone=, color= or series=; "
                f"got {named or 'none'}"
            )
        if self.tone is not None and self.tone not in tuple(Tone):
            raise ValidationError(f"{owner}.tone is one of {[t.value for t in Tone]}")
        if self.color is not None:
            _validate_color(self.color, f"{owner}.color")
        if self.series is not None and (
            isinstance(self.series, bool)
            or not isinstance(self.series, int)
            or not 0 <= self.series < len(SERIES_TOKENS)
        ):
            raise ValidationError(
                f"{owner}.series indexes the {len(SERIES_TOKENS)} chart colours, "
                f"0 to {len(SERIES_TOKENS) - 1}, got: {self.series!r}"
            )

    def fill(self, theme: Theme) -> str:
        """The swatch's colour in ``theme``."""
        if self.tone is not None:
            return str(getattr(theme.semantic, self.tone))
        if self.color is not None:
            return self.color
        return chart_colors(theme)[self.series or 0]


class Legend(Component):
    """
    A chart's key, stated in HTML: a swatch, then a label, for each series (#337).

    Outlook blocks images by default, and the plain-text part has none, so a key
    drawn into the picture is lost to both. This states it again in markup. It
    never styles the plot: an entry names a theme colour and the caller draws
    the chart in the same theme (``chart_style``), so the two agree because both
    read the theme. A swatch is a shaded inline box the status dot's size, so it
    renders with images off; the Word engine shades a non-breaking space, a small
    square, as it does the dot.

    Place it under a chart in a :class:`~pyhermes.builder.composition.Stack`, beside
    one in a split, or as ``ChartBlock(legend=...)``.

    Args:
        entries: One to twelve :class:`LegendEntry`; a bare label takes the next
                 chart colour in order.
        layout:  ``"row"``, wrapping along a line, or ``"column"``, one a line.
        spacing: Moves ``caption_gap``, after a swatch, and ``gutter``, between
                 entries in a row.
    """

    template_path = "analysis/legend.html"

    SPACING_TOKENS = ("caption_gap", "gutter")

    LAYOUTS = ("row", "column")

    #: The fewest and the most entries a key takes.
    BOUNDS = (1, 12)

    def __init__(
        self,
        entries: Sequence[LegendEntry | str],
        layout: str = "row",
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        low, high = self.BOUNDS
        if isinstance(entries, (str, LegendEntry)) or not low <= len(entries) <= high:
            raise ValidationError(f"Legend takes a list of {low} to {high} entries")
        if layout not in self.LAYOUTS:
            raise ValidationError(
                f"Legend's layout is one of {list(self.LAYOUTS)}, got: {layout!r}"
            )
        coerced = []
        for index, entry in enumerate(entries):
            if isinstance(entry, str):
                entry = LegendEntry(entry, series=index % len(SERIES_TOKENS))
            if not isinstance(entry, LegendEntry):
                raise ValidationError(
                    f"legend.entries[{index}] must be a LegendEntry or a label, "
                    f"got: {type(entry).__name__}"
                )
            entry.validate(f"legend.entries[{index}]")
            coerced.append(entry)
        self.entries = coerced
        self.layout = layout

    def check_theme(self, theme: Theme | str, owner: str = "Legend") -> None:
        """
        Refuse an entry whose colour ``theme`` does not draw a chart in.

        A hex outside the theme's chart colours would key a colour the
        picture cannot contain, and a series past the end of a cycle whose
        tokens coincide names no colour at all.
        """
        colors = chart_colors(resolve_theme(theme))
        for index, entry in enumerate(self.entries):
            if entry.color is not None and entry.color.upper() not in map(str.upper, colors):
                raise ValidationError(
                    f"{owner}'s entry {index} ({entry.label!r}) is {entry.color}, which is not "
                    f"one of this theme's chart colours {list(colors)}. Name it by series= or "
                    "tone=, so the key recolours with the theme."
                )
            if entry.series is not None and entry.series >= len(colors):
                raise ValidationError(
                    f"{owner}'s entry {index} ({entry.label!r}) names series {entry.series}, "
                    f"and this theme draws {len(colors)} distinct chart colours."
                )

    def text(self) -> str:
        """``Key: 10Y gilt, 2Y gilt``."""
        return self._with_subtitle(wrap("Key: " + ", ".join(e.label for e in self.entries)))

    def render(self, engine: Renderer) -> str:
        engine = respaced(engine, self.spacing, type(self).__name__)
        entries = [{"label": e.label, "fill": e.fill(engine.theme)} for e in self.entries]
        return engine.render(self.template_path, {"entries": entries, "layout": self.layout})

    def context(self) -> dict[str, Any]:
        raise NotImplementedError("Legend resolves its swatches against the theme; see render().")


def legends(components: Sequence[Component]) -> list[Legend]:
    """Every legend among ``components`` and the blocks they hold, in reading order."""
    from .components import descendants

    return [component for component in descendants(components) if isinstance(component, Legend)]


# ──────────────────────────────────────────────────────────────────────
# Figure grid (#336)
# ──────────────────────────────────────────────────────────────────────

#: What a panel of a grid may be: a chart or a picture, never a table (#336).
PANEL_KINDS = (ChartBlock, ImageBlock)

#: What a panel may not carry, because the grid carries it once for all of them.
_GRID_OWNED = ("label", "anchor", "caption", "source", "disclosure", "notes", "wrap")


class FigureGrid(Exhibit, Component):
    """
    Two to four charts or pictures as one exhibit, each panel lettered: *Exhibit 3 (a), (b)*.

    **The grid is the exhibit.** The document's walk numbers it once, as it
    would a single chart, and it is listed once in a list of exhibits. Each
    panel prints its letter above it, behind its own ``subtitle`` as its title,
    and anchors as the grid's anchor and its letter (``exhibit-3-a``), so a
    cross-reference to a panel validates and, on paper, reads its page.

    One caption heads the grid, and one source line and one disclosure sit
    beneath every panel, so a panel's own are refused; its legend is kept. The
    panels sit ``columns`` across and stack on a phone; on paper the ``figure``
    break rule keeps the grid on one sheet. The walk stops at the grid, as at
    any exhibit, so its panels are never numbered (`builder-architecture.md`).

    Args:
        panels:     Two to four :class:`ChartBlock` or :class:`ImageBlock`.
        caption:    The heading line, where the number goes.
        label, anchor: Numbering and its ``id``; see :class:`Exhibit`. A grid
                    is an exhibit by default.
        source, disclosure: The attribution and compliance copy for every panel.
        columns:    Panels across, 1 to 4, and no more than there are panels.
        notes:      Footnotes called by ``[^n]`` in ``caption`` or ``source``.
        subtitle:   The italic standfirst every component may carry.
        spacing:    Moves ``gutter``, between panels, ``block_gap``, between
                    rows, and the caption and subtitle gaps.
    """

    template_path = "analysis/figure-grid.html"

    SPACING_TOKENS = ("caption_gap", "subtitle_gap", "gutter", "block_gap")

    PANELS = range(2, 5)

    def __init__(
        self,
        panels: Sequence[ChartBlock | ImageBlock],
        caption: str = "",
        label: str = "Exhibit",
        source: str = "",
        disclosure: str = "",
        columns: int = 2,
        anchor: str = "",
        notes: Sequence[Footnote | str] | None = None,
        subtitle: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        held: list[object] = [panels] if isinstance(panels, Component) else list(panels)
        if len(held) not in self.PANELS:
            raise ValidationError(f"FigureGrid takes 2 to 4 panels, got {len(held)}.")
        checked = [_check_panel(panel, index) for index, panel in enumerate(held)]
        if (
            not isinstance(columns, int)
            or isinstance(columns, bool)
            or not 1 <= columns <= len(held)
        ):
            raise ValidationError(
                f"FigureGrid's columns run 1 to its {len(held)} panels, got: {columns!r}"
            )
        self.validate_exhibit(label, anchor)
        self.notes = coerce_notes(notes, [caption, source], "FigureGrid")
        self.panels = checked
        self.columns = columns
        self.caption = caption
        self.source = source
        self.disclosure = disclosure
        self.subtitle = subtitle

    @staticmethod
    def letter(index: int) -> str:
        """The letter panel ``index`` prints, ``a`` for the first."""
        return ascii_lowercase[index]

    def panel_anchor(self, index: int) -> str:
        """Panel ``index``'s ``id``: the grid's and its letter, or ``""`` when the grid has none."""
        anchor = self.resolved_anchor()
        return f"{anchor}-{self.letter(index)}" if anchor else ""

    def panel_title(self, index: int) -> str:
        """``(a) UK``: the panel's letter, then its own subtitle."""
        subtitle = self.panels[index].subtitle
        return f"({self.letter(index)}) {subtitle}" if subtitle else f"({self.letter(index)})"

    def children(self) -> list[Component]:
        return list(self.panels)

    def images(self) -> list[EmailImage]:
        return [image for panel in self.panels for image in panel.images()]

    def marked_copy(self) -> list[str]:
        return [self.caption, self.source]

    def anchors(self) -> list[tuple[str, str]]:
        owner = self.numbered("") or "an unnumbered FigureGrid"
        return [
            (anchor, f"panel ({self.letter(index)}) of {owner}")
            for index in range(len(self.panels))
            if (anchor := self.panel_anchor(index))
        ]

    def text(self) -> str:
        """The heading once, then each panel's letter and alt text, then the shared copy."""
        lines = []
        for index, panel in enumerate(self.panels):
            line = wrap(f"{self.panel_title(index)} [{panel.image.alt}]")
            legend = getattr(panel, "legend", None)
            lines.append(join_blocks(line, legend.text()) if legend else line)
        return self._with_subtitle(
            wrap(text_markers(self.numbered(self.caption), self.notes, self.citing)),
            *lines,
            wrap(text_markers(self.source, self.notes, self.citing)),
            wrap(self.disclosure),
        )

    def render(self, engine: Renderer) -> str:
        """The grid, each panel's image sized to the cell it gets once the gutters take theirs."""
        engine = respaced(engine, self.spacing, type(self).__name__)
        within, gutter = cell_width_of(engine), scheme_of(engine).space.gutter
        panel_px = max(1, int((within - gutter * (self.columns - 1)) // self.columns))
        share = round((100 - 100 * gutter / within * (self.columns - 1)) / self.columns, 2)
        drawn = [self._panel(engine, index, panel_px) for index in range(len(self.panels))]
        rows = [drawn[start : start + self.columns] for start in range(0, len(drawn), self.columns)]
        return engine.render(
            self.template_path,
            {**self.context(), "rows": rows, "share": f"{share:g}", "columns": self.columns},
        )

    def _panel(self, engine: Renderer, index: int, panel_px: int) -> dict[str, Any]:
        """What the template draws for panel ``index``: its title, its image and its key."""
        panel = self.panels[index]
        legend = getattr(panel, "legend", None)
        last_row = index >= self.columns * (math.ceil(len(self.panels) / self.columns) - 1)
        return {
            "title": self.panel_title(index),
            "anchor": self.panel_anchor(index),
            "src": panel.image.src,
            "alt": panel.image.alt,
            "width": min(panel.image.width or panel_px, panel_px),
            "bordered": isinstance(panel, ChartBlock),
            "link_url": getattr(panel, "link_url", ""),
            "legend": legend.render(engine) if legend else "",
            # On paper and on a slide a row's gap is below it; in an email
            # the panels may stack, so each but the last keeps its gap.
            "gap": not last_row if engine.medium.paged else index < len(self.panels) - 1,
        }

    def context(self) -> dict[str, Any]:
        return {
            "subtitle": self.subtitle,
            "caption_parts": split_markers(self.numbered(self.caption), self.notes, self.citing),
            "caption": self.numbered(self.caption),
            "anchor": self.resolved_anchor(),
            "source_parts": split_markers(self.source, self.notes, self.citing),
            "source": self.source,
            "disclosure": self.disclosure,
        }


def _check_panel(panel: object, index: int) -> ChartBlock | ImageBlock:
    """Refuse a panel that is not a chart or a picture, or that carries what the grid owns."""
    if not isinstance(panel, PANEL_KINDS):
        raise ValidationError(
            f"figure_grid.panels[{index}] must be a ChartBlock or an ImageBlock, got "
            f"{type(panel).__name__}. A table is its own exhibit."
        )
    for name in _GRID_OWNED:
        if getattr(panel, name, None):
            raise ValidationError(
                f"figure_grid.panels[{index}] sets {name}=, which the grid carries once for "
                "every panel. Set it on the FigureGrid; a panel's subtitle is its title."
            )
    if panel.image.decorative:
        raise ValidationError(
            f"figure_grid.panels[{index}] is decorative, and a panel carries information: "
            "give it alt text."
        )
    return panel


__all__ = ["FigureGrid", "Legend", "LegendEntry", "PANEL_KINDS", "legends"]
