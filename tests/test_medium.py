"""
The medium: who owns the skeleton, the slot contract and the constraints.

Three claims are load-bearing and none is visible in a golden — the
constraint set belongs to the medium rather than to ``Email``, the slots come
from the region classes rather than a second list, and the medium reaches a
template the way the other three namespaces do.
"""

import shutil
from dataclasses import replace

import pytest

from pyhermes.builder import Email, FullWidth, TextBlock
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.exceptions import SizeError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.medium import DEFAULT_MEDIUM, Medium
from pyhermes.builder.regions import Banner, Footer, Header
from pyhermes.builder.sizing import DEFAULT_PAGE, SPACIOUS_SIZES, STANDARD_SIZES, PageFormat
from pyhermes.email.medium import _SIZE_LIMIT_KB, EMAIL_MEDIUM, validate_gmail_size

#: A medium identical to the shipped one but for its (absent) constraints.
UNCHECKED = Medium(
    name="unchecked",
    skeleton=EMAIL_MEDIUM.skeleton,
    region_types=EMAIL_MEDIUM.region_types,
)


def oversized(valid_metadata, medium=None) -> Email:
    """An email whose rendered HTML is comfortably past the Gmail limit."""
    email = Email(valid_metadata, medium=medium) if medium else Email(valid_metadata)
    filler = "x" * ((_SIZE_LIMIT_KB + 10) * 1024)
    email.add_section(FullWidth(content=TextBlock(f"<p>{filler}</p>")))
    return email


class TestTheMediumOwnsTheConstraint:
    def test_the_shipped_medium_still_enforces_the_gmail_limit(self, valid_metadata):
        # The behaviour that must not change while its owner moves.
        with pytest.raises(SizeError, match="Gmail clipping limit"):
            oversized(valid_metadata).render()

    def test_a_medium_without_constraints_renders_the_same_document(self, valid_metadata):
        # The proof the check is the medium's, not Email's: same email, same
        # skeleton, no constraint, no raise.
        html = oversized(valid_metadata, medium=UNCHECKED).render()
        assert len(html.encode("utf-8")) / 1024 > _SIZE_LIMIT_KB

    def test_constraints_run_in_order_and_receive_the_hint(self):
        seen = []
        medium = Medium(
            name="probe",
            skeleton="base.html",
            constraints=(
                lambda html, hint="": seen.append(("first", hint)),
                lambda html, hint="": seen.append(("second", hint)),
            ),
        )
        medium.validate("<html></html>", "a hint")
        assert seen == [("first", "a hint"), ("second", "a hint")]

    def test_the_inline_image_hint_still_reaches_the_failure(self, valid_metadata, png_bytes):
        # _inline_image_hint now feeds a constraint rather than a private
        # method, so the guidance a caller gets has to survive the move.
        email = oversized(valid_metadata)
        email.set_banner(Banner(logo_url=EmailImage.inline(png_bytes, alt="Logo", width=100)))
        with pytest.raises(SizeError, match="inlined image"):
            email.render()

    def test_the_check_is_importable_from_the_medium_that_owns_it(self):
        with pytest.raises(SizeError):
            validate_gmail_size("x" * ((_SIZE_LIMIT_KB + 1) * 1024))


class TestTheSlotsComeFromTheRegions:
    def test_the_email_medium_derives_its_slots_from_its_region_classes(self):
        assert EMAIL_MEDIUM.region_types == (Header, Banner, Footer)
        assert EMAIL_MEDIUM.slots == Header.SLOTS + Banner.SLOTS + Footer.SLOTS

    def test_the_skeleton_names_every_slot_the_medium_claims(self, engine):
        # A slot the skeleton does not name renders a whole region into
        # nothing, silently. StrictUndefined catches the opposite case only.
        skeleton = (engine.template_dir / EMAIL_MEDIUM.skeleton).read_text(encoding="utf-8")
        for slot in EMAIL_MEDIUM.slots:
            assert f"{{{{ {slot}_html }}}}" in skeleton

    def test_render_loads_the_skeleton_the_medium_names(self, valid_metadata, engine, tmp_path):
        # The literal "base.html" is gone from render(); this is what proves
        # it, and it is the mechanism every later medium arrives through.
        templates = tmp_path / "templates"
        shutil.copytree(engine.template_dir, templates)
        (templates / "probe.html").write_text("PROBE {{ sections_html }}", encoding="utf-8")
        email = Email(
            valid_metadata,
            template_dir=templates,
            medium=replace(EMAIL_MEDIUM, skeleton="probe.html"),
        )
        assert email.render().startswith("PROBE")

    def test_the_body_is_not_a_region(self, engine):
        # The ordered section list is deliberately not a region, so it is not
        # a slot -- though the skeleton still names it.
        skeleton = (engine.template_dir / EMAIL_MEDIUM.skeleton).read_text(encoding="utf-8")
        assert "{{ sections_html }}" in skeleton
        assert "sections" not in EMAIL_MEDIUM.slots


