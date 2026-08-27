"""
Skeleton parameters: the logo's alt/width, and the footer link labels.

Everything here follows one rule — anything that isn't core formatting
should be passable, and every default reproduces what base.html hardcoded
before, so an existing email renders unchanged unless it opts in.

Fonts, colours, padding and table geometry are deliberately NOT parameters:
they are the design system, not content.
"""

import pytest

from svc.builder import EmailBuilder, FullWidth, Header
from svc.builder.images import EmailImage
from svc.builder.models import EmailMetadata

LABEL_DEFAULTS = {
    "unsubscribe_label": "Unsubscribe",
    "view_in_browser_label": "View in browser",
}


def render(valid_metadata, text_block, **extra) -> str:
    return (
        EmailBuilder()
        .metadata({**valid_metadata, **extra})
        .section(FullWidth(content=text_block))
        .render()
    )


class TestLogoAlt:
    def test_defaults_to_the_firm_name(self, valid_metadata, text_block):
        # What base.html hardcoded before this was configurable.
        html = render(valid_metadata, text_block, logo_url="https://x.test/l.png")
        assert f'alt="{valid_metadata["firm_name"]}"' in html

    def test_explicit_alt_wins(self, valid_metadata, text_block):
        html = render(
            valid_metadata, text_block, logo_url="https://x.test/l.png", logo_alt="Acme logo"
        )
        assert 'alt="Acme logo"' in html

    def test_an_email_image_supplies_its_own_alt(self, valid_metadata, text_block):
        # Regression: the logo slot used to ignore an EmailImage's alt entirely.
        image = EmailImage.hosted("https://x.test/l.png", alt="Acme wordmark")
        html = render(valid_metadata, text_block, logo_url=image)
        assert 'alt="Acme wordmark"' in html

    def test_metadata_beats_the_image(self, valid_metadata, text_block):
        image = EmailImage.hosted("https://x.test/l.png", alt="from image")
        html = render(valid_metadata, text_block, logo_url=image, logo_alt="from metadata")
        assert 'alt="from metadata"' in html
        assert "from image" not in html

    def test_alt_is_escaped(self, valid_metadata, text_block):
        html = render(
            valid_metadata, text_block, logo_url="https://x.test/l.png", logo_alt='R&D "team"'
        )
        assert 'alt="R&amp;D &quot;team&quot;"' in html

    def test_resolution_order_without_rendering(self, valid_metadata):
        """The chain lives on the header; the firm name is handed to it."""
        firm_name = valid_metadata["firm_name"]
        header = EmailMetadata(**valid_metadata).header
        assert header.resolved_logo_alt(firm_name) == firm_name
        header.logo_url = EmailImage.hosted("https://x.test/l.png", alt="img")
        assert header.resolved_logo_alt(firm_name) == "img"
        header.logo_alt = "explicit"
        assert header.resolved_logo_alt(firm_name) == "explicit"


class TestLogoWidth:
    def test_defaults_to_ninety(self, valid_metadata, text_block):
        html = render(valid_metadata, text_block, logo_url="https://x.test/l.png")
        assert 'width="90"' in html
        assert "max-width:90px" in html

    def test_explicit_width_wins(self, valid_metadata, text_block):
        html = render(valid_metadata, text_block, logo_url="https://x.test/l.png", logo_width=120)
        assert 'width="120"' in html
        assert "max-width:120px" in html

    def test_an_email_image_supplies_its_own_width(self, valid_metadata, text_block):
        image = EmailImage.hosted("https://x.test/l.png", alt="logo", width=64)
        html = render(valid_metadata, text_block, logo_url=image)
        assert 'width="64"' in html

    def test_resolution_order(self, valid_metadata):
        header = EmailMetadata(**valid_metadata).header
        assert header.resolved_logo_width() == Header.DEFAULT_LOGO_WIDTH
        header.logo_url = EmailImage.hosted("https://x.test/l.png", alt="a", width=64)
        assert header.resolved_logo_width() == 64
        header.logo_width = 200
        assert header.resolved_logo_width() == 200


class TestSkeletonCopy:
    @pytest.mark.parametrize(("field", "default"), sorted(LABEL_DEFAULTS.items()))
    def test_defaults_match_what_was_hardcoded(self, valid_metadata, text_block, field, default):
        # The labels are the footer region's copy; the flat keyword
        # is the pre-split spelling, so the default is read off the region.
        assert getattr(EmailMetadata(**valid_metadata).footer, field) == default
        assert default in render(valid_metadata, text_block)

    @pytest.mark.parametrize("field", sorted(LABEL_DEFAULTS))
    def test_each_label_is_overridable(self, valid_metadata, text_block, field):
        html = render(valid_metadata, text_block, **{field: "CUSTOM-LABEL"})
        assert "CUSTOM-LABEL" in html

    def test_a_non_english_newsletter(self, valid_metadata, text_block):
        html = render(
            valid_metadata,
            text_block,
            unsubscribe_label="Se désabonner",
            view_in_browser_label="Voir en ligne",
        )
        for text in ("Se désabonner", "Voir en ligne"):
            assert text in html

    def test_labels_are_escaped(self, valid_metadata, text_block):
        html = render(valid_metadata, text_block, unsubscribe_label="R&D")
        assert "R&amp;D" in html
