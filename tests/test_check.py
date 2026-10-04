"""
The portability check ships in the package (#278): its API, its command, and qa's re-export.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import pyhermes.check as check_module
import qa.lint
from pyhermes.builder import Email, FullWidth, TextBlock
from pyhermes.check import Severity, TargetError, check, load_target
from pyhermes.check.__main__ import EXIT_BUILD_FAILED, EXIT_LINT_ERRORS, EXIT_OK, main
from qa import preview
from qa.fixtures import kitchen_sink

DRAFT = """
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock


def build():
    return (
        EmailBuilder()
        .metadata({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
        .section(FullWidth(TextBlock("<p>From a draft.</p>")))
    )


def not_an_email():
    return 42
"""


@pytest.fixture
def draft(tmp_path: Path) -> Path:
    path = tmp_path / "weekly.py"
    path.write_text(DRAFT, encoding="utf-8")
    return path


class TestTheApi:
    def test_check_is_the_documents_own_rules(self):
        email = kitchen_sink.build()
        assert check(email) == qa.lint.lint_document(email)

    def test_qa_lint_is_the_same_module_objects(self):
        for name in qa.lint.__all__:
            assert getattr(qa.lint, name) is getattr(check_module.lint, name)

    def test_an_error_is_reported(self):
        email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
        email.add_section(FullWidth(TextBlock('<p><img src="https://example.com/x.png"></p>')))
        assert any(f.severity is Severity.ERROR for f in check(email))


class TestLoadingADraft:
    def test_a_builder_is_built_and_named_for_its_file(self, draft):
        name, document = load_target(f"{draft}:build")
        assert name == "weekly-build"
        assert "From a draft." in document.render()

    @pytest.mark.parametrize(
        ("suffix", "message"),
        [
            (":missing", "no attribute 'missing'"),
            (":not_an_email", "returned int"),
            ("", "names no callable"),
        ],
    )
    def test_a_bad_target_says_why(self, draft, suffix, message):
        with pytest.raises(TargetError, match=message):
            load_target(f"{draft}{suffix}")

    @pytest.mark.parametrize("drive", ["C:/u/weekly.py", "c:\\u\\weekly.py"])
    def test_a_drive_letter_is_never_the_separator(self, drive):
        """A Windows path with no callable names no callable, on any OS (#372)."""
        with pytest.raises(TargetError, match="names no callable"):
            load_target(drive)

    def test_a_drive_path_with_a_callable_splits_on_the_last_colon(self):
        with pytest.raises(TargetError, match=r"No such file: C:/u/weekly\.py"):
            load_target("C:/u/weekly.py:build")

    def test_preview_loads_through_the_same_loader(self, draft):
        assert preview.PreviewError is TargetError
        name, document = preview.resolve(f"{draft}:build")
        assert name == "weekly-build"
        assert document.render() == load_target(f"{draft}:build")[1].render()


class TestTheCommand:
    def test_it_writes_both_parts_and_exits_clean(self, draft, tmp_path, capsys):
        out = tmp_path / "out"
        assert main([f"{draft}:build", "--out", str(out)]) == EXIT_OK
        _, document = load_target(f"{draft}:build")
        assert (out / "weekly-build.html").read_text(encoding="utf-8") == document.render()
        assert (out / "weekly-build.txt").read_text(encoding="utf-8") == document.text()
        assert "No findings." in capsys.readouterr().out

    def test_a_lint_error_exits_one(self, tmp_path, capsys):
        broken = tmp_path / "broken.py"
        broken.write_text(
            DRAFT.replace("<p>From a draft.</p>", "<p><img src='https://example.com/x.png'></p>"),
            encoding="utf-8",
        )
        assert main([f"{broken}:build", "--out", str(tmp_path)]) == EXIT_LINT_ERRORS
        assert "img-width-attr" in capsys.readouterr().out

    def test_an_unbuildable_draft_exits_two(self, tmp_path, capsys):
        assert main([f"{tmp_path / 'nope.py'}:build"]) == EXIT_BUILD_FAILED
        assert "No such file" in capsys.readouterr().err

    def test_it_runs_as_a_module(self, draft, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "pyhermes.check", f"{draft}:build", "--out", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == EXIT_OK, result.stderr
        assert (tmp_path / "weekly-build.html").is_file()
