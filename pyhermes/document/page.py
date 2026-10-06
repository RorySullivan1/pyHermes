"""
``Page`` — an explicit sheet boundary in the section tree.

A container of containers that asks the renderer to break before or after
it. In a paged medium that is a real page break; in every other it is
nothing, and the sections inside simply run on. One tree, two outputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING

from pyhermes.builder.components import Component
from pyhermes.builder.containers import Container, section_spacing_tokens
from pyhermes.builder.engine import Renderer, rebind, scheme_of
from pyhermes.builder.enums import TextAlign
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import ImageAsset
from pyhermes.builder.medium import Medium
from pyhermes.builder.sizing import PageFormat, Spacing
from pyhermes.builder.textgen import join_blocks, underline

if TYPE_CHECKING:  # pragma: no cover
    from pyhermes.builder.images import EmailImage

#: The ways up a page's sheets may be laid (#341).
ORIENTATIONS: tuple[str, ...] = ("portrait", "landscape")


class Page(Container):
    """
    A run of sections that starts, or ends, on a sheet of its own.

    **It flattens where pages do not exist.** In a paged medium a ``Page``
    wraps its sections in a block carrying the break it asked for; in the
    email medium — or any medium whose ``paged`` is false — it renders its
    sections and nothing else, byte for byte as though it were not there.
    That is what lets one section tree target both: a document author says
    "this starts a new page", and a reader in a mail client, where the idea
    has no meaning, is not shown an artefact of it.

    The decision is made in Python rather than left to CSS: ``break-before``
    is inert in a mail client, but the wrapper element around it is not.

    **A page may not hold a page:** an inner break would either duplicate
    the outer one or contradict it, so it is refused at construction.

    Args:
        sections:     The containers on this page, in reading order.
        break_before: Start this page on a fresh sheet.
        break_after:  End it, so whatever follows starts on a fresh one.
        title:        An optional heading, as any container may carry.
        spacing:      Spacing for every section on this page: any token a
                      section or component reads.
        orientation:  ``"portrait"`` or ``"landscape"``: the medium's sheet, turned
                      where it is the other way up (#341). A turned page starts
                      and ends a sheet, whatever its breaks say.
    """

    template_path = "document/page.html"

    def __init__(
        self,
        sections: list[Container],
        break_before: bool = True,
        break_after: bool = False,
        title: str | None = None,
        background_color: str | None = None,
        align: str | TextAlign | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        orientation: str | None = None,
    ):
        super().__init__(
            title=title, background_color=background_color, align=align, spacing=spacing
        )
        if not sections:
            raise ValidationError("a page needs at least one section")
        for section in sections:
            if isinstance(section, Page) or hasattr(section, "sections"):
                raise ValidationError(
                    "a page may not contain a page: an inner break would either "
                    "duplicate the outer one or contradict it. Put the sections "
                    "side by side instead."
                )
            if not isinstance(section, Container):
                raise ValidationError(f"a page holds containers, got: {type(section).__name__}")
        if orientation is not None and orientation not in ORIENTATIONS:
            raise ValidationError(
                f"a page's orientation must be one of {ORIENTATIONS} or None, got: {orientation!r}"
            )
        self.sections = list(sections)
        self.break_before = break_before
        self.break_after = break_after
        self.orientation = orientation

    def turned_sheet(self, medium: Medium) -> PageFormat | None:
        """
        The sheet this page lays on when it is not ``medium``'s own, else ``None``.

        Only a paged medium with a sheet height has a way up to turn; a
        square sheet is both, so it never turns.
        """
        page = medium.page_format
        if not medium.paged or self.orientation is None or page.height is None:
            return None
        if page.orientation in (self.orientation, "square"):
            return None
        return replace(page, width=page.height, height=page.width)

    @classmethod
    def spacing_tokens(cls) -> tuple[str, ...]:
        """Every token a section or component reads: a page reaches all of them."""
        return section_spacing_tokens()

    def resolved_anchor(self) -> str:
        """None: a page's title is never rendered, so there is no heading to land on."""
        return ""

    def components(self) -> list[Component]:
        """Every component on this page, in reading order."""
        return [component for section in self.sections for component in section.components()]

    def assets(self) -> list[ImageAsset]:
        """The manifest entries from every section here, in reading order."""
        return [asset for section in self.sections for asset in section.assets()]

    def images(self) -> list[EmailImage]:
        """Every image on this page, for a document walking its own tree."""
        return [image for section in self.sections for image in _section_images(section)]

    def text(self) -> str:
        """
        This page as plain text: its title, then its sections.

        A break projects to nothing. Plain text has no sheets, which is the
        same reason the email medium flattens the render.
        """
        return join_blocks(
            underline(self.title or ""), *(section.text() for section in self.sections)
        )

    def render(self, engine: Renderer) -> str:
        """
        The sections, wrapped in their break — or bare, where pages are not.

        The flattening is byte-exact: what a non-paged medium gets is what
        the same sections would have produced without the ``Page`` at all.
        """
        if (turned := self.turned_sheet(engine.medium)) is not None:
            # Column widths are computed for the sheet the sections print on.
            engine = rebind(engine, size=scheme_of(engine).with_page(turned))
        spaced = self._spaced(engine)
        sections = list(self.sections)
        if sections and engine.medium.paged and (self.break_before or self.sheet_top):
            # The page opens a sheet, so its first section does (#396).
            sections[0] = sections[0].at_sheet_top()
        inner = "\n".join(section.render(spaced) for section in sections)
        if not engine.medium.paged:
            return inner
        return engine.render(
            self.template_path,
            {
                **self._base_context(engine),
                "sections_html": inner,
                "break_before": self.break_before,
                "break_after": self.break_after,
            },
        )


def _section_images(section: Container) -> list[EmailImage]:
    """Every image a section's components carry."""
    return [image for component in section.components() for image in component.images()]
