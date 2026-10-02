"""
A block or a section shown in chosen media only (#365): ``Only`` and ``OnlySections``.

Decided in Python, so an omitted block emits no bytes, carries no image into
the manifest and projects no text. Route B, the owner's decision of
2026-10-01: two wrappers, and no ``media=`` field on any existing class.
"""

from __future__ import annotations

import pytest

from pyhermes.builder import (
    Button,
    Contents,
    DataTable,
    Email,
    FullWidth,
    ImageBlock,
    Only,
    OnlySections,
    Stack,
    TextBlock,
    TwoColumn,
    ValidationError,
)
from pyhermes.builder.images import EmailImage
from pyhermes.builder.medium import DEFAULT_MEDIUM, SHIPPED_MEDIA
from pyhermes.builder.models import Footnote, TableRow
from pyhermes.document import Page, PagedDocument
from qa.fixtures._png import solid_png

FACTS = {"firm_name": "F", "campaign_name": "C"}
NOTE_PNG = solid_png(40, 40, (200, 10, 10))


def download() -> Only:
    return Only(Button("Download the PDF", "https://example.com/review.pdf"), media="email")


def page_note() -> OnlySections:
    image = EmailImage.attached(NOTE_PNG, alt="Page note mark", width=40)
    return OnlySections(
        [FullWidth(Stack([TextBlock("<p>PRINTNOTE</p>"), ImageBlock(image)]), title="Page note")],
        media=("document",),
    )


def tree(document):
    document.add_section(FullWidth(Contents(), title="In this issue"))
    document.add_section(
        FullWidth(Stack([TextBlock("<p>Body copy</p>"), download()]), title="Intro")
    )
    document.add_section(page_note())
    document.add_section(FullWidth(TextBlock("<p>Closing</p>"), title="Close"))
    return document


@pytest.fixture
def email():
    return tree(Email({"email_subject": "S", **FACTS}))


@pytest.fixture
def paper():
    return tree(PagedDocument(FACTS))


class TestAnEmailOnlyBlock:
    def test_it_renders_in_the_email(self, email):
        assert "Download the PDF" in email.render()
        assert "Download the PDF" in email.text()

    def test_it_is_absent_from_the_paged_render_bytes_included(self, paper):
        html = paper.render()
        assert "Download the PDF" not in html and "review.pdf" not in html
        assert "Download the PDF" not in paper.text()

    def test_it_leaves_no_gap_in_a_stack(self, paper):
        with_wrapper = PagedDocument(FACTS).add_section(
            FullWidth(Stack([TextBlock("<p>Body copy</p>"), download()]))
        )
        without = PagedDocument(FACTS).add_section(
            FullWidth(Stack([TextBlock("<p>Body copy</p>")]))
        )
        assert with_wrapper.render() == without.render()


class TestAPrintOnlySection:
    def test_it_renders_on_paper(self, paper):
        assert "PRINTNOTE" in paper.render()
        assert "PRINTNOTE" in paper.text()

    def test_it_is_absent_from_the_email_bytes_included(self, email):
        html = email.render()
        assert "PRINTNOTE" not in html and 'id="page-note"' not in html
        assert "PRINTNOTE" not in email.text()

    def test_it_leaves_no_band_or_line_behind(self):
        def built(*extra):
            document = Email({"email_subject": "S", **FACTS})
            document.add_section(FullWidth(TextBlock("<p>a</p>")))
            for section in extra:
                document.add_section(section)
            document.add_section(FullWidth(TextBlock("<p>b</p>")))
            return document

        assert built(page_note()).render() == built().render()
        assert built(page_note()).text() == built().text()

    def test_its_image_leaves_the_manifest(self, email, paper):
        assert email.assets() == []
        assert [asset.filename for asset in paper.assets()] != []
        assert all(image.alt != "Page note mark" for image in email.images())

    def test_a_contents_lists_it_only_where_it_is_shown(self, email, paper):
        assert "Page note" not in email.render()
        assert 'href="#page-note"' in paper.render()

    def test_a_link_to_it_from_the_email_is_named(self):
        document = Email({"email_subject": "S", **FACTS})
        document.add_section(page_note())
        document.add_section(FullWidth(TextBlock('<p><a href="#page-note">see</a></p>')))
        with pytest.raises(ValidationError, match="#page-note"):
            document.render()


