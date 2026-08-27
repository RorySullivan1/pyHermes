"""
Component construction rules and isolated rendering.

Every component is rendered on its own against the real templates, so a
template/context mismatch (a new template variable with no matching key in
context()) fails here rather than only in the full-email integration run.
"""

import pytest

from svc.builder import (
    AuthorBlock,
    CardGroup,
    ChartBlock,
    ContactBlock,
    DataTable,
    NumberedList,
    TextBlock,
)
from svc.builder.components import Component
from svc.builder.exceptions import ValidationError
from svc.builder.models import KpiItem, TableRow


class TestCardGroup:
    """Construction rules. Orientation, cards and the KpiStrip deprecation
    live in test_cards.py; this covers the component's place among the rest."""

    @pytest.mark.parametrize("count", [2, 3, 4])
    def test_accepts_two_to_four_items(self, count):
        items = [KpiItem(label=f"L{i}", value=f"{i}") for i in range(count)]
        CardGroup(items)

    @pytest.mark.parametrize("count", [0, 1, 5])
    def test_rejects_out_of_range_item_counts(self, count):
        items = [KpiItem(label=f"L{i}", value=f"{i}") for i in range(count)]
        with pytest.raises(ValidationError, match="2–4 items"):
            CardGroup(items)

    def test_propagates_item_validation(self):
        with pytest.raises(ValidationError, match="kpi.label"):
            CardGroup([KpiItem(label="", value="1"), KpiItem(label="B", value="2")])

    def test_renders(self, engine, kpi_items):
        html = CardGroup(kpi_items).render(engine)
        assert "5,234" in html
        assert "#4A7C59" in html


class TestDataTable:
    def test_renders(self, engine, table_rows):
        html = DataTable(headers=["Asset", "1W", "YTD"], rows=table_rows).render(engine)
        assert "Equities" in html
        assert "#4A7C59" in html

    def test_requires_headers(self, table_rows):
        with pytest.raises(ValidationError, match="header"):
            DataTable(headers=[], rows=table_rows)

    def test_requires_rows(self):
        with pytest.raises(ValidationError, match="row"):
            DataTable(headers=["A"], rows=[])

    def test_rejects_ragged_rows(self):
        # Regression: #6 — this silently rendered a misaligned table.
        with pytest.raises(ValidationError, match="cells but there are"):
            DataTable(headers=["A", "B"], rows=[TableRow(cells=["only-one"])])

    def test_error_names_the_offending_row(self):
        rows = [TableRow(cells=["a", "b"]), TableRow(cells=["c"])]
        with pytest.raises(ValidationError, match="row 1"):
            DataTable(headers=["A", "B"], rows=rows)

    def test_rejects_short_color_list(self):
        # Regression: #6 — crashed the render under StrictUndefined.
        with pytest.raises(ValidationError, match="same length"):
            DataTable(
                headers=["A", "B", "C"],
                rows=[TableRow(cells=["1", "2", "3"], colors=["#000000"])],
            )

    def test_renders_without_colors(self, engine):
        # Regression: #6 — the documented "empty = no colors" case also
        # crashed, because the template indexed colors before checking it.
        html = DataTable(headers=["A", "B"], rows=[TableRow(cells=["1", "2"])]).render(engine)
        assert "#5A5A5A" in html  # the template's fallback cell color

    def test_applies_per_cell_colors(self, engine):
        html = DataTable(
            headers=["A", "B"],
            rows=[TableRow(cells=["1", "2"], colors=["#111111", "#00FF00"])],
        ).render(engine)
        # Cell 0 is the label column and is always #3B3B3B by design;
        # only the non-first cells take their color from the list.
        assert "#00FF00" in html

    def test_alternating_row_flag(self, engine):
        rows = [TableRow(cells=["a"]), TableRow(cells=["b"])]
        table = DataTable(headers=["A"], rows=rows)
        assert [r["alt"] for r in table.context()["rows"]] == [False, True]


class TestChartBlock:
    def test_renders(self, engine):
        html = ChartBlock(image_url="https://x.test/c.png", alt_text="Chart").render(engine)
        assert "https://x.test/c.png" in html

    def test_requires_image_url(self):
        with pytest.raises(ValidationError, match="image_url"):
            ChartBlock(image_url="")


class TestTextBlock:
    def test_renders_raw_html(self, engine):
        # autoescape is OFF by design — HTML passes through untouched.
        html = TextBlock("<p>Hello <strong>world</strong></p>").render(engine)
        assert "<strong>world</strong>" in html

    def test_requires_content(self):
        with pytest.raises(ValidationError, match="content"):
            TextBlock("")


class TestNumberedList:
    def test_renders(self, engine, numbered_items):
        html = NumberedList(items=numbered_items).render(engine)
        assert "The curve steepened." in html

    def test_requires_items(self):
        with pytest.raises(ValidationError, match="at least one item"):
            NumberedList(items=[])

    def test_propagates_item_validation(self):
        from svc.builder.models import NumberedItem

        with pytest.raises(ValidationError, match="numbered_item.body"):
            NumberedList(items=[NumberedItem(number="01", title="T", body="")])


class TestAuthorBlock:
    def test_renders(self, engine):
        html = AuthorBlock(name="Jane Doe", job_title="Strategist").render(engine)
        assert "Jane Doe" in html

    def test_requires_name(self):
        with pytest.raises(ValidationError, match="name"):
            AuthorBlock(name="")


class TestContactBlock:
    def test_requires_a_heading(self):
        with pytest.raises(ValidationError):
            ContactBlock(heading="", cta_url="https://x.com/contact")

    def test_requires_a_cta_url(self):
        with pytest.raises(ValidationError):
            ContactBlock(heading="Questions?", cta_url="")

    def test_rejects_an_unsafe_cta_url(self):
        with pytest.raises(ValidationError):
            ContactBlock(heading="Questions?", cta_url="javascript:alert(1)")

    def test_renders_the_dual_cta_and_escapes_text(self, engine):
        html = ContactBlock(
            "Questions & feedback?", "Ask the desk.", "Reach out", "https://x.com/contact"
        ).render(engine)
        assert "v:roundrect" in html  # Outlook button survives
        assert "https://x.com/contact" in html
        assert "Reach out" in html
        assert "Questions &amp; feedback?" in html  # escaped by the template


class TestComponentBase:
    def test_render_without_template_path_raises(self, engine):
        class Bare(Component):
            def context(self):
                return {}

        with pytest.raises(ValidationError, match="no template_path"):
            Bare().render(engine)

    def test_context_is_abstract(self):
        with pytest.raises(NotImplementedError):
            Component().context()
