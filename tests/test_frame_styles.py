"""
Frames (#390): one vocabulary, ``"solid"`` or ``"dashed"``, for a section's border,
a ``Callout`` and a ``DataTable``; and a rule after a table's column.

The Word engine lists ``border-style`` and the per-side styles as fully supported
on a cell, so the email draws the dash as paper does; a real Outlook's render
joins #288's check (`design-axes.md`).
"""

from __future__ import annotations

import re

import pytest

from pyhermes.brochure import Brochure, Panel
from pyhermes.builder import (
    Callout,
    Column,
    DataTable,
    EmailBuilder,
    FullWidth,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import TableRow
from pyhermes.builder.theming import DEFAULT_THEME
from pyhermes.deck import Deck
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from qa.fixtures import _paged

FACTS = {"firm_name": "Hermes Research", "campaign_name": "Frames"}
RULE, RULE_DARK = DEFAULT_THEME.palette.rule, DEFAULT_THEME.palette.rule_dark


def _email(*sections):
    builder = EmailBuilder().metadata({**FACTS, "email_subject": "Frames"})
    for section in sections:
        builder.section(section)
    return builder.build()


def _paper(*sections):
    document = PagedDocument(_paged.facts(), cover=EmptyCover(), back_matter=EmptyBackMatter())
    for section in sections:
        document.add_section(section)
    return document


def _table(**options) -> DataTable:
    return DataTable(
        [Column("Fund", rule_after=True), "Cost"],
        [TableRow(["Core", "0.03%"]), TableRow(["Satellite", "0.12%"])],
        **options,
    )


def _framed() -> list:
    return [
        TwoColumn(
            left=Callout(TextBlock("<p>Buy.</p>"), label="Verdict", frame="dashed"),
            right=TextBlock("<p>Beside it.</p>"),
            border=True,
            frame="dashed",
        ),
        FullWidth(_table(frame="dashed")),
    ]


class TestOneVocabulary:
    @pytest.mark.parametrize(
        "build",
        [
            lambda: Callout(TextBlock("<p>x</p>"), frame="dotted"),
            lambda: FullWidth(TextBlock("<p>x</p>"), border=True, frame="double"),
            lambda: _table(frame="Dashed"),
        ],
        ids=["callout", "section", "table"],
    )
    def test_a_frame_outside_the_vocabulary_is_refused(self, build):
        with pytest.raises(ValidationError, match=r"\['solid', 'dashed'\]"):
            build()

    def test_a_dashed_frame_needs_a_border_on_a_callout(self):
        with pytest.raises(ValidationError, match="needs border=True"):
            Callout(TextBlock("<p>x</p>"), border=False, frame="dashed")

    def test_a_dashed_frame_needs_a_border_on_a_section(self):
        with pytest.raises(ValidationError, match="needs border=True"):
            FullWidth(TextBlock("<p>x</p>"), frame="dashed")

    def test_a_rule_after_is_true_or_false(self):
        with pytest.raises(ValidationError, match="rule_after"):
            DataTable([Column("A", rule_after="yes"), "B"], [TableRow(["x", "1"])])  # type: ignore[arg-type]

    def test_solid_is_the_default_and_draws_what_it_drew(self):
        html = _email(
            FullWidth(Callout(TextBlock("<p>x</p>")), border=True), FullWidth(_table())
        ).render()
        assert "dashed" not in html
        assert f"border:1px solid {RULE}" in html


class TestEachMediumDrawsTheDash:
    def _count(self, html: str) -> int:
        return len(re.findall(r"border(?:-\w+)?:\s*1px dashed", html))

    def test_in_the_email(self):
        assert self._count(_email(*_framed()).render()) >= 3

    def test_on_paper(self):
        assert self._count(_paper(*_framed()).render()) >= 3

    def test_in_a_brochure_panel(self):
        panels = [Panel([FullWidth(TextBlock(f"<p>Face {n}</p>"))]) for n in range(5)]
        panels.append(Panel(_framed()))
        assert self._count(Brochure(FACTS, panels).render()) >= 3

    def test_on_a_slide(self):
        assert self._count(Deck(FACTS).add_slide(_framed(), "Frames").render()) >= 3


class TestATableFrame:
    def test_it_wraps_the_table_in_a_cell_rather_than_bordering_it(self):
        html = _email(FullWidth(_table(frame="dashed"))).render()
        wrapper = re.search(r'<table role="presentation"[^>]*><tr><td style="([^"]*)">', html)
        assert wrapper and f"border: 1px dashed {RULE}" in wrapper.group(1)
        assert re.search(r'<table class="data-table"[^>]*style="border-collapse: collapse;">', html)

    def test_no_frame_adds_no_wrapper(self):
        framed = _email(FullWidth(_table(frame="solid"))).render()
        bare = _email(FullWidth(_table())).render()
        assert framed.count('role="presentation"') == bare.count('role="presentation"') + 1


class TestARuleAfterAColumn:
    def test_it_rules_the_head_the_units_and_every_body_cell(self):
        table = DataTable(
            [Column("Fund", rule_after=True), Column("Cost", unit="%")],
            [TableRow(["Core", "0.03"]), TableRow(["Satellite", "0.12"])],
        )
        html = _email(FullWidth(table)).render()
        assert html.count(f"border-right: 1px solid {RULE_DARK}") == 4

    def test_only_the_named_column_is_ruled(self):
        html = _paper(FullWidth(_table())).render()
        cells = re.findall(r"<t[hd] [^>]*>(?:Fund|Cost|Core|0\.03%)</t[hd]>", html)
        ruled = [cell for cell in cells if "border-right" in cell]
        assert len(cells) == 4 and len(ruled) == 2
        assert all(">Fund<" in cell or ">Core<" in cell for cell in ruled)
