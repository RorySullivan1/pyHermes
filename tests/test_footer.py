"""
The footer region — extraction, model, rendering, and the MinimalFooter variant.

Covers epic #55: ``email > header | body | footer``. The byte-identity bar the
epic promises lives in ``tests/test_goldens.py``; this module covers the
structure that bar is silent about, and the compliance floor no golden can
express (a *variant* that dropped the unsubscribe link would have its own
golden, and the golden would happily pin the omission).
"""

import dataclasses
from typing import ClassVar

import pytest

from qa.fixtures._png import solid_png
from svc.builder import (
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    MinimalFooter,
    TextBlock,
)
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import SizeError, ValidationError
from svc.builder.images import EmailImage
from svc.builder.models import EmailMetadata
from svc.config import config_override

TEMPLATE_DIR = TemplateEngine().template_dir


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


class TestTheFooterLeftTheSkeleton:
    """#63: the pure template split — the markup moved, the output did not."""

    @pytest.mark.parametrize("name", ["footer-contact.html", "footer-legal.html"])
    def test_the_region_templates_ship_in_the_package(self, name):
        assert (TEMPLATE_DIR / "regions" / name).is_file()

    def test_base_html_keeps_only_the_holes(self):
        base = _template("base.html")
        assert "{{ footer_contact_html }}" in base
        assert "{{ footer_legal_html }}" in base
        for moved in ("FOOTER PART 1", "FOOTER PART 2", "v:roundrect", "footer_disclaimer"):
            assert moved not in base, f"base.html still carries footer markup: {moved!r}"

    def test_the_split_is_where_the_dom_splits(self):
        """
        The reason there are two templates rather than one: the contact card
        is a ``<tr>`` inside the body table and the legal block is a sibling
        table below it. The tags the skeleton keeps between the two holes are
        the ones a single fragment would have had to close.
        """
        base = _template("base.html")
        between = base.split("{{ footer_contact_html }}")[1].split("{{ footer_legal_html }}")[0]
        assert "</table>" in between and "/Main container" in between

        contact = _template("regions/footer-contact.html")
        legal = _template("regions/footer-legal.html")
        assert contact.lstrip().startswith("<!--") and "<tr>" in contact
        assert "<table" in legal and "<tr>" not in legal.split("<table", 1)[0]

    def test_the_fragile_outlook_markup_moved_intact(self):
        """
        The dual emission — ``v:roundrect`` for Outlook, an anchor for
        everyone else — is the footer's equivalent of the header's VML hero,
        and the most diff-sensitive markup in the move.
        """
        contact = _template("regions/footer-contact.html")
        for vml in ("<!--[if mso]>", "<v:roundrect", "</v:roundrect>", "<![endif]-->"):
            assert vml in contact
        assert "<!--[if !mso]><!-->" in contact and "<!--<![endif]-->" in contact

    def test_no_vml_leaked_into_the_legal_block(self):
        assert "v:" not in _template("regions/footer-legal.html")

    def test_the_escaping_split_survived_the_move(self):
        """
        ``footer_disclaimer`` is an HTML field and stays raw; every other
        footer variable keeps its ``escape_html`` filter. A move that
        silently escaped the disclaimer would render callers' markup as text.
        """
        legal = _template("regions/footer-legal.html")
        assert "{{footer_disclaimer}}" in legal
        contact = _template("regions/footer-contact.html")
        for escaped in (
            "contact_heading",
            "contact_description",
            "contact_url",
            "contact_cta_label",
        ):
            assert f"{{{{ {escaped} | escape_html }}}}" in contact
        for escaped in ("current_year", "firm_name", "unsubscribe_label", "unsubscribe_url"):
            assert f"{{{{ {escaped} | escape_html }}}}" in legal


