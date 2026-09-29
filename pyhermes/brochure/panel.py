"""
``Panel`` — one face of a folded sheet, and the unit a brochure is laid out on.

A container of containers, in :class:`~pyhermes.document.page.Page`'s shape. In the
brochure medium it is a fixed box on one side of the sheet; in every other
medium it flattens to its sections, so a tree written for a brochure still
renders as an email or a paged document.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pyhermes.builder.components import Component
from pyhermes.builder.containers import Container
from pyhermes.builder.engine import Renderer, rebind, scheme_of
from pyhermes.builder.enums import EmbedStrategy, TextAlign
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage, ImageAsset
from pyhermes.builder.sizing import PageMargin, SizeScheme
from pyhermes.builder.textgen import join_blocks, underline
from pyhermes.document.page import Page

from .fold import FoldFormat, _px


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

    def ground(self, bleed: int | float, panels: int) -> dict[str, int | float]:
        """
        This panel's ground, on the side: its box grown into the bleed.

        Every panel meets the trim at the top and the bottom; only the first
        and last on a side meet it at a side edge too. A fold between two
        panels is not a trim, so neither ground crosses it.
        """
        left = bleed if self.position == 1 else 0
        right = bleed if self.position == panels else 0
        return {
            "left": _px(self.left - left),
            "top": _px(-bleed),
            "width": _px(self.width + left + right),
            "height": _px(self.height + 2 * bleed),
        }


class Panel(Container):
    """
    A run of sections confined to one face of the sheet.

    **The panel is the layout unit; the sheet is only the CSS page.** Its
    sections render against a frame the panel's width, with ``pad_x`` set to
    the panel's ``inset``, so every container insets its copy by the safe
    distance without learning what a panel is.

    **A fixed box, and overflow is clipped** rather than carried onto another
    sheet or painted into the neighbour; `brochure.md` has the measurements.
    :func:`pyhermes.brochure.overflowing_panels` makes the clip loud.

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
        background_image: A picture filling the panel's ground to the bleed
                          (#189), attached or inline: a printed panel carries
                          its own image. Its sections' grounds go clear over it.
    """

    template_path = "brochure/panel.html"

    #: The images this container carries itself, as a region declares its own
    #: (standing rule 7): walked by :meth:`images`, so they reach the manifest.
    IMAGE_FIELDS: tuple[str, ...] = ("background_image",)

    def __init__(
        self,
        sections: list[Container],
        title: str | None = None,
        background_color: str | None = None,
        align: str | TextAlign | None = None,
        inset: int | float | None = None,
        background_image: EmailImage | None = None,
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
        if background_image is not None and not isinstance(background_image, EmailImage):
            raise ValidationError(
                f"{self._name()}'s background_image must be an EmailImage, "
                f"got: {type(background_image).__name__}"
            )
        if background_image is not None and background_image.strategy is EmbedStrategy.REMOTE:
            raise ValidationError(
                f"{self._name()}'s background_image is hosted, and the PDF exporter "
                "fetches nothing: attach it with EmailImage.attached()"
            )
        self.sections = list(sections)
        self.inset = inset
        self.background_image = background_image

    def _name(self) -> str:
        """How errors name this panel."""
        return f"the panel titled {self.title!r}" if getattr(self, "title", None) else "a panel"

    def resolved_anchor(self) -> str:
        """None: a panel's title is never rendered, so there is no heading to land on."""
        return ""

    def components(self) -> list[Component]:
        """Every component on this panel, in reading order."""
        return [component for section in self.sections for component in section.components()]

    def own_images(self) -> list[EmailImage]:
        """The images this panel carries itself, from ``IMAGE_FIELDS``."""
        return [image for name in self.IMAGE_FIELDS if (image := getattr(self, name))]

    def assets(self) -> list[ImageAsset]:
        """The manifest entries: this panel's own images, then every section's."""
        own = [asset for image in self.own_images() if (asset := image.asset)]
        return own + [asset for section in self.sections for asset in section.assets()]

    def images(self) -> list[EmailImage]:
        """Every image on this panel: its ground first, then its sections'."""
        return self.own_images() + [
            image for section in self.sections for image in section.images()
        ]

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

    def render_box(
        self, engine: Renderer, box: PanelBox, inset: int | float, fold: FoldFormat
    ) -> str:
        """
        This panel as a fixed box at ``box``, its copy ``inset`` from each edge.

        The sections render against a frame this panel's width, so every
        column width inside is computed for the panel rather than the sheet.
        Its ground runs into ``fold.bleed`` on every edge that is a trim edge.
        """
        shared: dict[str, object] = {"size": _panel_scheme(scheme_of(engine), box, inset)}
        if self.background_color:
            # A panel's ground is the surface its sections sit on, so every
            # section's own default ground becomes it, and a highlight band
            # inside still tints against it.
            palette = replace(engine.theme.palette, surface=self.background_color)
            shared["theme"] = replace(engine.theme, palette=palette)
        panel_engine = rebind(engine, **shared)
        inner = "\n".join(section.render(panel_engine) for section in self.sections)
        return engine.render(
            self.template_path,
            {
                **self._base_context(engine),
                "sections_html": inner,
                "box": box,
                "inset": inset,
                "content_height": _px(box.height - 2 * inset),
                "ground": box.ground(fold.bleed, fold.panels),
                "background_image": self.background_image.src if self.background_image else "",
            },
        )


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
