"""
Container classes for the email builder.

A container defines the layout geometry for a section of the email —
single column, two-column split, highlight band, etc.  Each container
wraps one or more rendered component HTML fragments and produces a
``<tr>`` block that drops into the main 680 px email body table.

Usage:
    engine  = TemplateEngine()
    kpi     = KpiStrip(items=[...])
    section = FullWidth(content=kpi, title="Market Snapshot")
    html    = section.render(engine)
"""

from __future__ import annotations

from .components import Component
from .engine import TemplateEngine
from .enums import ThreeColumnRatio, TwoColumnRatio
from .exceptions import ValidationError
from .models import _validate_color


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

    def _base_context(self, engine: TemplateEngine) -> dict:
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

    def render(self, engine: TemplateEngine) -> str:
        raise NotImplementedError


class FullWidth(Container):
    """
    Single-column, full 616 px content-width container.

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

    def render(self, engine: TemplateEngine) -> str:
        ctx = self._base_context(engine)
        ctx["content"] = self.content.render(engine)
        return engine.render(self.template_path, ctx)


class TwoColumn(Container):
    """
    Two-column container with configurable split ratio.

    Slots are positional: ``left`` is always the visually-left column,
    ``right`` is always the visually-right column. The ``ratio`` string
    determines the column widths.

    Supported ratios:
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

    _ratio_map = {
        TwoColumnRatio.EQUAL: "common/containers/col-50-50.html",
        TwoColumnRatio.NARROW_WIDE: "common/containers/col-30-70.html",
        TwoColumnRatio.WIDE_NARROW: "common/containers/col-70-30.html",
    }

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
        # A StrEnum member equals and hashes as its string value, so this
        # membership test accepts both the enum and the bare ratio string.
        if ratio not in self._ratio_map:
            raise ValidationError(
                f"Unsupported ratio '{ratio}'. Use: {[r.value for r in self._ratio_map]}"
            )
        if left is None and right is None:
            raise ValidationError("TwoColumn requires at least one of 'left' or 'right'.")
        self.ratio = ratio
        self.template_path = self._ratio_map[TwoColumnRatio(ratio)]
        self.left = left
        self.right = right

    def render(self, engine: TemplateEngine) -> str:
        # Both keys are always injected: the column templates emit {{ left }}
        # and {{ right }} unconditionally, so a missing key would raise under
        # StrictUndefined.  An omitted column renders as an empty cell.
        ctx = self._base_context(engine)
        ctx["left"] = self.left.render(engine) if self.left else ""
        ctx["right"] = self.right.render(engine) if self.right else ""
        return engine.render(self.template_path, ctx)


class ThreeColumn(Container):
    """
    Three-column container with configurable split ratio.

    Slots are positional: ``left`` / ``center`` / ``right`` are always the
    visually left, middle, and right columns. The ``ratio`` string (or a
    :class:`~svc.builder.enums.ThreeColumnRatio` member) sets the widths.

    Supported ratios (each totals the 616 px content width, two 16 px gutters):
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

    _ratio_map = {
        ThreeColumnRatio.EQUAL: "common/containers/col-33-33-33.html",
        ThreeColumnRatio.WIDE_LEFT: "common/containers/col-50-25-25.html",
        ThreeColumnRatio.WIDE_CENTER: "common/containers/col-25-50-25.html",
        ThreeColumnRatio.WIDE_RIGHT: "common/containers/col-25-25-50.html",
    }

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
        # A StrEnum member equals and hashes as its string value, so this
        # membership test accepts both the enum and the bare ratio string.
        if ratio not in self._ratio_map:
            raise ValidationError(
                f"Unsupported ratio '{ratio}'. Use: {[r.value for r in self._ratio_map]}"
            )
        if left is None and center is None and right is None:
            raise ValidationError(
                "ThreeColumn requires at least one of 'left', 'center', or 'right'."
            )
        self.ratio = ratio
        self.template_path = self._ratio_map[ThreeColumnRatio(ratio)]
        self.left = left
        self.center = center
        self.right = right

    def render(self, engine: TemplateEngine) -> str:
        # All three keys are always injected: the column templates emit
        # {{ left }} / {{ center }} / {{ right }} unconditionally, so a missing
        # key would raise under StrictUndefined.  An omitted column renders as
        # an empty cell.
        ctx = self._base_context(engine)
        ctx["left"] = self.left.render(engine) if self.left else ""
        ctx["center"] = self.center.render(engine) if self.center else ""
        ctx["right"] = self.right.render(engine) if self.right else ""
        return engine.render(self.template_path, ctx)
