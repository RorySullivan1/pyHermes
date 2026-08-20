"""
Container geometry, optional-title handling, and column rules.

The title-less and single-column cases are regression tests: both raised
TemplateError before the fixes for #15 and #5, because a context key that
is injected only conditionally is *undefined* under StrictUndefined — and
an undefined name raises even when it is only tested for truthiness.
"""

import pytest

from svc.builder import FullWidth, TwoColumn
from svc.builder.containers import Container
from svc.builder.exceptions import EmailBuilderError, ValidationError

RATIOS = ["50-50", "30-70", "70-30"]


class TestFullWidth:
    def test_renders_with_title(self, engine, text_block):
        html = FullWidth(content=text_block, title="Market Snapshot").render(engine)
        assert "Market Snapshot" in html
        assert "Narrative prose." in html

    def test_renders_without_title(self, engine, text_block):
        # Regression: #15
        html = FullWidth(content=text_block).render(engine)
        assert "Narrative prose." in html

    def test_background_color_reaches_the_html(self, engine, text_block):
        html = FullWidth(content=text_block, background_color="#ABCDEF").render(engine)
        assert "#ABCDEF" in html


class TestHighlightProperty:
    """`highlight` is a property of any container, not a container type (#Card rework)."""

    def test_off_by_default(self, engine, text_block):
        html = FullWidth(content=text_block, title="T").render(engine)
        assert "border-top:1px solid #D6D2CB" not in html
        assert "#F8F7F5" not in html

    def test_on_adds_tint_and_hairline_rules(self, engine, text_block):
        html = FullWidth(content=text_block, title="T", highlight=True).render(engine)
        assert "border-top:1px solid #D6D2CB" in html
        assert "border-bottom:1px solid #D6D2CB" in html
        assert "#F8F7F5" in html

    def test_explicit_background_beats_the_highlight_tint(self, engine, text_block):
        html = FullWidth(content=text_block, highlight=True, background_color="#EEF5FF").render(
            engine
        )
        assert "#EEF5FF" in html
        assert "#F8F7F5" not in html

    @pytest.mark.parametrize("ratio", RATIOS)
    def test_available_on_two_column_too(self, engine, text_block, ratio):
        # It lives on the base Container, so every container gets it.
        html = TwoColumn(ratio=ratio, left=text_block, right=text_block, highlight=True).render(
            engine
        )
        assert "border-top:1px solid #D6D2CB" in html

    def test_injected_into_context_even_when_false(self, engine):
        # StrictUndefined: the templates gate on it, so it must always be present.
        assert Container()._base_context(engine)["highlight"] is False


class TestTwoColumn:
    @pytest.mark.parametrize("ratio", RATIOS)
    def test_each_ratio_renders(self, engine, text_block, ratio):
        html = TwoColumn(ratio=ratio, left=text_block, right=text_block).render(engine)
        assert html.count("Narrative prose.") == 2

    @pytest.mark.parametrize("ratio", RATIOS)
    def test_each_ratio_renders_without_title(self, engine, text_block, ratio):
        # Regression: #15 — all three ratio templates shared the bug.
        TwoColumn(ratio=ratio, left=text_block, right=text_block).render(engine)

    def test_default_ratio_is_50_50(self, text_block):
        assert TwoColumn(left=text_block).ratio == "50-50"

    @pytest.mark.parametrize("omitted", ["left", "right"])
    def test_one_column_may_be_omitted(self, engine, text_block, omitted):
        # Regression: #5 — Optional[Component] advertised None as valid
        # while passing None crashed the render.
        kwargs = {"left": text_block, "right": text_block}
        kwargs[omitted] = None
        html = TwoColumn(**kwargs).render(engine)
        assert html.count("Narrative prose.") == 1

    def test_both_columns_omitted_is_rejected(self):
        with pytest.raises(ValidationError, match="at least one"):
            TwoColumn(left=None, right=None)

    def test_unsupported_ratio_raises_validation_error(self, text_block):
        # Regression: #8 — this used to be a bare ValueError, escaping the
        # documented "catch EmailBuilderError for anything rejected" contract.
        with pytest.raises(ValidationError, match="Unsupported ratio"):
            TwoColumn(ratio="bogus", left=text_block)

    def test_unsupported_ratio_is_catchable_as_the_base_class(self, text_block):
        with pytest.raises(EmailBuilderError):
            TwoColumn(ratio="bogus", left=text_block)

    def test_ratio_error_lists_the_supported_values(self, text_block):
        with pytest.raises(ValidationError) as exc:
            TwoColumn(ratio="bogus", left=text_block)
        for ratio in RATIOS:
            assert ratio in str(exc.value)


class TestContainerBase:
    @pytest.mark.parametrize("color", ["not-a-color", "#GGGGGG", "4A7C59", "#4A7C5"])
    def test_invalid_background_color_raises(self, text_block, color):
        # Regression: #8 — background_color bypassed hex validation entirely
        # and flowed unchecked into the rendered CSS.
        with pytest.raises(ValidationError, match="hex color"):
            FullWidth(content=text_block, background_color=color)

    def test_background_color_is_optional(self, text_block):
        FullWidth(content=text_block, background_color=None)

    def test_title_defaults_to_empty_string_in_context(self, engine):
        # The templates gate on {% if section_title %}, so the key must be
        # present-and-falsey rather than absent.
        assert Container()._base_context(engine)["section_title"] == ""

    def test_base_render_is_abstract(self, engine):
        with pytest.raises(NotImplementedError):
            Container().render(engine)
