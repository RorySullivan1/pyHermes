"""
Tests for the size vocabulary (epic #45, sub-issue #39).

The module under test ships no behaviour of its own — it is a table of
numbers. So the tests here answer the two questions a table of numbers can
get wrong: are the numbers *right* (do they still describe the templates),
and is the table *closed* (can a half-built scheme reach a render).
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from typing import Any

import pytest

from svc.builder.enums import SizeTheme
from svc.builder.exceptions import ValidationError
from svc.builder.filters import percent
from svc.builder.sizing import (
    PRINT_DENSITIES,
    SIZE_SCHEMES,
    STANDARD_SIZES,
    ComponentScale,
    FrameGeometry,
    PageFormat,
    PageMargin,
    SizeScheme,
    SpacingScale,
    TypeScale,
    _remainder_order,
    column_layout,
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
        "masthead_top": 18,
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
        "table_cell_pad_mobile": 6,
        "table_bar_height": 6,
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
        # None is the shipped value, not a gap: an email body is continuous
        # and ends where its content does. See PageFormat.
        "height": None,
        "pad_x": 32,
        "outer_pad_y": 28,
        "mobile_breakpoint": 700,
        "narrow_column": 300,
        # Zero all round: an email is not printed. See PageMargin.
        "margin": PageMargin(),
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

    def test_a_page_knows_its_own_orientation(self) -> None:
        # Derived, never stored: a declared orientation is a second fact about
        # the same two numbers, and the two can disagree.
        assert PageFormat(680).orientation == "continuous"
        assert PageFormat(794, 1123).orientation == "portrait"
        assert PageFormat(1123, 794).orientation == "landscape"
        assert PageFormat(800, 800).orientation == "square"

    def test_a_page_validates_the_breakpoint_it_declares(self) -> None:
        with pytest.raises(ValidationError, match="must exceed"):
            PageFormat(width=680, mobile_breakpoint=680)

    def test_a_page_that_never_collapses_is_legal(self) -> None:
        # A printed page has no breakpoint, and that is a state rather than a
        # missing number.
        assert PageFormat(width=794, height=1123).mobile_breakpoint is None

    def test_a_page_is_its_sheet_and_its_frame_is_what_the_margin_leaves(self) -> None:
        page = PageFormat(794, 1123, margin=PageMargin(top=10, right=20, bottom=30, left=40))
        assert (page.width, page.height) == (794, 1123)
        assert (page.frame_width, page.frame_height) == (794 - 60, 1123 - 40)
        assert PageFormat(680).frame_height is None

    def test_a_zero_margin_is_legal_where_no_other_size_is(self) -> None:
        # The continuous page an email renders into has none.
        assert PageFormat(680).margin == PageMargin(0, 0, 0, 0)

    @pytest.mark.parametrize("bad", [-1, True, "4", 4.0])
    def test_a_margin_refuses_what_a_size_refuses(self, bad: object) -> None:
        with pytest.raises(ValidationError, match="page.margin.left"):
            PageMargin(left=bad)  # type: ignore[arg-type]

    def test_a_margin_that_leaves_no_frame_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="no content width"):
            PageFormat(794, 1123, margin=PageMargin(right=400, left=394))
        with pytest.raises(ValidationError, match="no content height"):
            PageFormat(794, 1123, margin=PageMargin(top=600, bottom=523))

    def test_a_page_margin_is_a_margin(self) -> None:
        with pytest.raises(ValidationError, match="must be a PageMargin"):
            PageFormat(794, 1123, margin=20)  # type: ignore[arg-type]

    def test_the_frame_reports_the_sheet_it_came_from(self) -> None:
        page = PageFormat(794, 1123, margin=PageMargin(top=10, right=20, bottom=30, left=40))
        frame = STANDARD_SIZES.with_page(page).frame
        assert (frame.width, frame.height) == (page.frame_width, page.frame_height)
        assert (frame.sheet_width, frame.sheet_height) == (794, 1123)

    def test_a_page_still_refuses_a_nonsense_dimension(self) -> None:
        with pytest.raises(ValidationError, match="must be positive"):
            PageFormat(width=0)
        with pytest.raises(ValidationError, match="must be positive"):
            PageFormat(width=680, height=-1)

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
                optional = getattr(layer_cls, "OPTIONAL", ())
                for spec in fields(layer_cls):
                    if spec.name in optional:
                        continue  # None is a state here -- a page with no height
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
        with pytest.raises(ValidationError, match="must be a SizeTheme, its name, or a SizeScheme"):
            resolve_size_scheme(28)  # type: ignore[arg-type]

    def test_a_scheme_is_returned_unchanged(self) -> None:
        house = STANDARD_SIZES.derive(space={"content_top": 8})
        assert resolve_size_scheme(house) is house


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


# ----------------------------------------------------------------------
# #41 — the tokens are live, and no scale literal survives
# ----------------------------------------------------------------------

#: The one token that legitimately never appears in rendered HTML.
#:
#: ``narrow_column`` is a threshold, not a size: it *chooses* between
#: ``space.column_pad_x`` and ``space.column_pad_x_narrow`` in Python. Both
#: of those still reach the page — the sentinel frame below is shaped so
#: that some column falls on each side of the threshold, or one of them
#: would go untested.
NEVER_RENDERED = {
    "frame.narrow_column",
    # No template reads a page height yet: an email is continuous. The paged
    # skeleton in #162 is what makes this token live.
    "frame.height",
    # The contact card was removed from the footer region in the Task 2
    # footer rework; these spacing tokens are no longer used in any template.
    "space.footer_contact_top",
    "space.footer_contact_bottom",
    # footer_legal_bottom was split into copyright_bottom in the rework.
    "space.footer_legal_bottom",
    # An email has no sheet, so nothing in it reads a print margin. The paged
    # page sentinel in test_paged.py is what pins this token (#175).
    "frame.margin",
}


#: The page the sentinel renders onto. Wide enough that three sentinel-sized
#: gutters still leave real columns.
#:
#: **The page dimensions are perturbed here rather than in the scheme**, because
#: since #159 the medium owns them and ``with_page`` layers them over whatever
#: the density said. Perturbing the scheme alone would prove nothing: the
#: medium would overwrite it with the shipped 680 and every template would
#: still render the value it always had.
SENTINEL_PAGE = PageFormat(width=20_001, mobile_breakpoint=20_100)


def _sentinel_scheme() -> SizeScheme:
    """
    A scheme in which every token is a distinctive, findable number.

    Sizes count up from 1010 and line-heights from 4.01, so each token's
    value appears in the rendered HTML if and only if some template
    actually reads it. The frame keeps a sane shape — padding inside the
    width, breakpoint outside it — because ``FrameGeometry`` validates
    those relationships and a nonsense frame would fail construction
    rather than prove anything.
    """
    px = iter(range(1010, 1400))
    line = iter(x / 100 for x in range(401, 500))
    layers: dict[str, Any] = {}
    for layer, layer_cls in SizeScheme.LAYERS.items():
        values: dict[str, int | float] = {}
        for spec in fields(layer_cls):
            if spec.name == "margin":
                values[spec.name] = SENTINEL_PAGE.margin
                continue
            values[spec.name] = next(line) if spec.name.endswith("_line") else next(px)
        if layer == "frame":
            # The threshold sits a quarter of the way into the content width,
            # so both column paddings are exercised rather than only the wide
            # one. Width and breakpoint come from SENTINEL_PAGE below.
            pad_x = 1017
            values.update(
                width=SENTINEL_PAGE.width,
                pad_x=pad_x,
                height=None,
                mobile_breakpoint=SENTINEL_PAGE.mobile_breakpoint,
                narrow_column=(SENTINEL_PAGE.width - 2 * pad_x) // 4,
            )
        layers[layer] = layer_cls(**values)
    return SizeScheme(**layers).with_page(SENTINEL_PAGE)


class TestTheTokensAreLive:
    """
    #41's real question: are the tokens wired, or merely present?

    A migration that replaced a literal with a token *nothing reads* would
    be byte-identical and completely inert. Rendering the exhaustive fixture
    under a scheme whose every token is a distinct sentinel answers it
    token by token, and fails naming the one that never arrived.
    """

    @pytest.fixture()
    def perturbed_html(self, monkeypatch: pytest.MonkeyPatch) -> str:
        from qa.fixtures import kitchen_sink
        from svc.builder import sizing

        scheme = _sentinel_scheme()
        monkeypatch.setitem(sizing.SIZE_SCHEMES, SizeTheme.SPACIOUS, scheme)
        builder = kitchen_sink.build()
        # The document's own tokens are under test, and a per-object override
        # (#213) replaces one by design, so the fixture's overrides step aside.
        for section in builder._sections:
            for node in [section, *section.components()]:
                node.spacing = None
        builder._metadata.size_theme = SizeTheme.SPACIOUS  # type: ignore[union-attr]
        # The page is the medium's since #159, so the sentinel has to reach
        # the render the way a real one would rather than through the scheme.
        builder._medium = replace(builder.medium, page_format=SENTINEL_PAGE)
        self.scheme = scheme
        return builder.render()

    @pytest.mark.parametrize(
        "token",
        sorted(
            f"{layer}.{spec.name}"
            for layer, layer_cls in SizeScheme.LAYERS.items()
            for spec in fields(layer_cls)
        ),
    )
    def test_every_token_reaches_the_html(self, token: str, perturbed_html: str) -> None:
        if token in NEVER_RENDERED:
            pytest.skip(f"{token} is resolved in Python, never emitted")
        layer, name = token.split(".")
        value = getattr(getattr(self.scheme, layer), name)
        # A leading token is stored as a ratio and *emitted* as a percentage,
        # because Outlook Classic ignores a unitless line-height (#78). So the
        # sentinel to look for is its CSS form, which also pins that the
        # conversion happens at all.
        expected = percent(value) if name.endswith("_line") else str(value)
        assert expected in perturbed_html, (
            f"{token} = {value} never reached the rendered email as "
            f"{expected!r} — the token is decorative, not wired"
        )

    def test_the_mobile_media_block_is_sized_too(self, perturbed_html: str) -> None:
        """
        The trap the epic named: ``@media`` overrides carrying their own
        literals would leave a themed email desktop-sized and mobile-
        standard. The block must read the same tokens as the inline styles
        it overrides.
        """
        block = perturbed_html[
            perturbed_html.index("@media only screen") : perturbed_html.index(
                "/* Force light rendering"
            )
        ]
        for token in ("space.mobile_pad_y", "space.mobile_pad_x", "type.title_mobile"):
            layer, name = token.split(".")
            assert str(getattr(getattr(self.scheme, layer), name)) in block, token

    def test_the_kpi_collapse_reuses_the_vertical_cards_padding(self, perturbed_html: str) -> None:
        """
        Deliberate sharing, not a coincidence: the mobile collapse *is* the
        vertical card layout, so ``.kpi-cell`` reads ``card_pad_*`` rather
        than a second pair of tokens. #43 depends on this — it is what stops
        a compact email rendering airier on a phone than on a desktop.
        """
        block = perturbed_html[
            perturbed_html.index(".kpi-cell {") : perturbed_html.index(".kpi-cell-last")
        ]
        assert str(self.scheme.component.card_pad_y) in block
        assert str(self.scheme.component.card_pad_x) in block


class TestNoScaleLiteralSurvives:
    """
    The other half of #41: a hardcoded px in a template is a bug.

    Stated as a rule with teeth, the way the colour epic's no-hex-literal
    rule is — the exceptions are named, and anything else fails here rather
    than being noticed in review.
    """

    #: Every literal a template may still carry, and why. See
    #: :mod:`svc.builder.sizing` for the full reasoning.
    DELIBERATE = {
        "padding:1px 1px 1px 1px": "the hairline frame of a highlighted band",
        "font-size:1px": "the preheader hider — not type",
        "font-size:0": "the accent rule's spacer cell",
        "line-height:0": "ditto",
    }

    DECL = re.compile(
        r"(?:font-size|line-height|padding|padding-top|padding-bottom|margin"
        r"|margin-top|margin-bottom|margin-right)\s*:\s*[^;\"}]*"
    )

    def test_every_size_declaration_is_a_token_or_a_named_exception(self) -> None:
        offenders: list[str] = []
        for path in _templates():
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                for decl in self.DECL.findall(line):
                    decl = decl.strip().rstrip(";")
                    if "{{" in decl or not re.search(r"[1-9]", decl):
                        continue  # tokenised, or an all-zero reset
                    if any(decl.startswith(known) for known in self.DELIBERATE):
                        continue
                    offenders.append(f"{path.relative_to(TEMPLATE_DIR)}:{line_no}: {decl}")
        assert not offenders, (
            "hardcoded sizes outside the documented exceptions:\n  " + "\n  ".join(offenders)
        )

    def test_the_named_exceptions_are_all_still_there(self) -> None:
        """
        An exception list that outlives its exception is a lie in the docs.
        """
        blob = "\n".join(p.read_text(encoding="utf-8") for p in _templates())
        for literal in self.DELIBERATE:
            assert literal in blob, f"{literal!r} is documented but no longer used"


# ----------------------------------------------------------------------
# #42 — column geometry is arithmetic, not eight files of literals
# ----------------------------------------------------------------------

RATIOS = ["50-50", "30-70", "70-30", "33-33-33", "50-25-25", "25-50-25", "25-25-50"]

#: What the eight deleted per-ratio templates hardcoded, column by column:
#: the width, and the horizontal cell padding each column carried.
#:
#: The widths still hold exactly. The *padding* is now the value a column
#: takes on its **gutter-facing** sides only — #85 zeroed the outer edges,
#: because the band is inset by ``frame.pad_x`` and padding it twice is what
#: made every multi-column section hang left of its own heading.
THE_OLD_LITERALS: dict[str, list[tuple[int, int]]] = {
    "50-50": [(300, 20), (300, 20)],
    "30-70": [(180, 16), (420, 20)],
    "70-30": [(420, 20), (180, 16)],
    "33-33-33": [(195, 16), (194, 16), (195, 16)],
    "50-25-25": [(292, 16), (146, 16), (146, 16)],
    "25-50-25": [(146, 16), (292, 16), (146, 16)],
    "25-25-50": [(146, 16), (146, 16), (292, 16)],
}


class TestColumnGeometry:
    @pytest.mark.parametrize("ratio", RATIOS)
    def test_it_reproduces_what_the_templates_hardcoded(self, ratio: str) -> None:
        """
        The byte-identity claim, stated as arithmetic.

        Padding included: the 20px / 16px split was never written down as a
        rule, only as a per-file choice, and ``narrow_column`` is that rule
        recovered — a 300 or 420px column had 20, a 292 or smaller one had 16.
        """
        weights = [int(part) for part in ratio.split("-")]
        columns = column_layout(weights, STANDARD_SIZES)
        # The gutter-facing padding of each column: its right for the first,
        # its left for the last, and either for a column with gutters on
        # both sides.
        computed = [
            (c.width, c.pad_left if index else c.pad_right) for index, c in enumerate(columns)
        ]
        assert computed == THE_OLD_LITERALS[ratio]

    @pytest.mark.parametrize("ratio", RATIOS)
    def test_the_outer_edges_carry_no_padding(self, ratio: str) -> None:
        """
        #85. The frame already supplies ``frame.pad_x`` on those two edges;
        padding them again is what put a column's text 12-16px left of the
        heading above it. Every *inner* edge still pads, so the gap between
        two columns is unchanged.
        """
        weights = [int(part) for part in ratio.split("-")]
        columns = column_layout(weights, STANDARD_SIZES)
        assert columns[0].pad_left == 0
        assert columns[-1].pad_right == 0
        for column in columns[1:]:
            assert column.pad_left > 0
        for column in columns[:-1]:
            assert column.pad_right > 0

    @pytest.mark.parametrize("ratio", RATIOS)
    def test_the_gap_between_columns_is_unchanged(self, ratio: str) -> None:
        """
        What #85 moved is the band's *outer* inset, not its internal rhythm:
        two facing paddings plus the gutter, exactly as the deleted
        templates had it.
        """
        weights = [int(part) for part in ratio.split("-")]
        columns = column_layout(weights, STANDARD_SIZES)
        old = THE_OLD_LITERALS[ratio]
        for index in range(len(columns) - 1):
            gap = (
                columns[index].pad_right + STANDARD_SIZES.space.gutter + columns[index + 1].pad_left
            )
            assert gap == old[index][1] + STANDARD_SIZES.space.gutter + old[index + 1][1]

    def test_equal_thirds_put_the_odd_pixels_on_the_outside(self) -> None:
        """
        584px does not divide by three, so two columns gain a pixel — and
        *which* two was already decided by hand, in ``col-33-33-33.html``.
        Outside-in reproduces it and is the better rule anyway: a reader
        notices an asymmetric left/right pair, not a centre column one pixel
        narrower than its neighbours.
        """
        assert [c.width for c in column_layout([33, 33, 33], STANDARD_SIZES)] == [
            195,
            194,
            195,
        ]

    @pytest.mark.parametrize(
        "count,expected", [(1, [0]), (2, [0, 1]), (3, [0, 2, 1]), (4, [0, 3, 1, 2])]
    )
    def test_the_remainder_order_is_outside_in(self, count: int, expected: list[int]) -> None:
        assert _remainder_order(count) == expected

    def test_weights_normalise_by_their_own_sum(self) -> None:
        """
        ``"33-33-33"`` sums to 99, not 100. Normalising by the sum is what
        makes it exact thirds instead of 99% of the frame with a hole in it.
        """
        widths = [c.width for c in column_layout([33, 33, 33], STANDARD_SIZES)]
        assert sum(widths) + 2 * STANDARD_SIZES.space.gutter == STANDARD_SIZES.frame.inner

    @pytest.mark.parametrize("ratio", RATIOS)
    @pytest.mark.parametrize("width", [480, 600, 680, 700, 1024])
    def test_columns_and_gutters_fill_the_frame_exactly(self, ratio: str, width: int) -> None:
        """
        The acceptance criterion at a frame the email has never shipped at.

        Every width a positive integer — Outlook reads the ``width``
        *attribute*, and an attribute cannot be 194.67 — and the columns
        plus their gutters accounting for the content width to the pixel.
        """
        scheme = STANDARD_SIZES.derive(frame={"width": width, "mobile_breakpoint": width + 20})
        weights = [int(part) for part in ratio.split("-")]
        columns = column_layout(weights, scheme)

        assert len(columns) == len(weights)
        assert all(isinstance(c.width, int) and c.width > 0 for c in columns)
        gutters = scheme.space.gutter * (len(columns) - 1)
        assert sum(c.width for c in columns) + gutters == scheme.frame.inner

    def test_an_impossible_frame_is_refused_rather_than_rendered(self) -> None:
        scheme = STANDARD_SIZES.derive(frame={"width": 50, "pad_x": 10})
        with pytest.raises(ValidationError, match="not enough for one pixel each"):
            column_layout([33, 33, 33], scheme)


class TestTheGeometryReachesTheTemplateOnce:
    """
    The attribute and the CSS must come from the *same* number.

    Writing it twice per column, in eight files, is what the epic named as
    the problem — so the test is not "the numbers are right" but "there is
    only one number".
    """

    def _render(self, ratio: str, scheme: SizeScheme | None = None) -> str:
        from svc.builder import TemplateEngine, TextBlock, ThreeColumn, TwoColumn

        engine = TemplateEngine().bound(size=scheme or STANDARD_SIZES)
        slots = [TextBlock(f"<p>{n}</p>") for n in ("a", "b", "c")]
        if ratio.count("-") == 1:
            container = TwoColumn(ratio=ratio, left=slots[0], right=slots[1])
        else:
            container = ThreeColumn(ratio=ratio, left=slots[0], center=slots[1], right=slots[2])
        return container.render(engine)

    @pytest.mark.parametrize("ratio", RATIOS)
    @pytest.mark.parametrize("width", [680, 900])
    def test_attribute_and_css_width_agree_per_column(self, ratio: str, width: int) -> None:
        scheme = STANDARD_SIZES.derive(frame={"width": width, "mobile_breakpoint": width + 20})
        html = self._render(ratio, scheme)
        expected = [c.width for c in column_layout([int(p) for p in ratio.split("-")], scheme)]

        # Each column appears twice in the MSO ghost table (attribute + CSS)
        # and twice on its own inline-block table — four times, one number.
        for column_width in expected:
            attrs = html.count(f'width="{column_width}"')
            css = html.count(f"width:{column_width}px")
            assert attrs == css, (
                f"{ratio} at {width}px: {attrs} attribute(s) but {css} CSS width(s) "
                f"for a {column_width}px column"
            )

    @pytest.mark.parametrize("ratio", RATIOS)
    def test_no_width_literal_survives_in_the_column_template(self, ratio: str) -> None:
        """
        Rendering at a non-shipped frame is the check that bites: a leftover
        literal would still say 300 or 616 while everything around it moved.
        """
        scheme = STANDARD_SIZES.derive(frame={"width": 900, "mobile_breakpoint": 920})
        html = self._render(ratio, scheme)
        for stale in ('width="616"', "width:616px", 'width="300"', 'width="195"'):
            assert stale not in html, f"{stale} survived a frame change"

    def test_the_container_template_carries_no_number(self) -> None:
        source = (TEMPLATE_DIR / "common" / "containers" / "columns.html").read_text(
            encoding="utf-8"
        )
        body = source[source.index("#}") :]  # the docstring comment may cite sizes
        offenders = re.findall(r'width[=:]\s*"?[0-9]+(?![0-9%])', body)
        assert not offenders, f"hardcoded widths in columns.html: {offenders}"

    def test_one_template_serves_every_split(self) -> None:
        from svc.builder import ThreeColumn, TwoColumn

        assert TwoColumn.template_path == ThreeColumn.template_path
        assert not list((TEMPLATE_DIR / "common" / "containers").glob("col-*.html")), (
            "a per-ratio template came back; the ratio selects numbers, not a file"
        )

    def test_the_frame_width_reaches_the_skeleton_and_the_footer(self) -> None:
        from qa.fixtures import kitchen_sink

        builder = kitchen_sink.build()
        builder._metadata.size_theme = SizeTheme.STANDARD  # type: ignore[union-attr]
        html = builder.render()
        assert html.count('width="680"') >= 2  # body table + the legal block
        assert "max-width:680px" in html
        assert "max-width:700px" in html  # the breakpoint, derived from the frame


# ----------------------------------------------------------------------
# #43 — the two shipped alternatives
# ----------------------------------------------------------------------

ALL_THEMES = list(SizeTheme)


class TestTheShippedSchemes:
    def test_every_theme_has_a_scheme(self) -> None:
        """
        The completeness net from #39, now real for all three.

        A ``SizeTheme`` member without a scheme was acceptable inside this
        epic's window and is not acceptable after it: it would be a name a
        caller can pass that fails at construction.
        """
        assert set(SIZE_SCHEMES) == set(SizeTheme)

    @pytest.mark.parametrize("theme", ALL_THEMES)
    def test_every_layer_and_token_is_populated(self, theme: SizeTheme) -> None:
        scheme = SIZE_SCHEMES[theme]
        for layer, layer_cls in SizeScheme.LAYERS.items():
            value = getattr(scheme, layer)
            assert isinstance(value, layer_cls)
            optional = getattr(layer_cls, "OPTIONAL", ())
            for spec in fields(layer_cls):
                token = getattr(value, spec.name)
                if token is None and spec.name in optional:
                    continue
                if isinstance(token, PageMargin):
                    continue  # validated by its own type, where zero is legal
                assert isinstance(token, (int, float)) and token > 0

    @pytest.mark.parametrize("theme", ALL_THEMES)
    def test_selectable_by_bare_string(self, theme: SizeTheme) -> None:
        from svc.builder.models import EmailMetadata

        assert (
            resolve_size_scheme(EmailMetadata(size_theme=theme.value).size_theme)
            is (SIZE_SCHEMES[theme])
        )

    def test_a_registered_theme_without_a_scheme_still_says_so(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        The guard #39 left in place, exercised rather than assumed. It
        matters again the moment a fourth member is added ahead of its
        values.
        """
        from svc.builder import sizing

        monkeypatch.delitem(sizing.SIZE_SCHEMES, SizeTheme.SPACIOUS)
        with pytest.raises(ValidationError, match="has no scheme yet"):
            resolve_size_scheme("spacious")

    def test_the_registry_is_not_mutated_at_runtime(self) -> None:
        before = dict(SIZE_SCHEMES)
        resolve_size_scheme("compact")
        resolve_size_scheme(SizeTheme.SPACIOUS)
        assert SIZE_SCHEMES == before


