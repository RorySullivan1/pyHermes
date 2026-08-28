"""
The font vocabulary: stacks, roles, validation, and the pin to today's values.

#104's bar is the one #39 and #47 set for their axes — the module lands
complete and validated, pinned to what the templates already render, before a
single template is touched. Nothing here may move a rendered byte, and the
gallery goldens are the gate that says so.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from svc.builder import DEFAULT_FONTS, FONT_THEMES, MODERN_FONTS, FontStack, FontTheme
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.typography import GENERIC_FAMILIES, resolve_font_theme

TEMPLATE_DIR = TemplateEngine().template_dir

#: The audit, as literals. Every stack the templates render today, in the
#: **spaced** spelling — the canonical one, chosen because it is the majority
#: (26 of 49 declarations) and the more readable. The unspaced spelling that
#: coexists in the templates is what #106 normalises away; this constant is
#: what it normalises *to*.
TODAYS_STACKS = {
    "serif": "Georgia, 'Times New Roman', serif",
    "sans": "Arial, Helvetica, sans-serif",
    "mono": "'Courier New', Courier, monospace",
}


def _all_templates() -> list[Path]:
    return sorted(TEMPLATE_DIR.rglob("*.html"))


#: One rendered ``font-family`` declaration, value included.
_FAMILY = re.compile(r"font-family:\s*[^;\"]+")


def _families(html: str) -> set[str]:
    """Every distinct stack a rendered email actually carries."""
    return {value.strip() for value in re.findall(r"font-family:\s*([^;\"]+)", html)}


class TestTheDefaultIsPinnedToTodaysValues:
    """
    The audit, asserted rather than remembered.

    A vocabulary whose defaults drifted from the templates would make #106's
    migration move bytes, and the whole epic rests on it not doing that.
    """

    def test_every_role_emits_an_audited_stack(self):
        emitted = {
            spec.name: getattr(DEFAULT_FONTS, spec.name).css
            for spec in dataclasses.fields(DEFAULT_FONTS)
        }
        assert emitted == {
            "heading": TODAYS_STACKS["serif"],
            "body": TODAYS_STACKS["serif"],
            "label": TODAYS_STACKS["sans"],
            "numeric": TODAYS_STACKS["mono"],
        }

    @pytest.mark.parametrize("stack", sorted(TODAYS_STACKS.values()))
    def test_each_audited_stack_is_actually_rendered_today(self, stack):
        """
        The other direction, and the one that catches a stale audit: every
        stack this module claims to reproduce must still reach the page.

        Read off the **render** rather than the templates — since #106 the
        templates hold tokens, so a literal search there would now pass
        vacuously. The gallery's widest email exercises all four roles.
        """
        from qa.fixtures import kitchen_sink

        assert stack in kitchen_sink.build().render(), (
            f"nothing renders {stack!r} — the audit has gone stale"
        )

    def test_the_default_render_carries_exactly_the_audited_three(self):
        """
        The audit pins the *default*: an email that chooses nothing renders
        the three stacks this module was built to reproduce, and no fourth.
        """
        from qa.fixtures import kitchen_sink

        assert _families(kitchen_sink.build().render()) == set(TODAYS_STACKS.values())

    def test_no_fixture_renders_a_stack_no_preset_declares(self):
        """
        Completeness across the gallery, and the claim had to widen when the
        second preset landed: a rendered face must come from the *vocabulary*
        — some registered preset — rather than from the audit's three. A
        literal sneaking back into a template fails here, because no preset
        declares it.
        """
        from qa.fixtures import all_fixtures

        declared = {
            getattr(theme, spec.name).css
            for theme in FONT_THEMES.values()
            for spec in dataclasses.fields(theme)
        }
        seen: set[str] = set()
        for build in all_fixtures().values():
            seen |= _families(build().render())
        assert seen <= declared, f"undeclared stack(s) rendered: {sorted(seen - declared)}"


class TestTheStackIsTheAtom:
    def test_families_are_stored_unquoted_and_quoted_on_emission(self):
        """
        Quoting is an emission concern, so a name is never stored pre-quoted —
        which is what lets the terminal-generic check compare plain strings.
        """
        stack = FontStack("Courier New", "Courier", "monospace")
        assert stack.families == ("Courier New", "Courier", "monospace")
        assert stack.css == "'Courier New', Courier, monospace"

    def test_the_formatting_contract_is_byte_exact(self):
        """
        One composer, so two emission sites cannot drift — the ``Rgba.css``
        lesson. Separator is ``", "``; only multi-word names are quoted.
        """
        assert FontStack("Arial", "Helvetica", "sans-serif").css == "Arial, Helvetica, sans-serif"

    def test_str_is_the_css_so_a_template_can_interpolate_it(self):
        stack = FontStack("Georgia", "Times New Roman", "serif")
        assert f"{stack}" == stack.css

    def test_a_chain_must_end_in_a_generic_family(self):
        """
        The rule that makes a caller's own face safe rather than a gamble: in
        email the fallback chain *is* the rendering.
        """
        with pytest.raises(ValidationError, match="generic family"):
            FontStack("Georgia", "Times New Roman")

    @pytest.mark.parametrize("generic", sorted(GENERIC_FAMILIES))
    def test_each_generic_is_accepted_as_a_terminal(self, generic):
        assert FontStack("Some Face", generic).families[-1] == generic

    def test_a_bare_generic_is_rejected_as_an_empty_decision(self):
        with pytest.raises(ValidationError, match="at least a face"):
            FontStack("serif")

    @pytest.mark.parametrize("bad", ['Ari"al', "Ari'al", "Arial;", "Arial{", "Arial}", "Ari<al"])
    def test_a_family_that_would_break_the_style_attribute_is_rejected(self, bad):
        """
        A shape-and-safety rule, the same family as the URL scheme check: the
        value is emitted inside a double-quoted ``style`` attribute.
        """
        with pytest.raises(ValidationError, match="quoted style attribute"):
            FontStack(bad, "sans-serif")

    @pytest.mark.parametrize("bad", ["", "   ", None, 42])
    def test_a_family_must_be_a_non_empty_string(self, bad):
        with pytest.raises(ValidationError, match="non-empty strings"):
            FontStack(bad, "sans-serif")

    def test_stacks_compare_by_their_chain(self):
        assert FontStack("Arial", "sans-serif") == FontStack("Arial", "sans-serif")
        assert FontStack("Arial", "sans-serif") != FontStack("Verdana", "sans-serif")


class TestTheThemeIsCompleteByConstruction:
    def test_every_role_is_populated_with_a_stack(self):
        for spec in dataclasses.fields(DEFAULT_FONTS):
            assert isinstance(getattr(DEFAULT_FONTS, spec.name), FontStack)

    def test_no_role_is_optional(self):
        """
        Frozen and complete, so a ``FontTheme`` that exists is one that
        renders and ``StrictUndefined`` cannot be tripped by a half-built one.
        """
        assert all(
            spec.default is dataclasses.MISSING or spec.default is not None
            for spec in dataclasses.fields(FontTheme)
        )
        assert FontTheme() == DEFAULT_FONTS

    def test_a_non_stack_role_is_rejected_naming_the_field(self):
        with pytest.raises(ValidationError, match="font.heading"):
            FontTheme(heading="Georgia, serif")  # type: ignore[arg-type]

    def test_it_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            DEFAULT_FONTS.heading = FontStack("Arial", "sans-serif")  # type: ignore[misc]

    def test_the_four_roles_are_named_by_job_not_by_face(self):
        """
        ``heading`` and ``body`` share a stack in the default and are separate
        roles anyway — the distinction the motivating preset needs, and the
        by-value naming mistake both prior audits existed to avoid.
        """
        names = {spec.name for spec in dataclasses.fields(FontTheme)}
        assert names == {"heading", "body", "label", "numeric"}
        assert DEFAULT_FONTS.heading == DEFAULT_FONTS.body


class TestDerive:
    def test_it_keeps_everything_it_was_not_told_to_change(self):
        derived = DEFAULT_FONTS.derive(heading=FontStack("Verdana", "Geneva", "sans-serif"))
        assert derived.heading.css == "Verdana, Geneva, sans-serif"
        assert derived.body == DEFAULT_FONTS.body
        assert derived.label == DEFAULT_FONTS.label
        assert derived.numeric == DEFAULT_FONTS.numeric

    def test_it_accepts_a_plain_iterable_of_families(self):
        derived = DEFAULT_FONTS.derive(heading=("Verdana", "Geneva", "sans-serif"))
        assert derived.heading == FontStack("Verdana", "Geneva", "sans-serif")

    def test_it_revalidates_so_a_derived_theme_is_never_less_valid(self):
        with pytest.raises(ValidationError, match="generic family"):
            DEFAULT_FONTS.derive(heading=("Verdana", "Geneva"))

    def test_an_unknown_role_raises_naming_the_known_ones(self):
        with pytest.raises(ValidationError, match="unknown font role"):
            DEFAULT_FONTS.derive(masthead=FontStack("Verdana", "sans-serif"))

    def test_it_does_not_mutate_the_original(self):
        DEFAULT_FONTS.derive(body=("Verdana", "sans-serif"))
        assert DEFAULT_FONTS.body.css == TODAYS_STACKS["serif"]


class TestThePresetRegistry:
    def test_classic_is_the_default_object(self):
        assert FONT_THEMES["classic"] is DEFAULT_FONTS

    def test_every_registered_preset_is_complete(self):
        """
        The completeness test in the #45 pattern: a preset missing a role
        would reach a template as ``None`` and render the string "None".
        """
        for name, theme in FONT_THEMES.items():
            for spec in dataclasses.fields(theme):
                assert isinstance(getattr(theme, spec.name), FontStack), f"{name}.{spec.name}"

    def test_a_theme_object_resolves_to_itself(self):
        custom = DEFAULT_FONTS.derive(label=("Verdana", "sans-serif"))
        assert resolve_font_theme(custom) is custom

    def test_a_preset_name_resolves(self):
        assert resolve_font_theme("classic") is DEFAULT_FONTS

    def test_an_unknown_name_raises_listing_what_exists(self):
        with pytest.raises(ValidationError, match="unknown font theme"):
            resolve_font_theme("helvetica")

    def test_modern_moves_only_the_roles_it_claims(self):
        """
        A preset is a curation, so what it leaves *alone* is as much of the
        decision as what it changes — and a shared role that had drifted
        would be invisible in a golden, which only says "these bytes moved".

        ``modern`` is a display swap: the two roles that carry titling and
        chrome move to the sans; the two that carry reading copy and figures
        are held at the default deliberately, because a newsletter is read in
        a serif and a table aligns in a mono.
        """
        moved = {"heading", "label"}
        held = {"body", "numeric"}
        assert moved | held == {spec.name for spec in dataclasses.fields(FontTheme)}

        for role in held:
            assert getattr(MODERN_FONTS, role) == getattr(DEFAULT_FONTS, role), role
        for role in moved:
            assert getattr(MODERN_FONTS, role) != getattr(DEFAULT_FONTS, role), role

    def test_the_two_presets_differ_in_face_and_in_nothing_else(self):
        """
        The A/B the ``modern_fonts`` golden rests on: every byte between the
        two renders is a typeface. Anything else moving would make that
        fixture's diff unreadable — which is the whole reason it reuses
        ``kitchen_sink``'s content rather than restating it — and it is also
        the epic's orthogonality claim, since a font swap moves no px.
        """
        from qa.fixtures import kitchen_sink, modern_fonts

        classic = kitchen_sink.build().render()
        modern = modern_fonts.build().render()

        assert _families(classic) != _families(modern)
        assert _FAMILY.sub("font-family:", classic) == _FAMILY.sub("font-family:", modern)


#: A theme whose every role is a distinct, findable family.
#:
#: The sizing epic's technique: rendering under a scheme where every token is
#: a sentinel answers "is this token actually *drawn*?", which neither the
#: goldens nor a default-valued render can.
SENTINEL_FONTS = FontTheme(
    heading=FontStack("SentinelHeading", "serif"),
    body=FontStack("SentinelBody", "serif"),
    label=FontStack("SentinelLabel", "sans-serif"),
    numeric=FontStack("SentinelNumeric", "monospace"),
)


class TestEveryRoleIsActuallyDrawn:
    """
    #106's proof, and the third state of one test.

    It began in #104 as "nothing imports the module", became #105's "bound but
    undrawn", and is now its final form: every role reaches the page and no
    shipped family survives a sentinel render. A role nobody draws is a field
    a caller can set to no effect — the failure the sizing epic named.
    """

    @staticmethod
    def _sentinel_html() -> str:
        from qa.fixtures import kitchen_sink

        email = kitchen_sink.build()
        email.metadata.font_theme = SENTINEL_FONTS
        return email.render()

    @pytest.mark.parametrize("role", ["heading", "body", "label", "numeric"])
    def test_the_role_reaches_the_page(self, role):
        stack = getattr(SENTINEL_FONTS, role)
        assert stack.css in self._sentinel_html(), f"font.{role} is bound but never drawn"

    def test_no_shipped_family_survives_a_sentinel_render(self):
        """
        The other direction, and the one that catches a bypassed token: a
        literal left behind would keep rendering Georgia or Arial under a
        theme that names neither.
        """
        html = self._sentinel_html()
        for family in ("Georgia", "Times New Roman", "Arial", "Helvetica", "Courier"):
            assert family not in html, f"{family!r} survived — a literal was left behind"

    def test_the_default_render_is_unchanged_by_the_migration(self):
        """
        The goldens are the real gate; this says the same thing at one email,
        so a failure points at the plumbing rather than at a template.
        """
        from qa.fixtures import kitchen_sink

        assert "Sentinel" not in kitchen_sink.build().render()


class TestNoLiteralSurvives:
    """
    Standing rule, in the shape rules 4 and 5 already have for colours and
    sizes: a face outside the vocabulary is a face the theme cannot move.
    """

    def test_no_template_declares_a_literal_family(self):
        offenders = []
        for path in _all_templates():
            for raw in re.findall(r"font-family:[^;\"]*", path.read_text()):
                if "{{ font." not in raw:
                    offenders.append(f"{path.name}: {raw.strip()}")
        assert not offenders, (
            "every font-family must read the font namespace; found literals in "
            + ", ".join(offenders)
        )

    def test_no_python_default_carries_a_family(self):
        """
        The other half of rules 4/5: a literal hiding in a Python default is
        just as unthemeable as one in markup.
        """
        for path in sorted(Path("svc").rglob("*.py")):
            if path.name == "typography.py":  # the vocabulary is where they live
                continue
            source = path.read_text()
            for family in ("Georgia", "Helvetica", "Courier New"):
                assert family not in source, f"{path} carries a font literal"

    def test_the_outlook_fallback_block_reads_the_body_token(self):
        """
        The one divergent copy this axis has, and the reason it is named: the
        ``[if mso]`` ``body, td, th`` rule is Outlook's floor for *everything*.
        Left literal, a themed email would render custom-faced in Gmail and
        Georgia in Outlook — the half-themed failure rules 4 and 5 exist to
        prevent, in the client hardest to check.
        """
        base = (TEMPLATE_DIR / "base.html").read_text()
        mso = base[base.index("<!--[if mso]>") : base.index("<![endif]-->")]
        assert "body, td, th { font-family: {{ font.body }}; }" in mso

    def test_the_dark_mode_and_media_blocks_carry_no_faces(self):
        """
        Checked rather than assumed, because rules 4 and 5 both name these two
        blocks as the drift sites. For fonts they are empty today — and a
        future edit adding a face to either must read a token like everything
        else, which the literal test above already enforces.
        """
        base = (TEMPLATE_DIR / "base.html").read_text()
        media = base[base.index("@media only screen") : base.index("Force light rendering")]
        dark = base[base.index("Force light rendering") : base.index("</style>")]
        assert "font-family" not in media
        assert "font-family" not in dark

    def test_the_engine_guarantees_a_font_theme_on_its_own(self):
        """
        The floor its two siblings already have: rendering a component
        without an ``Email`` still resolves the namespace, so a template that
        reads it in #106 cannot trip ``StrictUndefined``.
        """
        rendered = TemplateEngine().render_string("{{ font.body }}|{{ font.numeric }}", {})
        assert rendered == f"{DEFAULT_FONTS.body}|{DEFAULT_FONTS.numeric}"

    def test_a_bound_theme_is_carried_on_the_shared_mapping(self):
        """
        The floor is the engine's; the choice is the email's. At this step the
        binding can only be observed on the binder, because no template draws
        it — #106 is where "the email's binding wins" becomes visible in a
        render, and the sentinel above becomes the assertion that it does.
        """
        chosen = DEFAULT_FONTS.derive(body=("Verdana", "sans-serif"))
        assert TemplateEngine().bound(font=chosen).shared["font"] is chosen

    def test_email_render_resolves_the_field_to_an_object(self):
        """
        A name on the metadata must reach the binder as a resolved
        ``FontTheme``, never as the string — the resolve-once rule its two
        siblings follow.
        """
        from qa.fixtures import kitchen_sink

        recorded: dict[str, object] = {}
        email = kitchen_sink.build()
        original = type(email._engine).bound

        def spy(self, **shared):
            recorded.update(shared)
            return original(self, **shared)

        type(email._engine).bound = spy  # type: ignore[method-assign]
        try:
            email.render()
        finally:
            type(email._engine).bound = original  # type: ignore[method-assign]

        assert isinstance(recorded["font"], FontTheme)
        assert recorded["font"] is DEFAULT_FONTS, "the 'classic' name must resolve to the object"

    def test_it_rides_the_existing_binder_rather_than_a_second_one(self):
        """
        The technique both prior epics carried: one binder, three shared
        values, and no signature in the section tree changed to carry them.
        """
        source = (Path("svc/builder") / "email.py").read_text()
        bind = source[source.index("self._engine.bound(") : source.index("sections_html =")]
        assert bind.count("bound(") == 1
        for value in ("theme=", "size=", "font="):
            assert value in bind, f"{value} is not on the shared binder"
