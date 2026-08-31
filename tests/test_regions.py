"""
The banner region — extraction, model, rendering, and the MinimalBanner variant.

Covers epic #38: ``email > header | body``. The byte-identity bar the epic
promises lives in ``tests/test_goldens.py``; this module covers the structure
that bar is silent about.
"""

import dataclasses
import re

import pytest

import svc.builder as builder_api
from svc.builder import (
    Banner,
    BannerPalette,
    BoxSurface,
    Email,
    EmailBuilder,
    EmptyHeader,
    Footer,
    Header,
    MinimalBanner,
    Rgba,
)
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.images import EmailImage
from svc.builder.models import EmailMetadata
from svc.builder.theming import DEFAULT_THEME

TEMPLATE_DIR = TemplateEngine().template_dir


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def _facts_for(region_cls: type) -> tuple[str, ...]:
    """The facts a region of this kind is handed, by its context name."""
    return {
        "header": EmailMetadata.HEADER_FACTS,
        "banner": EmailMetadata.BANNER_FACTS,
        "footer": EmailMetadata.FOOTER_FACTS,
    }[region_cls.CONTEXT_NAME]


def _theme_token(path: str):
    """Follow a ``BannerPalette.FALLBACKS`` path into the default theme."""
    layer, token = path.split(".")
    return getattr(getattr(DEFAULT_THEME, layer), token)