class TestTheSchemesAreCuratedNotScaled:
    """
    The epic's word was *curated*, and that is checkable.

    A multiplier would be cheaper to write and worse to read: it would
    shrink fine print below legibility, scale leading linearly with type
    when leading should move the other way, and treat a KPI number as
    ordinary body copy.
    """

    def test_no_single_multiplier_explains_a_theme(self) -> None:
        from svc.builder.sizing import COMPACT_SIZES

        ratios = {
            round(
                getattr(COMPACT_SIZES.type, spec.name) / getattr(STANDARD_SIZES.type, spec.name),
                3,
            )
            for spec in fields(TypeScale)
        }
        assert len(ratios) > 1, "the type scale is a single multiplier, not a curation"

    def test_fine_print_holds_at_the_readability_floor_in_compact(self) -> None:
        from svc.builder.sizing import COMPACT_SIZES

        assert COMPACT_SIZES.type.micro == STANDARD_SIZES.type.micro == 9.5
        assert COMPACT_SIZES.type.label == STANDARD_SIZES.type.label == 10

    def test_leading_does_not_track_type_linearly(self) -> None:
        from svc.builder.sizing import COMPACT_SIZES

        type_drop = COMPACT_SIZES.type.body / STANDARD_SIZES.type.body
        leading_drop = COMPACT_SIZES.type.body_line / STANDARD_SIZES.type.body_line
        assert leading_drop > type_drop, "smaller type needs proportionally more leading, not less"

    def test_the_kpi_value_gives_up_the_least(self) -> None:
        from svc.builder.sizing import COMPACT_SIZES

        kpi = COMPACT_SIZES.component.kpi_value / STANDARD_SIZES.component.kpi_value
        title = COMPACT_SIZES.type.title / STANDARD_SIZES.type.title
        assert kpi > title, "a KPI strip exists to be read across a room"

    def test_every_theme_keeps_the_shipped_frame_width(self) -> None:
        """
        An epic non-goal, stated as a test. Density is not width: a
        narrow-frame theme is a separate, deliberate decision with its own
        client-testing burden and its own interplay with image ``width=``.
        """
        for theme, scheme in SIZE_SCHEMES.items():
            assert scheme.frame.width == 680, theme

    def test_dense_holds_fine_print_at_the_print_floor(self) -> None:
        """#211: label and micro may move in print, and never below 8px (6pt)."""
        from svc.builder.sizing import DENSE_SIZES

        assert min(DENSE_SIZES.type.label, DENSE_SIZES.type.micro) >= 8
        assert DENSE_SIZES.type.micro < STANDARD_SIZES.type.micro

    def test_dense_tightens_leading_less_than_type(self) -> None:
        from svc.builder.sizing import COMPACT_SIZES, DENSE_SIZES

        type_drop = DENSE_SIZES.type.body / COMPACT_SIZES.type.body
        leading_drop = DENSE_SIZES.type.body_line / COMPACT_SIZES.type.body_line
        assert leading_drop > type_drop

    def test_dense_gives_up_the_kpi_value_least(self) -> None:
        from svc.builder.sizing import COMPACT_SIZES, DENSE_SIZES

        kpi = DENSE_SIZES.component.kpi_value / COMPACT_SIZES.component.kpi_value
        body = DENSE_SIZES.type.body / COMPACT_SIZES.type.body
        assert kpi > body

    def test_dense_is_denser_than_compact_everywhere_it_decides(self) -> None:
        """Written as a derive of compact, so no token it sets may be roomier."""
        from svc.builder.sizing import COMPACT_SIZES, DENSE_SIZES

        for layer in ("type", "space", "component"):
            for spec in fields(SizeScheme.LAYERS[layer]):
                dense = getattr(getattr(DENSE_SIZES, layer), spec.name)
                compact = getattr(getattr(COMPACT_SIZES, layer), spec.name)
                assert dense <= compact, f"{layer}.{spec.name}"

    def test_spacious_moves_the_narrow_column_threshold_down(self) -> None:
        """
        The one token that moves the *other* way in the roomiest theme, and
        the clearest evidence these were curated rather than scaled. A 24px
        gutter puts a two-up split at 288px; holding the threshold at 300
        would have given the airiest theme the tightest column padding.
        """
        from svc.builder.sizing import SPACIOUS_SIZES

        two_up = column_layout([50, 50], SPACIOUS_SIZES)
        assert two_up[0].width < STANDARD_SIZES.frame.narrow_column
        # The gutter-facing side: the outer edge is zero for every theme.
        assert two_up[0].pad_right == SPACIOUS_SIZES.space.column_pad_x
        assert two_up[0].pad_right > STANDARD_SIZES.space.column_pad_x


