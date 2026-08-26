"""
Tests for the size vocabulary (epic #45, sub-issue #39).

The module under test ships no behaviour of its own — it is a table of
numbers. So the tests here answer the two questions a table of numbers can
get wrong: are the numbers *right* (do they still describe the templates),
and is the table *closed* (can a half-built scheme reach a render).
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from svc.builder.enums import SizeTheme
from svc.builder.exceptions import ValidationError
from svc.builder.sizing import (
    SIZE_SCHEMES,
    STANDARD_SIZES,
    ComponentScale,
    FrameGeometry,
    SizeScheme,
    SpacingScale,
    TypeScale,
    resolve_size_scheme,
)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "svc" / "builder" / "templates"


def _templates() -> list[Path]:
    return sorted(TEMPLATE_DIR.rglob("*.html"))


# ----------------------------------------------------------------------
# The audit — every token, and the value it was read out of the templates at
# ----------------------------------------------------------------------

#: The audit result, restated here so that changing a shipped size is a
#: deliberate act with a visible diff rather than a one-character edit in
#: ``sizing.py``. Kept exhaustive by ``test_the_audit_covers_every_token``:
#: a new token must be added here, which is where someone has to write down
#: what it is worth.
AUDIT: dict[str, dict[str, int | float]] = {
    "type": {
        "title": 28,
        "title_mobile": 22,
        "section": 17,
        "subheading": 16,
        "item_title": 15,
        "body": 14,
        "secondary": 13,
        "small": 11,
        "label": 10,
        "micro": 9.5,
        "title_line": 1.2,
        "heading_line": 1.3,
        "body_line": 1.72,
        "secondary_line": 1.4,
    },
    "space": {
        "gutter": 16,
        "section_title_top": 22,
        "section_title_top_split": 2,
        "section_title_bottom": 12,
        "content_top": 16,
        "content_bottom": 14,
        "column_top": 2,
        "column_bottom": 26,
        "column_pad_x": 20,
        "column_pad_x_narrow": 16,
        "mobile_pad_y": 20,
        "mobile_pad_x": 18,
        "block_gap": 16,
        "subtitle_gap": 12,
        "caption_gap": 8,
        "masthead_bar_y": 7,
        "masthead_logo_top": 18,
        "masthead_title_top": 10,
        "masthead_title_bottom": 6,
        "masthead_campaign_bottom": 8,
        "masthead_meta_top": 10,
        "masthead_meta_bottom": 18,
        "masthead_vml_height": 180,
        "footer_contact_top": 8,
        "footer_contact_bottom": 30,
        "footer_legal_top": 20,
        "footer_legal_bottom": 8,
        "footer_copyright_top": 6,
        "footer_copyright_bottom": 24,
    },
    "component": {
        "kpi_value": 21,
        "card_pad_y": 14,
        "card_pad_x": 16,
        "kpi_pad_y": 16,
        "kpi_pad_x": 12,
        "card_label_gap": 6,
        "card_value_gap": 4,
        "card_body_line": 1.6,
        "table_cell_pad": 12,
        "list_ordinal_width": 22,
        "list_ordinal_gap": 12,
        "list_title_gap": 6,
        "list_body_line": 1.68,
        "author_name_gap": 4,
        "author_sep_gap": 4,
        "author_rule_gap": 14,
        "cta_width": 150,
        "cta_height": 38,
        "contact_pad_y": 22,
        "contact_pad_x": 24,
        "contact_heading_gap": 6,
        "contact_cta_gap": 16,
        "contact_line": 1.55,
        "legal_line": 1.6,
    },
    "frame": {
        "width": 680,
        "pad_x": 32,
        "outer_pad_y": 28,
        "mobile_breakpoint": 700,
        "narrow_column": 300,
    },
}


class TestTheAudit:
    """STANDARD is the templates' own numbers, and the audit says so."""

    @pytest.mark.parametrize("layer", sorted(AUDIT))
    def test_standard_matches_the_audit(self, layer: str) -> None:
        actual = getattr(STANDARD_SIZES, layer)
        for token, expected in AUDIT[layer].items():
            assert getattr(actual, token) == expected, f"{layer}.{token} drifted from the audit"

    @pytest.mark.parametrize("layer", sorted(AUDIT))
    def test_the_audit_covers_every_token(self, layer: str) -> None:
        """
        A token missing from the audit is one nobody wrote a value down for.

        This is the same shape as the fixture-completeness tests: it
        introspects rather than hand-listing, so a token added later is
        covered without anyone remembering.
        """
        declared = {spec.name for spec in fields(SizeScheme.LAYERS[layer])}
        assert declared == set(AUDIT[layer])

    def test_inner_width_is_derived_not_stored(self) -> None:
        assert STANDARD_SIZES.frame.inner == 616
        assert (
            STANDARD_SIZES.frame.inner
            == STANDARD_SIZES.frame.width - 2 * STANDARD_SIZES.frame.pad_x
        )

    def test_every_font_size_literal_left_in_a_template_is_deliberate(self) -> None:
        """
        Any ``font-size`` still hardcoded must be one of the recorded hacks.

        ``1px`` hides the preheader and ``0`` collapses the accent rule's
        spacer cell; neither is type, and neither should move with a density
        theme. Every other value belongs to the scale, and this test is what
        stops a new template quietly inventing one.
        """
        deliberate = {"1px", "0"}
        known = {
            str(getattr(STANDARD_SIZES.type, spec.name)) + "px" for spec in fields(TypeScale)
        } | {str(STANDARD_SIZES.component.kpi_value) + "px"}
        offenders: list[str] = []
        for path in _templates():
            for literal in re.findall(
                r"font-size:\s*([0-9.]+(?:px)?)", path.read_text(encoding="utf-8")
            ):
                if literal in deliberate or literal in known:
                    continue
                offenders.append(f"{path.relative_to(TEMPLATE_DIR)}: {literal}")
        assert not offenders, "font-size literals outside the audited scale: " + ", ".join(
            offenders
        )


