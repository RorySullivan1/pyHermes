"""
Skeleton parameters: the logo's alt/width, and the footer link labels.

Everything here follows one rule — anything that isn't core formatting
should be passable, and every default reproduces what base.html hardcoded
before, so an existing email renders unchanged unless it opts in.

Fonts, colours, padding and table geometry are deliberately NOT parameters:
they are the design system, not content.
"""

import pytest

from pyhermes.builder import Banner, EmailBuilder, FullWidth
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import EmailMetadata

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
        header = EmailMetadata(**valid_metadata).banner
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
        header = EmailMetadata(**valid_metadata).banner
        assert header.resolved_logo_width() == Banner.DEFAULT_LOGO_WIDTH
        header.logo_url = EmailImage.hosted("https://x.test/l.png", alt="a", width=64)
        assert header.resolved_logo_width() == 64
        header.logo_width = 200
        assert header.resolved_logo_width() == 200


#: A default footer link renders only once its URL is set (#258).
URLS = {"unsubscribe_url": "https://example.com/u", "view_in_browser_url": "https://example.com/v"}


class TestSkeletonCopy:
    @pytest.fixture
    def valid_metadata(self, valid_metadata):
        return {**valid_metadata, **URLS}

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
        """
        #115 completed this: the wording travelled from #64, the language
        declaration did not, so a French newsletter announced itself as
        English. Both halves are asserted here because they are one claim —
        a template fork is avoided only if *everything* language-dependent
        is a parameter.
        """
        html = render(
            valid_metadata,
            text_block,
            language="fr",
            unsubscribe_label="Se désabonner",
            view_in_browser_label="Voir en ligne",
        )
        for text in ('lang="fr"', "Se désabonner", "Voir en ligne"):
            assert text in html
        assert 'lang="en"' not in html

    def test_labels_are_escaped(self, valid_metadata, text_block):
        html = render(valid_metadata, text_block, unsubscribe_label="R&D")
        assert "R&amp;D" in html


class TestTheLanguageDeclaration:
    """
    #115. The field's own shape is tested in ``tests/test_models.py``; what
    is checked here is that it reaches the one attribute it exists for.
    """

    def test_the_default_declares_english(self, valid_metadata, text_block):
        assert 'lang="en"' in render(valid_metadata, text_block)

    def test_a_regional_tag_reaches_the_root_element(self, valid_metadata, text_block):
        assert 'lang="en-GB"' in render(valid_metadata, text_block, language="en-GB")

    def test_it_is_the_root_element_that_carries_it(self, valid_metadata, text_block):
        """
        Not merely *somewhere* in the document: a ``lang`` on the wrong
        element scopes to that element, and the point of the field is that
        the whole message is declared. The skeleton opens the root element
        on line two, under the doctype.
        """
        html = render(valid_metadata, text_block, language="pt-BR")
        assert html.splitlines()[1].startswith('<html lang="pt-BR"')
