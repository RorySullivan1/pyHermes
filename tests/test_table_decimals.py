"""
Decimal alignment and a units row (#226), the fourth child of epic #217.

The padding is computed once in Python and handed to both projections, so
the markup's non-breaking spaces and the text part's spaces are one count.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import ColumnGroup, DataTable, FullWidth
from pyhermes.builder.email import Email
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import Column, TableRow
from pyhermes.builder.typography import FontStack, FontTheme
from qa.screenshots import VIEWPORTS, _launch, _load_playwright, available

FIGURES = ["4.5%", "12.25%", "7%"]


def _table(**column) -> DataTable:
    spec = {"align_decimal": True, **column}
    return DataTable(
        ["Fund", Column("1Y", **spec)],
        [TableRow([name, figure]) for name, figure in zip("ABC", FIGURES, strict=True)],
    )


def _cells(html: str) -> list[str]:
    """The figure column's cell contents, in row order."""
    body = html[html.index("<tbody>") :]
    return re.findall(r"<td [^>]*>([^<]*)</td>", body)


class TestOneCountReachesBothProjections:
    def test_the_markup_and_the_text_hold_the_same_string(self):
        table = _table()
        markup = [cell.replace("&nbsp;", " ") for cell in _cells(table.render(TemplateEngine()))]
        pads = [row[1] for row in table._pads()]
        assert markup == [text + " " * pad for text, pad in zip(FIGURES, pads, strict=True)]
        _, _, *rows = table.text().splitlines()
        for row, cell in zip(rows, markup, strict=True):
            assert row.split("  ", 1)[1].strip() == cell.strip()
            assert row.endswith(cell.rstrip())

    def test_the_points_share_one_column_in_the_text_part(self):
        _, _, *rows = _table().text().splitlines()
        figures = dict(zip(FIGURES, rows, strict=True))
        point = figures["12.25%"].index(".")
        assert figures["4.5%"].index(".") == point
        # No point: the suffix stands where it would, the 7 over the units digit.
        assert figures["7%"].index("%") == point

    def test_an_unaligned_column_has_no_padding(self):
        html = _table(align_decimal=False).render(TemplateEngine())
        assert "&nbsp;" not in html

    def test_a_text_column_refuses_it_by_name(self):
        with pytest.raises(ValidationError, match="column.align_decimal"):
            DataTable([Column("Fund", align_decimal=True), "1Y"], [TableRow(["A", "1.0"])])

    def test_a_subhead_is_not_padded(self):
        table = DataTable(
            ["Fund", Column("1Y", align_decimal=True)],
            [TableRow(["Equities"], kind="subhead"), TableRow(["A", "1.25"])],
        )
        assert table._pads()[0] == [0, 0]


class TestAProportionalFaceStillGetsThePadding:
    """The decision #226 pins: the padding is emitted whatever the face."""

    def test_a_sans_numeric_face_keeps_the_padding(self):
        fonts = FontTheme(numeric=FontStack("Helvetica", "Arial", "sans-serif"))
        email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
        email.metadata.font_theme = fonts
        email.add_section(FullWidth(content=_table()))
        html = email.render()
        assert "Helvetica, Arial, sans-serif" in html
        assert "7%&nbsp;&nbsp;&nbsp;" in html


class TestTheUnitsRow:
    def _table(self) -> DataTable:
        return DataTable(
            ["Fund", Column("1Y", unit="%"), Column("Vol", unit="ann."), "Rank"],
            [TableRow(["A", "4.5", "12", "1"])],
            groups=[ColumnGroup("Share class"), ColumnGroup("Figures", 3)],
        )

    def test_it_is_a_row_of_heads_inside_the_thead(self):
        table = self._table()
        head = table.render(TemplateEngine())
        head = head[head.index("<thead>") : head.index("</thead>")]
        rows = head.split("<tr")[1:]
        assert len(rows) == 3, "groups, heads, units"
        units = re.findall(r'<th scope="col"[^>]*>([^<]*)</th>', rows[2])
        assert units == [column.unit for column in table.resolved_columns()]

    def test_the_text_part_prints_it_under_the_heads(self):
        group, head, units, rule, *_ = self._table().text().splitlines()
        assert head.split() == ["Fund", "1Y", "Vol", "Rank"]
        assert units.split() == ["%", "ann."]
        assert set(rule) <= {"-", " "}

    def test_no_units_means_no_row(self):
        table = DataTable(["Fund", "1Y"], [TableRow(["A", "4.5"])])
        head = table.render(TemplateEngine())
        assert head[head.index("<thead>") : head.index("</thead>")].count("<tr") == 1

    def test_a_unit_is_escaped(self):
        table = DataTable(["Fund", Column("1Y", unit="<b>")], [TableRow(["A", "1"])])
        assert "&lt;b&gt;" in table.render(TemplateEngine())

    def test_a_unit_that_is_not_text_raises(self):
        with pytest.raises(ValidationError, match="column.unit"):
            Column("1Y", unit=5).validate()  # type: ignore[arg-type]


_POINTS = """() => [...document.querySelectorAll('.data-table tbody td')].map(td => {
  const node = td.firstChild, text = node ? node.textContent : '';
  const at = text.lastIndexOf('.') >= 0 ? text.lastIndexOf('.') : text.indexOf('%');
  if (!node || at < 0) return null;
  const range = document.createRange();
  range.setStart(node, at); range.setEnd(node, at + 1);
  return range.getBoundingClientRect().left;
})"""


@pytest.mark.skipif(not available(), reason='no browser; the "[qa]" extra')
@pytest.mark.parametrize("viewport", sorted(VIEWPORTS))
def test_chromium_puts_the_points_in_one_column(viewport):
    # "7%" has no point; its '%' stands where the point would.
    email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
    email.add_section(FullWidth(content=_table()))
    width, height = VIEWPORTS[viewport]
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.set_content(email.render())
        points = page.evaluate(_POINTS)
        browser.close()
    four, twelve, seven = points
    assert four == pytest.approx(twelve, abs=0.5)
    assert seven == pytest.approx(twelve, abs=0.5)


class TestAMarkerHangsPastThePoint:
    """Found on the factsheet's first raster (#228): ``11.94¹`` pulled its column askew."""

    def _table(self) -> DataTable:
        return DataTable(
            ["Basis", Column("Since", align_decimal=True)],
            [TableRow(["NAV", "11.94[^1]"]), TableRow(["Price", "11.9"])],
            notes=["Annualised from inception."],
        )

    def test_the_markup_measures_the_figure_without_its_superscript(self):
        cells = _cells_with_markers(self._table().render(TemplateEngine()))
        assert cells == ["11.94", "11.9&nbsp;"]

    def test_the_text_part_counts_the_spelled_marker(self):
        _, _, nav, price = self._table().text().splitlines()
        assert nav.index(".") == price.index(".")


def _cells_with_markers(html: str) -> list[str]:
    body = html[html.index("<tbody>") :]
    return re.findall(r"<td [^>]*>([^<]*)", body)
