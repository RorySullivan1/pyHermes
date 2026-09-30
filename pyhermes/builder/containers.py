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

from collections.abc import Mapping, Sequence
from typing import ClassVar

from pyhermes.config import get_config

from .apparatus import slugify, validate_anchor
from .components import Component
from .engine import Renderer, respaced, scheme_of
from .enums import TextAlign, ThreeColumnRatio, TwoColumnRatio
from .exceptions import ValidationError
from .images import EmailImage, ImageAsset
from .models import _validate_align, _validate_color
from .sizing import STANDARD_SIZES, SizeScheme, Spacing, coerce_spacing, column_layout
from .textgen import join_blocks, underline


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

    def __init__(
        self,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
        align: str | TextAlign | None = None,
        anchor: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        if background_color:
            _validate_color(background_color, "container.background_color")
        _validate_align(align or "", "container.align")
        validate_anchor(anchor or "", "container.anchor")
        self.title = title
        self.background_color = background_color
        self.highlight = highlight
        self.align = align
        self.anchor = anchor
        self.spacing = coerce_spacing(spacing, self.spacing_tokens(), self._owner())

    @classmethod
    def spacing_tokens(cls) -> tuple[str, ...]:
        """The tokens a ``spacing`` on this class may move."""
        return cls.SPACING_TOKENS

    def _owner(self) -> str:
        """How errors name this section."""
        title = getattr(self, "title", None)
        return f"{type(self).__name__} {title!r}" if title else type(self).__name__

    def _spaced(self, engine: Renderer) -> Renderer:
        """``engine`` as this section and everything inside it render against."""
        return respaced(engine, self.spacing, self._owner())

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
        ctx: dict = {"section_title": self.title or "", "highlight": self.highlight}
        if self.background_color:
            ctx["background_color"] = self.background_color
        # Always injected, empty when unset: the templates gate on it with
        # ``{% if %}``, and under StrictUndefined an *undefined* name raises
        # rather than testing falsey — ``section_title``'s reasoning exactly.
        ctx["section_align"] = self.align or ""
        ctx["section_anchor"] = self.resolved_anchor()
        return ctx

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
        return join_blocks(underline(self.title or ""), *(c.text() for c in self.components()))

    def render(self, engine: Renderer) -> str:
        raise NotImplementedError


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

    SPACING_TOKENS = (
        "section_title_top",
        "section_title_bottom",
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

    def _column_context(self, engine: Renderer, contents: list[str], scheme: SizeScheme) -> dict:
        geometry = column_layout(self._weights(self.ratio), scheme)
        ctx = self._base_context(engine)
        ctx["columns"] = [
            {
                "width": column.width,
                "pad_left": column.pad_left,
                "pad_right": column.pad_right,
                "content": content,
            }
            for column, content in zip(geometry, contents, strict=True)
        ]
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
    """

    template_path = "common/containers/full-width.html"

    SPACING_TOKENS: ClassVar[tuple[str, ...]] = (
        "section_title_top",
        "section_title_bottom",
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
    ):
        super().__init__(title, background_color, highlight, align, anchor, spacing)
        self.content = content

    def components(self) -> list[Component]:
        return [self.content]

    def render(self, engine: Renderer) -> str:
        engine = self._spaced(engine)
        ctx = self._base_context(engine)
        ctx["content"] = self.content.render(engine)
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
    ):
        super().__init__(content, title, background_color, highlight, align, anchor, spacing)
        if isinstance(count, bool) or count not in self.COUNTS:
            raise ValidationError(
                f"FlowedColumns takes {self.COUNTS.start} to {self.COUNTS.stop - 1} "
                f"columns, got: {count!r}"
            )
        self.count = count

    def render(self, engine: Renderer) -> str:
        engine = self._spaced(engine)
        ctx = self._base_context(engine)
        ctx["content"] = self.content.render(engine)
        ctx["flow_columns"] = self.count if engine.medium.paged else 0
        return engine.render(self.template_path, ctx)


class TwoColumn(_SplitContainer):
    """
    Two-column container with configurable split ratio.

    Slots are positional — ``left`` and ``right`` are the visual columns —
    and the ``ratio`` string determines their widths.

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
    ):
        super().__init__(title, background_color, highlight, align, anchor, spacing)
        self.ratio = self._check_ratio(ratio)
        if left is None and right is None:
            raise ValidationError("TwoColumn requires at least one of 'left' or 'right'.")
        self.left = left
        self.right = right

    def components(self) -> list[Component]:
        return [c for c in (self.left, self.right) if c is not None]

    def render(self, engine: Renderer) -> str:
        engine = self._spaced(engine)
        # Every column is always present in the list: the template walks it
        # unconditionally, and an omitted column renders as an empty cell
        # rather than a missing one — the geometry has to hold either way.
        contents = [
            component.render(engine) if component else "" for component in (self.left, self.right)
        ]
        ctx = self._column_context(engine, contents, scheme_of(engine))
        return engine.render(self.template_path, ctx)


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
        anchor, spacing:  As on ``FullWidth``.

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
    ):
        super().__init__(title, background_color, highlight, align, anchor, spacing)
        self.ratio = self._check_ratio(ratio)
        if left is None and center is None and right is None:
            raise ValidationError(
                "ThreeColumn requires at least one of 'left', 'center', or 'right'."
            )
        self.left = left
        self.center = center
        self.right = right

    def components(self) -> list[Component]:
        return [c for c in (self.left, self.center, self.right) if c is not None]

    def render(self, engine: Renderer) -> str:
        engine = self._spaced(engine)
        # See TwoColumn.render() — an omitted column is an empty cell, not a
        # missing one, because the geometry has to hold either way.
        contents = [
            component.render(engine) if component else ""
            for component in (self.left, self.center, self.right)
        ]
        ctx = self._column_context(engine, contents, scheme_of(engine))
        return engine.render(self.template_path, ctx)


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
        title, background_color, highlight, align, anchor, spacing: As on
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
    ):
        super().__init__(title, background_color, highlight, align, anchor, spacing)
        self.ratio = self._check_ratio(ratio)
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

    def components(self) -> list[Component]:
        return [c for c in self.columns if c is not None]

    def render(self, engine: Renderer) -> str:
        engine = self._spaced(engine)
        contents = [c.render(engine) if c else "" for c in self.columns]
        ctx = self._column_context(engine, contents, scheme_of(engine))
        return engine.render(self.template_path, ctx)


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
