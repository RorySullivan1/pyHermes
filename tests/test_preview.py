"""
The ``preview`` CLI (#61).

It composes the gallery (#57), the lint pass (#60) and the screenshot runner
(#59), so what is worth testing here is the *seams* — target resolution, the
exit codes a shell will branch on, and the error paths — rather than re-testing
the three tools it calls.

Only the capture test needs a browser; everything else runs in the core suite,
which stays browser-free by design.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pyhermes.builder import Email
from pyhermes.builder.exceptions import ValidationError
from qa.fixtures import all_brochure_fixtures, all_fixtures, all_paged_fixtures
from qa.preview import (
    EXIT_BUILD_FAILED,
    EXIT_LINT_ERRORS,
    EXIT_OK,
    PreviewError,
    main,
    resolve,
)
from qa.screenshots import available

requires_browser = pytest.mark.skipif(
    not available(),
    reason='no browser; screenshots are the optional "[qa]" extra',
)


def write_module(directory: Path, name: str, body: str) -> Path:
    path = directory / f"{name}.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


VALID_METADATA = '{"email_subject": "S", "firm_name": "F", "campaign_name": "c"}'

RETURNS_EMAIL = f"""
    from pyhermes.builder import Email, FullWidth, TextBlock

    def build():
        email = Email(metadata={VALID_METADATA})
        return email.add_section(FullWidth(content=TextBlock("<p>Body.</p>")))
"""

RETURNS_BUILDER = f"""
    from pyhermes.builder import EmailBuilder, FullWidth, TextBlock

    def build():
        return (
            EmailBuilder()
            .metadata({VALID_METADATA})
            .section(FullWidth(content=TextBlock("<p>Body.</p>")))
        )
