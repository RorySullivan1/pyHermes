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

from svc.builder import DEFAULT_FONTS, FONT_THEMES, FontStack, FontTheme
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
    def test_each_audited_stack_is_actually_drawn_today(self, stack):
        """
        The other direction, and the one that catches a stale audit: every
        stack this module claims to reproduce must appear verbatim in a
        template right now. Read off the templates, never hand-confirmed.

        Matched as the stack string rather than after a ``font-family:``
        prefix, because the mono stack is only ever reached through the data
        table's per-column ``{% if loop.first %}`` branch.
        """
        carriers = [p.name for p in _all_templates() if stack in p.read_text()]
        assert carriers, f"no template renders {stack!r} — the audit has gone stale"

    def test_no_template_carries_a_stack_the_vocabulary_lacks(self):
        """
        Completeness of the audit itself: strip whitespace and every
        ``font-family`` value in the templates must be one of the three. A
        fourth stack appearing later fails here rather than being silently
        left behind by #106's migration.
        """
        seen: set[str] = set()
        for path in _all_templates():
            for raw in re.findall(r"font-family:\s*([^;\"]+)", path.read_text()):
                if "{%" in raw or "{{" in raw:  # the data table's per-column branch
                    branch = r"([A-Za-z'][^{}%]*?(?:serif|sans-serif|monospace))"
                    seen.update(re.findall(branch, raw))
                else:
                    seen.add(raw)
        canonical = {re.sub(r",\s*", ", ", s.strip()) for s in seen}
        assert canonical == set(TODAYS_STACKS.values())


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


class TestTheNamespaceIsBoundButUndrawn:
    """
    #105's proof, and the inversion of the sizing epic's sentinel test.

    The tokens are now resolved once and bound on the same ``BoundEngine`` as
    the theme and the size scheme — but no template reads them yet, so this
    step's byte-identity is a *property* rather than a claim. #106 flips the
    sentinel below to "every role appears".
    """

    def test_no_template_reads_the_namespace_yet(self):
        for path in _all_templates():
            assert "{{ font." not in path.read_text(), f"{path.name} reads the namespace early"

    def test_a_sentinel_theme_changes_nothing(self):
        """
        Bound, and provably undrawn: a theme whose every stack is a findable
        family must leave the render untouched, because nothing reads it.
        The same email under the default and under the sentinel is byte-equal,
        and no sentinel family appears anywhere.
        """
        from qa.fixtures import kitchen_sink

        sentinel = FontTheme(
            heading=FontStack("SentinelHeading", "serif"),
            body=FontStack("SentinelBody", "serif"),
            label=FontStack("SentinelLabel", "sans-serif"),
            numeric=FontStack("SentinelNumeric", "monospace"),
        )
        default_html = kitchen_sink.build().render()
        email = kitchen_sink.build()
        email.metadata.font_theme = sentinel
        assert email.render() == default_html
        assert "Sentinel" not in default_html

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