class TestTheBlocksOwnMedium:
    def test_a_block_outside_any_document_shows_in_every_walk(self):
        block = download()
        assert block.text() and block.children()

    def test_a_block_rendered_alone_follows_the_engines_medium(self):
        from pyhermes.builder.engine import TemplateEngine

        engine = TemplateEngine().bound(medium=DEFAULT_MEDIUM)
        assert download().render(engine) == ""
        assert "Download" in Only(Button("Download", "https://x.org"), "html").render(engine)

    def test_an_omitted_block_leaves_its_cell_empty(self, paper):
        document = PagedDocument(FACTS).add_section(
            TwoColumn("50-50", TextBlock("<p>Left</p>"), download())
        )
        assert "Left" in document.render() and "Download" not in document.render()


class TestWhatItRefuses:
    def test_a_labelled_exhibit(self):
        table = DataTable(["A"], [TableRow(["1"])], caption="Yields", label="Exhibit")
        with pytest.raises(ValidationError, match="labelled 'Exhibit'.*numbered across"):
            Only(table, "email")
        with pytest.raises(ValidationError, match="OnlySections holds a DataTable labelled"):
            OnlySections([FullWidth(table)], "document")

    def test_a_footnote(self):
        noted = TextBlock("<p>Rates rose.[^1]</p>", notes=[Footnote("Source: BoE.")])
        with pytest.raises(ValidationError, match="with footnotes"):
            Only(noted, "email")

    def test_a_citation(self):
        with pytest.raises(ValidationError, match="with a citation"):
            Only(TextBlock("<p>As shown [@fama1993].</p>"), "email")

    def test_one_inside_a_stack(self):
        noted = TextBlock("<p>Rates rose.[^1]</p>", notes=[Footnote("Source: BoE.")])
        with pytest.raises(ValidationError, match="footnotes"):
            Only(Stack([TextBlock("<p>x</p>"), noted]), "email")

    def test_an_unlabelled_exhibit_is_fine(self):
        Only(DataTable(["A"], [TableRow(["1"])]), "email")

    @pytest.mark.parametrize("media", ["pdf", ("email", "print"), (), None, 3])
    def test_a_medium_nothing_ships(self, media):
        with pytest.raises(ValidationError):
            Only(TextBlock("<p>x</p>"), media)

    def test_a_section_where_a_block_goes_and_the_reverse(self):
        with pytest.raises(ValidationError, match="OnlySections"):
            Only(FullWidth(TextBlock("<p>x</p>")), "email")
        with pytest.raises(ValidationError, match="holds sections"):
            OnlySections([TextBlock("<p>x</p>")], "email")

    def test_nesting_with_a_page_either_way(self):
        section = FullWidth(TextBlock("<p>x</p>"))
        with pytest.raises(ValidationError, match="cannot nest"):
            OnlySections([Page([section])], "document")
        with pytest.raises(ValidationError):
            Page([OnlySections([section], "document")])


def test_the_shipped_media_are_the_ones_named():
    from pyhermes.brochure import BROCHURE_MEDIUM
    from pyhermes.deck import DECK_MEDIUM
    from pyhermes.document import PAGED_MEDIUM
    from pyhermes.email import EMAIL_MEDIUM

    shipped = {m.name for m in (DEFAULT_MEDIUM, EMAIL_MEDIUM, PAGED_MEDIUM, BROCHURE_MEDIUM)}
    assert shipped | {DECK_MEDIUM.name} == set(SHIPPED_MEDIA)
