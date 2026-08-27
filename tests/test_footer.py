"""The reworked footer region: one slot, structured presentation, optional disclaimer."""

import pytest

from svc.builder import EmailBuilder, Footer, FullWidth, TextBlock
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.images import EmailImage

TEMPLATE_DIR = TemplateEngine().template_dir


def _render(footer: Footer | None = None) -> str:
    builder = EmailBuilder().metadata(
        {"email_subject": "S", "firm_name": "F", "campaign_name": "c", "current_year": "2026"}
    )
    if footer is not None:
        builder.footer(footer)
    return builder.section(FullWidth(content=TextBlock("<p>Body.</p>"))).render()


class TestFooterStructure:
    def test_base_html_has_one_footer_slot(self):
        base = (TEMPLATE_DIR / "base.html").read_text(encoding="utf-8")
        assert "{{ footer_html }}" in base
        assert "{{ footer_contact_html }}" not in base
        assert "{{ footer_legal_html }}" not in base

    def test_old_templates_are_gone(self):
        assert not (TEMPLATE_DIR / "regions" / "footer-contact.html").exists()
        assert not (TEMPLATE_DIR / "regions" / "footer-legal.html").exists()
        assert (TEMPLATE_DIR / "regions" / "footer.html").is_file()

    def test_copyright_and_links_always_render(self):
        html = _render()
        assert "&copy;" in html and "2026" in html
        assert "Unsubscribe" in html and "View in browser" in html


class TestDisclaimer:
    def test_empty_disclaimer_omits_the_line(self):
        # When no disclaimer is set, no disclaimer <div> should appear.
        html_no_disc = _render(Footer())
        html_with_disc = _render(Footer(disclaimer="UNIQUEMARK"))
        # The unique marker only appears in the second render.
        assert "UNIQUEMARK" not in html_no_disc
        assert "UNIQUEMARK" in html_with_disc
        # The footer of an empty-disclaimer render contains no disclaimer <div>.
        # Split on /Main container to get to the footer region.
        footer_section = html_no_disc.split("/Main container")[1]
        assert '<div style="font-family:Arial' not in footer_section

    def test_block_disclaimer_renders_without_breaking_its_wrapper(self):
        # The #3 regression: a <p> disclaimer must NOT sit inside a <p>.
        # The template wraps the disclaimer in a <div>, never a <p>.
        html = _render(Footer(disclaimer="<p>Not advice.</p>"))
        assert "<p>Not advice.</p>" in html
        # The disclaimer must be inside a <div>, not a wrapping <p>.
        # Find where the disclaimer appears and check the surrounding context.
        idx = html.index("<p>Not advice.</p>")
        # Look back 200 chars for an opening <p> that wraps our disclaimer.
        context_before = html[max(0, idx - 200) : idx]
        # There should be no unclosed <p ...> immediately before our <p>.
        # The template uses a <div> wrapper, so we should see a <div before us.
        assert "<div" in context_before
        # The immediate parent element should be a div, not a p.
        # Confirm the template wraps disclaimer in a div by checking no <p>\n...<p> pattern.
        legal = html.split("/Main container")[1]
        assert "<p>\n                <p>" not in legal


class TestPresentation:
    def test_border_adds_a_box(self):
        assert "border:1px solid" in _render(Footer(border=True))

    def test_background_color_is_applied_and_validated(self):
        assert "#123456" in _render(Footer(background_color="#123456"))
        with pytest.raises(ValidationError):
            Footer(background_color="red")

    def test_image_renders_and_enters_the_manifest(self, png_bytes):
        footer = Footer(image=EmailImage.attached(png_bytes, alt="Sign-off", width=100))
        html = _render(footer)
        assert 'alt="Sign-off"' in html and 'width="100"' in html
        assert footer.assets(), "attached footer image must reach the asset manifest"

    def test_image_width_falls_back_to_default(self, png_bytes):
        footer = Footer(image=EmailImage.attached(png_bytes, alt="x"))
        assert 'width="120"' in _render(footer)


class TestMinimalFooterIsGone:
    def test_it_is_no_longer_importable(self):
        with pytest.raises(ImportError):
            from svc.builder import MinimalFooter  # noqa: F401
