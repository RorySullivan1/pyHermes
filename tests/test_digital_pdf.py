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
from qa.fixtures._png import solid_png
from svc.builder import ChartBlock, FullWidth, ImageBlock, TextBlock, TwoColumn
from svc.builder.enums import TwoColumnRatio
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
    """One 1150px image on a sheet, shown at its declared 300px (#201)."""
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


#: The tagged variant on the screen profile: what #199 measured.
TAGGED = PdfProfile(name="SCREEN, tagged", dpi=150, jpeg_quality=85, variant="pdf/ua-1")


def _alt_values(pdf: bytes) -> list[str]:
    """Every /Alt, literal or UTF-16 hex: a non-ASCII alt is written as the latter."""
    blob = _inflated(pdf)
    found = [text.decode("latin-1") for text in re.findall(rb"/Alt\s*\(([^)]*)\)", blob)]
    for hexed in re.findall(rb"/Alt\s*<([0-9A-Fa-f]+)>", blob):
        found.append(bytes.fromhex(hexed.decode()).decode("utf-16"))
    return found


def _decorative_and_content() -> PagedDocument:
    document = PagedDocument({"firm_name": "Hermes Research", "campaign_name": "Tags"})
    rule = EmailImage.attached(brochure._DESK_PNG, width=40, decorative=True)
    chart = EmailImage.attached(paged._CURVE_PNG, alt="The curve, by tenor", width=300)
    document.add_section(FullWidth(content=ImageBlock(image=rule)))
    document.add_section(FullWidth(content=ImageBlock(image=chart)))
    return document


class TestTheTaggedPdfCarriesItsStructure:
    """#199: the four structural facts, read back. Structural only: pypdfium2
    cannot validate PDF/UA, and veraPDF is a Java tool this repo will not carry."""

    @pytest.fixture(scope="class")
    @classmethod
    def tagged(cls) -> bytes:
        return _inflated(render_pdf(all_paged_fixtures()["a4_portrait"](), TAGGED))

    def test_it_is_marked(self, tagged):
        assert re.search(rb"/MarkInfo\s*<<\s*/Marked\s+true\s*>>", tagged)

    def test_it_has_a_structure_tree(self, tagged):
        assert b"/StructTreeRoot" in tagged

    def test_the_catalog_carries_the_documents_language(self, tagged):
        assert set(re.findall(rb"/Lang\s*\(([^)]*)\)", tagged)) == {b"en-GB"}

    def test_every_image_carries_its_alt_text(self):
        pdf = render_pdf(all_paged_fixtures()["a4_portrait"](), TAGGED)
        # The cover mark's alt has an em dash, so it arrives as UTF-16 hex.
        assert sorted(_alt_values(pdf)) == [
            "2s10s spread over the quarter",
            "Hermes Research — quarterly review",
        ]

    def test_a_content_image_carries_its_alt_text(self):
        assert _alt_values(render_pdf(_decorative_and_content(), TAGGED)) == ["The curve, by tenor"]


class TestWhatKeepsTheScreenProfileUntagged:
    """
    #199's decision, pinned by the two measurements that made it.

    WeasyPrint 70 tags by element name and never reads ``role``, so the
    markup is right and the file is not. When either test below fails, the
    blocker has moved: revisit the default in ``digital-pdf.md`` and #202.
    """

    def test_the_screen_profile_is_untagged(self):
        assert SCREEN.variant is None and PRINT.variant is None

    def test_every_layout_table_is_tagged_as_a_data_table(self):
        document = all_paged_fixtures()["a4_portrait"]()
        tables = re.findall(r"<table\b[^>]*>", document.render())
        layout_tables = [t for t in tables if 'role="presentation"' in t]
        tagged = _inflated(render_pdf(document, TAGGED))
        # Twenty layout tables and one data table, and every one a /Table: a
        # screen reader would announce twenty grids that carry no data.
        assert (len(layout_tables), len(tables)) == (20, 21)
        assert len(re.findall(rb"/S\s*/Table\b", tagged)) == len(tables)

    def test_a_decorative_image_is_an_unlabelled_figure_not_an_artifact(self, caplog):
        with caplog.at_level("ERROR", logger="weasyprint"):
            tagged = _inflated(render_pdf(_decorative_and_content(), TAGGED))
        # Two figures, one alt: the decorative image is a Figure with no /Alt,
        # which PDF/UA forbids, and WeasyPrint says so as it writes it.
        assert len(re.findall(rb"/S\s*/Figure\b", tagged)) == 2
        assert "has no required alt description" in caplog.text


