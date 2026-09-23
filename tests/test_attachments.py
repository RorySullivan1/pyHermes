"""
Attachments in ``build_message`` (#197): one send carries a cover email and a file.

The MIME half runs everywhere, on stand-in bytes: assembly never reads what
an attachment holds. The ``pdf_attachment`` half renders a real document and
skips without ``[pdf]``.
"""

from __future__ import annotations

import base64
import re
from email import message_from_bytes

import pytest

from svc.builder import EmailBuilder, FullWidth, ImageBlock
from svc.builder.images import EmailImage
from svc.config import config_override
from svc.delivery import Attachment, MessageError, build_message, save_eml
from svc.delivery.message import collect_cid_references, to_wire_bytes

ENVELOPE = {
    "subject": "Quarterly Review",
    "sender": "research@example.com",
    "to": "reader@example.com",
}

#: Stand-in bytes: assembly treats an attachment as opaque, so no PDF is needed.
PDF_BYTES = b"%PDF-1.7\n% a stand-in the delivery layer never parses\n%%EOF\n"


@pytest.fixture
def cid_email(valid_metadata, png_bytes, other_png_bytes):
    """A cover email carrying two distinct CID images."""
    first = EmailImage.attached(png_bytes, alt="Factor returns", width=300)
    second = EmailImage.attached(other_png_bytes, alt="Drawdown", width=300)
    return (
        EmailBuilder()
        .metadata(valid_metadata)
        .section(FullWidth(content=ImageBlock(first), title="Factors"))
        .section(FullWidth(content=ImageBlock(second), title="Drawdown"))
        .build()
    )


@pytest.fixture
def review() -> Attachment:
    return Attachment(PDF_BYTES, "review.pdf", "application/pdf")


def _structure(message) -> list[tuple[int, str]]:
    def walk(part, depth=0):
        yield depth, part.get_content_type()
        if part.is_multipart():
            for child in part.get_payload():
                yield from walk(child, depth + 1)

    return list(walk(message))


def _normalize_boundaries(raw: bytes) -> bytes:
    """Every random MIME boundary as a positional token, as test_delivery does."""
    for index, token in enumerate(re.findall(rb'boundary="([^"]+)"', raw)):
        raw = raw.replace(token, b"BOUNDARY-%d" % index)
    return raw


def _by_filename(message, filename: str):
    return next(part for part in message.walk() if part.get_filename() == filename)


class TestAnAttachmentIsValidatedAtConstruction:
    @pytest.mark.parametrize(
        ("fields", "names"),
        [
            ({"data": b""}, "data"),
            ({"filename": ""}, "filename"),
            ({"filename": ".."}, "filename"),
            ({"filename": "reports/review.pdf"}, "path separator"),
            ({"filename": "reports\\review.pdf"}, "path separator"),
            ({"filename": "review.pdf\r\nBcc: x@evil.test"}, "line break"),
            ({"mime_type": "pdf"}, "mime_type"),
            ({"mime_type": "application/"}, "mime_type"),
            ({"mime_type": "application/pdf; name=x"}, "mime_type"),
        ],
    )
    def test_a_bad_field_names_itself(self, fields, names):
        values = {"data": PDF_BYTES, "filename": "review.pdf", "mime_type": "application/pdf"}
        with pytest.raises(MessageError, match=names):
            Attachment(**{**values, **fields})

    def test_it_is_not_an_image_asset(self, review):
        # A sibling, not the same class: an asset is referenced by cid: and
        # rendered in place, an attachment by nothing and shown as a file.
        from svc.builder.images import ImageAsset

        assert not isinstance(review, ImageAsset)

    def test_anything_else_in_the_list_is_refused(self, cid_email):
        with pytest.raises(MessageError, match="Attachment instances"):
            build_message(cid_email, **ENVELOPE, attachments=[PDF_BYTES])  # type: ignore[list-item]


