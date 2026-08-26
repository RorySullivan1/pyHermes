"""
The header region — extraction, model, rendering, and the MinimalHeader variant.

Covers epic #38: ``email > header | body``. The byte-identity bar the epic
promises lives in ``tests/test_goldens.py``; this module covers the structure
that bar is silent about.
"""

import dataclasses

import pytest

from svc.builder import Email, EmailBuilder, Header
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.images import EmailImage
from svc.builder.models import EmailMetadata

TEMPLATE_DIR = TemplateEngine().template_dir


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


class TestTheHeaderLeftTheSkeleton:
    """#33: the pure template split — the markup moved, the output did not."""

    def test_the_region_template_ships_in_the_package(self):
        assert (TEMPLATE_DIR / "regions" / "header.html").is_file()

    def test_base_html_keeps_only_the_hole(self):
        base = _template("base.html")
        assert "{{ header_html }}" in base
        for moved in ("HEADER: Disclaimer bar", "HEADER: Background image", "v:rect"):
            assert moved not in base, f"base.html still carries header markup: {moved!r}"

    def test_the_fragile_outlook_markup_moved_intact(self):
        header = _template("regions/header.html")
        for vml in ("<v:rect", "<v:fill", "<v:textbox", "</v:textbox>", "</v:rect>"):
            assert vml in header

    @pytest.mark.parametrize(
        "variable",
        [
            "header_disclaimer",
            "firm_name",
            "campaign_name",
            "date_range",
            "issue_label",
        ],
    )
    def test_the_skeleton_no_longer_names_a_header_only_variable(self, variable):
        """
        ``firm_name`` is the exception that proves the rule — the footer's
        copyright line still names it, which is why facts stay email-level.
        """
        base = _template("base.html")
        header = _template("regions/header.html")
        assert variable in header
        if variable != "firm_name":
            assert variable not in base

    def test_the_footer_deliberately_stayed(self):
        """Epic non-goal: the footer is the same kind of candidate, later."""
        base = _template("base.html")
        assert "FOOTER PART 1" in base and "FOOTER PART 2" in base


