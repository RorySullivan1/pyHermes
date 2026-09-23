"""
The digital PDF (#193): a paged document finished for the screen.

Every test here reads a PDF back, so the module needs ``[pdf]`` and ``[qa]``
and skips without either. The facts under test are the ones only the written
file can show: its document information, its outline, and its bytes.
"""

from __future__ import annotations

import ctypes
import importlib.util
import re
import zlib

import pytest

from qa.fixtures import _paged as paged
from qa.fixtures import all_brochure_fixtures, all_paged_fixtures
from qa.fixtures import tri_fold_letter as brochure
from svc.builder import FullWidth, ImageBlock, TextBlock
from svc.builder.images import EmailImage
from svc.document import PagedDocument
from svc.pdf import PRINT, SCREEN, PdfProfile, available, layout, render_pdf, save_pdf

pytestmark = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the digital-PDF tests need the "[pdf]" and "[qa]" extras',
)


def _read(pdf: bytes):
    import pypdfium2

    return pypdfium2.PdfDocument(pdf)


def _info(pdf: bytes) -> dict[str, str]:
    return dict(_read(pdf).get_metadata_dict())


def _inflated(pdf: bytes) -> bytes:
    """The PDF plus every Flate stream inflated, object streams included."""
    blob = bytearray(pdf)
    for match in re.finditer(rb"stream\r?\n", pdf):
        end = pdf.find(b"endstream", match.end())
        try:
            blob += zlib.decompress(pdf[match.end() : end])
        except zlib.error:
            continue
    return bytes(blob)


def _image_objects(pdf: bytes) -> list[tuple[int, int, float]]:
    """Each placed image as (pixel width, pixel height, displayed width in px)."""
    import pypdfium2.raw as pdfium_raw

    placed = []
    for page in _read(pdf):
        for image in page.get_objects(filter=[pdfium_raw.FPDF_PAGEOBJ_IMAGE]):
            left, _, right, _ = image.get_bounds()
            width, height = image.get_px_size()
            placed.append((width, height, (right - left) * 96 / 72))
    return placed


def _xobject_sizes(pdf: bytes) -> set[tuple[int, int]]:
    """Every image XObject's pixel size, a CSS background's included."""
    found = re.findall(rb"/Width\s+(\d+)\s*/Height\s+(\d+)", _inflated(pdf))
    return {(int(width), int(height)) for width, height in found}


def _links(pdf: bytes) -> list[tuple[int, int, int, int | None, str | None]]:
    """Every link annotation: sheet, position, and its target sheet or URI."""
    import pypdfium2.raw as pdfium_raw

    document, found = _read(pdf), []
    for index, page in enumerate(document):
        position, link = ctypes.c_int(0), pdfium_raw.FPDF_LINK()
        while pdfium_raw.FPDFLink_Enumerate(page, ctypes.byref(position), ctypes.byref(link)):
            rect = pdfium_raw.FS_RECTF()
            pdfium_raw.FPDFLink_GetAnnotRect(link, rect)
            dest = pdfium_raw.FPDFLink_GetDest(document, link)
            target = pdfium_raw.FPDFDest_GetDestPageIndex(document, dest) if dest else None
            action, uri = pdfium_raw.FPDFLink_GetAction(link), None
            if action:
                size = pdfium_raw.FPDFAction_GetURIPath(document, action, None, 0)
                buffer = ctypes.create_string_buffer(size)
                pdfium_raw.FPDFAction_GetURIPath(document, action, buffer, size)
                uri = buffer.value.decode()
            found.append((index, round(rect.left), round(rect.top), target, uri))
    return found


def _text(pdf: bytes) -> list[str]:
    return [page.get_textpage().get_text_range() for page in _read(pdf)]


def _outline(pdf: bytes) -> list[tuple[int, str]]:
    return [(mark.level, mark.get_title()) for mark in _read(pdf).get_toc()]


def _alt_text(pdf: bytes) -> list[bytes]:
    return re.findall(rb"/Alt\s*\(([^)]*)\)", _inflated(pdf))


#: The brochure's cover ground, reused on a sheet: 1150px across.
_WIDE_PNG = brochure._COVER_PNG


