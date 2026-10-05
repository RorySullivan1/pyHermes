"""
A QR code back to the web (#344): bytes in the builder, rendered by the ``[qr]`` extra.

On paper the code prints at its size and decodes to its URL from the
rasterised PDF; in an email it is a button and no image reaches the manifest.
The purity half (no ``segno`` in ``[dev]``) is ``test_data_layer.py``'s.
"""

from __future__ import annotations

import importlib.util
import io

import pytest

from pyhermes.builder import Button, Email, FullWidth, QrCode
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.surfaces import QR_LABEL, QR_MIN_SIZE
from pyhermes.document import EmptyCover, PagedDocument
from pyhermes.pdf import available as pdf_available
from qa.fixtures import _qr, all_brochure_fixtures, all_fixtures

requires_qr = pytest.mark.skipif(
    importlib.util.find_spec("segno") is None,
    reason='rendering a code needs the "[qr]" extra',
)
requires_reading = pytest.mark.skipif(
    not pdf_available()
    or importlib.util.find_spec("pypdfium2") is None
    or importlib.util.find_spec("zxingcpp") is None,
    reason='decoding a printed code needs the "[pdf]" and "[qa]" extras',
)

FACTS = {"firm_name": "F", "campaign_name": "C"}
URL = "https://example.com/web"


def _code(**kwargs) -> QrCode:
    return QrCode(_qr.qr_png(), _qr.URL, **kwargs)


def _email(*blocks) -> Email:
    email = Email({**FACTS, "email_subject": "S"})
    for block in blocks:
        email.add_section(FullWidth(content=block))
    return email


def _paged(*blocks) -> PagedDocument:
    document = PagedDocument(FACTS, cover=EmptyCover())
    for block in blocks:
        document.add_section(FullWidth(content=block))
    return document


class TestConstruction:
    @pytest.mark.parametrize(
        "url", ["javascript:alert(1)", "/relative/path", "cid:abc", "file:///etc/passwd"]
    )
    def test_a_url_a_phone_cannot_open_is_refused(self, url):
        with pytest.raises(ValidationError):
            QrCode(_qr.qr_png(), url)

    @pytest.mark.parametrize("url", [URL, "http://example.com", "mailto:desk@example.com"])
    def test_http_https_and_mailto_are_taken(self, url):
        assert QrCode(_qr.qr_png(), url).url == url

    @pytest.mark.parametrize("size", [QR_MIN_SIZE - 1, 0, True, 96.0])
    def test_a_size_too_small_to_scan_is_refused(self, size):
        with pytest.raises(ValidationError, match="scan"):
            _code(size=size)

    def test_bytes_become_an_attached_image_labelled_by_the_url(self):
        code = _code()
        assert code.image.alt == f"QR code for {_qr.URL}"
        assert code.image.width == 96

    def test_a_hosted_image_is_refused(self):
        with pytest.raises(ValidationError, match="hosted"):
            QrCode(EmailImage.hosted("https://example.com/q.png", alt="q", width=96), URL)

    def test_anything_but_an_image_is_refused(self):
        with pytest.raises(ValidationError, match="PNG bytes"):
            QrCode("not bytes", URL)  # type: ignore[arg-type]


class TestInAnEmail:
    def test_it_is_the_button_byte_for_byte(self):
        code = _email(_code(caption="Read online")).render()
        button = _email(Button("Read online", _qr.URL)).render()
        assert code == button

    def test_without_a_caption_the_button_says_view_online(self):
        assert QR_LABEL in _email(_code()).render()

    def test_no_image_reaches_the_manifest(self):
        email = _email(_code())
        assert email.assets() == []
        assert email.images() == []
        assert "cid:" not in email.render()

    def test_the_kitchen_sinks_code_leaves_its_manifest_too(self):
        cid = EmailImage.attached(_qr.qr_png(), alt="x", width=96).content_id
        email = all_fixtures()["kitchen_sink"]()
        assert cid not in {asset.content_id for asset in email.assets()}

    def test_the_text_part_is_the_url(self):
        assert _qr.URL in _email(_code()).text()
        assert f"Read online: {_qr.URL}" in _email(_code(caption="Read online")).text()


class TestOnPaper:
    def test_it_prints_the_image_at_its_size_with_the_url_beneath(self):
        html = _paged(_code(caption="The full review")).render()
        assert 'width="96" height="96"' in html
        assert "width: 96px; height: 96px;" in html
        assert html.index('class="figure qr-code"') < html.index(_qr.URL)

    def test_the_image_reaches_the_manifest(self):
        cid = _code().image.content_id
        assert cid in {asset.content_id for asset in _paged(_code()).assets()}

    def test_the_brochure_carries_it_on_its_back_cover(self):
        brochure = all_brochure_fixtures()["tri_fold_letter"]()
        assert _code().image.content_id in {a.content_id for a in brochure.assets()}


@requires_qr
class TestTheAdapter:
    def test_the_galleries_constant_is_segnos_symbol_for_its_url(self):
        import segno

        symbol = segno.make(_qr.URL, error="m", micro=False)
        rows = tuple("".join("1" if cell else "0" for cell in row) for row in symbol.matrix)
        assert rows == _qr.MODULES

    def test_two_renders_are_one_content_id(self):
        from pyhermes.qr import qr_code

        first, second = qr_code(URL), qr_code(URL)
        assert first.image.content_id == second.image.content_id

    def test_it_carries_enough_pixels_to_print(self):
        from PIL import Image

        from pyhermes.config import get_config
        from pyhermes.qr import qr_code

        code = qr_code(URL)
        pixels = Image.open(io.BytesIO(code.image.asset.data)).size[0]
        assert pixels >= code.size * get_config().print_dpi / 96

    def test_it_is_painted_in_the_themes_ink_on_its_surface(self):
        from PIL import Image

        from pyhermes.builder.theming import resolve_theme
        from pyhermes.qr import qr_code

        theme = resolve_theme("slate")
        image = Image.open(io.BytesIO(qr_code(URL, theme="slate").image.asset.data))
        colours = {
            "#{:02X}{:02X}{:02X}".format(*rgb[:3]) for _, rgb in image.convert("RGB").getcolors()
        }
        assert colours == {theme.text.primary, theme.palette.surface}

    def test_a_bad_url_is_refused_before_segno_runs(self):
        from pyhermes.qr import qr_code

        with pytest.raises(ValidationError):
            qr_code("javascript:alert(1)")

    def test_it_writes_no_metadata_chunk(self):
        from pyhermes.qr import render_qr

        png = render_qr(URL, dark="#000000", light="#FFFFFF")
        assert b"tEXt" not in png and b"tIME" not in png


def _decoded(pdf: bytes) -> list[str]:
    import pypdfium2
    import zxingcpp

    return [
        result.text
        for sheet in pypdfium2.PdfDocument(pdf)
        for result in zxingcpp.read_barcodes(sheet.render(scale=2).to_pil())
    ]


@requires_reading
class TestItDecodesFromThePrintedSheet:
    def test_on_a_paged_page(self):
        from pyhermes.pdf import render_pdf

        assert _decoded(render_pdf(_paged(_code()))) == [_qr.URL]

    def test_on_a_brochure_panel(self):
        from pyhermes.pdf import render_pdf

        assert _qr.URL in _decoded(render_pdf(all_brochure_fixtures()["tri_fold_letter"]()))

    @requires_qr
    def test_the_adapters_code_decodes_too(self):
        from pyhermes.pdf import render_pdf
        from pyhermes.qr import qr_code

        assert _decoded(render_pdf(_paged(qr_code(URL, "Online")))) == [URL]