class TestEveryThemeRendersAWholeEmail:
    @pytest.fixture(params=[t.value for t in SizeTheme if t not in PRINT_DENSITIES])
    def rendered(self, request: pytest.FixtureRequest) -> tuple[SizeScheme, str]:
        from qa.fixtures import kitchen_sink

        theme = SizeTheme(request.param)
        html = kitchen_sink.build(size_theme=theme).render()
        return SIZE_SCHEMES[theme], html

    def test_it_renders_and_passes_the_size_check(self, rendered: tuple[SizeScheme, str]) -> None:
        """
        ``render()`` applies the 102 KB limit itself, so reaching this
        assertion at all means the density did not push the document over.
        """
        _, html = rendered
        assert html.startswith("<!DOCTYPE html>")
        assert len(html.encode()) < 102 * 1024

    def test_its_sentinels_appear(self, rendered: tuple[SizeScheme, str]) -> None:
        scheme, html = rendered
        for token in ("type.body", "type.title", "space.gutter", "component.kpi_value"):
            layer, name = token.split(".")
            assert str(getattr(getattr(scheme, layer), name)) in html, token

    def test_its_columns_still_fill_the_frame(self, rendered: tuple[SizeScheme, str]) -> None:
        scheme, _ = rendered
        for ratio in RATIOS:
            columns = column_layout([int(p) for p in ratio.split("-")], scheme)
            gutters = scheme.space.gutter * (len(columns) - 1)
            assert sum(c.width for c in columns) + gutters == scheme.frame.inner

    def test_the_mobile_collapse_is_never_airier_than_the_desktop_cell(
        self, rendered: tuple[SizeScheme, str]
    ) -> None:
        """
        #43's mobile-coherence criterion, and the reason ``.kpi-cell`` reads
        ``card_pad_*`` rather than tokens of its own: on a phone a KPI strip
        *becomes* the vertical card layout, so it must be padded like one.
        """
        scheme, html = rendered
        block = html[html.index(".kpi-cell {") : html.index(".kpi-cell-last")]
        expected = f"padding:{scheme.component.card_pad_y}px {scheme.component.card_pad_x}px"
        assert expected in block


