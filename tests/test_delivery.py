"""
Tests for the delivery layer: MIME assembly and the CID seam.

The point of this suite is the last test class: until now the builder's
"for every src=cid:X there is an ImageAsset for X" contract was documented
but never executed. Here it is built, assembled, serialised, parsed back,
and checked.
"""

from email import message_from_bytes
from email.message import EmailMessage

import pytest

from svc.builder import Email, EmailBuilder, FullWidth, ImageBlock
from svc.builder.exceptions import EmailBuilderError
from svc.builder.images import EmailImage, ImageAsset
from svc.delivery import (
    DeliveryError,
    MessageError,
    build_message,
    collect_cid_references,
    save_eml,
)

ENVELOPE = {
    "subject": "Weekly Market Wrap",
    "sender": "research@example.com",
    "to": "reader@example.com",
}


@pytest.fixture
def plain_email(valid_metadata, text_block) -> Email:
    """An email with no images at all."""
    return EmailBuilder().metadata(valid_metadata).section(FullWidth(content=text_block)).build()


@pytest.fixture
def cid_email(valid_metadata, png_bytes, other_png_bytes) -> Email:
    """An email carrying two distinct CID-embedded images."""
    first = EmailImage.attached(png_bytes, alt="Factor returns", width=300)
    second = EmailImage.attached(other_png_bytes, alt="Drawdown", width=300)
    return (
        EmailBuilder()
        .metadata(valid_metadata)
        .section(FullWidth(content=ImageBlock(first), title="Factors"))
        .section(FullWidth(content=ImageBlock(second), title="Drawdown"))
        .build()
    )


class _StubEmail:
    """A RenderableEmail whose HTML and manifest can be made to disagree."""

    def __init__(self, html: str, assets: list[ImageAsset]):
        self._html = html
        self._assets = assets

    def render(self) -> str:
        return self._html

    def assets(self) -> list[ImageAsset]:
        return list(self._assets)


def _asset(content_id: str, png_bytes: bytes) -> ImageAsset:
    return ImageAsset(
        content_id=content_id, data=png_bytes, mime_type="image/png", filename=f"{content_id}.png"
    )


class TestExceptionHierarchy:
    def test_delivery_error_is_not_a_builder_error(self):
        # The sibling rule: a send failure must be catchable apart from a
        # build failure, so callers can tell "the email is wrong" from
        # "sending it is wrong".
        assert not issubclass(DeliveryError, EmailBuilderError)
        assert not issubclass(EmailBuilderError, DeliveryError)

    def test_message_error_is_a_delivery_error(self):
        assert issubclass(MessageError, DeliveryError)


class TestCidReferenceCollection:
    def test_finds_src_attribute_references(self):
        assert collect_cid_references('<img src="cid:abc123" alt="x">') == ["abc123"]

    def test_finds_css_url_references(self):
        # The header background is a CSS background, so an attribute that
        # merely *contains* cid: must be scanned too.
        html = "<td style=\"background-image:url('cid:hero99'); color:#fff\">x</td>"
        assert collect_cid_references(html) == ["hero99"]

    def test_dedupes_preserving_first_seen_order(self):
        html = '<img src="cid:b"><img src="cid:a"><img src="cid:b">'
        assert collect_cid_references(html) == ["b", "a"]

    def test_ignores_non_cid_urls(self):
        assert collect_cid_references('<img src="https://cdn.example.com/x.png">') == []


class TestEnvelopeValidation:
    @pytest.mark.parametrize("field", ["subject", "sender"])
    def test_blank_required_header_is_rejected(self, plain_email, field):
        envelope = {**ENVELOPE, field: "   "}
        with pytest.raises(MessageError, match=field):
            build_message(plain_email, **envelope)

    def test_no_recipients_is_rejected(self, plain_email):
        with pytest.raises(MessageError, match="recipient"):
            build_message(plain_email, **{**ENVELOPE, "to": []})

    def test_blank_recipients_are_dropped_and_then_rejected(self, plain_email):
        with pytest.raises(MessageError, match="recipient"):
            build_message(plain_email, **{**ENVELOPE, "to": ["", "  "]})


class TestHeaders:
    def test_sets_the_envelope_headers(self, plain_email):
        message = build_message(
            plain_email,
            subject="Weekly Market Wrap",
            sender="research@example.com",
            to=["a@example.com", "b@example.com"],
            cc="cc@example.com",
            reply_to="noreply@example.com",
        )
        assert message["Subject"] == "Weekly Market Wrap"
        assert message["From"] == "research@example.com"
        assert message["To"] == "a@example.com, b@example.com"
        assert message["Cc"] == "cc@example.com"
        assert message["Reply-To"] == "noreply@example.com"

    def test_omits_optional_headers_when_unset(self, plain_email):
        message = build_message(plain_email, **ENVELOPE)
        assert message["Cc"] is None
        assert message["Reply-To"] is None

    def test_does_not_stamp_date_or_message_id(self, plain_email):
        # Assembly stays pure so it is deterministic and testable; the
        # transport stamps these at send time.
        message = build_message(plain_email, **ENVELOPE)
        assert message["Date"] is None
        assert message["Message-ID"] is None

    def test_assembly_is_deterministic(self, plain_email):
        first = build_message(plain_email, **ENVELOPE).as_bytes()
        second = build_message(plain_email, **ENVELOPE).as_bytes()
        assert first == second


