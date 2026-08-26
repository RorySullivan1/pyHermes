"""
The colour vocabulary — the frozen Theme and the audit it encodes.

Covers epic #46's first step (#47). Nothing renders from these tokens yet;
what is pinned here is that the vocabulary is complete, immutable, validated,
and that it composes today's exact ``rgba()`` strings — because byte-identity
at the default theme is the bar every later step of the epic is judged on.
"""

import dataclasses
import re
from pathlib import Path

import pytest

from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.theming import (
    DEFAULT_THEME,
    THEMES,
    Palette,
    Rgba,
    SemanticColors,
    ShadowStyle,
    TextColors,
    Theme,
)

TEMPLATE_DIR = TemplateEngine().template_dir

LAYERS = [Palette, TextColors, SemanticColors]


def _template_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(TEMPLATE_DIR.rglob("*.html")))


class TestTheLayersAreATightVocabulary:
    @pytest.mark.parametrize("layer", [*LAYERS, ShadowStyle, Theme, Rgba])
    def test_every_layer_is_frozen(self, layer):
        assert layer.__dataclass_params__.frozen

    def test_a_theme_cannot_be_mutated(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            DEFAULT_THEME.palette.surface = "#000000"

    def test_a_theme_is_hashable(self):
        """Frozen all the way down — so a theme can key a cache or a set."""
        assert len({DEFAULT_THEME, Theme()}) == 1

    @pytest.mark.parametrize("layer", LAYERS)
    def test_no_token_field_is_optional(self, layer):
        """
        Completeness by construction is the ``StrictUndefined`` safety net:
        a theme that exists is a theme that renders. A token typed
        ``str | None`` would move that failure to render time.
        """
        for spec in dataclasses.fields(layer):
            assert spec.type == "str", f"{layer.__name__}.{spec.name} is not a plain token"
            assert spec.default is not dataclasses.MISSING

    def test_the_theme_is_exactly_four_layers(self):
        assert [f.name for f in dataclasses.fields(Theme)] == [
            "palette",
            "text",
            "semantic",
            "shadow",
        ]


class TestValidationHappensAtConstruction:
    @pytest.mark.parametrize("bad", ["red", "#FFF", "#GGGGGG", "5B8A9A", ""])
    def test_a_bad_hex_is_rejected(self, bad):
        with pytest.raises(ValidationError, match=r"palette\.surface"):
            Palette(surface=bad)

    def test_the_message_names_the_layer_and_the_token(self):
        with pytest.raises(ValidationError, match=r"text\.on_dark_muted"):
            TextColors(on_dark_muted="nope")
        with pytest.raises(ValidationError, match=r"semantic\.negative"):
            SemanticColors(negative="nope")

    @pytest.mark.parametrize("bad", [-0.1, 1.5, 2])
    def test_an_out_of_range_alpha_is_rejected(self, bad):
        with pytest.raises(ValidationError, match=r"shadow\.alpha"):
            Rgba("#000000", bad)

    def test_a_non_numeric_alpha_is_rejected(self):
        with pytest.raises(ValidationError, match=r"shadow\.alpha"):
            Rgba("#000000", "0.5")  # type: ignore[arg-type]

    def test_a_wrong_layer_type_is_rejected(self):
        with pytest.raises(ValidationError, match=r"theme\.palette"):
            Theme(palette=TextColors())  # type: ignore[arg-type]
        with pytest.raises(ValidationError, match=r"shadow\.scrim"):
            ShadowStyle(scrim="rgba(0,0,0,0.5)")  # type: ignore[arg-type]

    def test_the_boundaries_are_allowed(self):
        assert Rgba("#000000", 0).alpha == 0
        assert Rgba("#000000", 1).alpha == 1


class TestTheRgbaFormattingContract:
    """
    The trap the epic named: composing ``rgba()`` from parts must reproduce
    today's exact decimal formatting, or every golden moves.
    """

    @pytest.mark.parametrize(
        ("shadow", "expected"),
        [
            ("scrim", "rgba(20,30,44,0.65)"),
            ("title", "rgba(0,0,0,0.4)"),
            ("subtitle", "rgba(0,0,0,0.3)"),
        ],
    )
    def test_it_reproduces_the_shipped_literal(self, shadow, expected):
        assert getattr(DEFAULT_THEME.shadow, shadow).css == expected

    @pytest.mark.parametrize("shadow", ["scrim", "title", "subtitle"])
    def test_the_shipped_literal_is_still_in_the_templates(self, shadow):
        """
        Reads the other way round too: if someone edits a template's rgba,
        this fails here rather than silently making the token a fiction.
        """
        assert getattr(DEFAULT_THEME.shadow, shadow).css in _template_text()

    def test_no_trailing_zeros(self):
        assert Rgba("#000000", 0.50).css == "rgba(0,0,0,0.5)"
        assert Rgba("#000000", 1.0).css == "rgba(0,0,0,1)"
        assert Rgba("#000000", 0.0).css == "rgba(0,0,0,0)"

    def test_it_stringifies_to_its_css(self):
        """So a template writes ``{{ theme.shadow.scrim }}``, not ``.css``."""
        assert f"{DEFAULT_THEME.shadow.scrim}" == DEFAULT_THEME.shadow.scrim.css

    def test_lowercase_hex_still_composes(self):
        assert Rgba("#141e2c", 0.65).css == "rgba(20,30,44,0.65)"


class TestTheAuditIsTrue:
    """
    Each default is a claim about the templates. These check the claim, so
    the docstring table cannot rot into the palette comment it replaces.
    """

    @pytest.mark.parametrize("layer_name", ["palette", "text", "semantic"])
    def test_every_token_value_is_valid_hex(self, layer_name):
        layer = getattr(DEFAULT_THEME, layer_name)
        for spec in dataclasses.fields(layer):
            assert re.fullmatch(r"#[0-9A-F]{6}", getattr(layer, spec.name)), (
                f"{layer_name}.{spec.name} is not uppercase #RRGGBB — the templates "
                "emit uppercase today, and the migration must match byte for byte."
            )

    @pytest.mark.parametrize("layer_name", ["palette", "text"])
    def test_every_surface_and_text_token_is_in_the_templates(self, layer_name):
        """
        ``semantic`` is exempt and the docstring says why: ``positive`` and
        ``negative`` have no render site today — they are the published
        vocabulary, carried by callers' own data.
        """
        text = _template_text()
        layer = getattr(DEFAULT_THEME, layer_name)
        for spec in dataclasses.fields(layer):
            value = getattr(layer, spec.name)
            assert value in text, f"{layer_name}.{spec.name} ({value}) renders nowhere"

    def test_the_audit_covers_every_hex_the_templates_use(self):
        """
        The completeness half: a colour in a template with no token is one
        the migration would have to leave hardcoded.
        """
        used = set(re.findall(r"#[0-9A-Fa-f]{6}", _template_text()))
        known = {
            getattr(layer, spec.name)
            for layer in (DEFAULT_THEME.palette, DEFAULT_THEME.text, DEFAULT_THEME.semantic)
            for spec in dataclasses.fields(layer)
        } | {DEFAULT_THEME.shadow.scrim.color}
        # The palette comment in base.html is the one place a hex appears
        # that no token needs to cover; #49 deletes it.
        comment_only = {"#F5F4F1"}
        assert used - known - comment_only == set()

    def test_the_stale_palette_comment_value_is_used_nowhere_real(self):
        """
        The audit's headline finding: the comment claimed row-alt was
        ``#F5F4F1``; the table actually alternates with ``#F8F7F5``.
        """
        base = (TEMPLATE_DIR / "base.html").read_text(encoding="utf-8")
        assert base.count("#F5F4F1") == 1  # the comment line, and nothing else
        assert DEFAULT_THEME.palette.row_alt == "#F8F7F5"
        assert DEFAULT_THEME.palette.row_alt in (
            (TEMPLATE_DIR / "analysis" / "data-table.html").read_text(encoding="utf-8")
        )

    def test_row_alt_and_highlight_tint_are_separate_tokens(self):
        """Same value today, different roles — recorded as a decision."""
        names = {f.name for f in dataclasses.fields(Palette)}
        assert {"row_alt", "highlight_tint"} <= names
        assert DEFAULT_THEME.palette.row_alt == DEFAULT_THEME.palette.highlight_tint
        assert Palette(row_alt="#123456").highlight_tint == "#F8F7F5"

    def test_rule_dark_matches_the_header_by_design(self):
        assert DEFAULT_THEME.palette.rule_dark == DEFAULT_THEME.palette.header_bg
        assert Palette(header_bg="#123456").rule_dark == "#2C3E50"


class TestThePresetRegistry:
    def test_classic_is_the_default_theme(self):
        assert THEMES["classic"] is DEFAULT_THEME

    def test_the_default_theme_is_a_default_construction(self):
        assert DEFAULT_THEME == Theme()

    def test_the_python_side_fallbacks_are_covered(self):
        """
        The three literals #49 has to remove from Python live in the theme
        now: ``Card.color``'s default, ``default_color``'s fallback, and the
        data-table's cell fallback are all the neutral.
        """
        from svc.builder.filters import default_color
        from svc.builder.models import Card

        assert DEFAULT_THEME.semantic.neutral == "#5A5A5A"
        assert Card("L", "V").color == DEFAULT_THEME.semantic.neutral
        assert default_color("") == DEFAULT_THEME.semantic.neutral


class TestNothingRendersFromItYet:
    def test_no_module_imports_theming(self):
        """
        #47 is inert by construction. The import lands in #48, and this test
        is what makes "zero rendering change" checkable rather than asserted.
        """
        package = Path(TEMPLATE_DIR).parent
        importers = [
            path.name
            for path in sorted(package.glob("*.py"))
            if path.name != "theming.py" and "theming" in path.read_text(encoding="utf-8")
        ]
        assert importers == [], f"{importers} already reach for the theme; #47 is inert"