class TestTheFooterModel:
    """#64: the footer's wording is a model of its own, validated early."""

    def test_it_is_exported_from_the_package(self):
        from svc.builder import Footer as Exported

        assert Exported is Footer

    @pytest.mark.parametrize(
        ("field", "default"),
        [
            ("contact_heading", "Questions or feedback?"),
            ("contact_cta_label", "Contact Us"),
            ("unsubscribe_label", "Unsubscribe"),
            ("view_in_browser_label", "View in browser"),
            ("contact_description", ""),
        ],
    )
    def test_defaults_reproduce_the_hardcoded_copy(self, field, default):
        assert getattr(Footer(), field) == default

    def test_the_facts_are_absent_from_its_constructor(self):
        """
        The ownership rule, from the region's side: a ``Footer`` cannot carry
        a competing ``firm_name`` or unsubscribe URL, because it has nowhere
        to put one.
        """
        declared = {f.name for f in dataclasses.fields(Footer)}
        assert declared.isdisjoint(EmailMetadata.FOOTER_FACTS)
        for fact in EmailMetadata.FOOTER_FACTS:
            with pytest.raises(TypeError):
                Footer(**{fact: "smuggled"})

    def test_the_two_key_sets_are_disjoint(self):
        """
        What makes ``{**presentation, **facts}`` safe rather than lucky. If
        the sets ever overlap, the layering silently starts *resolving* a
        collision instead of never having one.
        """
        presentation = set(Footer().context({}))
        assert presentation.isdisjoint(EmailMetadata.FOOTER_FACTS)

    def test_a_fact_wins_over_a_presentation_key_of_the_same_name(self):
        ctx = Footer().context({"contact_cta_label": "FACT"})
        assert ctx["contact_cta_label"] == "FACT"


class TestTheFlatKeywordsStillWork:
    """#64: the pre-split spelling builds the region for you."""

    @pytest.mark.parametrize(
        "field",
        [
            "contact_heading",
            "contact_description",
            "contact_cta_label",
            "unsubscribe_label",
            "view_in_browser_label",
        ],
    )
    def test_a_flat_keyword_lands_on_the_footer(self, field):
        metadata = EmailMetadata(**{field: "FLAT"})
        assert getattr(metadata.footer, field) == "FLAT"

    @pytest.mark.parametrize(
        "field",
        [
            "contact_heading",
            "contact_description",
            "contact_cta_label",
            "unsubscribe_label",
            "view_in_browser_label",
        ],
    )
    def test_a_flat_keyword_never_becomes_an_attribute(self, field):
        """
        InitVars leave a class attribute behind, so ``hasattr`` says little;
        what matters is that no per-instance state shadows the region.
        """
        assert field not in vars(EmailMetadata(contact_heading="FLAT"))

    def test_a_flat_keyword_is_absent_from_fields_repr_and_equality(self):
        declared = {f.name for f in dataclasses.fields(EmailMetadata)}
        assert "contact_cta_label" not in declared
        assert EmailMetadata(contact_cta_label="A") != EmailMetadata(contact_cta_label="B")

    def test_flat_and_explicit_together_is_an_error(self):
        with pytest.raises(ValidationError, match=r"flat footer field\(s\)"):
            EmailMetadata(footer=Footer(contact_cta_label="A"), contact_cta_label="B")

    def test_the_two_regions_hydrate_independently(self):
        metadata = EmailMetadata(logo_url="https://x.test/l.png", contact_cta_label="Write in")
        assert metadata.header.logo_url == "https://x.test/l.png"
        assert metadata.footer.contact_cta_label == "Write in"


class TestTheEmailApi:
    """#65: selecting a footer is an argument, on the header's terms."""

    def _metadata(self, **extra):
        return {
            "email_subject": "S",
            "firm_name": "F",
            "campaign_name": "c",
            "contact_url": "https://x.test/c",
            **extra,
        }

    def test_the_constructor_argument_wins_over_the_metadata(self):
        email = Email(self._metadata(), footer=Footer(contact_cta_label="ARGUMENT"))
        assert email.footer.contact_cta_label == "ARGUMENT"
        assert "ARGUMENT" in email.render()

    def test_omitting_it_uses_the_metadata_footer(self):
        metadata = EmailMetadata(**self._metadata(contact_cta_label="FLAT"))
        assert Email(metadata).footer is metadata.footer

    def test_the_accessor_is_read_only(self):
        email = Email(self._metadata())
        with pytest.raises(AttributeError):
            email.footer = Footer()  # type: ignore[misc]

    def test_set_footer_swaps_it_and_chains(self):
        email = Email(self._metadata())
        assert email.set_footer(Footer(contact_cta_label="SWAPPED")) is email
        assert "SWAPPED" in email.render()

    def test_the_builder_sets_it(self):
        html = (
            EmailBuilder()
            .metadata(self._metadata())
            .footer(Footer(contact_cta_label="FLUENT"))
            .section(FullWidth(content=TextBlock("<p>body</p>")))
            .render()
        )
        assert "FLUENT" in html

    def test_the_builder_rejects_it_before_metadata(self):
        with pytest.raises(RuntimeError, match="Call .metadata"):
            EmailBuilder().footer(Footer())

    def test_the_default_and_explicit_paths_render_identically(self):
        """
        #65's "one render path, not two": the default is a
        default-constructed region, not a legacy inline branch.
        """
        flat = Email(self._metadata(contact_cta_label="SAME")).render()
        explicit = Email(self._metadata(), footer=Footer(contact_cta_label="SAME")).render()
        assert flat == explicit


