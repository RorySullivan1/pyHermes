"""
Three labelled equations on A4, one engineered to fall at a sheet's foot (#232).

The equation images are ``solid_png`` bytes at the pixel size a real render
has, so the golden never depends on matplotlib. ``LEAD_IN_PARAGRAPHS`` puts the
second equation where its caption would open the next sheet if the paged
skeleton's ``.figure`` rule were removed; the PDF test proves both halves.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import FullWidth, MathBlock, TextBlock
from svc.document import (
    PAGED_MEDIUM,
    EmptyBackMatter,
    EmptyContentsPage,
    EmptyCover,
    EmptyRunningHeader,
    PagedDocument,
    RunningFooter,
)

from . import _paged
from ._png import solid_png

#: The sheets this document lays out to; the PDF test asserts it.
SHEETS = 2

#: Each equation: its source lines, caption, and the pixel size a 4x render has.
EQUATIONS = [
    ([r"\sigma_p^2 = w^\top \Sigma w"], "Portfolio variance", (319, 87)),
    (
        [
            r"\text{VaR}_{99\%} = -q_{0.01}(r)",
            r"\text{ES}_{99\%} = \mathbb{E}[r \mid r \leq q_{0.01}]",
        ],
        "Value at risk and expected shortfall",
        (547, 152),
    ),
    ([r"\hat{\beta} = (X^\top X)^{-1} X^\top y"], "The least-squares estimate", (496, 85)),
]

#: The equation placed at a sheet's foot, and how many paragraphs precede it.
ENGINEERED = 1
LEAD_IN_PARAGRAPHS = 8

_SCALE = 4


def _paragraphs(count: int, topic: str) -> TextBlock:
    return TextBlock(
        "".join(
            f"<p>{topic}, paragraph {n}: the book held its weights through the month "
            "and the covariance estimate moved less than the returns did.</p>"
            for n in range(1, count + 1)
        )
    )


def _equation(index: int) -> MathBlock:
    lines, caption, (width, height) = EQUATIONS[index]
    return MathBlock(
        solid_png(width, height, (59, 59, 59)),
        lines=lines,
        width=round(width / _SCALE),
        caption=caption,
        label="Equation",
    )


def build_with(lead_in: int, template_dir: Path | None = None) -> PagedDocument:
    """The document with the engineered lead-in as a parameter, for tuning."""
    document = PagedDocument(
        _paged.facts(),
        template_dir=template_dir,
        medium=PAGED_MEDIUM,
        cover=EmptyCover(),
        contents=EmptyContentsPage(),
        running_header=EmptyRunningHeader(),
        running_footer=RunningFooter(label="Hermes Research · Risk Notes", show_page_number=True),
        back_matter=EmptyBackMatter(),
    )
    document.add_section(FullWidth(title="Risk", content=_paragraphs(2, "Risk")))
    document.add_section(FullWidth(content=_equation(0)))
    document.add_section(FullWidth(title="Tails", content=_paragraphs(lead_in, "Tails")))
    document.add_section(FullWidth(content=_equation(ENGINEERED)))
    document.add_section(FullWidth(title="Estimation", content=_paragraphs(3, "Estimation")))
    document.add_section(FullWidth(content=_equation(2)))
    return document


def build(template_dir: Path | None = None) -> PagedDocument:
    """Build the risk notes. Deterministic: same bytes every call."""
    return build_with(LEAD_IN_PARAGRAPHS, template_dir)
