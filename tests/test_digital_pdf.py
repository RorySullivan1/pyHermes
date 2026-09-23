"""
The digital PDF (#193): a paged document finished for the screen.

Every test here reads a PDF back, so the module needs ``[pdf]`` and ``[qa]``
and skips without either. The facts under test are the ones only the written
file can show: its document information, its outline, and its bytes.
"""

from __future__ import annotations

import importlib.util

import pytest

from qa.fixtures import _paged as paged
from qa.fixtures import all_brochure_fixtures, all_paged_fixtures
from svc.builder import FullWidth, TextBlock
from svc.document import PagedDocument
from svc.pdf import available, render_pdf

pytestmark = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the digital-PDF tests need the "[pdf]" and "[qa]" extras',
)


def _read(pdf: bytes):
    import pypdfium2

    return pypdfium2.PdfDocument(pdf)


def _info(pdf: bytes) -> dict[str, str]:
    return dict(_read(pdf).get_metadata_dict())


@pytest.fixture(scope="module")
def a4_portrait() -> PagedDocument:
    return all_paged_fixtures()["a4_portrait"]()


@pytest.fixture(scope="module")
def a4_portrait_pdf(a4_portrait) -> bytes:
    return render_pdf(a4_portrait)


class TestTheMetadataIsTheDocumentsFacts:
    """#195: every field of the document information comes from a fact."""

    def test_each_field_reads_back_as_the_fact_it_came_from(self, a4_portrait_pdf):
        facts = paged.facts()
        info = _info(a4_portrait_pdf)
        assert info["Title"] == facts["campaign_name"]
        assert info["Author"] == facts["firm_name"]
        assert info["Subject"] == " · ".join(
            (facts["campaign_name"], facts["department"], facts["date_range"])
        )
        assert info["Keywords"] == f"{facts['department']}, {facts['issue_label']}"

    def test_the_brochure_carries_the_same_three(self):
        facts = paged.facts()
        info = _info(render_pdf(all_brochure_fixtures()["tri_fold_letter"]()))
        assert info["Author"] == facts["firm_name"]
        assert info["Subject"].startswith(facts["campaign_name"])
        assert info["Keywords"]

    def test_an_absent_fact_leaves_its_field_empty_rather_than_padded(self):
        document = PagedDocument({"firm_name": "Hermes Research", "campaign_name": "Note"})
        document.add_section(FullWidth(content=TextBlock("<p>Short.</p>")))
        info = _info(render_pdf(document))
        # No department and no date: the subject is the campaign alone, with no
        # dangling separator, and there is nothing to key the document by.
        assert info["Subject"] == "Note"
        assert info["Keywords"] == ""

    def test_a_quote_and_an_ampersand_read_back_exactly(self):
        firm = 'Smith & "Sons" <Partners>'
        document = PagedDocument({"firm_name": firm, "campaign_name": "Q&A"})
        document.add_section(FullWidth(content=TextBlock("<p>Short.</p>")))
        info = _info(render_pdf(document))
        # Escaped as an attribute: a quote that closed it would truncate the
        # author and spill the rest of the name into the head as markup.
        assert info["Author"] == firm
        assert info["Title"] == "Q&A"


class TestTheBytesAreDeterministic:
    """The goldens rest on this, and so would any PDF golden."""

    def test_there_is_no_creation_or_modification_date(self, a4_portrait_pdf):
        info = _info(a4_portrait_pdf)
        assert info["CreationDate"] == ""
        assert info["ModDate"] == ""

    def test_two_renders_of_one_document_are_byte_identical(self, a4_portrait, a4_portrait_pdf):
        # Needs HarfBuzz-Subset: without it WeasyPrint subsets fonts through
        # fontTools, which stamps the clock into each font's head table.
        assert render_pdf(a4_portrait) == a4_portrait_pdf


class TestTheOutlineIsTheDocumentsShape:
    """#195: the bookmark outline, pinned as it is and as it should be."""

    def test_the_cover_title_heads_it_and_every_sheet_a_reader_seeks_follows(self, a4_portrait_pdf):
        outline = [(mark.level, mark.get_title()) for mark in _read(a4_portrait_pdf).get_toc()]
        # The contents sheet and the disclosures are bookmarked beside the
        # sections, by decision: the outline is how a screen reader moves
        # through the file, and both are places a reader goes. The contents
        # sheet lists only sections, because it is not one.
        assert outline == [
            (0, "Quarterly Review"),
            (1, "In This Review"),
            (1, "Market Snapshot"),
            (1, "Narrative"),
            (1, "Factor Returns"),
            (1, "Positioning"),
            (1, "Methodology"),
            (1, "Important Disclosures"),
        ]
