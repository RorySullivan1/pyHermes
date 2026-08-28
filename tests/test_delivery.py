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


def _normalize_boundaries(raw: bytes) -> bytes:
    """Replace every random MIME boundary with a fixed, positional token.

    The stdlib leaves a boundary unset until serialisation, then draws one
    from ``random.randrange()`` — one draw per multipart per
    ``build_message()`` call, since each call builds a fresh
    ``EmailMessage``. See the module docstring on
    ``svc/delivery/message.py``.

    **Every**, not the first: since #111 a message is always a
    ``multipart/alternative``, and one with CID images carries a second
    boundary for the nested ``multipart/related``. Normalising only the
    first is the exact trap that docstring warns about — the comparison
    then still differs on the other and the test fails for a reason that
    has nothing to do with what it is checking.

    Each token appears in a ``Content-Type`` header and in every
    ``--<token>`` delimiter line built from it, and is the *only* thing
    that varies between two assemblies of the same input.
    """
    for index, match in enumerate(_BOUNDARY_RE.finditer(raw)):
        raw = raw.replace(match.group(1), b"BOUNDARY-%d" % index)
    return raw


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

    def __init__(self, html: str, assets: list[ImageAsset], text: str = "stub text"):
        self._html = html
        self._assets = assets
        self._text = text

    def render(self) -> str:
        return self._html

    def text(self) -> str:
        return self._text

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

    def test_ignores_a_cid_looking_string_in_prose_attributes(self):
        # alt/title/aria-label are caller-supplied prose, not fetchable
        # references -- a "cid:"-looking string there must not be treated
        # as a manifest requirement, or a stray alt text rejects an
        # otherwise valid email.
        html = (
            '<img src="https://x/y.png" alt="cid:not-an-asset" '
            'title="cid:also-not-an-asset" aria-label="cid:nope">'
        )
        assert collect_cid_references(html) == []

    @pytest.mark.parametrize(
        "attr", ["src", "href", "xlink:href", "background", "poster", "srcset"]
    )
    def test_finds_references_in_every_fetching_attribute(self, attr):
        html = f'<x {attr}="cid:abc123">'
        assert collect_cid_references(html) == ["abc123"]


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
        # Banner injection: a bare newline reaching email.policy raises
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

    @pytest.mark.parametrize("fixture", ["plain_email", "cid_email"])
    def test_assembly_is_deterministic_modulo_mime_boundaries(self, fixture, request):
        """
        Assembly is pure — no clock, no network, no ``random`` of its own —
        so two builds of one input differ *only* in the boundaries the
        stdlib draws at serialisation.

        Both paths carry at least one now: #111 made every message a
        ``multipart/alternative``, so the no-images case is no longer
        byte-identical outright, and the images case carries a second.
        """
        email = request.getfixturevalue(fixture)
        first = build_message(email, **ENVELOPE).as_bytes()
        second = build_message(email, **ENVELOPE).as_bytes()

        # The non-determinism is real, not a hypothetical — assert it so
        # this test cannot pass vacuously if a future stdlib pins the
        # boundary and the claim below becomes trivially true.
        assert first != second

        assert _normalize_boundaries(first) == _normalize_boundaries(second)

    def test_an_email_with_images_carries_two_boundaries(self, cid_email):
        """
        The count the module docstring now names, asserted — because code
        written against the old single-boundary shape normalises one and
        still differs on the other, and that failure is confusing rather
        than informative.
        """
        raw = build_message(cid_email, **ENVELOPE).as_bytes()
        assert len(_BOUNDARY_RE.findall(raw)) == 2


def _structure(message) -> list[tuple[int, str]]:
    """(depth, content-type) for every part, in document order."""

    def walk(part, depth=0):
        yield depth, part.get_content_type()
        if part.is_multipart():
            for child in part.get_payload():
                yield from walk(child, depth + 1)

    return list(walk(message))


