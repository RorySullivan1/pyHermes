"""
Tests for the delivery layer: MIME assembly and the CID seam.

The point of this suite is the last test class: until now the builder's
"for every src=cid:X there is an ImageAsset for X" contract was documented
but never executed. Here it is built, assembled, serialised, parsed back,
and checked.
"""

import re
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

_BOUNDARY_RE = re.compile(rb'boundary="([^"]+)"')


def _normalize_boundary(raw: bytes) -> bytes:
    """Replace a message's random MIME boundary with a fixed token.

    ``EmailMessage.make_related()`` leaves the boundary unset, so the
    stdlib generator draws a fresh one from ``random.randrange()`` on every
    ``as_bytes()`` call — see the module docstring on
    ``svc/delivery/message.py``. That token appears both in the
    ``Content-Type`` header and in every ``--<token>`` delimiter line, and
    is the *only* thing that varies between two assemblies of the same
    input, so replacing every occurrence of it isolates that one axis for
    a determinism check.
    """
    match = _BOUNDARY_RE.search(raw)
    if match is None:
        return raw
    return raw.replace(match.group(1), b"BOUNDARY")


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

    def test_finds_css_url_references_inside_a_style_block(self):
        # A bare HTMLParser treats <style> text as opaque CDATA and never
        # looks inside it -- a real gap, since the header background can be
        # styled this way instead of via a style= attribute.
        html = "<style>.h{background:url(cid:styled1)}</style>"
        assert collect_cid_references(html) == ["styled1"]

    def test_finds_references_inside_a_conditional_comment(self):
        # Outlook's VML fill only renders inside an <!--[if mso]> conditional
        # comment; a bare HTMLParser treats the whole comment as opaque text.
        html = '<!--[if mso]><v:fill src="cid:mso1"/><![endif]-->'
        assert collect_cid_references(html) == ["mso1"]

    def test_finds_references_in_a_srcset_list(self):
        # srcset is a comma-separated list of "<url> <descriptor>" pairs;
        # naively treating the whole attribute as one url would swallow the
        # remainder of the string into a single bogus id.
        html = '<img srcset="cid:f 1x, cid:g 2x">'
        assert collect_cid_references(html) == ["f", "g"]


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

    @pytest.mark.parametrize("control_char", ["\r", "\n"])
    @pytest.mark.parametrize("field", ["subject", "sender"])
    def test_control_char_in_scalar_field_raises_message_error(
        self, plain_email, field, control_char
    ):
        # Header injection: a bare newline reaching email.policy raises
        # ValueError, not MessageError -- callers following the documented
        # "catch DeliveryError" contract in exceptions.py would miss it.
        envelope = {**ENVELOPE, field: f"a{control_char}Bcc: x@evil.test"}
        with pytest.raises(MessageError, match=field):
            build_message(plain_email, **envelope)

    @pytest.mark.parametrize("control_char", ["\r", "\n"])
    def test_control_char_in_reply_to_raises_message_error(self, plain_email, control_char):
        envelope = {**ENVELOPE, "reply_to": f"a{control_char}Bcc: x@evil.test"}
        with pytest.raises(MessageError, match="reply_to"):
            build_message(plain_email, **envelope)

    @pytest.mark.parametrize("control_char", ["\r", "\n"])
    @pytest.mark.parametrize("field", ["to", "cc"])
    def test_control_char_in_an_address_raises_message_error(
        self, plain_email, field, control_char
    ):
        envelope = {**ENVELOPE, field: [f"a{control_char}Bcc: x@evil.test"]}
        with pytest.raises(MessageError, match=field):
            build_message(plain_email, **envelope)


