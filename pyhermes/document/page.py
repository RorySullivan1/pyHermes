"""
``Page`` — an explicit sheet boundary in the section tree.

A container of containers that asks the renderer to break before or after
it. In a paged medium that is a real page break; in every other it is
nothing, and the sections inside simply run on. One tree, two outputs.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import TYPE_CHECKING

from pyhermes.builder.components import Component
from pyhermes.builder.containers import Container, section_spacing_tokens
from pyhermes.builder.engine import Renderer
from pyhermes.builder.enums import TextAlign
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import ImageAsset
from pyhermes.builder.sizing import Spacing
from pyhermes.builder.textgen import join_blocks, underline

if TYPE_CHECKING:  # pragma: no cover
    from pyhermes.builder.images import EmailImage


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

    The decision is made in Python rather than left to CSS. ``break-before``
    is inert in a mail client, so emitting it would *look* harmless — but the
    wrapper element around it is not, and an email would carry a ``div`` that
    exists for a medium it is not being read in.

    **A page may not hold a page.** Nesting has no meaning — an inner break
    would either duplicate the outer one or contradict it — so it is refused
    at construction rather than rendered into something arbitrary.

    Args:
        sections:     The containers on this page, in reading order.
        break_before: Start this page on a fresh sheet.
        break_after:  End it, so whatever follows starts on a fresh one.
        title:        An optional heading, as any container may carry.
        spacing:      Spacing for every section on this page: any token a
                      section or component reads.
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
    ):
        super().__init__(
            title=title, background_color=background_color, align=align, spacing=spacing
        )
        if not sections:
            raise ValidationError("a page needs at least one section")
        for section in sections:
            if isinstance(section, Page):
                raise ValidationError(
                    "a page may not contain a page: an inner break would either "
                    "duplicate the outer one or contradict it. Put the sections "
                    "side by side instead."
                )
            if not isinstance(section, Container):
                raise ValidationError(f"a page holds containers, got: {type(section).__name__}")
        self.sections = list(sections)
        self.break_before = break_before
        self.break_after = break_after

    @classmethod
    def spacing_tokens(cls) -> tuple[str, ...]:
        """Every token a section or component reads: a page reaches all of them."""
        return section_spacing_tokens()

    def opening(self) -> Page:
        """This page without its leading break, for a body that already opens a sheet."""
        opened = copy.copy(self)
        opened.break_before = False
        return opened

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
        spaced = self._spaced(engine)
        inner = "\n".join(section.render(spaced) for section in self.sections)
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