@dataclasses.dataclass
class _SignedFooter(Footer):
    """
    A hypothetical variant that carries bytes.

    No shipped footer has an image, which is exactly why the protocol slot
    has to be exercised: the failure it prevents — a region whose bytes never
    reach the manifest and whose ``cid:`` reference renders broken — cannot
    show up in the gallery until someone writes this class for real.
    """

    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("signature_url",)

    signature_url: str | EmailImage = ""


class TestTheFooterFeedsTheManifest:
    """#65: a region's images reach ``Email.assets()`` or they reach nobody."""

    def _email(self, footer):
        return Email(
            {
                "email_subject": "S",
                "firm_name": "F",
                "campaign_name": "c",
                "contact_url": "https://x.test/c",
            },
            footer=footer,
        )

    def test_an_image_bearing_footer_reaches_assets(self):
        image = EmailImage.attached(solid_png(8, 8, (10, 20, 30)), alt="Signature", width=40)
        email = self._email(_SignedFooter(signature_url=image))
        assert [a.content_id for a in email.assets()] == [image.asset.content_id]
        assert image in email.images()

    def test_the_default_footer_contributes_nothing(self):
        assert self._email(Footer()).assets() == []

    def test_a_dangerous_url_on_a_footer_image_field_names_the_footer(self):
        """The base's validation generalised: the message says where it lives."""
        with pytest.raises(ValidationError, match=r"footer\.signature_url"):
            _SignedFooter(signature_url="javascript:alert(1)")

    def test_a_non_url_non_image_is_rejected(self):
        with pytest.raises(ValidationError, match=r"footer\.signature_url"):
            _SignedFooter(signature_url=object())  # type: ignore[arg-type]


class TestTheFooterIsInsideTheSizeBudget:
    """#65: composition must not open a seam where footer bytes escape."""

    def _build(self, **extra):
        return Email(
            {
                "email_subject": "S",
                "firm_name": "F",
                "campaign_name": "c",
                "contact_url": "https://x.test/c",
                **extra,
            }
        )

    def test_footer_bytes_count_against_the_limit(self):
        baseline_kb = len(self._build().render().encode("utf-8")) / 1024
        # A ceiling the lean email clears and the heavy footer does not, so
        # the only thing under test is whether the footer's bytes are counted.
        with config_override(
            size_limit_kb=baseline_kb + 1,
            size_warn_kb=baseline_kb,
            inline_image_limit_kb=1,
        ):
            self._build().render()
            with pytest.raises(SizeError):
                self._build(contact_description="x" * 4096).render()


def _public_footers() -> list[type[Footer]]:
    """Every ``Footer`` the package exports, found by introspection."""
    import svc.builder as builder_api

    return sorted(
        (
            obj
            for name in builder_api.__all__
            if isinstance(obj := getattr(builder_api, name), type) and issubclass(obj, Footer)
        ),
        key=lambda cls: cls.__name__,
    )


