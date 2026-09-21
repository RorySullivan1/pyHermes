"""
TemplateEngine — loading, StrictUndefined behavior, and error wrapping.

Everything Jinja2 raises should surface as TemplateError so callers can
catch EmailBuilderError for anything the builder rejected.
"""

from pathlib import Path

import pytest

from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import EmailBuilderError, TemplateError, ValidationError


class TestConstruction:
    def test_defaults_to_the_packaged_templates_dir(self, engine):
        assert engine.template_dir.is_dir()
        assert (engine.template_dir / "base.html").is_file()

    def test_templates_live_inside_the_package(self, engine):
        # Regression: #10 — templates used to sit at the repo root and were
        # resolved by walking up three parents, so they were absent from a
        # wheel install. They must resolve *inside* svc/builder for the
        # package to be installable without a source tree.
        import svc.builder

        package_dir = Path(svc.builder.__file__).resolve().parent
        assert engine.template_dir.is_relative_to(package_dir)

    def test_all_templates_are_packaged(self, engine):
        # Every template the components reference must ship with the package.
        expected = {
            "base.html",
            "analysis/card-group.html",
            "analysis/data-table.html",
            "analysis/chart-block.html",
            "text/text-block.html",
            "text/numbered-list.html",
            "text/author-block.html",
            "media/image-block.html",
            "regions/header-bar.html",
            "regions/banner.html",
            "regions/banner-minimal.html",
            "regions/footer.html",
            "common/containers/full-width.html",
            # One file for every split since #42; the eight per-ratio
            # templates it replaced differed only in a comment and the
            # numbers, and the numbers are computed now.
            "common/containers/columns.html",
        }
        missing = {t for t in expected if not (engine.template_dir / t).is_file()}
        assert not missing, f"templates missing from the package: {sorted(missing)}"

    def test_missing_template_dir_raises(self, tmp_path):
        with pytest.raises(TemplateError, match="Template directory not found"):
            TemplateEngine(tmp_path / "does-not-exist")

    def test_accepts_an_explicit_dir(self, tmp_path):
        (tmp_path / "x.html").write_text("hi")
        assert TemplateEngine(tmp_path).render("x.html", {}) == "hi"


class TestTheMediumScopedSearchPath:
    """
    #160: a medium forks one template without forking the tree.

    The mechanism is a ChoiceLoader whose overlays come first. It ships
    switched on and doing nothing — the email medium declares a directory
    that does not exist — so the fall-through is exercised by every render
    in the suite and a fork is a file, not a migration.
    """

    @pytest.fixture()
    def tree(self, tmp_path: Path) -> Path:
        (tmp_path / "text").mkdir()
        (tmp_path / "text" / "block.html").write_text("shared", encoding="utf-8")
        (tmp_path / "paged" / "text").mkdir(parents=True)
        (tmp_path / "paged" / "text" / "block.html").write_text("forked", encoding="utf-8")
        return tmp_path

    def test_an_overlay_shadows_the_shared_template(self, tree):
        engine = TemplateEngine(tree, search_path=("paged",))
        assert engine.render("text/block.html", {}) == "forked"

    def test_the_fork_is_invisible_without_the_search_path(self, tree):
        # The half that makes a fork safe: one medium's markup cannot leak
        # into another's just by existing.
        assert TemplateEngine(tree).render("text/block.html", {}) == "shared"

    def test_a_medium_falls_through_for_what_it_has_not_forked(self, tree):
        (tree / "other.html").write_text("only shared", encoding="utf-8")
        engine = TemplateEngine(tree, search_path=("paged",))
        assert engine.render("other.html", {}) == "only shared"

    def test_a_search_path_with_no_directory_behind_it_is_not_an_error(self, tree):
        # What a medium that has forked nothing looks like -- including the
        # shipped email one, whose directory does not exist.
        engine = TemplateEngine(tree, search_path=("nothing-here",))
        assert engine.render("text/block.html", {}) == "shared"

    def test_earlier_entries_win(self, tree):
        (tree / "first" / "text").mkdir(parents=True)
        (tree / "first" / "text" / "block.html").write_text("first", encoding="utf-8")
        engine = TemplateEngine(tree, search_path=("first", "paged"))
        assert engine.render("text/block.html", {}) == "first"

    def test_the_root_is_still_the_template_dir(self, tree):
        # Everything that locates a template by path -- the packaging test,
        # the golden harness -- reads this, and an overlay must not move it.
        assert TemplateEngine(tree, search_path=("paged",)).template_dir == tree.resolve()


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
        # Regression: #18 — this used to be a bare ValueError.
        with pytest.raises(ValidationError, match="invalid hex color"):
            engine.render_string("{{ c | validate_hex_color }}", {"c": "red"})

    def test_validate_hex_color_rejects_non_strings(self, engine):
        with pytest.raises(ValidationError, match="must be a string"):
            engine.render_string("{{ c | validate_hex_color }}", {"c": 123})

    def test_filter_errors_are_catchable_as_the_base_class(self, engine):
        # The contract CLAUDE.md states: catch EmailBuilderError for anything
        # the builder rejected. A bare ValueError escaped it (#18).
        with pytest.raises(EmailBuilderError):
            engine.render_string("{{ c | validate_hex_color }}", {"c": "red"})

    def test_default_color_errors_are_catchable_as_the_base_class(self, engine):
        with pytest.raises(EmailBuilderError):
            engine.render_string(
                "{{ c | default_color(theme.semantic.neutral) }}", {"c": "not-a-color"}
            )

    def test_default_color_validates_its_fallback(self, engine):
        with pytest.raises(ValidationError):
            engine.render_string("{{ c | default_color('nope') }}", {"c": ""})

    def test_filter_errors_propagate_as_validation_not_template_errors(self, engine):
        # A deliberate choice (#18): a bad colour is a *data* failure, so it
        # surfaces as ValidationError rather than being re-wrapped as
        # TemplateError by engine.render. Both satisfy the base-class
        # contract; this pins which one callers actually see.
        with pytest.raises(ValidationError):
            engine.render_string("{{ c | validate_hex_color }}", {"c": "red"})
        assert not issubclass(ValidationError, TemplateError)

    def test_default_color_falls_back(self, engine):
        # The fallback is a required argument since #49: a filter is handed a
        # theme's colour, it never reaches for one globally.
        rendered = engine.render_string(
            "{{ c | default_color(theme.semantic.neutral) }}", {"c": ""}
        )
        assert rendered == "#5A5A5A"

    def test_size_kb_measures_utf8_bytes(self, engine):
        # "é" is 2 bytes in UTF-8, so 512 of them is exactly 1 KB.
        assert engine.render_string("{{ s | size_kb }}", {"s": "é" * 512}) == "1.0"
