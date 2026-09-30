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
    FullWidth,
    ImageBlock,
    Stack,
    TextBlock,
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
