"""
Per-column alignment and kind (#117), the first step of the DataTable epic #116.

The claim this file exists to hold: **alignment resolves once, and both
projections read that one resolution.** Before #117 the rule lived as
``loop.first`` in the template and was *re-derived* in
``svc/builder/textgen.py`` so the two would agree — correct, and impossible
to extend. A test that only checked the HTML would let them drift apart.
"""

from __future__ import annotations

import re

import pytest

from svc.builder import DataTable
from svc.builder.engine import TemplateEngine
from svc.builder.enums import ColumnAlign, ColumnKind
from svc.builder.exceptions import ValidationError
from svc.builder.models import Column, TableRow, coerce_column
from svc.builder.textgen import table as text_table

TEMPLATE = TemplateEngine().template_dir / "analysis" / "data-table.html"


def _html(component: DataTable) -> str:
    return component.render(TemplateEngine())


def _html_aligns(html: str) -> list[str]:
    """The `text-align` of each cell in the first body row."""
    row = html.split("<tr")[2]
    return re.findall(r"text-align: ([a-z]+)", row)


def _text_align_of(column_text: str) -> str:
    """Infer a text column's alignment from where its padding sits."""
    left, right = column_text != column_text.lstrip(), column_text != column_text.rstrip()
    if left and right:
        return "center"
    return "right" if left else "left"


class TestTheResolutionReproducesTheOldConvention:
    """
    Byte-identity is the bar: a table built from plain strings must render
    exactly as it did before this class existed.
    """

    def test_strings_and_columns_render_identically(self):
        rows = [TableRow(["Value", "+1.8%"]), TableRow(["Momentum", "-11.2%"])]
        from_strings = DataTable(["Factor", "1M"], rows)
        from_columns = DataTable([Column("Factor"), Column("1M")], rows)

        assert _html(from_strings) == _html(from_columns)
        assert from_strings.text() == from_columns.text()

    def test_the_position_rule_is_the_old_loop_first(self):
        column = Column("Anything")
        assert column.resolved_kind(0) is ColumnKind.TEXT
        assert column.resolved_kind(1) is ColumnKind.NUMERIC
        assert column.resolved_align(0) is ColumnAlign.LEFT
        assert column.resolved_align(3) is ColumnAlign.RIGHT

    def test_headers_still_reads_back_as_strings(self):
        component = DataTable(["Factor", Column("1M")], [TableRow(["a", "b"])])
        assert component.headers == ["Factor", "1M"]


class TestTheChainRunsThroughKind:
    def test_a_text_column_anywhere_is_left_aligned(self):
        """
        The point of naming the kind: saying `kind="text"` on the third
        column gets left alignment without also having to say so.
        """
        assert Column("Desk", kind="text").resolved_align(2) is ColumnAlign.LEFT

    def test_a_numeric_first_column_is_right_aligned(self):
        assert Column("Rank", kind="numeric").resolved_align(0) is ColumnAlign.RIGHT

    def test_an_explicit_align_wins_over_the_kind(self):
        column = Column("Mid", align="center", kind="numeric")
        assert column.resolved_align(1) is ColumnAlign.CENTER
        assert column.resolved_kind(1) is ColumnKind.NUMERIC


class TestTheCaseThatWasImpossible:
    """Two text columns — unreachable before #117, at any argument."""

    def build(self) -> DataTable:
        return DataTable(
            [Column("Name", kind="text"), Column("Desk", kind="text"), "1M"],
            [TableRow(["Value", "Global Macro", "+1.8%"])],
        )

    def test_both_text_columns_are_left_aligned(self):
        assert _html_aligns(_html(self.build()))[:2] == ["left", "left"]

    def test_only_the_numeric_column_takes_the_numeric_face(self):
        html = _html(self.build())
        row = html.split("<tr")[2]
        assert row.count("Courier") == 2, "one numeric cell, whose stack names Courier twice"

    def test_only_the_numeric_column_is_bold(self):
        row = _html(self.build()).split("<tr")[2]
        assert row.count("font-weight: bold") == 1