class TestTheCallerFacingSurfaceStaysClosed:
    def test_size_theme_is_the_whole_of_it(self) -> None:
        """
        No per-component size parameter appeared anywhere in this epic. A
        ``font_size=`` on a call site would dissolve the design system one
        component at a time, exactly as a ``title_color=`` would have
        dissolved the palette.
        """
        import inspect

        import svc.builder as builder

        banned = ("font_size", "line_height", "padding", "size_px", "width_px")
        offenders: list[str] = []
        for name in builder.__all__:
            obj = getattr(builder, name)
            if not inspect.isclass(obj):
                continue
            try:
                parameters = inspect.signature(obj).parameters
            except (TypeError, ValueError):  # pragma: no cover - builtins
                continue
            offenders += [f"{name}({parameter})" for parameter in parameters if parameter in banned]
        assert not offenders, f"per-call-site size parameters appeared: {offenders}"

    def test_a_scheme_object_is_accepted_as_a_size_theme(self) -> None:
        """
        Superseded by #212: the narrow rule recorded that widening was
        additive, and this is that widening. The reason it existed survives
        as a gate on the email medium, pinned in ``test_spacing.py``.
        """
        from svc.builder.models import EmailMetadata

        house = STANDARD_SIZES.derive(space={"content_top": 8})
        assert EmailMetadata(size_theme=house).size_theme is house
