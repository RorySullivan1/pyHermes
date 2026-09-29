"""
The PDF exporter (#164): the third exporter, and the first real pagination.

Two halves. The **policy** half runs everywhere — the exporter must be
importable without WeasyPrint, the core must never import it, and the fetcher
must refuse what it is not given. The **render** half skips when the
``[pdf]`` extra is absent, which is what proves the extra is optional.
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import re
import zlib

import pytest

from pyhermes.builder import FullWidth, TextBlock
from pyhermes.builder.images import EmailImage
from pyhermes.document import (
    Cover,
    EmptyBackMatter,
    EmptyCover,
    EmptyRunningFooter,
    EmptyRunningHeader,
    Page,
    PagedDocument,
)
from pyhermes.pdf import (
    BackendError,
    BackendMissingError,
    PdfError,
    UnreachableResourceError,
    available,
    page_count,
    render_pdf,
    save_pdf,
)
from pyhermes.pdf.exporter import _backend, _own_errors
from qa.fixtures import a4_long_table as long_table
from qa.fixtures import all_paged_fixtures

requires_backend = pytest.mark.skipif(
    not available(),
    reason='no WeasyPrint; the PDF exporter is the optional "[pdf]" extra',
)

FACTS = {"firm_name": "Hermes Research", "campaign_name": "Quarterly Review"}


def _decompressed(pdf: bytes) -> bytes:
    """The PDF plus every FlateDecode stream it carries, inflated."""
    blob = bytearray(pdf)
    for match in re.finditer(rb"stream\r?\n", pdf):
        end = pdf.find(b"endstream", match.end())
        try:
            blob += zlib.decompress(pdf[match.end() : end])
        except zlib.error:
            continue
    return bytes(blob)


BARE = {
    "cover": EmptyCover(),
    "running_header": EmptyRunningHeader(),
    "running_footer": EmptyRunningFooter(),
    "back_matter": EmptyBackMatter(),
}


def document(*sections) -> PagedDocument:
    """A paged document with no regions, so only its sections make pages."""
    built = PagedDocument(FACTS, **BARE)
    for section in sections or (FullWidth(content=TextBlock("<p>Short.</p>")),):
        built.add_section(section)
    return built


class TestTheCoreNeverImportsTheBackend:
    """
    The purity rule the send adapters already hold, for the third exporter.

    ``pip install -e .`` must render and project everything; only turning a
    document into PDF bytes may need the extra.
    """

    @pytest.mark.parametrize(
        "package", ["pyhermes/builder", "pyhermes/document", "pyhermes/email", "pyhermes/brochure"]
    )
    def test_no_module_imports_weasyprint(self, package):
        for path in sorted(pathlib.Path(package).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    continue
                assert not any(name.split(".")[0] == "weasyprint" for name in names), (
                    f"{path} imports weasyprint; the core install is Jinja2-only"
                )

    def test_the_exporter_itself_imports_it_lazily(self):
        # pyhermes.pdf must import cleanly without the extra, so a caller catches
        # BackendMissingError rather than an ImportError from their own graph.
        tree = ast.parse(pathlib.Path("pyhermes/pdf/exporter.py").read_text(encoding="utf-8"))
        module_level = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        assert not any(
            "weasyprint" in (getattr(n, "module", "") or "")
            or any(a.name.startswith("weasyprint") for a in getattr(n, "names", []))
            for n in module_level
        )

    def test_a_missing_backend_names_the_install(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def refuse(name, *args, **kwargs):
            if name == "weasyprint":
                raise ImportError("no weasyprint")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", refuse)
        with pytest.raises(BackendMissingError, match=r"pyhermes\[pdf\]"):
            _backend()

    def test_a_backend_that_cannot_load_its_libraries_is_unavailable(self, monkeypatch):
        # A WeasyPrint wheel without Pango fails at import with OSError from
        # cffi, not ImportError; available() must still answer False (#241).
        import builtins

        real_import = builtins.__import__

        def refuse(name, *args, **kwargs):
            if name == "weasyprint":
                raise OSError("cannot load library 'libpango-1.0-0'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", refuse)
        assert available() is False

    def test_a_backend_that_cannot_load_its_libraries_names_the_system_packages(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def refuse(name, *args, **kwargs):
            if name == "weasyprint":
                raise OSError("cannot load library 'libpango-1.0-0'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", refuse)
        with pytest.raises(BackendMissingError, match="Pango") as info:
            _backend()
        assert isinstance(info.value.__cause__, OSError)
        assert "libpango" in str(info.value)

    def test_every_failure_is_catchable_as_one_base(self):
        assert issubclass(BackendMissingError, PdfError)
        assert issubclass(UnreachableResourceError, PdfError)
        assert issubclass(BackendError, PdfError)

    def test_it_is_not_a_delivery_failure(self):
        # A document that will not print is neither a build failure nor a
        # transport failure, and a caller must be able to tell the three apart.
        from pyhermes.builder.exceptions import EmailBuilderError
        from pyhermes.delivery.exceptions import DeliveryError

        assert not issubclass(PdfError, (EmailBuilderError, DeliveryError))


@requires_backend
class TestTheExporterOwnsEveryBackendFailure:
    """
    ``except PdfError`` is the documented contract, so nothing WeasyPrint
    raises may escape it (#241).
    """

    def test_an_unnamed_backend_failure_arrives_as_a_pdf_error_with_its_cause(self):
        with pytest.raises(BackendError, match="synthetic") as info:
            with _own_errors():
                raise RuntimeError("synthetic backend failure")
        assert isinstance(info.value, PdfError)
        assert isinstance(info.value.__cause__, RuntimeError)

    def test_the_exporters_own_errors_pass_through_unchanged(self):
        original = UnreachableResourceError("https://example.com/chart.png")
        with pytest.raises(UnreachableResourceError) as info:
            with _own_errors():
                raise original
        assert info.value is original


@requires_backend
class TestTheFetcherServesTheManifestAndNothingElse:
    def test_a_hosted_image_is_refused_by_url(self, png_bytes):
        # Not slow -- refused. A build that reaches the network for an image
        # the caller forgot to attach is the failure this policy prevents.
        doc = document(
            FullWidth(
                content=TextBlock('<p><img src="https://cdn.example.com/x.png" width="10"></p>')
            )
        )
        with pytest.raises(UnreachableResourceError, match="cdn.example.com"):
            render_pdf(doc)

    def test_the_refusal_says_what_to_do_instead(self, png_bytes):
        doc = document(
            FullWidth(content=TextBlock('<p><img src="http://example.com/y.png" width="10"></p>'))
        )
        with pytest.raises(UnreachableResourceError, match="EmailImage.attached"):
            render_pdf(doc)

    def test_a_declared_attachment_is_served(self, png_bytes):
        from pyhermes.builder import ChartBlock

        doc = document(
            FullWidth(content=ChartBlock(EmailImage.attached(png_bytes, alt="C", width=40)))
        )
        assert render_pdf(doc).startswith(b"%PDF")

    def test_an_inlined_image_never_reaches_the_fetcher(self, png_bytes):
        # A data URI carries its own bytes, so it resolves without the
        # manifest -- and must not be refused for not being in one.
        from pyhermes.builder import ChartBlock

        doc = document(
            FullWidth(content=ChartBlock(EmailImage.inline(png_bytes, alt="C", width=40)))
        )
        assert render_pdf(doc).startswith(b"%PDF")

    def test_the_fetcher_refuses_an_undeclared_cid(self):
        from pyhermes.pdf.fetcher import build_fetcher

        with pytest.raises(UnreachableResourceError, match="asset manifest"):
            build_fetcher([]).fetch("cid:nothing-here")


@requires_backend
class TestThePagesBreakWhereTheTreeSaysTheyDo:
    """
    #163 pinned the markup and said plainly that it could not verify a print
    engine honours it. This is where that claim gets its teeth.
    """

    def test_one_short_section_is_one_page(self):
        assert page_count(document()) == 1

    def test_a_page_break_adds_a_sheet(self):
        # Identical content, one flag apart. Overflow cannot explain this.
        short = FullWidth(content=TextBlock("<p>Short.</p>"))
        broken = document(short, Page([FullWidth(content=TextBlock("<p>Next.</p>"))]))
        unbroken = document(
            short,
            Page([FullWidth(content=TextBlock("<p>Next.</p>"))], break_before=False),
        )
        assert page_count(broken) == page_count(unbroken) + 1

    def test_a_page_opening_the_body_opens_no_blank_sheet(self):
        # The body already starts a sheet, so a page's leading break there is
        # redundant, and the running boxes' seed leaves ahead of the body
        # table once made it open a blank one. Found by the factsheet, whose
        # first sheet could not be a Page.
        body = [FullWidth(content=TextBlock("<p>Short.</p>"))]
        assert page_count(document(Page(body))) == page_count(document(*body)) == 1

    def test_a_page_opening_the_body_after_a_cover_opens_no_blank_sheet(self):
        body = [FullWidth(content=TextBlock("<p>Short.</p>"))]
        covered = {**BARE, "cover": Cover()}
        paged = PagedDocument(FACTS, **covered).add_section(Page(body))
        bare = PagedDocument(FACTS, **covered).add_section(body[0])
        assert page_count(paged) == page_count(bare) == 2

    def test_the_gallery_paginates_as_its_page_format_implies(self):
        # The same content on a shorter page needs more sheets. Each count
        # includes the cover, the contents sheet (#183) and the back matter.
        a4 = page_count(all_paged_fixtures()["a4_portrait"]())
        slide = page_count(all_paged_fixtures()["slide_16_9"]())
        assert a4 == 5 and slide == 6, (a4, slide)

    def test_every_sheet_is_the_mediums_page(self):
        import weasyprint

        from pyhermes.pdf.fetcher import build_fetcher

        fixture = all_paged_fixtures()["a4_portrait"]()
        rendered = weasyprint.HTML(
            string=fixture.render(), url_fetcher=build_fetcher(fixture.assets())
        ).render()
        page = fixture.medium.page_format
        for sheet in rendered.pages:
            assert (round(sheet.width), round(sheet.height)) == (page.width, page.height)


@requires_backend
class TestTheBytesAreAPdf:
    def test_render_pdf_returns_a_pdf(self):
        assert render_pdf(document()).startswith(b"%PDF")

    def test_save_pdf_writes_one(self, tmp_path):
        path = save_pdf(document(), tmp_path / "out" / "doc.pdf")
        assert path.is_file() and path.read_bytes().startswith(b"%PDF")

    def test_a_real_face_is_embedded_rather_than_a_fallback(self):
        """
        The font stack has to resolve to a real face, and the PDF has to
        carry it.

        A print engine picks from *system* fonts, not from the web-safe
        stacks the theme names, so a machine with none installed renders in a
        last-resort fallback and still hands back a finished-looking PDF.
        That failure is silent by construction, which is why it gets a test.

        The bytes are read decompressed: font objects live inside FlateDecode
        streams, so searching the raw file finds nothing and would pass this
        test for the wrong reason — which is exactly what it did first.
        """
        blob = _decompressed(render_pdf(all_paged_fixtures()["a4_portrait"]()))
        assert b"/FontFile" in blob, "no font embedded; the PDF would not be portable"
        faces = {name.decode() for name in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+#\-]+)", blob)}
        assert faces, "no face named"
        assert any("serif" in face.lower() for face in faces), (
            f"the classic theme asks for a serif and the PDF embeds {sorted(faces)}"
        )


@requires_backend
class TestWhatOnlyAPrintEngineCouldShow:
    """
    Two defects the first real PDF surfaced, neither of which any golden or
    browser screenshot could see. Both are in the paged skeleton, so both are
    pinned by measuring the laid-out result rather than the markup.
    """

    @staticmethod
    def _laid_out(document):
        import weasyprint

        from pyhermes.pdf.fetcher import build_fetcher

        return weasyprint.HTML(
            string=document.render(), url_fetcher=build_fetcher(document.assets())
        ).render()

    @staticmethod
    def _table_widths(page, frame_width: int) -> list[tuple[int, int]]:
        """Each table's laid-out width beside the width it should fill."""
        widths: list[tuple[int, int]] = []

        def walk(box, container: int):
            kind = type(box).__name__
            if kind == "TableBox":
                widths.append((round(box.width), container))
            elif kind == "InlineTableBox":
                # A split's column: what a table inside it fills is the column.
                container = round(box.width)
            for child in getattr(box, "children", []):
                walk(child, container)

        walk(page._page_box, frame_width)
        return widths

    @staticmethod
    def _text_of(page) -> str:
        found: list[str] = []

        def walk(box):
            text = getattr(box, "text", None)
            if isinstance(text, str):
                found.append(text)
            for child in getattr(box, "children", []):
                walk(child)

        walk(page._page_box)
        return " ".join(found)

    def test_a_tables_width_attribute_reaches_the_layout(self):
        """
        The component templates carry table widths as HTML *attributes*,
        because Outlook's Word engine reads nothing else. A print engine
        honours the CSS property instead and does not map the attribute, so
        without the skeleton's mapping rule every table shrink-wraps to its
        content — measured at 188px inside a 794px page, rendering perfectly
        and looking like a different document.
        """
        fixture = all_paged_fixtures()["a4_portrait"]()
        # Sheet three: the cover and the contents sheet come first.
        body = self._laid_out(fixture).pages[2]
        # The frame, not the sheet: since #175 the page's margins sit outside it.
        frame_width = fixture.medium.page_format.frame_width
        widths = self._table_widths(body, frame_width)
        assert widths, "no tables laid out"
        assert any(container < frame_width for _, container in widths), (
            "no table inside a split, so the column case is unmeasured"
        )
        # Every table fills what holds it — the frame, or its column — not its content.
        shrunk = [(width, container) for width, container in widths if width <= container * 0.85]
        assert not shrunk, f"a table shrink-wrapped (width, container): {shrunk}"

    def test_no_running_box_appears_on_the_cover(self):
        """
        A zero margin does **not** suppress a margin box: it renders anyway,
        clipped against the page edge, which is what the first PDF showed —
        a folio on the cover of a document. Only ``content: none`` removes it.
        """
        fixture = all_paged_fixtures()["a4_portrait"]()
        pages = self._laid_out(fixture).pages
        cover, body = self._text_of(pages[0]), self._text_of(pages[1])

        assert "Quarterly Review" in cover, "the cover did not render"
        assert "Confidential" not in cover, "the running footer leaked onto the cover"
        assert "1 / 5" not in cover, "the folio leaked onto the cover"
        # ...and it is suppressed only there: the contents sheet carries both.
        assert "Confidential" in body and "2 / 5" in body


requires_rasteriser = pytest.mark.skipif(
    importlib.util.find_spec("pypdfium2") is None,
    reason='no pypdfium2; reading a sheet\'s text needs the "[qa]" extra',
)

#: The paged skeleton's break rules, one per line of its style block.
_BREAK_RULE = re.compile(r"^\s*\.[\w .>-]*\{ *(?:page-)?break-[^}]*\}\s*$", re.M)


def _sheets(
    document, *, strip_break_rules: bool = False, strip_rule: str = ""
) -> list[tuple[str, int]]:
    """Each sheet's text and its image count, read back out of the PDF."""
    import pypdfium2
    import pypdfium2.raw as pdfium_raw
    import weasyprint

    from pyhermes.pdf.fetcher import build_fetcher

    html = document.render()
    if strip_break_rules:
        html, removed = _BREAK_RULE.subn("", html)
        assert removed == 8, f"expected the eight break rules, stripped {removed}"
    if strip_rule:
        html, removed = re.subn(
            rf"^\s*{re.escape(strip_rule)} \{{[^}}]*\}}\s*$", "", html, flags=re.M
        )
        assert removed == 1, f"{strip_rule} is not one of the break rules"
    pdf = pypdfium2.PdfDocument(
        weasyprint.HTML(string=html, url_fetcher=build_fetcher(document.assets())).write_pdf()
    )
    image = [pdfium_raw.FPDF_PAGEOBJ_IMAGE]
    return [
        (sheet.get_textpage().get_text_range(), len(list(sheet.get_objects(filter=image))))
        for sheet in pdf
    ]


def _sheet_of(sheets, needle: str) -> int:
    return next(i for i, (text, _) in enumerate(sheets) if needle in text)


def _title_sheet(sheets) -> int:
    pattern = re.compile(rf"^{long_table.ENGINEERED_TITLE}\s*$", re.M)
    return next(i for i, (text, _) in enumerate(sheets) if pattern.search(text))


#: Both head shapes, one row and the tiered head of #223 and #226: each boundary
#: is re-measured under each, since the break rules were tuned on a one-row head.
_HEADS = [long_table.build, long_table.build_grouped]
_HEAD_IDS = ["one-row-head", "tiered-head"]
_GROUPS = long_table.GROUPS


def _table_sheets(sheets) -> list[int]:
    return [i for i, (text, _) in enumerate(sheets) if any(h in text for h in long_table.HOLDINGS)]


@requires_backend
@requires_rasteriser
class TestALongTableCrossesSheetsIntact:
    """
    #176: the test that reads sheet two, which would have caught the missing
    ``thead`` on the day the paged medium shipped. Every claim is read back
    out of the PDF's text, sheet by sheet.
    """

    @pytest.fixture(scope="class", params=_HEADS, ids=_HEAD_IDS)
    def sheets(self, request):
        return _sheets(request.param())

    def test_the_table_spans_several_sheets(self, sheets):
        assert len(_table_sheets(sheets)) > 1

    def test_every_sheet_of_the_table_carries_its_headers(self, sheets):
        grouped = any(g.label.upper() in sheets[_table_sheets(sheets)[0]][0] for g in _GROUPS)
        heads = [h.upper() for h in long_table.HEADERS]
        if grouped:
            heads += [g.label.upper() for g in _GROUPS] + [u for u in long_table.UNITS if u]
        for index in _table_sheets(sheets):
            text = sheets[index][0]
            missing = [h for h in heads if h not in text]
            assert not missing, f"sheet {index + 1} lost its column headers {missing}"

    def test_the_total_shares_a_sheet_with_the_row_above_it(self, sheets):
        assert _sheet_of(sheets, long_table.TOTAL) == _sheet_of(sheets, long_table.HOLDINGS[-1])

    def test_the_subhead_shares_a_sheet_with_the_row_below_it(self, sheets):
        first_credit = long_table.HOLDINGS[len(long_table.HOLDINGS) // 2]
        assert _sheet_of(sheets, long_table.SUBHEAD) == _sheet_of(sheets, first_credit)

    def test_the_title_shares_a_sheet_with_its_first_line(self, sheets):
        assert _title_sheet(sheets) == _sheet_of(sheets, long_table.ENGINEERED_FIRST_LINE)

    def test_the_chart_keeps_its_fine_print(self, sheets):
        index = _sheet_of(sheets, long_table.CHART_DISCLOSURE[:30])
        text, images = sheets[index]
        assert long_table.CHART_SOURCE in text and images, "the fine print left its chart"

    def test_the_chart_keeps_its_subtitle(self, sheets):
        # Found by the raster rather than the issue: a figure that moves whole
        # left its standfirst behind at the foot of the sheet before.
        index = _sheet_of(sheets, long_table.CHART_SUBTITLE)
        assert sheets[index][1], "the subtitle ended a sheet without its chart"


@requires_backend
@requires_rasteriser
class TestTheFixtureIsEngineeredRatherThanLucky:
    """
    Each boundary the fixture carries must fail without its rule, or the
    tests above pass for the wrong reason. When layout moves and one of
    these goes green, retune the paragraph counts in ``a4_long_table``.
    """

    @pytest.fixture(scope="class", params=_HEADS, ids=_HEAD_IDS)
    def sheets(self, request):
        return _sheets(request.param(), strip_break_rules=True)

    def test_without_its_rule_the_total_opens_a_sheet_alone(self, sheets):
        text = sheets[_sheet_of(sheets, long_table.TOTAL)][0]
        assert not any(h in text for h in long_table.HOLDINGS)

    def test_without_its_rule_the_title_ends_a_sheet(self, sheets):
        assert _title_sheet(sheets) != _sheet_of(sheets, long_table.ENGINEERED_FIRST_LINE)

    def test_without_its_rules_the_fine_print_leaves_the_chart(self, sheets):
        text, images = sheets[_sheet_of(sheets, long_table.CHART_DISCLOSURE[:30])]
        assert not (long_table.CHART_SOURCE in text and images)


@requires_backend
@requires_rasteriser
def test_without_its_rule_a_subtitle_ends_the_sheet_its_figure_left():
    # The two rules interact: the figure's moves the chart whole, and only the
    # subtitle's stops it leaving its standfirst behind. So this strips one.
    sheets = _sheets(long_table.build(), strip_rule=".subtitle")
    assert not sheets[_sheet_of(sheets, long_table.CHART_SUBTITLE)][1]


def _without_thead(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of the packaged templates whose data table has no thead."""
    import shutil

    from pyhermes.builder.engine import TemplateEngine

    destination = tmp_path / "templates"
    shutil.copytree(TemplateEngine().template_dir, destination)
    table = destination / "analysis" / "data-table.html"
    source = table.read_text(encoding="utf-8")
    assert "<thead>" in source and "</thead>" in source
    table.write_text(source.replace("<thead>", "").replace("</thead>", ""), encoding="utf-8")
    return destination


class TestRemovingTheTheadIsCaught:
    """
    A guard that passes with the bug present is a comment (#130), so the bug
    is put back and both guards must go red: the lint rule, which needs no
    backend, and the PDF test, which does.
    """

    def test_the_lint_rule_fires(self, tmp_path):
        from qa.lint import lint_document

        document = long_table.build(template_dir=_without_thead(tmp_path))
        assert "table-structure" in {f.rule_id for f in lint_document(document)}

    @requires_backend
    @requires_rasteriser
    def test_the_headers_vanish_from_sheet_two(self, tmp_path):
        sheets = _sheets(long_table.build(template_dir=_without_thead(tmp_path)))
        second = _table_sheets(sheets)[1]
        assert long_table.HEADERS[0].upper() not in sheets[second][0]