class TestSubjectResolution:
    """`subject` falls back to the email's own metadata (#72)."""

    def test_defaults_to_the_emails_own_subject(self, plain_email):
        envelope = {k: v for k, v in ENVELOPE.items() if k != "subject"}
        message = build_message(plain_email, **envelope)
        assert message["Subject"] == plain_email.metadata.email_subject

    def test_an_explicit_subject_wins_over_the_metadata(self, plain_email):
        envelope = {**ENVELOPE, "subject": "Sent under a different subject"}
        message = build_message(plain_email, **envelope)
        assert message["Subject"] == "Sent under a different subject"
        assert message["Subject"] != plain_email.metadata.email_subject

    def test_an_explicitly_blank_subject_is_still_an_error(self, plain_email):
        # Passing "" is a mistake, not a request to fall back -- a caller who
        # passed something meant it.
        with pytest.raises(MessageError, match="subject"):
            build_message(plain_email, **{**ENVELOPE, "subject": ""})

    def test_an_unbuilt_builder_gets_a_message_naming_the_fix(self, valid_metadata, text_block):
        # EmailBuilder satisfies render()/assets() but uses `metadata` as a
        # fluent setter, so there is nothing to read a subject from.
        builder = EmailBuilder().metadata(valid_metadata).section(FullWidth(content=text_block))
        envelope = {k: v for k, v in ENVELOPE.items() if k != "subject"}
        with pytest.raises(MessageError, match=r"build\(\)"):
            build_message(builder, **envelope)

    def test_that_same_builder_works_once_built_or_given_a_subject(
        self, valid_metadata, text_block
    ):
        builder = EmailBuilder().metadata(valid_metadata).section(FullWidth(content=text_block))
        envelope = {k: v for k, v in ENVELOPE.items() if k != "subject"}
        assert build_message(builder.build(), **envelope)["Subject"]
        assert build_message(builder, **ENVELOPE)["Subject"] == ENVELOPE["subject"]


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
        # No CID images, so no multipart/related and no MIME boundary —
        # this path is byte-identical outright.
        first = build_message(plain_email, **ENVELOPE).as_bytes()
        second = build_message(plain_email, **ENVELOPE).as_bytes()
        assert first == second

    def test_multipart_assembly_is_deterministic_modulo_mime_boundary(self, cid_email):
        # An email with CID images becomes multipart/related, and
        # EmailMessage.make_related() never sets a boundary, so the stdlib
        # generator draws a fresh random one per as_bytes() call — that is
        # the one axis on which two assemblies of the same input are
        # allowed to differ (see svc/delivery/message.py's docstring).
        first = build_message(cid_email, **ENVELOPE).as_bytes()
        second = build_message(cid_email, **ENVELOPE).as_bytes()

        # The non-determinism is real, not a hypothetical — assert it so
        # this test cannot pass vacuously if a future stdlib pins the
        # boundary and the claim below becomes trivially true.
        assert first != second

        assert _normalize_boundary(first) == _normalize_boundary(second)


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

    def test_multipart_related_names_the_root_part_type(self, cid_email):
        # RFC 2387: multipart/related needs a 'type' param naming the root
        # part's media type, or a strict client has no defined way to pick
        # text/html out of the image/* parts sitting alongside it.
        message = build_message(cid_email, **ENVELOPE)
        assert message.get_param("type") == "text/html"

    def test_content_id_header_matches_the_html_cid_reference_exactly(self, cid_email):
        # Deliberately bare, not "<id@domain>": the HTML the builder already
        # rendered says src="cid:<bare-id>", and RFC 2392 defines a cid: URL
        # as the Content-ID with only the brackets removed. Qualifying the
        # header with a domain here, without also rewriting the HTML, would
        # make the two sides disagree and break every embedded image.
        html = cid_email.render()
        referenced = set(collect_cid_references(html))
        message = build_message(cid_email, **ENVELOPE)
        images = [p for p in message.walk() if p.get_content_maintype() == "image"]
        for part in images:
            bare = part["Content-ID"].strip("<>")
            assert "@" not in bare
            assert bare in referenced

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

    def test_attached_but_unreferenced_asset_warns_but_still_assembles(self, png_bytes):
        # Not fatal: the cost is only message weight, and treating it as
        # fatal would turn any gap in the (necessarily incomplete) HTML
        # collector into a false rejection of a valid email.
        stub = _StubEmail("<p>no images here</p>", [_asset("orphan1", png_bytes)])
        with pytest.warns(UserWarning, match="orphan1"):
            message = build_message(stub, **ENVELOPE)
        assert message.get_content_type() == "multipart/related"

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

    def test_saved_message_uses_crlf_line_endings(self, cid_email, tmp_path):
        # RFC 5322 mandates CRLF; the default policy generates bare LF, which
        # a strict client is entitled to reject even though Python's own
        # parser tolerates it.
        path = save_eml(build_message(cid_email, **ENVELOPE), tmp_path / "crlf.eml")
        raw = path.read_bytes()
        assert b"\r\n" in raw
        assert raw.replace(b"\r\n", b"").count(b"\n") == 0

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
