"""
Card, CardGroup, and the KpiStrip deprecation.

Highlight used to be a container type; it is now a property of any
container (covered in test_containers.py). KpiStrip used to be a component;
it is now a deprecated alias for a horizontal CardGroup.
"""

import warnings

import pytest

from pyhermes.builder import CardGroup, FullWidth, KpiStrip
from pyhermes.builder.enums import CardOrientation
from pyhermes.builder.exceptions import EmailBuilderError, ValidationError
from pyhermes.builder.models import Card, KpiItem


def cards(n: int) -> list[Card]:
    return [Card(label=f"L{i}", value=str(i)) for i in range(n)]


class TestCardModel:
    def test_value_only_card(self):
        Card(label="S&P 500", value="5,234").validate()

    def test_prose_only_card(self):
        Card(label="Positioning", body="<p>Wording, no figure.</p>").validate()

    def test_value_and_prose_together(self):
        Card(label="Rates", value="4.28%", body="<p>The curve steepened.</p>").validate()

    def test_label_is_required(self):
        with pytest.raises(ValidationError, match="card.label"):
            Card(label="", value="5").validate()

    def test_a_label_alone_is_rejected(self):
        # A card with nothing to say is a caller mistake, not a blank card.
        with pytest.raises(ValidationError, match="requires a 'value' or a 'body'"):
            Card(label="Lonely").validate()

    def test_colour_is_validated(self):
        with pytest.raises(ValidationError, match="hex color"):
            Card(label="L", value="1", color="not-a-color").validate()

    def test_rejections_are_catchable_as_the_base_class(self):
        with pytest.raises(EmailBuilderError):
            Card(label="").validate()


class TestKpiItemIsACard:
    def test_kpi_item_is_a_card(self):
        assert isinstance(KpiItem("S&P 500", "5,234"), Card)

    def test_positional_construction_is_unchanged(self):
        # The field order Card introduced must match KpiItem's original one,
        # or every existing positional call silently changes meaning.
        kpi = KpiItem("S&P 500", "5,234.18", "#4A7C59", "+1.42% WoW")
        assert (kpi.label, kpi.value, kpi.color, kpi.sublabel) == (
            "S&P 500",
            "5,234.18",
            "#4A7C59",
            "+1.42% WoW",
        )

    def test_a_kpi_still_requires_a_value(self):
        # Stricter than Card: a KPI with prose but no figure is not a KPI.
        with pytest.raises(ValidationError, match="kpi.value"):
            KpiItem(label="Rates", body="<p>prose</p>").validate()

    def test_kpi_label_is_required(self):
        with pytest.raises(ValidationError, match="kpi.label"):
            KpiItem(label="", value="5").validate()

    def test_cards_and_kpi_items_mix_in_one_group(self, engine):
        group = CardGroup([KpiItem("A", "1"), Card("B", "2")], orientation="vertical")
        assert "A" in group.render(engine)


class TestCardGroupOrientation:
    def test_defaults_to_horizontal(self):
        assert CardGroup(cards(2)).orientation == "horizontal"

    @pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
    def test_both_orientations_render(self, engine, orientation):
        html = CardGroup(cards(2), orientation=orientation).render(engine)
        assert "L0" in html and "L1" in html

    def test_rejects_an_unknown_orientation(self):
        with pytest.raises(ValidationError, match="Unsupported orientation"):
            CardGroup(cards(2), orientation="diagonal")

    def test_accepts_an_orientation_enum_member(self, engine):
        html = CardGroup(cards(2), orientation=CardOrientation.VERTICAL).render(engine)
        assert html.count("<tr>") == 2  # vertical: one row per card

    def test_horizontal_lays_cards_across_one_row(self, engine):
        html = CardGroup(cards(2), orientation="horizontal").render(engine)
        assert html.count("<tr>") == 1
        assert "width: 50.0%" in html

    def test_vertical_gives_each_card_its_own_row(self, engine):
        html = CardGroup(cards(3), orientation="vertical").render(engine)
        assert html.count("<tr>") == 3

    def test_horizontal_keeps_the_mobile_stacking_hook(self, engine):
        # base.html collapses .kpi-cell to full width on small screens.
        html = CardGroup(cards(3), orientation="horizontal").render(engine)
        assert "kpi-cell" in html and "kpi-cell-last" in html


class TestCardGroupLimits:
    @pytest.mark.parametrize("count", [2, 3, 4])
    def test_horizontal_accepts_two_to_four(self, count):
        CardGroup(cards(count), orientation="horizontal")

    @pytest.mark.parametrize("count", [0, 1, 5])
    def test_horizontal_rejects_out_of_range(self, count):
        with pytest.raises(ValidationError, match="2–4 items"):
            CardGroup(cards(count), orientation="horizontal")

    @pytest.mark.parametrize("count", [1, 2, 7])
    def test_vertical_has_no_upper_bound(self, engine, count):
        # A stack is not width-constrained, so the 2-4 rule must not apply.
        CardGroup(cards(count), orientation="vertical").render(engine)

    def test_vertical_still_needs_at_least_one(self):
        with pytest.raises(ValidationError, match="at least one item"):
            CardGroup([], orientation="vertical")

    def test_card_validation_propagates(self):
        with pytest.raises(ValidationError, match="card.label"):
            CardGroup([Card("", "1"), Card("B", "2")])


class TestCardBodyRendering:
    def test_body_renders_in_a_vertical_stack(self, engine):
        html = CardGroup([Card("Note", body="<em>prose</em>")], orientation="vertical").render(
            engine
        )
        assert "<em>prose</em>" in html

    def test_body_is_an_html_field_and_stays_raw(self, engine):
        # Consistent with TextBlock.content and NumberedItem.body.
        html = CardGroup(
            [Card("Note", body="<strong>bold</strong>")], orientation="vertical"
        ).render(engine)
        assert "&lt;strong&gt;" not in html

    def test_label_and_value_are_still_escaped(self, engine):
        html = CardGroup([Card("A & B", "1 & 2")], orientation="vertical").render(engine)
        assert "A &amp; B" in html and "1 &amp; 2" in html

    def test_a_card_without_a_value_omits_the_numeral(self, engine):
        html = CardGroup([Card("Note", body="<p>x</p>")], orientation="vertical").render(engine)
        assert "font-size: 21px" not in html


class TestKpiStripDeprecation:
    def test_still_works(self, engine):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            html = KpiStrip(items=cards(3)).render(engine)
        assert "L0" in html

    def test_warns(self, engine):
        with pytest.warns(DeprecationWarning, match="CardGroup"):
            KpiStrip(items=cards(3))

    def test_is_a_horizontal_card_group(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            strip = KpiStrip(items=cards(3))
        assert isinstance(strip, CardGroup)
        assert strip.orientation == "horizontal"

    def test_items_attribute_still_reads(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            strip = KpiStrip(items=cards(2))
        assert strip.items == strip.cards

    def test_renders_identically_to_the_horizontal_group(self, engine):
        group = cards(3)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            legacy = KpiStrip(items=group).render(engine)
        assert legacy == CardGroup(group, orientation="horizontal").render(engine)


def test_a_stack_inside_a_highlighted_container(engine):
    html = FullWidth(
        content=CardGroup(cards(2), orientation="vertical"),
        title="Themes",
        highlight=True,
    ).render(engine)
    assert "#F8F7F5" in html and "L0" in html