"""


class TestResolvingAFixture:
    @pytest.mark.parametrize("name", sorted(all_fixtures()))
    def test_every_gallery_fixture_resolves(self, name):
        resolved_name, email = resolve(name)

        assert resolved_name == name
        assert isinstance(email, Email)

    def test_an_unknown_name_lists_what_is_available(self):
        with pytest.raises(PreviewError, match="kitchen_sink"):
            resolve("nosuchfixture")

    def test_the_error_points_at_the_other_form(self):
        """
        A user whose file is not a fixture needs telling *how* to name it, not
        just that this name was wrong.
        """
        with pytest.raises(PreviewError, match=r"path:callable|\.py:"):
            resolve("nosuchfixture")


class TestResolvingAModuleSpec:
    def test_a_callable_returning_an_email(self, tmp_path):
        module = write_module(tmp_path, "draft", RETURNS_EMAIL)

        name, email = resolve(f"{module}:build")

        assert name == "draft-build"
        assert isinstance(email, Email)

    def test_a_callable_returning_a_builder_is_built(self, tmp_path):
        """
        Both are public API; a caller should not have to remember which one
        their own function returns.
        """
        module = write_module(tmp_path, "draft", RETURNS_BUILDER)

        _, email = resolve(f"{module}:build")

        assert isinstance(email, Email)

    def test_the_name_combines_module_and_callable(self, tmp_path):
        """Two files both defining build() must not collide in output/."""
        first = write_module(tmp_path, "weekly", RETURNS_EMAIL)
        second = write_module(tmp_path, "monthly", RETURNS_EMAIL)

        assert resolve(f"{first}:build")[0] != resolve(f"{second}:build")[0]

    def test_a_missing_file_is_named(self, tmp_path):
        with pytest.raises(PreviewError, match="No such file"):
            resolve(f"{tmp_path / 'absent.py'}:build")

    def test_a_missing_attribute_is_named(self, tmp_path):
        module = write_module(tmp_path, "draft", RETURNS_EMAIL)

        with pytest.raises(PreviewError, match="no attribute 'absent'"):
            resolve(f"{module}:absent")

    def test_a_non_callable_attribute_is_rejected(self, tmp_path):
        module = write_module(tmp_path, "draft", "value = 3\n")

        with pytest.raises(PreviewError, match="not callable"):
            resolve(f"{module}:value")

    def test_a_wrong_return_type_names_what_came_back(self, tmp_path):
        module = write_module(tmp_path, "draft", "def build():\n    return 'html'\n")

        with pytest.raises(PreviewError, match="str, not a Document"):
            resolve(f"{module}:build")

    def test_an_import_error_is_reported_not_raised_raw(self, tmp_path):
        module = write_module(tmp_path, "draft", "import nonexistent_module_xyz\n")

        with pytest.raises(PreviewError, match="failed to import"):
            resolve(f"{module}:build")

    def test_a_builder_error_at_import_propagates_as_itself(self, tmp_path):
        """
        A ValidationError must not be flattened into "failed to import" — the
        builder's own message names the field, and that is the useful one.
        """
        module = write_module(
            tmp_path,
            "draft",
            """
            from pyhermes.builder import Email

            Email(metadata={"email_subject": "", "firm_name": "F", "campaign_name": "c"})
            """,
        )

        with pytest.raises(ValidationError, match="email_subject"):
            resolve(f"{module}:build")

    def test_a_target_with_no_callable_after_the_colon(self, tmp_path):
        with pytest.raises(PreviewError, match="names no callable"):
            resolve(f"{tmp_path / 'draft.py'}:")


class TestTheCommand:
    def test_it_writes_html_to_the_output_directory(self, tmp_path, capsys):
        code = main(["minimal", "--out", str(tmp_path)])

        assert code == EXIT_OK
        written = tmp_path / "minimal.html"
        assert written.is_file()
        assert written.read_text(encoding="utf-8").startswith("<!DOCTYPE html")
        assert str(written) in capsys.readouterr().out

    def test_what_it_writes_is_what_render_produces(self, tmp_path):
        """The CLI must not be a second rendering path."""
        main(["minimal", "--out", str(tmp_path)])

        expected = all_fixtures()["minimal"]().render()
        assert (tmp_path / "minimal.html").read_text(encoding="utf-8") == expected

    def test_it_writes_the_text_projection_beside_the_html(self, tmp_path, capsys):
        code = main(["minimal", "--out", str(tmp_path)])

        assert code == EXIT_OK
        written = tmp_path / "minimal.txt"
        assert written.is_file()
        assert str(written) in capsys.readouterr().out

    def test_what_it_writes_is_what_text_produces(self, tmp_path):
        """
        The no-second-rendering-path rule, applied to the second projection.
        An email has two readable parts since #109, and a CLI that produced
        its own version of either would be worse than useless.
        """
        main(["minimal", "--out", str(tmp_path)])

        expected = all_fixtures()["minimal"]().text()
        assert (tmp_path / "minimal.txt").read_text(encoding="utf-8") == expected

    def test_a_draft_target_gets_both_projections_too(self, tmp_path):
        """
        Both halves for a user's own build function, not only for a fixture.
        A draft is never in the registry, and that asymmetry is what
        ``capture_emails`` was created to close in the screenshot runner — so
        it is worth pinning that this half does not reintroduce it.
        """
        module = write_module(tmp_path, "draft", RETURNS_EMAIL)

        assert main([f"{module}:build", "--out", str(tmp_path)]) == EXIT_OK
        assert (tmp_path / "draft-build.html").is_file()
        assert (tmp_path / "draft-build.txt").is_file()

    def test_list_enumerates_the_gallery(self, capsys):
        code = main(["--list"])

        assert code == EXIT_OK
        # Both galleries: preview only ever *looks* at what it is handed, so
        # refusing to show a paged fixture would be an opinion it has no use
        # for. The registries stay apart for the test suite (#165).
        gallery = {**all_fixtures(), **all_paged_fixtures(), **all_brochure_fixtures()}
        assert capsys.readouterr().out.split() == sorted(gallery)

    def test_no_target_and_no_list_is_a_usage_error(self):
        with pytest.raises(SystemExit) as excinfo:
            main([])

        assert excinfo.value.code == 2

    def test_an_unresolvable_target_exits_build_failed(self, tmp_path, capsys):
        code = main(["nosuchfixture", "--out", str(tmp_path)])

        assert code == EXIT_BUILD_FAILED
        assert "error:" in capsys.readouterr().err

    def test_a_builder_error_prints_its_own_message(self, tmp_path, capsys):
        module = write_module(
            tmp_path,
            "draft",
            """
            from pyhermes.builder import Email

            def build():
                return Email(
                    metadata={"email_subject": "", "firm_name": "F", "campaign_name": "c"}
                )
            """,
        )

        code = main([f"{module}:build", "--out", str(tmp_path)])

        assert code == EXIT_BUILD_FAILED
        captured = capsys.readouterr().err
        assert "ValidationError" in captured
        assert "email_subject" in captured
        assert "Traceback" not in captured


class TestLinting:
    def test_a_clean_email_exits_zero(self, tmp_path, capsys):
        code = main(["minimal", "--lint", "--out", str(tmp_path)])

        assert code == EXIT_OK
        assert "No findings." in capsys.readouterr().out

    def test_findings_fail_the_command(self, tmp_path, capsys):
        """
        The exit code is the point: it is what lets this run in a shell or a
        hook rather than being read by a human every time.
        """
        module = write_module(
            tmp_path,
            "draft",
            f"""
            from pyhermes.builder import Email, FullWidth, TextBlock

            def build():
                email = Email(metadata={VALID_METADATA})
                return email.add_section(
                    FullWidth(content=TextBlock('<p><img src="a.png"></p>'))
                )
            """,
        )

        code = main([f"{module}:build", "--lint", "--out", str(tmp_path)])

        assert code == EXIT_LINT_ERRORS
        assert "img-width-attr" in capsys.readouterr().out

    def test_the_html_is_still_written_when_linting_fails(self, tmp_path):
        """Saving is not conditional on the email being clean — you want to look at it."""
        module = write_module(
            tmp_path,
            "draft",
            f"""
            from pyhermes.builder import Email, FullWidth, TextBlock

            def build():
                email = Email(metadata={VALID_METADATA})
                return email.add_section(
                    FullWidth(content=TextBlock('<p><img src="a.png"></p>'))
                )
            """,
        )

        assert main([f"{module}:build", "--lint", "--out", str(tmp_path)]) == EXIT_LINT_ERRORS
        assert (tmp_path / "draft-build.html").is_file()

    def test_its_findings_match_the_lint_api(self, tmp_path, capsys):
        """Same input, same findings — the CLI adds no rules of its own."""
        from qa.lint import format_findings, lint_html

        main(["kitchen_sink", "--lint", "--out", str(tmp_path)])
        printed = capsys.readouterr().out

        expected = format_findings(lint_html(all_fixtures()["kitchen_sink"]().render()))
        assert expected in printed


class TestScreenshots:
    def test_a_missing_browser_is_a_skip_not_a_failure(self, tmp_path, capsys, monkeypatch):
        """
        The [qa] extra is optional by design, so an absent browser must not
        turn a perfectly good email into a non-zero exit.
        """
        from qa import preview

        def refuse(*_args, **_kwargs):
            raise preview.ScreenshotError("no browser here")

        monkeypatch.setattr(preview, "capture_emails", refuse)

        code = main(["minimal", "--screenshot", "--out", str(tmp_path)])

        assert code == EXIT_OK
        assert "screenshots skipped" in capsys.readouterr().err

    def test_a_skip_does_not_mask_lint_errors(self, tmp_path, monkeypatch):
        """The two flags are independent; one degrading must not rescue the other."""
        from qa import preview

        monkeypatch.setattr(
            preview,
            "capture_emails",
            lambda *_a, **_k: (_ for _ in ()).throw(preview.ScreenshotError("none")),
        )
        module = write_module(
            tmp_path,
            "draft",
            f"""
            from pyhermes.builder import Email, FullWidth, TextBlock

            def build():
                email = Email(metadata={VALID_METADATA})
                return email.add_section(
                    FullWidth(content=TextBlock('<p><img src="a.png"></p>'))
                )
            """,
        )

        code = main([f"{module}:build", "--lint", "--screenshot", "--out", str(tmp_path)])

        assert code == EXIT_LINT_ERRORS

    @requires_browser
    def test_it_captures_through_the_same_runner(self, tmp_path):
        """
        A user's draft is not in the gallery, so this is the case capture_gallery
        could never serve — and the reason capture_emails exists.
        """
        module = write_module(tmp_path, "draft", RETURNS_EMAIL)

        code = main([f"{module}:build", "--screenshot", "--out", str(tmp_path)])

        assert code == EXIT_OK
        shots = tmp_path / "screenshots"
        assert (shots / "draft-build-chromium-desktop.png").is_file()
        assert (shots / "draft-build-chromium-mobile.png").is_file()
        assert (shots / "run.json").is_file()


class TestOpen:
    def test_it_opens_the_file_it_wrote(self, tmp_path, monkeypatch):
        opened = []
        monkeypatch.setattr("qa.preview.webbrowser.open", opened.append)

        main(["minimal", "--open", "--out", str(tmp_path)])

        assert opened == [(tmp_path / "minimal.html").resolve().as_uri()]
