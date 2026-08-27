"""
The banner region — extraction, model, rendering, and the MinimalBanner variant.

Covers epic #38: ``email > header | body``. The byte-identity bar the epic
promises lives in ``tests/test_goldens.py``; this module covers the structure
that bar is silent about.
"""

import dataclasses

import pytest

from svc.builder import Banner, Email, EmailBuilder, MinimalBanner
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.images import EmailImage
from svc.builder.models import EmailMetadata

TEMPLATE_DIR = TemplateEngine().template_dir


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


class TestTheBannerLeftTheSkeleton:
    """#33: the pure template split — the markup moved, the output did not."""

    @pytest.mark.parametrize("slot", ["header_bar", "banner"])
    def test_the_region_templates_ship_in_the_package(self, slot):
        assert (TEMPLATE_DIR / Banner.TEMPLATE_PATHS[slot]).is_file()

    def test_base_html_keeps_only_the_holes(self):
        base = _template("base.html")
        for hole in ("{{ header_bar_html }}", "{{ banner_html }}"):
            assert hole in base
        for moved in ("HEADER: Disclaimer bar", "HEADER: Background image", "v:rect"):
            assert moved not in base, f"base.html still carries banner markup: {moved!r}"

    def test_the_fragile_outlook_markup_moved_intact(self):
        banner = _template("regions/banner.html")
        for vml in ("<v:rect", "<v:fill", "<v:textbox", "</v:textbox>", "</v:rect>"):
            assert vml in banner

    def test_the_strip_exists_in_exactly_one_template(self):
        """
        #89's point. Both variants used to carry their own copy of the strip,
        byte-identical apart from a marker comment — the drift-by-copy a
        shared template makes impossible. ``MinimalBanner`` composes
        ``Banner``'s path rather than restating it.
        """
        carriers = [
            path.name
            for path in (TEMPLATE_DIR / "regions").glob("*.html")
            if "{{header_disclaimer}}" in path.read_text(encoding="utf-8")
        ]
        assert carriers == ["header-bar.html"]
        assert MinimalBanner.TEMPLATE_PATHS["header_bar"] == Banner.TEMPLATE_PATHS["header_bar"]

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
        ``firm_name`` is the exception that proves the rule: it is a *fact*,
        so the footer's copyright line names it too — which is why facts stay
        email-level rather than moving onto the region that displays them.
        """
        base = _template("base.html")
        region = _template("regions/header-bar.html") + _template("regions/banner.html")
        assert variable in region
        assert variable not in base
        if variable == "firm_name":
            assert variable in _template("regions/footer.html")


class TestTheBannerModel:
    """#34: the masthead's presentation is a model of its own, validated early."""

    def test_it_is_exported_from_the_package(self):
        from svc.builder import Banner as Exported

        assert Exported is Banner

    @pytest.mark.parametrize("field", ["logo_url", "background_image_url"])
    def test_a_dangerous_url_is_rejected_at_construction(self, field):
        with pytest.raises(ValidationError, match=rf"banner\.{field}"):
            Banner(**{field: "javascript:alert(1)"})

    @pytest.mark.parametrize("value", [0, -1])
    def test_a_non_positive_logo_width_is_rejected(self, value):
        with pytest.raises(ValidationError, match=r"banner\.logo_width"):
            Banner(logo_width=value)

    def test_a_wrong_type_names_itself(self):
        with pytest.raises(ValidationError, match="URL string or an EmailImage"):
            Banner(logo_url=42)  # type: ignore[arg-type]

    def test_an_email_image_carries_its_own_validation(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        assert Banner(logo_url=image).images() == [image]

    def test_only_email_images_reach_the_manifest(self, png_bytes):
        """A hosted URL has no bytes to attach, so it is absent by design."""
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        banner = Banner(logo_url=image, background_image_url="https://cdn.test/bg.png")
        assert [a.content_id for a in banner.assets()] == [image.content_id]

    def test_the_logo_alt_chain(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="from the image")
        assert Banner().resolved_logo_alt("Acme") == "Acme"
        assert Banner(logo_url=image).resolved_logo_alt("Acme") == "from the image"
        assert Banner(logo_url=image, logo_alt="explicit").resolved_logo_alt("Acme") == "explicit"

    def test_the_logo_width_chain(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="a", width=64)
        assert Banner().resolved_logo_width() == Banner.DEFAULT_LOGO_WIDTH
        assert Banner(logo_url=image).resolved_logo_width() == 64
        assert Banner(logo_url=image, logo_width=200).resolved_logo_width() == 200

    def test_the_title_chain(self):
        assert Banner().resolved_title("Acme") == "Acme"
        assert Banner(title="Q3 Outlook").resolved_title("Acme") == "Q3 Outlook"

    def test_the_subtitle_chain(self):
        assert Banner().resolved_subtitle("weekly") == "weekly"
        assert Banner(subtitle="What the curve is pricing").resolved_subtitle("weekly") == (
            "What the curve is pricing"
        )


class TestFactsFlowDown:
    """
    Epic principle 1, made mechanical rather than remembered.
    """

    def test_the_email_owns_the_facts_the_banner_renders(self):
        banner = Banner(logo_alt="a logo")
        context = banner.context({"firm_name": "Acme Research"})
        assert context["firm_name"] == "Acme Research"

    def test_a_banner_cannot_shadow_a_fact(self):
        """
        Nothing on ``Banner`` collides with a fact today. The layering is what
        keeps that true when a later variant adds a field: facts go over the
        region's own keys, so the email wins by construction.
        """
        banner = Banner(logo_alt="a logo")
        assert banner.context({"logo_alt": "the email insists"})["logo_alt"] == "the email insists"

    def test_the_two_key_sets_are_disjoint(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata)
        presentation = set(metadata.banner.context({}))
        assert presentation & set(EmailMetadata.BANNER_FACTS) == set()

    def test_the_template_names_only_keys_the_context_supplies(self, valid_metadata):
        """StrictUndefined turns a missing key into a render failure."""
        metadata = EmailMetadata(**valid_metadata)
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert valid_metadata["firm_name"] in html


class TestTheHeadlineIsPresentation:
    """
    #91: the masthead stops being forced to say who sent the email.

    The chain resolves into a key of its *own* rather than in place, because
    its fallbacks are facts and facts land last in ``Region.context()``.
    Resolving ``title`` into ``firm_name`` would be a region shadowing a
    fact — the one thing the layering exists to prevent.
    """

    def test_an_explicit_title_reaches_the_masthead(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, banner=Banner(title="Q3 Outlook"))
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert "Q3 Outlook" in html

    def test_an_unset_title_falls_back_to_the_firm(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata)
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert valid_metadata["firm_name"] in html

    def test_the_fact_still_reaches_the_rest_of_the_email(self, valid_metadata):
        """
        The acceptance criterion that says the escape hatch is not a lie: a
        banner reading "Q3 Outlook" must not change who the copyright line
        says sent it.
        """
        renamed = Email(valid_metadata, banner=Banner(title="Q3 Outlook")).render()
        assert renamed.count(valid_metadata["firm_name"]) >= 1
        plain = Email(valid_metadata).render()
        # One occurrence moved (the masthead); every other one stayed.
        assert renamed.count(valid_metadata["firm_name"]) == (
            plain.count(valid_metadata["firm_name"]) - 1
        )

    def test_the_copy_is_escaped(self, valid_metadata):
        """Free-form means arbitrary copy, not markup."""
        metadata = EmailMetadata(**valid_metadata, banner=Banner(title="Rates & Credit <b>"))
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert "Rates &amp; Credit &lt;b&gt;" in html

    @pytest.mark.parametrize("template", ["regions/banner.html", "regions/banner-minimal.html"])
    @pytest.mark.parametrize("fact", ["firm_name", "campaign_name"])
    def test_the_template_reads_the_resolved_key_not_the_fact(self, template, fact):
        """
        The chain must not be bypassable. Reading ``{{ firm_name }}`` again
        would render correctly for every email that never sets a title, so
        nothing else in the suite would notice — the field would simply be
        unreachable. Hence a grep, on the template rather than the render.
        """
        source = _template(template)
        assert f"{{{{ {fact} " not in source, (
            f"{template} reads the fact '{fact}' directly; the banner's headline "
            "must come from 'banner_title' / 'banner_subtitle' or Banner.title "
            "becomes unreachable."
        )


class TestTheDepartmentLine:
    """
    #92: the desk beneath the firm — a fact, and an optional one.

    ``department`` is on ``EmailMetadata`` rather than on ``Banner`` because
    it is *who the email is from*, the same kind of truth as ``firm_name``.
    Putting it on the region would let two renders of one email disagree
    about its sender.
    """

    @pytest.mark.parametrize("region", [Banner, MinimalBanner])
    def test_it_renders_when_set(self, valid_metadata, region):
        metadata = EmailMetadata(**valid_metadata, department="Rates Strategy", banner=region())
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert "Rates Strategy" in html

    @pytest.mark.parametrize("region", [Banner, MinimalBanner])
    def test_absence_collapses_rather_than_blanks(self, valid_metadata, region):
        """
        Guard the element, not its text. An empty ``department`` must leave
        no ``<p>`` behind and reserve no height — which is what makes every
        fixture that does not opt in byte-identical, and is asserted here by
        string absence rather than by eyeball.
        """
        metadata = EmailMetadata(**valid_metadata, banner=region())
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert "text-transform:uppercase" in html, "the date/issue bar should still be here"
        assert "masthead_department_top" not in html
        # The department's <p> is the only one carrying a top margin.
        assert "margin:6px 0 0 0" not in html

    def test_it_is_a_fact_the_banner_cannot_shadow(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, department="Rates Strategy")
        assert "department" in EmailMetadata.BANNER_FACTS
        assert metadata.banner_facts()["department"] == "Rates Strategy"

    def test_the_copy_is_escaped(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, department="Rates & Credit")
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert "Rates &amp; Credit" in html


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
        assert metadata.banner == Banner(
            logo_url=image,
            logo_alt="explicit",
            logo_width=128,
            background_image_url="https://cdn.test/bg.png",
        )

    def test_they_are_constructor_only(self, valid_metadata):
        """
        InitVars: they never become attributes, so the banner stays the single
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
                banner=Banner(logo_alt="from the banner"),
                logo_alt="from the keyword",
            )

    def test_an_explicit_banner_alone_is_fine(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, banner=Banner(logo_alt="explicit"))
        assert metadata.banner.logo_alt == "explicit"

    def test_both_spellings_render_the_same_bytes(self, valid_metadata, png_bytes):
        """
        The guarantee ``kitchen_sink``'s golden used to carry.

        Until #91 the broadest fixture built its masthead the flat way, so
        the flat path was pinned byte-for-byte by a golden. #91 gave the
        banner two fields with no flat spelling — the keywords exist for a
        pre-split call site, and a field added after the split has none — so
        the fixture moved to an explicit ``Banner`` and that coverage had to
        go somewhere. Here is stronger than there: a golden pins each
        spelling's own bytes and would not notice the two diverging, whereas
        this asserts they *converge*, which is the actual promise.
        """
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        fields = {
            "logo_url": image,
            "logo_alt": "explicit",
            "logo_width": 128,
            "header_bg_image_url": "https://cdn.test/bg.png",
        }
        flat = Email({**valid_metadata, **fields})
        explicit = Email(
            valid_metadata,
            banner=Banner(
                logo_url=image,
                logo_alt="explicit",
                logo_width=128,
                background_image_url="https://cdn.test/bg.png",
            ),
        )
        assert flat.render() == explicit.render()


class TestTheEmailApi:
    """#35: selecting a region is an argument, not a template fork."""

    def test_the_default_banner_comes_from_the_metadata(self, valid_metadata):
        email = Email({**valid_metadata, "logo_alt": "explicit"})
        assert email.banner is email.metadata.banner

    def test_an_explicit_banner_wins(self, valid_metadata):
        chosen = Banner(logo_alt="chosen")
        email = Email(valid_metadata, banner=chosen)
        assert email.banner is chosen

    def test_the_builder_sets_it(self, valid_metadata):
        chosen = Banner(logo_alt="chosen")
        email = EmailBuilder().metadata(valid_metadata).banner(chosen).build()
        assert email.banner is chosen

    def test_the_builder_keeps_its_sequencing_rule(self):
        with pytest.raises(RuntimeError, match="metadata"):
            EmailBuilder().banner(Banner())

    def test_the_banner_renders_into_the_skeleton(self, valid_metadata):
        email = Email({**valid_metadata, "logo_alt": "explicit"})
        html = email.render()
        assert "{{ banner_html }}" not in html
        assert 'alt="explicit"' in html

    def test_a_cid_logo_is_attached_exactly_once(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        email = Email(valid_metadata, banner=Banner(logo_url=image, background_image_url=image))
        assert [a.content_id for a in email.assets()] == [image.content_id]
        # Referenced four times in the markup — logo and background, each once
        # for Outlook and once for everyone else — attached exactly once.
        assert email.render().count(f"cid:{image.content_id}") == 4


class TestTheMinimalBannerVariant:
    """#36: a region abstraction with one implementation is a refactor in a hat."""

    def test_it_is_exported_from_the_package(self):
        from svc.builder import MinimalBanner as Exported

        assert Exported is MinimalBanner

    def test_it_renders_its_own_template(self):
        assert MinimalBanner.TEMPLATE_PATHS != Banner.TEMPLATE_PATHS
        assert (TEMPLATE_DIR / MinimalBanner.TEMPLATE_PATHS["banner"]).is_file()

    def test_a_background_image_is_rejected_rather_than_ignored(self):
        with pytest.raises(ValidationError, match="not supported by MinimalBanner"):
            MinimalBanner(background_image_url="https://cdn.test/bg.png")

    def test_it_still_validates_what_the_base_banner_does(self):
        with pytest.raises(ValidationError, match=r"banner\.logo_url"):
            MinimalBanner(logo_url="javascript:alert(1)")

    def test_the_fragile_outlook_markup_is_gone(self, valid_metadata):
        html = Email(valid_metadata, banner=MinimalBanner()).render()
        for vml in ("<v:rect", "<v:fill", "<v:textbox"):
            assert vml not in html
        assert "background-image" not in html

    def test_the_email_level_facts_still_flow_down(self):
        facts = {
            "email_subject": "Subject",
            "firm_name": "Acme Research",
            "campaign_name": "weekly-wrap",
            "date_range": "Week ending 24 August",
            "issue_label": "Issue 002",
            "header_disclaimer": "Not investment advice.",
        }
        html = Email(facts, banner=MinimalBanner()).render()
        for value in facts.values():
            if value != "Subject":
                assert value in html

    def test_the_logo_chains_are_inherited(self, png_bytes):
        image = EmailImage.attached(png_bytes, alt="from the image", width=64)
        banner = MinimalBanner(logo_url=image)
        assert banner.resolved_logo_alt("Acme") == "from the image"
        assert banner.resolved_logo_width() == 64

    def test_a_cid_logo_reaches_the_manifest_exactly_once(self, valid_metadata, png_bytes):
        image = EmailImage.attached(png_bytes, alt="Firm logo")
        email = Email(valid_metadata, banner=MinimalBanner(logo_url=image))
        assert [a.content_id for a in email.assets()] == [image.content_id]
        # One <img>, not the default header's mso/non-mso pair.
        assert email.render().count(f"cid:{image.content_id}") == 1

    def test_the_mobile_rules_still_apply_to_it(self, valid_metadata):
        """The variant is a region, not a second skeleton — base.html's CSS is shared."""
        html = Email(valid_metadata, banner=MinimalBanner()).render()
        assert 'class="mobile-title"' in html
        assert ".kpi-cell" in html

    def test_the_default_banner_is_undisturbed(self, valid_metadata):
        """The variant adds; it does not change what an existing email renders."""
        default = Email(valid_metadata).render()
        assert "<v:rect" in default
