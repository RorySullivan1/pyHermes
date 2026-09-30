"""
Blocks that hold blocks: a Stack in a cell (#262), a split inside a cell (#263).
"""

from __future__ import annotations

import pytest

from pyhermes.builder import (
    CardGroup,
    Contents,
    DataTable,
    Email,
    FourColumn,
    FullWidth,
    ImageBlock,
    Stack,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import KpiItem, TableRow
from qa.fixtures._png import solid_png

FACTS = {"email_subject": "S", "firm_name": "F", "campaign_name": "C"}


def _table(caption: str) -> DataTable:
    return DataTable(["A", "B"], [TableRow(["x", "1"])], label="Exhibit", caption=caption)


def _email(*sections) -> Email:
    email = Email(FACTS)
    for section in sections:
        email.add_section(section)
    return email


class TestAStackRendersItsBlocksInOrder:
    def test_in_a_full_width_section(self):
        stack = Stack([TextBlock("<p>First</p>"), TextBlock("<p>Second</p>")])
        html = _email(FullWidth(stack, title="T")).render()
        assert html.index("First") < html.index("Second")

    def test_in_a_column(self):
        stack = Stack([CardGroup([KpiItem("a", "1"), KpiItem("b", "2")]), TextBlock("<p>Note</p>")])
        html = _email(TwoColumn("30-70", left=stack, right=TextBlock("<p>R</p>"))).render()
        assert html.index(">a<") < html.index("Note") < html.index(">R<")

    def test_each_gap_but_the_last_is_block_gap(self):
        html = Stack([TextBlock("<p>a</p>"), TextBlock("<p>b</p>")], spacing={"block_gap": 7})
        rendered = _email(FullWidth(html)).render()
        assert rendered.count("padding:0 0 7px 0;") == 1
        assert rendered.count('<td style="padding:0;">') >= 1


class TestTheDocumentSeesInsideAStack:
    def test_exhibits_number_in_reading_order(self):
        email = _email(
            FullWidth(_table("Before")),
            FullWidth(Stack([TextBlock("<p>x</p>"), _table("Inside")])),
        )
        html = email.render()
        assert "Exhibit 1 · Before" in html and "Exhibit 2 · Inside" in html

    def test_notes_inside_are_numbered_with_the_rest(self):
        email = _email(
            FullWidth(TextBlock("<p>a[^1]</p>", notes=["first"])),
            FullWidth(Stack([TextBlock("<p>b[^1]</p>", notes=["second"])])),
        )
        text = email.text()
        assert "[1] first" in text and "[2] second" in text

    def test_a_reference_to_an_exhibit_inside_lands(self):
        link = TextBlock('<p>See <a class="xref" href="#exhibit-1">Exhibit 1</a>.</p>')
        _email(FullWidth(Stack([_table("Inside"), link]))).render()

    def test_a_contents_inside_is_filled(self):
        email = _email(
            FullWidth(Stack([Contents(), TextBlock("<p>x</p>")]), title="Index"),
            FullWidth(TextBlock("<p>y</p>"), title="Rates"),
        )
        assert 'href="#rates"' in email.render()

    def test_an_attached_image_inside_reaches_the_manifest(self):
        image = EmailImage.attached(solid_png(20, 10, (1, 2, 3)), alt="Mark", width=20)
        email = _email(FullWidth(Stack([TextBlock("<p>x</p>"), ImageBlock(image)])))
        assert [asset.content_id for asset in email.assets()] == [image.content_id]
        assert f"cid:{image.content_id}" in email.render()

    def test_the_text_part_reads_the_blocks_in_order(self):
        stack = Stack([TextBlock("<p>First</p>"), _table("T"), TextBlock("<p>Last</p>")])
        text = _email(FullWidth(stack, title="Section")).text()
        assert text.index("First") < text.index("Exhibit 1 · T") < text.index("Last")


class TestAStackRefusesWhatIsNotAList:
    def test_an_empty_one(self):
        with pytest.raises(ValidationError, match="at least one"):
            Stack([])

    def test_a_single_component_not_in_a_list(self):
        with pytest.raises(ValidationError, match="list of components"):
            Stack(TextBlock("<p>x</p>"))  # type: ignore[arg-type]

    def test_a_section_among_the_blocks(self):
        with pytest.raises(ValidationError, match="item 1 must be a Component, got FullWidth"):
            Stack([TextBlock("<p>x</p>"), FullWidth(TextBlock("<p>y</p>"))])  # type: ignore[list-item]


def test_a_mobile_token_inside_a_stack_is_refused_on_an_email():
    cards = CardGroup([KpiItem("a", "1"), KpiItem("b", "2")], spacing={"card_pad_x": 4})
    with pytest.raises(ValidationError, match="card_pad_x"):
        _email(FullWidth(Stack([cards])))


class TestWeights:
    """#264: a split takes any weights, and the named presets are weights too."""

    @pytest.mark.parametrize("size_theme", ["standard", "compact", "spacious"])
    def test_sixty_forty_fills_the_content_width_at_every_density(self, size_theme):
        from pyhermes.builder import SIZE_SCHEMES
        from pyhermes.builder.sizing import column_layout

        scheme = SIZE_SCHEMES[size_theme]
        widths = [column.width for column in column_layout((60, 40), scheme)]
        assert sum(widths) + scheme.space.gutter == scheme.frame.inner
        email = Email({**FACTS, "size_theme": size_theme})
        email.add_section(TwoColumn((60, 40), TextBlock("<p>L</p>"), TextBlock("<p>R</p>")))
        rendered = email.render()
        for width in widths:
            assert f'width="{width}"' in rendered

    @pytest.mark.parametrize(
        ("preset", "weights"), [("30-70", (30, 70)), ("50-50", (1, 1)), ("70-30", (7, 3))]
    )
    def test_a_preset_renders_as_its_own_weights(self, preset, weights):
        def render(ratio):
            return _email(TwoColumn(ratio, TextBlock("<p>L</p>"), TextBlock("<p>R</p>"))).render()

        assert render(preset) == render(weights)

    def test_three_columns_take_weights_too(self):
        section = ThreeColumn((2, 1, 1), TextBlock("<p>a</p>"), TextBlock("<p>b</p>"))
        assert section.ratio == (2, 1, 1)
        assert 'width="292"' in _email(section).render()

    @pytest.mark.parametrize(
        ("ratio", "message"),
        [
            ((95, 5), "column 2 30px wide"),
            ((1,), "takes 2 positive weights"),
            ((1, 0), "takes 2 positive weights"),
            ((1, True), "takes 2 positive weights"),
            ("60-40", "or 2 weights such as"),
        ],
    )
    def test_a_bad_ratio_is_refused_at_construction(self, ratio, message):
        with pytest.raises(ValidationError, match=message):
            TwoColumn(ratio, TextBlock("<p>L</p>"), TextBlock("<p>R</p>"))

    def test_the_floor_is_a_config_value(self):
        from pyhermes.config import config_override

        with config_override(min_column_px=20):
            TwoColumn((95, 5), TextBlock("<p>L</p>"), TextBlock("<p>R</p>"))


class TestFourColumn:
    def _columns(self):
        return [TextBlock(f"<p>c{n}</p>") for n in range(4)]

    def test_four_equal_quarters_fill_the_frame(self):
        html = _email(FourColumn(self._columns(), title="Four")).render()
        assert html.count('width="142"') >= 4
        assert html.index("c0") < html.index("c1") < html.index("c2") < html.index("c3")

    def test_it_takes_weights(self):
        from pyhermes.builder import STANDARD_SIZES
        from pyhermes.builder.sizing import column_layout

        section = FourColumn(self._columns(), ratio=(2, 1, 1, 1))
        wide = column_layout((2, 1, 1, 1), STANDARD_SIZES)[0].width
        assert wide > 142 and f'width="{wide}"' in _email(section).render()

    def test_an_empty_column_keeps_its_place(self):
        columns = self._columns()
        columns[2] = None
        section = FourColumn(columns)
        assert [c.content for c in section.components()] == ["<p>c0</p>", "<p>c1</p>", "<p>c3</p>"]
        assert _email(section).text().count("c") >= 3

    @pytest.mark.parametrize(
        ("columns", "message"),
        [
            ([TextBlock("<p>a</p>")] * 3, "four columns, got 3"),
            ([None] * 4, "at least one filled"),
            ([TextBlock("<p>a</p>"), "b", None, None], "column 2 must be a Component"),
        ],
    )
    def test_a_bad_row_is_refused(self, columns, message):
        with pytest.raises(ValidationError, match=message):
            FourColumn(columns)