class TestStructure:
    def test_email_without_images_is_not_multipart(self, plain_email):
        message = build_message(plain_email, **ENVELOPE)
        assert message.get_content_type() == "text/html"
        assert not message.is_multipart()

    def test_email_with_images_is_multipart_related(self, cid_email):
        message = build_message(cid_email, **ENVELOPE)
        assert message.get_content_type() == "multipart/related"
        types = [part.get_content_type() for part in message.walk()]
        assert types.count("text/html") == 1
        assert types.count("image/png") == 2

    def test_image_parts_are_inline_with_bracketed_content_ids(self, cid_email):
        message = build_message(cid_email, **ENVELOPE)
        images = [p for p in message.walk() if p.get_content_maintype() == "image"]
        assert images, "expected inline image parts"
        for part in images:
            content_id = part["Content-ID"]
            # Bare ids make an RFC-invalid header; add_related() does not
            # bracket for us, so assembly must.
            assert content_id.startswith("<") and content_id.endswith(">")
            assert part.get_content_disposition() == "inline"

    def test_repeated_image_is_attached_once(self, valid_metadata, png_bytes):
        # Content-IDs are content-addressed, so the same bytes in two
        # sections dedupe to one asset -- and therefore one MIME part.
        image = EmailImage.attached(png_bytes, alt="Chart", width=300)
        email = (
            EmailBuilder()
            .metadata(valid_metadata)
            .section(FullWidth(content=ImageBlock(image), title="One"))
            .section(FullWidth(content=ImageBlock(image), title="Two"))
            .build()
        )
        message = build_message(email, **ENVELOPE)
        images = [p for p in message.walk() if p.get_content_maintype() == "image"]
        assert len(images) == 1


class TestManifestVerification:
    def test_referenced_but_unattached_cid_is_rejected(self, png_bytes):
        stub = _StubEmail('<img src="cid:missing1">', [_asset("present1", png_bytes)])
        with pytest.raises(MessageError, match="missing1"):
            build_message(stub, **ENVELOPE)

    def test_attached_but_unreferenced_asset_is_rejected(self, png_bytes):
        stub = _StubEmail("<p>no images here</p>", [_asset("orphan1", png_bytes)])
        with pytest.raises(MessageError, match="orphan1"):
            build_message(stub, **ENVELOPE)

    def test_matching_manifest_assembles(self, png_bytes):
        stub = _StubEmail('<img src="cid:ok1">', [_asset("ok1", png_bytes)])
        assert build_message(stub, **ENVELOPE).get_content_type() == "multipart/related"

    def test_unusable_mime_type_is_rejected(self, png_bytes):
        broken = ImageAsset(
            content_id="bad1", data=png_bytes, mime_type="image-png", filename="bad1.png"
        )
        stub = _StubEmail('<img src="cid:bad1">', [broken])
        with pytest.raises(MessageError, match="bad1"):
            build_message(stub, **ENVELOPE)

    def test_builder_errors_are_not_swallowed(self, valid_metadata):
        class _Exploding:
            def render(self) -> str:
                raise EmailBuilderError("bad template")

            def assets(self) -> list[ImageAsset]:
                return []

        with pytest.raises(EmailBuilderError):
            build_message(_Exploding(), **ENVELOPE)


class TestDryRun:
    def test_save_eml_writes_and_creates_parents(self, plain_email, tmp_path):
        target = tmp_path / "nested" / "preview.eml"
        written = save_eml(build_message(plain_email, **ENVELOPE), target)
        assert written == target
        assert target.read_bytes().startswith(b"Subject:")

    def test_saved_message_reparses(self, cid_email, tmp_path):
        path = save_eml(build_message(cid_email, **ENVELOPE), tmp_path / "m.eml")
        reparsed = message_from_bytes(path.read_bytes(), _class=EmailMessage)
        assert reparsed["Subject"] == ENVELOPE["subject"]
        assert reparsed.get_content_type() == "multipart/related"


class TestCidSeamEndToEnd:
    """The contract, executed: every src="cid:X" resolves to an attached part."""

    def test_every_referenced_cid_resolves_to_a_part_with_matching_bytes(self, cid_email, tmp_path):
        html = cid_email.render()
        manifest = {asset.content_id: asset for asset in cid_email.assets()}
        referenced = collect_cid_references(html)
        assert referenced, "fixture should reference at least one cid:"

        path = save_eml(build_message(cid_email, **ENVELOPE), tmp_path / "seam.eml")
        reparsed = message_from_bytes(path.read_bytes(), _class=EmailMessage)

        # Index the delivered parts by the bare id, undoing the <> brackets
        # the MIME header required.
        delivered = {
            part["Content-ID"].strip("<>"): part for part in reparsed.walk() if part["Content-ID"]
        }

        for content_id in referenced:
            assert content_id in delivered, f"cid:{content_id} was never attached"
            part = delivered[content_id]
            assert part.get_payload(decode=True) == manifest[content_id].data
            assert part.get_content_type() == manifest[content_id].mime_type
            assert part.get_content_disposition() == "inline"

    def test_no_part_is_delivered_that_the_html_never_asked_for(self, cid_email, tmp_path):
        path = save_eml(build_message(cid_email, **ENVELOPE), tmp_path / "seam2.eml")
        reparsed = message_from_bytes(path.read_bytes(), _class=EmailMessage)
        delivered = {
            part["Content-ID"].strip("<>") for part in reparsed.walk() if part["Content-ID"]
        }
        assert delivered == set(collect_cid_references(cid_email.render()))