class TestTheMinimalFooterVariant:
    """#66: a seam with one implementation is a refactor, not a seam."""

    FACTS = {
        "email_subject": "S",
        "firm_name": "Hermes Research",
        "campaign_name": "c",
        "current_year": "2026",
        "footer_disclaimer": "<em>Legal copy</em>",
        "contact_url": "https://x.test/c",
        "unsubscribe_url": "https://x.test/u",
        "view_in_browser_url": "https://x.test/v",
    }

    def _html(self, footer):
        return Email(self.FACTS, footer=footer).render()

    def test_it_is_exported_and_is_a_footer(self):
        from svc.builder import MinimalFooter as Exported

        assert Exported is MinimalFooter
        assert issubclass(MinimalFooter, Footer)

    def test_it_composes_the_legal_template_rather_than_forking_it(self):
        assert MinimalFooter.TEMPLATE_PATHS["footer_legal"] == Footer.TEMPLATE_PATHS["footer_legal"]

    def test_the_contact_card_is_absent(self):
        html = self._html(MinimalFooter())
        assert "FOOTER PART 1" not in html
        assert "Questions or feedback?" not in html

    def test_no_vml_anywhere_in_the_footer(self):
        """
        The variant's real payoff: the ``v:roundrect`` dual emission is gone
        by omission, not adapted. The masthead's VML is untouched — this is
        a footer choice.
        """
        html = self._html(MinimalFooter())
        below = html.split("/Main container", 1)[1]
        assert "v:" not in below and "[if mso]" not in below

    def test_the_legal_block_is_intact(self):
        html = self._html(MinimalFooter())
        assert "<em>Legal copy</em>" in html
        assert "https://x.test/u" in html and "https://x.test/v" in html
        assert "2026" in html and "Hermes Research" in html

    def test_the_legal_block_is_byte_identical_to_the_default_footers(self):
        """Composition, proven: the shared template renders the same bytes."""
        marker = "FOOTER PART 2"
        default = self._html(Footer())
        minimal = self._html(MinimalFooter())
        assert default[default.index(marker) :] == minimal[minimal.index(marker) :]

    def test_the_cta_label_appears_twice_by_default_and_never_here(self):
        """
        The companion to the skeleton-copy test: the default emits the label
        twice (VML for Outlook, an anchor for everyone else); the variant
        emits it zero times because the block it lived in is gone.
        """
        assert self._html(Footer(contact_cta_label="Reach out")).count("Reach out") == 2
        assert self._html(MinimalFooter(contact_cta_label="Reach out")).count("Reach out") == 0

    def test_choosing_a_footer_leaves_the_masthead_alone(self):
        """The two region choices are independent — this one moves no byte above."""
        marker = "SECTIONS: Insert containers here"
        default = self._html(Footer())
        minimal = self._html(MinimalFooter())
        assert default[: default.index(marker)] == minimal[: minimal.index(marker)]


class TestTheComplianceFloor:
    """
    #55's non-goal, enforced: legal content is not optional.

    A golden cannot express this. A variant that dropped the unsubscribe link
    would have a golden of its own, and the golden would pin the omission as
    faithfully as it pins anything else.
    """

    def test_the_required_slot_cannot_be_left_unfilled(self):
        @dataclasses.dataclass
        class ContactOnlyFooter(Footer):
            TEMPLATE_PATHS: ClassVar[dict[str, str]] = {
                "footer_contact": "regions/footer-contact.html"
            }

        with pytest.raises(ValidationError, match=r"required slot\(s\) \['footer_legal'\]"):
            ContactOnlyFooter()

    def test_the_contact_slot_is_droppable_by_contrast(self):
        """The floor is a floor, not a ban on variation."""
        assert "footer_contact" not in Footer.REQUIRED_SLOTS
        MinimalFooter()

    @pytest.mark.parametrize("footer_cls", _public_footers(), ids=lambda c: c.__name__)
    def test_every_shipped_footer_renders_the_legal_essentials(self, footer_cls):
        """
        The structural half, over every ``Footer`` the package exports —
        introspected, so a variant added later is covered without anyone
        remembering to list it here.
        """
        html = Email(TestTheMinimalFooterVariant.FACTS, footer=footer_cls()).render()
        assert "<em>Legal copy</em>" in html, f"{footer_cls.__name__} drops the disclaimer"
        assert "https://x.test/u" in html, f"{footer_cls.__name__} drops the unsubscribe link"
