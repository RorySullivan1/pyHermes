"""The reworked footer region: one slot, structured presentation, optional disclaimer."""

import pytest

from pyhermes.builder import EmailBuilder, Footer, FullWidth, TextBlock
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import FooterLink, LinkRow

TEMPLATE_DIR = TemplateEngine().template_dir


URLS = {"unsubscribe_url": "https://acme.test/u", "view_in_browser_url": "https://acme.test/v"}


def _builder(footer: Footer | None = None, **facts: str) -> EmailBuilder:
    builder = EmailBuilder().metadata(
        {"email_subject": "S", "firm_name": "F", "campaign_name": "c", "current_year": "2026"}
        | facts
    )
    if footer is not None:
        builder.footer(footer)
    return builder.section(FullWidth(content=TextBlock("<p>Body.</p>")))


def _render(footer: Footer | None = None, **facts: str) -> str:
    return _builder(footer, **(URLS | facts)).render()


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

    def test_the_default_row_renders_copyright_and_both_links(self):
        """
        The *default* path, and the distinction the name has to carry.

        This asserts that a footer told nothing still renders the row built
        from the email's own facts — a statement about resolution, **not** a
        content mandate. pyHermes does not require an unsubscribe link or any
        other content: a caller who supplies their own ``LinkRow`` may drop
        either link, and ``TestTheLinkRow`` says so by name. What the region
        guarantees is that a *variant* will not silently drop the block the
        caller's content sits in, which is `REQUIRED_SLOTS`' actual job.
        """
        html = _render()
        assert "&copy;" in html and "2026" in html
        assert "Unsubscribe" in html and "View in browser" in html


class TestAnUnsetDefaultLinkIsLeftOut:
    """#258: a default link whose URL fact is unset rendered as ``href=""``."""

    def test_with_neither_url_the_row_is_the_copyright_alone(self):
        builder = _builder()
        html, text = builder.render(), builder.text()
        assert 'href=""' not in html
        assert "Unsubscribe" not in html and "View in browser" not in html
        assert "&copy; 2026 F" in html and "&nbsp;&middot;&nbsp;" not in html
        assert "Unsubscribe" not in text and "View in browser" not in text

    @pytest.mark.parametrize(
        ("fact", "kept", "dropped"),
        [
            ("unsubscribe_url", "Unsubscribe", "View in browser"),
            ("view_in_browser_url", "View in browser", "Unsubscribe"),
        ],
    )
    def test_with_one_url_only_that_link_renders(self, fact, kept, dropped):
        html = _builder(**{fact: "https://acme.test/x"}).render()
        assert (
            f'href="https://acme.test/x" style="color:#5B8A9A; text-decoration:underline;">{kept}'
            in html
        )
        assert dropped not in html
        assert 'href=""' not in html

    def test_an_explicit_row_is_still_taken_exactly_as_given(self):
        footer = Footer(link_row=LinkRow(links=[FooterLink("Portal", "")]))
        assert 'href=""' in _builder(footer).render()


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
            from pyhermes.builder import MinimalFooter  # noqa: F401


