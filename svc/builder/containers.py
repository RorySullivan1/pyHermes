"""
Container classes for the email builder.

A container defines the layout geometry for a section of the email —
single column, two-column split, highlight band, etc.  Each container
wraps one or more rendered component HTML fragments and produces a
``<tr>`` block that drops into the main email body table.

Column widths are **computed, never written down**: the ratio's own name
is its weights, and :func:`~svc.builder.sizing.column_layout` splits the
active scheme's content width by them. That is why one template serves
every split — see #42 in :mod:`svc.builder.sizing`.

Usage:
    engine  = TemplateEngine()
    kpi     = KpiStrip(items=[...])
    section = FullWidth(content=kpi, title="Market Snapshot")
    html    = section.render(engine)
"""

from __future__ import annotations

from .components import Component
from .engine import Renderer
from .enums import ThreeColumnRatio, TwoColumnRatio
from .exceptions import ValidationError
from .images import ImageAsset
from .models import _validate_color
from .sizing import STANDARD_SIZES, SizeScheme, column_layout


class Container:
    """
    Abstract base for all layout containers.

    Subclasses set ``template_path`` and implement ``context()``.
    Every container may optionally have a section title and
    background-color override.

    Raises:
        ValidationError: If ``background_color`` is not a ``#RRGGBB`` hex color.
    """

    template_path: str = ""

    def __init__(
        self,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
    ):
        if background_color:
            _validate_color(background_color, "container.background_color")
        self.title = title
        self.background_color = background_color
        self.highlight = highlight

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

    def render(self, engine: Renderer) -> str:
        raise NotImplementedError


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

    #: The split this container was built with, as its bare string or the
    #: matching enum member. Set by each subclass's ``__init__``.
    ratio: str

    #: The closed set of splits this container accepts.
    _ratio_enum: type[TwoColumnRatio] | type[ThreeColumnRatio]

    @classmethod
    def _check_ratio(cls, ratio: str) -> None:
        """
        A StrEnum member equals and hashes as its string value, so this
        membership test accepts both the enum and the bare ratio string.
        """
        if ratio not in set(cls._ratio_enum):
            raise ValidationError(
                f"Unsupported ratio '{ratio}'. Use: {[r.value for r in cls._ratio_enum]}"
            )

    @staticmethod
    def _weights(ratio: str) -> list[int]:
        """
        A ratio's own name is its weights: ``"25-25-50"`` -> ``[25, 25, 50]``.

        No lookup table, because a table would be a second place for the
        split to be written down and therefore a second place to be wrong.
        :func:`~svc.builder.sizing.column_layout` normalises by the sum, so
        ``"33-33-33"`` is exact thirds rather than 99% of the frame.
        """
        return [int(part) for part in str(ratio).split("-")]

    def _column_context(self, engine: Renderer, contents: list[str], scheme: SizeScheme) -> dict:
        geometry = column_layout(self._weights(self.ratio), scheme)
        ctx = self._base_context(engine)
        ctx["columns"] = [
            {"width": column.width, "pad_x": column.pad_x, "content": content}
            for column, content in zip(geometry, contents, strict=True)
        ]
        return ctx

    @staticmethod
    def _scheme(engine: Renderer) -> SizeScheme:
        """
        The scheme the email bound, or the shipped one.

        A container is handed a :class:`~svc.builder.engine.BoundEngine`
        during ``Email.render()``, and that is where the resolved scheme
        lives — the same binder the theme rides. Rendering a container
        directly against a bare ``TemplateEngine`` stays legal and falls
        back to ``STANDARD_SIZES``, matching the engine's own floor.
        """
        shared = getattr(engine, "shared", {})
        scheme = shared.get("size") if isinstance(shared, dict) else None
        return scheme if isinstance(scheme, SizeScheme) else STANDARD_SIZES


class FullWidth(Container):
    """
    Single-column container spanning the frame's full content width.

    Args:
        content:          A Component instance to render inside the container.
        title:            Optional section heading.
        background_color: Optional hex background override.
    """

    template_path = "common/containers/full-width.html"

    def __init__(
        self,
        content: Component,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
    ):
        super().__init__(title, background_color, highlight)
        self.content = content

    def components(self) -> list[Component]:
        return [self.content]

    def render(self, engine: Renderer) -> str:
        ctx = self._base_context(engine)
        ctx["content"] = self.content.render(engine)
        return engine.render(self.template_path, ctx)


class TwoColumn(_SplitContainer):
    """
    Two-column container with configurable split ratio.

    Slots are positional: ``left`` is always the visually-left column,
    ``right`` is always the visually-right column. The ``ratio`` string
    determines the column widths.

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

    Raises:
        ValidationError: On an unsupported ratio, a non-hex background color,
            or when both columns are omitted.
    """

    _ratio_enum = TwoColumnRatio

    def __init__(
        self,
        ratio: str | TwoColumnRatio = TwoColumnRatio.EQUAL,
        left: Component | None = None,
        right: Component | None = None,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
    ):
        super().__init__(title, background_color, highlight)
        self._check_ratio(ratio)
        if left is None and right is None:
            raise ValidationError("TwoColumn requires at least one of 'left' or 'right'.")
        self.ratio = ratio
        self.left = left
        self.right = right

    def components(self) -> list[Component]:
        return [c for c in (self.left, self.right) if c is not None]

    def render(self, engine: Renderer) -> str:
        # Every column is always present in the list: the template walks it
        # unconditionally, and an omitted column renders as an empty cell
        # rather than a missing one — the geometry has to hold either way.
        contents = [
            component.render(engine) if component else "" for component in (self.left, self.right)
        ]
        ctx = self._column_context(engine, contents, self._scheme(engine))
        return engine.render(self.template_path, ctx)


class ThreeColumn(_SplitContainer):
    """
    Three-column container with configurable split ratio.

    Slots are positional: ``left`` / ``center`` / ``right`` are always the
    visually left, middle, and right columns. The ``ratio`` string (or a
    :class:`~svc.builder.enums.ThreeColumnRatio` member) sets the widths.

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

    Raises:
        ValidationError: On an unsupported ratio, a non-hex background color,
            or when all three columns are omitted.
    """

    _ratio_enum = ThreeColumnRatio

    def __init__(
        self,
        ratio: str | ThreeColumnRatio = ThreeColumnRatio.EQUAL,
        left: Component | None = None,
        center: Component | None = None,
        right: Component | None = None,
        title: str | None = None,
        background_color: str | None = None,
        highlight: bool = False,
    ):
        super().__init__(title, background_color, highlight)
        self._check_ratio(ratio)
        if left is None and center is None and right is None:
            raise ValidationError(
                "ThreeColumn requires at least one of 'left', 'center', or 'right'."
            )
        self.ratio = ratio
        self.left = left
        self.center = center
        self.right = right

    def components(self) -> list[Component]:
        return [c for c in (self.left, self.center, self.right) if c is not None]

    def render(self, engine: Renderer) -> str:
        # See TwoColumn.render() — an omitted column is an empty cell, not a
        # missing one, because the geometry has to hold either way.
        contents = [
            component.render(engine) if component else ""
            for component in (self.left, self.center, self.right)
        ]
        ctx = self._column_context(engine, contents, self._scheme(engine))
        return engine.render(self.template_path, ctx)
