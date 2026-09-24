"""
A heat scale and an in-cell bar (#227), the fifth child of epic #217.

Both read the raw figure the format contract keeps on the cell (#225), both
take their colour from the live theme, and neither changes the text part.
"""

from __future__ import annotations

import re

import pytest

from qa.lint import lint_html
from svc.builder import DataTable, FullWidth, HeatScale
from svc.builder.email import Email
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.filters import heat_color
from svc.builder.formats import pct
from svc.builder.models import Cell, Column, TableRow
from svc.builder.theming import DEFAULT_THEME, SLATE_THEME


def one_place(value: float) -> str:
    return pct(value, 1)


SCALE = HeatScale(0.0, 0.10)


def _table(scale=SCALE, bar=False, rows=None) -> DataTable:
    return DataTable(
        ["Fund", Column("1Y", format=one_place, scale=scale, bar=bar)],
        rows or [TableRow(["High", 0.10]), TableRow(["Mid", 0.05]), TableRow(["Low", 0.0])],
    )


def _backgrounds(html: str) -> list[str]:
    body = html[html.index("<tbody>") :]
    return re.findall(r'<td align="right" style="[^"]*background-color: (#[0-9A-F]{6});"', body)


def _email(table: DataTable, theme: str = "classic") -> str:
    email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C", "theme": theme})
    email.add_section(FullWidth(content=table))
    return email.render()


class TestAHeatScaleValidates:
    @pytest.mark.parametrize(
        ("low", "high", "mid"), [(1, 1, None), (2, 1, None), (0, 1, 1), (0, 1, -1), (0, 1, 2)]
    )
    def test_a_bad_range_raises(self, low, high, mid):
        with pytest.raises(ValidationError, match="heat_scale"):
            HeatScale(low, high, mid).validate()

    @pytest.mark.parametrize("bad", ["0", True, None])
    def test_a_non_number_raises_by_name(self, bad):
        with pytest.raises(ValidationError, match="heat_scale.low"):
            HeatScale(bad, 1).validate()

    def test_a_column_whose_cells_have_no_figure_raises_naming_the_cell(self):
        with pytest.raises(ValidationError, match=r"row 0, column '1Y'.*'10%'"):
            _table(rows=[TableRow(["High", "10%"])])

    def test_a_text_column_refuses_both(self):
        with pytest.raises(ValidationError, match="text column"):
            DataTable([Column("Fund", scale=SCALE)], [TableRow([Cell("x", value=1)])])

    def test_a_scale_that_is_not_a_heat_scale_raises(self):
        with pytest.raises(ValidationError, match="column.scale"):
            Column("1Y", scale=(0, 1)).validate()  # type: ignore[arg-type]


class TestTheThemeColoursTheScale:
    def test_the_ends_are_the_themes_and_the_middle_is_pinned(self):
        high, mid, low = _backgrounds(_table().render(TemplateEngine()))
        assert high == DEFAULT_THEME.semantic.positive
        assert low == DEFAULT_THEME.palette.surface
        assert mid == "#A5BEAC"

    def test_slate_recolours_the_same_table(self):
        classic = _backgrounds(_email(_table()))
        slate = _backgrounds(_email(_table(), "slate"))
        assert slate[0] == SLATE_THEME.semantic.positive != classic[0]
        assert slate[2] == SLATE_THEME.palette.surface

    def test_a_mid_diverges_to_the_negative_token(self):
        rows = [TableRow(["Up", 0.10]), TableRow(["Flat", 0.05]), TableRow(["Down", 0.0])]
        up, flat, down = _backgrounds(
            _table(HeatScale(0.0, 0.10, mid=0.05), rows=rows).render(TemplateEngine())
        )
        assert (up, flat, down) == (
            DEFAULT_THEME.semantic.positive,
            DEFAULT_THEME.palette.surface,
            DEFAULT_THEME.semantic.negative,
        )

    def test_a_figure_outside_the_range_is_clamped(self):
        rows = [TableRow(["Above", 0.5]), TableRow(["Below", -0.5])]
        above, below = _backgrounds(_table(rows=rows).render(TemplateEngine()))
        assert above == DEFAULT_THEME.semantic.positive and below == DEFAULT_THEME.palette.surface


class TestTheFilterIsByteExact:
    def test_it_pins_the_midpoint(self):
        assert heat_color(0.5, "#FFFFFF", "#4A7C59") == "#A5BEAC"

    def test_the_ends_are_the_ends(self):
        assert heat_color(0, "#FFFFFF", "#4A7C59") == "#FFFFFF"
        assert heat_color(1, "#FFFFFF", "#4A7C59") == "#4A7C59"

    @pytest.mark.parametrize("position", [-0.1, 1.1, "0.5", True])
    def test_a_bad_position_raises(self, position):
        with pytest.raises(ValidationError):
            heat_color(position, "#FFFFFF", "#4A7C59")

    def test_a_bad_end_raises(self):
        with pytest.raises(ValidationError):
            heat_color(0.5, "white", "#4A7C59")


class TestPrecedence:
    def test_an_explicit_background_beats_the_scale(self):
        rows = [TableRow(["High", Cell(value=0.10, background="#FBF3E2")])]
        assert _backgrounds(_table(rows=rows).render(TemplateEngine())) == ["#FBF3E2"]

    def test_a_subhead_and_a_total_take_neither(self):
        rows = [
            TableRow(["Book"], kind="subhead"),
            TableRow(["High", 0.10]),
            TableRow(["Total", Cell("10.0%")], kind="total"),
        ]
        html = _table(bar=True, rows=rows).render(TemplateEngine())
        assert html.count('class="cell-bar"') == 1
        assert _backgrounds(html)[-1] == DEFAULT_THEME.palette.surface


class TestTheBar:
    def test_it_is_a_presentation_table_whose_width_is_the_percentage(self):
        rows = [TableRow(["A", 0.08]), TableRow(["B", 0.02]), TableRow(["C", -0.01])]
        html = _table(scale=None, bar=True, rows=rows).render(TemplateEngine())
        rows = re.findall(r'class="cell-bar"[^>]*><tr>(.*?)</tr>', html)
        widths = [re.findall(r'width="(\d+)%"', row) for row in rows]
        assert widths == [["100"], ["25", "75"], ["100"]]
        assert "background-color" not in rows[2], "a negative figure draws no bar"

    def test_a_scale_sets_what_a_full_bar_means(self):
        html = _table(bar=True, rows=[TableRow(["A", 0.05])]).render(TemplateEngine())
        assert re.search(r'class="cell-bar"[^>]*><tr><td width="50%"', html)

    def test_the_bar_takes_the_accent_and_the_size_token(self):
        html = _email(_table(scale=None, bar=True))
        bar = html[html.index('class="cell-bar"') :]
        bar = bar[: bar.index("</table>")]
        assert f"background-color: {DEFAULT_THEME.palette.accent}" in bar
        assert "height: 6px" in bar and "padding: 0 !important" in bar

    def test_every_lint_rule_stays_clean(self):
        html = _email(_table(bar=True))
        assert not [f for f in lint_html(html) if f.severity.value == "error"]


class TestTheTextPartIsUntouched:
    def test_a_scale_and_a_bar_project_to_the_same_text(self):
        plain = _table(scale=None).text()
        assert _table().text() == plain
        assert _table(bar=True).text() == plain
