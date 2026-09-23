"""
``Brochure`` — panels in the order a reader meets them, printed in the order a press needs.

The brochure counterpart to :class:`~svc.document.document.PagedDocument`.
The caller hands over panels in reader order; the fold's imposition decides
which side and position each one prints at, and the same three projections
follow.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, ClassVar, Self

from svc.builder.containers import Container
from svc.builder.document import Document
from svc.builder.engine import Renderer
from svc.builder.exceptions import ValidationError
from svc.builder.models import DocumentMetadata

from .fold import TRI_FOLD_LETTER, FoldFormat, _px
from .imposition import face_name, impose, sides
from .medium import brochure_medium
from .panel import Panel


class Brochure(Document):
    """
    One sheet, folded: its panels, its fold, and the print it becomes.

    **Reader order is the only order the API speaks.** Panels are given as a
    reader meets them, front cover first, and no argument takes a printer
    position: imposition is a rendering fact the fold owns. The plain-text
    projection is reader order too, because a text reader reads.

    **The panels are fixed at construction**, and their count must be the
    fold's: a five-panel tri-fold is an error, not a blank face.
    :meth:`add_section` is refused.

    **Footnotes are refused.** A note floats to the foot of a sheet, and a
    side's foot runs under three panels that a reader meets separately.

    Args:
        metadata:     Mapping of facts, or a ``DocumentMetadata``.
        panels:       Every face of the sheet, in reader order.
        fold:         The sheet and its fold. Defaults to a letter tri-fold.
        template_dir: Root of the templates. Defaults to the packaged copy.

    Raises:
        ValidationError: If the panel count is not the fold's, a panel is not
            a :class:`~svc.brochure.panel.Panel`, or a component carries a
            footnote.
    """

    METADATA: ClassVar[type[DocumentMetadata]] = DocumentMetadata

    def __init__(
        self,
        metadata: dict[str, Any] | DocumentMetadata,
        panels: list[Panel],
        fold: FoldFormat = TRI_FOLD_LETTER,
        template_dir: Path | None = None,
    ):
        super().__init__(metadata, template_dir, brochure_medium(fold))
        self._fold = fold
        self._proof = False
        if len(panels) != fold.faces:
            raise ValidationError(
                f"a {fold.kind.value}-fold has {fold.faces} panels, "
                f"{fold.panels} a side; got {len(panels)}. Pass every face in reader "
                f"order: {', '.join(face_name(fold, n) for n in range(1, fold.faces + 1))}."
            )
        for reader, panel in enumerate(panels, start=1):
            if not isinstance(panel, Panel):
                raise ValidationError(
                    f"the {face_name(fold, reader)} must be a Panel, got: {type(panel).__name__}"
                )
            Document.add_section(self, panel)
        if self._footnotes():
            raise ValidationError(
                "a brochure cannot carry footnotes: a note floats to the foot of a sheet, "
                "and a side's foot runs under three panels. Put the note in the panel's copy."
            )

    @property
    def fold(self) -> FoldFormat:
        """The sheet and its fold."""
        return self._fold

    @property
    def panels(self) -> list[Panel]:
        """Every panel, in reader order."""
        return [section for section in self._sections if isinstance(section, Panel)]

    def add_section(self, container: Container) -> Self:
        """Refused: a brochure's panels are fixed by its fold, and given at construction."""
        raise ValidationError(
            "a brochure's panels are given at construction, all "
            f"{self._fold.faces} of them; a folded sheet has no room for another section"
        )

    def render(self, proof: bool | None = None) -> str:
        """
        Render both sides of the sheet.

        ``proof=True`` draws a light guide on every fold and labels each panel
        with its reader index and name, so a designer can check the
        imposition without folding paper. ``None`` takes this brochure's own
        setting, which is off unless it came from :meth:`proof`.
        """
        standing = self._proof
        self._proof = standing if proof is None else proof
        try:
            return super().render()
        finally:
            self._proof = standing

    def proof(self) -> Brochure:
        """
        This brochure as a proof: the same panels, rendered with guides and labels.

        A copy, so the brochure a printer is sent never carries the flag, and
        ``render_pdf(brochure.proof())`` prints a proof through the unchanged
        exporter.
        """
        proof = copy.copy(self)
        proof._proof = True
        return proof

    def inset(self, panel: Panel) -> int | float:
        """The distance ``panel`` keeps its copy from its edges: its own, or the fold's."""
        return self._fold.inset if panel.inset is None else panel.inset

    def _render_body(self, engine: Renderer, sections: list[Container]) -> str:
        """The two sides, each holding its panels in the printer's order."""
        panels = self.panels
        boxes = impose(self._fold)
        rendered = {}
        for box in boxes:
            panel = panels[box.reader - 1]
            rendered[box.reader] = panel.render_box(engine, box, self.inset(panel))
        return "\n".join(
            engine.render(
                "brochure/side.html",
                {
                    "side": side,
                    "panels_html": "\n".join(rendered[reader] for reader in readers),
                    "proof": self._proof,
                    "folds": [_px(edge) for edge in self._fold.offsets(side)[1:]],
                    "labels": [
                        {"box": boxes[reader - 1], "name": face_name(self._fold, reader)}
                        for reader in readers
                    ],
                },
            )
            for side, readers in enumerate(sides(self._fold), start=1)
        )