class TestTheMessageShape:
    """The #197 done-when, part by part."""

    @pytest.fixture
    def message(self, cid_email, review):
        return build_message(cid_email, **ENVELOPE, attachments=[review])

    def test_the_email_is_the_first_part_of_a_mixed_message(self, message):
        assert _structure(message) == [
            (0, "multipart/mixed"),
            (1, "multipart/alternative"),
            (2, "text/plain"),
            (2, "multipart/related"),
            (3, "text/html"),
            (3, "image/png"),
            (3, "image/png"),
            (1, "application/pdf"),
        ]

    def test_the_pdf_is_an_attachment_with_its_filename(self, message):
        last = message.get_payload()[-1]
        assert last.get_content_disposition() == "attachment"
        assert last.get_filename() == "review.pdf"
        assert last.get_content() == PDF_BYTES

    def test_the_html_still_resolves_both_images(self, message, cid_email):
        related = message.get_payload()[0].get_payload()[-1]
        html, *images = related.get_payload()
        referenced = collect_cid_references(html.get_content())
        attached = [image["Content-ID"].strip("<>") for image in images]
        assert len(referenced) == 2
        assert sorted(referenced) == sorted(attached)
        assert all(image.get_content_disposition() == "inline" for image in images)

    def test_several_attachments_keep_their_order(self, cid_email, review):
        appendix = Attachment(b"a,b\n1,2\n", "appendix.csv", "text/csv")
        message = build_message(cid_email, **ENVELOPE, attachments=[review, appendix])
        files = [part.get_filename() for part in message.get_payload()[1:]]
        assert files == ["review.pdf", "appendix.csv"]


class TestNoAttachmentsChangesNothing:
    def test_an_empty_list_is_the_message_without_the_argument(self, cid_email):
        without = to_wire_bytes(build_message(cid_email, **ENVELOPE))
        empty = to_wire_bytes(build_message(cid_email, **ENVELOPE, attachments=()))
        assert _normalize_boundaries(without) == _normalize_boundaries(empty)

    def test_the_alternative_stays_the_root(self, cid_email):
        message = build_message(cid_email, **ENVELOPE, attachments=())
        assert message.get_content_type() == "multipart/alternative"
        assert not any(part.get_content_disposition() == "attachment" for part in message.walk())


class TestTheFileSurvivesTheWire:
    def test_save_eml_round_trips_it(self, cid_email, review, tmp_path):
        path = save_eml(
            build_message(cid_email, **ENVELOPE, attachments=[review]), tmp_path / "m.eml"
        )
        parsed = message_from_bytes(path.read_bytes())
        assert _by_filename(parsed, "review.pdf").get_payload(decode=True) == PDF_BYTES

    def test_the_gmail_adapter_sends_it_unchanged(self, cid_email, review):
        from svc.gmail import send_message

        class Recording:
            raw = ""

            def send_raw(self, raw_message: str, *, user_id: str = "me") -> dict:
                Recording.raw = raw_message
                return {"id": "msg-1"}

        send_message(
            build_message(cid_email, **ENVELOPE, attachments=[review]), transport=Recording()
        )
        parsed = message_from_bytes(base64.urlsafe_b64decode(Recording.raw))
        assert _by_filename(parsed, "review.pdf").get_payload(decode=True) == PDF_BYTES

    def test_the_outlook_adapter_sends_it_unchanged(self, cid_email, review):
        from svc.outlook import send_message

        class Recording:
            encoded = ""

            def send_mime(self, encoded_message: str, *, user_id: str = "me") -> None:
                Recording.encoded = encoded_message

        send_message(
            build_message(cid_email, **ENVELOPE, attachments=[review]), transport=Recording()
        )
        parsed = message_from_bytes(base64.b64decode(Recording.encoded))
        assert _by_filename(parsed, "review.pdf").get_payload(decode=True) == PDF_BYTES


def _file(kilobytes: int, name: str = "review.pdf", hint: str = "") -> Attachment:
    """An attachment of ``kilobytes`` of incompressible bytes, as a PDF would be."""
    data = bytes((index * 7919) % 251 for index in range(kilobytes * 1024))
    return Attachment(data, name, "application/pdf", size_hint=hint)


#: A budget small enough to cross with test-sized files; the shape is the claim.
SMALL_BUDGET = {"attachment_limit_kb": 96, "attachment_warn_kb": 48}


