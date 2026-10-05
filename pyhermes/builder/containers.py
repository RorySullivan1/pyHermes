"""
Containers — the layout geometry of one section.

A container wraps rendered component fragments and produces the ``<tr>``
block that drops into the body table: full width, a two- or three-column
split, optionally a highlight band.

**Column widths are computed, never written down.** A ratio's own name is its
weights, and :func:`~pyhermes.builder.sizing.column_layout` splits the active
scheme's content width by them — which is why one template serves every
split::

    section = FullWidth(content=CardGroup([...]), title="Market Snapshot")
    html = section.render(engine)
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import ClassVar

from pyhermes.config import get_config

from .apparatus import UNRESOLVED, Citing, slugify, split_markers, text_markers, validate_anchor
from .components import Component, descendants
from .composition import refuse_numbered
from .engine import Renderer, grounded, on_ground, rebind, respaced, scheme_of
from .enums import TextAlign, ThreeColumnRatio, TwoColumnRatio, VerticalAlign
from .exceptions import ValidationError
from .images import EmailImage, ImageAsset
from .medium import check_media, walking_medium
from .models import (
    Badge,
    Footnote,
    _validate_align,
    _validate_color,
    check_kicker,
    check_valign,
    coerce_badge,
    coerce_notes,
)
from .sizing import (
    PHONE_FLOOR,
    STANDARD_SIZES,
    SizeScheme,
    Spacing,
    check_unstacked,
    coerce_spacing,
    coerce_stack,
    column_layout,
    shares,
)
from .textgen import join_blocks, join_sections, underline, wrap


class Container:
    """
    Abstract base for all layout containers.

    Subclasses set ``template_path`` and implement ``context()``.
    Every container may optionally have a section title, a
    background-color override and an ``align`` for its copy.

    **Alignment is inherited, not resolved (#126).** ``align`` is declared
    on this container's *cells* and reaches the prose inside by ordinary
    CSS inheritance — there is deliberately no ``resolved_align()`` and
    nothing is threaded into the components, so ``Component.render()``
    still takes one argument. That differs from ``Column``/``Cell``
    (#117, #118), which need a *computed* value because
    :func:`~pyhermes.builder.textgen.table` reads it too; prose alignment has
    one reader and projects to nothing.

    Two things make that mechanism sound rather than hopeful:

    * **Every structural component already declares its own alignment**,
      so inheritance stops where it should. A KPI cell is centred and a
      table column resolves from its ``kind`` whatever the section says.
      Nothing arranges this; ``TestTheBoundaryHolds`` is what keeps a
      future template edit from removing one of those declarations and
      letting a section leak in.
    * **The declaration is doubled.** ``text-align`` is an inherited
      property — [MS-CSS21] section 16.2 records it as ``Inherited: yes``
      for Microsoft's own engine, and lists no deviation from that (only
      that the ``inherit`` *keyword* is unsupported in Quirks and IE7
      modes, which this package never writes). Outlook Classic's Word
      engine is a different renderer from the one that document
      specifies, so #125 also put the ``align`` **attribute** on these
      same cells; the attribute aligns a cell's content directly and needs
      no inheritance at all. That is why #125 was ordered first — the
      belt-and-braces was in place before anything depended on it.

    **A split's cells fill their columns since #129.** They did not when
    ``align`` first landed: ``display:inline-block`` on the column stopped
    it being a table box, so the cell inside shrink-wrapped to its own copy
    and a split's alignment had no room to show. ``inline-table`` fixed it,
    and a browser test holds it — see ``columns.html`` for why the obvious
    ``width="100%"`` does not work.

    Raises:
        ValidationError: If ``background_color`` is not a ``#RRGGBB`` hex color.
    """

    template_path: str = ""

    #: The spacing tokens this container's own template reads, and so the
    #: only ones its ``spacing`` may move (#213).
    SPACING_TOKENS: ClassVar[tuple[str, ...]] = ()

    #: This section's spacing override, or ``None`` for the document's.
    spacing: Spacing | None = None

    #: The appendix letter this section opens, set by the document's walk (#309).
    letter: str = ""

    #: The row ``id`` a kept section carries on paper, set by the document's walk (#364).
    kept_mark: str = ""

    #: How a citation in ``source`` is spelled, handed down by the document's walk (#338).
    citing: Citing = UNRESOLVED

    def __init__(
        self,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        text_color: str | None = None,
        border: bool = False,
        border_color: str | None = None,
        keep_together: bool = False,
        break_before: bool = False,
        badge: Badge | str | None = None,
        kicker: str | None = None,
        source: str | None = None,
        as_of: str | None = None,
        source_notes: Sequence[Footnote | str] | None = None,
    ):
        for value, name in (
            (background_color, "background_color"),
            (text_color, "text_color"),
            (border_color, "border_color"),
        ):
            if value:
                _validate_color(value, f"container.{name}")
        if border_color and not border:
            raise ValidationError("container.border_color needs border=True to draw anything.")
        _validate_align(align or "", "container.align")
        validate_anchor(anchor or "", "container.anchor")
        self.title = title
        self.background_color = background_color
        self.text_color = text_color
        self.border = border
        self.border_color = border_color
        self.highlight = highlight
        self.align = align
        self.anchor = anchor
        self.spacing = coerce_spacing(spacing, self.spacing_tokens(), self._owner())
        for flag, name in ((keep_together, "keep_together"), (break_before, "break_before")):
            if not isinstance(flag, bool):
                raise ValidationError(f"{self._owner()}'s {name} is True or False, got: {flag!r}")
        self.keep_together = keep_together
        self.break_before = break_before
        self.badge = coerce_badge(badge, f"{type(self).__name__}.badge")
        if self.badge is not None and not title:
            raise ValidationError(
                f"{self._owner()}'s badge sits after its title (#325); give the section a title"
            )
        self.kicker = check_kicker(kicker, title, self._owner())
        self._check_source(source, as_of)
        self.source = source or ""
        self.as_of = as_of or ""
        self.source_notes = coerce_notes(source_notes, [self.source], f"{self._owner()}'s source")

    def _check_source(self, source: str | None, as_of: str | None) -> None:
        """Refuse a source line that is not plain text, and a date with no source to date."""
        for name, value in (("source", source), ("as_of", as_of)):
            if value is not None and not isinstance(value, str):
                raise ValidationError(
                    f"{self._owner()}'s {name} is plain text, got: {type(value).__name__}"
                )
        if as_of and not source:
            raise ValidationError(f"{self._owner()} has an as_of date but no source to date")

    def footnotes(self) -> list[Footnote]:
        """The notes this section's own source line calls (#338); its blocks report theirs."""
        return list(self.source_notes)

    def marked_copy(self) -> list[str]:
        """This section's own copy that may carry a marker: its source line (#338)."""
        return [self.source] if self.source else []

    def source_text(self) -> str:
        """``Source: X as of Y``, the source line as the text part prints it, or ``""``."""
        source = text_markers(self.source, self.source_notes, self.citing)
        return f"{source} as of {self.as_of}" if self.as_of else source

    @classmethod
    def spacing_tokens(cls) -> tuple[str, ...]:
        """The tokens a ``spacing`` on this class may move."""
        return cls.SPACING_TOKENS

    def _owner(self) -> str:
        """How errors name this section."""
        title = getattr(self, "title", None)
        return f"{type(self).__name__} {title!r}" if title else type(self).__name__

    def _slot(self, name: str, value: object) -> Component:
        """``value`` if it is a component, else a ``ValidationError`` naming what to use instead."""
        if isinstance(value, Component):
            return value
        got = type(value).__name__
        if isinstance(value, Container):
            hint = "A section cannot sit inside a section; to split a cell, use Columns([...])."
        elif isinstance(value, (list, tuple)):
            hint = "To put several blocks in one cell, use Stack([...])."
        else:
            hint = "Wrap text in a TextBlock."
        owner = type(self).__name__
        raise ValidationError(f"{owner}.{name} must be a Component, got {got}. {hint}")

    def _spaced(self, engine: Renderer) -> Renderer:
        """``engine`` as this section and everything inside it render against."""
        engine = respaced(engine, self.spacing, self._owner())
        if self.align:
            # What places a block sized to a share of its cell (#357).
            engine = rebind(engine, placement=str(self.align))
        return grounded(engine, engine.theme.on_ground(self.background_color, self.text_color))

    def opening(self) -> Container:
        """This section without its leading break, for a body that already opens a sheet."""
        opened = copy.copy(self)
        opened.break_before = False
        return opened

    def heading(self) -> str:
        """The title as printed: behind its appendix letter when the walk gave it one."""
        if self.letter and self.title:
            return get_config().appendix_heading.format(letter=self.letter, title=self.title)
        return self.title or ""

    def resolved_anchor(self) -> str:
        """The ``id`` this section's title carries: the caller's, or a slug of the title."""
        if not self.title:
            return ""
        return self.anchor or slugify(self.title)

    def _base_context(self, engine: Renderer) -> dict:
        """
        Shared context keys injected into every container template.

        ``section_title`` is always injected — the templates gate on it with
        ``{% if section_title %}``, and under ``StrictUndefined`` an *undefined*
        name raises rather than testing falsey.  Empty string = no title.

        ``background_color`` is injected only when set: the templates supply
        their own tint via ``| default(...)``, which only substitutes for an
        undefined value, not an empty one — and that default now depends on
        ``highlight``, so the flag is always injected too.
        """
        ctx: dict = {
            "section_title": self.heading(),
            "section_badge": self.badge.drawn() if self.badge else None,
            # On a ground of its own the accent may not read, so it takes the rebound type.
            "section_kicker": (
                {"text": self.kicker, "grounded": on_ground(engine)} if self.kicker else None
            ),
            "highlight": self.highlight,
        }
        if self.background_color:
            ctx["background_color"] = self.background_color
        # Always injected, empty when unset: the templates gate on it with
        # ``{% if %}``, and under StrictUndefined an *undefined* name raises
        # rather than testing falsey — ``section_title``'s reasoning exactly.
        ctx["section_align"] = self.align or ""
        ctx["section_anchor"] = self.resolved_anchor()
        ctx["section_border"] = (
            (self.border_color or engine.theme.palette.rule) if self.border else ""
        )
        ctx["section_break"] = self._break_style(engine)
        ctx["section_kept"] = self.kept_mark if ctx["section_break"] and self.keep_together else ""
        ctx["section_source"] = (
            split_markers(self.source, self.source_notes, self.citing) if self.source else []
        )
        ctx["section_as_of"] = self.as_of
        return ctx

    def _break_style(self, engine: Renderer) -> str:
        """The section row's break declarations on paper, both spellings; empty elsewhere (#364)."""
        if not engine.medium.paged:
            return ""
        rules = []
        if self.break_before:
            rules.append("break-before:page; page-break-before:always;")
        if self.keep_together:
            rules.append("break-inside:avoid; page-break-inside:avoid;")
        return " ".join(rules)

    def components(self) -> list[Component]:
        """
        Return the components occupying this container's slots.

        Subclasses list their own slots — one for a single column, the
        filled columns for a split. Used to walk the section tree without
        rendering it, which is how the email collects its asset manifest.
        """
        raise NotImplementedError

    def assets(self) -> list[ImageAsset]:
        """Return the attachment manifest entries from every component here."""
        return [asset for component in self.components() for asset in component.assets()]

    def images(self) -> list[EmailImage]:
        """Every image in this section: its components', and any it carries itself."""
        return [image for component in self.components() for image in component.images()]

    def text(self) -> str:
        """
        This section as plain text: its title, then its components (#109).

        Implemented **once, here**, because :meth:`components` already returns
        the occupied slots in reading order — which is what makes a split
        collapse to sequential blocks for free: plain text has one column, so
        a ``TwoColumn``'s left then right simply run top to bottom, and no
        subclass needs its own projection.

        ``highlight``, ``background_color`` and the column ratio project to
        nothing. They are presentation, and a plain-text part has no surface
        for them to sit on.
        """
        return join_blocks(
            self.headed(), *(c.text() for c in self.components()), wrap(self.source_text())
        )

    def headed(self) -> str:
        """The title underlined, and the kicker on the line above it (#333)."""
        title = underline(self.titled())
        return f"{self.kicker}\n{title}" if title and self.kicker else title

    def titled(self) -> str:
        """The title as the text part prints it: the heading, and its badge after it (#325)."""
        heading = self.heading()
        return f"{heading} {self.badge.text()}" if heading and self.badge else heading

    def render(self, engine: Renderer) -> str:
        raise NotImplementedError


def _in_cell(engine: Renderer, width: int) -> Renderer:
    """``engine`` bound to the content width of the cell it renders into, for a nested split."""
    return rebind(engine, cell_width=width)


def _is_weight(value: object) -> bool:
    """A positive int or float, and not a bool, which is an int to Python."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


class _SplitContainer(Container):
    """
    Shared machinery for every multi-column container.

    Two things live here rather than in ``TwoColumn`` and ``ThreeColumn``
    separately, because they were the same in both: the ratio-to-weights
    reading, and building the per-column context the one column template
    consumes.
    """

    #: One template for every split. The ratio no longer selects a file —
    #: it selects *numbers*, which is the whole point of #42.
    template_path = "common/containers/columns.html"

    SPACING_TOKENS: ClassVar[tuple[str, ...]] = (
        "section_title_top",
        "section_title_bottom",
        "caption_gap",
        "column_top",
        "column_bottom",
        "column_pad_x",
        "column_pad_x_narrow",
        "gutter",
        "pad_x",
    )

    #: The split this container was built with: a preset's name (or its enum
    #: member), or a tuple of weights (#264). Set by each subclass's ``__init__``.
    ratio: str | tuple[int | float, ...]

    #: The named splits this container accepts as a string.
    _presets: ClassVar[tuple[str, ...]]

    #: How many columns this split has, which is how many weights it takes.
    COUNT: ClassVar[int]

    #: How the columns stack on a phone: ``"natural"``, ``"reverse"`` or ``False`` (#362, #363).
    stack: str | bool = "natural"

    #: Where each column sits in the row's height, on paper only (#356).
    valign: str = "top"

    @classmethod
    def _check_ratio(cls, ratio: object) -> str | tuple[int | float, ...]:
        """
        ``ratio`` as stored: a preset string as given, or weights as a tuple.

        A StrEnum member equals and hashes as its string value, so the preset
        test accepts both. Weights must be one positive number per column, and
        none may compute narrower than ``Config.min_column_px`` at the email frame.
        """
        if isinstance(ratio, str):
            if ratio not in cls._presets:
                raise ValidationError(
                    f"Unsupported ratio '{ratio}'. Use one of {[str(p) for p in cls._presets]}, "
                    f"or {cls.COUNT} weights such as {(3,) * (cls.COUNT - 1) + (2,)}."
                )
            return ratio
        weights = tuple(ratio) if isinstance(ratio, Sequence) else ()
        if len(weights) != cls.COUNT or not all(_is_weight(weight) for weight in weights):
            raise ValidationError(
                f"{cls.__name__} takes {cls.COUNT} positive weights, got: {ratio!r}"
            )
        floor = get_config().min_column_px
        for index, column in enumerate(column_layout(weights, STANDARD_SIZES)):
            if column.width < floor:
                raise ValidationError(
                    f"weights {weights} make column {index + 1} {column.width}px wide at the "
                    f"680px email frame, below Config.min_column_px ({floor})."
                )
        return weights

    def _check_stack(self, stack: object) -> str | bool:
        """
        How this split stacks on a phone (#362, #363), refusing ``False`` where a column won't fit.

        Unstacked, the split keeps its proportions at the phone floor inside
        the band's inset, so each column must stay above ``Config.min_column_px``
        there, as it must at the 680px frame.
        """
        stack = coerce_stack(stack, type(self).__name__)
        if stack is False:
            frame, gutter = STANDARD_SIZES.frame, STANDARD_SIZES.space.gutter
            phone = PHONE_FLOOR - 2 * frame.pad_x
            available = phone * (1 - gutter * (self.COUNT - 1) / frame.inner)
            check_unstacked(self._weights(self.ratio), available, type(self).__name__)
        return stack

    def _check_nested(self) -> None:
        """Refuse an unstacked ``Columns`` in an unstacked split: two levels never fit a phone."""
        if self.stack is not False:
            return
        for inner in descendants(self.components()):
            if getattr(inner, "stack", None) is False:
                raise ValidationError(
                    f"{type(self).__name__} with stack=False holds a Columns with stack=False; "
                    "one of the two must stack on a phone."
                )

    @staticmethod
    def _weights(ratio: str | tuple[int | float, ...]) -> list[int | float]:
        """
        A preset's own name is its weights: ``"25-25-50"`` -> ``[25, 25, 50]``.

        No lookup table, because a table would be a second place for the
        split to be written down and therefore a second place to be wrong.
        :func:`~pyhermes.builder.sizing.column_layout` normalises by the sum, so
        ``"33-33-33"`` is exact thirds rather than 99% of the frame.
        """
        if isinstance(ratio, str):
            return [int(part) for part in ratio.split("-")]
        return list(ratio)

    def _render_split(self, engine: Renderer, slots: Sequence[Component | None]) -> str:
        """Each slot rendered into its column's content width, then the split around them."""
        engine = self._spaced(engine)
        scheme = scheme_of(engine)
        geometry = column_layout(self._weights(self.ratio), scheme)
        # An omitted column is an empty cell, not a missing one: the geometry holds either way.
        contents = [
            slot.render(_in_cell(engine, int(col.width - col.pad_left - col.pad_right)))
            if slot
            else ""
            for slot, col in zip(slots, geometry, strict=True)
        ]
        return engine.render(self.template_path, self._column_context(engine, contents, scheme))

    def _column_context(self, engine: Renderer, contents: list[str], scheme: SizeScheme) -> dict:
        geometry = column_layout(self._weights(self.ratio), scheme)
        widths = [column.width for column in geometry]
        *percent, gutter = shares(widths, scheme.space.gutter, scheme.frame.inner)
        ctx = self._base_context(engine)
        columns = [
            {
                "width": column.width,
                "share": share,
                "pad_left": column.pad_left,
                "pad_right": column.pad_right,
                "content": content,
            }
            for column, share, content in zip(geometry, percent, contents, strict=True)
        ]
        # Nothing stacks on paper, so a reversed or unstacked split prints as written.
        stack = self.stack if not engine.medium.paged else "natural"
        ctx["stack"] = "fixed" if stack is False else stack
        ctx["gutter_share"] = gutter
        ctx["valign"] = self.valign
        ctx["columns"] = columns[::-1] if stack == "reverse" else columns
        return ctx


class FullWidth(Container):
    """
    Single-column container spanning the frame's full content width.

    Args:
        content:          A Component instance to render inside the container.
        title:            Optional section heading.
        background_color: Optional hex background override.
        anchor:           The title's ``id``; a slug of the title when unset.
        spacing:          A :class:`~pyhermes.builder.sizing.Spacing`, or a mapping of
                          the ``SPACING_TOKENS`` it moves, for this section.
        badge:            A :class:`~pyhermes.builder.models.Badge`, or a label, after
                          the title (#325); every section takes one.
        kicker:           A short label set above the title, plain text (#333); every
                          section takes one, and a titled one only.
        source, as_of:    One fine-print line at the section's foot, for every block in
                          it (#338): plain text, ``[^n]`` and ``[@key]`` allowed, as on an
                          exhibit's source. ``source_notes`` are the notes it calls. Every
                          section takes one.
    """

    template_path = "common/containers/full-width.html"

    SPACING_TOKENS: ClassVar[tuple[str, ...]] = (
        "section_title_top",
        "section_title_bottom",
        "caption_gap",
        "content_top",
        "content_bottom",
        "pad_x",
    )

    def __init__(
        self,
        content: Component,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        text_color: str | None = None,
        border: bool = False,
        border_color: str | None = None,
        keep_together: bool = False,
        break_before: bool = False,
        badge: Badge | str | None = None,
        kicker: str | None = None,
        source: str | None = None,
        as_of: str | None = None,
        source_notes: Sequence[Footnote | str] | None = None,
    ):
        super().__init__(
            title,
            background_color,
            highlight,
            align,
            anchor,
            spacing,
            text_color=text_color,
            border=border,
            border_color=border_color,
            keep_together=keep_together,
            break_before=break_before,
            badge=badge,
            kicker=kicker,
            source=source,
            as_of=as_of,
            source_notes=source_notes,
        )
        self.content = self._slot("content", content)

    def components(self) -> list[Component]:
        return [self.content]

    def render(self, engine: Renderer) -> str:
        engine = self._spaced(engine)
        ctx = self._base_context(engine)
        ctx["content"] = self.content.render(_in_cell(engine, int(scheme_of(engine).frame.inner)))
        ctx["flow_columns"] = 0
        return engine.render(self.template_path, ctx)


class FlowedColumns(FullWidth):
    """
    One block of prose flowed through columns of one measure (#189).

    **Not a split.** :class:`TwoColumn` and :class:`ThreeColumn` place
    *separate components* side by side in fixed-ratio cells; this flows *one*
    component, usually a :class:`~pyhermes.builder.components.TextBlock`, down one
    column and on into the next, as a newspaper sets copy. Use a split to
    put a chart beside its commentary; use this to set a long passage.

    **Paper only in effect.** CSS multi-column does not survive Outlook's
    Word engine, so in an email this renders byte for byte as a
    :class:`FullWidth` holding the same content: one column.

    Args:
        content: The component to flow.
        count:   How many columns, two to four.
        title, background_color, highlight, align, anchor, spacing: As on ``FullWidth``.
    """

    #: The columns a measure can hold at the paged frame widths before a line
    #: falls under a readable length.
    COUNTS = range(2, 5)

    #: ``FullWidth``'s, and the gap between the flowed columns.
    SPACING_TOKENS = (*FullWidth.SPACING_TOKENS, "gutter")

    def __init__(
        self,
        content: Component,
        count: int = 2,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        text_color: str | None = None,
        border: bool = False,
        border_color: str | None = None,
        keep_together: bool = False,
        break_before: bool = False,
        badge: Badge | str | None = None,
        kicker: str | None = None,
        source: str | None = None,
        as_of: str | None = None,
        source_notes: Sequence[Footnote | str] | None = None,
    ):
        super().__init__(
            content,
            title,
            background_color,
            highlight,
            align,
            anchor,
            spacing,
            text_color=text_color,
            border=border,
            border_color=border_color,
            keep_together=keep_together,
            break_before=break_before,
            badge=badge,
            kicker=kicker,
            source=source,
            as_of=as_of,
            source_notes=source_notes,
        )
        if isinstance(count, bool) or count not in self.COUNTS:
            raise ValidationError(
                f"FlowedColumns takes {self.COUNTS.start} to {self.COUNTS.stop - 1} "
                f"columns, got: {count!r}"
            )
        self.count = count

    def render(self, engine: Renderer) -> str:
        engine = self._spaced(engine)
        ctx = self._base_context(engine)
        scheme = scheme_of(engine)
        flowing = self.count if engine.medium.paged else 1
        # On paper the content is set one flowed column wide, which is what a measure reads (#358).
        within = (scheme.frame.inner - scheme.space.gutter * (flowing - 1)) / flowing
        ctx["content"] = self.content.render(_in_cell(engine, int(within)))
        ctx["flow_columns"] = self.count if engine.medium.paged else 0
        return engine.render(self.template_path, ctx)


class TwoColumn(_SplitContainer):
    """
    Two-column container with configurable split ratio.

    Slots are positional: ``left`` and ``right`` are the visual columns.
    Supported ratios (widths shown at the shipped 680 px frame, and
    *derived* from it rather than hardcoded — a different frame width
    yields different columns from the same ratio):
        ``"50-50"``  — equal 300 px columns
        ``"30-70"``  — 180 px left + 420 px right
        ``"70-30"``  — 420 px left + 180 px right

    At least one of ``left`` / ``right`` must be supplied; an omitted column
    renders as an empty cell.

    Args:
        ratio:            Column ratio string.
        left:             Component rendered in the left column.
        right:            Component rendered in the right column.
        title:            Optional section heading.
        background_color: Optional hex background override (``#RRGGBB``).
        anchor, spacing:  As on ``FullWidth``.
        valign:           ``"top"``, ``"middle"`` or ``"bottom"``, on paper; an email refuses it.

    Raises:
        ValidationError: On an unsupported ratio, a non-hex background color,
            or when both columns are omitted.
    """

    _presets = tuple(TwoColumnRatio)
    COUNT = 2

    def __init__(
        self,
        ratio: str | TwoColumnRatio | Sequence[int | float] = TwoColumnRatio.EQUAL,
        left: Component | None = None,
        right: Component | None = None,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        text_color: str | None = None,
        border: bool = False,
        border_color: str | None = None,
        keep_together: bool = False,
        break_before: bool = False,
        badge: Badge | str | None = None,
        kicker: str | None = None,
        stack: str | bool = "natural",
        valign: str | VerticalAlign = "top",
        source: str | None = None,
        as_of: str | None = None,
        source_notes: Sequence[Footnote | str] | None = None,
    ):
        super().__init__(
            title,
            background_color,
            highlight,
            align,
            anchor,
            spacing,
            text_color=text_color,
            border=border,
            border_color=border_color,
            keep_together=keep_together,
            break_before=break_before,
            badge=badge,
            kicker=kicker,
            source=source,
            as_of=as_of,
            source_notes=source_notes,
        )
        self.ratio = self._check_ratio(ratio)
        self.stack = self._check_stack(stack)
        self.valign = check_valign(valign, type(self).__name__)
        if left is None and right is None:
            raise ValidationError("TwoColumn requires at least one of 'left' or 'right'.")
        self.left = None if left is None else self._slot("left", left)
        self.right = None if right is None else self._slot("right", right)
        self._check_nested()

    def components(self) -> list[Component]:
        return [c for c in (self.left, self.right) if c is not None]

    def render(self, engine: Renderer) -> str:
        return self._render_split(engine, (self.left, self.right))


class ThreeColumn(_SplitContainer):
    """
    Three-column container with configurable split ratio.

    Slots are positional: ``left`` / ``center`` / ``right`` are always the
    visually left, middle, and right columns. The ``ratio`` string (or a
    :class:`~pyhermes.builder.enums.ThreeColumnRatio` member) sets the widths.

    Supported ratios (widths shown at the shipped 680 px frame — each
    totals the 616 px content width across two 16 px gutters, and each is
    derived from the frame rather than hardcoded):
        ``"33-33-33"``  — equal thirds (195 / 194 / 195 px)
        ``"50-25-25"``  — wide left    (292 / 146 / 146 px)
        ``"25-50-25"``  — wide centre  (146 / 292 / 146 px)
        ``"25-25-50"``  — wide right   (146 / 146 / 292 px)

    At least one of ``left`` / ``center`` / ``right`` must be supplied; an
    omitted column renders as an empty cell.

    Args:
        ratio:            Column ratio string or ``ThreeColumnRatio`` member.
        left:             Component rendered in the left column.
        center:           Component rendered in the centre column.
        right:            Component rendered in the right column.
        title:            Optional section heading.
        background_color: Optional hex background override (``#RRGGBB``).
        anchor, spacing, valign: As on ``TwoColumn``.

    Raises:
        ValidationError: On an unsupported ratio, a non-hex background color,
            or when all three columns are omitted.
    """

    _presets = tuple(ThreeColumnRatio)
    COUNT = 3

    def __init__(
        self,
        ratio: str | ThreeColumnRatio | Sequence[int | float] = ThreeColumnRatio.EQUAL,
        left: Component | None = None,
        center: Component | None = None,
        right: Component | None = None,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        text_color: str | None = None,
        border: bool = False,
        border_color: str | None = None,
        keep_together: bool = False,
        break_before: bool = False,
        badge: Badge | str | None = None,
        kicker: str | None = None,
        stack: str | bool = "natural",
        valign: str | VerticalAlign = "top",
        source: str | None = None,
        as_of: str | None = None,
        source_notes: Sequence[Footnote | str] | None = None,
    ):
        super().__init__(
            title,
            background_color,
            highlight,
            align,
            anchor,
            spacing,
            text_color=text_color,
            border=border,
            border_color=border_color,
            keep_together=keep_together,
            break_before=break_before,
            badge=badge,
            kicker=kicker,
            source=source,
            as_of=as_of,
            source_notes=source_notes,
        )
        self.ratio = self._check_ratio(ratio)
        self.stack = self._check_stack(stack)
        self.valign = check_valign(valign, type(self).__name__)
        if left is None and center is None and right is None:
            raise ValidationError(
                "ThreeColumn requires at least one of 'left', 'center', or 'right'."
            )
        self.left = None if left is None else self._slot("left", left)
        self.center = None if center is None else self._slot("center", center)
        self.right = None if right is None else self._slot("right", right)
        self._check_nested()

    def components(self) -> list[Component]:
        return [c for c in (self.left, self.center, self.right) if c is not None]

    def render(self, engine: Renderer) -> str:
        return self._render_split(engine, (self.left, self.center, self.right))


class FourColumn(_SplitContainer):
    """
    Four columns side by side: a row of small charts, logos or figures (#264).

    Slots are a list, left to right, because four named slots read worse than
    a position. ``None`` leaves a column empty, and at least one must be
    filled. Equal quarters by default (142px each at the 680px frame); pass
    four weights for anything else. On a phone the columns stack, left first.

    Args:
        columns:          Four components, or ``None`` for an empty column.
        ratio:            ``"25-25-25-25"``, or four positive weights.
        title, background_color, highlight, align, anchor, spacing, valign: As on
                          ``TwoColumn``.
    """

    _presets = ("25-25-25-25",)
    COUNT = 4

    #: A split's tokens less ``column_pad_x``: a column wide enough to take it
    #: (``frame.narrow_column``) leaves three others under ``Config.min_column_px``.
    SPACING_TOKENS = tuple(
        token for token in _SplitContainer.SPACING_TOKENS if token != "column_pad_x"
    )

    def __init__(
        self,
        columns: Sequence[Component | None],
        ratio: str | Sequence[int | float] = "25-25-25-25",
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        text_color: str | None = None,
        border: bool = False,
        border_color: str | None = None,
        keep_together: bool = False,
        break_before: bool = False,
        badge: Badge | str | None = None,
        kicker: str | None = None,
        stack: str | bool = "natural",
        valign: str | VerticalAlign = "top",
        source: str | None = None,
        as_of: str | None = None,
        source_notes: Sequence[Footnote | str] | None = None,
    ):
        super().__init__(
            title,
            background_color,
            highlight,
            align,
            anchor,
            spacing,
            text_color=text_color,
            border=border,
            border_color=border_color,
            keep_together=keep_together,
            break_before=break_before,
            badge=badge,
            kicker=kicker,
            source=source,
            as_of=as_of,
            source_notes=source_notes,
        )
        self.ratio = self._check_ratio(ratio)
        self.stack = self._check_stack(stack)
        self.valign = check_valign(valign, type(self).__name__)
        slots = list(columns)
        if len(slots) != self.COUNT:
            raise ValidationError(f"FourColumn takes four columns, got {len(slots)}.")
        if all(slot is None for slot in slots):
            raise ValidationError("FourColumn requires at least one filled column.")
        for index, slot in enumerate(slots):
            if slot is not None and not isinstance(slot, Component):
                raise ValidationError(
                    f"FourColumn column {index + 1} must be a Component or None, "
                    f"got {type(slot).__name__}."
                )
        self.columns = slots
        self._check_nested()

    def components(self) -> list[Component]:
        return [c for c in self.columns if c is not None]

    def render(self, engine: Renderer) -> str:
        return self._render_split(engine, self.columns)


class Appendices(Container):
    """
    The back of a document, lettered: each titled section is an appendix (#309).

    A section list that flattens to its sections, as a ``Page`` does, and
    marks them for the walk. Each titled section opens the next appendix, so
    its heading reads "Appendix A: Data sources", and an exhibit inside is
    numbered within it, "Exhibit A.1"; an untitled section continues the
    appendix before it. The letters are the document's, computed once, so the
    contents, the running header and the text part print the same heading.

    On paper the appendices open a fresh sheet unless ``break_before`` is
    off; in an email the wrapper is not emitted, as with a ``Page``.

    Args:
        sections:     The appendices' sections, in reading order. The first
                      must be titled, since it opens Appendix A.
        break_before: On paper, start the appendices on a fresh sheet.
        spacing:      Spacing for every section here: any token one reads.
    """

    template_path = "document/page.html"

    def __init__(
        self,
        sections: Sequence[Container],
        break_before: bool = True,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        super().__init__(spacing=spacing)
        sections = list(sections)
        if not sections:
            raise ValidationError("Appendices needs at least one section.")
        for section in sections:
            if not isinstance(section, Container) or hasattr(section, "sections"):
                raise ValidationError(
                    "Appendices holds sections such as FullWidth, got "
                    f"{type(section).__name__}; a page or a second Appendices cannot nest."
                )
        if not sections[0].title:
            raise ValidationError(
                "the first section in Appendices must be titled: it opens Appendix A."
            )
        if sum(1 for section in sections if section.title) > len(LETTERS):
            raise ValidationError(f"Appendices letters at most {len(LETTERS)} appendices, A to Z.")
        self.sections = sections
        self.break_before = break_before

    @classmethod
    def spacing_tokens(cls) -> tuple[str, ...]:
        """Every token a section or component reads: the appendices reach all of them."""
        return section_spacing_tokens()

    def lettered(self) -> list[tuple[str, Container]]:
        """Each section with the letter of the appendix it falls in."""
        letters: list[tuple[str, Container]] = []
        count = 0
        for section in self.sections:
            count += bool(section.title)
            letters.append((LETTERS[count - 1], section))
        return letters

    def resolved_anchor(self) -> str:
        """None: the appendices have no heading of their own; their sections do."""
        return ""

    def components(self) -> list[Component]:
        """Every component in the appendices, in reading order."""
        return [component for section in self.sections for component in section.components()]

    def assets(self) -> list[ImageAsset]:
        """The manifest entries from every section here, in reading order."""
        return [asset for section in self.sections for asset in section.assets()]

    def images(self) -> list[EmailImage]:
        """Every image in the appendices, section by section."""
        return [image for section in self.sections for image in section.images()]

    def text(self) -> str:
        """Each section's projection in turn; the break is nothing in plain text."""
        return join_sections(*(section.text() for section in self.sections))

    def render(self, engine: Renderer) -> str:
        """The sections, wrapped in their break on paper and bare everywhere else."""
        spaced = self._spaced(engine)
        inner = "\n".join(section.render(spaced) for section in self.sections)
        if not engine.medium.paged or not self.break_before:
            return inner
        return engine.render(
            self.template_path,
            {
                **self._base_context(engine),
                "sections_html": inner,
                "break_before": True,
                "break_after": False,
            },
        )


#: The letters an appendix takes, in order.
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class OnlySections(Container):
    """
    Sections shown in the chosen media and omitted, bytes and all, from the rest (#365).

    A section list that flattens to its sections, as a ``Page`` does, where its
    medium matches, and to nothing where it does not: no band, no images in
    the manifest, no text, no contents entry and no anchor. A labelled
    exhibit, a footnote or a citation inside is refused, because omitting it
    would renumber the rest of the document.

    It sits at the top of a document. A page, a panel, a slide and
    ``Appendices`` each hold sections only, and it holds no section list.

    Args:
        sections: The sections, in reading order.
        media:    The media they show in: ``"email"``, ``"document"``,
                  ``"brochure"``, ``"deck"`` or ``"html"``.
        spacing:  Spacing for every section here: any token one reads.
    """

    def __init__(
        self,
        sections: Sequence[Container],
        media: Sequence[str] | str,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        super().__init__(spacing=spacing)
        held = list(sections)
        if not held:
            raise ValidationError("OnlySections needs at least one section.")
        for section in held:
            if not isinstance(section, Container) or hasattr(section, "sections"):
                raise ValidationError(
                    "OnlySections holds sections such as FullWidth, got "
                    f"{type(section).__name__}; a page or another section list cannot nest."
                )
        self.media = check_media(media, "OnlySections")
        refuse_numbered(
            "OnlySections", [component for section in held for component in section.components()]
        )
        self._held = held

    def shown_in(self, medium: str | None) -> bool:
        """Whether ``medium`` shows these sections; ``None``, a walk outside any document, does."""
        return medium is None or medium in self.media

    @property
    def sections(self) -> list[Container]:
        """The sections the current walk's medium shows: all of them, or none."""
        return list(self._held) if self.shown_in(walking_medium()) else []

    @classmethod
    def spacing_tokens(cls) -> tuple[str, ...]:
        """Every token a section or component reads: the list reaches all of them."""
        return section_spacing_tokens()

    def resolved_anchor(self) -> str:
        """None: the list has no heading; its sections do."""
        return ""

    def components(self) -> list[Component]:
        return [component for section in self.sections for component in section.components()]

    def assets(self) -> list[ImageAsset]:
        return [asset for section in self.sections for asset in section.assets()]

    def images(self) -> list[EmailImage]:
        return [image for section in self.sections for image in section.images()]

    def text(self) -> str:
        return join_sections(*(section.text() for section in self.sections))

    def render(self, engine: Renderer) -> str:
        if not self.shown_in(engine.medium.name):
            return ""
        spaced = self._spaced(engine)
        return "\n".join(section.render(spaced) for section in self._held)


def section_spacing_tokens() -> tuple[str, ...]:
    """
    Every spacing token a section or component reads, across every class.

    What a container of containers may move: a :class:`~pyhermes.document.page.Page`
    reaches every section on it, so its override may name any of them.
    """
    seen: set[str] = set()
    pending: list[type] = [Container, Component]
    while pending:
        cls = pending.pop()
        seen.update(getattr(cls, "SPACING_TOKENS", ()))
        pending.extend(cls.__subclasses__())
    return tuple(sorted(seen))