class TestStructure:
    def test_an_email_without_images_is_text_then_html(self, plain_email):
        message = build_message(plain_email, **ENVELOPE)
        assert _structure(message) == [
            (0, "multipart/alternative"),
            (1, "text/plain"),
            (1, "text/html"),
        ]

    def test_an_email_with_images_nests_the_related_subtree(self, cid_email):
        """
        The reserved structure, exactly as the module docstring promised it
        before #111: the ``multipart/related`` subtree is what it always was,
        one level deeper.
        """
        message = build_message(cid_email, **ENVELOPE)
        assert _structure(message) == [
            (0, "multipart/alternative"),
            (1, "text/plain"),
            (1, "multipart/related"),
            (2, "text/html"),
            (2, "image/png"),
            (2, "image/png"),
        ]

    def test_the_text_part_comes_first(self, plain_email):
        """
        RFC 2046 §5.1.4 orders an alternative by *increasing* preference, so
        the fallback goes first. Reversing them is silent: every graphical
        client still shows the HTML, and only the readers who need the
        fallback see the wrong thing.
        """
        parts = build_message(plain_email, **ENVELOPE).get_payload()
        assert [p.get_content_type() for p in parts] == ["text/plain", "text/html"]

    def test_the_text_part_is_what_the_builder_projected(self, plain_email):
        message = build_message(plain_email, **ENVELOPE)
        part = message.get_payload()[0]
        assert part.get_content().rstrip("\n") == plain_email.text()

    def test_the_images_relate_to_the_html_not_to_the_alternative(self, cid_email):
        """
        They are resources of the HTML alternative specifically. Relating
        them to the alternative would attach them to the text part too —
        which is how a text-only reader ends up with a paperclip for art
        they cannot see.
        """
        message = build_message(cid_email, **ENVELOPE)
        text_part, related = message.get_payload()
        assert text_part.get_content_type() == "text/plain"
        assert not text_part.is_multipart()
        assert [p.get_content_maintype() for p in related.get_payload()[1:]] == ["image", "image"]

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
        # text/html out of the image/* parts sitting alongside it. Since #111
        # that param belongs to the nested related part, not the top level.
        related = build_message(cid_email, **ENVELOPE).get_payload()[-1]
        assert related.get_content_type() == "multipart/related"
        assert related.get_param("type") == "text/html"

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
        assert _structure(message) == [
            (0, "multipart/alternative"),
            (1, "text/plain"),
            (1, "multipart/related"),
            (2, "text/html"),
            (2, "image/png"),
        ]

    def test_matching_manifest_assembles(self, png_bytes):
        stub = _StubEmail('<img src="cid:ok1">', [_asset("ok1", png_bytes)])
        assert build_message(stub, **ENVELOPE).get_payload()[-1].get_content_type() == (
            "multipart/related"
        )

    def test_a_text_part_mentioning_cid_does_not_trip_the_check(self, png_bytes):
        """
        The cross-check is scoped to the HTML deliberately: the text part
        carries URLs as text and never a ``cid:`` reference, so documentation
        copy that happens to say ``cid:`` must not be read as one — nor
        satisfy a reference the HTML makes.
        """
        stub = _StubEmail(
            "<p>no images here</p>",
            [],
            text="Attached images use cid:missing1 references.",
        )
        message = build_message(stub, **ENVELOPE)
        assert _structure(message) == [
            (0, "multipart/alternative"),
            (1, "text/plain"),
            (1, "text/html"),
        ]

    def test_unusable_mime_type_is_rejected(self, png_bytes):
        broken = ImageAsset(
            content_id="bad1", data=png_bytes, mime_type="image-png", filename="bad1.png"
        )
        stub = _StubEmail('<img src="cid:bad1">', [broken])
        with pytest.raises(MessageError, match="bad1"):
            build_message(stub, **ENVELOPE)

    def test_builder_errors_are_not_swallowed(self, valid_metadata):
        class _Exploding:
            def text(self) -> str:
                return "text"

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
        assert _structure(reparsed) == [
            (0, "multipart/alternative"),
            (1, "text/plain"),
            (1, "multipart/related"),
            (2, "text/html"),
            (2, "image/png"),
            (2, "image/png"),
        ]


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