class TestTheSizeBudget:
    """#198: a message a server would refuse is refused here, by name."""

    def test_over_the_limit_it_names_the_total_the_limit_and_each_file(self, cid_email):
        files = [_file(60), _file(20, "appendix.csv")]
        with config_override(**SMALL_BUDGET):
            with pytest.raises(MessageError) as raised:
                build_message(cid_email, **ENVELOPE, attachments=files)
        message = str(raised.value)
        total = re.search(r"the message is ([\d,.]+) KB on the wire", message)
        # Base64 is what a server counts: 80 KB of files is over 96 KB sent.
        assert total and float(total.group(1).replace(",", "")) > 96
        assert "96 KB attachment limit" in message
        assert "review.pdf is 60.0 KB" in message
        assert "appendix.csv is 20.0 KB" in message

    def test_it_quotes_the_producers_hint(self, cid_email):
        hinted = _file(90, hint="rendered under PRINT; try SCREEN")
        with config_override(**SMALL_BUDGET):
            with pytest.raises(MessageError, match=r"\(rendered under PRINT; try SCREEN\)"):
                build_message(cid_email, **ENVELOPE, attachments=[hinted])

    def test_between_the_thresholds_it_warns_with_the_total_and_threshold(self, cid_email, capsys):
        with config_override(**SMALL_BUDGET):
            build_message(cid_email, **ENVELOPE, attachments=[_file(40)])
        printed = capsys.readouterr().out
        assert re.search(r"WARNING: Message size [\d,.]+ KB with attachments", printed)
        assert "(target < 48 KB)" in printed

    def test_under_the_warning_it_prints_nothing(self, cid_email, capsys):
        with config_override(**SMALL_BUDGET):
            build_message(cid_email, **ENVELOPE, attachments=[_file(1)])
        assert "Message size" not in capsys.readouterr().out

    def test_with_no_attachment_no_check_runs_at_all(self, cid_email, capsys):
        # A cover email alone is over this budget, and is still not measured:
        # the budget is about files, and the 102 KB check owns the HTML.
        with config_override(attachment_limit_kb=1, attachment_warn_kb=1):
            build_message(cid_email, **ENVELOPE)
        assert "Message size" not in capsys.readouterr().out


class TestAPdfAttachment:
    """``pdf_attachment`` renders the document; it needs the ``[pdf]`` extra."""

    @pytest.fixture(scope="class")
    @classmethod
    def document(cls):
        from svc.pdf import available

        if not available():
            pytest.skip('pdf_attachment renders, and needs the "[pdf]" extra')
        from qa.fixtures import all_paged_fixtures

        return all_paged_fixtures()["a4_portrait"]()

    def test_it_is_the_screen_render_by_default(self, document):
        from svc.pdf import SCREEN, pdf_attachment, render_pdf

        attachment = pdf_attachment(document, "review.pdf")
        assert attachment.data == render_pdf(document, SCREEN)
        assert (attachment.filename, attachment.mime_type) == ("review.pdf", "application/pdf")
        assert attachment.size_hint == ""

    def test_under_print_it_names_the_remedy(self, document):
        from svc.pdf import PRINT, pdf_attachment, render_pdf

        attachment = pdf_attachment(document, "review.pdf", PRINT)
        assert attachment.data == render_pdf(document, PRINT)
        assert "PRINT" in attachment.size_hint and "SCREEN" in attachment.size_hint

    def test_over_budget_a_print_pdf_points_at_screen(self, document, cid_email):
        from svc.pdf import PRINT, pdf_attachment

        attachment = pdf_attachment(document, "review.pdf", PRINT)
        with config_override(attachment_limit_kb=8, attachment_warn_kb=4):
            with pytest.raises(MessageError, match=r"profile=SCREEN"):
                build_message(cid_email, **ENVELOPE, attachments=[attachment])

    def test_a_path_is_refused_before_anything_renders(self, document, monkeypatch):
        import svc.pdf.attachment as module
        from svc.pdf import pdf_attachment

        monkeypatch.setattr(module, "render_pdf", lambda *a: PDF_BYTES)
        with pytest.raises(MessageError, match="path separator"):
            pdf_attachment(document, "../review.pdf")