class TestTheLandscapeReport:
    """#200: the epic's claim, as a fixture: a landscape report with a cover and
    contents, read on a screen, and sent by email as a PDF."""

    @pytest.fixture(scope="class")
    @classmethod
    def report(cls) -> PagedDocument:
        return all_paged_fixtures()["letter_landscape_report"]()

    @pytest.fixture(scope="class")
    @classmethod
    def pdf(cls, report) -> bytes:
        return render_pdf(report, SCREEN)

    def test_every_sheet_is_letter_landscape(self, pdf):
        sizes = {tuple(round(v * 96 / 72) for v in page.get_size()) for page in _read(pdf)}
        assert sizes == {(1056, 816)}

    def test_it_rasters_one_image_per_sheet(self, report, tmp_path):
        from qa.screenshots import capture_pages

        shots, _ = capture_pages({"letter_landscape_report": report}, tmp_path)
        assert len(shots) == len(_read(render_pdf(report))) == 5
        assert {(shot.width, shot.height) for shot in shots} == {(1056, 816)}

    def test_the_contents_entries_link_to_the_sheets_their_sections_start_on(self, pdf):
        contents = [link for link in _links(pdf) if link[0] == 1]
        text = _text(pdf)
        assert {target for *_, target, _ in contents} == {2, 3}
        assert "Summary" in text[2] and "From the Desk" in text[3]

    def test_the_running_header_follows_the_section(self, pdf):
        # Read from the top margin band, where the box prints: the label
        # before the first section, then the section each sheet holds.
        margin_pt = 72 * 72 / 96  # Letter's 0.75in margin, in points
        tops = []
        for page in list(_read(pdf))[1:4]:
            width, height = page.get_size()
            band = page.get_textpage().get_text_bounded(0, height - margin_pt, width, height)
            tops.append(band.strip())
        assert tops == ["Global Rates Review", "Summary", "From the Desk"]

    def test_a_centred_cover_centres_its_logo(self, pdf):
        # A block image ignores text-align; this fixture is the first centred
        # cover, and the first raster showed the mark stranded at the left.
        [page] = [next(iter(_read(pdf)))]
        import pypdfium2.raw as pdfium_raw

        [mark] = [
            image
            for image in page.get_objects(filter=[pdfium_raw.FPDF_PAGEOBJ_IMAGE])
            if image.get_px_size() == (64, 64)
        ]
        left, _, right, _ = mark.get_bounds()
        assert (left + right) / 2 * 96 / 72 == pytest.approx(1056 / 2, abs=1)

    def test_it_goes_out_as_one_message(self, report, pdf):
        from email import message_from_bytes

        from svc.builder import EmailBuilder
        from svc.delivery import build_message
        from svc.delivery.message import to_wire_bytes
        from svc.pdf import pdf_attachment

        cover = (
            EmailBuilder()
            .metadata({**report.metadata.to_dict(), "email_subject": "Global Rates Review"})
            .section(FullWidth(content=TextBlock("<p>This quarter's review is attached.</p>")))
            .build()
        )
        attachment = pdf_attachment(report, "global-rates-review.pdf")
        message = build_message(
            cover, sender="research@example.com", to="clients@example.com", attachments=[attachment]
        )
        parsed = message_from_bytes(to_wire_bytes(message))
        [sent] = [part for part in parsed.walk() if part.get_filename()]
        assert sent.get_payload(decode=True) == pdf
        assert _info(pdf)["Author"] == "Hermes Research"


class TestAnImagePrintsAtItsDeclaredWidth:
    """
    #201: a print engine maps no ``width`` attribute, so the image templates
    state the width again, as a CSS cap on ``width: 100%``. Each width is read
    off the sheet; a browser shows the email's images at the same widths.
    """

    #: A4's column: the 794px sheet, less its margins and the frame's padding.
    COLUMN = 578

    @pytest.fixture(scope="class")
    @classmethod
    def shown(cls) -> dict[str, float]:
        """Each image's displayed width, keyed by its alt, read in document order."""
        wide, small = solid_png(1150, 200, (91, 138, 154)), solid_png(72, 72, (245, 242, 236))

        def image(png: bytes, alt: str, width: int | None = None) -> ImageBlock:
            return ImageBlock(image=EmailImage.attached(png, alt=alt, width=width))

        chart = EmailImage.attached(small, alt="widened chart", width=200)
        sections = [
            FullWidth(content=image(wide, "narrowed", 300)),
            FullWidth(content=ChartBlock(chart, source="Hermes Research")),
            FullWidth(content=image(wide, "capped", 900)),
            FullWidth(content=image(small, "undeclared")),
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                left=image(wide, "capped in a half", 600),
                right=image(small, "small in a half", 60),
            ),
        ]
        document = PagedDocument({"firm_name": "Hermes Research", "campaign_name": "Widths"})
        for section in sections:
            document.add_section(section)
        alts = ["narrowed", "widened chart", "capped", "undeclared"]
        alts += ["capped in a half", "small in a half"]
        widths = [shown for _, _, shown in _image_objects(render_pdf(document))]
        return dict(zip(alts, widths, strict=True))

    def test_a_large_source_prints_at_its_declared_width(self, shown):
        assert shown["narrowed"] == pytest.approx(300, abs=0.5)

    def test_a_small_source_is_scaled_up_to_it(self, shown):
        # The chart's 1px border sits outside the width it declares.
        assert shown["widened chart"] == pytest.approx(200, abs=0.5)

    def test_a_width_past_the_column_is_capped_at_the_column(self, shown):
        assert shown["capped"] == pytest.approx(self.COLUMN, abs=0.5)

    def test_an_undeclared_width_is_the_columns(self, shown):
        assert shown["undeclared"] == pytest.approx(self.COLUMN, abs=0.5)

    def test_a_width_past_a_half_shrinks_to_the_half_and_does_not_widen_it(self, shown):
        # A fixed CSS width here widened the whole frame past the page margin
        # and put a4_portrait on six sheets: a px width is not compressible.
        assert shown["capped in a half"] < self.COLUMN / 2
        assert shown["small in a half"] == pytest.approx(60, abs=0.5)

    def test_the_cover_logo_prints_at_its_declared_width(self):
        # a4_portrait's mark is 72px, declared at 96: it printed at 72 before.
        document = all_paged_fixtures()["a4_portrait"]()
        [logo] = [shown for w, _, shown in _image_objects(render_pdf(document)) if w == 72]
        assert logo == pytest.approx(96, abs=0.5)
