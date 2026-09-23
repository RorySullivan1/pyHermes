"""
``Panel`` — one face of a folded sheet, and the unit a brochure is laid out on.

A container of containers, in :class:`~svc.document.page.Page`'s shape. In the
brochure medium it is a fixed box on one side of the sheet; in every other
medium it flattens to its sections, so a tree written for a brochure still
renders as an email or a paged document.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from svc.builder.components import Component
from svc.builder.containers import Container
from svc.builder.engine import BoundEngine, Renderer, TemplateEngine
from svc.builder.enums import TextAlign
from svc.builder.exceptions import ValidationError
from svc.builder.images import ImageAsset
from svc.builder.sizing import STANDARD_SIZES, PageMargin, SizeScheme
from svc.builder.textgen import join_blocks, underline
from svc.document.page import Page

from .fold import _px

if TYPE_CHECKING:  # pragma: no cover
    from svc.builder.images import EmailImage


@dataclass(frozen=True)
class PanelBox:
    """
    Where one panel sits on the sheet: computed by the brochure, never passed in.

    ``reader`` is the panel's place in reading order, from 1; ``side`` and
    ``position`` are where the printer puts it. The caller only ever speaks
    reader order, which is why this is not a constructor argument anywhere.
    """

    reader: int
    side: int
    position: int
    left: int | float
    width: int | float
    height: int | float


class Panel(Container):
    """
    A run of sections confined to one face of the sheet.

    **The panel is the layout unit; the sheet is only the CSS page.** Its
    sections render against a frame the panel's width, with ``pad_x`` set to
    the panel's ``inset``, so every container insets its copy by the safe
    distance without learning what a panel is.

    **A fixed box, and overflow is clipped** rather than carried onto another
    sheet or painted into the neighbour; `brochure.md` has the measurements.
    :func:`svc.brochure.overflowing_panels` makes the clip loud.

    **It flattens where panels do not exist**, byte for byte, as a ``Page``
    does. It may hold neither a panel nor a page.

    Args:
        sections:         The containers on this panel, in reading order.
        title:            Names the panel in errors and heads it in plain text.
                          Not rendered: a panel's first section carries its heading.
        background_color: The panel's ground, and the surface its sections sit on.
        align:            Alignment inherited by the copy inside.
        inset:            Distance from the panel's edges to its copy, in px.
                          ``None`` takes the fold's.
    """

    template_path = "brochure/panel.html"

    def __init__(
        self,
        sections: list[Container],
        title: str | None = None,
        background_color: str | None = None,
        align: str | TextAlign | None = None,
        inset: int | float | None = None,
    ):
        super().__init__(title=title, background_color=background_color, align=align)
        if not sections:
            raise ValidationError(f"{self._name()} needs at least one section")
        for section in sections:
            if isinstance(section, (Panel, Page)):
                raise ValidationError(
                    f"{self._name()} may not contain a {type(section).__name__.lower()}: "
                    "a boundary inside a panel has no meaning on a folded sheet"
                )
            if not isinstance(section, Container):
                raise ValidationError(
                    f"{self._name()} holds containers, got: {type(section).__name__}"
                )
        if inset is not None and (
            isinstance(inset, bool) or not isinstance(inset, (int, float)) or inset < 0
        ):
            raise ValidationError(f"{self._name()}'s inset must be a number of px, got: {inset!r}")
        self.sections = list(sections)
        self.inset = inset

    def _name(self) -> str:
        """How errors name this panel."""
        return f"the panel titled {self.title!r}" if getattr(self, "title", None) else "a panel"

    def resolved_anchor(self) -> str:
        """None: a panel's title is never rendered, so there is no heading to land on."""
        return ""

    def components(self) -> list[Component]:
        """Every component on this panel, in reading order."""
        return [component for section in self.sections for component in section.components()]

    def assets(self) -> list[ImageAsset]:
        """The manifest entries from every section here, in reading order."""
        return [asset for section in self.sections for asset in section.assets()]

    def images(self) -> list[EmailImage]:
        """Every image on this panel."""
        return [image for component in self.components() for image in component.images()]

    def text(self) -> str:
        """This panel as plain text: its title, then its sections. A fold projects to nothing."""
        return join_blocks(
            underline(self.title or ""), *(section.text() for section in self.sections)
        )

    def render(self, engine: Renderer) -> str:
        """
        The sections, bare.

        Only a brochure knows where on the sheet a panel sits, so the box is
        :meth:`render_box`, which the brochure calls. Anywhere else, and in
        any medium, a panel is its sections run on.
        """
        return "\n".join(section.render(engine) for section in self.sections)

    def render_box(self, engine: Renderer, box: PanelBox, inset: int | float) -> str:
        """
        This panel as a fixed box at ``box``, its copy ``inset`` from each edge.

        The sections render against a frame this panel's width, so every
        column width inside is computed for the panel rather than the sheet.
        """
        shared: dict[str, object] = {"size": _panel_scheme(_scheme(engine), box, inset)}
        if self.background_color:
            # A panel's ground is the surface its sections sit on, so every
            # section's own default ground becomes it, and a highlight band
            # inside still tints against it.
            palette = replace(engine.theme.palette, surface=self.background_color)
            shared["theme"] = replace(engine.theme, palette=palette)
        panel_engine = _rebind(engine, shared)
        inner = "\n".join(section.render(panel_engine) for section in self.sections)
        return engine.render(
            self.template_path,
            {
                **self._base_context(engine),
                "sections_html": inner,
                "box": box,
                "inset": inset,
                "content_height": _px(box.height - 2 * inset),
            },
        )


def _scheme(engine: Renderer) -> SizeScheme:
    """The scheme the document bound, or the shipped one."""
    shared = getattr(engine, "shared", {})
    scheme = shared.get("size") if isinstance(shared, dict) else None
    return scheme if isinstance(scheme, SizeScheme) else STANDARD_SIZES


def _panel_scheme(scheme: SizeScheme, box: PanelBox, inset: int | float) -> SizeScheme:
    """
    The density, on a frame one panel wide.

    ``pad_x`` becomes the inset, because that is the one horizontal padding
    every container template already applies; the vertical inset is the
    panel box's own padding. No margin and no breakpoint: a panel is inside
    a sheet that has neither.
    """
    frame = replace(
        scheme.frame,
        width=box.width,
        height=_px(box.height - 2 * inset),
        mobile_breakpoint=None,
        margin=PageMargin(),
        pad_x=inset,
    )
    return scheme.derive(frame=frame)


def _rebind(engine: Renderer, shared: dict[str, object]) -> Renderer:
    """``engine`` with ``shared`` bound over whatever it had."""
    if isinstance(engine, BoundEngine):
        return BoundEngine(engine.engine, {**engine.shared, **shared})
    if isinstance(engine, TemplateEngine):
        return engine.bound(**shared)
    raise TypeError(f"cannot bind a panel's frame onto {type(engine).__name__}")