# ----------------------------------------------------------------------
# The layers themselves
# ----------------------------------------------------------------------


class TestLayers:
    @pytest.mark.parametrize("layer_cls", [TypeScale, SpacingScale, ComponentScale, FrameGeometry])
    def test_frozen(self, layer_cls: type) -> None:
        instance = layer_cls()
        first = fields(instance)[0].name
        with pytest.raises(FrozenInstanceError):
            setattr(instance, first, 1)

    @pytest.mark.parametrize("layer_cls", [TypeScale, SpacingScale, ComponentScale, FrameGeometry])
    def test_hashable(self, layer_cls: type) -> None:
        assert hash(layer_cls()) == hash(layer_cls())

    @pytest.mark.parametrize("bad", [0, -1, -0.5])
    def test_non_positive_rejected(self, bad: float) -> None:
        with pytest.raises(ValidationError, match="must be positive"):
            TypeScale(body=bad)

    @pytest.mark.parametrize("bad", ["14", None, [14]])
    def test_non_numeric_rejected(self, bad: object) -> None:
        with pytest.raises(ValidationError, match="must be a positive number"):
            TypeScale(body=bad)  # type: ignore[arg-type]

    def test_bool_rejected(self) -> None:
        """``True`` is an ``int``; it would render as ``1px`` if it slipped."""
        with pytest.raises(ValidationError, match="must be a positive number"):
            TypeScale(body=True)  # type: ignore[arg-type]

    def test_integral_float_rejected_by_name(self) -> None:
        """
        The trap the epic named: ``14.0`` renders ``14.0px``.

        Legal CSS, and a byte-identity failure — so it is refused at
        construction, and the message says what to pass instead.
        """
        with pytest.raises(ValidationError) as exc:
            TypeScale(body=14.0)
        assert "14.0px" in str(exc.value)
        assert "Pass 14 instead" in str(exc.value)

    def test_genuine_fraction_accepted(self) -> None:
        """9.5 is a real size in this email; the rule cannot be 'ints only'."""
        assert TypeScale(micro=9.5).micro == 9.5
        assert TypeScale(body_line=1.72).body_line == 1.72

    def test_frame_padding_must_leave_content(self) -> None:
        with pytest.raises(ValidationError, match="no content width"):
            FrameGeometry(width=64, pad_x=32)

    def test_breakpoint_must_exceed_the_frame(self) -> None:
        with pytest.raises(ValidationError, match="must exceed"):
            FrameGeometry(width=680, mobile_breakpoint=680)