class TestBothProjectionsAgree:
    """
    The criterion #117 exists for. Two independent readers, one resolution —
    asserted against the source rather than against each other, so a test
    cannot pass by both being wrong in the same way.
    """

    @staticmethod
    def build() -> DataTable:
        return DataTable(
            [
                Column("Name", kind="text"),
                Column("Middle", align="center"),
                Column("Figure"),
            ],
            [TableRow(["Value", "x", "1"]), TableRow(["Momentum", "wide-value", "-11.2%"])],
        )

    def test_the_html_reads_the_resolved_alignment(self):
        component = self.build()
        expected = [column.align for column in component.resolved_columns()]
        assert _html_aligns(_html(component)) == expected

    def test_the_text_projection_reads_the_same_resolution(self):
        component = self.build()
        expected = [column.align for column in component.resolved_columns()]

        # The short row, sliced back into its columns by the rule's own widths.
        lines = component.text().splitlines()
        widths = [len(part) for part in lines[1].split("  ")]
        short = lines[2]
        observed, at = [], 0
        for width in widths:
            observed.append(_text_align_of(short[at : at + width]))
            at += width + 2

        assert observed == expected

    def test_a_numeric_first_column_moves_in_both(self):
        """
        `textgen.table()` used to assume column zero was the label. A table
        that says otherwise must move in the text part too, not only in the
        markup.
        """
        component = DataTable(
            [Column("Rank", kind="numeric"), Column("Name", kind="text")],
            [TableRow(["1", "Value"]), TableRow(["10", "Momentum"])],
        )
        assert _html_aligns(_html(component)) == ["right", "left"]
        # "Rank" is four wide, so a right-aligned "1" carries three spaces.
        assert component.text().splitlines()[2] == "   1  Value"


class TestTextTableTakesItsAlignments:
    def test_omitted_aligns_keep_the_pre_117_default(self):
        """
        A caller composing a table by hand still gets sensible output, so
        the fallback is the convention rather than an error.
        """
        rendered = text_table(["A", "B"], [["x", "1"], ["longer", "22"]])
        assert rendered.splitlines()[2] == "x        1"

    def test_center_is_honoured(self):
        rendered = text_table(["A"], [["x"], ["wide-cell"]], aligns=["center"])
        assert rendered.splitlines()[2] == "    x"


class TestValidation:
    @pytest.mark.parametrize("bad", ["middle", "justify", "LEFT", "top"])
    def test_an_unknown_align_raises_naming_the_field(self, bad):
        with pytest.raises(ValidationError, match="column.align"):
            coerce_column(Column("H", align=bad))

    @pytest.mark.parametrize("bad", ["number", "string", "TEXT", "money"])
    def test_an_unknown_kind_raises_naming_the_field(self, bad):
        with pytest.raises(ValidationError, match="column.kind"):
            coerce_column(Column("H", kind=bad))

    def test_an_empty_header_raises(self):
        with pytest.raises(ValidationError, match="column.header"):
            coerce_column(Column(""))

    def test_a_non_string_non_column_raises_naming_where_it_came_from(self):
        with pytest.raises(ValidationError, match=r"headers\[1\]"):
            DataTable(["Factor", 7], [TableRow(["a", "b"])])

    def test_the_cell_count_message_still_names_the_row(self):
        with pytest.raises(ValidationError, match="row 0 has 1 cells"):
            DataTable(["A", "B"], [TableRow(["only"])])

    def test_a_bare_string_is_accepted_and_validated(self):
        assert coerce_column("Factor") == Column("Factor")


class TestTheConventionCannotCreepBack:
    def test_the_template_no_longer_decides_from_a_columns_position(self):
        """
        `loop.first` was correct and compact, and it decided four things at
        once. Grep-asserted, because re-introducing it would render correctly
        today and quietly make `Column` unreachable.
        """
        assert "loop.first" not in TEMPLATE.read_text()

    def test_the_template_reads_the_resolved_keys(self):
        source = TEMPLATE.read_text()
        assert "column.align" in source
        assert 'column.kind == "text"' in source
