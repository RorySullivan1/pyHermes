"""
Tests for image sources, embed strategies, and the attachment manifest.

The through-line: the builder decides each image's ``src`` and *declares*
what a delivery layer must attach, but never attaches anything itself. So
these tests care about two things — that the ``src`` is right for the
strategy, and that the manifest matches the ``cid:`` references in the HTML.
"""

import base64
import dataclasses

import pytest

from svc.builder import (
    ChartBlock,
    EmailBuilder,
    EmailImage,
    FullWidth,
    ImageBlock,
    TextBlock,
    TwoColumn,
)
from svc.builder.enums import EmbedStrategy
from svc.builder.exceptions import SizeError, ValidationError
from svc.builder.images import INLINE_LIMIT_KB, dedupe_assets, sniff_image_type
from svc.builder.models import EmailMetadata


class TestSniffing:
    def test_detects_png(self, png_bytes):
        assert sniff_image_type(png_bytes) == ("image/png", ".png")

    def test_detects_jpeg(self, jpeg_bytes):
        assert sniff_image_type(jpeg_bytes) == ("image/jpeg", ".jpg")

    def test_detects_gif(self, gif_bytes):
        assert sniff_image_type(gif_bytes) == ("image/gif", ".gif")

    def test_reads_bytes_not_the_extension(self, tmp_path, png_bytes):
        # A PNG misnamed .jpg is still a PNG; the extension is a claim.
        lying = tmp_path / "actually-a-png.jpg"
        lying.write_bytes(png_bytes)
        assert EmailImage.attached(lying, alt="x").mime_type == "image/png"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError, match="empty"):
            sniff_image_type(b"")

    def test_webp_rejection_names_outlook(self):
        webp = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 16
        with pytest.raises(ValidationError, match="WebP"):
            sniff_image_type(webp)

    def test_svg_rejection_names_svg(self):
        with pytest.raises(ValidationError, match="SVG"):
            sniff_image_type(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')

    def test_rejects_an_unknown_format(self):
        with pytest.raises(ValidationError, match="Unrecognised"):
            sniff_image_type(b"NOT-AN-IMAGE" + b"\x00" * 16)


class TestHosted:
    def test_src_is_the_url(self):
        image = EmailImage.hosted("https://cdn.test/c.png", alt="Chart")
        assert image.src == "https://cdn.test/c.png"
        assert image.strategy == EmbedStrategy.REMOTE

    def test_has_no_asset_to_attach(self):
        # Nothing to attach: the bytes live on someone else's server.
        assert EmailImage.hosted("https://cdn.test/c.png", alt="Chart").asset is None

    def test_rejects_an_empty_url(self):
        with pytest.raises(ValidationError, match="requires a url"):
            EmailImage.hosted("", alt="Chart")

    @pytest.mark.parametrize(
        "url", ["javascript:alert(1)", "vbscript:msgbox(1)", "file:///etc/passwd"]
    )
    def test_rejects_unsafe_schemes(self, url):
        with pytest.raises(ValidationError, match="scheme"):
            EmailImage.hosted(url, alt="Chart")

    def test_accepts_a_relative_url(self):
        assert EmailImage.hosted("images/c.png", alt="Chart").src == "images/c.png"


class TestAttached:
    def test_src_is_a_cid_reference(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart")
        assert image.src == f"cid:{image.content_id}"

    def test_reads_from_a_path(self, png_file):
        image = EmailImage.attached(png_file, alt="Chart")
        assert image.mime_type == "image/png"
        assert image.filename == "chart.png"

    def test_unreadable_path_raises(self, tmp_path):
        with pytest.raises(ValidationError, match="cannot read image file"):
            EmailImage.attached(tmp_path / "nope.png", alt="Chart")

    def test_content_id_is_derived_from_the_bytes(self, png_bytes):
        # Content-addressed, so the same input always gives the same output.
        first = EmailImage.attached(png_bytes, alt="a")
        second = EmailImage.attached(png_bytes, alt="b")
        assert first.content_id == second.content_id

    def test_different_bytes_get_different_ids(self, png_bytes, other_png_bytes):
        assert (
            EmailImage.attached(png_bytes, alt="a").content_id
            != EmailImage.attached(other_png_bytes, alt="b").content_id
        )

    def test_accepts_an_explicit_content_id(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart", content_id="factor-chart")
        assert image.src == "cid:factor-chart"

    # "" is absent deliberately: an empty content_id means "derive one from
    # the bytes", covered by test_content_id_is_derived_from_the_bytes.
    @pytest.mark.parametrize("bad", ["has space", "<angled>", "with@at", "a" * 129])
    def test_rejects_an_unsafe_content_id(self, png_bytes, bad):
        with pytest.raises(ValidationError, match="content_id"):
            EmailImage.attached(png_bytes, alt="Chart", content_id=bad)

    def test_asset_carries_what_the_delivery_layer_needs(self, png_bytes):
        asset = EmailImage.attached(png_bytes, alt="Chart").asset
        assert asset is not None
        assert asset.data == png_bytes
        assert asset.mime_type == "image/png"
        assert asset.filename.endswith(".png")
        # Bare: the cid: prefix and the <> of a MIME header are each added by
        # the consumer that needs them.
        assert "<" not in asset.content_id and not asset.content_id.startswith("cid:")

    def test_default_filename_falls_back_to_the_content_id(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart")
        assert image.filename == f"{image.content_id}.png"


class TestInline:
    def test_src_is_a_data_uri(self, png_bytes):
        image = EmailImage.inline(png_bytes, alt="Chart")
        assert image.src == f"data:image/png;base64,{base64.b64encode(png_bytes).decode()}"

    def test_carries_no_asset(self, png_bytes):
        # The bytes are already in the HTML; there is nothing left to attach.
        assert EmailImage.inline(png_bytes, alt="Chart").asset is None

    def test_rejects_an_image_over_the_inline_cap(self, png_bytes):
        # Padding a real PNG keeps the signature valid while blowing the cap.
        oversized = png_bytes + b"\x00" * (INLINE_LIMIT_KB * 1024)
        with pytest.raises(SizeError, match="per-image cap"):
            EmailImage.inline(oversized, alt="Chart")

    def test_the_cap_error_points_at_the_alternative(self, png_bytes):
        oversized = png_bytes + b"\x00" * (INLINE_LIMIT_KB * 1024)
        with pytest.raises(SizeError, match="EmailImage.attached"):
            EmailImage.inline(oversized, alt="Chart")


class TestSharedValidation:
    @pytest.mark.parametrize("alt", ["", "   "])
    def test_alt_text_is_required(self, png_bytes, alt):
        # Alt text is what the reader sees while images are blocked, which
        # for Outlook desktop is the default state.
        with pytest.raises(ValidationError, match="image.alt"):
            EmailImage.attached(png_bytes, alt=alt)

    @pytest.mark.parametrize("width", [0, -10, 1.5, "300", True])
    def test_width_must_be_positive_pixels(self, width):
        with pytest.raises(ValidationError, match="image.width"):
            EmailImage.hosted("https://cdn.test/c.png", alt="Chart", width=width)

    def test_width_may_be_omitted(self):
        assert EmailImage.hosted("https://cdn.test/c.png", alt="Chart").width is None


class TestDecorativeImages:
    """
    ``alt=""`` is an assertion, not an absence (#149).

    It is the only correct value for an image carrying no information: an
    omitted attribute makes a screen reader announce the filename, and any
    string makes it announce the decoration. The rule above stays exactly as
    it is for content images; this is the one deliberate opt-out.
    """

    @pytest.mark.parametrize("strategy", ["hosted", "attached", "inline"])
    def test_every_strategy_takes_the_opt_out(self, png_bytes, strategy):
        source = "https://cdn.test/rule.png" if strategy == "hosted" else png_bytes
        image = getattr(EmailImage, strategy)(source, decorative=True)
        assert image.alt == ""
        assert image.decorative is True

    @pytest.mark.parametrize("alt", ["", "   "])
    def test_an_empty_string_alone_still_raises(self, alt):
        """
        The opt-out must be unreachable by accident, or it stops being one:
        a caller who forgot alt text has to keep failing.
        """
        with pytest.raises(ValidationError, match="image.alt"):
            EmailImage.hosted("https://cdn.test/c.png", alt=alt)

    def test_the_error_names_the_opt_out(self):
        with pytest.raises(ValidationError, match="decorative=True"):
            EmailImage.hosted("https://cdn.test/c.png")

    def test_alt_text_and_decorative_together_raise(self):
        """Two contradictory claims about the same image."""
        with pytest.raises(ValidationError, match="cannot also carry alt text"):
            EmailImage.hosted("https://cdn.test/c.png", alt="Chart", decorative=True)

    def test_the_render_carries_the_marker(self, engine):
        """
        ``alt=""`` alone is indistinguishable from a forgotten alt in the
        rendered HTML, so the annotation is what says which one it is — the
        job ``role="presentation"`` already does for a layout table.
        """
        html = ImageBlock("https://cdn.test/rule.png", decorative=True).render(engine)
        assert 'alt=""' in html
        assert 'role="presentation"' in html

    def test_a_content_image_carries_no_marker(self, engine):
        html = ImageBlock("https://cdn.test/c.png", alt_text="Chart").render(engine)
        img = html[html.index("<img ") : html.index(">", html.index("<img "))]
        assert 'role="presentation"' not in img
        assert 'role="presentation"' in html, "the wrapper table still declares itself"

    def test_it_projects_to_nothing_in_the_text_part(self):
        """
        Not to an empty ``[]`` — the mirror of ``alt=""``. The caption still
        projects: that is copy the reader is meant to read either way.
        """
        block = ImageBlock("https://cdn.test/rule.png", decorative=True, caption="Fig 1")
        assert "[]" not in block.text()
        assert "Fig 1" in block.text()


class TestImageBlock:
    def test_renders_the_src_and_alt(self, engine, png_bytes):
        html = ImageBlock(EmailImage.attached(png_bytes, alt="Factor returns")).render(engine)
        assert 'alt="Factor returns"' in html
        assert "cid:" in html

    def test_emits_the_width_attribute_for_outlook(self, engine):
        # Outlook's Word engine honours the attribute and ignores max-width.
        html = ImageBlock("https://cdn.test/c.png", alt_text="Chart", width=300).render(engine)
        assert 'width="300"' in html

    def test_defaults_to_full_width(self, engine):
        html = ImageBlock("https://cdn.test/c.png", alt_text="Chart").render(engine)
        assert 'width="100%"' in html

    def test_accepts_a_bare_url(self, engine):
        html = ImageBlock("https://cdn.test/c.png", alt_text="Chart").render(engine)
        assert "https://cdn.test/c.png" in html

    def test_a_bare_url_still_needs_alt_text(self):
        with pytest.raises(ValidationError, match="image.alt"):
            ImageBlock("https://cdn.test/c.png")

    def test_renders_a_caption(self, engine):
        html = ImageBlock("https://cdn.test/c.png", alt_text="C", caption="Source: X").render(
            engine
        )
        assert "Source: X" in html

    def test_wraps_in_a_link(self, engine):
        html = ImageBlock(
            "https://cdn.test/c.png", alt_text="C", link_url="https://x.test/report"
        ).render(engine)
        assert 'href="https://x.test/report"' in html

    def test_rejects_an_unsafe_link_url(self):
        with pytest.raises(ValidationError, match="link_url"):
            ImageBlock("https://cdn.test/c.png", alt_text="C", link_url="javascript:alert(1)")

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_alignment(self, engine, align):
        html = ImageBlock("https://cdn.test/c.png", alt_text="C", align=align).render(engine)
        assert f'align="{align}"' in html

    def test_rejects_an_unknown_alignment(self):
        with pytest.raises(ValidationError, match="alignment"):
            ImageBlock("https://cdn.test/c.png", alt_text="C", align="justified")

    def test_requires_an_image(self):
        with pytest.raises(ValidationError, match="requires an image"):
            ImageBlock("")

    def test_escapes_the_src_so_it_cannot_break_out_of_the_attribute(self, engine):
        html = ImageBlock('https://cdn.test/c.png?a="b', alt_text="Chart").render(engine)
        assert 'src="https://cdn.test/c.png?a=&quot;b"' in html

    def test_escapes_the_alt_text(self, engine):
        html = ImageBlock("https://cdn.test/c.png", alt_text='S&P "YTD"').render(engine)
        assert 'alt="S&amp;P &quot;YTD&quot;"' in html

    def test_reports_its_image_and_asset(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart")
        block = ImageBlock(image)
        assert block.images() == [image]
        assert [a.content_id for a in block.assets()] == [image.content_id]

    def test_a_hosted_image_contributes_no_asset(self):
        assert ImageBlock("https://cdn.test/c.png", alt_text="C").assets() == []


class TestChartBlockImages:
    def test_still_accepts_a_bare_url(self, engine):
        html = ChartBlock(image_url="https://x.test/c.png", alt_text="Chart").render(engine)
        assert "https://x.test/c.png" in html

    def test_accepts_an_email_image(self, engine, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Factor returns", width=616)
        html = ChartBlock(image, source="Source: Bloomberg").render(engine)
        assert f'src="cid:{image.content_id}"' in html
        assert 'width="616"' in html
        assert 'alt="Factor returns"' in html

    def test_an_email_image_surfaces_in_the_manifest(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart")
        assert [a.content_id for a in ChartBlock(image).assets()] == [image.content_id]

    def test_width_applies_to_a_bare_url(self, engine):
        html = ChartBlock("https://x.test/c.png", alt_text="C", width=400).render(engine)
        assert 'width="400"' in html

    def test_legacy_attributes_still_read(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart")
        assert ChartBlock(image).image_url == image.src
        assert ChartBlock(image).alt_text == "Chart"


class TestHeaderImages:
    """
    The masthead's images belong to the header region, not the metadata.

    The flat keywords still build that header, which is what keeps an email
    written before the split working unchanged.
    """

    def test_logo_accepts_an_email_image(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        metadata = EmailMetadata(**valid_metadata, logo_url=image)
        metadata.validate()
        assert metadata.banner.context({})["logo_url"] == image.src

    def test_a_plain_url_is_untouched(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, logo_url="https://cdn.test/l.png")
        assert metadata.banner.context({})["logo_url"] == "https://cdn.test/l.png"

    def test_header_images_reach_the_manifest(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        metadata = EmailMetadata(**valid_metadata, header_bg_image_url=image)
        assert [a.content_id for a in metadata.banner.assets()] == [image.content_id]

    def test_a_plain_url_still_has_its_scheme_checked(self, valid_metadata):
        # Now at construction: the header validates in __init__, so the flat
        # keyword raises where it is written rather than at .validate().
        with pytest.raises(ValidationError, match="banner.logo_url"):
            EmailMetadata(**valid_metadata, logo_url="javascript:alert(1)")

    def test_to_dict_covers_every_field_but_the_regions_and_the_bound_ones(self, valid_metadata):
        """
        A region renders itself; it reaches base.html as its slot strings.
        The theme and the size theme reach every template through the bound
        engine, so both are out for the mirror-image reason — one value,
        one source.
        """
        metadata = EmailMetadata(**valid_metadata)
        declared = {f.name for f in dataclasses.fields(EmailMetadata)}
        assert set(metadata.to_dict()) == declared - {
            "header",
            "banner",
            "footer",
            "theme",
            "size_theme",
            "font_theme",
        }


class TestEmailManifest:
    def _email(self, valid_metadata, *sections):
        builder = EmailBuilder().metadata(valid_metadata)
        for section in sections:
            builder.section(section)
        return builder.build()

    def test_no_images_means_an_empty_manifest(self, valid_metadata, text_block):
        assert self._email(valid_metadata, FullWidth(content=text_block)).assets() == []

    def test_collects_across_sections(self, valid_metadata, png_bytes, other_png_bytes):
        one = EmailImage.attached(png_bytes, alt="One")
        two = EmailImage.attached(other_png_bytes, alt="Two")
        email = self._email(
            valid_metadata,
            FullWidth(content=ImageBlock(one)),
            FullWidth(content=ChartBlock(two)),
        )
        assert [a.content_id for a in email.assets()] == [one.content_id, two.content_id]

    def test_collects_from_both_columns(self, valid_metadata, png_bytes, other_png_bytes):
        one = EmailImage.attached(png_bytes, alt="One")
        two = EmailImage.attached(other_png_bytes, alt="Two")
        email = self._email(valid_metadata, TwoColumn(left=ImageBlock(one), right=ImageBlock(two)))
        assert len(email.assets()) == 2

    def test_metadata_images_come_first(self, valid_metadata, png_bytes, other_png_bytes):
        logo = EmailImage.attached(png_bytes, alt="Logo")
        chart = EmailImage.attached(other_png_bytes, alt="Chart")
        email = self._email(
            {**valid_metadata, "logo_url": logo}, FullWidth(content=ImageBlock(chart))
        )
        assert [a.content_id for a in email.assets()] == [logo.content_id, chart.content_id]

    def test_the_same_image_is_attached_once(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart")
        email = self._email(
            valid_metadata,
            FullWidth(content=ImageBlock(image)),
            FullWidth(content=ChartBlock(image)),
        )
        assert len(email.assets()) == 1

    def test_hosted_and_inline_images_are_absent(self, valid_metadata, png_bytes):
        email = self._email(
            valid_metadata,
            FullWidth(content=ImageBlock("https://cdn.test/c.png", alt_text="Hosted")),
            FullWidth(content=ImageBlock(EmailImage.inline(png_bytes, alt="Inline"))),
        )
        assert email.assets() == []
        # ...but both are still images the email knows about.
        assert len(email.images()) == 2

    def test_every_cid_in_the_html_has_a_manifest_entry(self, valid_metadata, png_bytes):
        import re

        image = EmailImage.attached(png_bytes, alt="Chart")
        email = self._email(valid_metadata, FullWidth(content=ImageBlock(image)))
        html = email.render()
        referenced = set(re.findall(r'src="cid:([^"]+)"', html))
        assert referenced == {a.content_id for a in email.assets()}

    def test_builder_exposes_the_manifest(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Chart")
        builder = (
            EmailBuilder().metadata(valid_metadata).section(FullWidth(content=ImageBlock(image)))
        )
        assert [a.content_id for a in builder.assets()] == [image.content_id]

    def test_a_data_uri_grows_the_html(self, valid_metadata, png_bytes):
        # The point of the strategy trade-off: inlining moves bytes into the
        # document, where they count against the 102 KB Gmail limit.
        plain = self._email(valid_metadata, FullWidth(content=TextBlock("<p>x</p>"))).render()
        inlined = self._email(
            valid_metadata, FullWidth(content=ImageBlock(EmailImage.inline(png_bytes, alt="I")))
        ).render()
        assert len(inlined) > len(plain) + len(base64.b64encode(png_bytes))


class TestDedupeAssets:
    def test_keeps_first_seen_order(self, png_bytes, other_png_bytes):
        a = EmailImage.attached(png_bytes, alt="a").asset
        b = EmailImage.attached(other_png_bytes, alt="b").asset
        assert dedupe_assets([a, b, a]) == [a, b]

    def test_empty(self):
        assert dedupe_assets([]) == []


class TestContentIdErrorMessage:
    """The rejection must describe what really happens to a Content-ID (#73)."""

    def test_does_not_promise_that_delivery_adds_an_at_sign(self, png_bytes):
        # svc/delivery emits `Content-ID: <bare-id>` and cannot qualify it:
        # RFC 2392 makes a cid: URL the id minus its brackets, so an "@"
        # would stop matching the src="cid:..." the builder already wrote --
        # and _CONTENT_ID_RE forbids "@" anyway.
        with pytest.raises(ValidationError) as caught:
            EmailImage.attached(png_bytes, alt="Chart", content_id="bad id!")
        message = str(caught.value)
        assert "added by the delivery layer" not in message
        assert "angle brackets" in message.lower()

    def test_an_at_sign_is_rejected_like_any_other_illegal_character(self, png_bytes):
        with pytest.raises(ValidationError):
            EmailImage.attached(png_bytes, alt="Chart", content_id="id@example.com")
