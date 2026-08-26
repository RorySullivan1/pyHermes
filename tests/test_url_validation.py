"""
URL scheme validation (#24).

#12 made every URL attribute-safe — escaping stops a value breaking *out* of
the attribute it sits in. It says nothing about what the URL does when
followed, which is what these tests cover.

Scheme-only by design: whether a URL resolves, and what its host or path
are, is explicitly out of scope.
"""

import pytest

from svc.builder import ChartBlock, EmailBuilder, FullWidth
from svc.builder.exceptions import EmailBuilderError, ValidationError
from svc.builder.models import EmailMetadata, _validate_url

METADATA_URL_FIELDS = [
    "contact_url",
    "unsubscribe_url",
    "view_in_browser_url",
]

#: The masthead URLs moved to the Header region (#34). The flat keywords still
#: reach them, and the error now names where the field lives.
HEADER_URL_FIELDS = {
    "logo_url": "header.logo_url",
    "header_bg_image_url": "header.background_image_url",
}

DANGEROUS = [
    "javascript:alert(1)",
    "vbscript:msgbox(1)",
    "data:text/html,<script>alert(1)</script>",
    "file:///etc/passwd",
]

SAFE = [
    "https://x.test/a.png",
    "http://x.test",
    "mailto:analyst@x.test",
    "mailto:a@b.test?subject=Hi",
    "cid:embedded-logo",
    "/relative/path.png",
    "//cdn.test/protocol-relative.png",
    "",
]


class TestValidateUrlHelper:
    @pytest.mark.parametrize("url", DANGEROUS)
    def test_rejects_dangerous_schemes(self, url):
        with pytest.raises(ValidationError, match="unsupported URL scheme"):
            _validate_url(url, "field")

    @pytest.mark.parametrize("url", SAFE)
    def test_accepts_safe_and_relative_urls(self, url):
        _validate_url(url, "field")

    @pytest.mark.parametrize(
        "url",
        [
            "JaVaScRiPt:alert(1)",
            "JAVASCRIPT:alert(1)",
            " javascript:alert(1)",
            "\tjavascript:alert(1)",
            "\njavascript:alert(1)",
            "java\tscript:alert(1)",
        ],
    )
    def test_rejects_case_and_whitespace_evasions(self, url):
        # The scheme is lowercased and stripped before comparison, so casing
        # and padding cannot smuggle one past; an inner tab makes it an
        # unknown scheme, which is rejected anyway.
        with pytest.raises(ValidationError):
            _validate_url(url, "field")

    def test_a_colon_later_in_the_url_is_not_a_scheme(self):
        # Only the part before the FIRST colon is the scheme — a payload in
        # a query string must not trip the check.
        _validate_url("https://x.test/a?next=javascript:alert(1)", "field")

    def test_error_names_the_field_and_lists_allowed_schemes(self):
        with pytest.raises(ValidationError) as exc:
            _validate_url("javascript:alert(1)", "metadata.contact_url")
        message = str(exc.value)
        assert "metadata.contact_url" in message
        for scheme in ("http", "https", "mailto", "cid"):
            assert scheme in message

    def test_is_catchable_as_the_base_class(self):
        with pytest.raises(EmailBuilderError):
            _validate_url("javascript:alert(1)", "field")


class TestEmailMetadata:
    @pytest.mark.parametrize("field", METADATA_URL_FIELDS)
    def test_every_url_field_is_validated(self, valid_metadata, field):
        valid_metadata[field] = "javascript:alert(1)"
        with pytest.raises(ValidationError, match=field):
            EmailMetadata(**valid_metadata).validate()

    @pytest.mark.parametrize("field", METADATA_URL_FIELDS)
    def test_safe_urls_are_accepted(self, valid_metadata, field):
        valid_metadata[field] = "https://x.test/ok"
        EmailMetadata(**valid_metadata).validate()

    @pytest.mark.parametrize("field", METADATA_URL_FIELDS)
    def test_url_fields_stay_optional(self, valid_metadata, field):
        valid_metadata[field] = ""
        EmailMetadata(**valid_metadata).validate()

    @pytest.mark.parametrize(("field", "named"), sorted(HEADER_URL_FIELDS.items()))
    def test_every_masthead_url_is_validated(self, valid_metadata, field, named):
        """
        The flat keyword still reaches the check; the message names the
        header, because that is where the field lives now.
        """
        valid_metadata[field] = "javascript:alert(1)"
        with pytest.raises(ValidationError, match=named.replace(".", r"\.")):
            EmailMetadata(**valid_metadata)

    @pytest.mark.parametrize("field", sorted(HEADER_URL_FIELDS))
    def test_safe_masthead_urls_are_accepted(self, valid_metadata, field):
        valid_metadata[field] = "https://x.test/ok"
        EmailMetadata(**valid_metadata).validate()

    @pytest.mark.parametrize("field", sorted(HEADER_URL_FIELDS))
    def test_masthead_url_fields_stay_optional(self, valid_metadata, field):
        valid_metadata[field] = ""
        EmailMetadata(**valid_metadata).validate()

    def test_rejected_at_construction_not_render(self, valid_metadata):
        # The repo validates in __init__, not at render time.
        valid_metadata["contact_url"] = "javascript:alert(1)"
        with pytest.raises(ValidationError):
            EmailBuilder().metadata(valid_metadata)


class TestChartBlock:
    @pytest.mark.parametrize("url", DANGEROUS)
    def test_rejects_dangerous_image_urls(self, url):
        with pytest.raises(ValidationError, match="chart.image_url"):
            ChartBlock(image_url=url)

    def test_accepts_a_normal_image_url(self, engine):
        ChartBlock(image_url="https://x.test/chart.png").render(engine)

    def test_accepts_a_cid_url_for_embedded_images(self, engine):
        ChartBlock(image_url="cid:chart-1").render(engine)

    def test_empty_url_still_rejected_by_the_existing_check(self):
        # Pre-existing rule, unchanged: image_url is required.
        with pytest.raises(ValidationError, match="requires an image_url"):
            ChartBlock(image_url="")


def test_a_dangerous_url_never_reaches_the_rendered_email(valid_metadata, text_block):
    valid_metadata["contact_url"] = "javascript:alert(1)"
    with pytest.raises(ValidationError):
        (EmailBuilder().metadata(valid_metadata).section(FullWidth(content=text_block)).render())