class TestSizeScheme:
    def test_frozen_and_complete(self) -> None:
        with pytest.raises(FrozenInstanceError):
            STANDARD_SIZES.type = TypeScale()  # type: ignore[misc]

    def test_layer_type_is_checked(self) -> None:
        with pytest.raises(ValidationError, match="must be a TypeScale"):
            SizeScheme(type=SpacingScale())  # type: ignore[arg-type]

    def test_every_layer_is_present_on_every_shipped_scheme(self) -> None:
        """
        The ``StrictUndefined`` safety net.

        A scheme missing a layer — or a layer missing a token — would blow
        up at render, in a template, on whichever email happened to use it.
        Frozen dataclasses make that unrepresentable; this asserts it stays
        that way as schemes are added.
        """
        for name, scheme in SIZE_SCHEMES.items():
            for layer, layer_cls in SizeScheme.LAYERS.items():
                value = getattr(scheme, layer)
                assert isinstance(value, layer_cls), f"{name}.{layer}"
                for spec in fields(layer_cls):
                    assert getattr(value, spec.name) is not None

    def test_derive_overrides_one_token_and_inherits_the_rest(self) -> None:
        dense = STANDARD_SIZES.derive(type={"body": 13})
        assert dense.type.body == 13
        assert dense.type.title == STANDARD_SIZES.type.title
        assert dense.space is STANDARD_SIZES.space
        assert STANDARD_SIZES.type.body == 14, "derive() must not mutate its source"

    def test_derive_accepts_a_whole_layer(self) -> None:
        assert STANDARD_SIZES.derive(space=SpacingScale(gutter=24)).space.gutter == 24

    def test_derive_revalidates(self) -> None:
        with pytest.raises(ValidationError, match="must be positive"):
            STANDARD_SIZES.derive(type={"body": -1})

    def test_derive_rejects_an_unknown_layer(self) -> None:
        with pytest.raises(ValidationError, match="unknown size layer"):
            STANDARD_SIZES.derive(typography={"body": 13})

    def test_derive_rejects_an_unknown_token(self) -> None:
        with pytest.raises(ValidationError, match="unknown token"):
            STANDARD_SIZES.derive(type={"headline": 13})

    def test_derive_rejects_a_non_mapping(self) -> None:
        with pytest.raises(ValidationError, match="must be a TypeScale or a mapping"):
            STANDARD_SIZES.derive(type=13)


class TestResolve:
    def test_member(self) -> None:
        assert resolve_size_scheme(SizeTheme.STANDARD) is STANDARD_SIZES

    def test_bare_string(self) -> None:
        assert resolve_size_scheme("standard") is STANDARD_SIZES

    def test_unknown_name(self) -> None:
        with pytest.raises(ValidationError, match="unknown size theme 'huge'"):
            resolve_size_scheme("huge")

    def test_wrong_type(self) -> None:
        with pytest.raises(ValidationError, match="must be a SizeTheme or its name"):
            resolve_size_scheme(28)  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# #40 — the scheme is selectable, and it reaches every template
# ----------------------------------------------------------------------


class TestTheSizeThemeIsSelectable:
    def test_the_default_is_standard(self) -> None:
        from svc.builder.models import EmailMetadata

        assert EmailMetadata().size_theme == SizeTheme.STANDARD

    @pytest.mark.parametrize("value", [SizeTheme.STANDARD, "standard"])
    def test_member_or_bare_string(self, value: SizeTheme | str) -> None:
        from svc.builder.models import EmailMetadata

        assert resolve_size_scheme(EmailMetadata(size_theme=value).size_theme) is (STANDARD_SIZES)

    def test_the_field_keeps_what_the_caller_passed(self) -> None:
        """
        Resolution happens once, in ``Email.render()``. Construction only
        *checks* — so a typo fails there, and the field stays the caller's
        own value rather than a silently normalised one.
        """
        from svc.builder.models import EmailMetadata

        assert EmailMetadata(size_theme="standard").size_theme == "standard"

    def test_an_unknown_name_raises_at_construction(self) -> None:
        from svc.builder.models import EmailMetadata

        with pytest.raises(ValidationError, match="unknown size theme 'huge'"):
            EmailMetadata(size_theme="huge")

    def test_it_is_not_in_the_skeleton_context(self) -> None:
        """One value, one source: the resolved scheme rides the binder."""
        from svc.builder.models import EmailMetadata

        assert "size_theme" not in EmailMetadata().to_dict()


