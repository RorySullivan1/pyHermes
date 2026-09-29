"""
The brochure medium: one sheet, folded into panels, printed on both sides.

A medium rather than a page preset because a fold changes the skeleton, the
unit of layout, the constraints and the lint rules, while keeping the PDF
exporter: the profile #157 defined for a medium. `.claude/rules/brochure.md`
carries the reasoning.
"""

from __future__ import annotations

from dataclasses import replace

from pyhermes.builder.medium import Medium

from .fold import TRI_FOLD_LETTER, FoldFormat

__all__ = ["BROCHURE_MEDIUM", "brochure_medium"]

#: The shipped brochure medium, on a letter tri-fold's sheet.
#:
#: The overlay searches ``brochure/`` first, then the paged medium's
#: ``document/``, then the shared tree, so a brochure forks only what a fold
#: demands and inherits the rest of the paged medium's templates. It has no
#: regions: every face of a brochure, the cover included, is a panel the
#: caller composes, and a ``Cover`` region would be a second way to fill the
#: first one.
BROCHURE_MEDIUM = Medium(
    name="brochure",
    skeleton="base.html",
    page_format=TRI_FOLD_LETTER.sheet,
    template_search_path=("brochure", "document"),
    paged=True,
)


def brochure_medium(fold: FoldFormat) -> Medium:
    """The brochure medium on ``fold``'s sheet."""
    return replace(BROCHURE_MEDIUM, page_format=fold.sheet)
