"""
Column groups (#223): a spanning header tier, the first child of epic #217.

Held here: a group is validated at construction, the markup and the text part
each read the groups and ``resolved_columns()`` rather than each other, and
the ``table-header-tier`` lint rule fires in every direction it claims.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import ColumnGroup, DataTable
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import TableRow
from qa.lint import lint_html

GROUPS = [ColumnGroup("Share class"), ColumnGroup("Annualised", 3)]


def _table(groups=GROUPS) -> DataTable:
    return DataTable(
        ["Fund", "1Y", "3Y", "5Y"],
        [TableRow(["Accumulation", "4.5%", "6.1%", "7.0%"])],
        groups=groups,
    )


def _thead(html: str) -> str:
    return html[html.index("<thead>") : html.index("</thead>")]


class TestAGroupValidatesAtConstruction:
    @pytest.mark.parametrize("span", [0, -1, True, 1.5])
    def test_a_span_that_is_not_a_positive_int_raises(self, span):
        with pytest.raises(ValidationError, match="column_group.span"):
            ColumnGroup("Annualised", span).validate()

    def test_a_blank_label_raises(self):
        with pytest.raises(ValidationError, match="column_group.label"):
            _table([ColumnGroup(""), ColumnGroup("Annualised", 3)])

    @pytest.mark.parametrize("spans", [(1, 2), (2, 3), (4, 1)])
    def test_spans_that_miscount_the_columns_raise(self, spans):
        with pytest.raises(ValidationError, match="data_table.groups"):
            _table([ColumnGroup(f"G{i}", span) for i, span in enumerate(spans)])

    def test_a_group_may_cover_one_column(self):
        assert _table().groups[0].span == 1

    def test_a_non_group_raises_by_name(self):
        with pytest.raises(ValidationError, match=r"data_table.groups\[0\]"):
            _table([("Annualised", 4)])


class TestNoGroupsIsByteIdentical:
    def test_the_head_is_one_row(self):
        html = _table(None).render(TemplateEngine())
        assert _thead(html).count("<tr") == 1
        assert "colspan" not in html and "colgroup" not in html

    def test_empty_groups_render_as_none(self):
        engine = TemplateEngine()
        assert _table([]).render(engine) == _table(None).render(engine)
        assert _table([]).text() == _table(None).text()


class TestBothProjectionsReadTheGroups:
    def test_the_markup_carries_a_tier_above_the_heads(self):
        table = _table()
        head = _thead(table.render(TemplateEngine()))
        rows = head.split("<tr")[1:]
        assert len(rows) == 2
        spans = [int(n) for n in re.findall(r'scope="colgroup" colspan="(\d+)"', rows[0])]
        assert spans == [group.span for group in table.groups]
        assert sum(spans) == len(table.resolved_columns())
        for group in table.groups:
            assert f">{group.label}</th>" in rows[0]
        assert rows[1].count('scope="col"') == len(table.resolved_columns())

    def test_the_text_part_centres_each_label_over_its_columns(self):
        table = _table()
        group_line, head_line, rule, *_ = table.text().splitlines()
        widths = [len(dash) for dash in rule.split("  ")]
        start = 0
        for group in table.groups:
            covered = sum(widths[: start + group.span]) + 2 * (start + group.span - 1)
            left = sum(widths[:start]) + 2 * start
            assert group.label in group_line[left:covered]
            start += group.span
        assert head_line.split()[0] == table.resolved_columns()[0].header

    def test_a_label_wider_than_its_columns_widens_the_last_one(self):
        table = DataTable(
            ["A", "B"], [TableRow(["x", "1"])], groups=[ColumnGroup("L"), ColumnGroup("Longer")]
        )
        group_line, _, rule, *_ = table.text().splitlines()
        assert rule.split("  ")[1] == "-" * len("Longer")
        assert group_line.endswith("Longer")


class TestTheHeaderTierRule:
    """A guard that passes with the bug present is a comment (#130)."""

    @pytest.fixture()
    def html(self):
        return _table().render(TemplateEngine())

    def test_the_shipped_render_is_clean(self, html):
        assert not [f for f in lint_html(html) if f.rule_id == "table-header-tier"]

    def test_a_span_in_the_body_fires(self, html):
        broken = html.replace("<td align", '<td colspan="2" align', 1)
        assert "table-header-tier" in {f.rule_id for f in lint_html(broken)}

    @pytest.mark.parametrize("span", ["2", "4"])
    def test_spans_that_miscount_the_columns_fire(self, html, span):
        broken = html.replace('colspan="3"', f'colspan="{span}"')
        assert "table-header-tier" in {f.rule_id for f in lint_html(broken)}

    def test_a_spanning_head_without_colgroup_scope_fires(self, html):
        broken = html.replace('scope="colgroup" colspan="3"', 'colspan="3"')
        assert "table-header-tier" in {f.rule_id for f in lint_html(broken)}

    @pytest.mark.parametrize("medium", ["email", "document", "brochure", "html"])
    def test_it_applies_to_every_medium(self, html, medium):
        broken = html.replace("<td align", '<td colspan="2" align', 1)
        assert "table-header-tier" in {f.rule_id for f in lint_html(broken, medium)}