class TestTheSchemeReachesEveryTemplate:
    """
    #40's plumbing — and the decision it inherited rather than re-made.

    #48 already built the injection mechanism the epic left to this issue:
    ``TemplateEngine.bound(**shared)`` returns a per-render view that merges
    shared values into every context. A size scheme is another shared value
    on the same binder, so containers, components and regions keep their
    one-argument ``render()`` and nothing in the section tree changed.
    """

    FACTS = {
        "email_subject": "S",
        "firm_name": "F",
        "campaign_name": "c",
        "contact_url": "https://x.test/c",
    }

    def _rendered_contexts(self, **metadata: object) -> dict[str, dict]:
        from svc.builder import (
            CardGroup,
            DataTable,
            Email,
            FullWidth,
            TemplateEngine,
            TextBlock,
            ThreeColumn,
            TwoColumn,
        )
        from svc.builder.models import Card, TableRow

        seen: dict[str, dict] = {}
        real = TemplateEngine()
        original = real.render

        def recording(name: str, context: dict) -> str:
            seen[name] = context
            return original(name, context)

        real.render = recording  # type: ignore[method-assign]

        email = Email({**self.FACTS, **metadata})
        email._engine = real  # the binder is built from this inside render()
        email.add_section(FullWidth(title="T", content=TextBlock("<p>x</p>")))
        email.add_section(
            TwoColumn(
                ratio="50-50",
                left=CardGroup([Card("L", "V"), Card("M", "W")], orientation="horizontal"),
                right=DataTable(headers=["H"], rows=[TableRow(["c"])]),
            )
        )
        email.add_section(ThreeColumn(ratio="33-33-33", left=TextBlock("<p>y</p>")))
        email.render()
        return seen

    def test_every_rendered_template_gets_the_size_namespace(self) -> None:
        seen = self._rendered_contexts()
        assert len(seen) >= 8, f"only rendered {sorted(seen)}"
        for name, context in seen.items():
            assert "size" in context, f"{name} rendered without the size scheme"
            assert context["size"] is STANDARD_SIZES

    def test_the_key_is_injected_unconditionally(self) -> None:
        """
        Never behind an ``if`` — the #5/#15 lesson. Under
        ``StrictUndefined`` an unused key is free and a missing one raises,
        so the asymmetry decides it.
        """
        for context in self._rendered_contexts(size_theme="standard").values():
            assert "size" in context

    def test_a_component_cannot_shadow_the_emails_scheme(self) -> None:
        from svc.builder import TemplateEngine

        binder = TemplateEngine().bound(size=STANDARD_SIZES)
        merged = {**{"size": "impostor"}, **binder.shared}
        assert merged["size"] is STANDARD_SIZES

    def test_two_emails_sharing_an_engine_do_not_interleave(self) -> None:
        """
        The constraint the epic set for whichever mechanism was chosen. A
        binder is per-render, so a second one cannot disturb the first.
        """
        from svc.builder import TemplateEngine

        engine = TemplateEngine()
        dense = STANDARD_SIZES.derive(type={"body": 13})
        first = engine.bound(size=STANDARD_SIZES)
        second = engine.bound(size=dense)
        assert first.shared["size"] is STANDARD_SIZES
        assert second.shared["size"] is dense

    def test_the_engine_guarantees_a_scheme_on_its_own(self) -> None:
        """
        Rendering a component standalone stays a one-liner: the engine
        layers ``STANDARD_SIZES`` *under* the caller's context, so a bound
        scheme still wins over this floor.
        """
        from svc.builder import TemplateEngine

        engine = TemplateEngine()
        assert engine.render_string("{{ size.type.body }}", {}) == "14"
        assert engine.render_string("{{ size.type.body }}", {"size": STANDARD_SIZES}) == "14"

    def test_naming_the_default_renders_identically_to_omitting_it(self) -> None:
        from qa.fixtures import kitchen_sink

        assert kitchen_sink.build().render() == kitchen_sink.build().render()
