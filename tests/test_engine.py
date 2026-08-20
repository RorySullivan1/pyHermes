"""
TemplateEngine — loading, StrictUndefined behavior, and error wrapping.

Everything Jinja2 raises should surface as TemplateError so callers can
catch EmailBuilderError for anything the builder rejected.
"""

import pytest

from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import EmailBuilderError, TemplateError


class TestConstruction:
    def test_defaults_to_the_repo_templates_dir(self, engine):
        assert engine.template_dir.is_dir()
        assert (engine.template_dir / "base.html").is_file()

    def test_missing_template_dir_raises(self, tmp_path):
        with pytest.raises(TemplateError, match="Template directory not found"):
            TemplateEngine(tmp_path / "does-not-exist")

    def test_accepts_an_explicit_dir(self, tmp_path):
        (tmp_path / "x.html").write_text("hi")
        assert TemplateEngine(tmp_path).render("x.html", {}) == "hi"


class TestEnvironmentConfiguration:
    def test_autoescape_is_off(self, engine):
        # HTML emails need raw output; callers pre-escape their own text.
        assert engine.environment.autoescape is False
        assert engine.render_string("{{ v }}", {"v": "<b>x</b>"}) == "<b>x</b>"

    def test_custom_filters_are_registered(self, engine):
        for name in ("validate_hex_color", "size_kb", "default_color"):
            assert name in engine.environment.filters


class TestErrorWrapping:
    def test_missing_template_raises_template_error(self, engine):
        with pytest.raises(TemplateError, match="Template not found"):
            engine.get_template("nope/missing.html")

    def test_render_of_missing_template_raises_template_error(self, engine):
        with pytest.raises(TemplateError, match="Template not found"):
            engine.render("nope/missing.html", {})

    def test_missing_context_variable_raises_template_error(self, engine):
        # StrictUndefined: a template variable with no matching context key
        # must fail loudly rather than rendering an empty string.
        with pytest.raises(TemplateError):
            engine.render_string("{{ never_supplied }}", {})

    def test_undefined_name_raises_even_inside_an_if(self, engine):
        # The exact hazard behind #5 and #15: testing an *undefined* name for
        # truthiness raises under StrictUndefined; it does not read as falsey.
        with pytest.raises(TemplateError):
            engine.render_string("{% if never_supplied %}x{% endif %}", {})

    def test_defined_falsey_value_is_fine_inside_an_if(self, engine):
        # ...which is why the fix injects the key with an empty default.
        assert engine.render_string("{% if v %}x{% endif %}", {"v": ""}) == ""

    def test_template_errors_are_catchable_as_the_base_class(self, engine):
        with pytest.raises(EmailBuilderError):
            engine.render("nope/missing.html", {})

    def test_error_message_names_the_template(self, engine):
        with pytest.raises(TemplateError, match="base.html"):
            engine.render("base.html", {})  # skeleton needs many vars


class TestFilters:
    def test_validate_hex_color_passes_valid(self, engine):
        assert engine.render_string("{{ c | validate_hex_color }}", {"c": "#4A7C59"}) == "#4A7C59"

    def test_validate_hex_color_rejects_invalid(self, engine):
        # Documents CURRENT behavior: the filter raises a bare ValueError,
        # which is not a jinja2.TemplateError, so the engine's except clause
        # does not wrap it.  See the xfail below for the contract this breaks.
        with pytest.raises(ValueError, match="Invalid hex color"):
            engine.render_string("{{ c | validate_hex_color }}", {"c": "red"})

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Known defect, not yet filed: filters.py raises bare ValueError, so a "
            "bad color in a template escapes the documented 'catch EmailBuilderError "
            "for anything the builder rejected' contract. Same defect class as #8, "
            "which fixed it for TwoColumn's ratio. Remove this marker when fixed."
        ),
    )
    def test_filter_errors_should_be_catchable_as_the_base_class(self, engine):
        with pytest.raises(EmailBuilderError):
            engine.render_string("{{ c | validate_hex_color }}", {"c": "red"})

    @pytest.mark.xfail(strict=True, reason="Same bare-ValueError defect as above.")
    def test_default_color_errors_should_be_catchable_as_the_base_class(self, engine):
        with pytest.raises(EmailBuilderError):
            engine.render_string("{{ c | default_color }}", {"c": "not-a-color"})

    def test_default_color_falls_back(self, engine):
        assert engine.render_string("{{ c | default_color }}", {"c": ""}) == "#5A5A5A"

    def test_size_kb_measures_utf8_bytes(self, engine):
        # "é" is 2 bytes in UTF-8, so 512 of them is exactly 1 KB.
        assert engine.render_string("{{ s | size_kb }}", {"s": "é" * 512}) == "1.0"