class TestTheBannerLeftTheSkeleton:
    """#33: the pure template split — the markup moved, the output did not."""

    @pytest.mark.parametrize("region", [Header, Banner, MinimalBanner, Footer])
    def test_the_region_templates_ship_in_the_package(self, region):
        for path in region.TEMPLATE_PATHS.values():
            assert (TEMPLATE_DIR / path).is_file()

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
        #89's point, still true after #95 moved the owner. Both banner
        variants used to carry their own copy of the strip, byte-identical
        apart from a marker comment — the drift-by-copy a shared template
        makes impossible.
        """
        carriers = [
            path.name
            for path in (TEMPLATE_DIR / "regions").glob("*.html")
            if "{{header_disclaimer}}" in path.read_text(encoding="utf-8")
        ]
        assert carriers == ["header-bar.html"]

    def test_exactly_one_region_owns_each_slot(self):
        """
        #95's structural claim. The strip lived in ``Banner.SLOTS`` between
        #89 and #95 — its own template, its own slot, someone else's class.
        Two regions declaring one slot would have the skeleton silently take
        whichever rendered last.
        """
        owners: dict[str, list[str]] = {}
        for region in (Header, Banner, Footer):
            for slot in region.SLOTS:
                owners.setdefault(slot, []).append(region.__name__)
        assert owners == {"header_bar": ["Header"], "banner": ["Banner"], "footer": ["Footer"]}

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

    @pytest.mark.parametrize(
        "region_name,facts",
        [
            ("header", EmailMetadata.HEADER_FACTS),
            ("banner", EmailMetadata.BANNER_FACTS),
            ("footer", EmailMetadata.FOOTER_FACTS),
        ],
    )
    def test_the_two_key_sets_are_disjoint(self, valid_metadata, region_name, facts):
        metadata = EmailMetadata(**valid_metadata)
        region = getattr(metadata, region_name)
        presentation = set(region.context({})) | set(region.theme_context(DEFAULT_THEME))
        assert presentation & set(facts) == set()

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
        empty = EmailMetadata(**valid_metadata, banner=region())
        set_ = EmailMetadata(**valid_metadata, department="Rates Strategy", banner=region())
        engine = TemplateEngine()
        without = empty.banner.render(engine, empty.banner_facts())
        with_ = set_.banner.render(engine, set_.banner_facts())
        # Counted rather than sniffed for a marker string: the department's
        # own styling is the meta bar's too (same type, colour and casing),
        # so an absent element is the only thing that distinguishes them.
        assert with_.count("<p ") == without.count("<p ") + 1
        assert "Rates Strategy" not in without

    def test_it_is_a_fact_the_banner_cannot_shadow(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, department="Rates Strategy")
        assert "department" in EmailMetadata.BANNER_FACTS
        assert metadata.banner_facts()["department"] == "Rates Strategy"

    def test_the_copy_is_escaped(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, department="Rates & Credit")
        html = metadata.banner.render(TemplateEngine(), metadata.banner_facts())
        assert "Rates &amp; Credit" in html


BANNER_TEMPLATES = ["regions/banner.html", "regions/banner-minimal.html"]


class TestTheBannerPaletteReachesTheMarkup:
    """
    #93: bounded colour deviation, wired through one resolved object.

    ``theming.py`` owns whether a ``BannerPalette`` is *valid*; this owns
    whether it *renders* — every role reaching its own site, an unset one
    reaching it identically, and the scrim's two emissions staying one
    source.
    """

    @staticmethod
    def _banner(palette=None, **banner_kwargs):
        metadata = EmailMetadata(
            email_subject="s",
            firm_name="Hermes Research",
            campaign_name="weekly",
            department="Rates Strategy",
            date_range="Week ending 24 August",
            issue_label="Issue 001",
            banner=Banner(
                background_image_url="https://cdn.test/bg.png",
                logo_url="https://cdn.test/logo.png",
                palette=palette,
                **banner_kwargs,
            ),
        )
        return metadata.banner.render_slots(TemplateEngine(), metadata.banner_facts())[
            "banner_html"
        ]

    @pytest.mark.parametrize("template", BANNER_TEMPLATES)
    def test_the_template_reads_the_palette_not_the_theme(self, template):
        """
        The bypass that would render correctly and be wrong: a template
        reading ``theme.text.on_dark`` again works for every banner that sets
        no palette, so nothing else in the suite notices, and the role is
        simply unreachable. Same grep, same reason, as #91's.
        """
        source = _template(template)
        assert "{{ theme." not in source, (
            f"{template} reads a theme token directly; every banner colour must "
            "come through 'banner_palette' or the override is unreachable."
        )

    @pytest.mark.parametrize("template", BANNER_TEMPLATES)
    def test_it_names_only_roles_the_palette_declares(self, template):
        """
        The other direction. ``StrictUndefined`` would catch a typo, but only
        for the variant actually rendered — and the two templates diverge.
        """
        named = set(re.findall(r"banner_palette\.([a-z_]+)", _template(template)))
        assert named <= set(BannerPalette.FALLBACKS), (
            f"{template} names {sorted(named - set(BannerPalette.FALLBACKS))}, "
            "which BannerPalette does not declare."
        )

    def test_every_declared_role_is_actually_drawn(self):
        """
        A role no template reads is a field a caller can set to no effect.
        The default banner is the exhaustive one; the minimal variant reads a
        subset, deliberately (it has no photograph, so no scrim and no
        legibility shadows).
        """
        drawn = set(re.findall(r"banner_palette\.([a-z_]+)", _template(BANNER_TEMPLATES[0])))
        assert drawn == set(BannerPalette.FALLBACKS)

    @pytest.mark.parametrize("role", ["band", "title", "subtitle", "meta", "accent"])
    def test_one_role_moves_and_nothing_else_does(self, role):
        """
        Stronger than "the override appears": the whole render must equal the
        default one with that role's token substituted. A change anywhere
        else — a colour that moved because two roles share a token by
        accident — fails here.
        """
        default = self._banner()
        override = "#123456"
        moved = self._banner(palette=BannerPalette(**{role: override}))
        fallback = _theme_token(BannerPalette.FALLBACKS[role])
        assert default.replace(fallback, override) == moved

    @pytest.mark.parametrize("role", ["title_shadow", "subtitle_shadow"])
    def test_a_shadow_role_moves_on_its_own(self, role):
        default = self._banner()
        override = Rgba("#123456", 0.5)
        moved = self._banner(palette=BannerPalette(**{role: override}))
        fallback = _theme_token(BannerPalette.FALLBACKS[role])
        assert default.replace(fallback.css, override.css) == moved

    def test_both_halves_of_a_custom_scrim_move_together(self):
        """
        The masthead emits the scrim twice — CSS ``rgba()`` for everyone,
        ``v:fill`` colour plus opacity for Outlook — and #46's whole lesson is
        that two sources drift. An override has to reach both, which is why
        the field is one ``Rgba`` and not a colour beside an alpha.
        """
        html = self._banner(palette=BannerPalette(scrim=Rgba("#CDEF01", 0.25)))
        assert "rgba(205,239,1,0.25)" in html
        assert 'color="#CDEF01" opacity="25%"' in html
        assert str(DEFAULT_THEME.shadow.scrim) not in html

    def test_an_unset_palette_renders_the_theme_byte_for_byte(self):
        assert self._banner() == self._banner(palette=BannerPalette())

    def test_it_does_not_reach_the_strip(self):
        """
        Scoped to the banner slot, not to the region. The strip at the top of
        the email renders on a surface the *theme* supplies, so it keeps the
        theme's tokens — and it becomes its own region in #87. Widening the
        palette to cover it would be "now every region gets a palette" one
        slot early.
        """
        metadata = EmailMetadata(
            email_subject="s",
            firm_name="f",
            campaign_name="c",
            header_disclaimer="disclaimer",
            banner=Banner(palette=BannerPalette(band="#123456", meta="#654321")),
        )
        strip = metadata.header.render_slots(TemplateEngine(), metadata.header_facts())[
            "header_bar_html"
        ]
        assert "#123456" not in strip and "#654321" not in strip
        assert DEFAULT_THEME.palette.header_bg in strip


class TestTheTwoTreacherousBlocksLeaveTheBannerAlone:
    """
    #46's lesson, checked rather than remembered.

    The dark-mode forcing block and the mobile ``@media`` rule carry their
    own copies of colours, so a themed email can render half-themed in the
    clients hardest to test. #93 asks the question for the banner: does
    either block reach it? Today neither does — the banner carries exactly
    one class, ``.mobile-title``, and the only rule naming it sets a
    ``font-size``. That is worth an assertion, because a later edit adding
    ``.surface`` to the masthead or a colour to ``.mobile-title`` would
    silently put a second source in front of ``BannerPalette``.
    """

    @staticmethod
    def _skeleton() -> str:
        from svc.builder import Email

        return Email({"email_subject": "s", "firm_name": "f", "campaign_name": "c"}).render()

    def test_the_banner_carries_one_class_and_it_is_size_only(self):
        used = {
            name
            for template in BANNER_TEMPLATES
            for match in re.findall(r'class="([^"]+)"', _template(template))
            for name in match.split()
        }
        assert used == {"mobile-title"}

        html = self._skeleton()
        rule = html[html.index(".mobile-title {") :]
        rule = rule[: rule.index("}")]
        assert "color" not in rule, f".mobile-title now sets a colour: {rule}"

    def test_no_colour_rule_targets_a_class_the_banner_uses(self):
        """
        Read off the skeleton's own CSS rather than hand-listed, so a new
        dark-mode selector is covered without anyone remembering to add it.
        """
        html = self._skeleton()
        style = html[html.index('<style type="text/css">') : html.index("</style>", 100)]
        coloured: set[str] = set()
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
            if "color:" in body:
                coloured.update(re.findall(r"\.([A-Za-z0-9_-]+)", selector))
        assert "mobile-title" not in coloured, (
            "a colour rule now targets the banner's only class; it would win "
            "over BannerPalette in exactly the clients hardest to test."
        )


class TestTheHeaderRegion:
    """
    #95: the strip stops being rendered by the banner and becomes a class.

    The region mechanism's own test. The strip already had its own template
    and its own slot after #89 — what #95 changes is the *owner*, so the
    headline assertion is that no rendered byte moved (the goldens), and
    everything here is about what the new owner adds.
    """

    @staticmethod
    def _strip(metadata: EmailMetadata) -> str:
        return metadata.header.render_slots(TemplateEngine(), metadata.header_facts())[
            "header_bar_html"
        ]

    def test_the_flat_path_still_renders_the_strip(self, valid_metadata):
        """
        Most callers never touch the region: they set the copy on the
        metadata and expect a band. That path did not change.
        """
        metadata = EmailMetadata(**valid_metadata, header_disclaimer="Not investment advice.")
        assert "Not investment advice." in self._strip(metadata)

    def test_unset_presentation_renders_the_themes_values(self, valid_metadata):
        metadata = EmailMetadata(**valid_metadata, header_disclaimer="d")
        strip = self._strip(metadata)
        assert DEFAULT_THEME.palette.header_bg in strip
        assert DEFAULT_THEME.text.on_dark_muted in strip
        assert "text-align:center;" in strip

    def test_the_colour_pair_moves_exactly_those_two_colours(self, valid_metadata):
        """
        Stronger than "the override appears": the whole strip must equal the
        default one with those two substitutions and nothing else.
        """
        plain = EmailMetadata(**valid_metadata, header_disclaimer="d")
        themed = EmailMetadata(
            **valid_metadata,
            header_disclaimer="d",
            header=Header(background_color="#EEF2F5", text_color="#1B1B1B"),
        )
        expected = (
            self._strip(plain)
            .replace(DEFAULT_THEME.palette.header_bg, "#EEF2F5")
            .replace(DEFAULT_THEME.text.on_dark_muted, "#1B1B1B")
        )
        assert expected == self._strip(themed)

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_alignment_reaches_the_markup(self, valid_metadata, align):
        metadata = EmailMetadata(
            **valid_metadata, header_disclaimer="d", header=Header(align=align)
        )
        assert f"text-align:{align};" in self._strip(metadata)

    def test_a_bad_alignment_raises_naming_the_field(self):
        with pytest.raises(ValidationError, match="header.align"):
            Header(align="middle")

    @pytest.mark.parametrize("field", ["background_color", "text_color"])
    def test_a_bad_hex_raises_naming_the_field(self, field):
        with pytest.raises(ValidationError, match=f"header.{field}"):
            Header(**{field: "slate"})

    def test_the_copy_is_raw_html_and_the_docstring_says_so(self, valid_metadata):
        """
        The contract #95 settled: kept raw for consistency with the other
        disclaimers, because escaping it would break every caller passing
        markup — so it is *stated* instead. A region whose text is raw HTML
        is a footgun, and the warning living only in a commit message is how
        it stays one.
        """
        metadata = EmailMetadata(**valid_metadata, header_disclaimer="<em>Not advice.</em>")
        assert "<em>Not advice.</em>" in self._strip(metadata)
        assert "raw HTML" in (Header.__doc__ or "")

    def test_the_email_api_carries_it(self, valid_metadata):
        chosen = Header(align="right")
        assert Email(valid_metadata, header=chosen).header is chosen
        assert Email(valid_metadata).set_header(chosen).header is chosen
        assert EmailBuilder().metadata(valid_metadata).header(chosen).build().header is chosen

    def test_the_builder_sequences_like_every_other_region(self, valid_metadata):
        with pytest.raises(RuntimeError, match="metadata"):
            EmailBuilder().header(Header())

    def test_the_old_masthead_signature_fails_loudly(self):
        """
        #90 freed the name for this class rather than aliasing it, so the
        one thing that must not happen is an old-style call quietly working.
        """
        with pytest.raises(TypeError):
            Header(logo_url="https://cdn.test/logo.png")  # type: ignore[call-arg]


class TestTheOmittedHeader:
    """
    #96: a region that fills no slot, and the decision beside it.

    The slot mechanism already supported true omission — an unfilled slot
    renders as the empty string, so the skeleton needs no conditional. What
    this adds is a name for it, and a recorded answer to the question the
    epic flagged: what an *empty default* header does.
    """

    def test_it_renders_nothing_at_all(self, valid_metadata):
        """
        Not "renders an empty band" — nothing. Asserted by absence of the
        markup rather than only by the golden, so the claim is legible in
        the suite rather than buried in a 300-line snapshot.
        """
        email = Email({**valid_metadata, "header_disclaimer": "Not advice."}, header=EmptyHeader())
        html = email.render()
        assert "HEADER: Disclaimer bar" not in html
        assert "Not advice." not in html
        assert (
            html.count("<tr>")
            == Email({**valid_metadata, "header_disclaimer": "Not advice."}).render().count("<tr>")
            - 1
        )

    def test_the_fact_survives_the_region_declining_it(self, valid_metadata):
        """
        The region decides whether to display the copy; it does not own it.
        An email that omits its strip still knows what the strip would have
        said, which is what makes swapping the region back a one-line change.
        """
        email = Email({**valid_metadata, "header_disclaimer": "Not advice."}, header=EmptyHeader())
        assert email.metadata.header_disclaimer == "Not advice."

    def test_an_empty_default_still_renders_the_band(self, valid_metadata):
        """
        #96's step-2 decision, pinned so it cannot drift silently.

        Auto-collapsing on empty copy was the alternative, and it was
        rejected on ownership rather than on taste: it would make the
        presence of the *box* depend on a fact the email owns rather than on
        the region, inverting the rule the layer rests on. ``Footer`` draws
        the same line — an empty ``disclaimer`` omits the fine-print line
        while the footer itself still renders.
        """
        html = Email(valid_metadata).render()
        assert "HEADER: Disclaimer bar" in html

    def test_it_keeps_the_headers_presentation_surface(self):
        """
        A subclass, so a caller can swap the variant in and out without
        rewriting the arguments — even though they render nothing today.
        """
        assert EmptyHeader(align="left").align == "left"
        with pytest.raises(ValidationError, match="header.align"):
            EmptyHeader(align="middle")

    def test_the_required_slot_asymmetry_is_deliberate(self):
        """
        ``Header`` declares no required slot and ``Footer`` declares one, and
        that is not a lower standard for the header. ``REQUIRED_SLOTS`` is a
        rule about *variants not dropping structure*, never about a caller
        supplying content — pyHermes does not require disclaimer language.
        The header's empty tuple says its whole box is optional; the
        footer's says a footer that renders nothing is a footer that failed.
        """
        assert Header.REQUIRED_SLOTS == ()
        assert Footer.REQUIRED_SLOTS == ("footer",)
        with pytest.raises(ValidationError, match="required slot"):
            type("EmptyFooter", (Footer,), {"TEMPLATE_PATHS": {}})()


class TestEveryRegionVariantHoldsTheContract:
    """
    The shared contract, checked by introspection rather than by a list.

    Every region and variant exported from ``svc.builder`` goes through this,
    so a variant added later is covered without anyone remembering to name
    it here — which is what #96 asked for and what a hand-written
    parametrize list cannot promise.
    """

    @staticmethod
    def _variants() -> list[type]:
        from svc.builder import regions as region_api

        return [
            obj
            for obj in vars(builder_api).values()
            if isinstance(obj, type)
            and issubclass(obj, region_api.Region)
            and obj is not region_api.Region
        ]

    def test_the_walk_finds_every_shipped_region(self):
        """A guard on the guard: an empty walk would pass everything below."""
        found = {cls.__name__ for cls in self._variants()}
        assert found >= {"Header", "EmptyHeader", "Banner", "MinimalBanner", "Footer"}

    def test_each_declares_only_slots_the_skeleton_names(self):
        skeleton = _template("base.html")
        for cls in self._variants():
            for slot in cls.SLOTS:
                assert f"{{{{ {slot}_html }}}}" in skeleton, f"{cls.__name__} names an unknown slot"

    def test_each_fills_only_slots_it_declares(self):
        for cls in self._variants():
            assert set(cls.TEMPLATE_PATHS) <= set(cls.SLOTS), (
                f"{cls.__name__} maps a template to a slot it does not declare"
            )

    def test_every_template_a_variant_names_ships(self):
        for cls in self._variants():
            for path in cls.TEMPLATE_PATHS.values():
                assert (TEMPLATE_DIR / path).is_file(), f"{cls.__name__} names a missing template"

    def test_each_constructs_and_renders_from_its_defaults(self):
        """
        Default-constructible is the contract ``EmailMetadata`` relies on:
        every region field is built by a ``default_factory`` calling the
        class with no arguments.
        """
        engine = TemplateEngine()
        for cls in self._variants():
            region = cls()
            slots = region.render_slots(engine, dict.fromkeys(_facts_for(cls), ""))
            assert set(slots) == {f"{slot}_html" for slot in cls.SLOTS}


class TestTheTwoBoxesShareOneSurface:
    """
    #99's parity, which is the requirement behind the whole footer epic: the
    header and footer are the email's two customisable outer boxes, and two
    boxes that behave alike should cost one API to learn.

    Parity is structural — both mix in :class:`BoxSurface` — and the tests
    below are what stop a third region redeclaring the three by hand, or the
    two drifting in *semantics* while the names still match.
    """

    BOXES = [Header, Footer]

    def test_both_inherit_the_surface_rather_than_redeclaring_it(self):
        for cls in self.BOXES:
            assert issubclass(cls, BoxSurface), (
                f"{cls.__name__} must mix in BoxSurface, not restate its fields — "
                "redeclaring them is how the two APIs drift apart."
            )

    def test_the_surface_is_the_same_three_fields_with_the_same_defaults(self):
        surface = {f.name: f.default for f in dataclasses.fields(BoxSurface)}
        assert surface == {"align": "center", "background_color": "", "text_color": ""}
        for cls in self.BOXES:
            own = {f.name: f.default for f in dataclasses.fields(cls)}
            assert own.items() >= surface.items(), (
                f"{cls.__name__} changed a shared field's default; parity is the "
                "semantics, not only the names."
            )

    @pytest.mark.parametrize("cls", BOXES)
    def test_each_validates_the_surface_the_same_way(self, cls):
        with pytest.raises(ValidationError, match=f"{cls.CONTEXT_NAME}.align"):
            cls(align="middle")
        with pytest.raises(ValidationError, match=f"{cls.CONTEXT_NAME}.background_color"):
            cls(background_color="beige")
        with pytest.raises(ValidationError, match=f"{cls.CONTEXT_NAME}.text_color"):
            cls(text_color="beige")

    @pytest.mark.parametrize("cls", BOXES)
    def test_each_resolves_the_surface_against_the_theme(self, cls):
        """
        The mechanism, not just the fields: an unset colour must arrive
        resolved rather than empty, and a set one must win — in both boxes,
        by the same hook.
        """
        inherited = cls().theme_context(DEFAULT_THEME)
        assert inherited and all(v for v in inherited.values())
        overridden = cls(background_color="#123456").theme_context(DEFAULT_THEME)
        assert "#123456" in overridden.values()

    def test_they_keep_their_own_fallback_tokens(self):
        """
        Shared fields, not shared tokens. The header's box sits on the dark
        band and the footer's on the wrapper — parity that forced one set of
        tokens on both would be parity as costume.
        """
        header = Header().theme_context(DEFAULT_THEME)
        footer = Footer().theme_context(DEFAULT_THEME)
        assert header["header_background"] == DEFAULT_THEME.palette.header_bg
        assert footer["footer_background"] == DEFAULT_THEME.palette.wrapper_bg
        assert header["header_background"] != footer["footer_background"]


class TestTheFooterBox:
    """#99: the footer's legal block gains the surface the header already had."""

    @staticmethod
    def _footer(**kwargs) -> str:
        metadata = EmailMetadata(
            email_subject="s",
            firm_name="Hermes Research",
            campaign_name="c",
            current_year="2026",
            unsubscribe_url="https://example.com/u",
            view_in_browser_url="https://example.com/v",
            footer=Footer(disclaimer="<p>Fine print.</p>", **kwargs),
        )
        return metadata.footer.render_slots(TemplateEngine(), metadata.footer_facts())[
            "footer_html"
        ]

    def test_unset_renders_the_themes_own_values(self):
        html = self._footer()
        assert DEFAULT_THEME.palette.wrapper_bg in html
        assert DEFAULT_THEME.text.fine_print in html
        assert DEFAULT_THEME.text.light in html
        assert "text-align:center" in html

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_alignment_reaches_every_row_of_the_box(self, align):
        """
        Disclaimer, copyright row and the sign-off image are one box, so one
        alignment moves all three — a box half-aligned would read as a bug.
        """
        html = self._footer(align=align, image="https://cdn.test/mark.png")
        assert html.count(f"text-align:{align}") == 3

    def test_the_background_moves_and_the_text_follows_it(self):
        html = self._footer(background_color="#1B2A38", text_color="#E8EEF2")
        assert "#1B2A38" in html and "#E8EEF2" in html
        assert DEFAULT_THEME.palette.wrapper_bg not in html
        assert DEFAULT_THEME.text.fine_print not in html
        assert DEFAULT_THEME.text.light not in html

    def test_text_color_collapses_both_type_tokens(self):
        """
        Documented coarseness, pinned. The theme keeps ``fine_print`` and
        ``light`` distinct; one override sets both, because a caller who has
        changed the ground needs *both* rows legible on it.
        """
        html = self._footer(text_color="#E8EEF2")
        assert html.count("color:#E8EEF2") == 2

    def test_links_keep_the_accent(self):
        """An explicit non-goal: the links are anchors, not box text."""
        html = self._footer(background_color="#1B2A38", text_color="#E8EEF2")
        assert DEFAULT_THEME.palette.accent in html

    def test_the_border_colour_resolves_the_same_way(self):
        assert DEFAULT_THEME.palette.rule in self._footer(border=True)
        assert "#654321" in self._footer(border=True, border_color="#654321")


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

    def test_the_banner_renders_into_the_skeleton(self, valid_metadata, png_bytes):
        """The alt is the probe, so the banner needs a logo for it to reach the markup.

        Before the empty-``src`` fix this passed with no ``logo_url`` at all, because
        the logo ``img`` rendered unconditionally — which is the defect, not the
        contract. Supplying one keeps the original claim and adds the alt chain.
        """
        logo = EmailImage.attached(png_bytes, alt="from the image")
        email = Email({**valid_metadata, "logo_url": logo, "logo_alt": "explicit"})
        html = email.render()
        assert "{{ banner_html }}" not in html
        assert 'alt="explicit"' in html

    def test_a_banner_without_a_logo_emits_no_image(self, valid_metadata):
        """An ``img`` with an empty ``src`` is a broken icon in every client.

        It shipped in nine of fourteen gallery fixtures until a real report was
        built against the public API, and the goldens pinned it the whole time.

        Scoped to ``img``. The ``v:fill`` in the ``[if mso]`` block carried the
        same defect and is handled by ``TestTheVmlFillSrcIsGated`` below.
        """
        html = Email(valid_metadata).render()
        images = re.findall(r"<img[^>]*>", html)
        assert not [tag for tag in images if 'src=""' in tag], (
            f"the banner emits a logo img with no source: {images}"
        )