class TestTheMediumRidesTheBinder:
    def test_the_engine_guarantees_a_medium_with_nothing_bound(self, engine):
        # The fourth namespace's floor, exactly as theme, size and font have
        # one: rendering a component on its own stays a one-liner.
        assert engine.render_string("{{ medium.name }}", {}) == DEFAULT_MEDIUM.name

    def test_the_floor_is_neither_paged_nor_email(self, engine):
        # A component rendered outside any document must not emit email-only
        # markup on the strength of a default.
        assert engine.render_string("{{ medium.email }}{{ medium.paged }}", {}) == "FalseFalse"

    def test_a_bound_medium_wins_over_the_floor(self, tmp_path):
        (tmp_path / "probe.html").write_text("{{ medium.name }}", encoding="utf-8")
        engine = TemplateEngine(tmp_path)
        assert engine.render("probe.html", {}) == DEFAULT_MEDIUM.name
        assert engine.bound(medium=EMAIL_MEDIUM).render("probe.html", {}) == "email"

    def test_render_binds_the_documents_own_medium(self, valid_metadata, monkeypatch):
        captured = {}
        original = TemplateEngine.bound

        def spy(self, **shared):
            captured.update(shared)
            return original(self, **shared)

        monkeypatch.setattr(TemplateEngine, "bound", spy)
        Email(valid_metadata).render()
        assert captured["medium"] is EMAIL_MEDIUM

    def test_the_medium_is_read_only(self, valid_metadata):
        email = Email(valid_metadata)
        assert email.medium is EMAIL_MEDIUM
        with pytest.raises(AttributeError):
            email.medium = DEFAULT_MEDIUM


class TestTheFrameBelongsToTheMedium:
    """
    #159: the page is the medium's, the padding inside it is the density's.

    The three shipped densities are the evidence: not one of them changes the
    width, only what sits inside it.
    """

    def test_no_shipped_density_declares_a_page_dimension(self):
        # The structural form of "density is not width". Before #159 a preset
        # could have set a width and nothing would have stopped it.
        from pyhermes.builder.sizing import SIZE_SCHEMES

        for theme, scheme in SIZE_SCHEMES.items():
            assert scheme.frame.width == DEFAULT_PAGE.width, theme
            assert scheme.frame.height == DEFAULT_PAGE.height, theme
            assert scheme.frame.mobile_breakpoint == DEFAULT_PAGE.mobile_breakpoint, theme

    def test_the_densities_still_differ_at_the_frames_edge(self):
        # ...and the half that IS the density's must not have been flattened
        # along the way.
        assert SPACIOUS_SIZES.frame.pad_x != STANDARD_SIZES.frame.pad_x
        assert SPACIOUS_SIZES.frame.outer_pad_y != STANDARD_SIZES.frame.outer_pad_y

    def test_the_page_is_layered_over_a_caller_derived_frame(self):
        # The same precedence facts get over a region and a bound value gets
        # over caller context: what the medium owns cannot be shadowed.
        forged = STANDARD_SIZES.derive(frame={"width": 1234, "mobile_breakpoint": 1300})
        assert forged.with_page(DEFAULT_PAGE).frame.width == DEFAULT_PAGE.width

    def test_a_density_already_on_that_page_is_returned_unchanged(self):
        # Not an optimisation detail: one scheme object per shipped page is
        # what lets a test assert the scheme is threaded, not rebuilt.
        assert STANDARD_SIZES.with_page(DEFAULT_PAGE) is STANDARD_SIZES

    def test_no_shipped_page_value_survives_a_medium_on_another_page(self, valid_metadata):
        """
        The sentinel #106 taught, aimed at the frame's new owner.

        Change only the medium's page -- no template, no density -- and every
        rendered page dimension has to follow. A template still reading the
        frame from the old owner would render 680 here and look perfectly
        correct doing it, which is exactly what a golden cannot see.
        """
        page = PageFormat(width=9001, mobile_breakpoint=9101)
        html = Email(valid_metadata, medium=replace(EMAIL_MEDIUM, page_format=page)).render()

        # Both page tokens any template reads, at their sentinel values...
        assert 'width="9001"' in html, "the frame width never reached the markup"
        assert "max-width:9001px" in html
        assert "max-width:9101px" in html, "the breakpoint never reached the media query"

        # ...and no trace of the page the medium did not name.
        for shipped in (DEFAULT_PAGE.width, DEFAULT_PAGE.mobile_breakpoint):
            assert f"max-width:{shipped}px" not in html, f"{shipped} survived a page change"
        assert f'width="{DEFAULT_PAGE.width}"' not in html

    def test_the_content_width_follows_the_page(self, valid_metadata):
        # frame.inner spans both owners -- width from the medium, pad_x from
        # the density -- so it is the one value that proves they compose.
        wide = replace(EMAIL_MEDIUM, page_format=PageFormat(width=900, mobile_breakpoint=920))
        assert STANDARD_SIZES.with_page(wide.page_format).frame.inner == 900 - 2 * 32


class TestTheMediumNamesItsTemplates:
    """#160: the search path is the medium's, and Email wires it."""

    def test_the_email_medium_declares_its_own_directory(self):
        assert EMAIL_MEDIUM.template_search_path == ("email",)

    def test_an_email_searches_that_directory_ahead_of_the_shared_tree(self, valid_metadata):
        assert Email(valid_metadata)._engine.search_path == EMAIL_MEDIUM.template_search_path

    def test_nothing_is_forked_yet(self, valid_metadata):
        # The claim that makes #160 byte-identical: the overlay is declared
        # and empty, so every lookup in the suite falls through to the shared
        # tree. When this first fails, a fork has landed and its PR owes a
        # reason -- see TemplateEngine's docstring.
        engine = Email(valid_metadata)._engine
        for sub in engine.search_path:
            assert not (engine.template_dir / sub).exists(), f"{sub}/ now holds a fork"

    def test_a_medium_that_forks_nothing_declares_nothing(self):
        assert DEFAULT_MEDIUM.template_search_path == ()