def _one_wide_image() -> PagedDocument:
    """
    One 1150px image on a sheet, shown at the column's width.

    The column caps it, not its width attribute: WeasyPrint maps no
    presentational hint, so an img's declared width does not reach the
    layout. The tests therefore measure the width it was shown at.
    """
    document = PagedDocument({"firm_name": "Hermes Research", "campaign_name": "Wide"})
    image = EmailImage.attached(_WIDE_PNG, alt="The cover ground, reduced", width=300)
    document.add_section(FullWidth(content=ImageBlock(image=image)))
    return document


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


class TestTheScreenProfileDownsamples:
    """#196: SCREEN caps an image at 150 dpi where it is shown; PRINT keeps it."""

    @pytest.fixture(scope="class")
    @classmethod
    def renders(cls) -> dict[str, bytes]:
        document = _one_wide_image()
        return {"PRINT": render_pdf(document, PRINT), "SCREEN": render_pdf(document, SCREEN)}

    def test_the_screen_file_is_smaller(self, renders):
        assert len(renders["SCREEN"]) < len(renders["PRINT"])

    def test_under_screen_the_image_is_at_most_150_dpi_where_shown(self, renders):
        [(width, _, shown)] = _image_objects(renders["SCREEN"])
        assert shown < 1150 * 96 / 150, "shown too wide for 150 dpi to reduce it"
        # 150 dpi over CSS's 96 px to the inch, plus WeasyPrint's rounding.
        assert width <= shown * 150 / 96 + 1

    def test_under_print_the_image_is_its_source(self, renders):
        [(width, height, _)] = _image_objects(renders["PRINT"])
        assert (width, height) == (1150, 2625)

    def test_a_css_background_is_downsampled_too(self):
        # The brochure's cover ground is a background, which pypdfium2 does not
        # list as an image object, so its XObject is read from the file.
        document = all_brochure_fixtures()["tri_fold_letter"]()
        assert (1150, 2625) in _xobject_sizes(render_pdf(document, PRINT))
        screen = _xobject_sizes(render_pdf(document, SCREEN))
        assert (1150, 2625) not in screen
        assert all(width < 1150 for width, _ in screen)

    def test_an_image_already_below_the_cap_is_left_alone(self):
        # 72px shown at 96: under 150 dpi already, so nothing is resampled.
        document = all_paged_fixtures()["a4_portrait"]()
        placed = {(w, h) for w, h, _ in _image_objects(render_pdf(document, SCREEN))}
        assert (72, 72) in placed


class TestAProfileIsDeterministic:
    @pytest.mark.parametrize("profile", [PRINT, SCREEN], ids=lambda p: p.name)
    def test_two_renders_under_one_profile_are_byte_identical(self, a4_portrait, profile):
        assert render_pdf(a4_portrait, profile) == render_pdf(a4_portrait, profile)

    def test_print_is_the_default_everywhere(self, a4_portrait, a4_portrait_pdf, tmp_path):
        assert render_pdf(a4_portrait, PRINT) == a4_portrait_pdf
        assert save_pdf(a4_portrait, tmp_path / "a.pdf").read_bytes() == a4_portrait_pdf

    def test_layout_carries_the_profile_to_its_own_write(self, a4_portrait):
        assert layout(a4_portrait, SCREEN).write_pdf() == render_pdf(a4_portrait, SCREEN)


class TestTheProfileTouchesOnlyTheImages:
    """#196: what downsampling must not reach, read back under both profiles."""

    @pytest.fixture(scope="class")
    @classmethod
    def pair(cls) -> tuple[bytes, bytes]:
        document = all_paged_fixtures()["a4_portrait"]()
        return render_pdf(document, PRINT), render_pdf(document, SCREEN)

    def test_the_text_layer(self, pair):
        assert _text(pair[0]) == _text(pair[1])

    def test_the_links(self, pair):
        assert _links(pair[0]) and _links(pair[0]) == _links(pair[1])

    def test_the_bookmarks(self, pair):
        assert _outline(pair[0]) == _outline(pair[1])

    def test_the_alt_text(self):
        # Alt text is written only into a tagged file, so the pair is tagged.
        document = _one_wide_image()
        tagged = {"variant": "pdf/ua-1"}
        full = render_pdf(document, PdfProfile(name="tagged print", **tagged))
        reduced = render_pdf(document, PdfProfile(name="tagged screen", dpi=150, **tagged))
        assert _alt_text(full) == _alt_text(reduced) == [b"The cover ground, reduced"]