class TestTheLinkRow:
    """
    #100: the copyright/link row stops being a fixed structure.

    The trigger for making it an object is the one that made ``Card`` and
    ``TableRow`` objects — the row has a variable-length part, and variable
    length is what fields cannot express.
    """

    def test_none_resolves_to_todays_row(self):
        """
        The path most callers are on. ``link_row=None`` builds the default
        pair from the email's own facts and this footer's labels, which is
        what makes the whole change byte-identical for them — the goldens
        are the real gate, and this says the same thing at one email.
        """
        html = _render()
        assert "&copy; 2026 F" in html
        assert "Unsubscribe" in html and "View in browser" in html

    def test_the_label_fields_still_work_on_the_default_path(self):
        """#64's back-compat: the labels parameterise the default pair."""
        html = _render(Footer(unsubscribe_label="Opt out", view_in_browser_label="Read online"))
        assert "Opt out" in html and "Read online" in html

    def test_a_custom_row_renders_its_copy_and_every_link_in_order(self):
        html = _render(
            Footer(
                link_row=LinkRow(
                    copyright="2026 Acme — all rights reserved",
                    links=[
                        FooterLink("Privacy", "https://acme.test/privacy"),
                        FooterLink("Terms", "https://acme.test/terms"),
                    ],
                )
            )
        )
        assert "2026 Acme &#8212; all rights reserved" in html
        assert html.index("Privacy") < html.index("Terms")
        assert "&copy;" not in html, "a caller's own line replaces the default entirely"
        assert html.count("&nbsp;&middot;&nbsp;") == 2

    def test_the_copyright_is_plain_text_and_escaped(self):
        html = _render(Footer(link_row=LinkRow(copyright="Smith & Sons <not markup>")))
        assert "Smith &amp; Sons &lt;not markup&gt;" in html

    def test_a_caller_can_write_the_copyright_sign(self):
        """
        #148: the field is plain text, so the caller writes the character.
        """
        html = _render(Footer(link_row=LinkRow(copyright="© 2026 Acme")))
        assert "&#169; 2026 Acme" in html

    def test_the_two_paths_agree_about_a_non_ascii_character(self):
        """
        The defect was the asymmetry, not the escaping.

        The default has always emitted the symbol as a reference, because a
        bare ``©`` mis-decoded as latin-1 renders as ``Â©``. A caller's line
        went out as the raw character or, if they wrote the entity, as
        literal text — so the one field with a recorded decision about this
        applied it to exactly one of its two branches.
        """
        default = _render(Footer())
        supplied = _render(Footer(link_row=LinkRow(copyright="© 2026 F")))
        for html in (default, supplied):
            assert "©" not in html

    def test_every_non_ascii_character_travels_as_a_reference(self):
        """
        Not a special case for one symbol: an em dash mis-decoded is
        ``â€"`` and an umlaut ``Ã¼``, which is the same failure.
        """
        html = _render(Footer(link_row=LinkRow(copyright="Zürich — 2026")))
        assert "Z&#252;rich &#8212; 2026" in html

    def test_an_entity_the_caller_writes_is_still_literal_text(self):
        """
        The field stays plain text. #148 gave the caller a way to render the
        character, and deliberately did not turn the row into a markup
        surface — a sixth raw-HTML field would also have to answer #130's
        div rule, and this line renders inside a ``p``.
        """
        html = _render(Footer(link_row=LinkRow(copyright="&copy; 2026 Acme")))
        assert "&amp;copy; 2026 Acme" in html

    def test_an_empty_link_list_renders_a_link_free_row(self):
        """
        Valid, not a ``ValidationError`` — and no dangling separator after
        the copyright, which is the visible half of the behaviour.
        """
        html = _render(Footer(link_row=LinkRow(links=[])))
        assert "&copy; 2026 F" in html
        assert "&nbsp;&middot;&nbsp;" not in html
        assert "Unsubscribe" not in html

    def test_a_row_without_an_unsubscribe_link_is_allowed(self):
        """
        Named so the decision is visible rather than merely absent.

        The library does not decide what an email must say: it cannot know
        whether this is a commercial newsletter, an internal research note or
        a transactional receipt, and each answers that differently. What it
        still guarantees is narrower — a region *variant* may not silently
        drop what the caller supplied, which is a rule about structure.
        """
        html = _render(
            Footer(link_row=LinkRow(links=[FooterLink("Privacy", "https://acme.test/p")]))
        )
        assert "Unsubscribe" not in html
        assert "Privacy" in html

    def test_a_variant_still_may_not_drop_the_block(self):
        """The other side of that line, and it is unchanged by #100."""
        with pytest.raises(ValidationError, match="required slot"):
            type("SilentFooter", (Footer,), {"TEMPLATE_PATHS": {}})()

    def test_an_unsafe_url_is_still_rejected(self):
        """
        A *safety* rule, not a content one — the library has opinions about
        what a link may do, never about which links an email carries.
        """
        with pytest.raises(ValidationError, match="footer_link.url"):
            FooterLink("Click", "javascript:alert(1)")

    def test_a_link_label_is_required(self):
        with pytest.raises(ValidationError, match="footer_link.label"):
            FooterLink("", "https://acme.test")

    def test_the_list_must_hold_footer_links(self):
        with pytest.raises(ValidationError, match=r"link_row.links\[0\]"):
            LinkRow(links=[("Privacy", "https://acme.test")])  # type: ignore[list-item]

    def test_link_labels_and_urls_are_escaped(self):
        html = _render(
            Footer(link_row=LinkRow(links=[FooterLink("Terms & Co", "https://a.test/?x=1&y=2")]))
        )
        assert "Terms &amp; Co" in html
        assert "https://a.test/?x=1&amp;y=2" in html