class TestTheVmlFillSrcIsGated:
    """
    #150 — the Outlook half of the defect #78 fixed in the CSS half.

    **Not yet verified in a real Outlook client.** These tests pin what the
    builder *emits*; what the Word engine *draws* from it is the open
    question, and standing rule 3 says no screenshot here can close it. The
    claim being staged is narrow: only the attribute moves. The rect, its
    colour and its opacity are untouched, because the scrim is drawn over
    the flat band whether or not there is a photograph — in this half and in
    the CSS half alike.
    """

    def _fill(self, html: str) -> str:
        match = re.search(r"<v:fill[^>]*>", html)
        assert match, "the masthead should always draw a v:fill"
        return match.group(0)

    def test_no_backdrop_emits_no_src(self, valid_metadata):
        assert "src=" not in self._fill(Email(valid_metadata).render())

    def test_a_backdrop_still_emits_its_src(self, valid_metadata):
        banner = Banner(background_image_url="https://cdn.test/hero.png")
        fill = self._fill(Email(valid_metadata, banner=banner).render())
        assert 'src="https://cdn.test/hero.png"' in fill

    @pytest.mark.parametrize("backdrop", ["", "https://cdn.test/hero.png"])
    def test_the_scrim_survives_either_way(self, valid_metadata, backdrop):
        """
        The load-bearing half of the claim: gating the src must not stop
        Outlook drawing the band and its scrim. If a future edit gates the
        whole ``v:rect`` instead, this is what fails.
        """
        banner = Banner(background_image_url=backdrop)
        fill = self._fill(Email(valid_metadata, banner=banner).render())
        assert 'type="frame"' in fill
        assert "color=" in fill and "opacity=" in fill

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
