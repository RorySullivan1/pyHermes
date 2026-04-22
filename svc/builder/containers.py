"""
Container classes for the email builder.

A container defines the layout geometry for a section of the email —
single column, two-column split, highlight band, etc.  Each container
wraps one or more rendered component HTML fragments and produces a
``<tr>`` block that drops into the main 600 px email body table.

Usage:
    engine  = TemplateEngine()
    kpi     = KpiStrip(items=[...])
    section = FullWidth(content=kpi, title="Market Snapshot")
    html    = section.render(engine)
"""

from __future__ import annotations

from typing import Optional

from .engine import TemplateEngine
from .components import Component


class Container:
    """
    Abstract base for all layout containers.

    Subclasses set ``template_path`` and implement ``context()``.
    Every container may optionally have a section title and
    background-color override.
    """

    template_path: str = ""

    def __init__(
        self,
        title: Optional[str] = None,
        background_color: Optional[str] = None,
    ):
        self.title = title
        self.background_color = background_color

    def _base_context(self, engine: TemplateEngine) -> dict:
        """Shared context keys injected into every container template."""
        ctx = {}
        if self.title:
            ctx["section_title"] = self.title
        if self.background_color:
            ctx["background_color"] = self.background_color
        return ctx

    def render(self, engine: TemplateEngine) -> str:
        raise NotImplementedError


class FullWidth(Container):
    """
    Single-column, full 536 px content-width container.

    Args:
        content:          A Component instance to render inside the container.
        title:            Optional section heading.
        background_color: Optional hex background override.
    """

    template_path = "common/containers/full-width.html"

    def __init__(
        self,
        content: Component,
        title: Optional[str] = None,
        background_color: Optional[str] = None,
    ):
        super().__init__(title, background_color)
        self.content = content

    def render(self, engine: TemplateEngine) -> str:
        ctx = self._base_context(engine)
        ctx["content"] = self.content.render(engine)
        return engine.render(self.template_path, ctx)


class Highlight(Container):
    """
    Full-width container with a tinted background for visual separation.

    Default tint is ``#F8F7F5`` (warm stone).  Override with
    ``background_color``.

    Args:
        content:          A Component instance.
        title:            Optional section heading.
        background_color: Hex colour for the tinted band.
    """

    template_path = "common/containers/highlight.html"

    def __init__(
        self,
        content: Component,
        title: Optional[str] = None,
        background_color: Optional[str] = None,
    ):
        super().__init__(title, background_color)
        self.content = content

    def render(self, engine: TemplateEngine) -> str:
        ctx = self._base_context(engine)
        ctx["content"] = self.content.render(engine)
        return engine.render(self.template_path, ctx)


class TwoColumn(Container):
    """
    Two-column container with configurable split ratio.

    Supported ratios:
        ``"50-50"``  — equal 260 px columns
        ``"30-70"``  — 155 px sidebar + 365 px main
        ``"70-30"``  — 365 px main + 155 px sidebar

    For ``50-50``, pass ``left`` and ``right``.
    For ``30-70``, pass ``sidebar`` (narrow) and ``main`` (wide).
    For ``70-30``, pass ``main`` (wide) and ``sidebar`` (narrow).

    Args:
        ratio:            Column ratio string.
        left / right:     Components for 50-50 layout.
        main / sidebar:   Components for 30-70 or 70-30 layout.
        title:            Optional section heading.
        background_color: Optional hex background override.
    """

    _ratio_map = {
        "50-50": "common/containers/col-50-50.html",
        "30-70": "common/containers/col-30-70.html",
        "70-30": "common/containers/col-70-30.html",
    }

    def __init__(
        self,
        ratio: str = "50-50",
        left: Optional[Component] = None,
        right: Optional[Component] = None,
        main: Optional[Component] = None,
        sidebar: Optional[Component] = None,
        title: Optional[str] = None,
        background_color: Optional[str] = None,
    ):
        super().__init__(title, background_color)
        if ratio not in self._ratio_map:
            raise ValueError(f"Unsupported ratio '{ratio}'. Use: {list(self._ratio_map)}")
        self.ratio = ratio
        self.template_path = self._ratio_map[ratio]
        self.left = left
        self.right = right
        self.main = main
        self.sidebar = sidebar

    def render(self, engine: TemplateEngine) -> str:
        ctx = self._base_context(engine)

        if self.ratio == "50-50":
            if self.left:
                ctx["left"] = self.left.render(engine)
            if self.right:
                ctx["right"] = self.right.render(engine)
        else:
            if self.main:
                ctx["main"] = self.main.render(engine)
            if self.sidebar:
                ctx["sidebar"] = self.sidebar.render(engine)

        return engine.render(self.template_path, ctx)