class TestTheHeaderModel:
    """#34: the masthead's presentation is a model of its own, validated early."""

    def test_it_is_exported_from_the_package(self):
        from svc.builder import Header as Exported

        assert Exported is Header

    @pytest.mark.parametrize("field", ["logo_url", "background_image_url"])
    def test_a_dangerous_url_is_rejected_at_construction(self, field):
        with pytest.raises(ValidationError, match=rf"header\.{field}"):
            Header(**{field: "javascript:alert(1)"})

    @pytest.mark.parametrize("value", [0, -1])
    def test_a_non_positive_logo_width_is_rejected(self, value):
        with pytest.raises(ValidationError, match=r"header\.logo_width"):
            Header(logo_width=value)

    def test_a_wrong_type_names_itself(self):
        with pytest.raises(ValidationError, match="URL string or an EmailImage"):
            Header(logo_url=42)  # type: ignore[arg-type]

    def test_an_email_image_carries_its_own_validation(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        assert Header(logo_url=image).images() == [image]

    def test_only_email_images_reach_the_manifest(self, png_bytes):
        """A hosted URL has no bytes to attach, so it is absent by design."""
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        header = Header(logo_url=image, background_image_url="https://cdn.test/bg.png")
        assert [a.content_id for a in header.assets()] == [image.content_id]

    def test_the_logo_alt_chain(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="from the image")
        assert Header().resolved_logo_alt("Acme") == "Acme"
        assert Header(logo_url=image).resolved_logo_alt("Acme") == "from the image"
        assert Header(logo_url=image, logo_alt="explicit").resolved_logo_alt("Acme") == "explicit"

    def test_the_logo_width_chain(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="a", width=64)
        assert Header().resolved_logo_width() == Header.DEFAULT_LOGO_WIDTH
        assert Header(logo_url=image).resolved_logo_width() == 64
        assert Header(logo_url=image, logo_width=200).resolved_logo_width() == 200


class TestFactsFlowDown:
    """
    Epic principle 1, made mechanical rather than remembered.
    """

    def test_the_email_owns_the_facts_the_header_renders(self):
        header = Header(logo_alt="a logo")
        context = header.context({"firm_name": "Acme Research"})
        assert context["firm_name"] == "Acme Research"

    def test_a_header_cannot_shadow_a_fact(self):
        """
        Nothing on ``Header`` collides with a fact today. The layering is what
        keeps that true when a later variant adds a field: facts go over the
        region's own keys, so the email wins by construction.
        """
        header = Header(logo_alt="a logo")
        assert header.context({"logo_alt": "the email insists"})["logo_alt"] == "the email insists"

    def test_the_two_key_sets_are_disjoint(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata)
        presentation = set(metadata.header.context({}))
        assert presentation & set(EmailMetadata.HEADER_FACTS) == set()

    def test_the_template_names_only_keys_the_context_supplies(self, valid_metadata):
        """StrictUndefined turns a missing key into a render failure."""
        metadata = EmailMetadata(**valid_metadata)
        html = metadata.header.render(TemplateEngine(), metadata.header_facts())
        assert valid_metadata["firm_name"] in html


class TestTheFlatKeywordsStillWork:
    """#34's back-compatibility bar: an email written before the split."""

    def test_they_build_the_header(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        metadata = EmailMetadata(
            **valid_metadata,
            logo_url=image,
            logo_alt="explicit",
            logo_width=128,
            header_bg_image_url="https://cdn.test/bg.png",
        )
        assert metadata.header == Header(
            logo_url=image,
            logo_alt="explicit",
            logo_width=128,
            background_image_url="https://cdn.test/bg.png",
        )

    def test_they_are_constructor_only(self, valid_metadata):
        """
        InitVars: they never become attributes, so the header stays the single
        owner and two emails differing only in masthead do not compare equal.
        """
        metadata = EmailMetadata(**valid_metadata, logo_alt="explicit")
        assert "logo_alt" not in vars(metadata)
        declared = {f.name for f in dataclasses.fields(EmailMetadata)}
        assert declared & {"logo_url", "logo_alt", "logo_width", "header_bg_image_url"} == set()

    def test_the_header_participates_in_equality(self, valid_metadata):
        plain = EmailMetadata(**valid_metadata)
        logoed = EmailMetadata(**valid_metadata, logo_alt="explicit")
        assert plain != logoed

    def test_both_spellings_at_once_is_an_error(self, valid_metadata):
        with pytest.raises(ValidationError, match="one or the other"):
            EmailMetadata(
                **valid_metadata,
                header=Header(logo_alt="from the header"),
                logo_alt="from the keyword",
            )

    def test_an_explicit_header_alone_is_fine(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, header=Header(logo_alt="explicit"))
        assert metadata.header.logo_alt == "explicit"


class TestTheEmailApi:
    """#35: selecting a region is an argument, not a template fork."""

    def test_the_default_header_comes_from_the_metadata(self, valid_metadata):
        email = Email({**valid_metadata, "logo_alt": "explicit"})
        assert email.header is email.metadata.header

    def test_an_explicit_header_wins(self, valid_metadata):
        chosen = Header(logo_alt="chosen")
        email = Email(valid_metadata, header=chosen)
        assert email.header is chosen

    def test_the_builder_sets_it(self, valid_metadata):
        chosen = Header(logo_alt="chosen")
        email = EmailBuilder().metadata(valid_metadata).header(chosen).build()
        assert email.header is chosen

    def test_the_builder_keeps_its_sequencing_rule(self):
        with pytest.raises(RuntimeError, match="metadata"):
            EmailBuilder().header(Header())

    def test_the_header_renders_into_the_skeleton(self, valid_metadata):
        email = Email({**valid_metadata, "logo_alt": "explicit"})
        html = email.render()
        assert "{{ header_html }}" not in html
        assert 'alt="explicit"' in html

    def test_a_cid_logo_is_attached_exactly_once(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        email = Email(valid_metadata, header=Header(logo_url=image, background_image_url=image))
        assert [a.content_id for a in email.assets()] == [image.content_id]
        # Referenced four times in the markup — logo and background, each once
        # for Outlook and once for everyone else — attached exactly once.
        assert email.render().count(f"cid:{image.content_id}") == 4
